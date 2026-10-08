"""Saved connections against a live database: SQLcl saves them, the tool must read them."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from sqlcl_conn_mng.sqlcl import SqlclRunner
from tests.integration.harness import (
    SQLCL_TIMEOUT,
    BuiltStore,
    CliResult,
    DbSettings,
    assert_no_password,
    copy_store,
    descriptor,
    ids_by_name,
    mask,
)

pytestmark = pytest.mark.integration

RunCli = Callable[..., CliResult]
Cli = Callable[..., CliResult]
SAVED = {
    "p_saved": True,
    "p_clone": True,
    "p_desc": True,
    "p_replace": True,
    "p_nopwd": False,
    "p_clone_user": False,
    "p_clone_nopwd": False,
}


@pytest.fixture(scope="module")
def cli(saved_pw_store: BuiltStore, db_settings: DbSettings, run_cli: RunCli) -> Cli:
    """Run the CLI on the saved-password store and fail if the password is ever printed."""

    def _run(*args: str) -> CliResult:
        result = run_cli(saved_pw_store.home, *args)
        assert_no_password(db_settings.password, result.stdout, result.stderr)
        return result

    return _run


@pytest.fixture(scope="module")
def sqlcl_states(
    saved_pw_store: BuiltStore, db_settings: DbSettings, sqlcl_path: str
) -> dict[str, str]:
    """Return the Password line value SQLcl itself shows for every saved connection."""
    runner = SqlclRunner(sqlcl_path, str(saved_pw_store.home), "thin", SQLCL_TIMEOUT)
    output = runner.run("\n".join(f"connmgr show {name}" for name in SAVED))
    assert_no_password(db_settings.password, output)
    names = re.findall(r"^Name:\s*(.+?)\s*$", output, flags=re.MULTILINE)
    states = re.findall(r"^Password:\s*(.+?)\s*$", output, flags=re.MULTILINE)
    if names != list(SAVED) or len(states) != len(names):
        pytest.fail(mask(f"unexpected connmgr show output:\n{output}", db_settings.password))
    return dict(zip(names, states, strict=True))


def test_list_reports_saved_connections(cli: Cli, db_settings: DbSettings) -> None:
    result = cli("list", "--format", "json")
    assert result.code == 0
    rows = {r["name"]: r for r in result.data}
    for name in ("p_saved", "p_nopwd"):
        assert rows[name]["connect_string"] == db_settings.connect
        assert rows[name]["user_name"] == db_settings.user
        assert rows[name]["folder"] == "/"


@pytest.mark.parametrize("name", ["p_saved", "p_nopwd"])
def test_show_reports_saved_connection(cli: Cli, db_settings: DbSettings, name: str) -> None:
    result = cli("show", "--name", name, "--format", "json")
    assert result.code == 0
    data: dict[str, Any] = result.data
    assert data["name"] == name
    assert data["connect_string"] == db_settings.connect
    assert data["user_name"] == db_settings.user
    assert data["folder"] == "/"


@pytest.mark.parametrize(("name", "saved"), list(SAVED.items()))
def test_check_password_matches_expectation(cli: Cli, name: str, saved: bool) -> None:
    result = cli("show", "--name", name, "--check-password", "--format", "json")
    assert result.code == 0
    assert result.data["password_saved"] is saved
    assert result.data["wallet_present"] is True


def test_sqlcl_agrees_on_saved_state(sqlcl_states: dict[str, str]) -> None:
    for name, saved in SAVED.items():
        expected = "******" if saved else "not saved"
        assert sqlcl_states[name] == expected, name


def test_replace_keeps_id_and_toggles_password(saved_pw_store: BuiltStore) -> None:
    first = ids_by_name(saved_pw_store.snapshots[1])["p_replace"]
    assert len(first) == 1
    assert ids_by_name(saved_pw_store.snapshots[2])["p_replace"] == first
    assert ids_by_name(saved_pw_store.snapshots[3])["p_replace"] == first
    assert "Password: not saved" in saved_pw_store.outputs[1]
    assert "Password: ******" in saved_pw_store.outputs[2]


def test_descriptor_connect_string_is_kept(cli: Cli, db_settings: DbSettings) -> None:
    result = cli("show", "--name", "p_desc", "--format", "json")
    assert result.code == 0
    assert result.data["connect_string"] == descriptor(db_settings.connect)


def test_connection_test_succeeds(cli: Cli) -> None:
    result = cli("test", "--name", "p_saved")
    assert result.code == 0


def test_export_has_wallets_and_no_password(
    cli: Cli, db_settings: DbSettings, tmp_path: Path
) -> None:
    target = tmp_path / "export.json"
    result = cli("export", "--output", str(target))
    assert result.code == 0
    text = target.read_text(encoding="utf-8")
    assert_no_password(db_settings.password, text)
    connections = json.loads(text)["connections"]
    assert {c["name"] for c in connections} == set(SAVED)
    assert all(c["wallet_present"] is True for c in connections)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "descriptor_connect_quoting: the tool quotes user@(DESCRIPTION=...) as one token "
        "and SQLcl then fails to connect"
    ),
)
def test_tool_add_with_descriptor(
    saved_pw_store: BuiltStore, db_settings: DbSettings, run_cli: RunCli, tmp_path: Path
) -> None:
    copy = copy_store(saved_pw_store.home, tmp_path)
    result = run_cli(
        copy,
        "add",
        "--name",
        "t_desc",
        "--user",
        db_settings.user,
        "--connect-string",
        descriptor(db_settings.connect),
        "--password-env",
        "SQLCL_ITEST_PASSWORD",
    )
    assert_no_password(db_settings.password, result.stdout, result.stderr)
    assert result.code == 0
