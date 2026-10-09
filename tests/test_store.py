"""Tests for the connection store."""

from __future__ import annotations

from pathlib import Path

import pytest

from sqlcl_conn_mng.store import ConnectionStore, StoreError, resolve_home
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
