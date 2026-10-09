"""Command-line interface for sqlcl-conn-mng."""

from __future__ import annotations

import argparse
import fnmatch
import getpass
import json
import logging
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from sqlcl_conn_mng import __version__
from sqlcl_conn_mng import sqlcl as sq
from sqlcl_conn_mng.models import Folder, SavedConnection
from sqlcl_conn_mng.store import ConnectionStore, StoreError, resolve_home

logger = logging.getLogger(__name__)

LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"]
FORMATS = ["table", "json"]
_INFO_FLAGS = ("-h", "--help", "--version")
_NEED_YES = "Refusing to run a destructive command without --yes."


def _add_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=FORMATS,
        default="table",
        help="Output format (default: table).",
    )


def _add_name(parser: argparse.ArgumentParser, help_text: str = "Connection name.") -> None:
    parser.add_argument("--name", required=True, help=help_text)


def _add_selector(parser: argparse.ArgumentParser) -> None:
    """Add the required --name / --filter / --all group (exactly one must be given)."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--name", help="Connection name.")
    group.add_argument(
        "--filter",
        dest="name_filter",
        metavar="PATTERN",
        help="Every connection whose name matches the case-sensitive glob PATTERN, e.g. 'dev_*'.",
    )
    group.add_argument(
        "--all",
        dest="select_all",
        action="store_true",
        help="Every saved connection.",
    )


def _add_filter(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--filter",
        dest="name_filter",
        metavar="PATTERN",
        help="Only connections whose name matches the case-sensitive glob PATTERN, e.g. 'dev_*'.",
    )


def _global_options() -> argparse.ArgumentParser:
    """Build the parent parser holding the options shared by every command."""
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument(
        "--home",
        help="SQLcl store root (default: SQLCL_CONN_HOME, else .sqlcl in the current directory).",
    )
    parent.add_argument(
        "--sqlcl",
        help="Path to the sql executable (default: SQLCL_BIN, else sql on PATH).",
    )
    parent.add_argument(
        "--driver",
        choices=["thin", "thick"],
        default="thin",
        help="JDBC driver; thick omits the -thin flag (default: thin).",
    )
    parent.add_argument(
        "--timeout",
        type=int,
        default=sq.DEFAULT_TIMEOUT,
        help="SQLcl run timeout in seconds (default: 120).",
    )
    parent.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default="INFO",
        help="Application log level (default: INFO).",
    )
    return parent


class CliParser(argparse.ArgumentParser):
    """Top-level parser that remembers its command parsers by name."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.commands: dict[str, argparse.ArgumentParser] = {}


