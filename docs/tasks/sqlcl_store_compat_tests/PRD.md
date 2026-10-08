# PRD: Integration Tests for Compatibility with SQLcl-Made Store Entries

## Objective

Add integration tests that create saved-connection store entries with real SQLcl 25.4.1 and prove that `sqlcl-conn-mng` reads them, reports them and operates on them correctly, and that SQLcl still writes the on-disk format recorded in `docs/tasks/sqlcl_jar_store_investigation/findings.md`. Run them, together with the lint, type and unit checks, both locally and in GitHub Actions on Ubuntu and Windows, through one `Makefile` that defines every command once.

## Background

`sqlcl-conn-mng` reads the store in Python and runs SQLcl for every write. Its unit tests use hand-written fake stores (`tests/conftest.py`), so nothing checks that the read path matches what SQLcl actually writes. The one integration test, `tests/test_integration.py`, covers a single folder add and delete.

The investigation task `sqlcl_jar_store_investigation` recorded what SQLcl writes for every operation, with expected files, keys, escaping and folder layout, but its probes ran in a scratch directory and none of them is a repeatable test. The follow-up task `sqlcl_free_catalog_writes` will write the same format from Python and needs a regression baseline taken from SQLcl itself.

The repository has no CI: every check runs only on a developer machine, and the commands are listed by hand in `README.md`, "Development". Running the new tests in GitHub Actions without copying those commands, the SQLcl release and the database settings into the workflow needs one shared entry point.

Decisions behind this PRD are recorded in `open_questions.md`.

## Requirements

### REQ-1: Integration harness

A `tests/integration/` package, selected by the existing `integration` marker, that provides:

- SQLcl discovery from `SQLCL_BIN`, then `sql` on `PATH`; every test in the package skips with a stated reason when no executable resolves.
- The SQLcl release, read from `version.txt` in the executable's directory, available to failure messages.
- A scenario store builder that runs one SQLcl process per store against a `tmp_path` store with `-home`, feeds a multi-command script on stdin, and fails the fixture unless each command's expected success line appears in the output.
- An in-process runner for the tool's CLI (`sqlcl_conn_mng.cli.main`) that always passes `--home <scenario store>` and returns the exit code and captured stdout and stderr.
- File-set snapshots taken with `take_snapshot` from `scripts/store_probe.py`, so a test can compare the files an operation created, changed and deleted without reading wallet bytes.
- Database settings read from `SQLCL_ITEST_CONNECT`, `SQLCL_ITEST_USER` and `SQLCL_ITEST_PASSWORD`; a test that needs a database skips when any of them is unset.
- A committed SQL Developer export fixture that `connmgr import` accepts, found by the discovery step in Phase 1 (`open_questions.md`, Q11).

### REQ-2: Folder compatibility

For a folder tree built by SQLcl with `connmgr add -folder` (nested, with missing parents), `rename -folder`, `move -folder`, `delete -folder` and `delete -folder -force`, and with connections placed by `move -conn`:

- `sqlcl-conn-mng folders --format json` reports the same tree, and `list --folder <path> --format json` returns exactly the connections SQLcl placed in that folder or below it.
- A connection SQLcl moved back to `/` is reported at `/`.
- After the last folder is deleted, the tool reports no folders.
- The tool's own `add-folder`, `delete-folder` (with and without `--force --yes`) and `move` commands work on a SQLcl-built tree, and the tool's view matches the tree afterwards.

### REQ-3: Import compatibility

For connections created by `connmgr import` of the fixture from REQ-1, including the `-duplicates RENAME` and `-duplicates REPLACE` variants:

- `list` and `export` report each imported connection with `type` `ORACLE_BASIC`, its `name`, `user_name`, and `host`, `port` and `serviceName` in `extra`, so no imported value is lost.
- `RENAME` produces `<name>_1`, and `REPLACE` produces a second connection with the same name and a different id; `list` reports both.
- `wallet_present` is true and `show --check-password` reports no saved password.

How the tool should present the connect string of an `ORACLE_BASIC` connection is not decided; it is recorded as a follow-up, not asserted (`open_questions.md`, Q6).

### REQ-4: Connection operation compatibility

For connections SQLcl created, then cloned (plain, `-username`, `-nopwd`), renamed, moved and deleted:

- `rename` keeps the id, and the tool reports the new name; `move` keeps the id, and the tool reports the new folder; `clone` gets a new id at `/` even when the original is in a folder; `delete` removes the connection and its folder references from the tool's view.
- The tool's own `rename`, `move`, `clone` and `delete --yes` commands work on SQLcl-made connections, and their results match the SQLcl-made equivalents above.
- Name lookup by the tool is case-sensitive: with `c1` and `C1` both saved, `show --name c1` and `show --name C1` return different ids.

### REQ-5: Edge-case values

SQLcl-made connections and folders carrying the values `findings.md` proved SQLcl accepts are reported by the tool with exactly those values:

- names with a leading space, inner spaces, and the characters `:` `=` `!` `.` `-` `_` `@` `(` `)` `,` `;` `$` `*` `+` `<` `>` `|` `[` `]` `{` `}` `%` `~` `^`;
- the user `u:s=e#r!\x y`;
- non-ASCII names such as `café1` and `über1`;
- folder names `back\slash` and `lt<gt>`, and folders `/dev` and `/DEV` side by side.

