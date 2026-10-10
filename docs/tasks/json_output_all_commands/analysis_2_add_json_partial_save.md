# Analysis 2 - Report the persisted save when a JSON folder move fails

## Decision: Valid â€” fix applied

In JSON mode a failing move now re-raises the same exception type with the message `Connection NAME saved, but moving it to FOLDER failed: <reason>`, so the error object and the stderr log both state the partial save. The error object keeps the REQ-5 keys; table mode is untouched.

**Why:** Table mode shows the save line before the failing move (analysis 1); JSON mode must not lose that information, and REQ-6 allows only one document on stdout.

**Commit:** 9f74003 - fix(cli): report the persisted save when a json add folder move fails (PR #5 review)
