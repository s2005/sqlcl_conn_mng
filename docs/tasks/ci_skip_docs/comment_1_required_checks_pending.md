# P1 - Keep required CI checks reportable for docs-only PRs

`.github/workflows/ci.yml:8`: if `checks (ubuntu-latest)` or `checks (windows-latest)` is a required status check, a docs-only PR skips the path-filtered CI workflow, the required checks stay pending and the PR cannot merge; Codex suggests keeping CI triggered and skipping the expensive steps conditionally, or updating the repository rules together with this change.
