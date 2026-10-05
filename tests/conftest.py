"""Shared pytest fixtures for sqlcl-conn-mng. All data is fake."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ID_DEV = "AAAAAAAAAAAAAAAAAAAAAA"
ID_ROOT = "BBBBBBBBBBBBBBBBBBBBBB"
ID_PROD = "CCCCCCCCCCCCCCCCCCCC_-"


def write_connection(home: Path, conn_id: str, props_text: str) -> None:
    """Create a connection directory with fake properties and a fake wallet."""
    conn_dir = home / "connections" / conn_id
    conn_dir.mkdir(parents=True)
    (conn_dir / "dbtools.properties").write_text(props_text, encoding="utf-8")
    (conn_dir / "credentials.sso").write_bytes(b"fake-wallet-bytes")


@pytest.fixture
def fake_home(tmp_path: Path) -> Path:
    """Return a fake store root with three connections and nested folders."""
    home = tmp_path / "store"
    write_connection(
        home,
        ID_DEV,
        "#comment\nname=dev_local\ntype=ORACLE_DATABASE\n"
        "connectionString=//localhost\\:1521/freepdb1\nuserName=scott\nextraKey=extraValue\n",
    )
    write_connection(
        home,
        ID_ROOT,
        "userName=hr\nname=root_conn\nconnectionString=//db.example.test\\:1521/svc\n"
        "type=ORACLE_DATABASE\n",
    )
    write_connection(
        home,
        ID_PROD,
        "name=Prod One\ntype=ORACLE_DATABASE\nconnectionString=//prod.example.test\\:1521/p\n"
        "userName=app\n",
    )
    folders = {
        "folders": [
            {
                "name": "dev",
                "connections": [],
                "folders": [{"name": "local", "connections": [ID_DEV], "folders": []}],
            },
            {"name": "prod", "connections": [ID_PROD], "folders": []},
        ]
    }
    folder_dir = home / "connection_folders"
    folder_dir.mkdir()
    (folder_dir / "folders.json").write_text(json.dumps(folders), encoding="utf-8")
    return home
