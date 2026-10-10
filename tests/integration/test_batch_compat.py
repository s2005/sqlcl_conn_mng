"""Batch selection: move and delete with --filter act on every match through real SQLcl."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from tests.integration.harness import BuiltStore, CliResult, copy_store

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]


def folders_by_name(store: Path, run_cli: RunCli) -> dict[str, str]:
    """Return the tool's list rows as a name to folder mapping."""
    result = run_cli(store, "list", "--format", "json")
    assert result.code == 0
    rows: list[dict[str, Any]] = result.data
    return {r["name"]: r["folder"] for r in rows}


def test_batch_move_then_delete_by_filter(
    import_store: BuiltStore, run_cli: RunCli, tmp_path: Path
) -> None:
    store = copy_store(import_store.home, tmp_path)
    before = folders_by_name(store, run_cli)
    assert {"imp1", "imp2", "imp3", "imp1_1", "imp2_1", "imp3_1"} <= set(before)

    assert run_cli(store, "add-folder", "--folder", "/bf").code == 0
    moved = run_cli(store, "move", "--filter", "imp?_1", "--folder", "/bf")
    assert moved.code == 0
    assert "Summary: 3 ok, 0 failed" in moved.stdout
    after_move = folders_by_name(store, run_cli)
    for name in ("imp1_1", "imp2_1", "imp3_1"):
        assert after_move[name] == "/bf"
    for name in ("imp1", "imp2", "imp3"):
        assert after_move[name] == before[name]

    refused = run_cli(store, "delete", "--filter", "imp?_1")
    assert refused.code == 1
    assert folders_by_name(store, run_cli) == after_move

    deleted = run_cli(store, "delete", "--filter", "imp?_1", "--yes")
    assert deleted.code == 0
    assert "Deleting 3 connection(s): imp1_1, imp2_1, imp3_1" in deleted.stdout
    assert "Summary: 3 ok, 0 failed" in deleted.stdout
    remaining = folders_by_name(store, run_cli)
    assert set(remaining) == set(before) - {"imp1_1", "imp2_1", "imp3_1"}


def test_batch_empty_filter_exits_one(
    import_store: BuiltStore, run_cli: RunCli, tmp_path: Path
) -> None:
    store = copy_store(import_store.home, tmp_path)
    assert run_cli(store, "move", "--filter", "nomatch*", "--folder", "/bf").code == 1


def test_batch_over_duplicate_names_is_refused(
    import_store: BuiltStore, run_cli: RunCli, tmp_path: Path
) -> None:
    """P1 review: import -duplicates REPLACE leaves two connections per name."""
    store = copy_store(import_store.home, tmp_path)
    before = folders_by_name(store, run_cli)
    result = run_cli(store, "delete", "--filter", "imp?", "--yes")
    assert result.code == 1
    assert "Deleting" not in result.stdout
    assert folders_by_name(store, run_cli) == before


def test_batch_move_json_envelope(
    import_store: BuiltStore, run_cli: RunCli, tmp_path: Path
) -> None:
    store = copy_store(import_store.home, tmp_path)
    assert run_cli(store, "add-folder", "--folder", "/jf").code == 0
    moved = run_cli(store, "move", "--filter", "imp?_1", "--folder", "/jf", "--format", "json")
    assert moved.code == 0
    doc: dict[str, Any] = moved.data
    assert doc["status"] == "ok"
    assert doc["command"] == "move"
    assert doc["ok"] == 3
    assert doc["failed"] == 0
    assert [r["name"] for r in doc["results"]] == ["imp1_1", "imp2_1", "imp3_1"]
    assert folders_by_name(store, run_cli)["imp1_1"] == "/jf"
