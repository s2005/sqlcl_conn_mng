# Analysis 2 - Validate unsupported types before replacing credentials

## Decision: Valid — fix applied

`_update_changes` in `cli.py` now refuses `--connect-string` for any connection type outside `ORACLE_DATABASE` and `ORACLE_BASIC` before the password step, whatever the password source, so nothing is written or reconnected for a refused type (exit 1). The guard in `ConnectionStore.update_properties` stays as a second line of defence for the metadata-only path and other callers.

**Why:** the reviewer is right and the gap was already noted after the first review round. The PRD (REQ-4) requires every validation to run before any write, and the password step is a write. SQLcl's own rewrite of an unsupported type is unverified, so refusing up front is the safe behavior.

**Commit:** 5fe5fab - fix(cli): refuse unsupported connection types before the password step (PR #4 review)
