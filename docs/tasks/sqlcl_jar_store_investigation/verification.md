# Verification Plan: Investigate SQLcl Store Writes for SQLcl-Free Catalog Management

## Purpose

Covers the probe harness (`scripts/store_probe.py` and its tests), the evidence behind every section of `findings.md`, and the clean-room and secret hygiene of the repository after the investigation. All commands run from `<repo-root>` in Git Bash.

## Pre-Implementation Verification

### Existing Tests Pass

```bash
uv run pytest -q
```

Expected: all pass (86 passed, 1 deselected at task creation).

### Linter Baseline

```bash
uv run ruff check src tests
```

Expected: `All checks passed!`.

### Toolchain Present

```bash
printf 'version
exit
' | MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates /nolog
javap -version
podman --version
```

Expected: `SQLcl) version: 25.4.1.0`, a JDK `javap`, and podman, each printing a version. `MSYS_NO_PATHCONV=1` stops Git Bash rewriting `/nolog` into a filesystem path; every SQLcl command in this plan needs it.

### Real Stores Untouched Baseline

```bash
touch <scratch-root>/start.marker
```

Phase 8 counts the files in `<repo-root>/.sqlcl` changed after this marker. `<home>/.sqlcl` is not inspected at all, because `AGENTS.md` forbids reading or listing it; it is protected by every SQLcl command passing `-home <scratch-root>/stores/...`, which Phase 8 checks in `findings.md`.

## Post-Implementation Verification

### Phase 1: Probe Harness and Scratch Environment

Covers REQ-1, REQ-9.

```bash
uv run pytest -q tests/test_store_probe.py
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy scripts/store_probe.py
uv run python scripts/store_probe.py --command snapshot --home <scratch-root>/stores/empty --output <scratch-root>/snapshots/empty.json
```

Expected: tests pass, including the test that a planted wallet marker and a planted password value never appear in stdout, stderr or the snapshot; lint, format and type checks are clean; the snapshot command exits 0.

### Phase 2: Operation Inventory and Black-Box Capture

Covers REQ-5.

```bash
uv run python scripts/store_probe.py --command diff --before <scratch-root>/snapshots/<op>-before.json --after <scratch-root>/snapshots/<op>-after.json
uv run sqlcl-conn-mng list --home <scratch-root>/stores/<store> --format json
```

Expected: one diff per row of the "Operation effect map" in `findings.md`; the tool's listing agrees with `connmgr list` for each store.

### Phase 3: Connection Id Rule

Covers REQ-2.

```bash
printf 'connmgr list\nconnmgr show <name>\n' | MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <scratch-root>/stores/id-roundtrip /nolog
```

Expected: the connection whose id was generated in Python is listed and shown; the outcome for the rule-breaking id is recorded in `findings.md`.

### Phase 4: dbtools.properties Write Format

Covers REQ-3.

```bash
printf 'connmgr show <name>\n' | MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <scratch-root>/stores/props-roundtrip /nolog
cmp <scratch-root>/stores/props-sqlcl/connections/<id>/dbtools.properties <scratch-root>/stores/props-roundtrip/connections/<id>/dbtools.properties
```

Expected: `show` prints the same name, connect string and user as for the SQLcl-written file; `cmp` reports identical, or each difference is listed in `findings.md` with why it is harmless.

### Phase 5: folders.json Write Format

Covers REQ-4.

```bash
printf 'connmgr list\n' | MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <scratch-root>/stores/folders-roundtrip /nolog
uv run sqlcl-conn-mng folders --home <scratch-root>/stores/folders-roundtrip --format json
cmp <scratch-root>/stores/folders-sqlcl/connection_folders/folders.json <scratch-root>/stores/folders-roundtrip/connection_folders/folders.json
```

Expected: both listings show the Python-written nested tree; `cmp` result handled as in Phase 4.

### Phase 6: credentials.sso Wallet Discovery and POC

Covers REQ-6.

