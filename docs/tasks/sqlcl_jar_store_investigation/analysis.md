# Analysis: Investigate SQLcl Store Writes for SQLcl-Free Catalog Management

## Goal

Learn exactly what SQLcl 25.4.1 writes to its saved-connection store for each catalog operation, well enough to reproduce it from Python, and decide which `sqlcl-conn-mng` commands can then run without SQLcl. The deliverable is knowledge (`findings.md`) plus the probe harness that produced it, not a change to the tool.

## Current Behavior

- `src/sqlcl_conn_mng/store.py` reads the store with no SQLcl: `ConnectionStore.connections()` walks `connections/<id>/dbtools.properties` (ids matched by `_ID_PATTERN`, `[A-Za-z0-9_-]{22}`), and `ConnectionStore.folders()` parses `connection_folders/folders.json`. `has_wallet()` only checks that `credentials.sso` exists and never opens it.
- `src/sqlcl_conn_mng/properties.py` parses Java properties text (escapes, continuations, `\uXXXX`) but has no writer.
- `src/sqlcl_conn_mng/sqlcl.py` runs SQLcl for every write and for the password check: `save_connection()` (`connect -save ... -savepwd -replace`), `delete_connection()`, `rename_connection()`, `move_connection()`, `clone_connection()` (`-username`, `-nopwd`), `add_folder()`, `delete_folder()` (`-force`), `show_connection()` and `check_connection()`. Success is detected from output text because SQLcl always exits 0.
- `README.md`, "Store format", records the read-side observations: opaque 22-character ids not derived from the name, `credentials.sso` always present whether or not a password is saved, the four known properties keys, and the `folders.json` tree of `name` / `connections` / `folders`.

Gaps for a SQLcl-free writer (each maps to a requirement):

| Gap | Requirement |
| --- | ----------- |
| No way to observe store changes repeatably and safely | REQ-1 |
| Id generation rule unknown; only its shape is known | REQ-2 |
| Exact properties output (header, order, escaping, encoding) unknown | REQ-3 |
| `folders.json` output details and tolerance unknown | REQ-4 |
| Per-operation side effects, validation and atomicity unknown | REQ-5 |
| Wallet content and password-presence rule unknown | REQ-6 |
| No decision on which runtime would write the wallet | REQ-7 |

## Feasibility

- **Metadata files (REQ-2 to REQ-5)**: straightforward. Both files are text, SQLcl can be driven against a throwaway store with `-home`, and every claim can be checked by round trip: write the file from Python, then ask SQLcl to read it. A JDK 17 with `javap` is installed, so class names, method signatures and string constants of `ConnectionStorage`, `ConnectionStoreCommand` and the folder classes are readable without decompiling.
- **Wallet (REQ-6)**: hard and uncertain. `credentials.sso` is an Oracle auto-login wallet produced by `oraclepki.jar` (`OracleFileSSOWalletImpl`, `OracleSecretStore`). Its obfuscation is not documented by Oracle. Third-party descriptions of the `cwallet.sso` layout exist and are a starting point, but whether a Python-written wallet is accepted can only be shown by building one, so this is a POC with a feasibility exit.
- **Live database**: SQLcl saves a connection only after connecting, so capturing `connect -save` and `clone` needs a running database. A podman Oracle container provides it (`open_questions.md`, Q7).

## Approach

### Option A: Black-box observation only

Run each SQLcl command against a scratch store and diff the store.

| Advantages | Disadvantages |
| ---------- | ------------- |
| No licence exposure | Cannot explain rules that a few samples do not reveal (id derivation, escaping corner cases) |
| Fast, fully reproducible | Says nothing about the wallet beyond size and hash |

### Option B: Clean-room - black-box plus class signatures and constants (recommended)

Option A, plus `javap -p` signatures and constant-pool strings of the classes in the four jars, to form hypotheses that the black-box runs then confirm. Every format claim is proven by a round trip. Local decompilation in the scratch directory is allowed only for a gap B cannot close and only after the user confirms the licence (`open_questions.md`, Q1).

| Advantages | Disadvantages |
| ---------- | ------------- |
| Signatures and constants name the files, keys, aliases and algorithms involved | Method logic stays a black box, so some rules need more experiments |
| Round trip proves behaviour, not just intent | Wallet obfuscation may not be recoverable without decompilation |
| No Oracle code enters the repository | |

### Option C: Full decompilation from the start

| Advantages | Disadvantages |
| ---------- | ------------- |
| Fastest route to exact rules, including the wallet | Licence terms must be checked first |
| | Risk of copied logic leaking into the MIT code base |

