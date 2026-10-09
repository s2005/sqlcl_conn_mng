# PRD: Batch Selection With --all And --filter

## Objective

Let `test`, `show`, `delete` and `move` act on many saved connections in one call, chosen with `--all` or with `--filter PATTERN`, and let `list` and `export` narrow their output with `--filter`. A typical use is `sqlcl-conn-mng test --all` or `sqlcl-conn-mng test --filter 'dev_*'` to check every matching connection.

## Background

Every connection-level command takes a single required `--name` (`src/sqlcl_conn_mng/cli.py`, `_add_name`). Checking ten connections means ten invocations and ten SQLcl start-ups driven by an outer shell loop. `list` can narrow by `--folder` only, and `export` always writes every connection. The decisions behind this task are recorded in `open_questions.md`.

## Requirements

### REQ-1: Mutually exclusive selector on test, show, delete and move

`test`, `show`, `delete` and `move` accept exactly one of `--name NAME`, `--filter PATTERN` or `--all`. Giving none, or more than one, is a usage error (exit 2) raised by argparse. `rename`, `clone`, `add`, `folders`, `add-folder` and `delete-folder` are unchanged.

### REQ-2: Filter semantics

`--filter PATTERN` is a shell-style glob (`fnmatch.fnmatchcase`) matched case-sensitively against the whole connection name. `*`, `?` and `[...]` are wildcards. On `list` it combines with `--folder` as AND.

### REQ-3: Name resolution before any action

A selector resolves to a list of connection names, sorted by name, read from the store once before the first action runs. `--name` resolves to that one name and keeps the existing "No saved connection named" error when it is absent. `--all` resolves to every connection. `--filter` resolves to the matching names.

### REQ-4: Batch execution and reporting

For a selection made with `--all` or `--filter`, the command processes every selected connection even when one fails. It prints one line per connection, `[OK] NAME` or `[FAIL] NAME: reason`, then `Summary: N ok, M failed`. The exit code is 1 when any connection failed or when the selection is empty (message `No connections match ...`), otherwise 0. A `--name` selection keeps today's output and exit codes unchanged.

### REQ-5: Guarded batch delete

`delete` with `--all` or `--filter` still requires `--yes`. Without it, nothing is deleted and the command exits 1 with the existing refusal message. With it, the matched names are printed before the first deletion.

### REQ-6: Per-command batch behaviour

- `test`: runs `check_connection` for each selected connection.
- `show`: with `--format json` prints a JSON list of the per-connection objects; with `table` prints the existing block per connection, separated by a blank line. `--check-password` applies to each.
- `delete`: runs `delete_connection` for each.
- `move`: moves each selected connection into `--folder`.
- `list`: gains an optional `--filter`. No `--all` (it already lists everything).
- `export`: gains an optional `--filter` and writes only the matching connections. No `--all`.

### REQ-7: Documentation

`README.md` command table, examples and exit-code section, and `.claude/skills/sqlcl-conn-mng/SKILL.md`, describe the new parameters, the filter syntax, the batch output and the exit codes.

### REQ-8: Version bump

The project version moves from `0.2.1` to `0.3.0` (additive input-parameter change, version still `0.x`). `pyproject.toml` is edited and `uv.lock` regenerated. The global copy is reinstalled and `sqlcl-conn-mng --version` prints `0.3.0`.

### REQ-9: Tests and no regression

Unit tests cover selector exclusivity, glob matching, empty match, continue-on-failure, delete guard and each command's batch path. Existing tests for `--name` pass unchanged. An integration test runs `move --filter` and `delete --filter --yes` against the real SQLcl.

## Non-Requirements

- `--all` and `--filter` on `rename`, `clone`, `add`, `folders`, `add-folder`, `delete-folder`: these need a distinct argument per item or do not select connections.
- `--all` on `list` and `export`: both already cover every connection.
- A `--dry-run` for batch delete, regular-expression or case-insensitive matching, parallel execution, stop-on-first-failure mode: not requested.
- Filtering by folder through `--filter`; `--folder` stays the folder selector.

## Acceptance Criteria

- **AC-1** - `test`, `show`, `delete` and `move` exit 2 with zero selectors and with two or more selectors (REQ-1)
- **AC-2** - `--name` behaves exactly as before, including output and exit codes (REQ-3, REQ-9)
- **AC-3** - `--filter 'dev_*'` selects only names matching case-sensitively, sorted (REQ-2, REQ-3)
- **AC-4** - `--all` selects every connection (REQ-1, REQ-3)
- **AC-5** - A batch continues after a failure, prints per-connection lines and a summary, and exits 1 (REQ-4)
- **AC-6** - An empty selection exits 1 with `No connections match` (REQ-4)
- **AC-7** - Batch `delete` without `--yes` deletes nothing and exits 1; with `--yes` it lists the names first (REQ-5)
- **AC-8** - Batch `show` prints a JSON list or per-connection table blocks (REQ-6)
- **AC-9** - Batch `test` and batch `move` run the SQLcl action for each selected connection (REQ-6)
- **AC-10** - `list --filter` and `export --filter` output only matching connections (REQ-2, REQ-6)
- **AC-11** - README and SKILL.md document every new parameter (REQ-7)
- **AC-12** - Version is `0.3.0` in `pyproject.toml`, `uv.lock` and the installed tool (REQ-8)
- **AC-13** - `make check`, `make unit` and `make integration` pass (REQ-9)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| src/sqlcl_conn_mng/cli.py | Update |
| tests/test_cli.py | Update |
| tests/integration/test_batch_compat.py | Create |
| README.md | Update |
| .claude/skills/sqlcl-conn-mng/SKILL.md | Update |
| pyproject.toml | Update |
| uv.lock | Update |
