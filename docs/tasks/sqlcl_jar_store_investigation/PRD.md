# PRD: Investigate SQLcl Store Writes for SQLcl-Free Catalog Management

## Objective

Produce a verified, clean-room specification of every change SQLcl 25.4.1 makes to its saved-connection store - connection ids, `dbtools.properties`, `connection_folders/folders.json` and the `credentials.sso` wallet - for each catalog operation, so that a follow-up task can implement those operations in `sqlcl-conn-mng` without SQLcl installed on the machine.

## Background

`sqlcl-conn-mng` reads the store directly (`src/sqlcl_conn_mng/store.py`) but runs SQLcl for every write (`src/sqlcl_conn_mng/sqlcl.py`): `add` (`connect -save`), `delete`, `rename`, `move`, `clone`, `add-folder`, `delete-folder`, and `show --check-password`. `README.md` states that SQLcl is the only supported writer of the store and that the format is undocumented by Oracle; the "Store format" section there was observed empirically and covers reading only.

Users who do not have SQLcl installed therefore cannot manage their catalog. Supporting them needs a precise description of what SQLcl writes, which lives in four jars of the SQLcl `lib` folder:

| Jar | Responsibility |
| --- | -------------- |
| `dbtools-sqlcl.jar` | `connmgr` command: `ConnectionStoreCommand`, `ConnectionStoreOptions` |
| `dbtools-core.jar` | Store persistence: `ConnectionStorage`, folder serialization |
| `dbtools-common.jar` | `connect -save`, `WalletUtils`, `ConnectionStoreBridge` |
| `oraclepki.jar` | Auto-login wallet: `OracleFileSSOWalletImpl`, `OracleSecretStore` |

SQLcl is licensed under the Oracle Free Use Terms and Conditions. The investigation is clean-room (see `open_questions.md`, Q1): findings are written as prose specifications backed by observed behaviour; no Oracle code is copied into this MIT repository. The decisions behind this PRD are recorded in `open_questions.md`.

## Requirements

### REQ-1: Reproducible store probe harness

A stdlib-only script, `scripts/store_probe.py`, with named arguments only:

- `snapshot --home <store> --output <file.json>` records every file under the store root: relative path, size, SHA-256 prefix (first 12 hex digits), and for `dbtools.properties` and `folders.json` their parsed content. For `credentials.sso` and any other binary file it records size and hash prefix only.
- `diff --before <a.json> --after <b.json>` prints files added, removed and changed, with key-level differences for properties files and a structural difference for `folders.json`.
- No byte of a `credentials.sso` file, and no value of a key whose name contains `password` or `pwd` (case-insensitive), ever reaches stdout, stderr or the snapshot file.

### REQ-2: Connection id rule

Determine how SQLcl generates the 22-character directory name under `connections/`: the alphabet, the source of randomness or derivation (the working hypothesis, which Phase 3 tests, is URL-safe Base64 of 128 bits without padding), whether `rename`, `move` and `clone` keep or change it, and whether SQLcl accepts a connection whose id was generated outside SQLcl by the same rule.

### REQ-3: `dbtools.properties` write format

