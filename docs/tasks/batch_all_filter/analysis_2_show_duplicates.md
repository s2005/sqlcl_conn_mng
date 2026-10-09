# Analysis 2 - Plain show with duplicate names

## Decision: Valid — fix applied

Selection now resolves to `SavedConnection` records (`_select_connections`). Name-based actions (`test`, `move`, `delete`, and `show --check-password`) still reject duplicate names through `_reject_duplicate_names`; plain `show` iterates the records and lists every duplicate with its own id.

**Why:** the guard from analysis 1 was needed only where SQLcl is addressed by name. Metadata `show` never calls SQLcl, so refusing it removed a safe read-only capability for no benefit.

**Commit:** 73c0bc2 - fix(cli): list duplicate records in plain show; report empty batch before SQLcl lookup (PR #3 review)
