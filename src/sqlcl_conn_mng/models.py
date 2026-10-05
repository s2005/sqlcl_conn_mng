"""Data models for saved connections and folders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ROOT_FOLDER = "/"


@dataclass(frozen=True)
class SavedConnection:
    """One saved connection as recorded in dbtools.properties."""

    id: str
    name: str
    type: str
    connect_string: str
    user_name: str
    folder: str
    path: str
    extra: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly view that never contains secrets."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "connect_string": self.connect_string,
            "user_name": self.user_name,
            "folder": self.folder,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True)
class Folder:
    """A connection folder from folders.json."""

    name: str
    path: str
    connections: list[str] = field(default_factory=list)
    folders: list[Folder] = field(default_factory=list)
