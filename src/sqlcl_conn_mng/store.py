"""Read-only access to the SQLcl saved-connection store."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from sqlcl_conn_mng.models import ROOT_FOLDER, Folder, SavedConnection
from sqlcl_conn_mng.properties import parse_properties

HOME_ENV_VAR = "SQLCL_CONN_HOME"
PROPERTIES_FILE = "dbtools.properties"
WALLET_FILE = "credentials.sso"
CONNECTIONS_DIR = "connections"
FOLDERS_FILE = Path("connection_folders") / "folders.json"
KNOWN_KEYS = {"name", "type", "connectionString", "userName"}
_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{22}")


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


class ConnectionStore:
    """Read-only view of a SQLcl store root (the directory given to -home)."""

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

    def has_wallet(self, conn_id: str) -> bool:
        """Report whether credentials.sso exists; the file is never opened."""
        return (self.home / CONNECTIONS_DIR / conn_id / WALLET_FILE).is_file()
