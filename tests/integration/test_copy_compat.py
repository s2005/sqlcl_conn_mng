"""The copy command against real SQLcl: a copied wallet keeps its saved password in the target."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from sqlcl_conn_mng.sqlcl import SqlclRunner, show_connection
from sqlcl_conn_mng.store import ConnectionStore
from tests.integration.harness import (
    SQLCL_TIMEOUT,
    BuiltStore,
    CliResult,
    DbSettings,
    assert_no_password,
    copy_store,
    snapshot,
)

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]
FOLDER = "/team/a"


def password_saved(sqlcl_path: str, store: Path, name: str) -> bool:
    """Ask real SQLcl whether the store holds a password for the connection."""
    runner = SqlclRunner(sqlcl_path, str(store), "thin", SQLCL_TIMEOUT)
    return show_connection(runner, name).password_saved


def test_copied_connections_keep_password_and_folder(
    saved_pw_store: BuiltStore,
    db_settings: DbSettings,
    run_cli: RunCli,
    sqlcl_path: str,
    tmp_path: Path,
) -> None:
    source = copy_store(saved_pw_store.home, tmp_path / "source")
    target = tmp_path / "target"
    assert run_cli(source, "add-folder", "--folder", FOLDER).code == 0
    assert run_cli(source, "move", "--name", "p_saved", "--folder", FOLDER).code == 0
    before = snapshot(source)
    expected = {c.name: c.folder for c in ConnectionStore(source).connections()}
    assert expected["p_saved"] == FOLDER

    result = run_cli(source, "copy", "--all", "--to-home", str(target))

    assert result.code == 0, result.stdout + result.stderr
    assert f"Summary: {len(expected)} ok, 0 failed" in result.stdout
    assert_no_password(db_settings.password, result.stdout, result.stderr)
    assert snapshot(source) == before
    copied = ConnectionStore(target).connections()
    assert {c.name: c.folder for c in copied} == expected
    source_ids = {c.id for c in ConnectionStore(source).connections()}
    assert not source_ids & {c.id for c in copied}
    assert password_saved(sqlcl_path, target, "p_saved") is True
    assert password_saved(sqlcl_path, target, "p_clone") is True
    assert password_saved(sqlcl_path, target, "p_nopwd") is False
    assert password_saved(sqlcl_path, target, "p_clone_nopwd") is False
