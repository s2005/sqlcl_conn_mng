# Analysis 1 - Emit the save confirmation before attempting the move

## Decision: Valid — fix applied

`_cmd_add` now prints the save line and then the move result separately in table mode, so the line is on stdout even when the move raises. JSON mode still builds one document after the move, so a failing move yields the error object only.

**Why:** REQ-2 requires table output to be unchanged, including the partial-success case of a failed move after a successful save.

**Commit:** 26324d1 - fix(cli): print add save line before the folder move (PR #5 review)
