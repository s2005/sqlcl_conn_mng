# Open Questions: Folder Selection For test

## Q1: How does --folder combine with the existing test selectors?

- **Why it matters**: decides which option sets are valid, which are usage errors (exit 2), and whether a bare `test` still refuses to run.
- **Options**: (a) `--folder` joins the selector set: exactly one of `--name`, `--all`, or a folder/filter selection (`--folder`, `--filter`, or both, ANDed as in `list`); `--name` and `--all` stay exclusive with everything else, and a bare `test` stays exit 2; (b) full `list` parity: every selector optional, a bare `test` tests every connection, `--all` kept as an alias; (c) `--folder` only narrows `--all` or `--filter` and is never a selector on its own.
- **Recommended**: (a) - it gives `test --folder /dev/local` and `test --folder /dev --filter 'x_*'` exactly as `list` reads them, while keeping the current guard that a bare `test` does not start SQLcl against every saved connection. (b) changes the meaning of an existing invocation; (c) makes the common case (`--folder` alone) need a redundant `--all`.
- **Answer**: (a) `--folder` joins the selectors; `--folder` and `--filter` combine as AND; `--name` or `--all` with `--folder` is exit 2; a bare `test` stays exit 2 - decided by user.

## Q2: Which commands get --folder selection?

- **Why it matters**: `show`, `delete` and `move` share `_add_selector` with `test` (`src/sqlcl_conn_mng/cli.py:42`), so the change could reach them with little code.
- **Options**: (a) `test` only; (b) `test` and `show` (both non-destructive); (c) `test`, `show`, `delete`; `move` already uses `--folder` as its destination, so it cannot take it as a selector.
- **Recommended**: (a) - the request names `test`; extending a selector to `delete` changes a destructive command and needs its own decision. The others go to Non-Requirements as a follow-up.
- **Answer**: (a) `test` only; `show`, `delete` go to Non-Requirements - decided by user.

## Q3: What does --folder match?

- **Why it matters**: "this folder" versus "this folder or below" changes which connections are tested.
- **Options**: (a) the folder and every subfolder, through the same `_in_folder` helper `list` uses; (b) the folder only.
- **Recommended**: (a) - the request asks for the `list` style, and reusing the helper keeps the two commands in step.
- **Answer**: (a) reuse `_in_folder` - decided by reading `src/sqlcl_conn_mng/cli.py:307` and `:432`.

## Q4: What happens when the folder selection matches nothing, including a folder that does not exist?

- **Why it matters**: scripts rely on the exit code; a typo in the folder must not look like success.
- **Options**: (a) the existing empty-batch error, exit 1, with the message naming every selector given, e.g. `No connections match --folder '/dev' --filter 'x_*'`; (b) a separate "folder does not exist" check before matching.
- **Recommended**: (a) - it reuses `_require_matches` and the JSON error envelope unchanged; (b) adds a second error path for the same outcome.
- **Answer**: (a) the existing empty-batch error, exit 1, message naming every selector given - decided by user.

## Q5: Is a version bump required, and which?

- **Why it matters**: the CLAUDE.md version rule applies to a new input option.
- **Options**: (a) minor, 0.5.0 to 0.6.0; (b) patch.
- **Recommended**: (a) - an additive option on a 0.x version is a minor bump.
- **Answer**: (a) 0.6.0, with `uv lock` - decided by reading `pyproject.toml` (version 0.5.0), `git remote get-url origin` (owner s2005) and `gh repo view --json isFork` (false).

## Q6: Which documents change?

- **Why it matters**: an undocumented option is treated as a bug.
- **Options**: (a) `README.md` (command table, Batch selection, JSON output, Examples) and `.claude/skills/sqlcl-conn-mng/SKILL.md` (command table, selector paragraph, minimum version); (b) `README.md` only.
- **Recommended**: (a) - commit 8d4e232 set the precedent of keeping the skill in step with the CLI and its minimum version.
- **Answer**: (a) - decided by reading commit 8d4e232 and `.claude/skills/sqlcl-conn-mng/SKILL.md:27`.

## Q7: Is the `--folder /` behaviour fixed in this task, and what should it mean?

- **Why it matters**: `_in_folder` (`src/sqlcl_conn_mng/cli.py:307`) builds `wanted = "/"` for `--folder /` and then looks for subfolders under `//`, so `list --folder /` returns only root-level connections, while the help says "this folder or below". `test --folder` reuses the helper and inherits the gap.
- **Options**: (a) fix it here in its own phase: `--folder /` (and any value that strips to empty, such as `///`) matches every connection, as "the root or below"; (b) keep the current root-only result and document it; (c) separate task.
- **Recommended**: (a) - it is the behaviour the help text already promises, and `test --folder /` should not silently skip every foldered connection.
- **Answer**: (b) keep today's behaviour: `--folder /` selects only root-level connections, for `list` and for the new `test --folder`. Redefining `/` would silently change what existing `list --folder /` callers get. A way to select the root and everything below, if wanted, is a separate option in a separate task. A first choice of (a) was reversed by the user before implementation - decided by user.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | REQ-1, REQ-2 |
| Q2 | Answered | Non-Requirements |
| Q3 | Answered | REQ-1 |
| Q4 | Answered | REQ-3 |
| Q5 | Answered | REQ-5 |
| Q6 | Answered | REQ-6 |
| Q7 | Answered | REQ-8, Non-Requirements |
