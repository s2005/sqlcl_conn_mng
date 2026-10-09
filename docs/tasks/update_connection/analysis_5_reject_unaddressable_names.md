# Analysis 5 - Reject names SQLcl cannot address

## Decision: Rejected â€” SQLcl 25.4.1 accepts and resolves all five characters

Probed in a temporary store: `connmgr clone` created connections named `a/b1`, `a#b1`, `a\b1`, `a'b1` and `a?b1`; `connmgr show` and `connect -name` resolved each one (the connect then failed only on the unreachable fixture host, ORA-17868). No character in the reported list is forbidden, so no extra name check is added and `update` keeps the same name rules as `add` and `rename`.

**Why:** a check against a list that SQLcl does not enforce would refuse names SQLcl itself creates and addresses. `update` stays consistent with `add` and `rename`, which share `validate_value` (newline, carriage return and double quote are the only values SQLcl cannot take safely on its command line).
