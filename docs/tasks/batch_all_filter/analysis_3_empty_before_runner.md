# Analysis 3 - Empty batch reported before SQLcl lookup

## Decision: Valid — fix applied

`_cmd_move` and `_cmd_test` call `_require_matches` for a batch selection before `_runner`, as `_cmd_delete` already did.

**Why:** an empty selection needs no SQLcl action, and the PRD (REQ-4, AC-6) specifies the `No connections match` message for it.

**Commit:** 73c0bc2 - fix(cli): list duplicate records in plain show; report empty batch before SQLcl lookup (PR #3 review)
