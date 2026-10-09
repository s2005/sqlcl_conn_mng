# sqlcl-conn-mng

Inspect and manage [Oracle SQLcl](https://www.oracle.com/database/sqldeveloper/technologies/sqlcl/) saved connections.

Read operations (`list`, `show`, `folders`, `export`) parse the SQLcl store files directly and do not need SQLcl. Every write operation runs SQLcl itself, because SQLcl is the only supported writer of the store, with one exception: `update` changes a name, user or connect string by rewriting that connection's `dbtools.properties` from Python. The tool never reads or writes `credentials.sso` (it only checks that the file exists), and never writes `folders.json`.

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
| `list` | `--filter` | no | all | Only connections whose name matches the glob; combines with `--folder` as AND. |
| `list` | `--format` | no | `table` | `table` or `json`. |
| `show` | `--name` / `--filter` / `--all` | one of the three | - | One connection by exact name (case-sensitive), every name matching a glob, or every connection. |
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
| `delete` | `--name` / `--filter` / `--all` | one of the three | - | Connection(s) to delete. |
| `delete` | `--yes` | yes in practice | off | Confirm the deletion; refused without it. |
| `rename` | `--name` | yes | - | Current connection name. |
| `rename` | `--new-name` | yes | - | New connection name. |
| `update` | `--name` | yes | - | Connection to update (one connection; no `--filter` or `--all`). |
| `update` | `--new-name` | no | unchanged | New connection name. |
| `update` | `--user` | no | unchanged | New database user. |
| `update` | `--connect-string` | no | unchanged | New connect string. |
| `update` | `--password-env` | no | unchanged | Change the password to the value of this environment variable. Excludes `--prompt-password`. |
| `update` | `--prompt-password` | no | off | Change the password to a value typed at a hidden prompt. Excludes `--password-env`. |
| `update` | `--no-save-password` | no | off | With a new password: do not store it. Needs a password source. |
| `move` | `--name` / `--filter` / `--all` | one of the three | - | Connection(s) to move. |
| `move` | `--folder` | yes | - | Destination folder, for example `/dev/local`. |
| `clone` | `--name` | yes | - | Connection to clone. |
| `clone` | `--new-name` | yes | - | Name of the clone. |
| `clone` | `--user` | no | same user | User for the clone. |
| `clone` | `--no-password` | no | off | Do not copy the saved password. |
| `test` | `--name` / `--filter` / `--all` | one of the three | - | Connection(s) to test. |
| `add-folder` | `--folder` | yes | - | Folder path to create, for example `/dev/local`. |
| `delete-folder` | `--folder` | yes | - | Folder path to delete. |
| `delete-folder` | `--force` | no | off | Also delete the connections inside, permanently. |
| `delete-folder` | `--yes` | with `--force` | off | Confirm a forced deletion; refused without it. |
| `export` | `--output` | yes | - | JSON file to write with the connection metadata. |
| `export` | `--filter` | no | all | Only connections whose name matches the glob. |

Notes:

- The password is read from the variable named by `--password-env` or a hidden prompt. It travels to SQLcl on stdin only, never on the command line.
- `add` saves the connection only if SQLcl can connect with the given credentials. Without `--no-save-password` the password is stored in the SQLcl wallet.
- Names, folders, users and connect strings must not contain a newline, carriage return or double quote. A password must not contain a newline or carriage return, and must not contain both `"` and `'`.
- `export` writes metadata only: no passwords and no wallet bytes.
- `update` needs at least one change option; none, an unknown name, or `--no-save-password` alone exits 1 and writes nothing. Giving both `--password-env` and `--prompt-password` is a usage error (exit code 2).
- `update` without a password source writes `--new-name`, `--user` and `--connect-string` into the connection's `dbtools.properties` and starts no SQLcl. Only those three values change; the connection id, every other key and its order, `folders.json` and `credentials.sso` stay byte-identical. The file is replaced atomically. A file with a comment or a continuation line is refused, because the rewrite would lose that text. The new values are not checked against the database.
- A connection imported from SQL Developer has type `ORACLE_BASIC`, and SQLcl reads its target from `host`, `port` and `serviceName` and ignores `connectionString`. So `--connect-string` on such a connection rewrites the file the way SQLcl does when it saves the connection again: `type` becomes `ORACLE_DATABASE`, `host`, `port` and `serviceName` are removed, and the keys are ordered `name`, `type`, `connectionString`, `userName`. `--connect-string` on any other connection type is refused before anything is written or any password is replaced (exit code 1). `--user` and `--new-name` never change the type or those keys.
- A saved password is not changed by a user or connect string update without a password source, so it can stop matching the new user or URL. Give a password source to replace it.
- `update` with `--password-env` or `--prompt-password` replaces the password with `connect -save NAME -replace` through SQLcl, using the new or current user and connect string (for an imported connection, the current target `//host:port/serviceName` is built from its `host`, `port` and `serviceName` keys). The connection is changed only when SQLcl connects; a failed connect leaves the store unchanged. The password is stored unless `--no-save-password` is given, and the connection id is kept.
- `update` checks everything first (the connection exists and its name is unique, the values pass the same checks as `add`, a new name differs case-insensitively from every other connection), then runs the password step, then writes the file. If the file write fails after the password step, the error says the password was already replaced.

### Batch selection

`test`, `show`, `delete` and `move` take exactly one of `--name NAME`, `--filter PATTERN` or `--all`. Giving none, or more than one, is a usage error (exit code 2). `list` and `export` take an optional `--filter`. The other commands are unchanged.

- `--filter PATTERN` is a shell-style glob (`*`, `?`, `[...]`) matched case-sensitively against the whole connection name, not against the folder. Quote the pattern so the shell does not expand it: `--filter 'dev_*'`. `--filter '*'` equals `--all`.
- The names are resolved once, sorted, before the first action runs. A batch that selects a name shared by more than one connection (possible after a SQLcl import with `-duplicates REPLACE`) is refused with exit code 1 and nothing is run, because SQLcl selects connections by name only. `show` without `--check-password` reads files only, so it still lists every duplicate record. With `--name`, output and exit codes are unchanged, and a wildcard in the value is not expanded.
- With `--all` or `--filter`, `test`, `delete` and `move` process every selected connection even when one fails. They print `[OK] NAME` or `[FAIL] NAME: reason` per connection, then `Summary: N ok, M failed`. The exit code is 1 when any connection failed or when nothing matched (`No connections match ...`).
- `delete` with `--all` or `--filter` still needs `--yes`; without it nothing is deleted. With it, the matched names are printed before the first deletion.
- `show` prints a JSON list (`--format json`) or the usual blocks separated by a blank line. With `--check-password`, a failing connection is logged to stderr, the others are still shown, and the exit code is 1.

## Environment variables

| Variable | Used by | Description |
| --- | --- | --- |
| `SQLCL_CONN_HOME` | all commands | Store root when `--home` is not given. |
| `SQLCL_BIN` | commands that run SQLcl | Path to `sql` when `--sqlcl` is not given. |
| Name given to `--password-env` | `add`, `update` | Holds the password. |

## Examples

```bash
# Read-only listing as JSON
MSYS_NO_PATHCONV=1 sqlcl-conn-mng list --folder /dev --format json

# Save a connection with the password from an environment variable, then file it
MSYS_NO_PATHCONV=1 sqlcl-conn-mng add --name dev_local --user scott \
  --connect-string //localhost:1521/freepdb1 --password-env DB_PASSWORD --folder /dev/local

# Change only the user, or only the password (from an environment variable)
sqlcl-conn-mng update --name dev_local --user hr
sqlcl-conn-mng update --name dev_local --password-env DB_PASSWORD

# Change the name, connect string and password in one call
sqlcl-conn-mng update --name dev_local --new-name dev_main \
  --connect-string //localhost:1521/freepdb2 --prompt-password

# Test every connection, or only the ones named dev_*
sqlcl-conn-mng test --all
sqlcl-conn-mng test --filter 'dev_*'

# Move matching connections into an existing folder, then delete them
MSYS_NO_PATHCONV=1 sqlcl-conn-mng move --filter 'tmp_*' --folder /scratch
sqlcl-conn-mng delete --filter 'tmp_*' --yes

# Folder management
MSYS_NO_PATHCONV=1 sqlcl-conn-mng add-folder --folder /dev/local
MSYS_NO_PATHCONV=1 sqlcl-conn-mng delete-folder --folder /dev/local --force --yes

# Export metadata
MSYS_NO_PATHCONV=1 sqlcl-conn-mng export --output connections.json
sqlcl-conn-mng export --output dev.json --filter 'dev_*'
```

## Store format

Summary of the SQLcl 25.4.1 store, observed empirically (the format is not documented by Oracle):

- The store root defaults to `.sqlcl` in the current directory; run the tool from `<repo-root>` so it uses `<repo-root>/.sqlcl`. That folder is gitignored because it holds wallets with saved passwords. SQLcl's own default when no `-home` is given is `<home>/.sqlcl` in the user's home directory; this tool always passes `-home` explicitly. SQLcl's `-home <dir>` option points at that root directly.
- `<home>/connections/<id>/` holds one saved connection. `<id>` is an opaque 22-character string (`[A-Za-z0-9_-]`) and is not derived from the name, so connections are looked up by the `name` property.
- Each connection directory has `dbtools.properties` and `credentials.sso`. The latter is an Oracle auto-login wallet and always exists, with or without a saved password, so its size says nothing about password presence. Use `show --check-password` for that.
- `dbtools.properties` is a Java properties file with the keys `name`, `type`, `connectionString` and `userName`. It uses Java escaping, for example `//host\:1521/svc`. Unknown keys are kept in `extra`. `update` rewrites this file with the same escaping (UTF-8, LF endings, no header), which SQLcl reads back.
- Folders live in `<home>/connection_folders/folders.json` as nested objects with `name`, `connections` (connection ids) and `folders`. A connection not referenced by any folder is at the root `/`. The file may be absent.
- SQLcl always exits with status 0, even on failure, so this tool detects success from SQLcl's output text.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success |
| 1 | Operational failure (SQLcl error, unknown connection, refused destructive command), a batch with a failed connection, or a batch selection that matched nothing |
| 2 | Invalid command-line usage |

## Development

Every check and test runs through a `make` target, so local runs and the CI workflow use the same commands. Run the targets from the repository root. On Windows, install GNU Make with Chocolatey (`choco install make`) and run them from Git Bash. Run `uv sync` once to install the dependencies.

| Target | What it does |
| ------ | ------------ |
| `make check` | Lint, format check and type check |
| `make unit` | Unit tests; the integration tests are deselected |
| `make integration` | Integration tests against a real SQLcl (see "Testing") |
| `make sqlcl` | Download and unpack the pinned SQLcl release into a local cache directory; does nothing when it is already there |
| `make db-start` | Start the disposable test database container and wait until it accepts connections |
| `make db-stop` | Remove the test database container |
| `make print-sqlcl-version` | Print the pinned SQLcl release |
| `make print-sqlcl-dir` | Print the SQLcl cache directory |
| `make print-sqlcl-bin` | Print the `bin` directory of the unpacked SQLcl release |

`PYTEST_ARGS` adds arguments to `make unit` and `make integration`, for example `make integration PYTEST_ARGS=tests/integration/test_folders_compat.py` to run one file, or `make unit PYTEST_ARGS=--cov` for coverage.

## Testing

Unit tests use temporary fake stores only and never touch a real store.

Integration tests (`make integration`) build connection stores in temporary directories with real SQLcl, then check that this tool reads them and operates on them correctly, and that SQLcl still writes the store format this tool expects. They never touch `<repo-root>/.sqlcl` or `<home>/.sqlcl`.

- The tests find SQLcl from `SQLCL_BIN`, else `sql` on `PATH`. When neither resolves, every integration test skips with a reason. On Windows, `SQLCL_BIN` must name `sql.exe`, not the extensionless `sql` shell script next to it.
- Without an installed SQLcl, `make sqlcl` downloads the pinned release; put the directory printed by `make print-sqlcl-bin` on `PATH`.
- SQLcl takes 10-20 seconds per start, so a full run takes several minutes.

The saved-password scenarios need a live database. They read three variables and skip, naming the missing ones, when any is unset:

| Variable | Meaning | Default under `make` |
| -------- | ------- | -------------------- |
| `SQLCL_ITEST_CONNECT` | Connect string of the test database, `//host:port/service` | The database started by `make db-start` |
| `SQLCL_ITEST_USER` | Database user the scenarios connect as | The user `make db-start` creates |
| `SQLCL_ITEST_PASSWORD` | That user's password | None; the scenarios skip without it |

`make db-start` starts the test database with Podman, creates the user with the password from `SQLCL_ITEST_PASSWORD`, and waits until the database is ready. It refuses to run when `SQLCL_ITEST_PASSWORD` is unset, and it hands the password to the container by variable name, so make never prints it. Set `ENGINE=docker` to use Docker instead of Podman. `make db-stop` removes the container. A full local run with the database, entering the password without echoing it:

```bash
read -rs SQLCL_ITEST_PASSWORD && export SQLCL_ITEST_PASSWORD
make db-start
make integration
make db-stop
```

The workflow `.github/workflows/ci.yml` runs on pull requests, on pushes to `main` and on manual dispatch, on Ubuntu and Windows. Both jobs run `make check`, `make unit`, `make sqlcl` (cached per SQLcl release) and `make integration`. The Ubuntu job also generates a random database password for the run, masks it in the log, and wraps the integration tests in `make db-start` and `make db-stop`, so the saved-password scenarios run there. The Windows runner cannot run the Linux database container, so on Windows those scenarios skip with a reason. The workflow needs no repository secret.

## License

MIT
