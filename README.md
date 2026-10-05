# sqlcl-conn-mng

Inspect and manage [Oracle SQLcl](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/) saved connections.

Read operations (`list`, `show`, `folders`, `export`) parse the SQLcl store files directly and do not need SQLcl. Every write operation runs SQLcl itself, because SQLcl is the only supported writer of the store. The tool never reads `credentials.sso` (it only checks that the file exists) and never writes the store from Python.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/)
- Oracle SQLcl (tested with 25.4.1) for the write commands, `test` and `show --check-password`

## Install

Install `sqlcl-conn-mng` as a global tool straight from the source repository, <https://github.com/s2005/sqlcl_conn_mng>. No checkout is needed:

```bash
uv tool install git+https://github.com/s2005/sqlcl_conn_mng.git
uv tool update-shell
```

To install from a local checkout instead, run this from `<repo-root>`:

```bash
uv tool install --from . sqlcl-conn-mng
uv tool update-shell
```

`uv tool update-shell` adds uv's tool directory to your user `PATH`. Open a new terminal, then confirm the command is found:

```bash
sqlcl-conn-mng --version
```

To upgrade, repeat the install with `--force`:

```bash
uv tool install --force git+https://github.com/s2005/sqlcl_conn_mng.git
```

Development setup, for working on the tool itself:

```bash
uv sync
```

## Install the agent skill