def build_parser() -> CliParser:
    """Build the argument parser. Kept separate so tests can inspect it."""
    parser = CliParser(
        prog="sqlcl-conn-mng",
        usage="%(prog)s COMMAND [options]",
        description=(
            "Inspect and manage Oracle SQLcl saved connections. "
            "The command is the first argument; the global options (--home, --sqlcl, "
            "--driver, --timeout, --log-level) go after it and are listed by "
            "'%(prog)s COMMAND --help'."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    # Consumed by _normalize_argv before parsing; declared here for the help text only.
    parser.add_argument(
        "--command",
        dest="command_option",
        metavar="COMMAND",
        help="Give the command by name when it is not the first argument.",
    )
    global_options = _global_options()
    sub = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="COMMAND",
        parser_class=argparse.ArgumentParser,
        prog=parser.prog,
    )

    p = sub.add_parser(
        "list", parents=[global_options], help="List saved connections (reads files, no SQLcl)."
    )
    p.add_argument("--folder", help="Only connections in this folder or below (default: all).")
    _add_format(p)
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("show", parents=[global_options], help="Show saved connections.")
    _add_selector(p)
    p.add_argument(
        "--check-password",
        action="store_true",
        help="Ask SQLcl whether a password is saved (default: off).",
    )
    _add_format(p)
    p.set_defaults(func=_cmd_show)

    p = sub.add_parser("folders", parents=[global_options], help="Show the folder tree.")
    _add_format(p)
    p.set_defaults(func=_cmd_folders)

    p = sub.add_parser(
        "add", parents=[global_options], help="Connect and save a connection through SQLcl."
    )
    _add_name(p, "Name to save the connection under.")
    p.add_argument("--user", required=True, help="Database user.")
    p.add_argument("--connect-string", required=True, help="Connect string, e.g. //host:1521/svc.")
    p.add_argument("--folder", help="Folder to move the connection into after saving.")
    p.add_argument("--replace", action="store_true", help="Replace an existing connection.")
    p.add_argument(
        "--no-save-password",
        action="store_true",
        help="Do not store the password (default: store it).",
    )
    p.add_argument(
        "--password-env",
        help="Environment variable holding the password (default: prompt).",
    )
    p.set_defaults(func=_cmd_add)

    p = sub.add_parser("delete", parents=[global_options], help="Delete saved connections.")
    _add_selector(p)
    p.add_argument("--yes", action="store_true", help="Confirm the deletion.")
    p.set_defaults(func=_cmd_delete)

    p = sub.add_parser("rename", parents=[global_options], help="Rename a saved connection.")
    _add_name(p, "Current connection name.")
    p.add_argument("--new-name", required=True, help="New connection name.")
    p.set_defaults(func=_cmd_rename)

    p = sub.add_parser("move", parents=[global_options], help="Move connections into a folder.")
    _add_selector(p)
    p.add_argument("--folder", required=True, help="Destination folder, e.g. /dev/local.")
    p.set_defaults(func=_cmd_move)

    p = sub.add_parser("clone", parents=[global_options], help="Clone a saved connection.")
    _add_name(p, "Name of the connection to clone.")
    p.add_argument("--new-name", required=True, help="Name of the clone.")
    p.add_argument("--user", help="User for the clone (default: same as the original).")
    p.add_argument(
        "--no-password",
        action="store_true",
        help="Do not copy the saved password (default: copy it).",
    )
    p.set_defaults(func=_cmd_clone)

    p = sub.add_parser(
        "test", parents=[global_options], help="Test saved connections through SQLcl."
    )
    _add_selector(p)
    p.set_defaults(func=_cmd_test)

    p = sub.add_parser("add-folder", parents=[global_options], help="Create a folder.")
    p.add_argument("--folder", required=True, help="Folder path, e.g. /dev/local.")
    p.set_defaults(func=_cmd_add_folder)

    p = sub.add_parser("delete-folder", parents=[global_options], help="Delete a folder.")
    p.add_argument("--folder", required=True, help="Folder path, e.g. /dev/local.")
    p.add_argument(
        "--force",
        action="store_true",
        help="Also delete the connections inside, permanently (default: off).",
    )
    p.add_argument("--yes", action="store_true", help="Confirm a forced deletion.")
    p.set_defaults(func=_cmd_delete_folder)

    p = sub.add_parser(
        "export", parents=[global_options], help="Write connection metadata (no passwords) as JSON."
    )
    p.add_argument("--output", required=True, help="Path of the JSON file to write.")
    p.set_defaults(func=_cmd_export)
    parser.commands.update(sub.choices)
    return parser


def setup_logging(level: str) -> None:
    """Configure root logging for the run."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    """Render rows as a left-aligned text table."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(cells: Sequence[str]) -> str:
        return "  ".join(c.ljust(widths[i]) for i, c in enumerate(cells)).rstrip()

    lines = [fmt(headers), fmt(["-" * w for w in widths])]
    lines.extend(fmt(row) for row in rows)
    return "\n".join(lines)


def _store(args: argparse.Namespace) -> ConnectionStore:
    return ConnectionStore(resolve_home(args.home))


def _runner(args: argparse.Namespace) -> sq.SqlclRunner:
    return sq.SqlclRunner(
        sq.resolve_sql_path(args.sqlcl),
        str(resolve_home(args.home)),
        args.driver,
        args.timeout,
    )


def _in_folder(conn: SavedConnection, folder: str) -> bool:
    wanted = "/" + folder.strip("/")
    return conn.folder == wanted or conn.folder.startswith(wanted + "/")


def _matches(name: str, pattern: str) -> bool:
    """Return whether name matches the shell-style glob pattern, case-sensitively."""
    return fnmatch.fnmatchcase(name, pattern)


def _select_names(args: argparse.Namespace, store: ConnectionStore) -> list[str]:
    """Resolve --name, --filter or --all to a sorted list of saved connection names."""
    if args.name is not None:
        if store.get(args.name) is None:
            raise ValueError(f"No saved connection named {args.name!r}")
        return [args.name]
    names = sorted(c.name for c in store.connections())
    if args.select_all:
        return names
    return [n for n in names if _matches(n, args.name_filter)]


def _dump(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


def _cmd_list(args: argparse.Namespace) -> int:
    conns = _store(args).connections()
    if args.folder:
        conns = [c for c in conns if _in_folder(c, args.folder)]
    if args.format == "json":
        _dump([c.to_dict() for c in conns])
        return 0
    rows = [[c.name, c.folder, c.type, c.user_name, c.connect_string] for c in conns]
    print(render_table(["name", "folder", "type", "user", "connect string"], rows))
    return 0


def _connection_data(
    args: argparse.Namespace, store: ConnectionStore, conn: SavedConnection
) -> dict[str, Any]:
    data = conn.to_dict()
    data["wallet_present"] = store.has_wallet(conn.id)
    if args.check_password:
        data["password_saved"] = sq.show_connection(_runner(args), conn.name).password_saved
    return data


def _connection_block(conn: SavedConnection, data: dict[str, Any], check_password: bool) -> str:
    lines = [
        f"Name: {conn.name}",
        f"Id: {conn.id}",
        f"Type: {conn.type}",
        f"Connect String: {conn.connect_string}",
        f"User: {conn.user_name}",
        f"Folder: {conn.folder}",
        f"Wallet file: {'present' if data['wallet_present'] else 'missing'}",
    ]
    if check_password:
        lines.append(f"Password: {'saved' if data['password_saved'] else 'not saved'}")
    lines.extend(f"{key}: {value}" for key, value in conn.extra.items())
    return "\n".join(lines)


def _cmd_show(args: argparse.Namespace) -> int:
    store = _store(args)
    conn = store.get(args.name)
    if conn is None:
        raise ValueError(f"No saved connection named {args.name!r}")
    data = _connection_data(args, store, conn)
    if args.format == "json":
        _dump(data)
        return 0
    print(_connection_block(conn, data, args.check_password))
    return 0


def _folder_dict(folder: Folder, names: dict[str, str]) -> dict[str, Any]:
    return {
        "name": folder.name,
        "path": folder.path,
        "connections": [names.get(c, c) for c in folder.connections],
        "folders": [_folder_dict(f, names) for f in folder.folders],
    }


def _folder_lines(folder: Folder, names: dict[str, str], depth: int) -> list[str]:
    indent = "  " * depth
    lines = [f"{indent}{folder.name}/"]
    lines.extend(f"{indent}  {names.get(c, c)}" for c in folder.connections)
    for child in folder.folders:
        lines.extend(_folder_lines(child, names, depth + 1))
    return lines


def _cmd_folders(args: argparse.Namespace) -> int:
    store = _store(args)
    conns = store.connections()
    names = {c.id: c.name for c in conns}
    folders = store.folders()
    root = [c.name for c in conns if c.folder == "/"]
    if args.format == "json":
        _dump({"folders": [_folder_dict(f, names) for f in folders], "root_connections": root})
        return 0
    lines = ["/"]
    lines.extend(f"  {name}" for name in root)
    for folder in folders:
        lines.extend(_folder_lines(folder, names, 1))
    print("\n".join(lines))
    return 0


def _read_password(args: argparse.Namespace) -> str:
    if args.password_env:
        value = os.environ.get(args.password_env)
        if not value:
            raise ValueError(f"Environment variable {args.password_env} is not set or empty")
        return value
    return getpass.getpass("Password: ")


def _cmd_add(args: argparse.Namespace) -> int:
    store = _store(args)
    if store.get(args.name) is not None and not args.replace:
        raise ValueError(f"Connection {args.name!r} already exists; use --replace")
    folder = sq.normalize_folder(args.folder) if args.folder else None
    runner = _runner(args)
    sq.save_connection(
        runner,
        args.name,
        args.user,
        args.connect_string,
        _read_password(args),
        save_password=not args.no_save_password,
        replace=args.replace,
    )
    if store.get(args.name) is None:
        raise sq.SqlclError("SQLcl did not save the connection; check the user and connect string")
    print(f"Connection {args.name} saved")
    if folder:
        print(sq.move_connection(runner, args.name, folder))
    return 0


def _cmd_delete(args: argparse.Namespace) -> int:
    if not args.yes:
        raise ValueError(_NEED_YES)
    print(sq.delete_connection(_runner(args), args.name))
    return 0


def _cmd_rename(args: argparse.Namespace) -> int:
    print(sq.rename_connection(_runner(args), args.name, args.new_name))
    return 0


def _cmd_move(args: argparse.Namespace) -> int:
    print(sq.move_connection(_runner(args), args.name, args.folder))
    return 0


def _cmd_clone(args: argparse.Namespace) -> int:
    runner = _runner(args)
    print(sq.clone_connection(runner, args.name, args.new_name, args.user, args.no_password))
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    print(sq.check_connection(_runner(args), args.name))
    return 0


def _cmd_add_folder(args: argparse.Namespace) -> int:
    print(sq.add_folder(_runner(args), args.folder))
    return 0


def _cmd_delete_folder(args: argparse.Namespace) -> int:
    if args.force and not args.yes:
        raise ValueError(_NEED_YES)
    print(sq.delete_folder(_runner(args), args.folder, args.force))
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    store = _store(args)
    items = []
    for conn in store.connections():
        item = conn.to_dict()
        item["wallet_present"] = store.has_wallet(conn.id)
        items.append(item)
    text = json.dumps({"connections": items}, indent=2, sort_keys=True)
    Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(f"Exported {len(items)} connection(s) to {args.output}")
    return 0


def _normalize_argv(parser: CliParser, argv: Sequence[str]) -> list[str]:
    """Enforce the command placement rules and return argv with the command first.

    The command is either the first argument or the value of one --command option, which
    is moved to the front. Every other placement is a usage error (exit 2).
    """
    args = list(argv)
    commands = parser.commands
    first_is_command = bool(args) and args[0] in commands
    positions = [i for i, a in enumerate(args) if a == "--command" or a.startswith("--command=")]
    if first_is_command:
        if positions:
            parser.error("the command is given twice: as the first argument and with --command")
        return args
    if not positions:
        if any(a in _INFO_FLAGS for a in args):
            return args
        parser.error("the command must be the first argument or be given with --command")
    if len(positions) > 1:
        parser.error("--command may be given only once")
    index = positions[0]
    token = args[index]
    if token.startswith("--command="):
        name = token.split("=", 1)[1]
        rest = args[:index] + args[index + 1 :]
    else:
        if index + 1 >= len(args) or args[index + 1].startswith("-"):
            parser.error("argument --command: expected one argument")
        name = args[index + 1]
        rest = args[:index] + args[index + 2 :]
    return [name, *rest]


def run(args: argparse.Namespace) -> int:
    """Execute the selected subcommand. Returns the process exit code."""
    handler: Callable[[argparse.Namespace], int] = args.func
    return handler(args)


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Returns an exit code instead of calling sys.exit()."""
    parser = build_parser()
    args = parser.parse_args(_normalize_argv(parser, sys.argv[1:] if argv is None else argv))
    setup_logging(args.log_level)

    try:
        return run(args)
    except (sq.SqlclError, StoreError, ValueError, OSError) as exc:
        logger.error("%s", exc)
        return 1
    except KeyboardInterrupt:
        logger.error("Interrupted")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
