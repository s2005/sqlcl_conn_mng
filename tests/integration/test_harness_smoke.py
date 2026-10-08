"""Smoke tests for the integration harness itself."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.integration.harness import BuiltStore, CliResult, StoreBuildError, import_step

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def smoke_store(build_store: Callable[..., BuiltStore]) -> BuiltStore:
    """Build one store with a single folder."""
    stage = [("connmgr add -folder /smoke", "Folder /smoke has been added")]
    return build_store("smoke", [stage])


def test_release_is_read(sqlcl_release: str) -> None:
    assert sqlcl_release != "unknown"


def test_folder_reported_by_tool(
    smoke_store: BuiltStore, run_cli: Callable[..., CliResult]
) -> None:
    result = run_cli(smoke_store.home, "folders", "--format", "json")
    assert result.code == 0
    assert [f["path"] for f in result.data["folders"]] == ["/smoke"]


def test_snapshot_excludes_sqlcl_subtree(smoke_store: BuiltStore) -> None:
    last = smoke_store.snapshots[-1]["files"]
    assert "connection_folders/folders.json" in last
    assert not any(key.startswith("sqlcl/") for key in last)
    assert len(smoke_store.snapshots) == 2
    assert smoke_store.snapshots[0]["files"] == {}


def test_tool_error_text_is_captured(
    smoke_store: BuiltStore, run_cli: Callable[..., CliResult]
) -> None:
    result = run_cli(smoke_store.home, "show", "--name", "nosuch")
    assert result.code == 1
    assert "nosuch" in result.stderr


def test_wrong_expected_line_names_step(build_store: Callable[..., BuiltStore]) -> None:
    stage = [
        ("connmgr add -folder /bad1", "Folder /bad1 has been added"),
        ("connmgr add -folder /bad2", "this line never appears"),
    ]
    with pytest.raises(StoreBuildError, match=r"stage 1, step 2"):
        build_store("bad", [stage])


def test_import_fixture_creates_basic_connections(
    build_store: Callable[..., BuiltStore], run_cli: Callable[..., CliResult]
) -> None:
    store = build_store("imported", [[import_step()]])
    result = run_cli(store.home, "list", "--format", "json")
    assert result.code == 0
    rows = result.data
    assert sorted(r["name"] for r in rows) == ["imp1", "imp2", "imp3"]
    assert {r["type"] for r in rows} == {"ORACLE_BASIC"}
