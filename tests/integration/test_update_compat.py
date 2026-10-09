"""The update command against real SQLcl: Python-edited metadata and SQLcl-written passwords."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from sqlcl_conn_mng.sqlcl import ShowResult, SqlclRunner, show_connection
from tests.integration.harness import (
    SPECIAL_USER,
    SQLCL_TIMEOUT,
    BuiltStore,
    CliResult,
    DbSettings,
    assert_no_password,
    copy_store,
    ids_by_name,
    snapshot,
)

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]
NEW_NAME = "upd name:1"
NEW_CONNECT = "//other.example.test:1521/svc"


def sqlcl_show(sqlcl_path: str, store: Path, name: str) -> ShowResult:
    """Ask real SQLcl what it reads from the store."""
    return show_connection(SqlclRunner(sqlcl_path, str(store), "thin", SQLCL_TIMEOUT), name)


# A connection SQLcl saved (ORACLE_DATABASE) and one imported from SQL Developer
# (ORACLE_BASIC, target in host, port and serviceName): both must follow a new connect string.
@pytest.mark.parametrize(
    ("store_fixture", "name", "folder"),
    [("saved_pw_store", "p_nopwd", "/"), ("folder_store", "imp2", "/ops2")],
)
def test_python_edited_metadata_is_read_by_sqlcl(
    request: pytest.FixtureRequest,
    store_fixture: str,
    name: str,
    folder: str,
    run_cli: RunCli,
    sqlcl_path: str,
    tmp_path: Path,
) -> None:
    built: BuiltStore = request.getfixturevalue(store_fixture)
    store = copy_store(built.home, tmp_path)
    before = snapshot(store)
    conn_id = ids_by_name(before)[name][0]
    result = run_cli(
        store,
        "update",
        "--name",
        name,
        "--new-name",
        NEW_NAME,
        "--user",
        SPECIAL_USER,
        "--connect-string",
        NEW_CONNECT,
    )
    assert result.code == 0, result.stderr
    after = snapshot(store)
    assert ids_by_name(after)[NEW_NAME] == [conn_id]
    changed = {k for k in after["files"] if after["files"][k] != before["files"].get(k)}
    assert changed == {f"connections/{conn_id}/dbtools.properties"}
    shown = sqlcl_show(sqlcl_path, store, NEW_NAME)
    assert shown.name == NEW_NAME
    assert shown.user == SPECIAL_USER
    assert shown.connect_string == NEW_CONNECT
    listing = run_cli(store, "list", "--format", "json")
    row = next(r for r in listing.data if r["id"] == conn_id)
    assert (row["name"], row["user_name"], row["connect_string"]) == (
        NEW_NAME,
        SPECIAL_USER,
        NEW_CONNECT,
    )
    assert row["folder"] == folder
    assert row["type"] == "ORACLE_DATABASE"
    assert row["extra"] == {}


def test_password_change_keeps_id_and_follows_flags(
    saved_pw_store: BuiltStore,
    db_settings: DbSettings,
    run_cli: RunCli,
    sqlcl_path: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SQLCL_ITEST_PASSWORD", db_settings.password)
    store = copy_store(saved_pw_store.home, tmp_path)
    ids = ids_by_name(snapshot(store))

    def update(*args: str) -> CliResult:
        result = run_cli(store, "update", *args, "--password-env", "SQLCL_ITEST_PASSWORD")
        assert_no_password(db_settings.password, result.stdout, result.stderr)
        return result

    assert update("--name", "p_nopwd").code == 0
    assert sqlcl_show(sqlcl_path, store, "p_nopwd").password_saved is True
    assert update("--name", "p_saved", "--no-save-password").code == 0
    assert sqlcl_show(sqlcl_path, store, "p_saved").password_saved is False
    combined = update(
        "--name", "p_replace", "--user", db_settings.user.upper(), "--new-name", "p_new"
    )
    assert combined.code == 0, combined.stderr
    shown = sqlcl_show(sqlcl_path, store, "p_new")
    assert shown.user == db_settings.user.upper()
    assert shown.password_saved is True
    after = ids_by_name(snapshot(store))
    assert after["p_nopwd"] == ids["p_nopwd"]
    assert after["p_saved"] == ids["p_saved"]
    assert after["p_new"] == ids["p_replace"]
    wrong = run_cli(
        store,
        "update",
        "--name",
        "p_nopwd",
        "--user",
        "no_such_user_x",
        "--password-env",
        "SQLCL_ITEST_PASSWORD",
    )
    assert wrong.code == 1
    assert sqlcl_show(sqlcl_path, store, "p_nopwd").user == db_settings.user
