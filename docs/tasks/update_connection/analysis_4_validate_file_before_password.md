# Analysis 4 - Validate the properties file before replacing the password

## Decision: Valid — fix applied

`ConnectionStore.check_rewritable` now performs the file checks (file exists, no comment or continuation line) and `_cmd_update` calls it, whenever a file change is requested, before the password step. `update_properties` reuses it. A password-only update never rewrites the file and is not affected.

**Why:** REQ-4 requires every validation to run before any write, and the password step is a write that cannot be undone. Same class as analysis 2.

**Commit:** 53ab73a - fix(cli): refuse an unwritable properties file before the password step (PR #4 review)
