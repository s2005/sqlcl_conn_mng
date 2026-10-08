# Analysis: Integration Tests for Compatibility with SQLcl-Made Store Entries

## Goal

Prove with repeatable tests that every kind of store entry SQLcl 25.4.1 writes is read and handled correctly by `sqlcl-conn-mng`, and pin the on-disk format that the future Python writer (`sqlcl_free_catalog_writes`) must reproduce. Run those tests and the existing checks in GitHub Actions as well as locally, with every command defined once (REQ-10, REQ-11).

## Current Behavior

- **Read path.** `ConnectionStore` (`src/sqlcl_conn_mng/store.py:65`) lists `connections/<id>/dbtools.properties` for directories whose name matches `[A-Za-z0-9_-]{22}` (`store.py:21`, `store.py:101`), parses them with `parse_properties` (`src/sqlcl_conn_mng/properties.py:85`), and maps ids to folders from `connection_folders/folders.json` (`store.py:71-90`). Keys other than `name`, `type`, `connectionString` and `userName` go to `extra` (`store.py:20`, `store.py:115`). Lookup by name is case-sensitive and returns the first match in `(name, id)` order (`store.py:118-125`).
- **Wallet.** `has_wallet` checks only that `credentials.sso` exists (`store.py:127-129`). `show --check-password` runs `connmgr show` and parses `Password: ******` or `Password: not saved` (`src/sqlcl_conn_mng/sqlcl.py:196-214`).
- **Write path.** Every write runs SQLcl through `SqlclRunner` (`sqlcl.py:95-137`): the script goes on stdin, argv never carries a password, and success is detected from output text because SQLcl always exits 0 (`sqlcl.py:140-144`).
- **CLI.** `cli.main(argv)` returns an exit code (`src/sqlcl_conn_mng/cli.py:449`); `list`, `show`, `folders` take `--format json`; `delete` and `delete-folder --force` need `--yes`; `list --folder` includes subfolders (`cli.py:113`).
- **Tests.** Unit tests use fake stores from `tests/conftest.py` with invented ids and a fake wallet. The one integration test, `tests/test_integration.py`, adds and deletes one folder. `tests/test_store_probe.py` already loads `scripts/store_probe.py` with `importlib`.
- **Gap.** Nothing checks the read path against files SQLcl really wrote: escaping, non-ASCII, imported connection types, folder ordering, case-only-different names, or the files each operation touches.
- **No CI.** There is no `.github/workflows/` directory and no `Makefile`; `README.md:237-251` lists the `uv run` commands for tests, lint, format and mypy by hand. `ruff check`, `ruff format --check` and `mypy` were clean on 2026-10-08.

## Feasibility

Straightforward for everything except the database scenarios and the import fixture:

- All folder commands, `import`, `clone`, `rename`, `move` and `delete` work without a database (`findings.md`, "Effects per Operation"), so most scenarios need only SQLcl.
- `connect -save` needs a live database. REQ-6 reads its settings from environment variables and skips without them (`open_questions.md`, Q4).
- The SQL Developer export format `connmgr import` accepts is not recorded in the repository; Phase 1 finds a minimal accepted file (`open_questions.md`, Q11).
- SQLcl start-up costs about 10-16 s per process; one process per scenario store keeps the run to a few minutes (`open_questions.md`, Q7).
- CI is feasible on both runner types. SQLcl 25.4.1 downloads without a login (`open_questions.md`, "Added on 2026-10-08"); `ubuntu-latest` has make 4.3, Podman 4.9.3 and Docker; `windows-latest` has Chocolatey, so `choco install make` gives the same GNU Make the user runs locally. Only Linux runners can run the Oracle XE container, so database scenarios run on Ubuntu only (REQ-11).

## Approach

### Option A: one SQLcl process per scenario store, shared read-only fixtures (recommended)