A value that SQLcl stores wrongly because of the tool's stdin encoding is committed as a strict `xfail` citing `sqlcl_stdin_encoding`, limited to the platform where it fails (`condition=sys.platform == "win32"`), so the same test passes on Linux (`open_questions.md`, Q12).

### REQ-6: Saved connections against a live database

With the database settings from REQ-1 set:

- `connect -save -savepwd` and `connect -save` without `-savepwd` produce connections the tool reports with the given name, connect string and user at `/`; `show --check-password` reports the password as saved and not saved respectively, and SQLcl's own `connmgr show` agrees.
- `connect -save -replace` keeps the id and switches the saved-password state both ways.
- `clone` of a password connection keeps the password; `clone -username` and `clone -nopwd` drop it.
- A connection saved with a descriptor connect string `(DESCRIPTION=...)` is reported with that exact string.
- The tool's `test` command succeeds on a connection saved with a password.

### REQ-7: Format conformance

For entries SQLcl wrote in the scenarios above, assert the format in `findings.md`:

- The connection id is 22 characters of URL-safe Base64 without padding and decodes to exactly 16 bytes.
- Each operation creates, changes and deletes the files listed in `findings.md`, "Effects per Operation"; for `credentials.sso` only presence and whether its hash changed are compared.
- `dbtools.properties` has no header or comment line, `key=value` lines, LF endings, a final LF and raw UTF-8, uses the escaping rules recorded there, and has the key order recorded for new and rewritten files.
- `folders.json` is compact UTF-8 JSON with no final newline; every folder object has `name`, `connections` and `folders` in that order; siblings are sorted by UTF-16 code units; moved ids are appended; deleting the last folder leaves `{"folders":[]}`.
- Every format assertion message names the SQLcl release from REQ-1, so a failure after an upgrade reads as format drift.

### REQ-8: Secret and store hygiene

- The tests use only `tmp_path` stores passed with `-home`; they never read or write `<repo-root>/.sqlcl` or `<home>/.sqlcl`.
- The database password reaches SQLcl only on stdin; it never appears in argv, logs, assertion messages or committed files.
- Every database test asserts that the password does not occur in the tool's stdout, stderr or export file.
- No test reads, prints or compares `credentials.sso` content beyond presence and a hash comparison.

### REQ-9: Documentation

`README.md`, "Development" and "Testing", document the `make` targets from REQ-10 as the way to run every check, the three `SQLCL_ITEST_*` variables, `make db-start` / `make db-stop` for the test database, the GitHub Actions workflow from REQ-11 and what each runner covers, and that `SQLCL_BIN` must name `sql.exe` on Windows. The README lists target names, not the commands behind them.

### REQ-10: Single entry point in a `Makefile`

A `Makefile` at the repository root is the only place that defines the commands for checks, tests, SQLcl and the test database (`open_questions.md`, Q13, Q14):

- `check`: `ruff check`, `ruff format --check` and `mypy`, through `uv run`.
- `unit`: the default `pytest` run.
- `integration`: `pytest -m integration`.
- `PYTEST_ARGS`: appended to both test targets, so one file or one test can be selected without a second command line.
- `print-sqlcl-version`: prints `SQLCL_VERSION`, so the workflow's cache key reads the version instead of repeating it.
- `sqlcl`: download `sqlcl-$(SQLCL_VERSION).zip` from Oracle into `.cache/sqlcl/` and unpack it with Python's `zipfile`, skipping both when the version is already unpacked; `SQLCL_VERSION` defaults to `25.4.1.022.0618`.
- `db-start`: start `gvenzl/oracle-xe:21-slim` as container `sqlcl-itest-xe` with `$(ENGINE)` (default `podman`, `ENGINE=docker` as fallback), create the user from `SQLCL_ITEST_USER` with the password from `SQLCL_ITEST_PASSWORD`, publish port `1521`, and wait until the database accepts connections; refuse to run when `SQLCL_ITEST_PASSWORD` is unset.
- `db-stop`: remove the container.
- Defaults `SQLCL_ITEST_USER ?= itest` and `SQLCL_ITEST_CONNECT ?= //localhost:$(DB_PORT)/XEPDB1`, exported to every recipe, so the user, port and service are defined once; only `SQLCL_ITEST_PASSWORD` has no default, and leaving it unset keeps the database scenarios skipped.
- `SHELL := bash`, so recipes behave the same under Git Bash on Windows and on Linux.
- Recipes pass the password to the container by variable name (`-e APP_USER_PASSWORD`) and never as a make variable, so make never echoes it.

### REQ-11: GitHub Actions workflow

`.github/workflows/ci.yml` runs on `pull_request`, on `push` to `main` and on `workflow_dispatch` (`open_questions.md`, Q12, Q15, Q16):

