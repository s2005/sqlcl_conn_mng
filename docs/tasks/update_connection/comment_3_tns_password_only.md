# P2 - Resolve TNS targets for password-only updates

`src/sqlcl_conn_mng/cli.py` (PR #4 review, third round): an `ORACLE_TNS` connection stores its target in `tnsAlias`, so a password-only update reaches the connect step with an empty `connect_string` and fails instead of reusing the alias.
