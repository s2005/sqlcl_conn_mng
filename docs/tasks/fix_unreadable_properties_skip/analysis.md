# Analysis: Skip Unreadable Connection Properties

## Goal

Keep read commands working when one `dbtools.properties` cannot be parsed, and point the user at the broken file (REQ-1 to REQ-4).

## Current Behavior

- `ConnectionStore.connections` (`src/sqlcl_conn_mng/store.py:160-186`) loops over `connections/<id>/` and calls `parse_properties(_read_text(props_file))` (`:173`) with no error handling.
- `_unescape` (`src/sqlcl_conn_mng/properties.py:51-54`) raises `ValueError("Malformed unicode escape in properties text: \\u<digits>")` for a `\u` not followed by four hex digits. The message carries neither the file nor the id.
- `_read_text` (`store.py:66-71`) falls back to Latin-1, so decoding never fails; only parsing can.
- `connections()` is the single read path behind `list`, `show`, `folders`, `export`, `get()` and every selector, plus clash checks in `add`, `update`, `copy` and `clone --user` (`src/sqlcl_conn_mng/cli.py:413`, `:417`, `:535`, `:620`, `:646`, `:659`, `:702`, `:751-752`, `:853`, `:876`, `:914`).
- `main` (`cli.py:1018-1021`) catches the `ValueError`, logs it and exits 1.

## Reproduction

Store built by SQLcl 25.4.1 (`connmgr import tests/integration/data/sqldev_export.json`, three connections `imp1`, `imp2`, `imp3`), then `name=` in `imp2`'s file replaced by `name=bad\u12zz`:

| Command | Result |
| ------- | ------ |
| `sqlcl-conn-mng list --format json` | `{"status": "error", "message": "Malformed unicode escape in properties text: \\u12zz"}`, exit 1; `imp1` and `imp3` not shown, broken id not named |
| SQLcl `connmgr list`, `connmgr show imp1`, `connmgr test imp1` | `Malformed \uxxxx encoding.` then `Exception in thread "main" java.lang.ExceptionInInitializerError at oracle.dbtools.plusplus.connections.db.NamedConnections.lookupConnectionIdentifier(NamedConnections.java:143)`; nothing works |

Unit-level reproduction without SQLcl (the escape is built with `chr(92)` so no shell layer alters it):

```bash
uv run python -c "import tempfile,pathlib; h=pathlib.Path(tempfile.mkdtemp()); [ (h/'connections'/i).mkdir(parents=True) for i in ('A'*22,'B'*22) ]; (h/'connections'/('A'*22)/'dbtools.properties').write_text('name=bad'+chr(92)+'u12zz'+chr(10)); (h/'connections'/('B'*22)/'dbtools.properties').write_text('name=good'+chr(10)); from sqlcl_conn_mng.cli import main; print('rc', main(['list','--home',str(h)]))"
```

Expected before the fix: the error line and `rc 1`. After: a warning naming `AAAAAAAAAAAAAAAAAAAAAA` and its path, a table holding `good`, `rc 0`.

## Feasibility

Small: one `try` around the parse in `connections()`, a module logger and a per-instance set of already-warned ids in `ConnectionStore`.

## Approach

In `connections()`, wrap `parse_properties(...)` in `try/except ValueError as exc`; on error, warn once (tracked in `self._skipped: set[str]`) and `continue`. Add `logger = logging.getLogger(__name__)` to `store.py`, the same pattern `cli.py` and `sqlcl.py` use.

| Advantages | Disadvantages |
| ---------- | ------------- |
| Every read command keeps working and the warning names the file to repair | A command can act without knowing the broken connection's name (see Risks) |
| Direct reads by id (`read_properties`, `check_rewritable`) are untouched, so a broken file is never rewritten (REQ-3) | -- |

Rejected alternative: fail fast with the file named (`open_questions.md` Q2).

## Implementation Notes

- Catch `ValueError` only (Q4). `UnicodeEncodeError` is a `ValueError` subclass but cannot come from parsing.
- Warning text includes `entry.name` (the id) and `props_file`; the log format already prefixes level and logger name.
- The skip set lives on the instance, so a new `ConnectionStore` (a new command) warns again.
- `folders` keeps showing the raw id for a connection id it cannot name (`_folder_dict` falls back to the id, `cli.py:604`); that is the useful output here.
- `export` omits the skipped connection; the warning on stderr says so.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A name clash check (`add`, `update --new-name`, `copy`) cannot see the broken connection's name | The name is unknowable while the file is unparseable; SQLcl crashes on such a store anyway, so SQLcl-backed commands fail before saving anything. README says to repair the file first |
| The warning is lost when stderr is discarded | Documented in README; exit code unchanged by design (Q3) |
| `export` output looks complete while one connection is missing | Warning on stderr names the file; README states it |

## Test Strategy

- Unit, `tests/test_store.py`: one bad file among good ones; result, single warning across repeated calls, direct reads still raise and leave bytes unchanged (REQ-1, REQ-3).
- Unit, `tests/test_cli.py`: `list --format json` valid JSON and exit 0, `folders` shows the bare id, `export` content (REQ-2).
- Manual: the SQLcl-built reproduction (AC-4).
