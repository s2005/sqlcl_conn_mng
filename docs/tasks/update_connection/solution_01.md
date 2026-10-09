# Solution 01: Convert The File The Way SQLcl Does

## Chosen approach

`ConnectionStore.update_properties` rewrites an `ORACLE_BASIC` file as `ORACLE_DATABASE` when the change holds a `connectionString`: `host`, `port` and `serviceName` are dropped and the keys are ordered `name`, `type`, `connectionString`, `userName`, then the remaining keys. This is the form SQLcl writes itself on `connect -save -replace` (observed in Phase 1 follow-up, see `notes.md`, D1). Any other type is refused with a `StoreError` before anything is written. Changes without a `connectionString` leave an `ORACLE_BASIC` file as it is.

## Why it beats the rejected options

- Option 02 leaves a command that reports success and has no effect.
- Option 03 needs a connect-string parser and cannot map descriptors to host, port and service.
- Option 04 blocks a change SQLcl itself performs on a replace.

## Drifts resolved

D1.

## Files to change

- `src/sqlcl_conn_mng/store.py`: `_with_connect_string_form`, constants, docstring.
- `tests/test_store.py`, `tests/test_cli.py`: unit tests.
- `tests/integration/test_update_compat.py`: metadata test runs on a saved and an imported connection.
- `README.md`, `PRD.md` (REQ-2, AC-2, AC-3), `open_questions.md` (Q13), `analysis.md`, `implementation_plan.md`, `verification.md`, `progress.md`.

## Implementation outline

1. Add the type constants and `_with_connect_string_form` to `store.py` and call it when `connectionString` is in the changes.
2. Cover conversion, key order, untouched cases and the refused type in unit tests.
3. Parametrize the integration metadata test over `saved_pw_store` and `folder_store` and require SQLcl's `connmgr show` to report the new connect string for both.
4. Replace the README caveat with the conversion rule.

## Verification steps

- `make unit`, `make check`.
- `make integration PYTEST_ARGS=tests/integration/test_update_compat.py` with the database variables set.
- `markdownlint-cli2` on the changed Markdown.
