# Analysis: Batch Selection With --all And --filter

## Goal

Run `test`, `show`, `delete` and `move` over many connections selected by `--all` or `--filter`, and narrow `list` and `export` by `--filter` (REQ-1 to REQ-6).

## Current Behavior

- `src/sqlcl_conn_mng/cli.py` builds each subcommand with `_add_name`, which declares `--name` as `required=True` (line 37-38).
- Handlers `_cmd_test`, `_cmd_delete`, `_cmd_move` and `_cmd_show` take one name from `args.name` and call `sq.check_connection`, `sq.delete_connection`, `sq.move_connection` or `sq.show_connection` (lines 262-287, 357-382).
- Errors are exceptions (`SqlclError`, `StoreError`, `ValueError`, `OSError`); `main` logs them and returns 1 (lines 455-459). There is no per-item error handling.
- `ConnectionStore.connections()` returns every `SavedConnection` (`store.py` line 92); `list` already filters in memory with `_in_folder` (cli.py line 241).
- `_cmd_export` iterates all connections (lines 397-407).
- `tests/test_cli.py` drives `main(argv)` with a `fake_home` fixture and `mocker` for SQLcl calls.

## Feasibility

Straightforward. Selection is an in-memory filter over `store.connections()`, and each action is an existing function of `sqlcl.py` that already works per name. No change to `sqlcl.py` or `store.py` is needed. SQLcl is started once per connection (each `sq.*` call runs it), which is acceptable for the stated use.

## Approach

Add a shared selector option group and a shared batch runner in `cli.py`.

| Option | Advantages | Disadvantages |
| ------ | ---------- | ------------- |
| A: shared helpers `_add_selector`, `_select_names`, `_run_batch` in `cli.py` (recommended) | One place defines flags, matching and reporting; handlers stay small; `--name` path untouched | Slightly more indirection in handlers |
| B: loop in each handler | No new abstraction | Four copies of matching, reporting and exit-code logic that can drift |
| C: new `batch.py` module | Isolated and testable | Over-sized for roughly 60 lines; the module would depend on `cli` argument shapes |

Option A. Details:

- `_add_selector(parser)` adds a required `argparse` mutually exclusive group with `--name`, `--filter` and `--all` (REQ-1). It replaces `_add_name` on `test`, `show`, `delete` and `move`; `_add_name` stays for `rename` and `clone`.
- `_select_names(args, store)` returns `sorted` names: the `--name` value after an existence check, every name for `--all`, or `fnmatch.fnmatchcase` matches (REQ-2, REQ-3). The `--name` branch keeps the `No saved connection named ...` `ValueError`. Wildcards in a `--name` value are not expanded.
- `_run_batch(args, names, action)` runs `action(name) -> str`. For a `--name` selection it calls `action` directly so output and exceptions are unchanged (REQ-4, AC-2). For a batch it catches `sq.SqlclError`, `StoreError`, `ValueError` and `OSError` per name, prints `[OK]` or `[FAIL]` lines and the summary, and returns 1 on any failure or empty selection.
- `show` builds data per name through a helper extracted from `_cmd_show`; batch JSON is a list, a single `--name` stays an object (REQ-6).
- `delete` checks `--yes` before resolving or acting, prints matched names, then runs the batch (REQ-5).
- `list` and `export` get an optional `--filter` applied with the same matcher after `--folder` where present.

## Implementation Notes

- Names are resolved once up front (REQ-3), so `delete` and `move` iterating a snapshot do not change membership mid-run.
- `move --folder` is normalised once by `sq.move_connection`; each call is independent.
- `--filter` patterns beginning with `/` are not an issue for Git Bash path conversion, but a `*` must be quoted in the shell; the README examples quote it.
- Plain ASCII markers `[OK]` and `[FAIL]` avoid Unicode encoding problems on Windows consoles.
- Empty `--filter ''` matches nothing and therefore hits the empty-selection error.
- Version: `s2005` owns the repo and there is no `upstream` remote, so the bump to `0.3.0` applies (`open_questions.md`, Q6).

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Bulk `delete` removes more than intended | `--yes` stays mandatory; matched names printed first; glob is anchored on the full name (AC-7) |
| Behaviour change for `--name` users | `--name` path bypasses the batch reporter; tests assert the old output (AC-2) |
| Argparse error text changes when `--name` is no longer individually required | Exit code stays 2; a test pins the usage error (AC-1) |
| Batch `test` is slow with many connections | Sequential by design; parallelism is a non-requirement |

## Test Strategy

- Unit (`tests/test_cli.py`, mocking `sq.*`): selector exclusivity per command, glob case sensitivity, empty match, continue-on-failure and exit code, delete without `--yes`, show batch JSON and table, list and export `--filter`, unchanged `--name` output.
- Integration (`tests/integration/test_batch_compat.py`, real SQLcl, style of `test_connection_ops_compat.py`): `move --filter` then `delete --filter --yes` on connections created in the harness store.
