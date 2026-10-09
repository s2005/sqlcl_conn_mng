# P1 - Preserve connection identity when selecting duplicate names

Batch selection reduces the matched connections to names, but a store built with SQLcl `import -duplicates REPLACE` can hold several connections with the same name and different IDs, so batch `show` repeats the first one and batch `move`, `test` and `delete` send the same ambiguous name repeatedly (`src/sqlcl_conn_mng/cli.py`, line 290, `_select_names`).
