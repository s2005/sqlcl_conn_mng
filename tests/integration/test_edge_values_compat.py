"""Edge values: names, users and folders with unusual characters survive SQLcl and the tool."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.integration.harness import (
    EDGE_FOLDERS,
    EDGE_NAMES,
    SPECIAL_USER,
    BuiltStore,
    CliResult,
    copy_store,
)

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]


def listed(store: Path, run_cli: RunCli) -> list[dict[str, Any]]:
    """Return the tool's list rows for a store."""
    result = run_cli(store, "list", "--format", "json")
    assert result.code == 0
    rows: list[dict[str, Any]] = result.data
    return rows


@pytest.mark.parametrize("name", EDGE_NAMES)
def test_edge_name(edge_store: BuiltStore, run_cli: RunCli, name: str) -> None:
    rows = [r for r in listed(edge_store.home, run_cli) if r["name"] == name]
    assert len(rows) == 1
    result = run_cli(edge_store.home, "show", "--name", name, "--format", "json")
    assert result.code == 0
    assert result.data["name"] == name
    assert result.data["user_name"] == "imp_user1"


def test_special_user(edge_store: BuiltStore, run_cli: RunCli) -> None:
    rows = [r for r in listed(edge_store.home, run_cli) if r["name"] == "c_special_user"]
    assert [r["user_name"] for r in rows] == [SPECIAL_USER]
    result = run_cli(edge_store.home, "show", "--name", "c_special_user", "--format", "json")
    assert result.code == 0
    assert result.data["user_name"] == SPECIAL_USER


def test_edge_folders(edge_store: BuiltStore, run_cli: RunCli) -> None:
    result = run_cli(edge_store.home, "folders", "--format", "json")
    assert result.code == 0
    paths = [f["path"] for f in result.data["folders"]]
    assert len(paths) == len(set(paths))
    assert set(paths) == set(EDGE_FOLDERS)
    assert "/dev" in paths
    assert "/DEV" in paths


def test_tool_clone_non_ascii_name(edge_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(edge_store.home, tmp_path)
    new_name = "caf\u00e92"
    result = run_cli(copy, "clone", "--name", "imp1", "--new-name", new_name)
    assert result.code == 0
    assert new_name in {r["name"] for r in listed(copy, run_cli)}
