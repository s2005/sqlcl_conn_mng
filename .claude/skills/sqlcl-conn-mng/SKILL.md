---
name: sqlcl-conn-mng
description: Manage Oracle SQLcl saved connections in this project's .sqlcl store with the sqlcl-conn-mng CLI - list, show, check whether a password is saved, add, delete, rename, move, clone, test, create and delete folders, and export metadata. Use when asked to inspect, add, change, test or organise SQLcl saved connections or connection folders, to find a connection's user or connect string, or to check whether a saved connection works.
---

# sqlcl-conn-mng

Drive the globally installed `sqlcl-conn-mng` CLI to inspect and manage SQLcl saved connections. The full option reference is in the `README.md` of the source repository, <https://github.com/s2005/sqlcl_conn_mng>, and its "Store format" section describes the connection store.

## Prerequisites

This skill assumes `sqlcl-conn-mng` is installed globally and on `PATH`. Check before the first command:

```bash
sqlcl-conn-mng --version
```

If the command is not found, install it from the source repository, then open a new terminal and repeat the check:

```bash
uv tool install git+https://github.com/s2005/sqlcl_conn_mng.git
uv tool update-shell
```

Installing needs [uv](https://docs.astral.sh/uv/). Do not fall back to `uv run` from a checkout.

## Ground rules

- Run every command from `<repo-root>` and always pass `--home .sqlcl` explicitly. That store is `<repo-root>/.sqlcl`.
- Never point the tool, or `sql`, at `<home>/.sqlcl` in the user's home directory, and never read, list or modify it. It holds the user's real connections.
- Never print, `cat`, `grep` or copy `credentials.sso` or `dbtools.properties`. Use `show` and `list` instead; they print metadata only.
- Never commit `.sqlcl/` or a file written by `export` unless the user asks for that file to be committed.
- The command is the first argument and the global options go after it; there are no other positional arguments. A bare command anywhere else is rejected (exit 2); use `--command NAME` then.
- Commands below are written for a POSIX shell with the `MSYS_NO_PATHCONV=1` prefix. Adapt them to the shell you run in, as described in [Operating systems and shells](#operating-systems-and-shells).

```bash
MSYS_NO_PATHCONV=1 sqlcl-conn-mng COMMAND --home .sqlcl [global options] [command options]
```

Global options besides `--home`: `--sqlcl PATH` (else `SQLCL_BIN`, else `sql` on PATH), `--driver thin|thick` (default `thin`), `--timeout SECONDS` (default `120`), `--log-level DEBUG|INFO|WARNING|ERROR`.

## Operating systems and shells

The tool behaves the same on Windows, Linux and macOS. Only the shell syntax around it differs. Identify the shell first, then apply its row.

| Shell | Prefix `MSYS_NO_PATHCONV=1` | Line continuation | Check a variable is set without printing it |
| --- | --- | --- | --- |
| Git Bash or MSYS2 on Windows | required on every command | `\` | `[ -n "${DB_PASSWORD}" ] && echo "DB_PASSWORD set"` |
| bash or zsh on Linux, macOS or WSL | harmless, keep or drop it | `\` | `[ -n "${DB_PASSWORD}" ] && echo "DB_PASSWORD set"` |
| PowerShell on Windows, Linux or macOS | drop it, it is a syntax error | `` ` `` | `if ($env:DB_PASSWORD) { 'DB_PASSWORD set' }` |
| cmd.exe on Windows | drop it, it is a syntax error | `^` | `if defined DB_PASSWORD echo DB_PASSWORD set` |

Why Git Bash needs the prefix: it rewrites an argument that starts with `/` before the CLI sees it, so `--folder /dev/local` arrives as `C:/Program Files/Git/dev/local` and the tool accepts it silently. Do not work around it with `//dev/local`: that reaches the CLI with both slashes. Shell state does not always persist between commands, so prefix each command rather than relying on one `export MSYS_NO_PATHCONV=1`.

Connection folders such as `/dev/local` are SQLcl folder names, not filesystem paths. Write them with forward slashes on every OS.

SQLcl lookup also differs by OS. On Windows `sql` resolves to `sql.exe` from the SQLcl `bin` folder; on Linux and macOS it is the `sql` script in the same folder. When it is not on `PATH`, pass `--sqlcl <sqlcl-dir>/bin/sql` (`--sqlcl <sqlcl-dir>\bin\sql.exe` on Windows) or set `SQLCL_BIN`:

| Shell | Set `SQLCL_BIN` for the session |
| --- | --- |
| bash, zsh, Git Bash | `export SQLCL_BIN=<sqlcl-dir>/bin/sql` |
| PowerShell | `$env:SQLCL_BIN = '<sqlcl-dir>\bin\sql.exe'` |
| cmd.exe | `set SQLCL_BIN=<sqlcl-dir>\bin\sql.exe` |

The protected user store `<home>/.sqlcl` is `~/.sqlcl` on Linux and macOS and `%USERPROFILE%\.sqlcl` on Windows.

## Read commands (no SQLcl, instant)

These parse the store files directly. Prefer `--format json` when the result is consumed by further steps.

| Task | Command |
| --- | --- |
| List all connections | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng list --home .sqlcl --format json` |
| List a folder and its subfolders | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng list --home .sqlcl --folder /dev --format json` |
| Show one connection | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng show --home .sqlcl --name NAME --format json` |
| Folder tree | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng folders --home .sqlcl --format json` |
| Export metadata to a file | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng export --home .sqlcl --output connections.json` |

Connection names are case-sensitive. `wallet_present` in `show` output only says the wallet file exists; it always exists, so it says nothing about a saved password.

## Commands that run SQLcl

Each starts SQLcl, which takes about 10 seconds. SQLcl always exits 0, so trust this tool's exit code, not SQLcl's.

| Task | Command |
| --- | --- |
| Is a password saved? | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng show --home .sqlcl --name NAME --check-password --format json` |
| Test a connection | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng test --home .sqlcl --name NAME` |
| Rename | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng rename --home .sqlcl --name OLD --new-name NEW` |
| Move into a folder | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng move --home .sqlcl --name NAME --folder /dev/local` |
| Clone | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng clone --home .sqlcl --name NAME --new-name COPY [--user U] [--no-password]` |
| Create a folder | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng add-folder --home .sqlcl --folder /dev/local` |
| Delete an empty folder | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng delete-folder --home .sqlcl --folder /dev/local` |

`test` needs a reachable database. If it fails, report the error text; do not retry with other credentials.

## Adding a connection

`add` saves only if SQLcl can actually connect, so the database must be up. The password must never appear in the conversation, a command line, a file or a commit.

1. Ask the user which environment variable already holds the password. Do not ask them to type or paste the password into the chat.
2. Check the variable is set without printing it, with the check for your shell from [Operating systems and shells](#operating-systems-and-shells).
3. Run, adapting the prefix and line continuation to your shell:

   ```bash
   MSYS_NO_PATHCONV=1 sqlcl-conn-mng add --home .sqlcl --name NAME --user USER \
     --connect-string //host:1521/service --password-env DB_PASSWORD [--folder /dev/local]
   ```

4. Confirm with `show --name NAME --check-password --format json`.

If no variable holds the password, do not run `add` without `--password-env`: it falls back to a hidden interactive prompt that hangs a non-interactive shell. Give the user the full command without `--password-env` to run in their own terminal, then verify with `show`.

Other `add` options: `--replace` overwrites a connection of the same name, `--no-save-password` keeps the password out of the wallet. Names, folders, users and connect strings must not contain a newline, carriage return or double quote.

## Destructive commands

Confirm with the user before running these, naming exactly what will be removed. Run `show` or `list --folder` first so the confirmation names real connections.

| Task | Command |
| --- | --- |
| Delete a connection | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng delete --home .sqlcl --name NAME --yes` |
| Delete a folder and every connection in it | `MSYS_NO_PATHCONV=1 sqlcl-conn-mng delete-folder --home .sqlcl --folder /dev/local --force --yes` |
| Replace an existing connection | `add ... --replace` |

The tool refuses `delete` and `delete-folder --force` without `--yes`. Deleted connections and their saved passwords cannot be recovered.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Operational failure: SQLcl error, unknown connection, refused destructive command. The reason is on stderr. |
| 2 | Invalid command-line usage |

If SQLcl is not found, the error says so: pass `--sqlcl` or set `SQLCL_BIN`.