The repository ships an agent skill, `sqlcl-conn-mng`, in `.claude/skills/sqlcl-conn-mng/`. It calls the globally installed `sqlcl-conn-mng` command, so install the tool first (see [Install](#install)). Then add the skill with the [skills](https://www.npmjs.com/package/skills) CLI:

```bash
npx skills add s2005/sqlcl_conn_mng
```

That installs the skill into the current project. Add `-g` to install it for your user instead, and `-a claude-code` to target one agent only:

```bash
npx skills add s2005/sqlcl_conn_mng -g -a claude-code
```

To see what the repository offers without installing anything:

```bash
npx skills add s2005/sqlcl_conn_mng --list
```

## Quick start

These commands are the same in every shell on Windows, Linux and macOS:

```bash
sqlcl-conn-mng list
sqlcl-conn-mng folders
sqlcl-conn-mng show --name my_conn --check-password
```

From a development checkout without the global install, prefix the commands with `uv run`.

Commands with an argument that starts with `/`, such as `--folder /dev/local`, need a `MSYS_NO_PATHCONV=1` prefix in Git Bash. See [Operating systems and shells](#operating-systems-and-shells) before running them.

## Operating systems and shells

The tool runs on Windows, Linux and macOS and behaves the same on each. The examples in the rest of this README are written for a POSIX shell with a `MSYS_NO_PATHCONV=1` prefix; adapt them to your shell:

| Shell | `MSYS_NO_PATHCONV=1` prefix | Line continuation |
| --- | --- | --- |
| Git Bash or MSYS2 on Windows | required | `\` |
| bash or zsh on Linux, macOS or WSL | harmless, keep or drop it | `\` |
| PowerShell on Windows, Linux or macOS | drop it | `` ` `` |
| cmd.exe on Windows | drop it | `^` |

Git Bash needs the prefix because it rewrites an argument that starts with `/` before the tool sees it, so `--folder /dev/local` arrives as `C:/Program Files/Git/dev/local` and is accepted without an error. Writing `//dev/local` is not a workaround, because the tool then receives both slashes. To set it once per session instead, run `export MSYS_NO_PATHCONV=1`.

The same command in each shell:

```bash
# bash, zsh, Git Bash
MSYS_NO_PATHCONV=1 sqlcl-conn-mng list --folder /dev --format json
```

```powershell
# PowerShell
sqlcl-conn-mng list --folder /dev --format json
```

```bat
:: cmd.exe
sqlcl-conn-mng list --folder /dev --format json
```

Connection folders such as `/dev/local` are SQLcl folder names, not filesystem paths, so they use forward slashes on every OS.

SQLcl is found through `--sqlcl`, then `SQLCL_BIN`, then `sql` on `PATH`. On Windows that resolves to `sql.exe` in the SQLcl `bin` folder; on Linux and macOS it is the `sql` script in the same folder. To set `SQLCL_BIN` for one session:

| Shell | Command |
| --- | --- |
| bash, zsh, Git Bash | `export SQLCL_BIN=<sqlcl-dir>/bin/sql` |
| PowerShell | `$env:SQLCL_BIN = '<sqlcl-dir>\bin\sql.exe'` |
| cmd.exe | `set SQLCL_BIN=<sqlcl-dir>\bin\sql.exe` |

SQLcl's own default store, used when no `-home` is given, is `~/.sqlcl` on Linux and macOS and `%USERPROFILE%\.sqlcl` on Windows. This tool always passes `-home`, so it never touches that store unless `--home` points at it.

## CLI reference

Usage: `sqlcl-conn-mng COMMAND [options]`. The command is the first argument. The global options go after it, mixed freely with the command's own options: `sqlcl-conn-mng list --home .sqlcl --format json`. There are no other positional arguments.

When the command is not the first argument, give it with `--command NAME` or `--command=NAME`, at any position: `sqlcl-conn-mng --command list --home .sqlcl --format json`. An unknown name is a usage error that lists the valid commands.

These command lines are rejected with a usage error and exit code 2:

- A bare command that is not the first argument, such as `sqlcl-conn-mng --log-level DEBUG list`.
- No command at all.
- The command given twice: as the first argument and with `--command`, or `--command` more than once, even when both name the same command.
- `--command` with no value.

### Global options

Accepted after the command (`sqlcl-conn-mng COMMAND --help` lists them), except `--command`, `--version` and the top-level `--help`.

| Option | Required | Default | Description |
| --- | --- | --- | --- |
| `--home` | no | `SQLCL_CONN_HOME`, else `.sqlcl` in the current directory | SQLcl store root, passed to SQLcl as `-home`. |
| `--sqlcl` | no | `SQLCL_BIN`, else `sql` on PATH | Path to the `sql` executable. |
| `--driver` | no | `thin` | `thin` or `thick`. `thick` omits the `-thin` flag. |
| `--timeout` | no | `120` | SQLcl run timeout in seconds. |
| `--log-level` | no | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `--command` | no | - | Name of the command, for use when it is not the first argument. See above. |
| `--version` | no | - | Print the version and exit. |
| `--help` | no | - | Print usage and exit. |

### Commands

| Command | Option | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `list` | `--folder` | no | all | Only connections in this folder or below. |
| `list` | `--format` | no | `table` | `table` or `json`. |
| `show` | `--name` | yes | - | Connection name (case-sensitive). |
| `show` | `--check-password` | no | off | Ask SQLcl whether a password is saved. |
| `show` | `--format` | no | `table` | `table` or `json`. |
| `folders` | `--format` | no | `table` | `table` or `json`. |
| `add` | `--name` | yes | - | Name to save the connection under. |
| `add` | `--user` | yes | - | Database user. |
| `add` | `--connect-string` | yes | - | Connect string, for example `//host:1521/svc`. |
| `add` | `--folder` | no | root | Existing folder to move the connection into after saving. |
| `add` | `--replace` | no | off | Replace an existing connection of the same name. |
| `add` | `--no-save-password` | no | off | Do not store the password. |
| `add` | `--password-env` | no | prompt | Environment variable holding the password; otherwise a hidden prompt. |
| `delete` | `--name` | yes | - | Connection to delete. |
| `delete` | `--yes` | yes in practice | off | Confirm the deletion; refused without it. |
| `rename` | `--name` | yes | - | Current connection name. |
| `rename` | `--new-name` | yes | - | New connection name. |
| `move` | `--name` | yes | - | Connection to move. |
| `move` | `--folder` | yes | - | Destination folder, for example `/dev/local`. |
| `clone` | `--name` | yes | - | Connection to clone. |
| `clone` | `--new-name` | yes | - | Name of the clone. |
| `clone` | `--user` | no | same user | User for the clone. |
| `clone` | `--no-password` | no | off | Do not copy the saved password. |
| `test` | `--name` | yes | - | Connection to test. |
| `add-folder` | `--folder` | yes | - | Folder path to create, for example `/dev/local`. |
| `delete-folder` | `--folder` | yes | - | Folder path to delete. |
| `delete-folder` | `--force` | no | off | Also delete the connections inside, permanently. |
| `delete-folder` | `--yes` | with `--force` | off | Confirm a forced deletion; refused without it. |
| `export` | `--output` | yes | - | JSON file to write with all connection metadata. |

Notes:

- The password is read from the variable named by `--password-env` or a hidden prompt. It travels to SQLcl on stdin only, never on the command line.
- `add` saves the connection only if SQLcl can connect with the given credentials. Without `--no-save-password` the password is stored in the SQLcl wallet.
- Names, folders, users and connect strings must not contain a newline, carriage return or double quote. A password must not contain a newline or carriage return, and must not contain both `"` and `'`.
- `export` writes metadata only: no passwords and no wallet bytes.

## Environment variables

| Variable | Used by | Description |
| --- | --- | --- |
| `SQLCL_CONN_HOME` | all commands | Store root when `--home` is not given. |
| `SQLCL_BIN` | commands that run SQLcl | Path to `sql` when `--sqlcl` is not given. |
| Name given to `--password-env` | `add` | Holds the password. |

## Examples

```bash
# Read-only listing as JSON
MSYS_NO_PATHCONV=1 sqlcl-conn-mng list --folder /dev --format json

# Save a connection with the password from an environment variable, then file it
MSYS_NO_PATHCONV=1 sqlcl-conn-mng add --name dev_local --user scott \
  --connect-string //localhost:1521/freepdb1 --password-env DB_PASSWORD --folder /dev/local

# Folder management
MSYS_NO_PATHCONV=1 sqlcl-conn-mng add-folder --folder /dev/local
MSYS_NO_PATHCONV=1 sqlcl-conn-mng delete-folder --folder /dev/local --force --yes

# Export metadata
MSYS_NO_PATHCONV=1 sqlcl-conn-mng export --output connections.json
```

## Store format

Summary of the SQLcl 25.4.1 store, observed empirically (the format is not documented by Oracle):

- The store root defaults to `.sqlcl` in the current directory; run the tool from `<repo-root>` so it uses `<repo-root>/.sqlcl`. That folder is gitignored because it holds wallets with saved passwords. SQLcl's own default when no `-home` is given is `<home>/.sqlcl` in the user's home directory; this tool always passes `-home` explicitly. SQLcl's `-home <dir>` option points at that root directly.
- `<home>/connections/<id>/` holds one saved connection. `<id>` is an opaque 22-character string (`[A-Za-z0-9_-]`) and is not derived from the name, so connections are looked up by the `name` property.
- Each connection directory has `dbtools.properties` and `credentials.sso`. The latter is an Oracle auto-login wallet and always exists, with or without a saved password, so its size says nothing about password presence. Use `show --check-password` for that.
- `dbtools.properties` is a Java properties file with the keys `name`, `type`, `connectionString` and `userName`. It uses Java escaping, for example `//host\:1521/svc`. Unknown keys are kept in `extra`.
- Folders live in `<home>/connection_folders/folders.json` as nested objects with `name`, `connections` (connection ids) and `folders`. A connection not referenced by any folder is at the root `/`. The file may be absent.
- SQLcl always exits with status 0, even on failure, so this tool detects success from SQLcl's output text.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Operational failure (SQLcl error, unknown connection, refused destructive command) |
| 2 | Invalid command-line usage |

## Development

```bash
uv sync                      # install dependencies
uv run pytest                # run unit tests
uv run pytest -m integration # run the real-SQLcl test (needs SQLcl)
uv run pytest --cov          # run tests with coverage
uv run ruff check --fix .    # lint and autofix
uv run ruff format .         # format
uv run mypy                  # type check
```

## Testing

Unit tests use temporary fake stores only and never touch a real store. The `integration` test runs real SQLcl against a temporary store and is skipped when `sql` cannot be found (set `SQLCL_BIN` to point at it). SQLcl takes about 10 seconds to start.

## License

MIT
