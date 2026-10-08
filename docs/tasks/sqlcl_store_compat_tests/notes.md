# Notes: Spec-to-Code Drift

Drift found before Phase 1, between the task files in this folder and the code they describe. Each entry was checked against the file contents on 2026-10-08.

## Drifts

### D1: Line references in `analysis.md` do not match the code

- Spec: `analysis.md`, "Current Behavior", cites `store.py:108`, `store.py:152`, `store.py:158-177`, `store.py:188`, `store.py:202`, `store.py:207-212`, `store.py:214-216` and `properties.py:336`.
- Code: `src/sqlcl_conn_mng/store.py` has 129 lines and `src/sqlcl_conn_mng/properties.py` has 91. The described behaviour exists at `store.py:21` (id pattern), `store.py:101` (directory filter), `store.py:71-90` (folders), `store.py:115` (`extra`), `store.py:120-125` (case-sensitive lookup), `store.py:127-129` (`has_wallet`) and `properties.py:85` (`parse_properties`).
- Difference: the behaviour matches; only the line numbers are stale.

### D2: The CLI's error text never reaches `capsys`

- Spec: `implementation_plan.md`, Phase 1: `run_cli` returns "exit code, stdout and stderr from `capsys`"; Phase 4: `assert_no_password` runs "over the stdout and stderr of every tool call".
- Code: `cli.main` reports every failure through `logger.error` (`src/sqlcl_conn_mng/cli.py:457-459`), and `setup_logging` calls `logging.basicConfig` (`cli.py:205-210`), which does nothing when the root logger already has handlers. Under pytest it always does, so the message goes to pytest's log capture. A probe run of `cli.main(["show", "--name", "nosuch", ...])` under `capsys` returned exit code 1 with the name absent from both captured streams. `capsys` is also function-scoped, so it cannot serve the module- and session-scoped store fixtures.
- Difference: a `capsys`-only runner would miss every error message, and the password check would not cover the text most likely to echo input.

### D3: The workflow cannot find SQLcl without repeating `Makefile` settings

- Spec: `implementation_plan.md`, Phase 6: cache `.cache/sqlcl` and "append the unpacked `bin` directory to `GITHUB_PATH`"; `PRD.md`, REQ-10 and REQ-11: no setting is repeated in the workflow. Phase 1 defines only `print-sqlcl-version` for the workflow to read.
- Code: no `Makefile` yet. `SQLCL_DIR := .cache/sqlcl` and the unpack layout (`$(SQLCL_DIR)/$(SQLCL_VERSION)/sqlcl/bin`, since the Oracle zip has a top-level `sqlcl/` folder) would exist only in the `Makefile`.
- Difference: with `print-sqlcl-version` alone, the workflow would have to write the cache directory and the bin path by hand, which REQ-11 forbids.

### D4: Phase 5 reuses fixtures that Phases 2-4 place in test modules

- Spec: `implementation_plan.md`, Phases 2-4 build each store as a "module store" in its test module; Phase 5 reuses them "through session-scoped versions of their fixtures, so no store is built twice".
- Code: pytest cannot share a fixture defined in one test module with another module, so Phase 5 would either move the fixtures or build the stores again.
- Difference: the plan's sequence implies a rewrite of the Phase 2-4 fixtures in Phase 5.

### D5: Test modules need the harness helpers, but the plan puts them in `conftest.py`

- Spec: `implementation_plan.md`, Phase 1 and "Affected Files", place the helpers (`snapshot`, `copy_store`, `assert_no_password`, the store builder) and the data types in `tests/integration/conftest.py`.
- Code: test modules must call these helpers and name the types directly; pytest discourages importing a `conftest.py` as a module, and `tests/__init__.py` (present) makes `tests.integration` an importable package.
- Difference: the helpers need a module that tests can import; `conftest.py` should hold only fixtures.

## Candidate Solutions

### 01: Amend the spec where it is wrong, and build the harness to fit the code

- Approach: correct the line references in `analysis.md` (D1); make `run_cli` redirect `sys.stdout` and `sys.stderr` with `contextlib` and attach a temporary handler to the `sqlcl_conn_mng` logger, appending the formatted records to the returned stderr text, so it works from any fixture scope (D2); add `print-sqlcl-dir` and `print-sqlcl-bin` targets beside `print-sqlcl-version` (D3); define the scenario store fixtures session-scoped in `tests/integration/conftest.py` from Phase 2 on (D4); put the helpers and data types in `tests/integration/harness.py`, imported by `conftest.py` and the test modules, and keep only fixtures in `conftest.py` (D5).
- Scope: task docs, `tests/integration/conftest.py`, `tests/integration/harness.py`, `Makefile`. No `src/` change.
- Pros: every drift resolved; no product change; the workflow reads every path from the `Makefile`; no store is built twice.
- Cons: two make targets the plan did not list; `run_cli` differs from the plan's wording.
- Risk: low.

### 02: Change the product so its errors reach stderr

- Approach: make `setup_logging` pass `force=True` or add its own stderr handler, so `capsys` sees errors.
- Scope: `src/sqlcl_conn_mng/cli.py` and unit tests.
- Pros: `run_cli` stays as planned.
- Cons: a product behaviour change the PRD rules out ("No change to `src/`"); leaves D1, D3 and D4 open.
- Risk: medium; changes logging for every user of the CLI.

### 03: Follow the plan literally

- Approach: `capsys` only, the cache path and bin path written into the workflow, module fixtures duplicated in Phase 5.
- Scope: as planned.
- Pros: no deviation from the wording.
- Cons: error text unchecked by `assert_no_password`; the workflow repeats `Makefile` settings against REQ-11; every store built twice against Phase 5's own goal.
- Risk: high; two acceptance criteria (AC-9, AC-12) would be met in letter only.
