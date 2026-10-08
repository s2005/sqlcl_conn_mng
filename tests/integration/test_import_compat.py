"""Import scenarios: connections imported by SQLcl must be read correctly by the tool."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.integration.harness import IMPORT_NAMES, BuiltStore, CliResult

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]
EXTRA = {"host": "db.example.test", "port": "1521", "serviceName": "fakesvc"}


def listed(store: BuiltStore, run_cli: RunCli) -> list[dict[str, Any]]:
    """Return the tool's list rows for the store."""
    result = run_cli(store.home, "list", "--format", "json")
    assert result.code == 0
    rows: list[dict[str, Any]] = result.data
    return rows


def user_of(name: str) -> str:
    """Return the user name the fixture gives a connection, from its base name."""
    base = name.split("_")[0]
    return f"imp_user{base.removeprefix('imp')}"


def test_listed_fields(import_store: BuiltStore, run_cli: RunCli) -> None:
    rows = listed(import_store, run_cli)
    assert rows
    for row in rows:
        assert row["type"] == "ORACLE_BASIC"
        assert row["folder"] == "/"
        assert row["user_name"] == user_of(row["name"])
        assert row["extra"] == EXTRA


def test_rename_duplicates(import_store: BuiltStore, run_cli: RunCli) -> None:
    names = {r["name"] for r in listed(import_store, run_cli)}
    assert {"imp1_1", "imp2_1", "imp3_1"} <= names


def test_replace_duplicates(import_store: BuiltStore, run_cli: RunCli) -> None:
    rows = listed(import_store, run_cli)
    for name in IMPORT_NAMES:
        ids = [r["id"] for r in rows if r["name"] == name]
        assert len(ids) == 2
        assert ids[0] != ids[1]


def test_show_wallet_without_password(import_store: BuiltStore, run_cli: RunCli) -> None:
    result = run_cli(
        import_store.home, "show", "--name", "imp1_1", "--check-password", "--format", "json"
    )
    assert result.code == 0
    assert result.data["wallet_present"] is True
    assert result.data["password_saved"] is False


def test_export(import_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    out = tmp_path / "export.json"
    result = run_cli(import_store.home, "export", "--output", str(out))
    assert result.code == 0
    exported = json.loads(out.read_text(encoding="utf-8"))["connections"]
    rows = listed(import_store, run_cli)
    assert len(exported) == len(rows)
    assert sorted(c["name"] for c in exported) == sorted(r["name"] for r in rows)
    for conn in exported:
        assert conn["user_name"] == user_of(conn["name"])
        assert conn["extra"] == EXTRA
        assert conn["wallet_present"] is True
