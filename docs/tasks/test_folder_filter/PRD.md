# PRD: Folder Selection For test

## Objective

Let `sqlcl-conn-mng test` select the connections to test by folder, the same way `list` filters by folder: `--folder PATH` selects every connection in that folder or below, and combines with `--filter PATTERN` as AND.

## Background

`test` takes exactly one of `--name`, `--filter` or `--all` (`src/sqlcl_conn_mng/cli.py:237-242`, through `_add_selector` at `:42`). `--filter` matches the connection name only, so connections that share a folder but no name pattern cannot be tested in one call. The workaround today is `list --folder ... --format json` followed by one `test --name` per connection. `list` already has `--folder` (folder or below, through `_in_folder` at `:307`) and `--filter`, combined as AND (`:430-441`). For `--folder /`, `_in_folder` compares subfolders against `//`, so `list --folder /` returns only root-level connections; this task keeps that behaviour (decision Q7). The decisions behind this PRD are recorded in `open_questions.md`.

## Requirements

### REQ-1: test --folder selects by folder

`test` accepts `--folder PATH`. It selects every saved connection whose folder is `PATH` or a subfolder of it, using the same `_in_folder` helper as `list`, so `test --folder /dev` and `list --folder /dev` select the same connections. The parsed value uses a dedicated destination (not `folder`), so the shared selection code can never mistake `move --folder` (a destination) for a selector.

### REQ-2: Selector rules

`test` takes exactly one of: `--name NAME`, `--all`, or a folder/filter selection made of `--folder`, `--filter`, or both.

- `--folder` and `--filter` together select connections matching both (AND), as in `list`.
- `--name` combined with any of `--folder`, `--filter`, `--all` is a usage error, exit code 2.
- `--all` combined with `--folder` or `--filter` is a usage error, exit code 2.
- No selector at all is a usage error, exit code 2, as today.
- Usage errors are raised during argument parsing, so `build_parser().parse_args(...)` exits 2 as well as `main(...)`.

### REQ-3: Empty folder selection

A folder/filter selection that matches nothing, including a folder that does not exist, fails with the existing empty-batch error: exit code 1, no SQLcl run, and a message naming every selector given, for example `No connections match --folder '/dev' --filter 'x_*'`. With `--format json` the existing error envelope carries that message.

### REQ-4: Batch behaviour for a folder selection

A `--folder` selection (with or without `--filter`) is a batch, identical to a `--filter` batch today: names sorted, connections sharing a name refused before any SQLcl run, one `[OK] NAME` / `[FAIL] NAME: reason` line per connection, `Summary: N ok, M failed`, continue after a failure, exit 1 on any failure, and the batch JSON envelope with `--format json`.

### REQ-5: Version bump

The project version goes from 0.5.0 to 0.6.0 in `pyproject.toml`, `uv.lock` is refreshed with `uv lock`, and `sqlcl-conn-mng --version` prints 0.6.0.

### REQ-6: Documentation

`README.md` documents `test --folder` in the command table, the Batch selection section, the JSON output batch list and the Examples. `.claude/skills/sqlcl-conn-mng/SKILL.md` documents it in its command table and selector paragraph, and states that 0.6.0 or newer is needed for `test --folder`.

### REQ-7: Other commands unchanged

`show`, `delete` and `move` keep exactly one of `--name`, `--filter`, `--all`; `move --folder` stays the destination folder; `list` and `export` are unchanged.

### REQ-8: Root folder keeps its current meaning

`_in_folder` is not changed. `list --folder /` keeps returning only root-level connections (those in no folder), and `test --folder /` selects the same set. A test pins this for both commands, so a later change to it is deliberate.

## Non-Requirements

- `--folder` as a selector on `show` or `delete` - out of scope by decision Q2; a follow-up task if wanted. `move` cannot take it, because its `--folder` is the destination.
- A separate "folder does not exist" error (decision Q4).
- Changing what `--folder /` selects, or adding an option that selects the root and every folder below it - a separate option in a follow-up task (decision Q7).
- Making the selector optional on `test` so a bare `test` tests everything (decision Q1).

## Acceptance Criteria

- **AC-1** - `test --folder /dev` runs SQLcl for exactly the connections `list --folder /dev` returns, and for no other (REQ-1, REQ-4)
- **AC-2** - `test --folder /dev --filter 'PAT'` runs SQLcl only for connections in `/dev` or below whose name matches `PAT` (REQ-2)
- **AC-3** - `test` with no selector, `--name` plus `--folder`, `--name` plus `--filter`, `--name` plus `--all`, `--all` plus `--folder`, `--all` plus `--filter` each exit 2 from both `parse_args` and `main` (REQ-2)
- **AC-4** - A folder selection matching nothing exits 1 without running SQLcl, and the log names every selector given; with `--format json` the error envelope carries the same message (REQ-3)
- **AC-5** - A folder batch prints per-connection lines and a summary in table mode, the batch envelope in JSON mode, exits 1 on any failure, and refuses a selection holding a duplicated name (REQ-4)
- **AC-6** - `pyproject.toml` and `uv.lock` carry 0.6.0 and `uv run sqlcl-conn-mng --version` prints 0.6.0 (REQ-5)
- **AC-7** - `README.md` and `SKILL.md` describe `test --folder` and its AND rule with `--filter`, and `SKILL.md` names 0.6.0 as the minimum version for it (REQ-6)
- **AC-8** - The existing selector tests for `show`, `delete`, `move` pass unchanged, and `move --filter ... --folder X` still moves into `X` (REQ-7)
- **AC-9** - `list --folder /` and `test --folder /` both select only `root_conn` in the test store, not the connections in `/dev/local` or `/prod` (REQ-8)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| `src/sqlcl_conn_mng/cli.py` | Update |
| `tests/test_cli.py` | Update |
| `pyproject.toml` | Update |
| `uv.lock` | Update |
| `README.md` | Update |
| `.claude/skills/sqlcl-conn-mng/SKILL.md` | Update |
