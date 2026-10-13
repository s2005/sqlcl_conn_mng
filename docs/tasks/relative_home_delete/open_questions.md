# Open Questions: Relative --home Breaks delete and delete-folder

## Probe Result

Probe run with SQLcl 25.4.1 on a store built from `tests/integration/data/sqldev_export.json`, once with a relative `--home st`, once with a nested relative `--home a/st`, once with an absolute path. No database is needed.

| Command | Relative `--home` | Absolute `--home` |
| ------- | ----------------- | ----------------- |
| `add-folder` | ok | ok |
| `rename` | ok | ok |
| `move` | ok | ok |
| `clone` | ok | ok |
| `show` | ok | ok |
| `delete` | exit 1, `SEVERE ... validatePermissions Error checking file permissions for st\connections\st\connections\<id>`, connection kept | ok |
| `delete-folder --force` | exit 1, same SEVERE, folder and connection kept | ok |

Earlier in the session `add`, `update --password-env` and `test` also worked with the relative `.sqlcl`. SQLcl joins the relative `-home` onto itself only on its delete path. The tool reports the failure (exit 1); it does not report false success.

## Q1: Where is the store path made absolute?

- **Why it matters**: decides which code paths are covered and whether any printed path changes.
- **Options**: (a) in `SqlclRunner.__init__` (`src/sqlcl_conn_mng/sqlcl.py:98`), so every SQLcl call gets an absolute `-home`, including the `copy` target runner (`src/sqlcl_conn_mng/cli.py:822`); (b) in `resolve_home` (`src/sqlcl_conn_mng/store.py:46`), which also changes the path held by `ConnectionStore` and does not cover `copy --to-home`; (c) in both.
- **Recommended**: (a) - one place, covers every runner, and the `copy` message (`cli.py:840`) keeps printing the path as the user typed it.
- **Answer**: (a) in `SqlclRunner.__init__` - decided by user.

## Q2: abspath or resolve?

- **Why it matters**: `Path.resolve()` follows symlinks and Windows junctions, so SQLcl would see a different path than the user gave; `os.path.abspath` only joins with the current directory and normalises `..`.
- **Options**: (a) `os.path.abspath`; (b) `Path.resolve()`.
- **Recommended**: (a) - fixes the defect without changing which path SQLcl sees for an already absolute store.
- **Answer**: (a) `os.path.abspath` - decided by user.

## Q3: Which tests prove the fix?

- **Why it matters**: the integration tests build stores under absolute temp paths, so none of them can see this defect today.
- **Options**: (a) unit test that `SqlclRunner.argv()` carries an absolute `-home` for a relative input, plus integration tests that run `delete` and `delete-folder --force` with a relative `--home` (cwd set to the store's parent); (b) unit test only; (c) integration tests only.
- **Recommended**: (a) - the unit test pins the mechanism, the integration tests pin the SQLcl behaviour that motivated it.
- **Answer**: (a) unit test plus integration tests for `delete` and `delete-folder --force` with a relative `--home` - decided by user.

## Q4: Version bump?

- **Why it matters**: the project rule makes a bump mandatory only when input parameters change; this fix changes none.
- **Options**: (a) patch bump in `pyproject.toml` plus `uv lock`; (b) no bump in this task.
- **Recommended**: (a) - user-visible bug fix, and it marks which installed copies have it.
- **Answer**: (a) patch bump, but from the current version: `main` is at 0.7.0 (`pyproject.toml:7`, `origin/main` at `dbb9d73`), so the bump is 0.7.0 -> 0.7.1 - decided by user, version read from `pyproject.toml`.

## Q5: README change?

- **Why it matters**: `README.md:142` says `--home` is "passed to SQLcl as `-home`"; after the fix the tool passes the absolute form.
- **Options**: (a) amend that row to say the path is made absolute before it is passed to SQLcl; (b) no doc change.
- **Recommended**: (a) - one sentence, keeps the reference accurate.
- **Answer**: (a) amend the `--home` row - decided by user.

## Q6: Report the SQLcl defect upstream or open a GitHub issue here?

- **Why it matters**: the root cause is in SQLcl; the tool only works around it.
- **Options**: (a) out of scope for this task, listed under Non-Requirements; (b) open a GitHub issue in this repo as part of the task.
- **Recommended**: (a) - the task fixes the tool; tracking is a separate decision.
- **Answer**: (a) out of scope, listed under Non-Requirements - decided by user.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | REQ-1 |
| Q2 | Answered | REQ-1 |
| Q3 | Answered | REQ-3 |
| Q4 | Answered | REQ-4 |
| Q5 | Answered | REQ-5 |
| Q6 | Answered | Non-Requirements |