Option B is recommended: it answers REQ-2 to REQ-5 with no licence exposure, and it fixes a clear gate for the one area (REQ-6) that may need more.

## Implementation Notes

- **Harness (REQ-1)** lives in `scripts/store_probe.py`, stdlib only, `argparse` with named options. It reuses `sqlcl_conn_mng.properties.parse_properties` when importable, so the probe and the tool parse properties identically. Wallet files and password-named keys are recorded as size and 12-hex-digit SHA-256 prefix only; that is safe here because every wallet holds only dummy passwords (see `~/.claude/rules/secrets.md` on fingerprinting low-entropy secrets).
- **Scratch layout**: one store per experiment under the session scratch directory, for example `<scratch-root>/stores/<phase>-<step>/`, with snapshots beside it. Nothing under `<scratch-root>` is committed.
- **SQLcl invocation** matches the tool: `MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <store> /nolog` (the prefix stops Git Bash rewriting `/nolog`) with the script on stdin, so findings apply to the commands `sqlcl-conn-mng` actually issues. Passwords go on stdin only, never on the command line.
- **javap usage**: `javap -p -cp <sqlcl-lib>/<jar> <class>` for signatures; `javap -v` output filtered to constant-pool `String` and `Utf8` entries for constants. Bytecode (`-c`) is not read under Option B. All dumps stay in `<scratch-root>/javap/`.
- **Id hypothesis (REQ-2)**: 22 characters over `[A-Za-z0-9_-]` is exactly URL-safe Base64 of 16 bytes without padding, which suggests an encoded random UUID. Test by decoding a sample of ids and checking UUID version and variant bits.
- **Properties writer (REQ-3)**: `java.util.Properties.store` writes a `#<date>` comment line and escapes `:` and `=`; the observed `//host\:1521/svc` in `README.md` is consistent with that. Confirm the header, key order and non-ASCII handling. If SQLcl uses `Properties.store`, key order depends on the JRE (hash order before Java 18, sorted by key from Java 18), so record the JRE SQLcl ran on and check whether SQLcl reads keys in any order.
- **Wallet (REQ-6)**: start from the empty wallet that every connection gets. Compare two SQLcl-written empty wallets: if they are byte-identical the empty case may reduce to a constant template, but a constant template is still Oracle-generated output and its reuse is a licence question to record, not a solution to adopt silently. Secret aliases should be visible as constants in `WalletUtils` and `OracleSecretStoreConstants`.
- **Atomicity (REQ-5)**: watch for temporary files and lock files during a write by snapshotting while a long `connmgr` script runs, and by checking file timestamps; record whether a reader can observe a half-written file.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A wallet byte or a dummy password reaches the transcript | Harness records size and hash only; unit test for REQ-1; passwords on stdin only; no `cat`, `xxd` or `head` on `.sso` files - byte-level analysis runs inside a script that prints offsets, lengths and structure names, never content |
| Oracle code copied into the repository | Option B; `javap` dumps and any decompiled source stay in `<scratch-root>`; AC-9 checks `git ls-files` |
| Wallet obfuscation cannot be reproduced | REQ-6 feasibility exit records the blocker; REQ-7 costs the JRE fallback so the follow-up still has a path |
| Experiments touch a real store | Every SQLcl call passes `-home <scratch-root>/stores/...`; AC-9 checks no file in `<repo-root>/.sqlcl` changed and every recorded SQLcl command targets a scratch store; `<home>/.sqlcl` is never listed, per `AGENTS.md` |
| podman machine is wedged | `podman-machine-recovery` skill; the metadata phases that need no connect (`add -folder`, `delete -folder`, `rename`, `move`, `delete`) can proceed on a store seeded once |
| Findings depend on SQLcl 25.4.1 internals | Version recorded in `findings.md`; harness kept so the capture can be repeated on a later release |

## Test Strategy

- **Unit**: `tests/test_store_probe.py` covers the harness - snapshot of a fake store built in `tmp_path` (same style as `tests/conftest.py`), diff of two snapshots, and the safety property that a planted wallet byte pattern and a planted password value never appear in stdout, stderr or the snapshot file.
- **Experimental (not automated)**: each finding is backed by a recorded probe run or round trip, reproducible from the commands written in `findings.md`. These runs need SQLcl and a podman Oracle container, and are not added to the test suite in this task.
- **Regression**: the existing suite (`uv run pytest -q`, 86 passed at baseline) must stay green; no source under `src/` changes.
