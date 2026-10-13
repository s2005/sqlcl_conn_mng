# Analysis: Copy Saved Connections Between Homes

## Goal

Copy saved connections, including their saved passwords, from one SQLcl store to another, without asking for the password and without contacting a database. Each copy keeps the folder path it had in the source.

## Current Behavior

- `ConnectionStore` (`src/sqlcl_conn_mng/store.py`) reads `connections/<id>/dbtools.properties` and `connection_folders/folders.json`. It writes only through `update_properties`, an atomic temp-file-and-`os.replace` rewrite of one properties file. `has_wallet` checks that `credentials.sso` exists and never opens it.
- Ids are matched by `_ID_PATTERN`, 22 characters from `[A-Za-z0-9_-]` (`store.py:33`). A directory outside that pattern is skipped by the tool even though SQLcl lists it.
- `resolve_home` (`store.py:42`) resolves a store root from an option, `SQLCL_CONN_HOME`, or `./.sqlcl`.
- All other writes go through `SqlclRunner` (`src/sqlcl_conn_mng/sqlcl.py:95`), which is bound to one `-home`. `_runner(args)` (`cli.py:298`) always builds it from `args.home`. `add_folder` and `move_connection` (`sqlcl.py:147`, `sqlcl.py:172`) wrap `connmgr add -folder` and `connmgr move -conn`.
- Batch commands share `_add_selector`, `_select_names`, `_reject_duplicate_names`, `_require_matches` and `_run_batch` (`cli.py:42`, `cli.py:346`, `cli.py:330`, `cli.py:360`, `cli.py:365`). `_run_batch` already catches `SqlclError`, `StoreError`, `ValueError` and `OSError` per item.
- No command reaches a second store.

## Feasibility

Straightforward. The id round-trip experiment (`docs/tasks/sqlcl_jar_store_investigation/findings.md`, "Id Round Trip") copied a connection directory byte for byte under new ids. SQLcl showed the password as saved and connected by the copied names. The wallet carries no reference to its directory or store. The remaining work is a file copy, a new-id generator, and two existing SQLcl wrappers pointed at the target home.

## Approach

### Option A: opaque directory copy plus SQLcl folder placement (chosen)

Copy `dbtools.properties` and `credentials.sso` into a staging directory in the target, rename it to `connections/<new id>`, then place the copy in its folder with `connmgr add -folder` (when missing) and `connmgr move` run against the target home.

| Advantages | Disadvantages |
| ---------- | ------------- |
| No database contact and no password handling; works offline (REQ-2) | Adds a second Python writer besides `update`; the README policy sentences must change (REQ-6) |
| Proven against SQLcl 25.4.1 by the id round trip | A nested folder still needs SQLcl, which takes 10-20 seconds per start |
| `folders.json` keeps a single writer, SQLcl (REQ-3) | Wallet formats other than the ones SQLcl writes are copied blindly, which is acceptable because nothing decodes them |

### Option B: SQLcl `connmgr import`

| Advantages | Disadvantages |
| ---------- | ------------- |
| SQLcl is the only writer | Needs a SQL Developer export, which nothing produces; converts to `ORACLE_BASIC`; passwords need `-key` handling |

### Option C: decode and `connect -save` in the target

| Advantages | Disadvantages |
| ---------- | ------------- |
| Wallet rewritten by SQLcl itself | Needs the database to be reachable; cleartext password in memory and on SQLcl stdin |

Option A follows from `open_questions.md` Q1.

## Implementation Notes

- **New id (REQ-2).** Use `base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=")`, which gives 22 characters matching `_ID_PATTERN`. Regenerate while the id exists under the target `connections/`.
- **Staging (REQ-2).** Use `tempfile.mkdtemp(dir=<to-home>/connections, prefix=".copy.")`, so the name starts with `.` and is never mistaken for a connection id. Copy with `shutil.copyfile`, then `os.replace(staging, final)`. On any exception, `shutil.rmtree(staging, ignore_errors=True)`. `copyfile` copies bytes only; no read into Python text and no logging of contents.
- **Store method (REQ-2).** `ConnectionStore.copy_connection_to(conn_id: str, target: ConnectionStore) -> str` returns the new id. It creates `target.home / CONNECTIONS_DIR` with `parents=True`. A missing source `dbtools.properties` raises `StoreError`.
- **Rollback on folder failure (REQ-3).** A `ConnectionStore.remove_connection_dir(conn_id)` helper removes the copied directory when the folder step raises. This is safe because `move` failed, so `folders.json` does not reference the id.
- **Folder existence (REQ-3).** Read `ConnectionStore(to_home).folders()` through `walk_folders`, once per connection rather than once per batch, because an earlier item may have created the folder.
- **Name clash (REQ-4).** Before copying each item, compare `name.casefold()` with every target connection name. This also catches two source names that differ only in case: the second one fails after the first is copied. That is the intended behaviour.
- **Same home (REQ-5).** Compare `Path.resolve()` of both homes before any read of the target. A clash raises `ValueError`, which `main` (`cli.py:779`) maps to exit code 1, as `_check_update_options` (`cli.py:575`) does for invalid option combinations.
- **Target runner.** Build `SqlclRunner` with `str(to_home)` instead of `args.home`, and only when a nested folder needs it. A root-only batch must not require SQLcl to be installed (REQ-3, AC-5).
- **Single result (REQ-1).** `_run_batch` with `--name` calls `_emit_ok(..., folder=getattr(args, "folder", None))`. `copy` has no `--folder` argument, so the field is omitted, which is acceptable. The success message should name the target home and folder, for example `Copied 'dev_local' to <to-home> /dev/local`.
- **Source is read-only.** The source store is opened for reading only. No SQLcl runs against `--home`.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A copied wallet is not accepted by another SQLcl release | Out of scope for 25.4.1, which is proven; the integration test runs against the pinned release in CI |
| A partial copy after a crash | Staging directory plus atomic rename; a leftover `.copy.*` directory is ignored by both readers because it fails `_ID_PATTERN` |
| Wallet bytes leak into logs | Only `shutil.copyfile` touches the file; tests assert the fake wallet bytes never appear in stdout or stderr |
| Target `folders.json` is malformed | `ConnectionStore.folders()` raises `StoreError`, so that item is reported `[FAIL]` before any write |
| User expects the copy to be tested | README states that the copy is not checked against a database; `test --home <to-home>` exists for that |

## Test Strategy

- **Unit, store (`tests/test_store.py`).** Byte-identical copy, new id shape and uniqueness, copy without a wallet, target creation, staging cleanup on an injected `OSError`, and the source unchanged (REQ-2).
- **Unit, CLI (`tests/test_cli.py`).** Parser and usage errors, `--name`, `--filter` and `--all` batches, JSON envelopes, the name clash in mixed case, the same-home refusal, the duplicate-name refusal, no SQLcl for root connections, mocked `add_folder` and `move_connection` calls with the target home, rollback when `move` raises, and no wallet bytes in output (REQ-1, REQ-3, REQ-4, REQ-5).
- **Integration (`tests/integration/test_copy_compat.py`).** With real SQLcl: copy a connection saved with a password (the `saved_pw_store` fixture, which needs the test database), then check that `connmgr show` in the target reports the password as saved and that `connmgr list` / `ConnectionStore.folders()` show the folder path. This skips without the database, like the other saved-password scenarios (REQ-2, REQ-3).
