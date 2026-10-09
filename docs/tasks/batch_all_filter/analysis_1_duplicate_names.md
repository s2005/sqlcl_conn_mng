# Analysis 1 - Duplicate connection names in a batch

## Decision: Valid — fix applied

`_select_names` now refuses a `--all` or `--filter` selection that contains a name shared by more than one connection, with an `Ambiguous selection` error (exit 1) and no SQLcl call. `--name` is unchanged. Superseded in part by analysis 2: the guard no longer applies to metadata-only `show`.

**Why:** every SQLcl action used here (`connmgr test`, `move`, `delete`) addresses a connection by name only, so targeting by ID is not possible and acting per name would hit the same connection twice. `import_store` in the integration tests really contains two connections per `imp1` to `imp3`. Rejecting the ambiguous batch is the smallest change that cannot act on the wrong connection; handling duplicates explicitly would need SQLcl support that does not exist. A batch whose matches are all unique still runs.

**Commit:** 1cf1f17 - fix(cli): refuse a batch that selects duplicate connection names (PR #3 review)
