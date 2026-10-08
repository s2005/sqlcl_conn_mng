# Solution 01: Amend the Plan and Compare Three Runtimes on Paper

## Chosen Approach

Phase 7 costs three runtimes from documented facts and the Phase 2 to 6 evidence, with no hands-on JRE proof:

- pure Python;
- Python plus a JRE and the Maven Central `oraclepki` jar;
- Python plus SQLcl, used only for the operations that write or read a saved password.

It ends with one recommendation that respects both of the user's decisions of 2026-10-08: no third-party libraries, and no plain-text passwords.

## Why It Beats the Alternatives

- **Over 02 (follow the plan literally)**: 02 proves a route the user has excluded, and brings a third-party jar into the experiments without changing any decision. 01 still records that route's coordinates, licence and footprint, so it can be reconsidered later.
- **Over 03 (drop Phase 7)**: 03 leaves REQ-7 and AC-7 unmet. 01 meets them, with one table and one recommendation.

## Drifts Resolved

- **D1**: the hands-on JRE proof is marked `[-]` (not applicable) in `progress.md`, with the reason.
- **D2**: the comparison gains the runtime the follow-up will actually use for password writes.
- **D3**: the skipped decompilation escalation is recorded in `open_questions.md` under Q1.

## Files to Change

| File | Change |
| ---- | ------ |
| `open_questions.md` | Q1, Q2 and Q3 outcomes; a new Q10 on plain-text passwords, answered by the user |
| `findings.md` | "Runtime Comparison" section |
| `progress.md` | Phase 6 closed with its blocker; Phase 7 items, with the hands-on item `[-]` |
| `verification.md` | AC-6 and AC-7 ticked once their checks pass |

## Implementation Outline

1. Record the decisions in `open_questions.md`.
2. Close Phase 6, since its verdict line names the blocker and the alternatives.
3. Write the Phase 7 comparison from documented facts: Maven Central metadata for `oraclepki`, the measured size of the SQLcl install, and the Phase 2 to 6 evidence for which operations each runtime covers.
4. End with one recommendation.

## Verification

- `findings.md` has a "Runtime Comparison" table with all three runtimes and every column filled, followed by one recommendation.
- `markdownlint-cli2 "docs/**/*.md"` from `<repo-root>` is clean.
