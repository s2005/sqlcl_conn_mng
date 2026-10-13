# Analysis: Relative --home Breaks delete and delete-folder

## Goal

Pass SQLcl an absolute `-home` on every call so that `delete` and `delete-folder --force` work with a relative store path (REQ-1, REQ-2), with tests that would have caught the defect (REQ-3).

## Current Behavior

- `resolve_home` (`src/sqlcl_conn_mng/store.py:46`) returns `Path(option).expanduser()` for `--home`, `Path(env).expanduser()` for `SQLCL_CONN_HOME`, and `Path.cwd() / ".sqlcl"` otherwise. Only the last form is absolute.
- `_runner` (`src/sqlcl_conn_mng/cli.py:385`) builds `SqlclRunner(..., str(resolve_home(args.home)), ...)`. The `copy` target runner (`cli.py:822`) passes `str(to_home)`, where `to_home = Path(args.to_home).expanduser()` (`cli.py:806`).
- `SqlclRunner.__init__` (`src/sqlcl_conn_mng/sqlcl.py:98`) stores the path as given, and `argv()` (`sqlcl.py:110`) passes it after `-home` (`sqlcl.py:115`).
- `delete_connection` (`sqlcl.py:161`) runs `connmgr delete -conn`, and `delete_folder` (`sqlcl.py:153`) runs `connmgr delete -folder` with `-force` when asked.
- With a relative `-home`, SQLcl 25.4.1 builds the wallet path as `<home>\connections\<home>\connections\<id>` on the delete path only, logs `SEVERE ... validatePermissions`, and does not delete. The tool's `_expect` does not find `has been deleted` and exits 1. The probe table is in `open_questions.md`.
- Coverage gap: every integration test passes an absolute temp path through `harness.run_cli` (`tests/integration/harness.py:303`), so the relative case is never exercised. `test_argv_thin_and_thick` (`tests/test_sqlcl.py:26`) pins the relative string `store-home` in `argv()`.

## Feasibility

Straightforward. One line in `SqlclRunner.__init__` fixes every SQLcl call. The integration harness runs the CLI in process, so a test can `monkeypatch.chdir` to the store's parent and pass the store's bare name as `--home`.

## Approach

Make the path absolute in `SqlclRunner.__init__` with `os.path.abspath` (Q1, Q2).

| Advantages | Disadvantages |
| ---------- | ------------- |
| One place covers `_runner` and the `copy` target runner | `argv()` no longer echoes the input string, so one existing unit test changes |
| `ConnectionStore` and every printed or JSON path stay as typed | The relative path is resolved against the current directory at runner construction, not at each call |
| `abspath` does not follow symlinks or junctions, so an absolute store path reaches SQLcl as given | |

Rejected: fixing `resolve_home` instead. It does not cover `copy --to-home`, and it changes the path held by `ConnectionStore`, which reaches messages.

## Implementation Notes

- `self.home = os.path.abspath(home)`. The constructor signature stays `home: str`.
- The process does not change directory between building a runner and running SQLcl, so resolving at construction is equivalent to resolving at each call.
- `~` is already expanded by `resolve_home` and by the `copy` code before the runner sees the path.
- Existing absolute paths pass through `abspath` unchanged apart from separator and `..` normalisation; on Windows `abspath` turns `/` into `\`, which SQLcl accepts (the absolute probe used a backslash path).
- Version: `pyproject.toml` is at 0.7.0 on `main` (`dbb9d73`); the bump is 0.7.1 (REQ-4).
- README `--home` row is `README.md:142` (REQ-5).

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A test somewhere asserts the raw `-home` string | `test_argv_thin_and_thick` is the only one found; it is updated in Phase 1. `make unit` catches others |
| The relative-path integration tests leak a changed current directory into later tests | Use `monkeypatch.chdir`, which pytest restores after each test |
| SQLcl fails on another command with a relative path that the probe did not cover | The fix makes every call absolute, so it does not depend on the probe being complete |

## Test Strategy

- Unit (`tests/test_sqlcl.py`): relative home becomes `os.path.abspath(...)` in `argv()`; absolute home is kept; update `test_argv_thin_and_thick` (REQ-1, REQ-3).
- Integration (`tests/integration/test_connection_ops_compat.py`): `delete` with a relative `--home` on a copy of `conn_ops_store` (REQ-2, REQ-3).
- Integration (`tests/integration/test_folders_compat.py`): `delete-folder --force` with a relative `--home` on a copy of `folder_store`, with the same assertions as `test_tool_force_delete_folder` (REQ-2, REQ-3).
- Both integration tests fail on the current code: the probe reproduced exit 1 for both commands.
