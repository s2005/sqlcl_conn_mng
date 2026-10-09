# Notes: Spec-To-Code Drift

## Drifts

### D1: SQLcl ignores `connectionString` for imported connections

- **Spec**: `PRD.md`, REQ-2 and AC-3 said a `--connect-string` change is written to `connectionString` and that real SQLcl `connmgr show` reports the new value.
- **Code**: `src/sqlcl_conn_mng/store.py`, `update_properties`, wrote only `name`, `userName` and `connectionString`.
- **Difference**: a connection imported from SQL Developer has type `ORACLE_BASIC` and the keys `host`, `port` and `serviceName` and no `connectionString` (`tests/integration/test_import_compat.py`, `EXTRA`). Observed with SQLcl 25.4.1 on such a connection updated to `--connect-string //badhost.invalid:1/nosvc`:
  - `connmgr show` still printed `localhost:1521/XEPDB1`;
  - `sql -name NAME` still connected to the real database.
  Name and user changes took effect. A connection saved by `connect -save` has type `ORACLE_DATABASE` and SQLcl reads its `connectionString`.
- **SQLcl's own behavior**: `connect -save NAME -replace` on the imported connection rewrote the file as `name`, `type=ORACLE_DATABASE`, `connectionString`, `userName`, with `host`, `port` and `serviceName` gone. So the password step already repairs this; only the metadata-only path is affected.

## Candidate solutions

### 01: Convert the file the way SQLcl does

- **Approach**: when a new `connectionString` is written to an `ORACLE_BASIC` file, rewrite the props as SQLcl does on a replace: `type=ORACLE_DATABASE`, `host`, `port` and `serviceName` dropped, key order `name`, `type`, `connectionString`, `userName`, other keys after. Refuse the change for any other type. Other changes (name, user) leave an `ORACLE_BASIC` file alone.
- **Scope of change**: `store.py`, tests, README, task documents.
- **Pros**: grounded in observed SQLcl output, no connect-string parser, handles descriptors, the result is a file SQLcl itself writes.
- **Cons**: the update changes `type` and removes three keys, which widens REQ-2 beyond three values for this one case.
- **Risk**: low; SQLcl reads its own form (integration test).

### 02: Document the limit, keep the code

- **Approach**: state in README that `--connect-string` has no effect on imported connections.
- **Scope of change**: README only.
- **Pros**: no new write behavior.
- **Cons**: a command that reports success and changes nothing SQLcl uses; not accepted as a fix.
- **Risk**: low for the code, high for users.

### 03: Rewrite `host`, `port`, `serviceName` from the new connect string

- **Approach**: parse the connect string and write the three keys.
- **Scope of change**: connect-string parser, writer, tests.
- **Pros**: keeps the connection `ORACLE_BASIC`.
- **Cons**: a descriptor or an alias cannot be mapped to host, port and service; a parser to maintain.
- **Risk**: medium.

### 04: Refuse `--connect-string` for non-`ORACLE_DATABASE` types

- **Approach**: raise an error for imported connections.
- **Scope of change**: `cli.py`, tests, README.
- **Pros**: no silent no-op.
- **Cons**: the user cannot do what they asked, although SQLcl itself converts such a connection.
- **Risk**: low.
