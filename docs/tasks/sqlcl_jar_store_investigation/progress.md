# Progress: Investigate SQLcl Store Writes for SQLcl-Free Catalog Management

## Status Legend

| Marker | Meaning |
| ------ | ------- |
| `[ ]` | Not started |
| `[x]` | Complete |
| `[~]` | In progress |
| `[!]` | Blocked or needs decision |
| `[-]` | Skipped / not applicable |

## Planning Checklist

- [x] Analyze current behavior.
- [x] Create open_questions.md and settle every entry (Q1-Q4 on recommended defaults; revisit before Phase 1 if the user disagrees)
- [x] Create analysis.md
- [x] Create PRD.md
- [x] Create implementation_plan.md
- [x] Create verification.md
- [x] Create progress.md

## Phase 1: Probe Harness and Scratch Environment

Requirements: REQ-1, REQ-9

- [x] Run the pre-implementation baseline from `verification.md`
- [x] Create `scripts/store_probe.py` with `--command snapshot` and `--command diff`, named options only
- [x] Record wallet files and password-named keys as size and hash prefix only
- [x] Create `tests/test_store_probe.py`, including the no-secret-output test
- [x] Create the scratch layout: `stores/`, `snapshots/`, `javap/`
- [x] Start the podman Oracle container and create the dummy schema
- [x] Dump `javap` signatures and constant-pool strings for the classes of interest into `<scratch-root>/javap/`
- [x] Start `findings.md` with the environment section and evidence-tag legend
- [x] Phase 1 verification passes

## Phase 2: Operation Inventory and Black-Box Capture

Requirements: REQ-5

- [x] Inventory every `connmgr` subcommand and flag; mark the store-writing ones
- [x] Capture `connect -save` with and without `-savepwd`, and with `-replace`
- [x] Capture `connmgr add -folder`, top-level and nested
- [x] Capture `connmgr delete -conn`, `rename -conn` and `move -conn`
- [x] Capture `connmgr clone` plain, with `-username` and with `-nopwd`
- [x] Capture `connmgr delete -folder` empty, non-empty without `-force`, and with `-force`
- [x] Capture any further writing subcommand found by the inventory
- [x] Record validation rules and exact success and failure output
- [x] Check atomicity: temporary files, lock files, concurrent writers
- [x] Write the "Operation effect map" section of `findings.md`
- [x] Phase 2 verification passes

## Phase 3: Connection Id Rule

Requirements: REQ-2

- [x] Decode the collected ids and check the UUID hypothesis
- [x] Check `javap` evidence for UUID or Base64 use
- [x] Record the effect of `rename`, `move` and `clone` on the id
- [x] Round trip with a Python-generated id, and with a rule-breaking id
- [x] Write the "Connection id" section of `findings.md`
- [x] Phase 3 verification passes

## Phase 4: dbtools.properties Write Format

Requirements: REQ-3

- [x] Record key set, order, header, line endings, trailing newline and encoding
- [x] Record escaping for special and non-ASCII characters
- [x] Record the writer in use and the JRE
- [x] Round trip a Python-written file and byte-compare it
- [x] Probe SQLcl tolerance: no header, reordered keys, LF versus CRLF, unknown key
- [x] Write the "dbtools.properties" section of `findings.md`
- [x] Phase 4 verification passes

## Phase 5: folders.json Write Format

Requirements: REQ-4

- [x] Record shape, keys, ordering, indentation, encoding and absent-file behaviour
- [x] Probe tolerance: dangling id, duplicate id, empty versus missing `connections`, unknown keys, compact JSON
- [x] Record the serializer in use
- [x] Round trip a Python-written nested tree and byte-compare it
- [x] Write the "folders.json" section of `findings.md`
- [x] Phase 5 verification passes

## Phase 6: credentials.sso Wallet Discovery and POC

Requirements: REQ-6

Reopened on 2026-10-08 by the user's request to complete password saving with obfuscation. The earlier blocker is historical; renewed acceptance requires an actual wallet round trip, without third-party runtime libraries or plaintext password storage.

- [x] Inspect dummy-wallet structure without rendering content bytes or secrets
- [x] Build standard-library Python empty and password-bearing wallet POCs in scratch only
- [x] Confirm SQLcl password state and saved-name database login
- [x] Reassess runtime recommendation and follow-up outline from the new evidence
- [x] Run full gates, clean scratch secrets, and commit the renewed findings

- [x] Compare wallet sizes and hashes across the Phase 2 cases
- [x] Record aliases/provider from `javap` and algorithms/format discriminators from renewed safe structure probes
- [x] Build the structure analyser in `<scratch-root>/poc/` - renewed clean-room structure probes completed
- [x] Map the wallet layout - wrapper, DER payload and Oracle localKeyId discriminators verified
- [x] POC: Python-written empty wallet accepted by SQLcl - fresh 270-byte wallet recognized
- [x] POC: Python-written wallet with the dummy password accepted by SQLcl - two fresh wallets logged in by saved name
- [x] Apply the escalation gate if needed - renewed layout mapped clean-room; no decompilation needed
- [x] Write the "credentials.sso" section of `findings.md` with the renewed verdict (accepted)
- [x] Black-box test of wallet-free alternatives: no wallet file, 0-byte wallet, `ojdbc.properties` password
- [x] Phase 6 verification passes - renewed verdict: accepted; plaintext remains rejected (Q10)

## Phase 7: Runtime Comparison

Requirements: REQ-7

- [x] Cost the pure-Python runtime
- [x] Cost the Python + JRE + Maven Central `oraclepki` runtime
- [-] Prove the JRE writer sequence if Phase 6 was blocked - not applicable: renewed Python POC accepted. Installed Oracle APIs served only as diagnostic readers; no JRE writer runtime was added
- [x] Write the "Runtime comparison" section of `findings.md` with one recommendation
- [x] Phase 7 verification passes

## Phase 8: Synthesis and Follow-Up Task Outline

Requirements: REQ-8, REQ-9

- [x] Review `findings.md`: every claim tagged, contradictions resolved
- [x] Write the "Follow-up" section with a verdict per command and the follow-up task(s)
- [x] Remove the non-shippable POC: delete `<scratch-root>/poc/`, `<scratch-root>/javap/` and wallet-holding scratch stores
- [x] Stop the podman Oracle container if this task started it
- [x] Run the AC-9 hygiene checks
- [x] Phase 8 verification passes

## Renewed Completion Evidence

- [x] Empty and two fully independent password wallets accepted by SQLcl 25.4.1; two saved-name logins returned the dummy user
- [x] Seven additional password-value round trips and SQLcl presence checks passed
- [x] Probe snapshots/diff and the application listing worked on the fresh store
- [x] Full suite: 93 passed, 1 integration test deselected by the existing project configuration
- [x] Ruff lint/format, both mypy targets, Markdown lint and Git diff checks passed
- [x] Dummy password and its Base64 absent from tracked/untracked repository files and snapshots; no forbidden tracked binary or snapshot
- [x] Repository store and environment files unchanged; user-home store never targeted
- [x] New dummy schema dropped, previously stopped container stopped again, all renewal scratch code/wallets/secrets removed

The completed result is the investigation and verified format specification. Production catalog/wallet code remains the explicitly identified follow-up task. The conditional standalone JRE writer experiment is not applicable because the Python POC succeeded.
