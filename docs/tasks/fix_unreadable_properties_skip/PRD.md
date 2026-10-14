# PRD: Skip Unreadable Connection Properties

## Objective

When one connection's `dbtools.properties` cannot be parsed, read commands skip that connection, log a warning that names its id and file, and keep working on the rest of the store.

## Background

`ConnectionStore.connections` (`src/sqlcl_conn_mng/store.py:160-186`) parses every `dbtools.properties`. A malformed `\u` escape makes `parse_properties` raise `ValueError` (`src/sqlcl_conn_mng/properties.py:54`), which ends the whole loop. `main` reports `Malformed unicode escape in properties text: \u12zz` and exits 1, without saying which of the connections is broken. Every command that lists or selects connections fails the same way. SQLcl 25.4.1 itself crashes on every `connmgr` command against such a store, so the tool is the only place a user can find the broken file. Reproduced on a SQLcl-built store (see `analysis.md`). Found by the test gap review (finding F3).

## Requirements

### REQ-1: A connection whose properties cannot be parsed is skipped with a warning

`ConnectionStore.connections()` catches `ValueError` from parsing one `dbtools.properties`, leaves that connection out of the result, and logs one `WARNING` per connection id per `ConnectionStore` instance. The warning names the connection id, the file path and the parse error, for example `Skipping connection <id>: cannot parse <path>: Malformed unicode escape ...`. Other connections are returned as before.

### REQ-2: Read commands keep working and keep their exit codes

`list`, `show`, `folders`, `export` and selector-based commands act on the readable connections. The skip alone does not change the exit code. The warning goes to the log (stderr), so the JSON document on stdout under `--format json` stays valid.

### REQ-3: Direct reads of the broken file still fail

`read_properties`, `check_rewritable` and `update_properties` on the broken connection's id keep raising, so nothing rewrites a file the tool could not parse.

### REQ-4: README states the behaviour

`README.md` says that a connection whose `dbtools.properties` cannot be parsed is skipped with a warning naming its file, and that SQLcl itself fails on every command until the file is repaired or removed.

### REQ-5: Patch version bump

The project version in `pyproject.toml` (and `uv.lock`) goes from 0.9.2 to 0.9.3, so the fixed release is distinguishable from the defective one. No input parameter changes.

## Non-Requirements

- `OSError` while reading a file (see `open_questions.md` Q4): the command still fails.
- Repairing or deleting the broken file.
- Malformed `folders.json` - task `fix_malformed_folders_json`.

## Acceptance Criteria

- **AC-1** - Unit test: a store with one malformed file returns the other connections from `connections()`, and `caplog` holds exactly one warning with the id and path even after several calls on the same instance (REQ-1)
- **AC-2** - CLI tests: `list --format json` returns the readable connections, valid JSON and exit 0; `folders` shows the broken id unnamed; `export` writes the readable connections (REQ-2)
- **AC-3** - Unit test: `read_properties` and `update_properties` on the broken id still raise, and the file bytes are unchanged (REQ-3)
- **AC-4** - The SQLcl-built reproduction from `analysis.md` lists two of the three connections and logs the warning with the path (REQ-1, REQ-2)
- **AC-5** - README updated and `markdownlint-cli2` reports no issue (REQ-4)
- **AC-6** - `make check` and `make unit` pass (REQ-1, REQ-2, REQ-3)
- **AC-7** - `uv run sqlcl-conn-mng --version` prints 0.9.3 (REQ-5)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| src/sqlcl_conn_mng/store.py | Update |
| tests/test_store.py | Update |
| tests/test_cli.py | Update |
| README.md | Update |
| pyproject.toml | Update |
| uv.lock | Update |
