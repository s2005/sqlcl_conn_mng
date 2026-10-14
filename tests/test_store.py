"""Tests for the connection store."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from sqlcl_conn_mng.store import ConnectionStore, StoreError, new_connection_id, resolve_home
from tests.conftest import ID_DEV, ID_PROD, ID_ROOT, write_connection


@pytest.mark.unit
def test_lists_connections_sorted_with_folders(fake_home: Path) -> None:
    conns = ConnectionStore(fake_home).connections()
    assert [c.name for c in conns] == ["Prod One", "dev_local", "root_conn"]
    by_name = {c.name: c for c in conns}
    assert by_name["dev_local"].folder == "/dev/local"
    assert by_name["dev_local"].connect_string == "//localhost:1521/freepdb1"
    assert by_name["dev_local"].extra == {"extraKey": "extraValue"}
    assert by_name["root_conn"].folder == "/"
    assert by_name["Prod One"].folder == "/prod"


@pytest.mark.unit
def test_get_is_case_sensitive_and_by_name_not_dir(fake_home: Path) -> None:
    store = ConnectionStore(fake_home)
    found = store.get("dev_local")
    assert found is not None
    assert found.id == ID_DEV
    assert store.get("DEV_LOCAL") is None
    assert store.get(ID_DEV) is None


@pytest.mark.unit
def test_folder_tree_and_paths(fake_home: Path) -> None:
    store = ConnectionStore(fake_home)
    folders = store.folders()
    assert [f.path for f in folders] == ["/dev", "/prod"]
    assert folders[0].folders[0].path == "/dev/local"
    assert store.folder_paths() == {ID_DEV: "/dev/local", ID_PROD: "/prod"}
    assert ID_ROOT not in store.folder_paths()


@pytest.mark.unit
def test_has_wallet_checks_existence_only(fake_home: Path) -> None:
    store = ConnectionStore(fake_home)
    assert store.has_wallet(ID_DEV)
    (fake_home / "connections" / ID_DEV / "credentials.sso").unlink()
    assert not store.has_wallet(ID_DEV)


@pytest.mark.unit
def test_missing_store_and_missing_folders_file(tmp_path: Path) -> None:
    store = ConnectionStore(tmp_path / "nothing")
    assert store.connections() == []
    assert store.folders() == []


@pytest.mark.unit
def test_non_id_directories_are_ignored(fake_home: Path) -> None:
    (fake_home / "connections" / "short").mkdir()
    (fake_home / "connections" / "short" / "dbtools.properties").write_text("name=x\n")
    assert len(ConnectionStore(fake_home).connections()) == 3


@pytest.mark.unit
def test_malformed_folders_json(fake_home: Path) -> None:
    (fake_home / "connection_folders" / "folders.json").write_text("{nope", encoding="utf-8")
    with pytest.raises(StoreError):
        ConnectionStore(fake_home).folders()


@pytest.mark.unit
@pytest.mark.parametrize("value", [None, 5, True, "x"])
@pytest.mark.parametrize(
    ("key", "where", "build"),
    [
        ("folders", "the top level", lambda v: {"folders": v}),
        ("folders", "/dev", lambda v: {"folders": [{"name": "dev", "folders": v}]}),
        ("connections", "/dev", lambda v: {"folders": [{"name": "dev", "connections": v}]}),
    ],
    ids=["top-folders", "nested-folders", "connections"],
)
def test_non_list_folder_values_raise_store_error(
    tmp_path: Path, key: str, where: str, build: Callable[[object], object], value: object
) -> None:
    home = tmp_path / "store"
    (home / "connection_folders").mkdir(parents=True)
    (home / "connection_folders" / "folders.json").write_text(
        json.dumps(build(value)), encoding="utf-8"
    )
    with pytest.raises(StoreError) as info:
        ConnectionStore(home).folders()
    message = str(info.value)
    assert message.startswith("Malformed folders.json:")
    assert repr(key) in message
    assert where in message


@pytest.mark.unit
def test_resolve_home_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = {"SQLCL_CONN_HOME": str(tmp_path / "env")}
    assert resolve_home(str(tmp_path / "opt"), env) == tmp_path / "opt"
    assert resolve_home(None, env) == tmp_path / "env"
    monkeypatch.chdir(tmp_path)
    assert resolve_home(None, {}) == tmp_path / ".sqlcl"


def _plain_store(tmp_path: Path, props_text: str) -> tuple[Path, Path]:
    """Create a one-connection store and return its home and properties file."""
    home = tmp_path / "plain"
    write_connection(home, ID_DEV, props_text)
    return home, home / "connections" / ID_DEV / "dbtools.properties"


PLAIN = "name=dev\ntype=ORACLE_DATABASE\nconnectionString=//h\\:1521/s\nuserName=scott\nextra=1\n"


@pytest.mark.unit
def test_update_properties_changes_only_given_keys(tmp_path: Path) -> None:
    home, props = _plain_store(tmp_path, PLAIN)
    wallet = home / "connections" / ID_DEV / "credentials.sso"
    wallet_before = wallet.read_bytes()
    ConnectionStore(home).update_properties(ID_DEV, {"userName": "hr", "name": "dev2"})
    assert props.read_bytes() == (
        b"name=dev2\ntype=ORACLE_DATABASE\nconnectionString=//h\\:1521/s\nuserName=hr\nextra=1\n"
    )
    assert wallet.read_bytes() == wallet_before
    assert sorted(p.name for p in props.parent.iterdir()) == [
        "credentials.sso",
        "dbtools.properties",
    ]


@pytest.mark.unit
def test_update_properties_leaves_folders_json_alone(fake_home: Path) -> None:
    folders = fake_home / "connection_folders" / "folders.json"
    before = folders.read_bytes()
    home, _ = _plain_store(fake_home.parent, PLAIN)
    ConnectionStore(home).update_properties(ID_DEV, {"connectionString": "//x:1/y"})
    assert folders.read_bytes() == before


@pytest.mark.unit
def test_update_properties_round_trips_special_values(tmp_path: Path) -> None:
    home, _ = _plain_store(tmp_path, PLAIN)
    store = ConnectionStore(home)
    weird = " we:ird=#!\\ name\\u00e9"
    store.update_properties(ID_DEV, {"name": weird})
    found = store.connections()[0]
    assert found.name == weird
    assert found.user_name == "scott"
    assert found.extra == {"extra": "1"}


@pytest.mark.unit
def test_update_properties_missing_file(tmp_path: Path) -> None:
    with pytest.raises(StoreError):
        ConnectionStore(tmp_path / "none").update_properties(ID_DEV, {"name": "x"})


@pytest.mark.unit
@pytest.mark.parametrize("text", ["#note\n" + PLAIN, "! note\n" + PLAIN, PLAIN + "long=a\\\nb\n"])
def test_update_properties_refuses_comment_and_continuation(tmp_path: Path, text: str) -> None:
    home, props = _plain_store(tmp_path, text)
    before = props.read_bytes()
    with pytest.raises(StoreError):
        ConnectionStore(home).update_properties(ID_DEV, {"name": "x"})
    assert props.read_bytes() == before


@pytest.mark.unit
def test_update_properties_refuses_other_keys(tmp_path: Path) -> None:
    home, props = _plain_store(tmp_path, PLAIN)
    before = props.read_bytes()
    with pytest.raises(StoreError):
        ConnectionStore(home).update_properties(ID_DEV, {"type": "X"})
    assert props.read_bytes() == before


@pytest.mark.unit
def test_update_properties_failed_replace_leaves_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home, props = _plain_store(tmp_path, PLAIN)
    before = props.read_bytes()

    def boom(*_args: object) -> None:
        raise OSError("locked")

    monkeypatch.setattr("sqlcl_conn_mng.store.os.replace", boom)
    with pytest.raises(OSError, match="locked"):
        ConnectionStore(home).update_properties(ID_DEV, {"name": "x"})
    assert props.read_bytes() == before
    assert sorted(p.name for p in props.parent.iterdir()) == [
        "credentials.sso",
        "dbtools.properties",
    ]


BASIC = "name=imp\ntype=ORACLE_BASIC\nhost=h1\nport=1521\nserviceName=s1\nuserName=scott\n"


@pytest.mark.unit
def test_update_properties_connect_string_converts_basic_like_sqlcl(tmp_path: Path) -> None:
    home, props = _plain_store(tmp_path, BASIC)
    ConnectionStore(home).update_properties(ID_DEV, {"connectionString": "//h2:1/s2"})
    assert props.read_bytes() == (
        b"name=imp\ntype=ORACLE_DATABASE\nconnectionString=//h2\\:1/s2\nuserName=scott\n"
    )
    found = ConnectionStore(home).connections()[0]
    assert (found.type, found.connect_string, found.extra) == ("ORACLE_DATABASE", "//h2:1/s2", {})


@pytest.mark.unit
def test_update_properties_basic_keeps_unrelated_keys_and_applies_other_changes(
    tmp_path: Path,
) -> None:
    home, props = _plain_store(tmp_path, BASIC + "role=SYSDBA\n")
    changes = {"connectionString": "//h2:1/s2", "userName": "hr", "name": "imp2"}
    ConnectionStore(home).update_properties(ID_DEV, changes)
    assert props.read_bytes() == (
        b"name=imp2\ntype=ORACLE_DATABASE\nconnectionString=//h2\\:1/s2\nuserName=hr\nrole=SYSDBA\n"
    )


@pytest.mark.unit
@pytest.mark.parametrize("changes", [{"userName": "hr"}, {"name": "imp2"}])
def test_update_properties_basic_untouched_without_connect_string(
    tmp_path: Path, changes: dict[str, str]
) -> None:
    home, props = _plain_store(tmp_path, BASIC)
    ConnectionStore(home).update_properties(ID_DEV, changes)
    text = props.read_text(encoding="utf-8")
    assert "type=ORACLE_BASIC\nhost=h1\nport=1521\nserviceName=s1\n" in text
    assert "connectionString" not in text


@pytest.mark.unit
def test_update_properties_connect_string_refused_for_other_type(tmp_path: Path) -> None:
    home, props = _plain_store(tmp_path, "name=x\ntype=ORACLE_TNS\ntnsAlias=a\nuserName=u\n")
    before = props.read_bytes()
    with pytest.raises(StoreError, match="ORACLE_TNS"):
        ConnectionStore(home).update_properties(ID_DEV, {"connectionString": "//h:1/s"})
    assert props.read_bytes() == before


# ---- copy_connection_to ----

_NEW_ID = re.compile(r"[A-Za-z0-9_-]{22}")


def _snapshot(home: Path) -> dict[str, bytes]:
    return {p.relative_to(home).as_posix(): p.read_bytes() for p in home.rglob("*") if p.is_file()}


@pytest.mark.unit
def test_new_connection_id_shape_and_skips_existing() -> None:
    new_id = new_connection_id(set())
    assert _NEW_ID.fullmatch(new_id)
    assert new_connection_id({new_id}) != new_id


@pytest.mark.unit
def test_copy_connection_is_byte_identical_under_a_new_id(fake_home: Path, tmp_path: Path) -> None:
    target = ConnectionStore(tmp_path / "target")
    write_connection(target.home, ID_ROOT, "name=other\ntype=ORACLE_DATABASE\n")
    new_id = ConnectionStore(fake_home).copy_connection_to(ID_DEV, target)
    assert _NEW_ID.fullmatch(new_id)
    assert new_id not in {ID_DEV, ID_ROOT}
    src = fake_home / "connections" / ID_DEV
    dst = target.home / "connections" / new_id
    assert (dst / "dbtools.properties").read_bytes() == (src / "dbtools.properties").read_bytes()
    assert (dst / "credentials.sso").read_bytes() == b"fake-wallet-bytes"
    assert sorted(p.name for p in dst.iterdir()) == ["credentials.sso", "dbtools.properties"]
    copied = target.get("dev_local")
    assert copied is not None
    assert (copied.id, copied.folder) == (new_id, "/")


@pytest.mark.unit
def test_copy_connection_without_wallet_has_none(fake_home: Path, tmp_path: Path) -> None:
    (fake_home / "connections" / ID_ROOT / "credentials.sso").unlink()
    target = ConnectionStore(tmp_path / "target")
    new_id = ConnectionStore(fake_home).copy_connection_to(ID_ROOT, target)
    assert (target.home / "connections" / new_id / "dbtools.properties").is_file()
    assert not target.has_wallet(new_id)


@pytest.mark.unit
def test_copy_connection_creates_a_missing_target_home(fake_home: Path, tmp_path: Path) -> None:
    target = ConnectionStore(tmp_path / "deep" / "target")
    ConnectionStore(fake_home).copy_connection_to(ID_PROD, target)
    assert [c.name for c in target.connections()] == ["Prod One"]


@pytest.mark.unit
def test_copy_connection_leaves_the_source_unchanged(fake_home: Path, tmp_path: Path) -> None:
    before = _snapshot(fake_home)
    ConnectionStore(fake_home).copy_connection_to(ID_DEV, ConnectionStore(tmp_path / "target"))
    assert _snapshot(fake_home) == before


@pytest.mark.unit
def test_copy_connection_missing_source_raises(fake_home: Path, tmp_path: Path) -> None:
    target = ConnectionStore(tmp_path / "target")
    with pytest.raises(StoreError, match="not found"):
        ConnectionStore(fake_home).copy_connection_to("Z" * 22, target)
    assert not (target.home / "connections").exists()


@pytest.mark.unit
def test_copy_connection_failure_leaves_no_staging_directory(
    fake_home: Path, tmp_path: Path, mocker: MockerFixture
) -> None:
    target = ConnectionStore(tmp_path / "target")
    mocker.patch("sqlcl_conn_mng.store.shutil.copyfile", side_effect=OSError("disk full"))
    with pytest.raises(OSError, match="disk full"):
        ConnectionStore(fake_home).copy_connection_to(ID_DEV, target)
    assert list((target.home / "connections").iterdir()) == []


@pytest.mark.unit
@pytest.mark.skipif(
    sys.platform == "win32", reason="POSIX permission bits are not meaningful on Windows"
)
def test_copy_connection_preserves_file_permissions(fake_home: Path, tmp_path: Path) -> None:
    src = fake_home / "connections" / ID_DEV
    (src / "credentials.sso").chmod(0o600)
    (src / "dbtools.properties").chmod(0o640)
    target = ConnectionStore(tmp_path / "target")
    old_umask = os.umask(0o022)
    try:
        new_id = ConnectionStore(fake_home).copy_connection_to(ID_DEV, target)
    finally:
        os.umask(old_umask)
    dst = target.home / "connections" / new_id
    assert stat.S_IMODE((dst / "credentials.sso").stat().st_mode) == 0o600
    assert stat.S_IMODE((dst / "dbtools.properties").stat().st_mode) == 0o640


@pytest.mark.unit
def test_copy_connection_copymode_failure_leaves_no_directory(
    fake_home: Path, tmp_path: Path, mocker: MockerFixture
) -> None:
    target = ConnectionStore(tmp_path / "target")
    mocker.patch("sqlcl_conn_mng.store.shutil.copymode", side_effect=OSError("mode denied"))
    with pytest.raises(OSError, match="mode denied"):
        ConnectionStore(fake_home).copy_connection_to(ID_DEV, target)
    assert list((target.home / "connections").iterdir()) == []


@pytest.mark.unit
def test_leftover_staging_directory_is_not_a_connection(fake_home: Path, tmp_path: Path) -> None:
    target = ConnectionStore(tmp_path / "target")
    staging = target.home / "connections" / ".copy.abc"
    staging.mkdir(parents=True)
    (staging / "dbtools.properties").write_text("name=half\n", encoding="utf-8")
    assert target.connections() == []


@pytest.mark.unit
def test_remove_connection_dir_removes_only_that_directory(fake_home: Path) -> None:
    ConnectionStore(fake_home).remove_connection_dir(ID_DEV)
    assert not (fake_home / "connections" / ID_DEV).exists()
    assert (fake_home / "connections" / ID_ROOT).is_dir()


@pytest.mark.unit
@pytest.mark.parametrize("bad", ["..", "../store", "short", "", "x" * 23])
def test_remove_connection_dir_refuses_a_non_id(fake_home: Path, bad: str) -> None:
    with pytest.raises(StoreError, match="Not a connection id"):
        ConnectionStore(fake_home).remove_connection_dir(bad)
    assert (fake_home / "connections").is_dir()
