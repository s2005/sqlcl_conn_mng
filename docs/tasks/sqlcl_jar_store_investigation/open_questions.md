# Open Questions: Investigate SQLcl Store Writes for SQLcl-Free Catalog Management

Context gathered before writing this file:

- Every write command (`add`, `delete`, `rename`, `move`, `clone`, `add-folder`, `delete-folder`) and `show --check-password` run SQLcl today (`src/sqlcl_conn_mng/sqlcl.py`). Only the read path (`src/sqlcl_conn_mng/store.py`) works without SQLcl.
- The installed SQLcl is 25.4.1. The classes that matter sit in four jars of its `lib` folder:

| Jar | Classes of interest |
| --- | ------------------- |
| `dbtools-sqlcl.jar` | `oracle.dbtools.plusplus.connections.db.ConnectionStoreCommand`, `ConnectionStoreOptions` (the `connmgr` command) |
| `dbtools-core.jar` | `oracle.dbtools.core.connections.storage.ConnectionStorage`, `oracle.dbtools.core.connections.folder.*` |
| `dbtools-common.jar` | `oracle.dbtools.common.utils.WalletUtils`, `oracle.dbtools.db.ConnectionStoreBridge`, the `connect -save` command classes |
| `oraclepki.jar` | `oracle.security.pki.OracleFileSSOWalletImpl`, `OracleSecretStore` (the `credentials.sso` auto-login wallet) |

- A JDK 17 with `javap` and `jar` is installed, so class signatures and constants can be read without extra tools.
- SQLcl's `LICENSE.txt` says the product is licensed under the Oracle Free Use Terms and Conditions and points at the online text; the local file carries no clause about reverse engineering.

## Q1: How deep may the jar inspection go?

- **Why it matters**: decides which techniques the investigation phases use and whether any finding can be reused as code. Decompiled Oracle code must never land in this MIT repository.
- **Options**: (a) clean-room: black-box observation of the store before and after each SQLcl command, plus `javap -p` signatures and `javap -constants` string constants; no method bodies. (b) Full local decompilation (CFR or similar) in the scratch directory, never committed, with findings written as prose specifications only. (c) Black-box observation only, no jar inspection.
- **Recommended**: (a), escalating to (b) only for a gap (a) cannot close and only after you have checked the Oracle Free Use Terms and Conditions yourself - why: (a) answers most format questions with no licence exposure, and the request explicitly asks what the jars do, which rules out (c).
- **Answer**: (a) clean-room first; local decompilation in the scratch directory only for a gap (a) cannot close, and only after the user confirms the licence allows it - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.
- **Outcome (Phase 6, first pass, superseded)**: the escalation to (b) was not taken. The one gap (a) could not close is the obfuscation of the auto-login wallet. The investigation does not reverse-engineer it, by decompilation or otherwise, so `[decompile]` evidence does not occur in `findings.md` (`notes.md`, D3).
- **Renewed outcome (2026-10-08)**: the escalation to (b) was still not taken. The wallet format was worked out from public research, cryptographic standards, `javap` signatures and black-box structure probes of dummy wallets, without decompiling any Oracle method body. The gap is closed, `[decompile]` evidence still does not occur in `findings.md`, and the new evidence carries the `[structure]` and `[standard]` tags (`findings.md`, "credentials.sso"; `notes.md`, D5; `solution_04.md`).

## Q2: Is writing `credentials.sso` from Python in scope for the investigation?

- **Why it matters**: the wallet is the hard part. `dbtools.properties` and `folders.json` are plain text; `credentials.sso` is an obfuscated Oracle auto-login wallet that exists even when no password is saved. Without it a SQLcl-free `add` or `clone` cannot produce a store SQLcl accepts.
- **Options**: (a) full: document the SSO wallet layout well enough to create an empty wallet, add or replace the password secret, read whether a secret is present, and copy it on clone. (b) partial: only how to create an empty wallet and detect whether a password secret exists; saving a password still needs SQLcl. (c) none: metadata files only; any operation that touches the wallet keeps needing SQLcl.
- **Recommended**: (a), run as its own phase with a feasibility exit (stop and record the blocker if the format cannot be reproduced) - why: without it the user goal is only half met, and the phase boundary keeps a failure from blocking the metadata findings.
- **Answer**: (a) full, in its own phase with a feasibility exit - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.
- **Outcome (Phase 6, first pass, superseded)**: the feasibility exit was taken; writing a wallet from Python is blocked. What works without wallet bytes: a connection without a saved password needs no `credentials.sso` at all, and clone, rename, move and delete only copy or leave the existing wallet (`findings.md`, "credentials.sso").
- **Renewed outcome (2026-10-08)**: the blocker is superseded. A standard-library Python writer generated an empty wallet and two password wallets; SQLcl 25.4.1 showed the expected password state for each and logged in by saved name with both password wallets (`findings.md`, "credentials.sso"; "Renewed Investigation Outcome" below).

## Q3: What runtime may the future SQLcl-free implementation assume?

