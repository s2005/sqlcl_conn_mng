# P2 - Reject names SQLcl cannot address

`src/sqlcl_conn_mng/cli.py` (PR #4 review, fourth round): `--new-name` containing `/`, `#`, `\`, `'` or `?` is accepted by `validate_value`, and the metadata-only path writes it into `dbtools.properties`; SQLcl is said to forbid these characters in connection names.
