# Analysis: Descriptor connect string quoting

## Goal

Make SQLcl accept every connect string the tool passes to `connect -save`.

## Current Behavior

`save_connection` (`src/sqlcl_conn_mng/sqlcl.py`) joins `user@connect` and calls `quote_arg` on the result. `quote_arg` returns a value unchanged when it matches `_SAFE_TOKEN` (`[A-Za-z0-9_./@:\\-]+`) and wraps it in double quotes otherwise. Callers: `add` and `update` in `src/sqlcl_conn_mng/cli.py`. `update` reads the stored connect string from the store, so a stored descriptor takes the same path.

## Feasibility

Straightforward. A live probe (REQ-1 to REQ-4) found a single working shape: quote the connect part alone.

| Target form | SQLcl |
| ----------- | ----- |
| `"itest@(DESCRIPTION=...)"` | fails |
| `itest@"(DESCRIPTION=...)"` | works |
| `"itest@//h:1521/s?connect_timeout=5"` | fails |
| `itest@"//h:1521/s?connect_timeout=5"` | works |
| `"itest@//h:1521/s"` | fails |
| `itest@//h:1521/s` | works |

## Approach

Build the target as the quoted user, an `@`, then the connect part. The connect part is the connect string itself when it is a safe token and `"<connect>"` otherwise. `validate_value` already rejects double quotes, so the added quotes cannot be broken out of.

| Advantages | Disadvantages |
| ---------- | ------------- |
| Fixes descriptors and `?` parameters with one rule | Changes the command text for every non-safe connect string |
| Matches the form the harness already proves | The user part still has to be safe on its own |

Descriptor-only quoting (open question Q2, option a) was rejected: it leaves the `?` parameter case failing.

## Implementation Notes

- `quote_arg` stays as is; the connect-part rule is local to `save_connection`.
- A user with a space is still quoted alone, as in `"my user"@//h/s`. The integration suite has a special-character user case (`SPECIAL_USER`) that covers the user side.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| A connect string that worked quoted whole now breaks | The probe showed whole quoting never works; the integration suite (161 tests) re-runs against the container |
| A user that needs quoting combined with a quoted connect | Covered by a unit test of the command text |

## Test Strategy

Unit tests of the command text (REQ-5). Integration tests in podman: remove the xfail from `test_tool_add_with_descriptor`, add a `?` parameter `add` case, an `update --connect-string` case and an `update --password-env` case on stored descriptor and `?` connections.
