# P2 - Keep duplicate records available to plain show

The duplicate-name guard also makes metadata-only `show --all` and `show --filter` exit 1, although plain `show` reads files only and could render both records; the rejection should apply only to name-based SQLcl operations (`src/sqlcl_conn_mng/cli.py`, line 293).
