# Open Questions: Integration Tests for Compatibility with SQLcl-Made Store Entries

Context gathered before writing this file:

- `sqlcl-conn-mng` reads the store in Python (`src/sqlcl_conn_mng/store.py`, `src/sqlcl_conn_mng/properties.py`) and runs SQLcl for every write (`src/sqlcl_conn_mng/sqlcl.py`). `show --check-password` asks SQLcl (`connmgr show`); `wallet_present` only checks that `credentials.sso` exists (`store.py:214`).
- The only integration test today is `tests/test_integration.py`: one folder add/delete round trip against a `tmp_path` store. It carries the `integration` marker, which `pyproject.toml` excludes by default (`addopts = ["-m", "not integration"]`). Baseline run on 2026-10-08: `uv run pytest -m integration -q` - 1 passed in 16 s, with `sql.exe` found on `PATH`.
- Setting `SQLCL_BIN` to the extensionless `<sqlcl-dir>/bin/sql` shell script fails on Windows with `[WinError 193] %1 is not a valid Win32 application`; it must name `sql.exe`.
- `docs/tasks/sqlcl_jar_store_investigation/findings.md` holds the clean-room specification of what SQLcl 25.4.1 writes for every operation, with expected files, keys, escaping, folder layout and output text. It is the oracle these tests can assert against.
- `connect -save` saves only after a successful database connection; `connmgr import`, `clone`, `rename`, `move`, `delete` and all folder commands do not connect (`findings.md`, "Effects per Operation").
- Python-side store writers do not exist yet; they are the follow-up task `sqlcl_free_catalog_writes`.
- No CI workflow exists in the repository (`.github/workflows` absent), so integration tests run locally only.

## Q1: Which direction of compatibility do the tests cover?

- **Why it matters**: decides whether the task needs a Python store writer at all.
- **Options**: (a) SQLcl writes the entries, and `sqlcl-conn-mng` reads them (`list`, `show`, `folders`, `export`) and operates on them through its own commands. (b) Also the reverse: entries written by `sqlcl-conn-mng` in Python and read by SQLcl. No Python writer exists yet, so this needs `sqlcl_free_catalog_writes` first. (c) Both now, with a test-only Python writer.
- **Recommended**: (a), with the store-building fixtures written so `sqlcl_free_catalog_writes` can add the reverse direction by reusing them - why: it matches the request ("entries made via the SQLcl tool"), and (c) would build a throwaway writer the follow-up replaces.
- **Answer**: (a) - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.

## Q2: Which SQLcl-made entries are covered?

