# P2 - Report the persisted save when a JSON folder move fails

With `add --format json --folder` a failing `move_connection` leaves the connection saved but stdout holds only a generic error object, so automation may retry the add (src/sqlcl_conn_mng/cli.py:564).
