# PRD: JSON Output For All Commands

## Objective

Give every command that prints a plain-text status message a `--format table|json` option. With `--format json` the command prints one JSON document to stdout instead of the status text. The default stays `table`.

## Background

Only `list`, `show` and `folders` have `--format` (`src/sqlcl_conn_mng/cli.py`, `_add_format`). The other ten commands - `add`, `update`, `delete`, `rename`, `move`, `clone`, `test`, `add-folder`, `delete-folder`, `export` - print status lines, and the batch commands print `[OK]` / `[FAIL]` lines and a `Summary:` line. A script that wants a machine-readable result has to parse that text. Decisions behind this task are in `open_questions.md`.

## Requirements

### REQ-1: `--format` on the ten status commands

`add`, `update`, `delete`, `rename`, `move`, `clone`, `test`, `add-folder`, `delete-folder` and `export` accept `--format` with the choices `table` and `json`, default `table`, using the same `_add_format` helper as `list`. Any other value is a usage error (exit 2). The option is listed in `--help` and in the README options table.

### REQ-2: Default output unchanged

Without `--format`, or with `--format table`, the stdout of all thirteen commands is byte-for-byte what it is today, including the `Deleting N connection(s)` line of `delete`.

### REQ-3: Single-result envelope

With `--format json`, a command that acts on one object (`add`, `update`, `rename`, `clone`, `add-folder`, `delete-folder`, `export`, and `delete`, `move`, `test` with `--name`) prints one object with the keys `status` (`"ok"`), `command` (the command name) and `message` (the text the command prints today), plus these fields:

| Command | Extra fields |
| ------- | ------------ |
| `add` | `name`, `folder` (omitted when not given) |
| `update` | `name`, `new_name` (omitted when not changed) |
| `rename` | `name`, `new_name` |
| `clone` | `name`, `new_name` |
| `delete`, `move`, `test` with `--name` | `name`; `move` also `folder` |
| `add-folder`, `delete-folder` | `folder` |
| `export` | `count`, `output` |

The helpers in `sqlcl.py` keep returning strings; nothing parses SQLcl output.

### REQ-4: Batch envelope

With `--format json`, `delete`, `move` and `test` given `--filter` or `--all` print one object with `status` (`"ok"` when no item failed, else `"error"`), `command`, `results` (a list of `{"name", "status", "message"}` in the processing order, `status` being `"ok"` or `"error"`), `ok` and `failed` (counts). The exit code is 1 when any item failed, as today. An empty match is an error (REQ-5).

### REQ-5: Error object

With `--format json`, a failure that `main` catches (`SqlclError`, `StoreError`, `ValueError`, `OSError`) and the keyboard interrupt print `{"status": "error", "command": "<name>", "message": "<text>"}` to stdout, in addition to the existing stderr log line. The exit code is unchanged (1). This applies to every command that has `--format`, including `list`, `show` and `folders`. Usage errors raised by argparse (exit 2) stay plain text on stderr.

### REQ-6: Stdout is one JSON document

With `--format json`, stdout contains exactly one JSON document and nothing else, on every path. The `Deleting N connection(s)` line of `delete`, the `[OK]` / `[FAIL]` lines, the `Summary:` line and the second line of `add` (folder move result) are not printed. Logging stays on stderr. `show --check-password` partial failures keep their current behaviour.

### REQ-7: Tests

Unit tests in `tests/test_cli.py` cover, for every command, the `json` path and the unchanged `table` path; the choice validation; the batch envelope with a failing item and an empty match; the error object; and that `json.loads(stdout)` succeeds on each path. One integration test runs a batch command with `--format json` against real SQLcl.

### REQ-8: Documentation and version

The README options table lists `--format` for the ten commands, and a section describes the envelopes of REQ-3, REQ-4 and REQ-5. `pyproject.toml` version goes from `0.4.0` to `0.5.0` (additive change to input parameters, repository owned by `s2005`, no `upstream` remote), `uv.lock` is refreshed, any global copy is reinstalled, and `--version` prints `0.5.0`.

## Non-Requirements

- No change to the default format, to the table output, or to exit codes.
- No change to the `sqlcl.py` helper signatures or return types, and no parsing of SQLcl text into fields.
- No change to `list`, `show` and `folders` JSON bodies; only their failure path gains the error object (REQ-5).
- No JSON for argparse usage errors.
- No JSON Lines mode and no new output formats.

## Acceptance Criteria

- **AC-1** - Each of the ten commands accepts `--format table` and `--format json`, defaults to `table`, and exits 2 on any other value (REQ-1)
- **AC-2** - Existing tests pass unchanged and the table output of all thirteen commands is identical to before (REQ-2)
- **AC-3** - Each single-result command prints one object with `status`, `command`, `message` and its extra fields under `--format json` (REQ-3)
- **AC-4** - `delete`, `move` and `test` with `--filter` or `--all` print the `results` envelope, with exit 1 when any item failed (REQ-4)
- **AC-5** - A caught failure under `--format json` prints the error object on stdout, keeps the stderr log and exit code 1, while usage errors stay plain text (REQ-5)
- **AC-6** - `json.loads` of stdout succeeds for every command on success, partial failure and error paths, including `delete` (REQ-6)
- **AC-7** - New unit tests and one integration test pass, and `make check` and `make unit` are clean (REQ-7)
- **AC-8** - The README documents the option and the envelopes, the version is `0.5.0`, and `--version` prints it (REQ-8)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| src/sqlcl_conn_mng/cli.py | Update |
| tests/test_cli.py | Update |
| tests/integration/test_batch_compat.py | Update |
| README.md | Update |
| pyproject.toml | Update |
| uv.lock | Update |