- **Why it matters**: sets the size of the scenario list and the run time.
- **Options**: (a) the full operation effect map in `findings.md`: `connect -save` with and without `-savepwd`, `-replace` both ways, `clone` plain / `-username` / `-nopwd`, `rename`, `move`, `delete`, folder add (nested) / rename / move / delete / `-force`, `connmgr import` of a SQL Developer export, plus the edge-case values the investigation proved (leading space in a name, `:=#!\` in a user, a descriptor connect string, non-ASCII names, names that differ only in case, `back\slash` and `lt<gt>` folder names). (b) a core subset: `connect -save` with and without a password, nested folders, `clone`, `rename`, `move`, `delete`.
- **Recommended**: (a) - why: each case already has an expected result in `findings.md`, and once the fixtures exist each extra scenario is a few lines.
- **Answer**: (a) - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.

## Q3: Do the tests also assert SQLcl's on-disk format?

- **Why it matters**: semantic checks prove the tool reads SQLcl's entries correctly today; format checks also catch a SQLcl upgrade that changes the format the Python writer will copy.
- **Options**: (a) semantic only: the tool's `list` / `show` / `folders` / `export` report the values given to SQLcl, cross-checked with SQLcl's own `connmgr show`. (b) semantic plus text-format conformance with `findings.md`: id rule, the file set each operation creates/changes/deletes, `dbtools.properties` (no header, LF, final LF, escaping, key order) and `folders.json` (compact, all three keys, siblings sorted, no final newline). Wallet bytes are never inspected in either option.
- **Recommended**: (b), with format tests failing on drift and naming the SQLcl version in the failure message - why: the format is undocumented by Oracle, and these tests are the cheapest way to notice drift before the Python writer ships.
- **Answer**: (b) - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.

## Q4: Where does the live database for `connect -save` come from?

- **Why it matters**: `connect -save` is the main way users save a connection, and SQLcl refuses to save without a successful connection.
- **Options**: (a) the tests read the connect string, user and password from environment variables and skip the database scenarios when they are unset; the database is started outside pytest, and `README.md` documents a podman command for it. (b) a session fixture starts and stops a podman `gvenzl/oracle-xe` container itself. (c) no database: create connections with `connmgr import` only and drop the `connect -save` scenarios.
- **Recommended**: (a) - why: a container start takes minutes and podman on Windows is fragile; (a) also works against any reachable database. The scenarios that need no database (folders, `import`, and `clone` / `rename` / `move` / `delete` of imported entries) still run whenever SQLcl is present.
- **Answer**: (a), with the variables `SQLCL_ITEST_CONNECT`, `SQLCL_ITEST_USER` and `SQLCL_ITEST_PASSWORD` - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree. Refined by Q14: the podman command lives in the `Makefile` target `db-start`, and `README.md` documents the target instead of the command.

## Q5: How do the tests check whether a password is saved?

- **Why it matters**: the investigation proved a Python wallet reader is feasible, but the product does not have one.
- **Options**: (a) use the tool's current behaviour only - `wallet_present` and `show --check-password` - and never open `credentials.sso`. (b) add a Python wallet reader to the tests.
- **Recommended**: (a) - why: (b) is product functionality owned by `sqlcl_free_catalog_writes`.
- **Answer**: (a) - decided by reading `~/.claude/rules/jira-scope.md` (no unrequested functionality) and `findings.md`, "Follow-Up Tasks". The tests also assert that the dummy password never appears in any tool output or export file.

## Q6: What happens when a test exposes a tool defect?

- **Why it matters**: the investigation already lists known gaps, for example SQLcl decoding stdin as cp1252 on Windows (`sqlcl_stdin_encoding`), which can corrupt non-ASCII names the tool passes to SQLcl.
- **Options**: (a) commit the test as `pytest.mark.xfail(strict=True, reason="<follow-up task>: <concern>")` and record the follow-up; fix nothing in `src/`. (b) fix the defect in this task.
- **Recommended**: (a) - why: one ticket, one fix; this task delivers tests.
- **Answer**: (a) - decided by reading `~/.claude/rules/jira-scope.md`. A defect without an existing follow-up task gets one named in `progress.md`. A gap whose expected behaviour is not decided yet - for example how the tool should present an imported `ORACLE_BASIC` connection, which has `host` / `port` / `serviceName` and no `connectionString` - gets a test asserting that no value is lost, and a follow-up note in `progress.md` instead of an `xfail`. SQLcl's own defects, such as its case-insensitive `rename -conn` lookup, are not tool-compatibility questions and get no test.

## Q7: How is SQLcl's start-up cost handled?

- **Why it matters**: each SQLcl start takes about 10-16 s (`README.md`, "Testing"; baseline run above). One process per operation over the full scenario list would run for many minutes.
- **Options**: (a) build each scenario's store with one SQLcl process running a multi-command script, share read-only stores across tests with module- or session-scoped fixtures, and drive the commands under test through the tool's CLI. (b) one SQLcl process per operation through the existing helpers.
- **Recommended**: (a) - why: same coverage, far fewer SQLcl starts.
- **Answer**: (a) - decided by reading `README.md`, "Testing", and the baseline run time.

## Q8: Where do the tests live, and how are they selected?

- **Why it matters**: `--strict-markers` rejects unregistered markers, and the default run must stay SQLcl-free.
- **Options**: (a) a new `tests/integration/` package using the existing `integration` marker; database scenarios skip on missing environment variables rather than needing a new marker. (b) extend `tests/test_integration.py`.
- **Recommended**: (a).
- **Answer**: (a) - decided by reading `pyproject.toml` (`markers`, `addopts`) and `tests/test_integration.py`. The existing test stays where it is.

## Q9: Does the task bump the version or update `README.md`?

- **Why it matters**: the global rules require a bump only when a tool's input parameters change, and require docs for anything a user must set.
- **Answer**: no version bump - tests, build tooling and docs only, no input parameter changes (`~/.claude/CLAUDE.md`, "Version bump on input parameter change"). `README.md`, "Development" and "Testing", are updated with the `make` targets, the new environment variables, the workflow and the `sql.exe` note - decided by reading `README.md:237-251`, which already documents the development commands and the integration run.

## Q10: Which stores and secrets may the tests touch?

- **Answer**: only `tmp_path` stores passed with `-home`; never `<repo-root>/.sqlcl` or `<home>/.sqlcl`; the database password only through an environment variable, never in argv, logs or assertion messages - decided by reading `AGENTS.md` and `~/.claude/rules/secrets.md`.

## Q11: What SQL Developer export does `connmgr import` accept?

- **Why it matters**: `connmgr import` is the only way to create a connection without a database, so the database-free scenarios need a committed export fixture. The investigation imported one (`findings.md`, "Effects per Operation", `imp/01_import`) but kept it in scratch, and `findings.md` records only the resulting keys, not the input file.
- **Options**: (a) discovery step in Phase 1: write a minimal export with fake host, port, service and user, and accept it when SQLcl prints `Importing connection <name>: Success` and writes `type=ORACLE_BASIC`. (b) skip import and run every connection scenario against the database.
- **Recommended**: (a) - why: it keeps most scenarios runnable without a database.
- **Answer**: (a), accepted on the first try in Phase 1 (2026-10-08). `tests/integration/data/sqldev_export.json` is a SQL Developer JSON export: a top-level `connections` list whose items have `name`, `type` `jdbc` and an `info` object with `ConnName`, `user`, `hostname`, `port`, `serviceName`, `OracleConnectionType` `BASIC`, `RaptorConnectionType` `Oracle`, `driver`, `customUrl`, `oraDriverType`, `subtype`, `SavePassword` `false`, `NoPasswordConnection` `TRUE` and an empty `role`. All values are fake (`db.example.test`, `1521`, `fakesvc`, `imp_user1` to `imp_user3`), and no password is present. SQLcl 25.4.1 printed `Importing connection imp1: Success`, `Importing connection imp3: Success`, `Importing connection imp2: Success` and `3 connection(s) processed`, and wrote three connection directories, each with `dbtools.properties` (keys `name, type, host, port, serviceName, userName`, `type=ORACLE_BASIC`, LF, final LF) and a 270-byte `credentials.sso`, matching `findings.md`, "Effects per Operation". The success lines come in an order other than the file's, so the store builder checks the lines of one step as a set, not a sequence. No fallback was needed: REQ-3 stays in scope, and Phases 2 and 3 run without a database.

## Added on 2026-10-08: Run the Tests in GitHub Actions

The user asked for the tests to run in GitHub Actions as well as locally, without duplicated code (DRY). Context gathered for the questions below:

- The repository has no workflow yet; `origin` is `github.com/s2005/sqlcl_conn_mng`.
- The pinned SQLcl release is downloadable without a login: `https://download.oracle.com/otn_software/java/sqldeveloper/sqlcl-25.4.1.022.0618.zip` answered `200`, `application/zip`, 102,068,355 bytes, on 2026-10-08.
- The investigation ran SQLcl on Java 17 (`findings.md`, "Environment"), and the key order of rewritten `dbtools.properties` files depends on Java 17 `Properties` iteration (`findings.md`, "Key Order").
- GitHub-hosted Windows runners cannot run Linux containers, so an Oracle XE container is available on `ubuntu-latest` only.
- `uv run ruff check src tests scripts`, `uv run ruff format --check src tests scripts` and `uv run mypy` were clean on 2026-10-08, so a lint gate would start green.
- The commands to run checks and the database settings would otherwise live in three places: `README.md`, the workflow file and the developer's shell.

## Q12: Which runners does the workflow use?

- **Why it matters**: the investigation qualified Windows only, and the cp1252 stdin issue exists only on Windows; the database container exists only on Linux runners.
- **Options**: (a) a matrix of `ubuntu-latest` (all tests, with the database) and `windows-latest` (all tests except the database scenarios, which skip). (b) `ubuntu-latest` only. (c) `windows-latest` only, without a database.
- **Recommended**: (a) - why: Linux gets full coverage including the database, and Windows keeps the platform the user works on and the one the investigation measured.
- **Answer**: (a) - decided by the user on 2026-10-08. The Windows-only strict `xfail` for the cp1252 stdin issue gets `condition=sys.platform == "win32"`, because the same test passes on Linux and a strict `xfail` would then fail.

## Q13: What is the single entry point shared by local runs and the workflow?

- **Why it matters**: DRY - the commands, the SQLcl version and the database container settings must be defined once.
- **Options**: (a) one stdlib-only Python script, `scripts/itest.py`, with argparse named options (`--command install-sqlcl|start-db|stop-db|check|unit|integration`), called by the workflow and documented in `README.md`; the SQLcl release, image name and variable names are constants in that script. (b) a `Makefile`; `make` is not part of Git Bash on Windows. (c) a bash script; argument handling is weaker and the global rules ask for argparse. (d) `nox` or `tox`; adds a dev dependency.
- **Recommended**: (a) - why: runs the same on Windows Git Bash, Linux and both runner types; follows the existing `scripts/store_probe.py` style (`--command`, stdlib only) and the named-parameters rule.
- **Answer**: (b) a `Makefile` - decided by the user on 2026-10-08 ("I am using it"). Checked afterwards: Git for Windows does not bundle `make`; the user's GNU Make 4.4.1 comes from Chocolatey. `ubuntu-latest` has make 4.3, and `windows-latest` has Chocolatey but no `make` on `PATH`, so the workflow installs it with `choco install make`, the same source as the local install. The `Makefile` is the only place that defines the check, test, SQLcl and database commands, the SQLcl release, the image name and the container name; `README.md` and the workflow call its targets. It sets `SHELL := bash` so recipes run in bash on Windows too.

## Q14: How is the database started in GitHub Actions?

- **Why it matters**: a GitHub service container is configured in the workflow file, which would duplicate the image and settings the local instructions use, and needs a fixed password before any step runs.
- **Options**: (a) the shared script starts `gvenzl/oracle-xe:21-slim` with `docker` in the workflow and `podman` locally (`--engine`), waits for readiness, and generates a random password per run that the workflow masks with `::add-mask::`. (b) a GitHub service container with the password in a repository secret.
- **Recommended**: (a) - why: one definition of the container for both places, and no stored secret at all because the database lives only for the job.
- **Answer**: (a), carried by the `Makefile` targets `db-start` and `db-stop` instead of a script (Q13) - decided by the user on 2026-10-08. `ENGINE` defaults to `podman`, which is the local engine and is also installed on `ubuntu-latest` (Podman 4.9.3), so both places run the same command; `ENGINE=docker` is the fallback. `db-start` refuses to run when `SQLCL_ITEST_PASSWORD` is unset; the workflow generates it per run and masks it, and a developer sets it locally.

## Q15: What does the workflow run?

- **Why it matters**: decides whether the workflow is a test runner only or the project's quality gate.
- **Options**: (a) lint, format check, mypy, unit tests and integration tests. (b) unit and integration tests only.
- **Recommended**: (a) - why: the lint gate is green today, so it costs nothing to add, and the same `check` command serves local runs.
- **Answer**: (a) - decided by the user on 2026-10-08.

## Q16: When does the workflow run, and which SQLcl and Java does it use?

- **Answer**: on `pull_request`, on `push` to `main` and on `workflow_dispatch`; SQLcl `25.4.1.022.0618` from the URL above, downloaded by the `Makefile` target `sqlcl` and cached by version; Java 17 (Temurin) through `actions/setup-java` - decided by reading `findings.md` ("Environment", "Key Order"), since the format tests assert the Java 17 key order and the 25.4.1 format.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered (default) | REQ-1, Non-Requirements |
| Q2 | Answered (default) | REQ-2 to REQ-6 |
| Q3 | Answered (default) | REQ-7 |
| Q4 | Answered (default), refined by Q14 | REQ-1, REQ-6, REQ-9, REQ-10 |
| Q5 | Answered | REQ-6, REQ-8 |
| Q6 | Answered | REQ-3, all scenario phases |
| Q7 | Answered | REQ-1 |
| Q8 | Answered | REQ-1 |
| Q9 | Answered | REQ-9, Non-Requirements |
| Q10 | Answered | REQ-8 |
| Q11 | Answered (Phase 1 discovery: accepted) | REQ-1, REQ-3 |
| Q12 | Answered (user) | REQ-5, REQ-11 |
| Q13 | Answered (user) | REQ-10 |
| Q14 | Answered (user) | REQ-10, REQ-11 |
| Q15 | Answered (user) | REQ-11 |
| Q16 | Answered | REQ-10, REQ-11 |
