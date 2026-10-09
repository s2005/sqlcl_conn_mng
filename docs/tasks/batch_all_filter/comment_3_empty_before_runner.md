# P2 - Check for empty batches before resolving SQLcl

`move --filter` and `test --filter` with no match build the SQLcl runner first, so without SQLcl installed they report "SQLcl not found" instead of "No connections match" (`src/sqlcl_conn_mng/cli.py`, line 491).
