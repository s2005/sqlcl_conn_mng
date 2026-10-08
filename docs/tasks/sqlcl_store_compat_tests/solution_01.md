# Solution 01: Amend the Spec and Build the Harness to Fit the Code

Chosen from `notes.md`, "Candidate Solutions".

## Chosen Approach

Keep `src/` untouched, correct the parts of the plan that do not match the code, and shape the harness and the `Makefile` so every drift in `notes.md` is resolved inside this task's own files.

## Why It Beats the Alternatives

- **Over 02:** 02 changes product logging, which the PRD excludes ("No change to `src/`"), and resolves only D2. 01 gets the same coverage of error text from the test side.
- **Over 03:** 03 meets AC-9 and AC-12 in letter only: the password check would skip the error text, and the workflow would repeat the `Makefile`'s cache and bin paths. 01 keeps both criteria meaningful.

## Drifts Resolved

| Drift | Resolution |
| ----- | ---------- |
| D1 | `analysis.md`, "Current Behavior", cites the current line numbers |
| D2 | `run_cli` captures stdout, stderr and the `sqlcl_conn_mng` log records without `capsys`, and works from any fixture scope |
| D3 | The `Makefile` gains `print-sqlcl-dir` and `print-sqlcl-bin`; the workflow reads the cache path and the bin directory from them |
| D4 | Scenario store fixtures live in `tests/integration/conftest.py` as session-scoped fixtures from Phase 2 on |
| D5 | Helpers and data types live in `tests/integration/harness.py`; `conftest.py` holds fixtures only |
| D6 | The non-ASCII cases carry one shared strict `xfail` limited to Linux (`STDIN_ENCODING_XFAIL`), where the first CI run showed the stdin-encoding mismatch |

## Files to Change

| File | Change |
| ---- | ------ |
| `docs/tasks/sqlcl_store_compat_tests/analysis.md` | Line references (D1) |
| `docs/tasks/sqlcl_store_compat_tests/implementation_plan.md` | `run_cli` wording, the two print targets, fixture placement (D2, D3, D4) |
| `tests/integration/conftest.py` | `run_cli` capture (D2); session-scoped store fixtures (D4) |
| `Makefile` | `print-sqlcl-dir`, `print-sqlcl-bin` (D3) |
| `tests/integration/harness.py` | New: helpers and data types (D5) |

## Implementation Outline

1. Correct the references in `analysis.md` and the affected bullets in `implementation_plan.md`.
2. `run_cli`: run `cli.main` under `contextlib.redirect_stdout` and `redirect_stderr` into `io.StringIO`, with a `logging.Handler` attached to the `sqlcl_conn_mng` logger for the call; the returned stderr text is the redirected stderr followed by the formatted log records.
3. `Makefile`: `print-sqlcl-dir` prints `$(abspath $(SQLCL_DIR))`; `print-sqlcl-bin` prints the absolute bin directory of the unpacked release.
4. Phases 2-4 add their store fixtures to `tests/integration/conftest.py` with `scope="session"`; Phase 5 imports nothing new and only requests them.

## Verification

- Harness smoke test: `run_cli` on an unknown connection returns exit code 1 and a stderr text naming the connection.
- `make -s print-sqlcl-dir` and `make -s print-sqlcl-bin` print absolute paths, and `sql` resolves from the printed bin directory after `make sqlcl`.
- Phase 5 runs without building any store a second time: one SQLcl build per scenario store in the `-rs`/timing output.
- `grep` over `.github/workflows/ci.yml` finds neither `.cache/sqlcl` nor `sqlcl/bin`.