```bash
printf 'connmgr show <name>\n' | MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <scratch-root>/stores/wallet-poc /nolog
```

Expected: for the Python-written empty wallet, `Password: not saved`; for the Python-written wallet with the dummy password, a saved-password line, and a `connect -name <name>` by saved name succeeds. Otherwise the blocker is named in `findings.md`. No command in this phase prints wallet content bytes; predict each command's output before running it.

Renewed Phase 6 verification on 2026-10-08: Python wrote an empty wallet and two independent password wallets without reading a template. SQLcl reported the expected password state and two saved-name database logins returned `WALLET_PROBE`. Seven additional password-value round trips and SQLcl alias-presence checks passed. AES-128 and AES-256 known-answer examples passed. Raw POC code and secrets remain scratch-only until Phase 8 cleanup. This supersedes the original blocker verdict.

### Phase 7: Runtime Comparison

Covers REQ-7.

Expected: the "Runtime comparison" table in `findings.md` has both runtimes with every column filled and ends with one recommendation. If Phase 6 was blocked, the JRE call sequence is shown working against a scratch store with the same `connmgr show` check as Phase 6.

### Phase 8: Synthesis and Follow-Up Task Outline

Covers REQ-8, REQ-9.

```bash
git ls-files | grep -E '\.(jar|class|java|sso)$'
git ls-files | grep -E 'snapshots?/.*\.json$'
PW=$(tr -d '[:space:]' < <scratch-root>/dummy_password); [ -n "$PW" ] || { echo "no password read - aborting"; exit 1; }; git grep -IlF --untracked -e "$PW"; echo "exit $?"
```

```bash
[ -d .sqlcl ] && find .sqlcl -type f -newer <scratch-root>/start.marker | wc -l
grep -n 'sql -S' docs/tasks/sqlcl_jar_store_investigation/findings.md | grep -vc -- '-home <scratch-root>/stores/'
```

Expected: the first two commands print nothing; the third prints only `exit 1` (no file contains the dummy password); the fourth prints `0` or nothing (no file in the repository store changed); the fifth prints `0` (every recorded SQLcl command targets a scratch store). The commands print counts and file names only, never contents.

### Linter

```bash
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy
uv run mypy scripts/store_probe.py
markdownlint-cli2 "docs/**/*.md"
```

Expected: all clean. Run `markdownlint-cli2` from `<repo-root>` so it picks up `.markdownlint-cli2.jsonc`.

### Regression Check

```bash
uv run pytest -q
```

Expected: all pass; the count is the baseline plus the new `tests/test_store_probe.py` tests.

## Final Acceptance Verification

The investigation can be accepted when all items are true:

- [x] AC-1 - harness snapshot and diff work on a scratch store, and wallet bytes and password values never reach output - verified by: Phase 1 verification
- [x] AC-2 - id rule documented with evidence, effect of rename, move and clone recorded, and a Python-generated id accepted by SQLcl - verified by: Phase 3 verification and the "Connection id" section of `findings.md`
- [x] AC-3 - `dbtools.properties` format documented and a Python-written file accepted with identical values, byte differences explained - verified by: Phase 4 verification
- [x] AC-4 - `folders.json` schema documented and a Python-written nested tree accepted by SQLcl and the tool, byte differences explained - verified by: Phase 5 verification
- [x] AC-5 - one row per store-writing operation in the "Operation effect map", each citing a diff - verified by: Phase 2 verification
- [x] AC-6 - wallet verdict recorded: both POC wallets accepted, or a named blocker with evidence - verified by: Phase 6 verification
- [x] AC-7 - runtime comparison table complete with one recommendation - verified by: Phase 7 verification
- [x] AC-8 - every claim in `findings.md` tagged, and the follow-up outline gives a verdict per command and names the follow-up task(s) - verified by: review of `findings.md` in Phase 8
- [x] AC-9 - no Oracle-derived file, wallet or snapshot tracked, no dummy password in the working tree, real stores untouched - verified by: Phase 8 verification
