# Analysis 1 - Derive the current target for imported connections

## Decision: Valid — fix applied

A password-only update on an imported `ORACLE_BASIC` connection passed an empty connect string to SQLcl. `_cmd_update` now builds the current target as `//host:port/serviceName` (port omitted when absent) from the connection's `host`, `port` and `serviceName` keys, and refuses with a clear error, before any prompt or SQLcl call, when `host` or `serviceName` is missing.

**Why:** the reviewer is right: `SavedConnection.connect_string` is empty for imported connections (`notes.md`, D1; `open_questions.md`, Q13), and `save_connection` validates it as non-empty. The easy connect form is the one SQLcl accepted in the Phase 1 replace probe, and after the replace SQLcl itself rewrites the file as `ORACLE_DATABASE`.

**Commit:** 2add451 - fix(cli): derive the current target of imported connections for password updates (PR #4 review)
