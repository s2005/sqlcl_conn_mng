# PRD: Update Command For Saved Connections

## Objective

Add an `update` command that changes one saved connection's name, user, connect string and/or password, in any combination, for example only the password.

## Background

The tool can `add` (with `--replace`), `rename`, `move`, `clone`, `delete` and `test` connections, but cannot change one attribute of an existing connection. Changing a password today means rerunning `add --replace` with the user and connect string. SQLcl has no `connmgr update`. The password lives in `credentials.sso`, which only SQLcl writes. Name, user and connect string live in `dbtools.properties`, whose format and a Python round trip are documented in `docs/tasks/sqlcl_jar_store_investigation/findings.md`. Decisions are in `open_questions.md`.

## Requirements

### REQ-1: Command and options

`sqlcl-conn-mng update --name NAME` takes these change options, all optional, at least one required: `--new-name`, `--user`, `--connect-string`, `--password-env VAR`, `--prompt-password`. `--password-env` and `--prompt-password` are mutually exclusive. `--no-save-password` is accepted only together with a password source. Giving no change option, an unknown `--name`, or `--no-save-password` alone is an error (exit 1, nothing written). The global options apply as for other commands. `update` takes a single `--name`, no `--filter` or `--all`.

### REQ-2: Metadata change without a connect

`--new-name`, `--user` and `--connect-string` without a password source are written by Python into the connection's `dbtools.properties`: only the values `name`, `userName`, `connectionString` change; the id, every other key and its order, `folders.json` and `credentials.sso` stay byte-identical. The file is written atomically (temporary file, then replace), as UTF-8 with LF endings, a final LF and the Java escaping in `findings.md`. No SQLcl process runs. A saved password is left as is and no warning is printed.

One exception to "only three values change": SQLcl reads an imported connection (type `ORACLE_BASIC`, target in `host`, `port` and `serviceName`) from those keys and ignores `connectionString`. When `--connect-string` is given for such a connection, the file is rewritten the way SQLcl rewrites it on `connect -save -replace`: `type=ORACLE_DATABASE`, `host`, `port` and `serviceName` removed, keys ordered `name`, `type`, `connectionString`, `userName`, remaining keys after. `--connect-string` on any type other than `ORACLE_DATABASE` and `ORACLE_BASIC` is refused (exit 1) during validation, before the password step and before any write, with or without a password source. `--new-name` and `--user` never change `type` or the target keys.

### REQ-3: Password change through SQLcl

With `--password-env` or `--prompt-password`, the password is replaced with `connect -save NAME -replace -savepwd` using the new or current user and connect string. `--no-save-password` drops `-savepwd`. The connection id is kept. The password is read as `add` reads it, travels on stdin only, and the connection is changed only when SQLcl connects.

### REQ-4: Validation, ordering and failure behaviour

Before any write: the connection exists; its name is not shared by another record; each value passes the existing value checks (non-empty, no newline, carriage return or double quote); a new name does not equal, case-insensitively, any other connection's name. Then the password step (REQ-3) runs first and the file write (REQ-2) second. A failed validation or a failed connect leaves the store unchanged. If the file write fails after the password step, the error says the password was already replaced.

### REQ-5: No secret in output

The password never appears in stdout, stderr, log output at any level, error messages or the command line of the SQLcl process.

### REQ-6: Documentation and version

`README.md` documents the command in the command table, notes, examples, and updates the statements that the tool never writes the store from Python and that `ConnectionStore` is read-only; it states that a changed user or URL without a password leaves the saved password unchanged. `.claude/skills/sqlcl-conn-mng/SKILL.md` lists `update`. The project version is bumped from `0.3.0` to `0.4.0` in `pyproject.toml` and `uv.lock`, and the global copy is reinstalled.

### REQ-7: Tests

Unit tests cover the property writer, option validation, ordering and failures. Integration tests with real SQLcl prove SQLcl reads the Python-written file and that the password change works.

## Non-Requirements

- `--filter` / `--all` for `update`.
- Removing or changing `rename`, `add` or `clone`.
- Changing the folder of a connection (use `move`).
- Writing `credentials.sso` from Python.
- Validating a user or URL change against the database when no password is given.
- A runtime warning about a stale saved password.

## Acceptance Criteria

- **AC-1** - `update --help` lists all options; no change option, unknown name, and `--no-save-password` alone each exit 1 with a message and write nothing; both password sources together is a usage error (exit 2) (REQ-1)
- **AC-2** - `update --name X --user U2`, `--connect-string C2` and `--new-name N2` each change only that value in `dbtools.properties`; id, other keys and order, `folders.json` and `credentials.sso` are unchanged; no SQLcl process is started (REQ-2)
- **AC-3** - after a metadata update, `list`, `show` and real SQLcl `connmgr show` report the new values, for a connection SQLcl saved and for one imported from SQL Developer (REQ-2, REQ-7)
- **AC-11** - `--connect-string` on an imported (`ORACLE_BASIC`) connection converts it to `ORACLE_DATABASE` with the SQLcl key order and no `host`, `port` or `serviceName`; on another type it exits 1 and writes nothing; `--user` and `--new-name` leave an imported file's type and target keys alone (REQ-2)
- **AC-4** - `update --name X --password-env VAR` runs `connect -save X -replace -savepwd` with the stored user and connect string, keeps the id, and `show --check-password` reports a saved password (REQ-3)
- **AC-5** - `--no-save-password` leaves no saved password; `--prompt-password` reads a hidden prompt (REQ-3)
- **AC-6** - a wrong password leaves `dbtools.properties` and `credentials.sso` unchanged and exits 1; a colliding new name (any letter case), a missing connection and an invalid value are refused before any write (REQ-4)
- **AC-7** - a combined update (password, user, connect string, new name) applies all of them in the REQ-4 order (REQ-4)
- **AC-8** - a test password does not appear in captured stdout, stderr, logs or the SQLcl argument list (REQ-5)
- **AC-9** - README, SKILL.md and version `0.4.0` are updated; `sqlcl-conn-mng --version` prints `0.4.0` (REQ-6)
- **AC-10** - `make check`, `make unit` and `make integration` pass (REQ-7)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| src/sqlcl_conn_mng/properties.py | Update |
| src/sqlcl_conn_mng/store.py | Update |
| src/sqlcl_conn_mng/cli.py | Update |
| tests/test_properties.py | Update |
| tests/test_store.py | Update |
| tests/test_cli.py | Update |
| tests/integration/test_update_compat.py | Create |
| README.md | Update |
| .claude/skills/sqlcl-conn-mng/SKILL.md | Update |
| pyproject.toml | Update |
| uv.lock | Update |
| docs/tasks/update_connection/open_questions.md | Update |