- **Why it matters**: if a JRE is acceptable, the wallet can be written by calling `oraclepki.jar` (also published on Maven Central) instead of reproducing its format, and the investigation focuses on API calls rather than byte layout.
- **Options**: (a) pure Python, no Java and no Oracle jars. (b) Python plus a JRE and the Maven Central `oraclepki` jar, used only for wallet operations. (c) investigate both and compare.
- **Recommended**: (c) - why: (a) is the stated goal, but (b) is the fallback if Q2 hits a wall, and knowing its cost up front avoids a second investigation.
- **Answer**: (c) investigate both, pure Python as the target and Python + JRE + Maven Central `oraclepki` as the costed fallback - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.
- **Revised answer (user, 2026-10-08, after Phase 6)**: (a). Saving must work "without using 3rd party libs", so the `oraclepki` route is costed on paper only and not adopted. Python plus SQLcl, used for password operations only, is added to the comparison (`notes.md`, D1 and D2; `solution_01.md`).

## Q4: One task with a phase per area, or several task folders?

- **Why it matters**: shapes how progress is tracked and reviewed.
- **Options**: (a) one investigation task (this folder) with a phase per area: harness, ids, `dbtools.properties`, `folders.json`, each `connmgr` operation, wallet, runtime comparison, synthesis. (b) one task folder per area, created now.
- **Recommended**: (a), with the final phase drafting the follow-up implementation task(s) from the findings - why: the areas share one harness and one findings document, and implementation tasks are better sized once the findings exist.
- **Answer**: (a) one task with a phase per area; the synthesis phase drafts the follow-up implementation task(s) - recommended default adopted on 2026-10-08 because the question went unanswered; reversible, revisit before Phase 1 starts if you disagree.

## Q5: Is `connmgr test` and the connect-before-save check in scope?

- **Why it matters**: SQLcl's `connect -save` saves only after a successful connection. A SQLcl-free `add` loses that check unless a database driver replaces it.
- **Options**: (a) out of scope: the request is about managing the catalog, not connectivity. (b) in scope: also investigate python-oracledb as a replacement for `test` and the save-time check.
- **Recommended**: (a) - why: connectivity needs a driver, not store knowledge; it becomes a follow-up note.
- **Answer**: (a) - decided by reading the request ("managing catalog of saved connections"); recorded as a follow-up in the synthesis phase.

## Q6: Which store and which passwords do the experiments use?

- **Why it matters**: the experiments write to a store and inspect wallet bytes.
- **Options**: (a) a throwaway store in the session scratch directory, passed with `-home`, with dummy passwords only. (b) `<repo-root>/.sqlcl`. (c) `<home>/.sqlcl`.
- **Recommended**: (a).
- **Answer**: (a) - decided by reading `AGENTS.md` (never touch `<home>/.sqlcl`, never print wallet contents) and `~/.claude/rules/secrets.md` (wallet bytes are never rendered to stdout).

## Q7: Where does the live database for `connect -save` come from?

- **Why it matters**: SQLcl saves a connection only after connecting, so capturing `add` and `clone` output needs a running database.
- **Options**: (a) podman Oracle container. (b) Vagrant Oracle VM.
- **Recommended**: (a).
- **Answer**: (a) - decided by the saved project preference for a podman container over the VM (`db-tool` skill for container management).

## Q8: Which SQLcl version is the baseline?

- **Why it matters**: the store format is undocumented and can change between releases.
- **Options**: (a) 25.4.1 only, recorded in the findings. (b) several versions.
- **Recommended**: (a).
- **Answer**: (a) - decided by reading the local install: 25.4.1 is the only SQLcl present and the version `README.md` documents. Cross-version checks become a follow-up.

## Q9: Where do the findings live?

- **Why it matters**: the global instructions forbid new reference documents unless asked.
- **Options**: (a) `findings.md` inside this task folder; `README.md` "Store format" is updated by the later implementation task. (b) a new `docs/store-format.md`.
- **Recommended**: (a).
- **Answer**: (a) - decided by reading `~/.claude/CLAUDE.md` (no reference docs unless the user asks for them).

## Q10: May a SQLcl-free writer store a password in plain text?

- **Why it matters**: Phase 6 showed that SQLcl connects with a password read from `ojdbc.properties` in the connection directory, which would make saving a password possible without a wallet (`findings.md`, "Prior Wallet Observations and Alternatives").
- **Options**: (a) yes, optionally, behind a warning. (b) no; saving a password keeps using SQLcl.
- **Answer**: (b) - decided by the user on 2026-10-08: "security will be broken by such change if password will be save in plain text".

## Renewed Investigation Outcome (2026-10-08)

The user reopened password saving with obfuscation. Q1 remains clean-room: public research, signatures/constants and dummy-wallet black-box probes; no decompilation was needed. Q2 now has an accepted standard-library Python POC: an empty wallet and two independently generated password wallets passed SQLcl read and saved-name login. Q3 remains pure Python without third-party runtime libraries. Q10 still forbids plaintext storage, but its old inference that password saving must therefore retain SQLcl is superseded. See `solution_04.md` and the renewed wallet section in `findings.md`. Earlier outcomes above describe the first investigation pass.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered; clean-room renewal accepted, no decompilation | All phases (method), Phase 6 (escalation gate) |
| Q2 | Answered; renewed Python wallet POC accepted | REQ-6, Phase 6 (feasibility exit) |
| Q3 | Revised by the user: (a) | REQ-7, Phase 7 |
| Q4 | Answered (default) | Task structure, REQ-8 |
| Q5 | Answered | Non-Requirements |
| Q6 | Answered | All phases |
| Q7 | Answered | Harness phase |
| Q8 | Answered | All phases |
| Q9 | Answered | Deliverables |
| Q10 | Plaintext rejected; obfuscated Python POC accepted | REQ-6, REQ-7, Phase 8 follow-up outline |
