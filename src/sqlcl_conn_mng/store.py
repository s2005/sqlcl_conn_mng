"""Access to the SQLcl saved-connection store: read everything, write dbtools.properties and copies."""

from __future__ import annotations

import base64
import contextlib
import json
import os
import re
import secrets
import shutil
import tempfile
from collections.abc import Container, Mapping
from pathlib import Path
from typing import Any

from sqlcl_conn_mng.models import ROOT_FOLDER, Folder, SavedConnection
from sqlcl_conn_mng.properties import format_properties, parse_properties

HOME_ENV_VAR = "SQLCL_CONN_HOME"
PROPERTIES_FILE = "dbtools.properties"
WALLET_FILE = "credentials.sso"
CONNECTIONS_DIR = "connections"
FOLDERS_FILE = Path("connection_folders") / "folders.json"
KNOWN_KEYS = {"name", "type", "connectionString", "userName"}
WRITABLE_KEYS = frozenset({"name", "connectionString", "userName"})
TYPE_DATABASE = "ORACLE_DATABASE"
TYPE_BASIC = "ORACLE_BASIC"
# Types whose connect string SQLcl reads from connectionString (TYPE_DATABASE), or can be
# converted to that form the way SQLcl does itself on connect -save -replace (TYPE_BASIC).
CONNECT_STRING_TYPES = frozenset({TYPE_DATABASE, TYPE_BASIC})
# The keys that give an ORACLE_BASIC connection its target; SQLcl reads them instead of
# connectionString and drops them when it rewrites the connection as ORACLE_DATABASE.
BASIC_TARGET_KEYS = frozenset({"host", "port", "serviceName"})
_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{22}")
# Prefix of the staging directory of a copy; the dot keeps it from matching _ID_PATTERN.
_STAGING_PREFIX = ".copy."
_COMMENT_MARKERS = "#!"
_LINE_BREAK = re.compile(r"\r\n|\r|\n")


class StoreError(Exception):
    """Raised when the store cannot be read."""


def resolve_home(option: str | None, environ: Mapping[str, str] | None = None) -> Path:
    """Resolve the store root: option, then SQLCL_CONN_HOME, then ./.sqlcl in the current directory."""
    env = os.environ if environ is None else environ
    if option:
        return Path(option).expanduser()
    from_env = env.get(HOME_ENV_VAR)
    if from_env:
        return Path(from_env).expanduser()
    return Path.cwd() / ".sqlcl"


def new_connection_id(existing: Container[str]) -> str:
    """Return a new connection id: 22 URL-safe characters from 16 random bytes, not in existing."""
    while True:
        candidate = base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode("ascii")
        if candidate not in existing:
            return candidate


def _read_text(path: Path) -> str:
    data = path.read_bytes()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _build_folder(node: Any, parent: str) -> Folder:
    if not isinstance(node, dict) or not isinstance(node.get("name"), str):
        raise StoreError("Malformed folders.json: folder entry without a name")
    path = parent.rstrip("/") + "/" + node["name"]
    connections = [c for c in node.get("connections", []) if isinstance(c, str)]
    children = [_build_folder(child, path) for child in node.get("folders", [])]
    return Folder(name=node["name"], path=path, connections=connections, folders=children)


def walk_folders(folders: list[Folder]) -> list[Folder]:
    """Flatten a folder tree depth-first."""
    flat: list[Folder] = []
    for folder in folders:
        flat.append(folder)
        flat.extend(walk_folders(folder.folders))
    return flat


def _has_comment_or_continuation(text: str) -> bool:
    """Report a comment line or a continuation line, which a rewrite would not preserve."""
    for raw in _LINE_BREAK.split(text):
        line = raw.lstrip(" \t\f")
        if line.startswith(tuple(_COMMENT_MARKERS)):
            return True
        if (len(line) - len(line.rstrip("\\"))) % 2 == 1:
            return True
    return False


def _with_connect_string_form(props: dict[str, str]) -> dict[str, str]:
    """Return props in the form where connectionString is what SQLcl reads.

    An ORACLE_BASIC connection (imported from SQL Developer) is read from host, port and
    serviceName, so a new connectionString would be ignored. SQLcl itself rewrites such a
    connection as ORACLE_DATABASE without those keys when it saves it again; this does the same,
    in the key order SQLcl writes. ORACLE_DATABASE props are returned unchanged.
    """
    kind = props.get("type", "")
    if kind == TYPE_DATABASE:
        return props
    if kind != TYPE_BASIC:
        raise StoreError(
            f"Cannot change the connect string of a connection of type {kind!r}: "
            f"only {TYPE_DATABASE} and {TYPE_BASIC} are supported"
        )
    converted = {"name": props.get("name", ""), "type": TYPE_DATABASE}
    converted["connectionString"] = props.get("connectionString", "")
    if "userName" in props:
        converted["userName"] = props["userName"]
    skipped = BASIC_TARGET_KEYS | set(converted)
    converted.update({k: v for k, v in props.items() if k not in skipped})
    return converted


