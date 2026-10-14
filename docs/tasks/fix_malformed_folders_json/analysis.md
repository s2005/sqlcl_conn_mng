# Analysis: Fix Malformed folders.json Crash

## Goal

Replace the uncaught `TypeError` on a non-list `folders` or `connections` value with the store's existing `Malformed folders.json` error (REQ-1, REQ-2).

## Current Behavior

- `ConnectionStore.folders` (`src/sqlcl_conn_mng/store.py:139-150`) parses the file, raises `StoreError` for invalid JSON (`:146-147`) and for a non-object top level (`:148-149`), then iterates `data.get("folders", [])`.
- `_build_folder` (`store.py:74-80`) checks that a node is a dict with a string `name`, then iterates `node.get("connections", [])` and `node.get("folders", [])` without a type check.
- `get(key, [])` returns `None` when the key is present with `null`, so the loop raises `TypeError: 'NoneType' object is not iterable`. A number or boolean raises `TypeError` the same way. A string is iterated per character: under `folders` each character fails the dict check and gives a misleading `folder entry without a name`; under `connections` every character is a `str` and becomes a bogus connection id.
- `main` (`src/sqlcl_conn_mng/cli.py:1016-1025`) does not catch `TypeError`, so the traceback reaches the user.
- `folders()` is reached by `connections()` through `folder_paths()` (`store.py:152-158`), so the crash hits `list`, `show`, `folders`, `export`, `update`, `add`, `clone --user` and every selector, plus `copy` on the target store (`cli.py:822`, `:853`).

## Reproduction

Run against a store built by SQLcl 25.4.1 itself (`connmgr import tests/integration/data/sqldev_export.json`, `connmgr add -folder /dev`, `connmgr move -conn imp1 /dev`), then edit `connection_folders/folders.json`:

| Mutation | SQLcl `connmgr list` | SQLcl `connmgr show imp2` | `sqlcl-conn-mng list` |
| -------- | -------------------- | ------------------------- | --------------------- |
| none (baseline) | tree printed | details printed | connections listed |
| folder `connections: null` | `Cannot invoke "java.util.List.stream()" because "this.connections" is null` | details printed | `TypeError` traceback |
| folder `folders: null` | `... because "this.folders" is null` | details printed | `TypeError` traceback |
| top-level `folders: null` | `... because "this.folders" is null` | details printed | `TypeError` traceback |

SQLcl treats the file as broken too (its `list` fails), so the tool reporting an error is consistent with SQLcl; only the traceback is the defect.

Unit-level reproduction without SQLcl. The store needs one connection directory: `connections()` returns early, before reading `folders.json`, when `connections/` is absent.

```bash
uv run python -c "import json,tempfile,pathlib; h=pathlib.Path(tempfile.mkdtemp()); c=h/'connections'/('A'*22); c.mkdir(parents=True); (c/'dbtools.properties').write_text('name=good'+chr(10)); (h/'connection_folders').mkdir(); (h/'connection_folders/folders.json').write_text(json.dumps({'folders':[{'name':'dev','connections':None}]})); from sqlcl_conn_mng.cli import main; main(['list','--home',str(h)])"
```

Expected before the fix: `TypeError` traceback. After: one `[ERROR]` log line, exit code 1.

## Feasibility

Small and local: one helper in `store.py` and two call sites. No SQLcl interaction changes.

## Approach

Add a private helper in `store.py`, for example `_list_value(node, key, where)`, that returns `node.get(key, [])` when it is a list and raises `StoreError(f"Malformed folders.json: {key!r} of {where} is not a list")` otherwise. Use it in `folders()` for the top level (`where` = `the top level`) and in `_build_folder` for `connections` and `folders` (`where` = the folder path being built).

| Advantages | Disadvantages |
| ---------- | ------------- |
| One rule for every non-list type, same error class as invalid JSON | Every command fails on such a store, while SQLcl's `show` still works |
| The message points at the exact key and folder to repair | -- |

Rejected alternative: treat `null` as `[]` (see `open_questions.md` Q2).

## Implementation Notes

- Keep the absent-key default (`[]`) unchanged (REQ-1).
- Keep skipping non-string entries inside a valid `connections` list; that is existing, tested behaviour.
- The folder path in the message is the one `_build_folder` computes, so a nested folder reads `/dev/local`.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A store SQLcl writes with `null` in normal operation becomes unreadable | SQLcl 25.4.1 writes `[]` for empty lists (`{"folders":[{"name":"dev","connections":[],"folders":[]}]}` observed after `connmgr add -folder`), and its own `list` fails on `null` |
| A string `connections` value was silently read as character ids before and now fails | Intended: those ids never matched a connection |

## Test Strategy

- Unit, `tests/test_store.py`: parametrized over key, nesting level and value (`None`, `5`, `True`, `"x"`); assert `StoreError` and message content (REQ-1). Existing `test_malformed_folders_json` and absent-key tests stay green.
- Unit, `tests/test_cli.py`: `main` on a `null` store returns 1, JSON error object under `--format json` (REQ-2).
- Manual: the SQLcl-built reproduction above (AC-4).
