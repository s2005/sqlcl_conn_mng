# Version 0.6.0 Is Also Claimed By PR 8

## Finding

Open PR 8 (`feat/copy-between-homes`) also sets `pyproject.toml` to `version = "0.6.0"`. This task (PR 9) bumps 0.5.0 to 0.6.0 as REQ-5 requires. Whichever PR merges second will ship its new option under a version number that already names a different feature set.

## Evidence

- `git show feat/copy-between-homes:pyproject.toml` prints `version = "0.6.0"`.
- `pyproject.toml` on this branch: `version = "0.6.0"` (commit 5d88286).
- PRD REQ-5, open_questions.md Q5.

## Effect

Two different releases would share the version 0.6.0, and the `SKILL.md` minimum-version sentence ("0.6.0 or newer for `test --folder`") would be wrong for the build of the PR that merges first. The global `uv tool` copy was reinstalled from this worktree, so it no longer contains PR 8's changes.

## Status

Open.

## Next step

After the first of PR 8 and PR 9 merges, rebase the other PR, bump it to 0.7.0, run `uv lock`, and update its `SKILL.md` minimum version.
