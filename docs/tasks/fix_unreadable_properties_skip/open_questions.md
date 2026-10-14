# Open Questions: Skip Unreadable Connection Properties

## Q1: Is there a defect to fix at all?

- **Why it matters**: the task exists only if one bad `dbtools.properties` really hides the rest of a store, and only if the tool can do better than SQLcl.
- **Options**: (a) reproduce on a store built by SQLcl's own `connmgr import`, corrupt one file, compare SQLcl and the tool; (b) trust the unit-level probe.
- **Recommended**: (a).
- **Answer**: confirmed - with `name=bad\u12zz` in one of three imported connections, `sqlcl-conn-mng list` prints only `Malformed unicode escape in properties text: \u12zz` and exits 1; the other two connections are not shown and the message names neither the connection id nor the file. SQLcl 25.4.1 is worse: every `connmgr` command, including `show` of a healthy connection, dies with `Malformed \uxxxx encoding.` and `java.lang.ExceptionInInitializerError`. The tool is therefore the only way to locate the broken file, which today it cannot do. Evidence in `analysis.md` - decided by reproduction.

## Q2: Skip the entry or only name it in the error?

- **Why it matters**: skipping keeps read commands working; naming only keeps fail-fast.
- **Options**: (a) skip the entry and log a warning naming the id and file; (b) keep failing, but name the id and file in the error.
- **Recommended**: (a).
- **Answer**: (a) skip and warn with the path - decided by user (re-confirmed after the SQLcl evidence above).

## Q3: What exit code does a command return when it skipped an entry?

- **Why it matters**: scripts that run `list` or `export` branch on it.
- **Options**: (a) unchanged by the skip (0 for a successful `list`); (b) 1 whenever an entry was skipped.
- **Recommended**: (a) - a skip is a warning, not a failure of the command; making it 1 would recreate the defect for scripts, and the warning on stderr is what points the user at the file.
- **Answer**: (a) - follows from the user's choice of skip-and-warn in Q2.

## Q4: Which read errors count as "unreadable"?

- **Why it matters**: `parse_properties` raises `ValueError` for a malformed `\u` escape; reading the file can also raise `OSError` (permission denied).
- **Options**: (a) `ValueError` from parsing only; (b) `ValueError` and `OSError`.
- **Recommended**: (a) - only the parse error was reproduced; an `OSError` usually means the whole store is unreadable (permissions, a share gone), where failing the command is the right answer. `_read_text` already falls back to Latin-1, so a decoding error cannot occur.
- **Answer**: (a) - decided by reading `src/sqlcl_conn_mng/properties.py:54` and `src/sqlcl_conn_mng/store.py:66-71`.

## Q5: One warning per file per command, or per read?

- **Why it matters**: some commands read the store several times (`update` calls `connections()` up to three times, `src/sqlcl_conn_mng/cli.py:702`, `:751`, `:752`), so a naive warning repeats.
- **Options**: (a) warn once per connection id per `ConnectionStore` instance; (b) warn on every read.
- **Recommended**: (a) - one line per broken file is what the user needs.
- **Answer**: (a) - decided by reading the call sites above.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | Phase 1 |
| Q2 | Answered | REQ-1 |
| Q3 | Answered | REQ-2 |
| Q4 | Answered | REQ-1, Non-Requirements |
| Q5 | Answered | REQ-1 |
