# Analysis 1 - Keep required CI checks reportable for docs-only PRs

## Decision: Rejected - no required status checks exist on `main`

The concern is conditional on `checks` being a required status check. It is not: `gh api repos/s2005/sqlcl_conn_mng/branches/main --jq .protected` prints `false`, and `gh api repos/s2005/sqlcl_conn_mng/rulesets` returns an empty list. With nothing required, a skipped CI workflow leaves no pending check and does not block a merge. No code change was made.

**Why:** Issue #10 names this exact case as a point to settle and states the trigger for the alternative: add a no-op job for docs-only changes only if `checks` becomes required. The PR description records the same boundary. Replacing `paths-ignore` with a conditional-skip job now would guard against a repository rule that does not exist, which is outside the scope of #10.
