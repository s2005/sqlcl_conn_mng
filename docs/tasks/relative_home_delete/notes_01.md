# Defect Reproduces Command Needs MSYS_NO_PATHCONV Under Git Bash

## Finding

The "Defect Reproduces" commands in `verification.md` build the throwaway store with `sql ... /nolog`. Under Git Bash, MSYS path conversion rewrites `/nolog` to `C:/Program Files/Git/nolog`, so SQLcl prints `Bad Option` and the import does not run. The later `delete --name imp1` then fails with `No saved connection named 'imp1'`, which looks like the defect but is not.

## Evidence

- Spec: `verification.md`, section "Defect Reproduces".
- Observed output: `Bad Option: C:/Program Files/Git/nolog`.
- With `MSYS_NO_PATHCONV=1` set on the `sql` call, the import prints `Importing connection imp1: Success`, and the fixed tool then prints `Connection imp1 has been deleted` with exit 0.
- The tool itself is not affected: `SqlclRunner.run` calls `subprocess.run` directly, with no MSYS shell in between.

## Effect

Only the manual verification command is affected. The code, the unit tests and the integration tests are not.

## Status

Resolved: `verification.md` now sets `MSYS_NO_PATHCONV=1` on the `sql` call.

## Next step

None.
