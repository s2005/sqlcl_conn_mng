# P1 - Emit the save confirmation before attempting the move

In table mode `add --folder` printed `Connection NAME saved` before moving the connection; the refactor delays it until after the move, so a failing move leaves stdout empty although the connection was saved (src/sqlcl_conn_mng/cli.py:563). Codex rated it P2; numbered P1 here as the first review item.
