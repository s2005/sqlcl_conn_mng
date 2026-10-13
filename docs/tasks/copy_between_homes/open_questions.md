# Open Questions: Copy Saved Connections Between Homes

## Q1: How is a connection, with its saved password, carried to the other home?

- **Why it matters**: decides whether the command needs SQLcl, a reachable database, or any handling of the decoded password.
- **Options**:
  (a) Copy the connection directory byte for byte (`dbtools.properties` and `credentials.sso`) into `<to-home>/connections/<new id>/`. The wallet is treated as opaque bytes, never opened or decoded. `docs/tasks/sqlcl_jar_store_investigation/findings.md` ("Id Round Trip") proved that a copied wallet works under another id: SQLcl showed the password as saved and connected.
  (b) Run SQLcl `connmgr import` in the target home. It reads a SQL Developer export, which this tool does not produce, and it writes `ORACLE_BASIC` connections. Passwords need `-key`.
  (c) Decode the password in Python and run `connect -save` in the target home. This needs the database to be reachable and puts the cleartext password in process memory and on SQLcl stdin.
- **Recommended**: (a). There is no database contact and the password is never decoded. The approach is already proven against SQLcl 25.4.1. The README sentence "never reads or writes `credentials.sso`" is reworded to "never decodes or prints it; `copy` duplicates the file as opaque bytes".
- **Answer**: (a) - decided by user, 2026-10-13 ("with password without asking"); mechanism from findings.md "Id Round Trip".

## Q2: Which folder does the copy land in?

- **Why it matters**: the tool never writes `folders.json`, so placing the copy in a folder needs SQLcl `connmgr add -folder` and `connmgr move` in the target home.
- **Options**: (a) the same folder path as in the source, created in the target if missing (SQLcl); (b) always root `/`; (c) the source path by default, with an optional `--folder` override.
- **Recommended**: (a). The copy mirrors the source and no extra option is needed. A connection at `/` needs no SQLcl run, so copying to root works without SQLcl.
- **Answer**: (a) - decided by user, 2026-10-13.

## Q3: What happens when the target home already has a connection of the same name?

- **Why it matters**: SQLcl selects connections by name only, so two same-named connections in one store break every later command (see `_reject_duplicate_names`, `src/sqlcl_conn_mng/cli.py:330`).
- **Options**: (a) refuse that connection, compared case-insensitively like `update` does, report `[FAIL]` and go on with the batch; (b) add `--replace` to overwrite; (c) rename automatically to `<name>_1`.
- **Recommended**: (a). It is safe, and `--replace` can follow as its own task.
- **Answer**: (a) - decided by user, 2026-10-13.

## Q4: Is moving between homes part of this task?

- **Why it matters**: the name `move` is already taken by the folder move, and deleting from the source is destructive.
- **Options**: (a) copy only; (b) add `--delete-source` to `copy`.
- **Recommended**: (a). It keeps one destructive path (`delete`), which already has the `--yes` guard.
- **Answer**: (a) copy only - decided by user, 2026-10-13. The README and skill docs add no tip about combining `copy` with `delete` and do not mention any future cross-home move.

## Q5: Same home as source and target?

- **Why it matters**: a copy into the same home always collides on the name.
- **Options**: (a) refuse with exit code 1 before any write, when both resolve to the same directory; (b) let the per-name collision check reject each item.
- **Recommended**: (a), because the error is clearer.
- **Answer**: (a) - decided by reading `src/sqlcl_conn_mng/store.py:42` (`resolve_home` gives comparable paths) and `src/sqlcl_conn_mng/cli.py:575` (`update` reports an invalid option combination as `ValueError`, exit code 1).

## Q6: What if the target home does not exist yet?

- **Why it matters**: decides whether a fresh store can be seeded with `copy`.
- **Options**: (a) create `<to-home>/connections/` as needed; (b) refuse unless the directory exists.
- **Recommended**: (a). SQLcl itself creates a missing home on first use.
- **Answer**: (a) - decided by user, 2026-10-13.

## Q7: Does the copy keep the source connection id?

- **Why it matters**: ids are unique per store only. Reusing one can collide with an earlier copy that was renamed.
- **Options**: (a) generate a new id by the rule SQLcl accepts (22 URL-safe characters from 16 random bytes); (b) keep the source id.
- **Recommended**: (a). This matches `clone` and avoids id collisions.
- **Answer**: (a) - decided by reading findings.md "Id Round Trip" and `src/sqlcl_conn_mng/store.py:33`.

## Q8: Batch selection, output and exit codes

- **Why it matters**: the CLI should stay consistent with `move`, `test` and `delete`.
- **Options**: (a) exactly one of `--name`, `--filter` or `--all`; `[OK]`/`[FAIL]` per connection, a summary, `--format json` batch output, exit code 1 on any failure or no match; (b) single connection only.
- **Recommended**: (a).
- **Answer**: (a) - decided by user request and `_run_batch`, `src/sqlcl_conn_mng/cli.py:365`.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | REQ-2, REQ-6 |
| Q2 | Answered | REQ-3 |
| Q3 | Answered | REQ-4 |
| Q4 | Answered | Non-Requirements |
| Q5 | Answered | REQ-5 |
| Q6 | Answered | REQ-2 |
| Q7 | Answered | REQ-2 |
| Q8 | Answered | REQ-1, REQ-5 |
