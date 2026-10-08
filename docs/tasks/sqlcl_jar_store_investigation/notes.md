# Notes: Spec Drift Found During Phase 6

Phase 6 ended with the pure-Python wallet blocked, and on 2026-10-08 the user ruled out both third-party libraries and plain-text password storage. Parts of the task specification no longer match the decisions in force.

## Drifts

### D1: Hands-on proof of the JRE route

- **Spec**: `implementation_plan.md`, Phase 7, line 169: if Phase 6 was blocked, the JRE option is "costed as the primary path and checked hands-on". The same requirement appears in `progress.md` line 107 ("Prove the JRE call sequence hands-on if Phase 6 was blocked") and `verification.md` line 119.
- **Decision**: the user requires SQLcl-free saving "without using 3rd party libs". The Maven Central `oraclepki` jar is a third-party library, licensed under the Oracle Free Use Terms and Conditions.
- **Difference**: the plan would build and prove a route that the follow-up is not allowed to use.

### D2: Runtimes to compare

- **Spec**: `PRD.md`, REQ-7, line 62: compare "pure Python, and Python plus a JRE calling the `oraclepki` jar".
- **Decision**: plain-text passwords are rejected because they break security. The only route left for saving a password is the one in use today: run SQLcl for that operation.
- **Difference**: the runtime the follow-up will actually use for password writes, Python plus SQLcl, is not one of the two runtimes REQ-7 names.

### D3: Wallet POC exit criterion

- **Spec**: `PRD.md`, REQ-6, and `implementation_plan.md`, Phase 6: the phase ends with a Python-written wallet accepted by SQLcl, or with a named blocker.
- **Decision**: the investigation does not reverse-engineer the obfuscation that protects Oracle's auto-login wallet, so no wallet is written from Python. The `open_questions.md` Q1 escalation gate (local decompilation) was not taken.
- **Difference**: none in outcome, since the blocker exit applies. The escalation step in the plan was skipped deliberately, and that is recorded here so it does not look like an omission.

## Candidate Solutions

### 01: Amend the plan; compare three runtimes on paper

- **Approach**: in Phase 7, cost three runtimes from documented facts, with no hands-on JRE proof: pure Python; Python plus a JRE and `oraclepki`; Python plus SQLcl for the password operations only. Recommend the combination that satisfies the user's constraints. Record D1 to D3 in `open_questions.md` and mark the hands-on item `[-]` in `progress.md`.
- **Scope**: `findings.md`, `open_questions.md`, `progress.md`; no code.
- **Pros**: matches the user's decisions; still meets REQ-7 and AC-7 (a full table and one recommendation); the JRE route stays documented for a future reconsideration.
- **Cons**: the JRE facts are not proven hands-on.
- **Risk**: low; the JRE route is not going to be used.

### 02: Follow the plan literally

- **Approach**: download `oraclepki`, prove create-wallet, add-secret and read-secret-presence in `<scratch-root>/poc/`, then compare.
- **Scope**: scratch-only Java or JShell code, plus a downloaded third-party jar.
- **Pros**: the plan is followed to the letter.
- **Cons**: it builds a route the user has excluded, and it brings a third-party library into the experiments for no decision value.
- **Risk**: medium; wasted work, and it could be mistaken for a recommendation.

### 03: Drop Phase 7

- **Approach**: skip the runtime comparison, because the user's constraints already decide it.
- **Scope**: `progress.md` only.
- **Pros**: least work.
- **Cons**: it fails REQ-7 and AC-7, and leaves the follow-up without the costed alternatives.
- **Risk**: high; an acceptance criterion would be left unmet.
