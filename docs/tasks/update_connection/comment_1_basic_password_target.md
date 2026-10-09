# P1 - Derive the current target for imported connections

`src/sqlcl_conn_mng/cli.py:563` (PR #4 review): a password-only update (`--password-env` or `--prompt-password` without `--connect-string`) on an imported `ORACLE_BASIC` connection passes an empty connect string to `save_connection`, because the target is stored in `host`, `port` and `serviceName`; `validate_value` then fails and such connections cannot get a password update.
