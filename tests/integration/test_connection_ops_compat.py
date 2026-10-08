"""Connection operations: SQLcl clones, moves, renames and deletes; the tool must read them."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.integration.harness import (
    BuiltStore,
    CliResult,
    copy_store,
    ids_by_name,
    raw_folder_ids,
    raw_folders,
)

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]
CLONES = ("c_user", "c_nopwd", "c1", "C1", "c_from_folder", "c_renamed")


def listed(store: Path, run_cli: RunCli) -> list[dict[str, Any]]:
    """Return the tool's list rows for a store."""
    result = run_cli(store, "list", "--format", "json")
    assert result.code == 0
    rows: list[dict[str, Any]] = result.data
    return rows


def row_of(store: Path, run_cli: RunCli, name: str) -> dict[str, Any]:
    """Return the single list row with exactly this name."""
    matches = [r for r in listed(store, run_cli) if r["name"] == name]
    assert len(matches) == 1
    return matches[0]


def test_rename_keeps_id(conn_ops_store: BuiltStore, run_cli: RunCli) -> None:
    before = ids_by_name(conn_ops_store.snapshots[3])
    assert len(before["c_plain"]) == 1
    assert ids_by_name(conn_ops_store.snapshots[4])["c_renamed"] == before["c_plain"]
    names = {r["name"] for r in listed(conn_ops_store.home, run_cli)}
    assert "c_plain" not in names
    assert "c_plain" not in ids_by_name(conn_ops_store.snapshots[-1])


def test_move_keeps_id(conn_ops_store: BuiltStore, run_cli: RunCli) -> None:
    before = ids_by_name(conn_ops_store.snapshots[1])["imp2"]
    row = row_of(conn_ops_store.home, run_cli, "imp2")
    assert [row["id"]] == before
    assert row["folder"] == "/f"


def test_clones_get_new_ids(conn_ops_store: BuiltStore, run_cli: RunCli) -> None:
    rows = listed(conn_ops_store.home, run_cli)
    by_name = {r["name"]: r["id"] for r in rows}
    originals = {by_name["imp1"], by_name["imp2"]}
    for name in CLONES:
        assert by_name[name] not in originals
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids))


def test_clone_of_foldered_original_is_at_root(conn_ops_store: BuiltStore, run_cli: RunCli) -> None:
    assert row_of(conn_ops_store.home, run_cli, "imp2")["folder"] == "/f"
    assert row_of(conn_ops_store.home, run_cli, "c_from_folder")["folder"] == "/"


def test_delete_removes_connection(conn_ops_store: BuiltStore, run_cli: RunCli) -> None:
    names = {r["name"] for r in listed(conn_ops_store.home, run_cli)}
    assert "c_doomed" not in names
    doomed = ids_by_name(conn_ops_store.snapshots[4])["c_doomed"]
    assert len(doomed) == 1
    folders = raw_folder_ids(raw_folders(conn_ops_store.snapshots[-1]))
    for ids in folders.values():
        assert doomed[0] not in ids
    key = f"connections/{doomed[0]}/dbtools.properties"
    assert key in conn_ops_store.snapshots[4]["files"]
    assert key not in conn_ops_store.snapshots[5]["files"]


@pytest.mark.parametrize(
    ("name", "user"),
    [
        ("c_user", "other_user"),
        ("c_nopwd", "imp_user1"),
        ("c_renamed", "imp_user1"),
    ],
)
def test_clone_user_name(conn_ops_store: BuiltStore, run_cli: RunCli, name: str, user: str) -> None:
    assert row_of(conn_ops_store.home, run_cli, name)["user_name"] == user


def test_case_twins_are_distinct(conn_ops_store: BuiltStore, run_cli: RunCli) -> None:
    shown = {}
    for name in ("c1", "C1"):
        result = run_cli(conn_ops_store.home, "show", "--name", name, "--format", "json")
        assert result.code == 0
        assert result.data["name"] == name
        shown[name] = result.data["id"]
    assert shown["c1"] != shown["C1"]


def test_tool_rename(conn_ops_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(conn_ops_store.home, tmp_path)
    old_id = row_of(copy, run_cli, "c_renamed")["id"]
    result = run_cli(copy, "rename", "--name", "c_renamed", "--new-name", "t_renamed")
    assert result.code == 0
    assert row_of(copy, run_cli, "t_renamed")["id"] == old_id
    assert "c_renamed" not in {r["name"] for r in listed(copy, run_cli)}


def test_tool_move(conn_ops_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(conn_ops_store.home, tmp_path)
    old_id = row_of(copy, run_cli, "c_user")["id"]
    result = run_cli(copy, "move", "--name", "c_user", "--folder", "/f")
    assert result.code == 0
    row = row_of(copy, run_cli, "c_user")
    assert row["id"] == old_id
    assert row["folder"] == "/f"


def test_tool_clone(conn_ops_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(conn_ops_store.home, tmp_path)
    original = row_of(copy, run_cli, "imp2")
    result = run_cli(copy, "clone", "--name", "imp2", "--new-name", "t_clone")
    assert result.code == 0
    clone = row_of(copy, run_cli, "t_clone")
    assert clone["id"] != original["id"]
    assert clone["folder"] == "/"


def test_tool_clone_with_user(conn_ops_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(conn_ops_store.home, tmp_path)
    result = run_cli(
        copy, "clone", "--name", "imp1", "--new-name", "t_user", "--user", "t_user_name"
    )
    assert result.code == 0
    assert row_of(copy, run_cli, "t_user")["user_name"] == "t_user_name"


def test_tool_clone_without_password(
    conn_ops_store: BuiltStore, run_cli: RunCli, tmp_path: Path
) -> None:
    copy = copy_store(conn_ops_store.home, tmp_path)
    original = row_of(copy, run_cli, "imp1")
    result = run_cli(copy, "clone", "--name", "imp1", "--new-name", "t_nopwd", "--no-password")
    assert result.code == 0
    clone = row_of(copy, run_cli, "t_nopwd")
    assert clone["id"] != original["id"]
    assert clone["user_name"] == "imp_user1"


def test_tool_delete(conn_ops_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(conn_ops_store.home, tmp_path)
    result = run_cli(copy, "delete", "--name", "c_nopwd", "--yes")
    assert result.code == 0
    assert "c_nopwd" not in {r["name"] for r in listed(copy, run_cli)}