class ConnectionStore:
    """View of a SQLcl store root (the directory given to -home).

    Everything is read-only except update_properties, which rewrites one dbtools.properties,
    and copy_connection_to / remove_connection_dir, which add and remove whole connection
    directories. The wallet is never opened and folders.json is never written.
    """

    def __init__(self, home: Path) -> None:
        self.home = home

    def folders(self) -> list[Folder]:
        """Return the top-level folders (empty when folders.json is absent)."""
        path = self.home / FOLDERS_FILE
        if not path.is_file():
            return []
        try:
            data = json.loads(_read_text(path))
        except json.JSONDecodeError as exc:
            raise StoreError(f"Malformed folders.json: {exc}") from exc
        if not isinstance(data, dict):
            raise StoreError("Malformed folders.json: top level is not an object")
        return [_build_folder(node, "") for node in data.get("folders", [])]

    def folder_paths(self) -> dict[str, str]:
        """Map connection id to its folder path; unreferenced ids are absent."""
        mapping: dict[str, str] = {}
        for folder in walk_folders(self.folders()):
            for conn_id in folder.connections:
                mapping.setdefault(conn_id, folder.path)
        return mapping

    def connections(self) -> list[SavedConnection]:
        """Return all saved connections sorted by name."""
        root = self.home / CONNECTIONS_DIR
        if not root.is_dir():
            return []
        paths = self.folder_paths()
        result: list[SavedConnection] = []
        for entry in root.iterdir():
            props_file = entry / PROPERTIES_FILE
            if not entry.is_dir() or not _ID_PATTERN.fullmatch(entry.name):
                continue
            if not props_file.is_file():
                continue
            props = parse_properties(_read_text(props_file))
            result.append(
                SavedConnection(
                    id=entry.name,
                    name=props.get("name", ""),
                    type=props.get("type", ""),
                    connect_string=props.get("connectionString", ""),
                    user_name=props.get("userName", ""),
                    folder=paths.get(entry.name, ROOT_FOLDER),
                    path=str(entry),
                    extra={k: v for k, v in props.items() if k not in KNOWN_KEYS},
                )
            )
        return sorted(result, key=lambda c: (c.name, c.id))

    def get(self, name: str) -> SavedConnection | None:
        """Look a connection up by its name property (case-sensitive)."""
        for conn in self.connections():
            if conn.name == name:
                return conn
        return None

    def check_rewritable(self, conn_id: str) -> str:
        """Return the text of one dbtools.properties if update_properties could rewrite it.

        Raises StoreError for a missing file or a file with a comment or continuation line, so a
        caller can refuse before it changes anything else.
        """
        target = self.home / CONNECTIONS_DIR / conn_id / PROPERTIES_FILE
        if not target.is_file():
            raise StoreError(f"Connection properties file not found for id {conn_id}")
        text = _read_text(target)
        if _has_comment_or_continuation(text):
            raise StoreError(
                f"Refusing to rewrite {PROPERTIES_FILE} for id {conn_id}: "
                "it has a comment or a continuation line"
            )
        return text

    def update_properties(self, conn_id: str, changes: Mapping[str, str]) -> None:
        """Set name, userName and/or connectionString in one dbtools.properties, atomically.

        Other keys, their order and the connection id stay as they are. A file holding a comment
        or a continuation line is refused, because the rewrite would lose that text. A new
        connectionString on an ORACLE_BASIC connection converts it to ORACLE_DATABASE as SQLcl
        does (host, port and serviceName are dropped); any other type is refused.
        """
        unknown = set(changes) - WRITABLE_KEYS
        if unknown:
            raise StoreError(f"Cannot write properties: {', '.join(sorted(unknown))}")
        text = self.check_rewritable(conn_id)
        target = self.home / CONNECTIONS_DIR / conn_id / PROPERTIES_FILE
        props = parse_properties(text)
        if "connectionString" in changes:
            props = _with_connect_string_form(props)
        props.update(changes)
        fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".dbtools.", suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(format_properties(props).encode("utf-8"))
            shutil.copymode(target, tmp_name)
            os.replace(tmp_name, target)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp_name)
            raise

    def has_wallet(self, conn_id: str) -> bool:
        """Report whether credentials.sso exists; the file is never opened."""
        return (self.home / CONNECTIONS_DIR / conn_id / WALLET_FILE).is_file()

    def copy_connection_to(self, conn_id: str, target: ConnectionStore) -> str:
        """Copy one connection directory into target under a new id and return that id.

        dbtools.properties and, when present, credentials.sso are copied as opaque bytes; the
        wallet is never opened, decoded or printed. The source file permissions are preserved.
        The files go to a staging directory inside the target connections directory and are
        renamed into place, so a failure leaves no partial connection directory. The target home
        is created when missing. The copy lands in the root folder; placing it in a folder is
        left to SQLcl.
        """
        source = self.home / CONNECTIONS_DIR / conn_id
        if not (source / PROPERTIES_FILE).is_file():
            raise StoreError(f"Connection properties file not found for id {conn_id}")
        root = target.home / CONNECTIONS_DIR
        root.mkdir(parents=True, exist_ok=True)
        new_id = new_connection_id({entry.name for entry in root.iterdir()})
        staging = Path(tempfile.mkdtemp(dir=root, prefix=_STAGING_PREFIX))
        try:
            shutil.copyfile(source / PROPERTIES_FILE, staging / PROPERTIES_FILE)
            shutil.copymode(source / PROPERTIES_FILE, staging / PROPERTIES_FILE)
            if (source / WALLET_FILE).is_file():
                shutil.copyfile(source / WALLET_FILE, staging / WALLET_FILE)
                shutil.copymode(source / WALLET_FILE, staging / WALLET_FILE)
            os.replace(staging, root / new_id)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return new_id

    def remove_connection_dir(self, conn_id: str) -> None:
        """Remove one connection directory, e.g. a copy that could not be placed in a folder.

        Only a name shaped like a connection id is accepted. The caller must know that
        folders.json does not reference the id.
        """
        if not _ID_PATTERN.fullmatch(conn_id):
            raise StoreError(f"Not a connection id: {conn_id!r}")
        shutil.rmtree(self.home / CONNECTIONS_DIR / conn_id)