- A matrix of `ubuntu-latest` and `windows-latest`. Each job sets up `uv`, Python 3.13 and Java 17 (Temurin), installs `make` with Chocolatey on Windows, restores the `.cache/sqlcl/` cache keyed by `SQLCL_VERSION`, and calls only `make` targets: `check`, `unit`, `sqlcl`, `integration`.
- On Ubuntu only: generate a random `SQLCL_ITEST_PASSWORD` per run with Python `secrets`, mask it with `::add-mask::` before it is written to `GITHUB_ENV`, run `make db-start` before `make integration`, and `make db-stop` in an `always()` step. User and connect string come from the `Makefile` defaults.
- On Windows the database variables stay unset, so the database scenarios skip with a reason.
- No command line, SQLcl version, image name or container setting is repeated in the workflow; the workflow only selects targets and sets variables.
- No repository secret is needed.

## Non-Requirements

- No Python store writer and no tests of entries written by `sqlcl-conn-mng` in Python and read by SQLcl; that direction belongs to `sqlcl_free_catalog_writes`, which can reuse this harness (`open_questions.md`, Q1).
- No change to `src/`. A defect the tests expose is committed as a strict `xfail` with its follow-up task (`open_questions.md`, Q6).
- No Python wallet reader, and no inspection of wallet bytes (`open_questions.md`, Q5).
- No tests of SQLcl's own defects, such as its case-insensitive `rename -conn` lookup.
- No SQLcl version other than 25.4.1 and no macOS run.
- No pytest-managed database container; the database is started by `make db-start`, outside pytest (`open_questions.md`, Q4, Q14).
- No database scenarios on the Windows runner, which cannot run the Linux database container (`open_questions.md`, Q12).
- No release, publish or deployment workflow.
- No change to `tests/test_integration.py`.
- No version bump: the task changes tests and documentation only (`open_questions.md`, Q9).

## Acceptance Criteria

- **AC-1** - with SQLcl present, `uv run pytest -m integration -q` runs the new package; with `SQLCL_BIN` naming a missing file and no `sql` on `PATH`, every new test skips with a reason and none fails; the default `uv run pytest -q` still selects no integration test (REQ-1)
- **AC-2** - the import fixture is committed, and SQLcl imports it with `Importing connection <name>: Success` (REQ-1, REQ-3)
- **AC-3** - folder scenarios pass: the tool's `folders` and `list --folder` match every SQLcl-built tree, and the tool's folder commands work on it (REQ-2)
- **AC-4** - import scenarios pass, including `RENAME` and `REPLACE`, with no imported value missing from `list` or `export` (REQ-3)
- **AC-5** - connection operation scenarios pass for SQLcl-made and tool-made rename, move, clone and delete, including case-sensitive lookup (REQ-4)
- **AC-6** - every edge-case value is reported exactly, or is a strict `xfail` citing its follow-up task (REQ-5)
- **AC-7** - with the `SQLCL_ITEST_*` variables set, the database scenarios pass; with any of them unset, they skip with a reason (REQ-6)
- **AC-8** - format conformance tests pass on SQLcl 25.4.1, and a forced mismatch shows the SQLcl release in the failure message (REQ-7)
- **AC-9** - no password in tool output or committed files, `<repo-root>/.sqlcl` unchanged, and no test opens `credentials.sso` beyond presence and hash (REQ-8)
- **AC-10** - `README.md`, "Development" and "Testing", document the `make` targets, the three variables, `db-start` / `db-stop`, the workflow and the `sql.exe` note, without repeating the commands behind the targets, and markdown lint is clean (REQ-9)
- **AC-11** - ruff check and format pass on `tests/`, the full unit suite passes, and every `xfail` is strict, names a follow-up task and is limited to the platform where it fails (REQ-1, REQ-2, REQ-3, REQ-4, REQ-5, REQ-6, REQ-7)
- **AC-12** - locally, `make check`, `make unit`, `make sqlcl`, `make db-start`, `make integration` and `make db-stop` succeed; `make db-start` without `SQLCL_ITEST_PASSWORD` fails with a message naming the variable; no recipe echo shows the password; and no command, version or container setting behind a target appears in the workflow or `README.md` (REQ-10)
- **AC-13** - a workflow run on the pull request is green on both runners: on Ubuntu the database scenarios run and pass, on Windows they skip with a reason; the password appears only as `***` in the logs; a second run restores SQLcl from the cache (REQ-11)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| `tests/integration/__init__.py` | Create |
| `tests/integration/conftest.py` | Create |
| `tests/integration/data/sqldev_export.json` | Create |
| `tests/integration/test_harness_smoke.py` | Create |
| `tests/integration/test_folders_compat.py` | Create |
| `tests/integration/test_import_compat.py` | Create |
| `tests/integration/test_connection_ops_compat.py` | Create |
| `tests/integration/test_edge_values_compat.py` | Create |
| `tests/integration/test_saved_password_compat.py` | Create |
| `tests/integration/test_format_conformance.py` | Create |
| `Makefile` | Create |
| `.github/workflows/ci.yml` | Create |
| `.gitignore` | Update (`.cache/`) |
| `README.md` | Update |
| `docs/tasks/sqlcl_store_compat_tests/progress.md` | Update |
| `docs/tasks/sqlcl_store_compat_tests/open_questions.md` | Update (Q11 outcome) |
