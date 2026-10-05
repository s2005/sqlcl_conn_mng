# Agent Guidance

## SQLcl connection store

- The SQLcl connection store for this project is the `.sqlcl` subfolder of the repository root, `<repo-root>/.sqlcl`. Use it by default.
- Point every call at it explicitly, run from `<repo-root>`: `sql -home .sqlcl ...` and `uv run sqlcl-conn-mng COMMAND --home .sqlcl ...`. The CLI defaults to `.sqlcl` in the current directory, so run it from `<repo-root>`; SQLcl itself defaults to `<home>/.sqlcl` in the user's home directory when `-home` is omitted, which touches the wrong store.
- Do not read, list or modify `<home>/.sqlcl`. It holds the user's real saved connections.
- `.sqlcl/` is gitignored because it holds `credentials.sso` wallets with saved passwords. Never commit it, and never print the contents of `credentials.sso` or the values in `dbtools.properties`.
- The store format is described in the "Store format" section of `README.md`.
