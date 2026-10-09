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
from tests.conftest import ID_DEV


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