Document the exact file SQLcl writes: key set and the condition under which each key appears, key order, header comment and timestamp line, escaping of `:`, `=`, `\`, spaces and non-ASCII characters, character encoding, line endings, and trailing newline. Confirm by round trip that a file written from Python is read by SQLcl (`connmgr show`, `connmgr list`) with the same values.

### REQ-4: `folders.json` write format

Document the schema SQLcl writes and expects: top-level shape, folder object keys, ordering of folders and connection ids, whitespace and indentation, encoding, behaviour when the file is absent, nested folder creation, and how SQLcl treats a dangling connection id or a connection id listed in two folders. Confirm by round trip that a file written from Python is read by SQLcl.

### REQ-5: Operation effect map

Enumerate every `connmgr` subcommand from SQLcl's own help and from `ConnectionStoreOptions`, and for each one that writes the store - plus `connect -save` with `-savepwd` and `-replace` - record: the files created, changed and deleted; the validation SQLcl applies before writing (name uniqueness and its case rule, folder existence, name character rules); the output text on success and on each failure; and whether the write is atomic (temporary file, rename, lock file).

### REQ-6: `credentials.sso` wallet

Determine, with a feasibility verdict:

- the layout of the wallet SQLcl writes with no saved password and with a saved password;
- the secret-store alias name(s) that hold the password and any other credential;
- the obfuscation or encryption `OracleFileSSOWalletImpl` applies and the key material it depends on;
- how `show` decides a password is saved, and what `clone -nopwd` and `connect -save` without `-savepwd` write;
- whether a wallet written from Python - empty, and holding a dummy password - is accepted by SQLcl.

The phase ends either with a Python-written wallet accepted by SQLcl, or with a named blocker and the evidence for it.

### REQ-7: Runtime comparison

Compare the two runtimes the follow-up implementation could use for wallet operations: pure Python, and Python plus a JRE calling the `oraclepki` jar published on Maven Central. For each: dependencies and their licences, install footprint, cross-platform behaviour on Windows, Linux and macOS, and which operations it covers. End with one recommendation.

### REQ-8: Findings and follow-up task outline

`findings.md` in this task folder holds the specification. Every claim carries its evidence tag: `[diff]` (captured store diff), `[javap]` (class signature or constant), `[round-trip]` (Python-written file accepted by SQLcl), or `[decompile]` (only if the Q1 escalation gate was passed). The final section is a follow-up outline that lists every `sqlcl-conn-mng` command with a verdict - feasible without SQLcl, feasible with the fallback runtime, or still needs SQLcl - and names the follow-up implementation task(s).

### REQ-9: Clean-room and secret hygiene

Nothing derived from Oracle binaries is committed: no jar, class file, decompiled source, `javap` dump, wallet file, or store snapshot containing wallet bytes. Experiments use only a throwaway store in the session scratch directory and dummy passwords; `<home>/.sqlcl` and `<repo-root>/.sqlcl` are never read or written. No dummy password appears in any tracked or untracked file of the repository.

## Non-Requirements

- No change to the behaviour or command-line options of `sqlcl-conn-mng`; therefore no version bump. Implementing SQLcl-free writes is the follow-up task drafted by REQ-8.
- No connectivity work: `connmgr test` and the connect-before-save check SQLcl performs are out of scope (`open_questions.md`, Q5). The follow-up outline notes python-oracledb as the candidate replacement.
- No SQLcl version other than 25.4.1 (`open_questions.md`, Q8). Cross-version checks are listed as a follow-up.
- No compatibility work with the SQL Developer or SQL Developer for VS Code connection stores.
- No update to `README.md`; its "Store format" section is updated by the implementation task.
- No standalone reference document outside this task folder (`open_questions.md`, Q9).

## Acceptance Criteria

- **AC-1** - `scripts/store_probe.py snapshot` and `diff` run against a scratch store and report per-file changes; a unit test proves that wallet bytes and password-named property values never appear in stdout, stderr or the snapshot file (REQ-1, REQ-9)
- **AC-2** - `findings.md` states the id rule with `[diff]` or `[javap]` evidence, states the effect of `rename`, `move` and `clone` on the id, and records a `[round-trip]` where SQLcl lists and shows a connection whose id was generated outside SQLcl (REQ-2)
- **AC-3** - `findings.md` documents the `dbtools.properties` format; a Python-written file is shown by `connmgr show` with identical values, and a byte comparison against the SQLcl-written file for the same input is either identical or lists every difference with why it is harmless (REQ-3)
- **AC-4** - `findings.md` documents the `folders.json` schema; a Python-written file with nested folders is listed by `connmgr list` and by `sqlcl-conn-mng folders` with the same tree, and the byte comparison is reported as in AC-3 (REQ-4)
- **AC-5** - `findings.md` has one row per store-writing operation listing files created, changed and deleted, validation rules, success and failure output, and atomicity, each row citing a captured diff (REQ-5)
- **AC-6** - `findings.md` records the wallet verdict: either a Python-written empty wallet and a Python-written wallet holding a dummy password are both accepted by SQLcl (`show` reports the expected password state and a connect with the saved password succeeds), or a named blocker with its evidence (REQ-6)
- **AC-7** - `findings.md` has the runtime comparison table and one recommendation (REQ-7)
- **AC-8** - every claim in `findings.md` carries an evidence tag, and its follow-up outline gives a verdict for every `sqlcl-conn-mng` command and names the follow-up task(s) (REQ-8)
- **AC-9** - `git ls-files` lists no `.jar`, `.class`, `.java`, `.sso` file or snapshot JSON; no dummy password is found in the working tree by `git grep -IlF --untracked`; no file in `<repo-root>/.sqlcl` changed during the task, and every SQLcl command recorded in `findings.md` passes `-home` pointing at a scratch store, so `<home>/.sqlcl` was never targeted (REQ-9)

## Deliverables

| Deliverable | Type |
| ----------- | ---- |
| `scripts/store_probe.py` | Create |
| `tests/test_store_probe.py` | Create |
| `docs/tasks/sqlcl_jar_store_investigation/findings.md` | Create |
| `docs/tasks/sqlcl_jar_store_investigation/open_questions.md` | Update (Q1 escalation outcome, if any) |
| `docs/tasks/sqlcl_jar_store_investigation/progress.md` | Update |
