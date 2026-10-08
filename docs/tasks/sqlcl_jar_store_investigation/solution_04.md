# Solution 04: Reopen Obfuscated Password Wallet Discovery

## Chosen Approach

Resume Phase 6 under the user's renewed request. Use standard-library Python, public format research, cryptographic standards, and black-box tests against dummy wallets. Keep wallet readers, writers and raw experiments outside the repository. No Oracle method-body decompilation is authorized by this approach.

## Why This Approach

The earlier blocker was a decision not to investigate the obfuscation, rather than a failed compatibility POC. The user now explicitly requests obfuscated password saving. A new experiment can establish whether that requirement is feasible without changing the decisions against third-party runtime libraries or plaintext storage.

Using Oracle's published wallet library would violate the runtime restriction. Using a separate operating-system credential format would not make a SQLcl-compatible connection store. Neither is silently substituted.

## Drift Resolved

Resolves D4 in `notes.md`: reopen the previously complete Phase 6 and reassess Phases 7-8 after fresh acceptance checks.

## Verification

- Generate an empty wallet and a wallet with dummy credentials from Python in scratch.
- Check SQLcl's password-state output and connect using only the saved name.
- Verify newly generated wallets vary and do not contain the dummy password or its Base64 representation in clear.
- Preserve the real stores and `.env`, run all project checks, and remove scratch secrets and wallet code.
- Record any actual blocker as incomplete renewed acceptance, rather than using the historical checklist as proof of success.
