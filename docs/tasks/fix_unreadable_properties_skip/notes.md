# Notes: Skip Unreadable Connection Properties

## Drifts

### D1: Spec forbids a version bump, project rule requires one

- **Spec ref**: `PRD.md`, "Non-Requirements" ("No version bump: no input parameter changes").
- **Code ref**: `pyproject.toml:7` (`version = "0.9.2"`).
- **Difference**: the spec forbids a bump. The project rule is that a change to code under `src/` bumps the version (patch for a fix; repo history #16, #18 and #19 each did), while docs-only changes do not. This task changes `src/sqlcl_conn_mng/store.py`, so the bump applies.

## Candidate solutions

### 01: Amend the spec and bump the patch version

- **Approach**: remove the no-bump line from the PRD, add REQ-5 and AC-7, and bump `0.9.2` to `0.9.3` in Phase 3.
- **Scope**: `PRD.md`, `implementation_plan.md`, `verification.md`, `progress.md`, `pyproject.toml`, `uv.lock`.
- **Pros**: follows the project rule; the fixed release is identifiable.
- **Cons**: the task grows by one small deliverable.
- **Risk**: low; a version number change only.

### 02: Keep the spec, no bump

- **Approach**: leave the PRD as written and ship without a version change.
- **Scope**: none.
- **Pros**: no extra work.
- **Cons**: breaks the project rule (code changed, no bump); the fixed release is indistinguishable from the defective one.
- **Risk**: medium; users cannot tell whether they have the fix.
