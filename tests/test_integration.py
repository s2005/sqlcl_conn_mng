"""Integration test against a real SQLcl. Uses a tmp_path store only."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest

from sqlcl_conn_mng import sqlcl as sq
from sqlcl_conn_mng.store import ConnectionStore

SQL_BIN = os.environ.get("SQLCL_BIN") or shutil.which("sql")


@pytest.mark.integration
@pytest.mark.skipif(SQL_BIN is None, reason="SQLcl (sql) not found")
def test_folder_roundtrip(tmp_path: Path) -> None:
    home = tmp_path / "sqlcl-home"
    home.mkdir()
    assert SQL_BIN is not None
    runner = sq.SqlclRunner(SQL_BIN, str(home), "thin", 180)
    sq.add_folder(runner, "/itest")
    store = ConnectionStore(home)
    assert [f.path for f in store.folders()] == ["/itest"]
    assert store.connections() == []
    sq.delete_folder(runner, "/itest")
    assert store.folders() == []
