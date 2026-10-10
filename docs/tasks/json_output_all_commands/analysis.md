# Analysis: JSON Output For All Commands

## Goal

Make the ten status-printing commands emit one JSON document under `--format json` (REQ-1, REQ-3, REQ-4, REQ-5, REQ-6) without changing any default output (REQ-2).

## Current Behavior

All code is in `src/sqlcl_conn_mng/cli.py`.

- `_add_format` (line 29) adds `--format table|json`; it is applied to `list`, `show` and `folders` only. `_dump` (line 378) prints sorted, indented JSON.
- `_run_batch` (line 355) serves `delete`, `move` and `test`. With `--name` it prints the action result; otherwise it prints `[OK] name` / `[FAIL] name: reason` and `Summary: N ok, M failed`, returning 1 on any failure.
- `_cmd_delete` prints `Deleting N connection(s): ...` before the batch (line 616).
- `_cmd_add` prints `Connection NAME saved` and, with `--folder`, the result of `sq.move_connection` as a second line.
- `_cmd_rename`, `_cmd_clone`, `_cmd_add_folder`, `_cmd_delete_folder` print the string returned by the `sqlcl.py` helper. `_cmd_update` prints `Connection NAME updated`. `_cmd_export` writes the file and prints `Exported N connection(s) to PATH`.
- `main` (line 714) catches `SqlclError`, `StoreError`, `ValueError`, `OSError` and `KeyboardInterrupt`, logs to stderr and returns 1. It has no knowledge of the command or of `--format`.
- `sqlcl.py` helpers (`rename_connection`, `move_connection`, `clone_connection`, `add_folder`, `delete_folder`, `delete_connection`, `check_connection`) return `str`.

## Feasibility

Straightforward. Every command already produces the message text; the work is to route it through one emit function that chooses text or JSON. The batch loop already knows each item's outcome. The only structural change is that `main` needs the command name and format for the error object (REQ-5), both available on `args` (`args.command`, `getattr(args, "format", "table")`).

## Approach

Two options for producing the JSON message.

| Option | Advantages | Disadvantages |
| ------ | ---------- | ------------- |
| A: Emit the existing string as `message` plus CLI-known fields (chosen, Q2) | No change to `sqlcl.py`; no dependency on SQLcl text; small diff | `message` is human text, not structured |
| B: Make `sqlcl.py` return structured results | Cleanly typed fields | Large diff across helpers and their tests; out of ticket scope |
| C: Parse SQLcl output into fields | Rich fields | Fragile against SQLcl releases |

Recommended: A, as decided in Q2.

Design for A:

1. Add `_add_format(p)` to the ten parsers (REQ-1).
2. Add `_emit_ok(args, message, **fields)`: in table mode `print(message)` (REQ-2); in json mode `_dump({"status": "ok", "command": args.command, "message": message, **fields})` (REQ-3). Fields whose value is `None` are dropped.
3. Change `_run_batch` so that in json mode it collects `{"name", "status", "message"}` per item instead of printing, then dumps the batch envelope (REQ-4). With `--name` it calls `_emit_ok(args, ..., name=...)`. `_cmd_delete` prints its `Deleting ...` line only in table mode (REQ-6).
4. `_cmd_add` builds its message from both lines; in table mode it still prints two lines (REQ-2), in json mode one object with `name` and `folder`.
5. In `main`, on the caught exceptions and on `KeyboardInterrupt`, after `logger.error`, call `_emit_error(args, message)` which prints the error object only when `getattr(args, "format", "table") == "json"` (REQ-5).

## Implementation Notes

- `args.command` is set by `add_subparsers(dest="command")`; the `--command NAME` placement is normalised before parsing, so the value is always the real name.
- The `message` of an `--name` batch item is the helper's return string, the same text printed today.
- Item order in `results` follows `_select_names`, sorted by name then id.
- The batch `status` is `"error"` when `failed > 0`; the exit code stays 1 and the document is still printed.
- A failing `test --name` raises; it reaches `main` and becomes the error object (REQ-5), as `--name` does not use the continue-on-failure loop.
- `getpass` writes its prompt to the terminal, not stdout, so `--password-env` is not needed for a valid JSON stdout; a prompt does not corrupt the document.
- `export` already writes JSON to a file; `--format json` only changes its stdout status line.
- Comments must follow the style of `cli.py`; no emoji, no non-ASCII characters in code.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Table output changes by accident (REQ-2) | Keep the existing tests unchanged; add a table-path assertion per command |
| A stray `print` or logger output reaches stdout in json mode | Test `json.loads(capsys stdout)` on every path (AC-6); logging already goes to stderr |
| `show --check-password` partial failure logs but still returns data | Out of scope; unchanged |
| Error object printed twice when `KeyboardInterrupt` follows a partial document | A single document is printed after the work finishes; batch output is built in memory first |

## Test Strategy

Unit tests in `tests/test_cli.py` with the existing fake runner and store fixtures: per command, json and table paths; choice validation (exit 2); batch envelope with a failing item and with an empty match; error object for each caught exception type; `json.loads` on every stdout. One integration test in `tests/integration/test_batch_compat.py` runs `move --filter ... --format json` against real SQLcl and parses the result.
