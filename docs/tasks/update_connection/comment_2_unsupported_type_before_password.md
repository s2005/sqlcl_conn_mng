# P2 - Validate unsupported types before replacing credentials

`src/sqlcl_conn_mng/cli.py` (PR #4 review, second round): `--connect-string` combined with a password source on an `ORACLE_TNS` or other unsupported connection type is checked only for the string itself; the type guard in `ConnectionStore.update_properties` runs after `save_connection`, so the password is replaced and the file write is then refused.
