"""Tests for the SQLcl runner with subprocess.run mocked."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest
from pytest_mock import MockerFixture

from sqlcl_conn_mng import sqlcl as sq

SECRET = "S3cret-pwd"


def _fake_run(mocker: MockerFixture, stdout: str, stderr: str = "") -> Any:
    done = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr=stderr)
    return mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run", return_value=done)


def _runner(driver: str = "thin") -> sq.SqlclRunner:
    return sq.SqlclRunner("sql-bin", "store-home", driver, 30)


@pytest.mark.unit
def test_argv_thin_and_thick() -> None:
    thin = _runner().argv()
    assert thin == [
        "sql-bin",
        "-S",
        "-nohistory",
        "-noupdates",
        "-thin",
        "-home",
        "store-home",
        "/nolog",
    ]
    assert "-thin" not in _runner("thick").argv()


@pytest.mark.unit
def test_run_feeds_stdin_and_cleans_output(mocker: MockerFixture) -> None:
    mock = _fake_run(mocker, "\x1b[31mFolder   /dev has been   added\x1b[0m\n\n")
    out = _runner().run("connmgr add -folder /dev")
    assert out == "Folder /dev has been added"
    kwargs = mock.call_args.kwargs
    assert kwargs["input"].endswith("exit\n")
    assert kwargs["text"] is True
    assert kwargs["capture_output"] is True
    assert kwargs["timeout"] == 30


@pytest.mark.unit
def test_timeout_and_missing_binary(mocker: MockerFixture) -> None:
    mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="sql", timeout=30),
    )
    with pytest.raises(sq.SqlclError, match="timed out"):
        _runner().run("x")
    mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run", side_effect=FileNotFoundError("nope"))
    with pytest.raises(sq.SqlclError, match="Cannot run"):
        _runner().run("x")


@pytest.mark.unit
def test_password_only_in_stdin(mocker: MockerFixture) -> None:
    mock = _fake_run(mocker, "Connected")
    sq.save_connection(_runner(), "c1", "scott", "//h:1521/s", SECRET)
    argv = mock.call_args.args[0]
    assert all(SECRET not in part for part in argv)
    stdin = mock.call_args.kwargs["input"]
    assert f'-password "{SECRET}"' in stdin
    assert "connect -save c1 -savepwd" in stdin
    assert "scott@//h:1521/s" in stdin


@pytest.mark.unit
def test_save_flags(mocker: MockerFixture) -> None:
    mock = _fake_run(mocker, "ok")
    sq.save_connection(_runner(), "c1", "u", "//h/s", "p", save_password=False, replace=True)
    stdin = mock.call_args.kwargs["input"]
    assert "-savepwd" not in stdin
    assert "-replace" in stdin


@pytest.mark.unit
def test_save_failure_hides_password(mocker: MockerFixture) -> None:
    _fake_run(mocker, f"Connection failed\n USER = u\n Error Message = bad {SECRET}")
    with pytest.raises(sq.SqlclError) as exc:
        sq.save_connection(_runner(), "c1", "u", "//h/s", SECRET)
    assert SECRET not in str(exc.value)
    assert "Connection failed" in str(exc.value)


@pytest.mark.unit
def test_save_syntax_error(mocker: MockerFixture) -> None:
    _fake_run(mocker, "Syntax error at column 5")
    with pytest.raises(sq.SqlclError, match="Syntax error"):
        sq.save_connection(_runner(), "c1", "u", "//h/s", "p")


@pytest.mark.unit
@pytest.mark.parametrize(
    ("call", "message"),
    [
        (lambda r: sq.add_folder(r, "/dev"), "Folder /dev has been added"),
        (lambda r: sq.delete_folder(r, "/dev", True), "Folder /dev has been deleted"),
        (lambda r: sq.delete_connection(r, "c1"), "Connection c1 has been deleted"),
        (lambda r: sq.rename_connection(r, "c1", "c2"), "Connection c1 has been renamed"),
        (lambda r: sq.move_connection(r, "c1", "/dev"), "Connection c1 has been moved to /dev"),
        (lambda r: sq.clone_connection(r, "c1", "c2"), "Connection c1 has been cloned"),
    ],
)
def test_operations_detect_success_and_failure(
    mocker: MockerFixture, call: Any, message: str
) -> None:
    _fake_run(mocker, message)
    assert message in call(_runner())
    _fake_run(mocker, "Could not find the specified connection: nosuch")
    with pytest.raises(sq.SqlclError, match="Could not find"):
        call(_runner())


@pytest.mark.unit
def test_operation_scripts(mocker: MockerFixture) -> None:
    mock = _fake_run(mocker, "has been cloned")
    sq.clone_connection(_runner(), "my conn", "new", user="bob", no_password=True)
    stdin = mock.call_args.kwargs["input"]
    assert 'connmgr clone -original "my conn" -username bob -nopwd new' in stdin
    mock = _fake_run(mocker, "has been deleted")
    sq.delete_folder(_runner(), "dev/", force=True)
    assert "connmgr delete -folder /dev -force" in mock.call_args.kwargs["input"]


@pytest.mark.unit
def test_delete_non_empty_folder_error(mocker: MockerFixture) -> None:
    _fake_run(mocker, "The folder you are trying to delete is not Empty. retry with -force flag")
    with pytest.raises(sq.SqlclError, match="not Empty"):
        sq.delete_folder(_runner(), "/dev")


@pytest.mark.unit
def test_show_parses_fields(mocker: MockerFixture) -> None:
    _fake_run(
        mocker,
        "Name: c1\nConnect String: //h:1521/s\nUser: scott\nPassword: ******\n",
    )
    result = sq.show_connection(_runner(), "c1")
    assert result == sq.ShowResult("c1", "//h:1521/s", "scott", True)
    _fake_run(mocker, "Name: c1\nConnect String: x\nUser: u\nPassword: not saved\n")
    assert not sq.show_connection(_runner(), "c1").password_saved


@pytest.mark.unit
@pytest.mark.parametrize(
    ("password_field", "expected"),
    [
        ("Password: ******\n", True),
        ("Password: not saved\n", False),
    ],
)
def test_show_password_saved_detection(
    mocker: MockerFixture, password_field: str, expected: bool
) -> None:
    _fake_run(mocker, f"Name: c1\nConnect String: x\nUser: u\n{password_field}")
    assert sq.show_connection(_runner(), "c1").password_saved is expected


@pytest.mark.unit
def test_show_unknown(mocker: MockerFixture) -> None:
    _fake_run(mocker, "Undefined connection nosuch")
    with pytest.raises(sq.SqlclError, match="Undefined connection"):
        sq.show_connection(_runner(), "nosuch")


@pytest.mark.unit
def test_check_connection_outcomes(mocker: MockerFixture) -> None:
    _fake_run(mocker, "Connection Test Successful")
    assert "Successful" in sq.check_connection(_runner(), "c1")
    _fake_run(mocker, "Connection Test Failed - ORA-12541: no listener")
    with pytest.raises(sq.SqlclError, match="ORA-12541"):
        sq.check_connection(_runner(), "c1")
    _fake_run(mocker, "something unexpected")
    with pytest.raises(sq.SqlclError):
        sq.check_connection(_runner(), "c1")


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["a\nb", "a\rb", 'a"b', ""])
def test_values_rejected(bad: str) -> None:
    with pytest.raises(ValueError, match="must not"):
        sq.quote_arg(bad, "name")


@pytest.mark.unit
def test_quote_arg() -> None:
    assert sq.quote_arg("plain_name", "name") == "plain_name"
    assert sq.quote_arg("has space", "name") == '"has space"'


@pytest.mark.unit
def test_quote_password_rules() -> None:
    assert sq.quote_password("abc") == '"abc"'
    assert sq.quote_password('a"b') == "'a\"b'"
    with pytest.raises(ValueError, match="both"):
        sq.quote_password("a\"b'c")
    with pytest.raises(ValueError, match="newline"):
        sq.quote_password("a\nb")
    with pytest.raises(ValueError, match="empty"):
        sq.quote_password("")


@pytest.mark.unit
def test_normalize_folder() -> None:
    assert sq.normalize_folder("dev/local/") == "/dev/local"
    with pytest.raises(ValueError, match="below the root"):
        sq.normalize_folder("/")


@pytest.mark.unit
def test_resolve_sql_path(mocker: MockerFixture, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SQLCL_BIN", raising=False)
    assert sq.resolve_sql_path("given") == "given"
    monkeypatch.setenv("SQLCL_BIN", "from-env")
    assert sq.resolve_sql_path(None) == "from-env"
    monkeypatch.delenv("SQLCL_BIN")
    mocker.patch("sqlcl_conn_mng.sqlcl.shutil.which", return_value=None)
    with pytest.raises(sq.SqlclError, match="not found"):
        sq.resolve_sql_path(None)
