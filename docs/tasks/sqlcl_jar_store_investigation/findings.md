# Findings: SQLcl 25.4.1 Saved-Connection Store Writes

Clean-room specification of what SQLcl writes to its saved-connection store, built from store diffs, `javap` signatures and constants, and round trips. No Oracle code, class file, `javap` dump or wallet byte is reproduced here (`open_questions.md`, Q1).

## Environment

| Item | Value |
| ---- | ----- |
| SQLcl | `Oracle SQLDeveloper Command-Line (SQLcl) version: 25.4.1.0 build: 25.4.1.022.0618` |
| JRE SQLcl runs on | Oracle JDK 17.0.15, the `JAVA_HOME` JDK (`show java`: `java.version= 17.0.15`, `file.encoding= UTF-8`) |
| OS | Windows 11 Enterprise 10.0.26200, Git Bash |
| Jars inspected | `dbtools-sqlcl.jar`, `dbtools-core.jar`, `dbtools-common.jar`, `oraclepki.jar` from `<sqlcl-dir>/lib` |
| Database | podman container `sqlcl-jar-probe-xe` (`gvenzl/oracle-xe:21-slim`), schema `PROBE`, connect string `//localhost:1537/XEPDB1` |
| Password | A random dummy password, held in a scratch file only and fed to SQLcl on stdin; never written here |

Every SQLcl run in this document uses the command line below, with the script on stdin. `<scratch-root>` is the session scratch directory; nothing under it is committed.

```bash
MSYS_NO_PATHCONV=1 sql -S -nohistory -noupdates -thin -home <scratch-root>/stores/<store> /nolog
```

## Evidence Tags

| Tag | Meaning |
| --- | ------- |
| `[diff]` | Observed in a store snapshot pair captured with `scripts/store_probe.py` |
| `[javap]` | Read from a class signature or a constant-pool string with `javap` |
| `[round-trip]` | A file written from Python was read back by SQLcl with the stated result |
| `[output]` | Exact SQLcl console output for the stated command |
| `[decompile]` | Read from decompiled code; used only if the Q1 escalation gate is passed |

## Side Effects of Any SQLcl Run

- Any SQLcl run with `-home <store>` creates `<store>/sqlcl/aliases.xml` (68 bytes) and an empty `<store>/sqlcl/history.log`, even with `-nohistory` and without touching a connection `[diff]`. A SQLcl-free writer does not need to create them, and the read path already ignores them.
