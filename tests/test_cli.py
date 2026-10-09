"""Tests for the sqlcl-conn-mng command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from sqlcl_conn_mng import __version__
from sqlcl_conn_mng.cli import (
    _global_options,
    _select_names,
    _store,
    build_parser,
    main,
    render_table,
)
from sqlcl_conn_mng.sqlcl import SqlclError
from sqlcl_conn_mng.store import ConnectionStore
from tests.conftest import ID_DEV, write_connection


@pytest.mark.unit
def test_parser_requires_command() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([])
    assert exc.value.code == 2


@pytest.mark.unit
def test_parser_rejects_positional() -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args(["list", "extra"])
    assert exc.value.code == 2


@pytest.mark.unit
def test_parser_defaults() -> None:
    args = build_parser().parse_args(["list"])
    assert args.driver == "thin"
    assert args.timeout == 120
    assert args.log_level == "INFO"
    assert args.format == "table"


@pytest.mark.unit
def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert __version__ in capsys.readouterr().out


@pytest.mark.unit
def test_list_json(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--home", str(fake_home), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert [c["name"] for c in data] == ["Prod One", "dev_local", "root_conn"]
    assert data[1]["folder"] == "/dev/local"
    assert "path" not in data[1]


@pytest.mark.unit
def test_list_table_and_folder_filter(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--home", str(fake_home), "--folder", "/dev"]) == 0
    out = capsys.readouterr().out
    assert "dev_local" in out
    assert "root_conn" not in out
    assert out.splitlines()[0].startswith("name")


@pytest.mark.unit
def test_show_json(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["show", "--home", str(fake_home), "--name", "dev_local", "--format", "json"]
    assert main(argv) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["id"] == ID_DEV
    assert data["wallet_present"] is True
    assert data["extra"] == {"extraKey": "extraValue"}


@pytest.mark.unit
def test_show_unknown_returns_one(fake_home: Path) -> None:
    assert main(["show", "--home", str(fake_home), "--name", "nosuch"]) == 1


@pytest.mark.unit
def test_show_check_password(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        return_value=mocker.Mock(
            stdout="Name: dev_local\nConnect String: //h/s\nUser: scott\nPassword: ******\n",
            stderr="",
        ),
    )
    argv = ["show", "--home", str(fake_home), "--sqlcl", "sql-bin", "--name", "dev_local"]
    assert main([*argv, "--check-password"]) == 0
    assert "Password: saved" in capsys.readouterr().out


@pytest.mark.unit
def test_folders_json(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["folders", "--home", str(fake_home), "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["root_connections"] == ["root_conn"]
    assert data["folders"][0]["folders"][0]["connections"] == ["dev_local"]


@pytest.mark.unit
def test_folders_table(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["folders", "--home", str(fake_home)]) == 0
    out = capsys.readouterr().out
    assert "dev/" in out
    assert "    dev_local" in out


@pytest.mark.unit
def test_export(fake_home: Path, tmp_path: Path) -> None:
    target = tmp_path / "out.json"
    assert main(["export", "--home", str(fake_home), "--output", str(target)]) == 0
    text = target.read_text(encoding="utf-8")
    data = json.loads(text)
    assert len(data["connections"]) == 3
    assert "fake-wallet-bytes" not in text
    assert all("path" not in c for c in data["connections"])


@pytest.mark.unit
def test_destructive_requires_yes(fake_home: Path, mocker: MockerFixture) -> None:
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    base = ["--home", str(fake_home), "--sqlcl", "sql-bin"]
    assert main(["delete", *base, "--name", "dev_local"]) == 1
    assert main(["delete-folder", *base, "--folder", "/dev", "--force"]) == 1
    run.assert_not_called()


@pytest.mark.unit
def test_delete_with_yes(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        return_value=mocker.Mock(stdout="Connection dev_local has been deleted", stderr=""),
    )
    argv = [
        "delete",
        "--home",
        str(fake_home),
        "--sqlcl",
        "sql-bin",
        "--name",
        "dev_local",
        "--yes",
    ]
    assert main(argv) == 0
    assert "has been deleted" in capsys.readouterr().out


@pytest.mark.unit
def test_sqlcl_failure_returns_one(fake_home: Path, mocker: MockerFixture) -> None:
    mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        return_value=mocker.Mock(stdout="Could not find the specified connection: x", stderr=""),
    )
    argv = [
        "rename",
        "--home",
        str(fake_home),
        "--sqlcl",
        "sql-bin",
        "--name",
        "x",
        "--new-name",
        "y",
    ]
    assert main(argv) == 1


@pytest.mark.unit
def test_add_reads_password_from_env_and_moves(
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("FAKE_PWD_VAR", "fake-pwd")
    run = mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        return_value=mocker.Mock(
            stdout="Connection dev_local has been moved to /dev/local", stderr=""
        ),
    )
    argv = [
        "add",
        "--home",
        str(fake_home),
        "--sqlcl",
        "sql-bin",
        "--name",
        "dev_local",
        "--user",
        "scott",
        "--connect-string",
        "//h:1521/s",
        "--replace",
        "--folder",
        "/dev/local",
        "--password-env",
        "FAKE_PWD_VAR",
    ]
    assert main(argv) == 0
    assert run.call_count == 2
    first_argv = run.call_args_list[0].args[0]
    assert all("fake-pwd" not in part for part in first_argv)
    assert '-password "fake-pwd"' in run.call_args_list[0].kwargs["input"]
    assert "saved" in capsys.readouterr().out


@pytest.mark.unit
def test_add_existing_without_replace_fails(fake_home: Path) -> None:
    argv = [
        "add",
        "--home",
        str(fake_home),
        "--name",
        "dev_local",
        "--user",
        "u",
        "--connect-string",
        "//h/s",
        "--password-env",
        "FAKE_PWD_VAR",
    ]
    assert main(argv) == 1


@pytest.mark.unit
def test_add_missing_password_env(fake_home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FAKE_PWD_VAR", raising=False)
    argv = [
        "add",
        "--home",
        str(fake_home),
        "--sqlcl",
        "sql-bin",
        "--name",
        "new",
        "--user",
        "u",
        "--connect-string",
        "//h/s",
        "--password-env",
        "FAKE_PWD_VAR",
    ]
    assert main(argv) == 1


@pytest.mark.unit
def test_render_table_alignment() -> None:
    text = render_table(["a", "bb"], [["xxx", "y"]])
    assert text.splitlines() == ["a    bb", "---  --", "xxx  y"]


# Command placement rules (AC-1 to AC-6).


def _list_json(capsys: pytest.CaptureFixture[str], argv: list[str]) -> list[str]:
    # Run main(argv) expecting success; return the connection names it printed.
    assert main(argv) == 0
    return [c["name"] for c in json.loads(capsys.readouterr().out)]


@pytest.mark.unit
def test_command_first_global_options_in_any_order(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    home = str(fake_home)
    expected = ["Prod One", "dev_local", "root_conn"]
    forms = [
        ["list", "--home", home, "--format", "json"],
        ["list", "--format", "json", "--home", home],
        ["list", "--log-level", "DEBUG", "--format", "json", "--timeout", "5", "--home", home],
    ]
    for argv in forms:
        assert _list_json(capsys, argv) == expected


@pytest.mark.unit
def test_command_option_forms(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = str(fake_home)
    expected = ["Prod One", "dev_local", "root_conn"]
    forms = [
        ["--home", home, "--command", "list", "--format", "json"],
        ["--home", home, "--command=list", "--format", "json"],
        ["--format", "json", "--home", home, "--command", "list"],
        ["--home", home, "--format", "json", "--command=list"],
    ]
    for argv in forms:
        assert _list_json(capsys, argv) == expected


@pytest.mark.unit
def test_command_option_unknown_name_exits_two() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--command", "bogus"])
    assert exc.value.code == 2


@pytest.mark.unit
def test_bare_command_after_options_is_rejected(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--home", str(fake_home), "list"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "the command must be the first argument or be given with --command" in err


@pytest.mark.unit
@pytest.mark.parametrize("argv", [[], ["--home", "x"], ["--log-level", "DEBUG"]])
def test_no_command_exits_two(argv: list[str], capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2
    assert "--command" in capsys.readouterr().err


@pytest.mark.unit
@pytest.mark.parametrize(
    "argv",
    [
        ["list", "--command", "list"],
        ["list", "--command=show"],
        ["--command", "list", "--command", "show"],
        ["--command", "list", "--command=list"],
        ["--command"],
        ["--home", "x", "--command"],
        ["--command", "--home", "x"],
    ],
)
def test_command_given_twice_or_without_value_exits_two(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(argv)
    assert exc.value.code == 2


@pytest.mark.unit
@pytest.mark.parametrize("flag", ["--help", "-h", "--version"])
def test_help_and_version_need_no_command(flag: str) -> None:
    with pytest.raises(SystemExit) as exc:
        main([flag])
    assert exc.value.code == 0


@pytest.mark.unit
def test_command_help_lists_global_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["list", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "--home" in out
    assert "--folder" in out


@pytest.mark.unit
def test_top_level_help_documents_command_option(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "--command" in out
    assert "after it" in out


@pytest.mark.unit
def test_no_command_option_shares_a_global_option_name() -> None:
    global_names = {s for a in _global_options()._actions for s in a.option_strings}
    assert global_names == {"--home", "--sqlcl", "--driver", "--timeout", "--log-level"}
    parser = build_parser()
    assert parser.commands
    for name, command in parser.commands.items():
        names = [s for a in command._actions for s in a.option_strings]
        # Each global option appears exactly once, so no command option reuses its name.
        for option in global_names:
            assert names.count(option) == 1, (name, option)
        assert len(names) == len(set(names)), name


SELECTOR_COMMANDS = [
    ["test"],
    ["show"],
    ["delete", "--yes"],
    ["move", "--folder", "/x"],
]


@pytest.mark.unit
@pytest.mark.parametrize("command", SELECTOR_COMMANDS, ids=lambda c: c[0])
def test_selector_requires_exactly_one(command: list[str]) -> None:
    parser = build_parser()
    for extra in (
        [],
        ["--name", "a", "--all"],
        ["--filter", "a*", "--all"],
        ["--name", "a", "--filter", "a"],
    ):
        with pytest.raises(SystemExit) as exc:
            parser.parse_args([*command, *extra])
        assert exc.value.code == 2
    for ok in (["--name", "a"], ["--filter", "a*"], ["--all"]):
        parser.parse_args([*command, *ok])


@pytest.mark.unit
@pytest.mark.parametrize("command", ["rename", "clone"])
def test_rename_and_clone_reject_batch_selectors(command: str) -> None:
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([command, "--all", "--new-name", "n"])
    assert exc.value.code == 2


def _select(fake_home: Path, argv: list[str]) -> list[str]:
    args = build_parser().parse_args(["show", "--home", str(fake_home), *argv])
    return _select_names(args, _store(args))


@pytest.mark.unit
def test_select_all_is_sorted(fake_home: Path) -> None:
    assert _select(fake_home, ["--all"]) == ["Prod One", "dev_local", "root_conn"]


@pytest.mark.unit
@pytest.mark.parametrize(
    ("pattern", "expected"),
    [
        ("dev_*", ["dev_local"]),
        ("*_*", ["dev_local", "root_conn"]),
        ("dev_loca?", ["dev_local"]),
        ("[dr]*", ["dev_local", "root_conn"]),
        ("DEV_*", []),
        ("dev", []),
        ("*", ["Prod One", "dev_local", "root_conn"]),
        ("", []),
    ],
)
def test_select_filter_glob(fake_home: Path, pattern: str, expected: list[str]) -> None:
    assert _select(fake_home, ["--filter", pattern]) == expected


@pytest.mark.unit
def test_select_name_is_literal(fake_home: Path) -> None:
    assert _select(fake_home, ["--name", "dev_local"]) == ["dev_local"]
    with pytest.raises(ValueError, match="No saved connection named"):
        _select(fake_home, ["--name", "dev_*"])


def _base(fake_home: Path) -> list[str]:
    return ["--home", str(fake_home), "--sqlcl", "sql-bin"]


def _fail_on(bad: str, mocker: MockerFixture, target: str) -> MockerFixture:
    """Patch a sqlcl function so it fails for one name and succeeds for the others."""

    def fake(runner: object, name: str, *rest: object) -> str:
        if name == bad:
            raise SqlclError(f"boom {name}")
        return f"done {name}"

    return mocker.patch(target, side_effect=fake)  # type: ignore[no-any-return]


@pytest.mark.unit
def test_test_name_output_unchanged(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch("sqlcl_conn_mng.sqlcl.check_connection", return_value="Connection OK")
    assert main(["test", *_base(fake_home), "--name", "dev_local"]) == 0
    assert capsys.readouterr().out == "Connection OK\n"


@pytest.mark.unit
def test_test_name_failure_propagates(fake_home: Path, mocker: MockerFixture) -> None:
    mocker.patch("sqlcl_conn_mng.sqlcl.check_connection", side_effect=SqlclError("bad"))
    assert main(["test", *_base(fake_home), "--name", "dev_local"]) == 1


@pytest.mark.unit
def test_test_batch_continues_after_failure(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    fake = _fail_on("dev_local", mocker, "sqlcl_conn_mng.sqlcl.check_connection")
    assert main(["test", *_base(fake_home), "--all"]) == 1
    assert fake.call_count == 3
    assert capsys.readouterr().out.splitlines() == [
        "[OK] Prod One",
        "[FAIL] dev_local: boom dev_local",
        "[OK] root_conn",
        "Summary: 2 ok, 1 failed",
    ]


@pytest.mark.unit
def test_test_batch_all_ok_exits_zero(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch("sqlcl_conn_mng.sqlcl.check_connection", return_value="ok")
    assert main(["test", *_base(fake_home), "--filter", "*_*"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "[OK] dev_local",
        "[OK] root_conn",
        "Summary: 2 ok, 0 failed",
    ]


@pytest.mark.unit
@pytest.mark.parametrize("command", [["test"], ["show"], ["move", "--folder", "/x"]])
def test_empty_selection_exits_one(
    command: list[str], fake_home: Path, mocker: MockerFixture, caplog: pytest.LogCaptureFixture
) -> None:
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main([*command, *_base(fake_home), "--filter", "nomatch*"]) == 1
    assert "No connections match --filter 'nomatch*'" in caplog.text
    run.assert_not_called()


@pytest.mark.unit
def test_delete_batch_without_yes_deletes_nothing(fake_home: Path, mocker: MockerFixture) -> None:
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(["delete", *_base(fake_home), "--all"]) == 1
    assert main(["delete", *_base(fake_home), "--filter", "dev_*"]) == 1
    run.assert_not_called()


@pytest.mark.unit
def test_delete_batch_lists_names_then_deletes(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    fake = _fail_on("root_conn", mocker, "sqlcl_conn_mng.sqlcl.delete_connection")
    argv = ["delete", *_base(fake_home), "--filter", "*_*", "--yes"]
    assert main(argv) == 1
    assert [c.args[1] for c in fake.call_args_list] == ["dev_local", "root_conn"]
    assert capsys.readouterr().out.splitlines() == [
        "Deleting 2 connection(s): dev_local, root_conn",
        "[OK] dev_local",
        "[FAIL] root_conn: boom root_conn",
        "Summary: 1 ok, 1 failed",
    ]


@pytest.mark.unit
def test_delete_name_with_yes_output_unchanged(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch("sqlcl_conn_mng.sqlcl.delete_connection", return_value="gone")
    assert main(["delete", *_base(fake_home), "--name", "dev_local", "--yes"]) == 0
    assert capsys.readouterr().out == "gone\n"


@pytest.mark.unit
def test_move_batch_passes_folder_to_each(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    fake = mocker.patch("sqlcl_conn_mng.sqlcl.move_connection", return_value="moved")
    assert main(["move", *_base(fake_home), "--filter", "*_*", "--folder", "/x"]) == 0
    assert [(c.args[1], c.args[2]) for c in fake.call_args_list] == [
        ("dev_local", "/x"),
        ("root_conn", "/x"),
    ]
    assert "Summary: 2 ok, 0 failed" in capsys.readouterr().out


@pytest.mark.unit
def test_show_name_json_is_object(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    argv = ["show", "--home", str(fake_home), "--name", "dev_local", "--format", "json"]
    assert main(argv) == 0
    assert isinstance(json.loads(capsys.readouterr().out), dict)


@pytest.mark.unit
def test_show_batch_json_is_sorted_list(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["show", "--home", str(fake_home), "--filter", "*_*", "--format", "json"]
    assert main(argv) == 0
    data = json.loads(capsys.readouterr().out)
    assert [c["name"] for c in data] == ["dev_local", "root_conn"]
    assert all("wallet_present" in c for c in data)


@pytest.mark.unit
def test_show_batch_table_blocks_separated_by_blank_line(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["show", "--home", str(fake_home), "--all"]) == 0
    blocks = capsys.readouterr().out.strip().split("\n\n")
    assert [b.splitlines()[0] for b in blocks] == [
        "Name: Prod One",
        "Name: dev_local",
        "Name: root_conn",
    ]


@pytest.mark.unit
def test_show_batch_check_password_continues_after_failure(
    fake_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    def fake(runner: object, name: str) -> object:
        if name == "dev_local":
            raise SqlclError("boom")
        return mocker.Mock(password_saved=True)

    mocker.patch("sqlcl_conn_mng.sqlcl.show_connection", side_effect=fake)
    argv = ["show", *_base(fake_home), "--all", "--check-password", "--format", "json"]
    assert main(argv) == 1
    data = json.loads(capsys.readouterr().out)
    assert [c["name"] for c in data] == ["Prod One", "root_conn"]


@pytest.mark.unit
def test_list_filter_table(fake_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--home", str(fake_home), "--filter", "dev_*"]) == 0
    out = capsys.readouterr().out
    assert "dev_local" in out
    assert "root_conn" not in out
    assert "Prod One" not in out


@pytest.mark.unit
def test_list_filter_json_and_folder_are_anded(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    base = ["list", "--home", str(fake_home), "--format", "json"]
    assert main([*base, "--filter", "*_*"]) == 0
    assert [c["name"] for c in json.loads(capsys.readouterr().out)] == ["dev_local", "root_conn"]
    assert main([*base, "--filter", "*_*", "--folder", "/dev"]) == 0
    assert [c["name"] for c in json.loads(capsys.readouterr().out)] == ["dev_local"]
    assert main([*base, "--filter", "root_*", "--folder", "/dev"]) == 0
    assert json.loads(capsys.readouterr().out) == []


@pytest.mark.unit
def test_list_filter_no_match_prints_header_only(
    fake_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["list", "--home", str(fake_home), "--filter", "nomatch*"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("name")


@pytest.mark.unit
def test_export_filter_writes_only_matches(
    fake_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "out.json"
    argv = ["export", "--home", str(fake_home), "--output", str(target), "--filter", "dev_*"]
    assert main(argv) == 0
    data = json.loads(target.read_text(encoding="utf-8"))
    assert [c["name"] for c in data["connections"]] == ["dev_local"]
    assert f"Exported 1 connection(s) to {target}" in capsys.readouterr().out


@pytest.mark.unit
def test_export_filter_no_match_exports_zero(
    fake_home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "out.json"
    argv = ["export", "--home", str(fake_home), "--output", str(target), "--filter", "nomatch*"]
    assert main(argv) == 0
    assert json.loads(target.read_text(encoding="utf-8")) == {"connections": []}
    assert "Exported 0 connection(s)" in capsys.readouterr().out


@pytest.fixture
def dup_home(fake_home: Path) -> Path:
    """Return fake_home plus a second connection that is also named dev_local."""
    write_connection(
        fake_home,
        "DDDDDDDDDDDDDDDDDDDDDD",
        "name=dev_local\ntype=ORACLE_DATABASE\nconnectionString=//other.example.test\\:1521/x\n"
        "userName=other\n",
    )
    return fake_home


@pytest.mark.unit
@pytest.mark.parametrize(
    "command",
    [
        ["test"],
        ["show", "--check-password"],
        ["delete", "--yes"],
        ["move", "--folder", "/x"],
    ],
    ids=lambda c: c[0],
)
@pytest.mark.parametrize("selector", [["--all"], ["--filter", "dev_*"]])
def test_batch_with_duplicate_names_is_refused(
    command: list[str],
    selector: list[str],
    dup_home: Path,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """P1 review: a name shared by two connections cannot be acted on one at a time."""
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main([*command, *_base(dup_home), *selector]) == 1
    assert "Ambiguous selection" in caplog.text
    assert "'dev_local'" in caplog.text
    run.assert_not_called()


@pytest.mark.unit
def test_batch_skipping_the_duplicate_name_still_runs(
    dup_home: Path, capsys: pytest.CaptureFixture[str], mocker: MockerFixture
) -> None:
    mocker.patch("sqlcl_conn_mng.sqlcl.check_connection", return_value="ok")
    assert main(["test", *_base(dup_home), "--filter", "root_*"]) == 0
    assert "[OK] root_conn" in capsys.readouterr().out


@pytest.mark.unit
def test_plain_show_lists_every_duplicate_record(
    dup_home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """P2 review: metadata-only show needs no SQLcl, so it can show both records."""
    argv = ["show", "--home", str(dup_home), "--filter", "dev_*", "--format", "json"]
    assert main(argv) == 0
    data = json.loads(capsys.readouterr().out)
    assert [c["name"] for c in data] == ["dev_local", "dev_local"]
    assert len({c["id"] for c in data}) == 2


@pytest.mark.unit
@pytest.mark.parametrize("command", [["test"], ["move", "--folder", "/x"]])
def test_empty_batch_is_reported_before_sqlcl_is_resolved(
    command: list[str],
    fake_home: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """P2 review: no match must say so even when SQLcl is not installed."""
    monkeypatch.delenv("SQLCL_BIN", raising=False)
    mocker.patch("sqlcl_conn_mng.sqlcl.shutil.which", return_value=None)
    argv = [*command, "--home", str(fake_home), "--filter", "nomatch*"]
    assert main(argv) == 1
    assert "No connections match" in caplog.text
    assert "SQLcl not found" not in caplog.text


# ---- update ----

SECRET = "fake-pwd-9z"
UPD_ID_A = "DDDDDDDDDDDDDDDDDDDDDD"
UPD_ID_B = "EEEEEEEEEEEEEEEEEEEEEE"
UPD_PROPS = "name={name}\ntype=ORACLE_DATABASE\nconnectionString=//h:1521/s\nuserName=scott\n"


def _upd_home(tmp_path: Path, extra: tuple[str, ...] = ()) -> Path:
    home = tmp_path / "upd"
    write_connection(home, UPD_ID_A, UPD_PROPS.format(name="alpha"))
    for index, name in enumerate(extra):
        write_connection(home, "F" * 21 + str(index), UPD_PROPS.format(name=name))
    return home


def _upd_argv(home: Path, *rest: str) -> list[str]:
    return ["update", "--home", str(home), "--sqlcl", "sql-bin", "--name", "alpha", *rest]


def _tree(home: Path) -> dict[str, bytes]:
    return {p.relative_to(home).as_posix(): p.read_bytes() for p in home.rglob("*") if p.is_file()}


def _ok_run(mocker: MockerFixture) -> object:
    return mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        return_value=mocker.Mock(stdout="Connection created and saved", stderr=""),
    )


@pytest.mark.unit
def test_update_help_lists_options(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["update", "--help"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for option in (
        "--name",
        "--new-name",
        "--user",
        "--connect-string",
        "--password-env",
        "--prompt-password",
        "--no-save-password",
    ):
        assert option in out
    assert "--filter" not in out
    assert "--all" not in out


@pytest.mark.unit
@pytest.mark.parametrize(
    "rest",
    [[], ["--no-save-password"], ["--user", ""], ["--new-name", 'a"b']],
)
def test_update_bad_options_write_nothing(
    tmp_path: Path, mocker: MockerFixture, rest: list[str]
) -> None:
    home = _upd_home(tmp_path)
    before = _tree(home)
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(_upd_argv(home, *rest)) == 1
    assert _tree(home) == before
    run.assert_not_called()


@pytest.mark.unit
def test_update_both_password_sources_is_usage_error(tmp_path: Path) -> None:
    home = _upd_home(tmp_path)
    with pytest.raises(SystemExit) as exc:
        main(_upd_argv(home, "--password-env", "X", "--prompt-password"))
    assert exc.value.code == 2


@pytest.mark.unit
def test_update_unknown_name_writes_nothing(tmp_path: Path, mocker: MockerFixture) -> None:
    home = _upd_home(tmp_path)
    before = _tree(home)
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    argv = ["update", "--home", str(home), "--name", "nosuch", "--user", "x"]
    assert main(argv) == 1
    assert _tree(home) == before
    run.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("rest", "expected"),
    [
        (
            ["--user", "hr"],
            "name=alpha\ntype=ORACLE_DATABASE\nconnectionString=//h\\:1521/s\nuserName=hr\n",
        ),
        (
            ["--connect-string", "//x:1/y"],
            "name=alpha\ntype=ORACLE_DATABASE\nconnectionString=//x\\:1/y\nuserName=scott\n",
        ),
        (
            ["--new-name", "beta"],
            "name=beta\ntype=ORACLE_DATABASE\nconnectionString=//h\\:1521/s\nuserName=scott\n",
        ),
    ],
)
def test_update_metadata_only_changes_one_value(
    tmp_path: Path, mocker: MockerFixture, rest: list[str], expected: str
) -> None:
    home = _upd_home(tmp_path)
    before = _tree(home)
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(_upd_argv(home, *rest)) == 0
    run.assert_not_called()
    after = _tree(home)
    props = f"connections/{UPD_ID_A}/dbtools.properties"
    assert after.pop(props).decode("utf-8") == expected
    before.pop(props)
    assert after == before


@pytest.mark.unit
@pytest.mark.parametrize("new_name", ["BETA", "beta"])
def test_update_new_name_collision_any_case_refused(
    tmp_path: Path, mocker: MockerFixture, new_name: str
) -> None:
    home = _upd_home(tmp_path, extra=("beta",))
    before = _tree(home)
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(_upd_argv(home, "--new-name", new_name)) == 1
    assert _tree(home) == before
    run.assert_not_called()


@pytest.mark.unit
def test_update_case_only_rename_of_itself_allowed(tmp_path: Path) -> None:
    home = _upd_home(tmp_path)
    assert main(_upd_argv(home, "--new-name", "ALPHA")) == 0
    assert _store_names(home) == ["ALPHA"]


def _store_names(home: Path) -> list[str]:
    return [c.name for c in ConnectionStore(home).connections()]


@pytest.mark.unit
def test_update_duplicate_record_names_refused(tmp_path: Path) -> None:
    home = _upd_home(tmp_path, extra=("alpha",))
    before = _tree(home)
    assert main(_upd_argv(home, "--user", "hr")) == 1
    assert _tree(home) == before


@pytest.mark.unit
def test_update_password_only_runs_replace_with_stored_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = _upd_home(tmp_path)
    before = _tree(home)
    run = _ok_run(mocker)
    assert main(_upd_argv(home, "--password-env", "FAKE_PWD_VAR")) == 0
    assert run.call_count == 1  # type: ignore[attr-defined]
    call = run.call_args  # type: ignore[attr-defined]
    script = call.kwargs["input"]
    assert "connect -save alpha -savepwd -replace" in script
    assert "scott@//h:1521/s" in script
    assert all(SECRET not in part for part in call.args[0])
    assert _tree(home) == before
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err


@pytest.mark.unit
def test_update_no_save_password_drops_savepwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = _upd_home(tmp_path)
    run = _ok_run(mocker)
    assert main(_upd_argv(home, "--password-env", "FAKE_PWD_VAR", "--no-save-password")) == 0
    script = run.call_args.kwargs["input"]  # type: ignore[attr-defined]
    assert "-savepwd" not in script
    assert "-replace" in script


@pytest.mark.unit
def test_update_prompt_password_uses_hidden_prompt(tmp_path: Path, mocker: MockerFixture) -> None:
    home = _upd_home(tmp_path)
    prompt = mocker.patch("sqlcl_conn_mng.cli.getpass.getpass", return_value=SECRET)
    run = _ok_run(mocker)
    assert main(_upd_argv(home, "--prompt-password")) == 0
    prompt.assert_called_once()
    assert SECRET in run.call_args.kwargs["input"]  # type: ignore[attr-defined]


@pytest.mark.unit
def test_update_combined_connects_with_new_values_then_writes_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = _upd_home(tmp_path)
    run = _ok_run(mocker)
    rest = [
        "--password-env",
        "FAKE_PWD_VAR",
        "--user",
        "hr",
        "--connect-string",
        "//x:1/y",
        "--new-name",
        "beta",
    ]
    assert main(_upd_argv(home, *rest)) == 0
    script = run.call_args.kwargs["input"]  # type: ignore[attr-defined]
    # the connect runs under the old name with the new user and connect string
    assert "connect -save alpha" in script
    assert "hr@//x:1/y" in script
    conn = ConnectionStore(home).connections()[0]
    assert (conn.id, conn.name, conn.user_name, conn.connect_string) == (
        UPD_ID_A,
        "beta",
        "hr",
        "//x:1/y",
    )
    captured = capsys.readouterr()
    assert SECRET not in captured.out + captured.err


@pytest.mark.unit
def test_update_failed_connect_leaves_store_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = _upd_home(tmp_path)
    before = _tree(home)
    mocker.patch(
        "sqlcl_conn_mng.sqlcl.subprocess.run",
        return_value=mocker.Mock(stdout="Connection failed ORA-01017", stderr=""),
    )
    rest = ["--password-env", "FAKE_PWD_VAR", "--user", "hr", "--new-name", "beta"]
    assert main(_upd_argv(home, *rest)) == 1
    assert _tree(home) == before


@pytest.mark.unit
def test_update_file_write_failure_after_password_step_says_so(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    mocker: MockerFixture,
) -> None:
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = _upd_home(tmp_path)
    _ok_run(mocker)
    mocker.patch.object(ConnectionStore, "update_properties", side_effect=OSError("locked"))
    assert main(_upd_argv(home, "--password-env", "FAKE_PWD_VAR", "--user", "hr")) == 1
    assert "password was already replaced" in caplog.text
    assert SECRET not in caplog.text


BASIC_PROPS = "name=alpha\ntype=ORACLE_BASIC\nhost=h1\nport=1521\nserviceName=s1\nuserName=scott\n"


@pytest.mark.unit
def test_update_connect_string_on_imported_connection_converts_it(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    home = tmp_path / "basic"
    write_connection(home, UPD_ID_A, BASIC_PROPS)
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(_upd_argv(home, "--connect-string", "//x:1/y")) == 0
    run.assert_not_called()
    conn = ConnectionStore(home).connections()[0]
    assert (conn.type, conn.connect_string, conn.extra) == ("ORACLE_DATABASE", "//x:1/y", {})


@pytest.mark.unit
def test_update_connect_string_unsupported_type_writes_nothing(
    tmp_path: Path, mocker: MockerFixture
) -> None:
    home = tmp_path / "tns"
    write_connection(home, UPD_ID_A, "name=alpha\ntype=ORACLE_TNS\ntnsAlias=a\nuserName=scott\n")
    before = _tree(home)
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(_upd_argv(home, "--connect-string", "//x:1/y")) == 1
    assert _tree(home) == before
    run.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("props", "target"),
    [
        (BASIC_PROPS, "scott@//h1:1521/s1"),
        (
            "name=alpha\ntype=ORACLE_BASIC\nhost=h1\nserviceName=s1\nuserName=scott\n",
            "scott@//h1/s1",
        ),
    ],
)
def test_p1_password_update_derives_target_of_imported_connection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mocker: MockerFixture,
    props: str,
    target: str,
) -> None:
    """P1 (PR #4): the connect target of an ORACLE_BASIC connection comes from host/port/service."""
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = tmp_path / "basic_pw"
    write_connection(home, UPD_ID_A, props)
    run = _ok_run(mocker)
    assert main(_upd_argv(home, "--password-env", "FAKE_PWD_VAR")) == 0
    assert target in run.call_args.kwargs["input"]  # type: ignore[attr-defined]


@pytest.mark.unit
def test_p1_password_update_imported_without_target_fails_before_connect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mocker: MockerFixture
) -> None:
    """P1 (PR #4): an imported connection with no host or service cannot be addressed."""
    monkeypatch.setenv("FAKE_PWD_VAR", SECRET)
    home = tmp_path / "basic_nohost"
    write_connection(home, UPD_ID_A, "name=alpha\ntype=ORACLE_BASIC\nuserName=scott\n")
    run = mocker.patch("sqlcl_conn_mng.sqlcl.subprocess.run")
    assert main(_upd_argv(home, "--password-env", "FAKE_PWD_VAR")) == 1
    run.assert_not_called()