Each scenario is a module- or session-scoped fixture that creates a `tmp_path_factory` store, runs one SQLcl script with all the commands that build it, checks each command's success line, and snapshots the store before and after. Tests then call `cli.main` in-process against that store and compare the tool's JSON with the values the script used. Tests that modify a store (the tool's own write commands) copy the built store into their own `tmp_path` first.

| Advantages | Disadvantages |
| ---------- | ------------- |
| Few SQLcl starts; the suite stays usable | A failing script command fails every test that shares the store |
| Read assertions are cheap and many | The fixture has to map each command to its success line |
| Snapshot pairs give the file-set check for REQ-7 for free | Per-operation file-set checks need a before/after pair around that operation, so those operations get their own script step |

### Option B: one SQLcl process per operation through `sqlcl.py` helpers

| Advantages | Disadvantages |
| ---------- | ------------- |
| Reuses `add_folder`, `move_connection` and friends unchanged | Dozens of SQLcl starts; the run takes far longer |
| Each operation isolated | `import` and `connect -save` with `-replace` have no helper |

Option A is recommended. For the per-operation file-set checks (REQ-7), a scenario fixture runs its setup in one process and each measured operation in its own process with snapshots around it; that is still one process per measured operation, not per command.

### Shared Entry Point for Local Runs and CI (REQ-10, REQ-11)

The user chose a `Makefile` (`open_questions.md`, Q13). It owns every command and every setting that both places need: the check and test commands, `SQLCL_VERSION`, the download URL, the image, the container name, the engine and the port. The workflow selects targets and sets environment variables; `README.md` names targets. Changing the SQLcl release or the image is then a one-line change in one file.

| Advantages | Disadvantages |
| ---------- | ------------- |
| One definition of every command, version and container setting | `make` must be installed on Windows (Chocolatey locally, `choco install make` on the runner) |
| The user already runs `make` locally | Recipes must stay bash-compatible on Windows and Linux (`SHELL := bash`) |
| The workflow stays a short list of `make` calls | Password generation and masking stay in the workflow, because only a workflow step can write to `GITHUB_ENV` and `::add-mask::` |

The workflow is one job definition with an OS matrix, so the steps are written once for both runners; the database steps carry `if: runner.os == 'Linux'`.

## Implementation Notes

- **SQLcl discovery (REQ-1).** Resolve `shutil.which(os.environ.get("SQLCL_BIN") or "sql")`; `which` returns an existing absolute path unchanged and `None` for a missing one, so a wrong `SQLCL_BIN` skips instead of failing with `WinError 193`. Read the release from `version.txt` (`RELEASE=` line) in the executable's directory; fall back to `unknown`.
- **Script builder (REQ-1).** Each step is `(command, expected_line)`. Run all steps through `SqlclRunner.run`, then check that the expected lines occur in order in the cleaned output. Success lines come from `findings.md`, "Validation and Output" (`has been added`, `has been moved to`, `has been renamed`, `has been cloned`, `has been deleted`, `Importing connection <name>: Success`, `Password: ******` / `Password: not saved` after `connect -save`).
- **Password on stdin (REQ-6, REQ-8).** `connect -save` scripts embed the password, so the builder must not include the script in any failure message; it reports the step number and the cleaned output with the password replaced, the same way `sqlcl._without_password` does (`sqlcl.py:249-251`).
- **CLI runner (REQ-1).** Call `cli.main([...command..., "--home", str(store), "--format", "json"])` under `capsys`; commands that run SQLcl also get `--sqlcl <resolved path>`. `delete` and forced `delete-folder` get `--yes`.
- **Snapshots (REQ-1, REQ-7).** Load `scripts/store_probe.py` with `importlib.util.spec_from_file_location`, as `tests/test_store_probe.py` does, and use `take_snapshot`. It records size and a hash prefix for `credentials.sso` and never its bytes. `diff_snapshots` prints instead of returning, so the tests compare the two snapshot dicts directly.
- **Ignored side files.** Every SQLcl run creates `sqlcl/aliases.xml`, `sqlcl/history.log` and up to three `aliases.xml.bak_<n>` (`findings.md`, "Side Effects of Any SQLcl Run"); file-set assertions exclude the `sqlcl/` subtree.
- **Random ids.** Ids are random, so tests find connections by name and compare ids only between before and after states.
- **Key order (REQ-7).** New files keep creation order (`name, type, connectionString, userName` for `connect -save`; `name, type, host, port, serviceName, userName` for `import`); files SQLcl rewrote (rename, clone) follow Java 17 `Properties` iteration order (`connectionString, name, type, userName`; `port, name, host, type, serviceName, userName` for an imported connection). The test states the expected order literally, not by reimplementing the hash order.
- **Non-ASCII (REQ-5).** SQLcl decodes stdin with the Windows ANSI code page (`findings.md`, "Validation and Output", input encoding rule). `SqlclRunner.run` uses `text=True`, so Python encodes stdin with the locale encoding; whether that matches SQLcl's decoding is exactly what the non-ASCII scenario checks through the tool. A mismatch becomes a strict `xfail` citing `sqlcl_stdin_encoding`.
- **Import fixture (REQ-1, REQ-3).** Phase 1 writes a minimal export with fake host, port, service and user and no password, and confirms SQLcl accepts it. If SQLcl rejects every candidate, the fallback in `open_questions.md`, Q11 applies.
- **Case pairs (REQ-4, REQ-5).** SQLcl allows `c1` beside `C1` and `/dev` beside `/DEV`. The tests use the tool's case-sensitive lookup and do not run SQLcl's `rename -conn` on a case pair, because SQLcl picks the wrong connection there (`findings.md`, "Case-Insensitive Lookup Defects").
- **Duplicate names (REQ-3).** `import -duplicates REPLACE` leaves two connections with the same name; the tests assert only what `list` reports, not which one `show --name` picks.
- **Platform-limited `xfail` (REQ-5).** SQLcl decodes stdin as cp1252 only on Windows. A strict `xfail` that also ran on Linux would turn an expected pass into a failure, so it carries `condition=sys.platform == "win32"`.
- **Format on Linux (REQ-7).** The investigation measured Windows only. The Ubuntu job is the first Linux run of the format tests; LF endings and UTF-8 are expected to match, and a difference is drift to record, not a test to weaken.
- **Make recipes and secrets (REQ-10).** make prints each recipe line after expanding make variables. The password is therefore referenced only as a shell variable and passed to the container by name (`APP_USER_PASSWORD="$$SQLCL_ITEST_PASSWORD" $(ENGINE) run -e APP_USER_PASSWORD ...`), so the echoed line shows the variable name, never the value. `ORACLE_PASSWORD` for `SYS` gets a separate random value inside the recipe, also never echoed.
- **Database readiness (REQ-10).** `db-start` polls `$(ENGINE) exec sqlcl-itest-xe healthcheck.sh` (shipped in the `gvenzl` image) with a bounded number of tries, then fails with the container log tail; it does not rely on engine-specific health status.
- **SQLcl download (REQ-10, REQ-11).** `curl -fsSL` fetches the zip (curl ships with Git for Windows and the runners), and `uv run python -m zipfile -e` unpacks it, so no `unzip` is needed on Windows. The workflow caches `.cache/sqlcl/` with key `sqlcl-<os>-$(SQLCL_VERSION)`; it reads the version with `make -s print-sqlcl-version` so the key does not repeat the number. The job adds the unpacked `bin` directory to `GITHUB_PATH`, and the harness finds `sql` (Linux) or `sql.exe` (Windows) there.
- **Java (REQ-11).** `actions/setup-java` with Temurin 17, matching the Java 17 key-order behaviour REQ-7 asserts.
- **Password in CI (REQ-8, REQ-11).** A workflow step generates the password with `python -c "import secrets; print(secrets.token_urlsafe(18))"` into a shell variable, runs `echo "::add-mask::$PW"` before anything else uses it, then appends it to `GITHUB_ENV`. The database lives only for the job, so no repository secret exists.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Long run time | One process per scenario store; read-only fixtures shared per module |
| A database password leaks through a failure message | The builder masks the password in every message; REQ-8 tests assert absence in all tool output |
| No hand-written export is accepted by `connmgr import` | Phase 1 discovery; fallback moves REQ-3 out and the database-free scenarios to Phase 4 |
| Format tests fail on a newer SQLcl | Intended: the message names the release, so the failure reads as drift to re-qualify, not a tool bug |
| Podman database unavailable on the machine | Database scenarios skip with a reason; everything else still runs |
| Tests modify a shared store | Tests that write copy the built store to their own `tmp_path` first |
| `SQLCL_BIN` points at the extensionless shell script on Windows | Discovery uses `shutil.which`; README documents `sql.exe` |
| GNU make on Windows runs recipes with `cmd.exe` | `SHELL := bash` in the `Makefile`; the workflow runs `make` from a `shell: bash` step |
| Rootless Podman on `ubuntu-latest` cannot run the Oracle XE container | `ENGINE=docker` fallback, set once in the workflow `env` if needed |
| Oracle moves or removes the versioned SQLcl zip | The cache keeps working for an unchanged version; a failing download names the URL from the `Makefile` |
| The password reaches the CI log before it is masked | The mask is the first command of the step that creates the password; recipes never echo it |
| Format tests differ on Linux | Treated as drift: recorded in `progress.md`, "Follow-Ups", and in `findings.md` by its own task, not hidden |
| The Windows job runs no database scenarios | Accepted (`open_questions.md`, Q12); the database scenarios run on Ubuntu and locally |

## Test Strategy

All new tests are integration tests under `tests/integration/`, marked `integration`, and excluded from the default run by `pyproject.toml`.

| Level | What |
| ----- | ---- |
| Harness smoke | SQLcl found, release read, one-folder store built, CLI runner returns JSON, skip behaviour without SQLcl |
| Read compatibility | `list`, `show`, `folders`, `export` against SQLcl-built stores (REQ-2 to REQ-6) |
| Operation compatibility | The tool's write commands applied to SQLcl-built stores (REQ-2, REQ-4) |
| Format conformance | Text files and file sets against `findings.md` (REQ-7) |
| Hygiene | Password absence in all output; real stores untouched (REQ-8) |
| Entry point | Every `make` target run locally; `db-start` refusal without a password (REQ-10) |
| CI | One workflow run on the pull request, green on both runners, database scenarios run on Ubuntu and skip on Windows, password masked, cache hit on rerun (REQ-11) |

The default unit run must stay unchanged in count and pass. No coverage threshold is configured in `pyproject.toml`, so none is asserted.
