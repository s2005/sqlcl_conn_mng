# Progress - CI skip for docs-only changes (issue #10)

- [x] `ci.yml` ignores `docs/**` and `**/*.md` on `pull_request` and `push`
- [x] `docs.yml` lints Markdown on docs-only changes
- [x] README CI section updated

## Review Feedback (PR #12)

- [-] P1: Keep required CI checks reportable for docs-only PRs (rejected - `main` has no branch protection or rulesets, so no required check is left pending)
