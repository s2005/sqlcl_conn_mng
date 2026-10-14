# Solution 01: Amend the spec and bump the patch version

## Approach

Replace the PRD non-requirement "No version bump" with a requirement (REQ-5) that bumps the patch version from 0.9.2 to 0.9.3 in Phase 3.

## Why it beats 02

The project rule is that every bug-fix PR bumps the patch version. Solution 02 leaves the fixed release indistinguishable from the defective one.

## Resolves

D1.

## Files

- `PRD.md`
- `implementation_plan.md`
- `verification.md`
- `progress.md`
- `pyproject.toml`
- `uv.lock`

## Outline

1. Amend the PRD: drop the no-bump line, add REQ-5 and AC-7, add `pyproject.toml` and `uv.lock` to Deliverables.
2. Add the bump to Phase 3 in the plan, verification and progress files.
3. In Phase 3, set `version = "0.9.3"` in `pyproject.toml` and run `uv lock`.

## Verification

`uv run sqlcl-conn-mng --version` prints 0.9.3.
