# Open Questions: Batch Selection With --all And --filter

## Q1: Which commands accept --all and --filter?

- **Why it matters**: sets the scope of the change; every command added needs code, tests and README rows.
- **Options**: (a) `test`, `show`, `delete`, `move`, `export` plus `list` (filter only); (b) `test` only; (c) every command that takes `--name`, including `rename` and `clone`.
- **Recommended**: (a) - these act on one existing connection with no per-item argument. `rename` and `clone` need a distinct `--new-name` per connection, so a batch form has no sensible meaning. `add`, `folders`, `add-folder` and `delete-folder` do not select connections.
- **Answer**: (a) `test`, `show`, `delete`, `move` take `--name`, `--filter` or `--all`; `list` and `export` take `--filter` only (they already cover every connection by default, so `--all` would be a no-op) - decided by user; the list/export `--filter`-only detail by reading `src/sqlcl_conn_mng/cli.py` lines 110-114 and 196-200.

## Q2: What does --filter match, and how?

- **Why it matters**: defines the user-visible matching contract.
- **Options**: (a) shell-style glob (`fnmatch`) on the connection name, case-sensitive; (b) case-insensitive substring; (c) regular expression.
- **Recommended**: (a) - familiar, no regex escaping, and `--name` is already case-sensitive. Combined with `--folder` where a command has it (AND).
- **Answer**: (a) shell-style glob, case-sensitive, on the connection name - decided by user.

## Q3: How do --name, --all and --filter relate?

- **Why it matters**: decides whether `--name` stays required and what combinations are usage errors.
- **Options**: (a) exactly one of `--name`, `--filter`, `--all` is required (mutually exclusive); (b) `--all` selects everything and `--filter` narrows it; `--filter` alone also works; (c) `--filter` requires `--all`.
- **Recommended**: (a) - one unambiguous selector per call, enforced by an argparse mutually exclusive group. `--filter '*'` equals `--all`.
- **Answer**: (a) exactly one of `--name`, `--filter`, `--all` on `test`, `show`, `delete`, `move` - decided by user.

## Q4: How are failures and empty matches reported in a batch?

- **Why it matters**: sets exit codes and output, which scripts depend on.
- **Options**: (a) process every match, print one result line per connection and a summary, exit 1 if any failed or nothing matched; (b) stop at the first failure; (c) always exit 0.
- **Recommended**: (a) - a bulk `test` must report all broken connections, not only the first. Zero matches is an error so a mistyped filter is not silent success.
- **Answer**: (a) continue through all matches, one result line each, a summary, exit 1 on any failure or zero matches - decided by user.

## Q5: How is the destructive `delete --all` / `--filter` guarded?

- **Why it matters**: bulk deletion is irreversible.
- **Options**: (a) keep the existing `--yes` requirement and list the matched names before deleting; (b) add a `--dry-run`; (c) require `--yes` plus an extra confirmation flag.
- **Recommended**: (a) - reuses the current guard; `--dry-run` is a separate improvement and out of scope.
- **Answer**: (a) keep `--yes`, list matched names before deleting, no `--dry-run` - decided by user.

## Q6: Is a version bump required?

- **Why it matters**: input parameters change.
- **Options**: (a) bump minor `0.2.1` to `0.3.0`; (b) no bump.
- **Recommended**: (a) - `git remote` is `s2005/sqlcl_conn_mng`, no `upstream` remote, user `s2005`; the change is additive.
- **Answer**: (a) - decided by the version-bump rule in the global CLAUDE.md and `pyproject.toml` line 7.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | REQ-1, REQ-6 |
| Q2 | Answered | REQ-2 |
| Q3 | Answered | REQ-1 |
| Q4 | Answered | REQ-4 |
| Q5 | Answered | REQ-5 |
| Q6 | Answered | REQ-8 |
