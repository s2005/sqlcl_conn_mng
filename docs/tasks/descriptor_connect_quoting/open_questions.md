# Open Questions: Descriptor connect string quoting

## Q1: Does the bug exist for `update`, or only for `add`?

- **Why it matters**: `add` (`cli.py:650`) and `update --password-env` (`cli.py:764`) both call `save_connection`, which wraps the whole `user@connect` target in double quotes when the connect string holds parentheses. The earlier xfail covers only `add`. If `update` is also broken, the fix needs a second test.
- **Options**: (a) test `add` only, (b) test `add` and `update` on a connection whose stored target is a descriptor.
- **Recommended**: (b) - both paths share the function, and `update` reads the stored `connectionString` as-is.
- **Answer**: Both are broken - decided by a live probe against the podman container (`add` with a descriptor, `update --connect-string` with a descriptor, and `update --password-env` on stored connections holding a descriptor or an easy-connect string with `?connect_timeout=5` all end in "Connection failed").

## Q2: How far should the quoting fix reach?

- **Why it matters**: the verified working form is `user@"(DESCRIPTION=...)"` (quote the descriptor only). Other connect strings with unsafe characters (a space, a `?` parameter) are quoted whole today and nothing shows whether SQLcl accepts that. A wider change alters the SQLcl command for connect strings nobody reported.
- **Options**: (a) change only the descriptor form (connect string starting with `(`), (b) quote the connect part separately for every non-safe connect string.
- **Recommended**: (a) - it matches the reported defect and the form the harness already proves works.
- **Answer**: (b) - decided by a live probe: SQLcl rejects a double-quoted `user@connect` target for every connect string, including plain `//host:port/service`; the tool avoids the failure for that one only because it leaves a safe token unquoted. Quoting the connect part alone (`user@"<connect>"`) works for a descriptor and for `?` parameters. Option (a) would leave the `?` case broken.

## Q3: Which database runs the integration tests?

- **Why it matters**: the old `oracle-sqlcl-mcp` container does not start (memory cgroup error), and the Vagrant VM is not wanted.
- **Options**: (a) `make db-start` (fresh `gvenzl/oracle-xe:21-slim` container `sqlcl-itest-xe`), (b) repair the old container.
- **Recommended**: (a).
- **Answer**: (a) - decided by reading `Makefile` (`db-start`, `db-stop`) and by the earlier run that passed 161 integration tests against it.

## Q4: Are unit tests needed beside the integration tests?

- **Why it matters**: the integration suite takes about 13 minutes and needs a database. The quoting is pure string building and is checked cheaply without one.
- **Options**: (a) integration tests only, (b) add unit tests of the command text in `tests/test_sqlcl.py`.
- **Recommended**: (b) - the integration tests prove SQLcl accepts the command, the unit tests keep the quoting from regressing in every CI run.
- **Answer**: (b) - decided by reading `tests/test_sqlcl.py`, which already unit-tests `quote_arg`.

## Q5: Does the fix need a version bump?

- **Why it matters**: the global rule bumps the version when input parameters change. No option changes here, but the previous fix in this repository was bumped on request anyway.
- **Options**: (a) no bump, (b) patch bump to 0.9.1, (c) minor bump to 0.10.0.
- **Recommended**: (b) - a bug fix with no parameter change, and a visible version helps tell fixed installs from stale ones.
- **Answer**: (b) patch bump to 0.9.1 - taken from the recommendation; no parameter changes, so the global rule does not require it. Change on request.

## Q6: What happens to the harness workaround after the fix?

- **Why it matters**: `tests/integration/harness.py` `save_command` quotes the descriptor on its own to work around this bug. After the fix it could call the tool's own quoting. Changing it is not needed for the fix.
- **Options**: (a) leave the harness unchanged, (b) switch it to the tool's quoting.
- **Recommended**: (a) - the harness is the independent reference for what SQLcl accepts, and the scope rule keeps unrelated edits out.
- **Answer**: (a) leave the harness unchanged - taken from the recommendation; revisit on request.

## Resolution Summary

| ID | Status | Carried by |
| -- | ------ | ---------- |
| Q1 | Answered | Phase 1 (xfail tests) |
| Q2 | Answered | Phase 2 |
| Q3 | Answered | Phase 1 (discovery) |
| Q4 | Answered | Phase 2 |
| Q5 | Answered | Phase 2 |
| Q6 | Answered | Phase 2 |
