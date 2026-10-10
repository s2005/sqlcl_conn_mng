# Open Questions: JSON Output For All Commands

## Q1: Which commands get `--format`?

- **Why it matters**: only `list`, `show` and `folders` have `--format table|json` (`src/sqlcl_conn_mng/cli.py`, `_add_format`). Ten commands print plain-text status lines: `add`, `update`, `delete`, `rename`, `move`, `clone`, `test`, `add-folder`, `delete-folder`, `export`.
- **Options**: (a) all ten; (b) all except `export`, whose result is the file it writes.
- **Recommended**: (a) - `export` still prints `Exported N connection(s) to PATH` to stdout, so a script reading stdout benefits the same way.
- **Answer**: (a) all ten - decided by user ("go with the recommendations"). Carried by REQ-1.

## Q2: What is the JSON shape of a status message?

- **Why it matters**: the helpers in `sqlcl.py` (`rename_connection`, `move_connection`, `clone_connection`, `add_folder`, ...) return a message string, not structured data. The shape decides whether they change.
- **Options**: (a) one common envelope `{"status": "ok", "command": "<name>", "message": "<text>"}` plus command-specific fields known to the CLI (`name`, `new_name`, `folder`, `count`); (b) per-command shapes only, no `message`; (c) parse the SQLcl text into fields.
- **Recommended**: (a) - the `sqlcl.py` helpers keep returning strings, nothing parses SQLcl output, and every command shares the keys `status`, `command`, `message`.
- **Answer**: (a) common envelope - decided by user. The `sqlcl.py` helpers keep returning strings; the CLI adds the fields it already knows. Carried by REQ-3.

## Q3: What do batch selections (`--filter`, `--all`) print under `--format json`?

- **Why it matters**: `_run_batch` prints `[OK] name` / `[FAIL] name: reason` per connection and a `Summary:` line; `delete` also prints a `Deleting N connection(s)` line first. Stdout must be exactly one JSON document, so those lines cannot be mixed in.
- **Options**: (a) one object `{"status", "command", "results": [{"name", "status", "message"}], "ok": N, "failed": N}`; (b) one JSON object per line.
- **Recommended**: (a) for `--filter` / `--all`; a `--name` selection keeps the single-object form from Q2. Exit code stays 1 when any item failed.
- **Answer**: (a) one object with `results[]` - decided by user. `--name` keeps the single-object form of Q2. Carried by REQ-4 and REQ-6.

## Q4: How are failures reported under `--format json`?

- **Why it matters**: today `main` logs the error to stderr through `logger.error` and returns 1. A script reading JSON from stdout gets nothing on failure.
- **Options**: (a) unchanged: stderr log, empty stdout, exit 1; (b) also print `{"status": "error", "command": "<name>", "message": "<text>"}` to stdout; (c) same object on stderr.
- **Recommended**: (b) - stdout is always valid JSON when `--format json` is given, the stderr log stays, exit code unchanged. Usage errors (exit 2, argparse) stay plain text.
- **Answer**: (b) JSON error object on stdout plus the existing stderr log - decided by user. Applies to every command that has `--format`, including `list`, `show` and `folders`. Carried by REQ-5.

## Q5: Does the default change?

- **Why it matters**: scripts parse today's plain text.
- **Options**: (a) default stays `table`, JSON only on request; (b) default becomes `json`.
- **Recommended**: (a) - matches `list`, `show`, `folders` and the user request ("if we have ... format json").
- **Answer**: (a) - decided by user request wording and `cli.py` `_add_format` (`default="table"`). Plain-text output of the ten commands is byte-for-byte unchanged without `--format`.

## Q6: Is a version bump and README update required?

- **Why it matters**: the change adds an input parameter to ten commands.
- **Options**: (a) bump minor `0.4.0` to `0.5.0`, update the README options table and examples; (b) no bump.
- **Recommended**: (a) - `~/.claude/CLAUDE.md` rule "Version bump on input parameter change" applies: `git remote -v` shows only `origin` (no `upstream`) and `git config user.name` is `s2005`. The change is additive, so minor. Missing option documentation is a defect.
- **Answer**: (a) - settled by the global rule and `pyproject.toml` (`version = "0.4.0"`), not by the user.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | REQ-1 |
| Q2 | Answered | REQ-3 |
| Q3 | Answered | REQ-4, REQ-6 |
| Q4 | Answered | REQ-5 |
| Q5 | Answered | REQ-2 |
| Q6 | Answered | REQ-8 |
