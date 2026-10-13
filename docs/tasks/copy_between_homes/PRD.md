# PRD: Copy Saved Connections Between Homes

## Objective

Add a `copy` subcommand that copies one or more saved connections from the store named by `--home` into another SQLcl store named by `--to-home`, carrying the saved password across without asking for it, and placing each copy in the same folder path it had in the source.

## Background

Every command works on a single store. `move` relocates connections between folders of one store, `clone` duplicates a connection inside one store, and `export` writes metadata without passwords and has no matching import. A connection can be brought into another store today only by re-running `add` there, which needs the password again and a reachable database.

The store investigation (`docs/tasks/sqlcl_jar_store_investigation/findings.md`, "Id Round Trip") proved that a connection directory copied byte for byte under a new id is a working connection for SQLcl 25.4.1: the copied `credentials.sso` was reported as saved and connected. The wallet does not depend on the directory or store it sits in. Decisions are recorded in `open_questions.md`.

## Requirements

### REQ-1: `copy` subcommand surface

- `sqlcl-conn-mng copy --to-home DIR (--name NAME | --filter PATTERN | --all) [--format table|json]`, plus the global options (`--home`, `--sqlcl`, `--driver`, `--timeout`, `--log-level`).
- `--to-home` is required. Exactly one of `--name`, `--filter` or `--all` is required. A missing or doubled selector is a usage error (exit code 2), the same as `move`.
- `--name` is a single result. `--filter` and `--all` are a batch with `[OK] NAME` or `[FAIL] NAME: reason` per connection and `Summary: N ok, M failed`. `--format json` prints the single-result or batch envelope described in README "JSON output".
- Exit code 1 when any selected connection fails or when a batch matches nothing.

### REQ-2: Copy each connection as opaque files under a new id

- Each copy goes to `<to-home>/connections/<new id>/`. The new id is 22 URL-safe characters from 16 random bytes, the rule SQLcl accepts. It never equals an id already present in the target.
- `dbtools.properties` and, when present, `credentials.sso` are copied byte for byte with their file permissions. The wallet is never opened, decoded, parsed or printed. A source without `credentials.sso` is copied without one.
- The files are written to a staging directory inside `<to-home>/connections/` and renamed into place, so a failed copy leaves no partial connection directory.
- `<to-home>` and `<to-home>/connections/` are created when missing.
- The source store is never modified.

### REQ-3: Place the copy in the source folder path

- A connection at `/` in the source stays at `/` in the target. No SQLcl is run for it.
- A connection in folder `/p/q` is placed in `/p/q` in the target through SQLcl run with `-home <to-home>`. The tool runs `connmgr add -folder /p/q` only when the folder is missing, then `connmgr move -conn NAME /p/q`. The tool still never writes `folders.json` itself.
- When a folder step fails, the copied connection directory is removed again and that connection is reported as failed. A folder created before the failure is left in place.

### REQ-4: Refuse a name that already exists in the target

- A connection whose name equals the name of any target connection, compared case-insensitively, is refused with a `[FAIL]` that names the clash. Nothing is written for it. The rest of the batch continues.
- The existing target connection is left unchanged.

### REQ-5: Checks before anything is written

- When `--home` and `--to-home` resolve to the same directory, the command exits with code 1 before any write, the same way `update` reports an invalid option combination.
- A batch selection that holds a name shared by several source connections is refused with exit code 1 and nothing is copied (the existing `_reject_duplicate_names` rule).
- `--name` of a connection that does not exist exits with code 1, the same as other `--name` commands.

### REQ-6: Documentation

- `README.md`: `copy` rows in the Commands table, a note on how the copy works (new id, opaque wallet copy, folder mirroring, name refusal, target creation), `copy` added to the "Batch selection" and "JSON output" lists, and one example. The sentences stating that the tool never reads or writes `credentials.sso` and that every write runs SQLcl are reworded to cover `copy`.
- `.claude/skills/sqlcl-conn-mng/SKILL.md`: `copy` in the description and command list, and the minimum version raised to 0.6.0 for `copy`.
- No tip about combining `copy` with `delete`, and no mention of a future cross-home move, in either file.

### REQ-7: Version bump

- `pyproject.toml` version goes from 0.5.0 to 0.6.0 (additive change in a `0.x` project), followed by `uv lock`. The global install is reinstalled, and `sqlcl-conn-mng --version` prints 0.6.0.

## Non-Requirements

- Moving between homes, including a `--delete-source` option (`open_questions.md`, Q4).
- Overwriting or renaming on a name clash (`--replace`, automatic `_1` suffix).
- A `--folder` override for the destination folder.
- Copying folders that hold no selected connection, or an empty folder tree.
- Decoding, re-encrypting or validating the wallet, and testing the copied connection against a database.
- Import of the JSON written by `export`.

## Acceptance Criteria

- **AC-1** - `copy --help` lists `--to-home`, `--name`, `--filter`, `--all` and `--format`. A missing `--to-home`, a missing selector or two selectors each exit with code 2. (REQ-1)
- **AC-2** - `--format json` prints the single-result envelope for `--name` and the batch envelope with `results`, `ok` and `failed` for `--filter` and `--all`. A batch with no match exits with code 1. (REQ-1)
- **AC-3** - After a copy, the target holds a new directory whose name is 22 URL-safe characters, differs from the source id and from every existing target id, and whose `dbtools.properties` and `credentials.sso` are byte-identical to the source. A source without a wallet produces a copy without one. (REQ-2)
- **AC-4** - A copy into a target home that does not exist creates it. The source store is byte-identical before and after, and no staging directory is left after a failed copy. (REQ-2)
- **AC-5** - A root-level connection is copied without any SQLcl run. A nested connection runs `connmgr add -folder` only when the folder is missing, then `connmgr move`, both with `-home <to-home>`. A failing folder step leaves no copied directory and reports `[FAIL]`. (REQ-3)
- **AC-6** - With real SQLcl, `connmgr show` in the target reports the copied password as saved, and `connmgr list` shows the copy in the source folder path. (REQ-2, REQ-3)
- **AC-7** - A name that exists in the target in any letter case gives `[FAIL]`. The other connections are copied, the exit code is 1, and the existing target connection is unchanged. (REQ-4)
- **AC-8** - The same home for `--home` and `--to-home` exits with code 1 with nothing written. A duplicate-name batch selection exits with code 1 with nothing copied. An unknown `--name` exits with code 1. (REQ-5)
- **AC-9** - `README.md` and `SKILL.md` document `copy` as listed in REQ-6, contain no move tip, and `markdownlint-cli2` reports no errors for them. (REQ-6)
- **AC-10** - `pyproject.toml` and `uv.lock` carry 0.6.0, and the globally installed `sqlcl-conn-mng --version` prints 0.6.0. (REQ-7)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| `src/sqlcl_conn_mng/store.py` | Update |
| `src/sqlcl_conn_mng/cli.py` | Update |
| `tests/test_store.py` | Update |
| `tests/test_cli.py` | Update |
| `tests/integration/test_copy_compat.py` | Create |
| `README.md` | Update |
| `.claude/skills/sqlcl-conn-mng/SKILL.md` | Update |
| `pyproject.toml` | Update |
| `uv.lock` | Update |
