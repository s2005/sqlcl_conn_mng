# PRD: Relative --home Breaks delete and delete-folder

## Objective

Make `delete` and `delete-folder --force` work when `--home` (or `SQLCL_CONN_HOME`) is a relative path, by passing SQLcl an absolute `-home` on every call.

## Background

`AGENTS.md` and `README.md` tell users to run the tool from `<repo-root>` with `--home .sqlcl`. With that relative path, SQLcl 25.4.1 fails on its delete path: it looks for the wallet under the doubled path `<home>\connections\<home>\connections\<id>`, logs `SEVERE ... validatePermissions Error checking file permissions`, and keeps the connection. The tool exits 1, so nothing reports false success, but the delete does not happen.

A probe on a store built from the import fixture showed the failure on `delete` and on `delete-folder --force`. `add-folder`, `rename`, `move`, `clone` and `show` worked with the same relative path, and so did `add`, `update` and `test`. With an absolute path every command worked. See `open_questions.md` for the probe table.

`SqlclRunner` (`src/sqlcl_conn_mng/sqlcl.py:98`) passes the path to SQLcl exactly as `resolve_home` returns it, so a relative `--home` reaches SQLcl as a relative `-home`. The integration tests build stores under absolute temp paths, so none of them can see the defect.

## Requirements

### REQ-1: SQLcl always gets an absolute -home

`SqlclRunner` stores `os.path.abspath(home)` and `argv()` passes that value after `-home`. This covers every runner, including the `copy` target runner (`src/sqlcl_conn_mng/cli.py:822`). An already absolute path is passed unchanged apart from normalisation. Symlinks and junctions are not resolved. `resolve_home` and `ConnectionStore` are not changed, so messages that print the store path, such as the `copy` result (`cli.py:840`), keep printing it as the user typed it.

### REQ-2: delete and delete-folder --force work with a relative store path

With the current directory set to the store's parent and `--home` given as a relative path:

- `delete --name <n> --yes` exits 0, prints `Connection <n> has been deleted`, and the connection is gone from `list`.
- `delete-folder --folder <f> --force --yes` on a folder that holds a connection exits 0, and the folder and its connection are gone.
- Neither command prints a `SEVERE` line.

### REQ-3: Tests pin the fix

- Unit test in `tests/test_sqlcl.py`: a runner built with a relative home puts the absolute form in `argv()`, and one built with an absolute home keeps it.
- The existing `test_argv_thin_and_thick` is updated to expect the absolute form of `store-home`.
- Integration tests run `delete` and `delete-folder --force` against a store copy with a relative `--home`, the current directory set with `monkeypatch.chdir`, and assert REQ-2.

### REQ-4: Patch version bump

`pyproject.toml` goes from 0.7.0 to 0.7.1 and `uv.lock` is refreshed with `uv lock`.

### REQ-5: README states that the store path is made absolute

The `--home` row of the global options table (`README.md:142`) says the path is made absolute before it is passed to SQLcl as `-home`.

## Non-Requirements

- Reporting the SQLcl defect to Oracle, or opening a GitHub issue in this repo for it (Q6).
- Changing `resolve_home`, `ConnectionStore`, or any printed or JSON path.
- Resolving symlinks or junctions in the store path.
- The `clone --user` password problem tracked in GitHub issue #11.
- Any change to the `.sqlcl` path convention in `AGENTS.md`.

## Acceptance Criteria

- **AC-1** - `SqlclRunner(..., "store-home", ...).argv()` contains `os.path.abspath("store-home")` after `-home`, and an absolute home is passed unchanged. (REQ-1, REQ-3)
- **AC-2** - With a relative `--home`, `delete --name <n> --yes` exits 0, the connection is gone from `list`, and the output has no `SEVERE` line. (REQ-2, REQ-3)
- **AC-3** - With a relative `--home`, `delete-folder --folder <f> --force --yes` exits 0, and the folder and the connection it held are gone. (REQ-2, REQ-3)
- **AC-4** - The `copy` result message still prints `--to-home` as given; the existing `copy` unit and integration tests pass unchanged. (REQ-1)
- **AC-5** - `uv run sqlcl-conn-mng --version` prints 0.7.1. (REQ-4)
- **AC-6** - The README `--home` row says the path is made absolute before it is passed to SQLcl. (REQ-5)
- **AC-7** - `make check`, `make unit` and `make integration` pass. (REQ-1, REQ-2, REQ-3)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| `src/sqlcl_conn_mng/sqlcl.py` | Update |
| `tests/test_sqlcl.py` | Update |
| `tests/integration/test_connection_ops_compat.py` | Update |
| `tests/integration/test_folders_compat.py` | Update |
| `pyproject.toml` | Update |
| `uv.lock` | Update |
| `README.md` | Update |
