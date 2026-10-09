# Open Questions: Update Command For Saved Connections

## Q1: How does `update` write the change?

- **Why it matters**: the README states the tool never writes the store from Python; SQLcl is the only supported writer. SQLcl has no `connmgr update`, so the mechanism sets the whole design.
- **Options**: (a) everything through SQLcl (`connect -save -replace`, `connmgr rename`); (b) name, user and connect string written to `dbtools.properties` from Python, password through `connect -save NAME -replace`.
- **Recommended**: (a) for the password; for metadata (a) cannot change a user or URL without a connect and a password, so (b).
- **Answer**: (b) - decided by user (Q3 and Q10). The password stays with SQLcl because `credentials.sso` is never written from Python. Feasibility of a Python `dbtools.properties` writer is shown by `docs/tasks/sqlcl_jar_store_investigation/findings.md`, "Properties Round Trip": SQLcl listed and showed files written by a Python prototype.

## Q2: Does `connect -save -replace` with a changed user or connect string touch `dbtools.properties` or the folder, and does a failed connect leave the old connection intact?

- **Why it matters**: the captured evidence covers `-replace` with unchanged user and connect string only (findings.md, "Effects per Operation"). The step order in Phase 3 depends on the outcome.
- **Options**: (a) probe it with real SQLcl in a discovery phase; (b) assume.
- **Recommended**: (a) - observable with the integration harness; a wrong assumption would ship a command that reports success without the stored values changing.
- **Answer**: probed in Phase 1 with SQLcl 25.4.1.022.0618 against the Oracle XE container, in a temporary store, using the tool's own `save_connection` (`connect -save NAME -savepwd [-replace] -password <hidden> user@connect`). Observed:
  - `-replace` with a changed user (`itest` to `ITEST`) rewrote `userName` in `dbtools.properties`; the id, the folder placement in `folders.json` and the saved wallet stayed.
  - `-replace` with a changed connect string (`//localhost:1521/XEPDB1` to `localhost:1521/XEPDB1`) rewrote `connectionString` the same way; id and folder stayed.
  - The key order after the rewrites is `name`, `type`, `connectionString`, `userName`, the order SQLcl uses for a new connection.
  - A connect that fails (unknown user) exits with a SQLcl error in the tool and leaves `dbtools.properties`, `folders.json` and the wallet as they were.
  - Conclusion: the Phase 3 order holds. The password step already writes the new user and connect string, so the later file write for those two keys is idempotent; it is still required for `--new-name` and for metadata-only updates.

## Q3: Is a password required when the user or the connect string changes?

- **Why it matters**: the tool never reads `credentials.sso`, and a metadata-only change needs no connect.
- **Options**: (a) required, change saved only after a successful connect; (b) not required, the change is written without a connect.
- **Recommended**: (a) for safety.
- **Answer**: (b) - decided by user. A user or connect-string change without a password source is written to `dbtools.properties` with no connect and no validation against the database.

## Q4: What happens to the saved-password state when a password is given?

- **Why it matters**: `-replace` without `-savepwd` drops the saved password, `-replace -savepwd` stores it.
- **Options**: (a) mirror `add`: save by default, `--no-save-password` drops it; (b) keep the prior state.
- **Recommended**: (b) least surprising; (a) simpler.
- **Answer**: (a) mirror `add` - decided by user. Without a password source the wallet is not touched.

## Q5: How is a password change requested?

- **Why it matters**: a user or URL change without a password source must not prompt.
- **Options**: (a) `--password-env VAR` or `--prompt-password`, either one means "change the password"; (b) always prompt when no other option is given.
- **Recommended**: (a).
- **Answer**: (a) - decided by user. The two flags are mutually exclusive.

## Q6: What is the step order, and what if a step fails?

- **Why it matters**: a combined change is a SQLcl call plus a file write and cannot be atomic.
- **Options**: (a) validate everything first, run `connect -replace` (changes nothing when the connect fails), then write `dbtools.properties`, and on a write failure report that the credentials were already replaced; (b) write the file first.
- **Recommended**: (a).
- **Answer**: (a), conditional on Q2 - decided by reading `src/sqlcl_conn_mng/sqlcl.py` (`save_connection` saves only after a successful connect).

## Q7: Single connection or batch?

- **Why it matters**: sets whether `update` uses `_add_selector`.
- **Options**: (a) `--name` only; (b) `--name` / `--filter` / `--all`.
- **Recommended**: (a) - a password, a new name and a user are per-connection values.
- **Answer**: (a) - decided by reading `docs/tasks/batch_all_filter/open_questions.md`, Q1, which excluded `rename` and `clone` for the same reason.

## Q8: Does `rename` stay?

- **Why it matters**: `update --new-name` alone duplicates `rename`.
- **Options**: (a) keep `rename` unchanged; (b) remove it.
- **Recommended**: (a) - removing a command is a breaking change nobody asked for.
- **Answer**: (a) - decided by the request, which names only `update`.

## Q9: Is a version bump required?

- **Why it matters**: a new command adds input parameters.
- **Options**: (a) bump minor `0.3.0` to `0.4.0`; (b) no bump.
- **Recommended**: (a) - no `upstream` remote, git user `s2005`, additive change.
- **Answer**: (a) - decided by the version-bump rule in the global CLAUDE.md and `pyproject.toml` line 7.

## Q10: Which keys does the Python writer change?

- **Why it matters**: bounds the new Python write path.
- **Options**: (a) `userName` and `connectionString` only, name stays with `connmgr rename`; (b) also `name`.
- **Recommended**: (a) - SQLcl's own rename has case-insensitive lookup defects, but it also keeps the folder lists consistent.
- **Answer**: (b) - decided by user. `name`, `userName` and `connectionString` are written by Python; the id, the other keys and their order, `folders.json` and the wallet are untouched (folders.json references ids, not names).

## Q11: What happens to a saved password that no longer matches a changed user or URL?

- **Why it matters**: without a password source the wallet cannot be cleared.
- **Options**: (a) warn and continue; (b) refuse when a password is saved; (c) silent.
- **Recommended**: (a).
- **Answer**: (c) silent - decided by user. The README documents the caveat; the command prints no warning.

## Q12: How is a new name checked for collisions?

- **Why it matters**: a Python write bypasses SQLcl's own check, and SQLcl looks names up case-insensitively in `rename` and `delete -folder -force`.
- **Options**: (a) refuse a new name equal to another connection's name, compared case-insensitively; (b) refuse exact matches only.
- **Recommended**: (a) - findings.md, "Case-Insensitive Lookup Defects", advises refusing an ambiguous lookup rather than reproducing it.
- **Answer**: (a) - decided by reading `docs/tasks/sqlcl_jar_store_investigation/findings.md`. The connection being updated is excluded from the comparison, so a case-only rename of itself is allowed.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | REQ-2, REQ-3 |
| Q2 | Answered | Phase 1 (discovery) |
| Q3 | Answered | REQ-2 |
| Q4 | Answered | REQ-3 |
| Q5 | Answered | REQ-1, REQ-3 |
| Q6 | Answered | REQ-4 |
| Q7 | Answered | REQ-1 |
| Q8 | Answered | Non-Requirements |
| Q9 | Answered | REQ-6 |
| Q10 | Answered | REQ-2 |
| Q11 | Answered | REQ-2, REQ-6 |
| Q12 | Answered | REQ-4 |
