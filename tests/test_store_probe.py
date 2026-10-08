"""Tests for scripts/store_probe.py. All data is fake."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

WALLET_MARKER = b"WALLET-MARKER-7f3a9c"
PLANTED_PW = "PW-PLANTED-91be42"
PLANTED_PW2 = "PW-PLANTED-2-c0ffee"
PLANTED_PW3 = "PW-CHANGED-5d1e77"
CONN_A = "AAAAAAAAAAAAAAAAAAAAAA"
CONN_B = "BBBBBBBBBBBBBBBBBBBBBB"

PROPS_TEXT = (
    "# header comment\n"
    "name=dev_local\n"
    "connectionString=//h\\:1521/s\n"
    f"password={PLANTED_PW}\n"
    f"customPwd={PLANTED_PW2}\n"
)


def _load_module() -> ModuleType:
    """Import the probe script as a module."""
    path = Path(__file__).resolve().parent.parent / "scripts" / "store_probe.py"
    spec = importlib.util.spec_from_file_location("store_probe", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = _load_module()


def _folders(dev: list[str], prod: list[str], extra: bool = False) -> dict[str, object]:
    """Build a folders.json document."""
    folders: list[dict[str, object]] = [
        {
            "name": "dev",
            "connections": [],
            "folders": [{"name": "local", "connections": dev, "folders": []}],
        },
        {"name": "prod", "connections": prod, "folders": []},
    ]
    if extra:
        folders.append({"name": "extra", "connections": [], "folders": []})
    return {"folders": folders}


def _write_store(
    home: Path,
    props: str = PROPS_TEXT,
    folders: dict[str, object] | None = None,
) -> None:
    """Create a fake store with one connection and a nested folder."""
    conn_dir = home / "connections" / CONN_A
    conn_dir.mkdir(parents=True, exist_ok=True)
    (conn_dir / "dbtools.properties").write_bytes(props.encode("utf-8"))
    (conn_dir / "credentials.sso").write_bytes(WALLET_MARKER)
    folder_dir = home / "connection_folders"
    folder_dir.mkdir(exist_ok=True)
    doc = folders if folders is not None else _folders([CONN_A], [])
    text = json.dumps(doc, indent=2) + "\n"
    (folder_dir / "folders.json").write_bytes(text.encode("utf-8"))


def _snap(home: Path, out: Path) -> int:
    """Run the snapshot command."""
    return int(probe.main(["--command", "snapshot", "--home", str(home), "--output", str(out)]))


def _diff(before: Path, after: Path) -> int:
    """Run the diff command."""
    return int(probe.main(["--command", "diff", "--before", str(before), "--after", str(after)]))


def test_snapshot_records_files_and_facts(tmp_path: Path) -> None:
    home = tmp_path / "store"
    _write_store(home)
    out = tmp_path / "snap" / "a.json"
    assert _snap(home, out) == 0
    snap = json.loads(out.read_text(encoding="utf-8"))
    files = snap["files"]
    assert sorted(files) == [
        "connection_folders/folders.json",
        f"connections/{CONN_A}/credentials.sso",
        f"connections/{CONN_A}/dbtools.properties",
    ]
    sso = files[f"connections/{CONN_A}/credentials.sso"]
    assert sso == {"size": len(WALLET_MARKER), "sha12": sso["sha12"]}
    assert len(sso["sha12"]) == 12
    props = files[f"connections/{CONN_A}/dbtools.properties"]
    assert props["size"] == len(PROPS_TEXT.encode("utf-8"))
    assert props["properties"]["name"] == "dev_local"
    assert props["properties"]["connectionString"] == "//h:1521/s"
    assert props["key_order"] == ["name", "connectionString", "password", "customPwd"]
    assert props["line_ending"] == "LF"
    assert props["trailing_newline"] is True
    assert props["encoding_ok_utf8"] is True
    assert props["comment_lines"] == ["# header comment"]
    for key, plain in (("password", PLANTED_PW), ("customPwd", PLANTED_PW2)):
        entry = props["properties"][key]
        assert entry["redacted"] is True
        assert entry["size"] == len(plain)
        assert len(entry["sha12"]) == 12
    folders = files["connection_folders/folders.json"]
    assert folders["json"] == _folders([CONN_A], [])
    assert folders["indent"] == "2 spaces"
    assert folders["line_ending"] == "LF"
    assert folders["trailing_newline"] is True


def test_snapshot_empty_dir_and_missing_home(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    out = tmp_path / "empty.json"
    assert _snap(empty, out) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["files"] == {}
    assert "0 files" in capsys.readouterr().out
    assert _snap(tmp_path / "missing", tmp_path / "x.json") == 1
    assert capsys.readouterr().err.startswith("error:")


def test_diff_reports_changes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "store"
    _write_store(home)
    before = tmp_path / "before.json"
    _snap(home, before)
    # change a key, add a connection, remove a file, move an id, add a folder
    changed = PROPS_TEXT.replace("name=dev_local", "name=renamed")
    (home / "connections" / CONN_A / "dbtools.properties").write_text(changed, encoding="utf-8")
    (home / "connections" / CONN_A / "credentials.sso").unlink()
    new_dir = home / "connections" / CONN_B
    new_dir.mkdir()
    (new_dir / "dbtools.properties").write_text("name=second\nuserName=hr\n", encoding="utf-8")
    doc = _folders([], [CONN_A, CONN_B], extra=True)
    (home / "connection_folders" / "folders.json").write_text(json.dumps(doc), encoding="utf-8")
    after = tmp_path / "after.json"
    _snap(home, after)
    capsys.readouterr()
    assert _diff(before, after) == 0
    out = capsys.readouterr().out
    assert f"added connections/{CONN_B}/dbtools.properties" in out
    assert "  key name = second" in out
    assert f"removed connections/{CONN_A}/credentials.sso" in out
    assert "  key changed name: dev_local -> renamed" in out
    assert f"  connection {CONN_A} moved /dev/local -> /prod" in out
    assert f"  connection {CONN_B} added to /prod" in out
    assert "  folder added /extra" in out
    assert "changed connection_folders/folders.json" in out
    assert "unchanged 0" in out


def test_diff_order_changed(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "store"
    _write_store(home, folders=_folders([], [CONN_A, CONN_B]))
    before = tmp_path / "b.json"
    _snap(home, before)
    doc = _folders([], [CONN_B, CONN_A])
    (home / "connection_folders" / "folders.json").write_text(json.dumps(doc), encoding="utf-8")
    after = tmp_path / "a.json"
    _snap(home, after)
    capsys.readouterr()
    assert _diff(before, after) == 0
    assert "  order changed in /prod" in capsys.readouterr().out


def test_no_secrets_reach_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    home = tmp_path / "store"
    _write_store(home)
    before = tmp_path / "before.json"
    after = tmp_path / "after.json"
    _snap(home, before)
    changed = PROPS_TEXT.replace(PLANTED_PW, PLANTED_PW3)
    (home / "connections" / CONN_A / "dbtools.properties").write_text(changed, encoding="utf-8")
    (home / "connections" / CONN_A / "credentials.sso").write_bytes(WALLET_MARKER + b"-2")
    _snap(home, after)
    assert _diff(before, after) == 0
    captured = capsys.readouterr()
    assert "key changed password: <redacted size=" in captured.out
    seen = (captured.out + captured.err).encode("utf-8")
    seen += before.read_bytes() + after.read_bytes()
    for secret in (WALLET_MARKER, PLANTED_PW.encode(), PLANTED_PW2.encode(), PLANTED_PW3.encode()):
        assert secret not in seen
    assert b"PW-" not in seen
    assert b"WALLET-MARKER" not in seen


def test_snapshot_requires_output() -> None:
    with pytest.raises(SystemExit) as info:
        probe.main(["--command", "snapshot", "--home", "somewhere"])
    assert info.value.code == 2


def test_diff_requires_after() -> None:
    with pytest.raises(SystemExit) as info:
        probe.main(["--command", "diff", "--before", "a.json"])
    assert info.value.code == 2
