# Analysis 3 - Resolve TNS targets for password-only updates

## Decision: Deferred — unsupported type, fails safely

A password-only update on an `ORACLE_TNS` connection already fails with a clear error before the password prompt and before any SQLcl call, so no credential changes. Supporting TNS aliases would need a verified SQLcl form for reconnecting by alias, which this task never observed.

**Why:** only `ORACLE_DATABASE` and `ORACLE_BASIC` were observed (`notes.md`, D1; `open_questions.md`, Q13). New connection types are new behavior; the scope rule asks for a separate ticket. The failure is safe and explicit, so nothing is made worse by leaving it.
