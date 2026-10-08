"""Folder scenarios: SQLcl builds the folder tree, the tool must read and edit it."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.integration.harness import BuiltStore, CliResult, copy_store, raw_folder_ids, raw_folders

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]


def node(name: str, path: str, connections: list[str], folders: list[Any]) -> dict[str, Any]:
    """Build one expected folder node of the tool's tree."""
    return {"name": name, "path": path, "connections": connections, "folders": folders}


def final_tree() -> dict[str, Any]:
    """Return the expected tool view of the final folder_store tree."""
    return {
        "folders": [
            node("empty", "/empty", [], [node("b", "/empty/b", ["imp1"], [])]),
            node("ops2", "/ops2", ["imp2"], []),
            node("team", "/team", [], [node("a", "/team/a", [], [])]),
        ],
        "root_connections": ["imp3"],
    }


def tree_of(store: Path, run_cli: RunCli) -> dict[str, Any]:
    """Return the tool's folders view of a store."""
    result = run_cli(store, "folders", "--format", "json")
    assert result.code == 0
    data: dict[str, Any] = result.data
    return data


def listed(store: Path, run_cli: RunCli, *args: str) -> list[dict[str, Any]]:
    """Return the tool's list rows for a store."""
    result = run_cli(store, "list", "--format", "json", *args)
    assert result.code == 0
    rows: list[dict[str, Any]] = result.data
    return rows


def id_of(store: Path, run_cli: RunCli, name: str) -> str:
    """Return the id the tool reports for a connection."""
    return str(next(r["id"] for r in listed(store, run_cli) if r["name"] == name))


def names_in(nodes: list[dict[str, Any]]) -> list[str]:
    """Collect the connection names of folder nodes and their descendants."""
    out: list[str] = []
    for item in nodes:
        out.extend(item["connections"])
        out.extend(names_in(item["folders"]))
    return out


def test_final_tree_matches_expected(folder_store: BuiltStore, run_cli: RunCli) -> None:
    assert tree_of(folder_store.home, run_cli) == final_tree()


@pytest.mark.parametrize(
    ("folder", "expected"),
    [
        ("/empty", ["imp1"]),
        ("/empty/b", ["imp1"]),
        ("/ops2", ["imp2"]),
        ("/team", []),
        ("/team/a", []),
    ],
)
def test_list_by_folder(
    folder_store: BuiltStore, run_cli: RunCli, folder: str, expected: list[str]
) -> None:
    rows = listed(folder_store.home, run_cli, "--folder", folder)
    assert sorted(r["name"] for r in rows) == expected


def test_connection_moved_to_root(folder_store: BuiltStore, run_cli: RunCli) -> None:
    rows = listed(folder_store.home, run_cli)
    imp3 = next(r for r in rows if r["name"] == "imp3")
    assert imp3["folder"] == "/"
    tree = tree_of(folder_store.home, run_cli)
    assert "imp3" not in names_in(tree["folders"])


def test_ids_in_raw_folders_file(folder_store: BuiltStore, run_cli: RunCli) -> None:
    home = folder_store.home
    id1 = id_of(home, run_cli, "imp1")
    id2 = id_of(home, run_cli, "imp2")
    id3 = id_of(home, run_cli, "imp3")
    final = raw_folders(folder_store.snapshots[-1])
    ids = raw_folder_ids(final)
    assert ids["/empty/b"] == [id1]
    assert ids["/ops2"] == [id2]
    assert raw_folder_ids(raw_folders(folder_store.snapshots[3]))["/ops"] == [id2, id3]


def test_folder_deletes(folder_delete_store: BuiltStore, run_cli: RunCli) -> None:
    home = folder_delete_store.home
    rows = listed(home, run_cli)
    assert sorted(r["name"] for r in rows) == ["imp2", "imp3"]
    assert tree_of(home, run_cli)["folders"] == []


def test_tool_add_folder(folder_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(folder_store.home, tmp_path)
    result = run_cli(copy, "add-folder", "--folder", "/team/a/c")
    assert result.code == 0
    expected = final_tree()
    expected["folders"][2]["folders"][0]["folders"] = [node("c", "/team/a/c", [], [])]
    assert tree_of(copy, run_cli) == expected


def test_tool_move_connection(folder_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(folder_store.home, tmp_path)
    result = run_cli(copy, "move", "--name", "imp3", "--folder", "/team/a")
    assert result.code == 0
    expected = final_tree()
    expected["folders"][2]["folders"][0]["connections"] = ["imp3"]
    expected["root_connections"] = []
    assert tree_of(copy, run_cli) == expected


def test_tool_delete_folder(folder_store: BuiltStore, run_cli: RunCli, tmp_path: Path) -> None:
    copy = copy_store(folder_store.home, tmp_path)
    result = run_cli(copy, "delete-folder", "--folder", "/team/a")
    assert result.code == 0
    expected = final_tree()
    expected["folders"][2]["folders"] = []
    assert tree_of(copy, run_cli) == expected


def test_tool_force_delete_folder(
    folder_store: BuiltStore, run_cli: RunCli, tmp_path: Path
) -> None:
    copy = copy_store(folder_store.home, tmp_path)
    result = run_cli(copy, "delete-folder", "--folder", "/empty", "--force", "--yes")
    assert result.code == 0
    expected = final_tree()
    expected["folders"] = expected["folders"][1:]
    assert tree_of(copy, run_cli) == expected
    assert sorted(r["name"] for r in listed(copy, run_cli)) == ["imp2", "imp3"]
