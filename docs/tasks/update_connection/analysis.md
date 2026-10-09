# Analysis: Update Command For Saved Connections

## Goal

Let a user change the name, user, connect string and/or password of one saved connection with a single `update` command (REQ-1).

## Current Behavior

- `src/sqlcl_conn_mng/cli.py` registers `add`, `rename`, `clone` and others; every write goes through `sqlcl.SqlclRunner` (`sqlcl.py:95`). `_cmd_add` (`cli.py:466`) reads the password with `_read_password` (`cli.py:457`) and calls `sq.save_connection` (`sqlcl.py:225`), which builds `connect -save NAME [-savepwd] [-replace] -password ... user@cs` and feeds it on stdin.
- `ConnectionStore` (`store.py:65`) is read-only: it parses `connections/<id>/dbtools.properties` through `parse_properties` (`properties.py:85`), which returns a dict and has no writer. `SavedConnection` is frozen (`models.py:11`).
- `connect -save N -replace` keeps the id and changes only `credentials.sso` when user and connect string are unchanged; `rename -conn` rewrites `dbtools.properties`; folders reference ids, not names (`findings.md`, "Effects per Operation", "Connection Id").
- Changing a password today needs `add --replace` with the user and connect string.

## Feasibility

Feasible. Name, user and connect string are plain keys in `dbtools.properties`. A Python prototype wrote such files with the Java escaping, no header, LF endings, UTF-8; all 48 files re-serialized byte-identically and SQLcl listed and showed the Python-written files (`findings.md`, "Properties Round Trip"). The password stays with SQLcl, so the unverified wallet format is not needed (REQ-3). The open point is Q2: whether `connect -replace` with a changed user or URL also touches `dbtools.properties` or the folder, which Phase 1 probes.

## Approach

Two writers behind one command:

| Part | Writer | Why |
| ---- | ------ | --- |
| Password | SQLcl `connect -save -replace` | Wallet is written only by SQLcl; existing `save_connection` |
| Name, user, connect string | Python, atomic rewrite of `dbtools.properties` | No SQLcl command changes user or URL without a connect (REQ-2) |

Alternatives considered:

| Option | Advantages | Disadvantages |
| ------ | ---------- | ------------- |
| A. All through SQLcl (`connect -replace`, `rename`) | No Python store writes | User or URL change needs the password and a live database; not what the user asked for (Q3) |
| B. Python for metadata, SQLcl for password (chosen) | Password-free metadata edits; password-only works; SQLcl stays sole wallet writer | First Python write path; needs escaping and atomicity tests |
| C. Python for everything incl. wallet | No SQLcl needed | Wallet writer is unverified for production (`findings.md`, "Security and Compatibility Boundary"); out of scope |

## Implementation Notes

- **Writer (REQ-2).** Add `format_properties(props: dict[str, str]) -> str` to `properties.py`: escape `\` as `\\`, `:` `=` `#` `!` with a leading backslash, a leading space as backslash-space, tab/newline/CR/form feed as `\t \n \r \f`; keys likewise plus every space; one `key=value` per line, LF, final LF, no header. Assert `parse_properties(format_properties(p)) == p` in tests for specials and non-ASCII.
- **Store write (REQ-2).** Add `ConnectionStore.update_properties(conn_id, changes)` to `store.py`: re-read the file, apply `name`, `userName`, `connectionString` changes in place (dict keeps key order and unknown keys), write bytes to a temporary file in the same directory, `os.replace` it onto the target. Update the class docstring and module docstring ("Read-only"). The read decodes UTF-8 with a Latin-1 fallback (`store.py:39`); the write is always UTF-8, so a Latin-1 file is rewritten as UTF-8. Raise `StoreError` when the file is missing.
- **Comments in the file.** `parse_properties` drops comments and blank lines; SQLcl-written files have none (`findings.md`). A rewrite would drop them, so the writer refuses a file that has a comment line or a continuation line (REQ-4 failure, `StoreError`) instead of silently losing text.
- **Command (REQ-1, REQ-3, REQ-4).** `_cmd_update` in `cli.py`: validate the option set, look the connection up (`store.get`, `cli.py` pattern of `_select_connections`) and refuse a name shared by several records (`_reject_duplicate_names`), validate values with `sq.validate_value`, check the new name against other connections case-insensitively, then password step, then file write. `--password-env` and `--prompt-password` form an argparse mutually exclusive group; `--prompt-password` reuses `getpass`. `_read_password` currently reads `args.password_env` or prompts; it is generalized so `update` can call it without changing `add`.
- **Password step.** `sq.save_connection(runner, name, user, cs, password, save_password=not args.no_save_password, replace=True)` with the new-or-current user and connect string, under the old name; the name is changed afterwards by the file write. The output filtering (`_without_password`, `sqlcl.py:249`) already protects REQ-5.
- **Order and partial failure (REQ-4).** If SQLcl rejects the connect, nothing was changed. If the file write fails afterwards, raise an error that says the password was already replaced.
- **Value limits.** The Python path accepts what `validate_value` accepts (no newline, CR, double quote), the same limit as `add`, even though the escaping could carry more; this keeps `update` and `add` consistent.
- **No concurrency control.** SQLcl takes no lock either (`findings.md`, "Atomicity"); the atomic replace prevents a torn file only.
- **Docs.** The README intro, "Store format" and the SKILL description say the tool never writes the store from Python; they change (REQ-6). Version bump follows the global rule (Q9).

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| `connect -replace` with a changed user or URL rewrites `dbtools.properties` or changes the folder differently than assumed | Phase 1 probes it; Phase 3 order is conditional on the result |
| Python writer produces a file SQLcl misreads for a special value | Round-trip unit tests and an integration test that runs `connmgr show` and `connmgr list` on a Python-edited store |
| Comments or continuation lines in a hand-edited file are lost | Writer refuses such a file |
| Stale saved password after a user or URL change without a password | Documented in README; no runtime warning by decision (Q11) |
| Partial update when the file write fails after the password step | Error text names the state; validation runs first so failure is rare |
| Name collision SQLcl would resolve case-insensitively | Refuse case-insensitive collisions (Q12) |
| Windows file replace while SQLcl holds the file | `os.replace` failure surfaces as `OSError`, which `main` already reports with exit 1 |

## Test Strategy

- Unit, `tests/test_properties.py`: `format_properties` escaping table and round trip with `parse_properties`.
- Unit, `tests/test_store.py`: `update_properties` keeps id, other keys, order, wallet bytes and `folders.json`; atomic (no temp file left); missing file; comment line refused.
- Unit, `tests/test_cli.py`: option validation (REQ-1), no SQLcl call for metadata-only changes, password step arguments from a fake runner, ordering, failure leaves the store unchanged, collision rules, no password in captured output (REQ-5). Follows the fake-runner style in the existing file.
- Integration, `tests/integration/test_update_compat.py` using the harness (`tests/integration/harness.py`): SQLcl reads the Python-edited values; password change keeps the id and the saved-password state follows the flags. Saved-password scenarios skip without the database variables, like `test_saved_password_compat.py`.
