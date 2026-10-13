# PRD: Descriptor connect string quoting

## Objective

Make `add` and `update` save a connection whose connect string is not a plain safe token, such as a TNS descriptor or an easy-connect string with `?` parameters. Today SQLcl answers "Connection failed" for all of them.

## Background

`save_connection` builds `connect -save ... <user>@<connect>` and passes the whole target through `quote_arg`, which wraps it in double quotes when it holds any character outside a small safe set. A live probe against Oracle XE in podman with SQLcl 25.4.1 showed that SQLcl rejects a double-quoted `user@connect` target for every connect string and accepts `user@"<connect>"`. See `open_questions.md` (Q1, Q2) for the probe results.

## Requirements

### REQ-1: Quote only the connect part

`save_connection` emits `<user>@<connect>` unquoted when the connect string is a safe token, and `<user>@"<connect>"` otherwise. The user part keeps `quote_arg` quoting. Values with a double quote, newline or carriage return stay rejected.

### REQ-2: `add` accepts descriptor and parameter connect strings

`add --connect-string` with a TNS descriptor and with `//host:port/service?connect_timeout=5` saves the connection and the saved connection connects.

### REQ-3: `update --connect-string` accepts such connect strings

`update --connect-string` with a descriptor, together with a password step, saves the connection and keeps its id.

### REQ-4: `update --password-env` works on stored descriptors

`update --password-env` on a connection whose stored connect string is a descriptor, or an easy-connect string with `?` parameters, replaces the password and keeps the id.

### REQ-5: Unit tests of the command text

`tests/test_sqlcl.py` asserts the exact `connect` command for a safe connect string, a descriptor and a `?` parameter string.

### REQ-6: Version bump

The project version moves from 0.9.0 to 0.9.1.

## Non-Requirements

- No new or changed command-line option.
- `tests/integration/harness.py` keeps its own descriptor quoting; it is the independent reference for what SQLcl accepts.
- Quoting of names, folders and passwords is unchanged.

## Acceptance Criteria

- **AC-1** - the unit tests show `user@//h/s` unquoted and `user@"<connect>"` for a descriptor and for a `?` parameter string (REQ-1, REQ-5)
- **AC-2** - the former strict xfail `test_tool_add_with_descriptor` passes without its marker, and a `?` parameter case passes (REQ-2)
- **AC-3** - an integration test updates a connect string to a descriptor and the connection is read back by SQLcl (REQ-3)
- **AC-4** - an integration test runs `update --password-env` on stored descriptor and `?` parameter connections, and the ids stay (REQ-4)
- **AC-5** - `uv run sqlcl-conn-mng --version` prints 0.9.1 (REQ-6)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| src/sqlcl_conn_mng/sqlcl.py | Update |
| tests/test_sqlcl.py | Update |
| tests/integration/test_saved_password_compat.py | Update |
| tests/integration/test_update_compat.py | Update |
| pyproject.toml, uv.lock | Update |
