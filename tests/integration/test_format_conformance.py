"""Format conformance: what SQLcl writes into a store matches findings.md."""

from __future__ import annotations

import base64
import binascii
import json
import re
from typing import Any

import pytest

from tests.integration.harness import (
    EDGE_NAMES,
    SPECIAL_USER,
    BuiltStore,
    DbSettings,
    assert_format,
    conn_dirs,
    conn_files,
    file_changes,
    ids_by_name,
    raw_folder_ids,
    raw_folders,
)

pytestmark = pytest.mark.integration

FOLDERS_KEY = "connection_folders/folders.json"
DB_FREE_STORES = (
    "folder_store",
    "folder_delete_store",
    "import_store",
    "conn_ops_store",
    "edge_store",
)
ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{22}")
FOLDER_KEYS = ["name", "connections", "folders"]
IMPORT_ORDER = ["name", "type", "host", "port", "serviceName", "userName"]
REREAD_IMPORT_ORDER = ["port", "name", "host", "type", "serviceName", "userName"]
SAVE_ORDER = ["name", "type", "connectionString", "userName"]
REREAD_SAVE_ORDER = ["connectionString", "name", "type", "userName"]
SPECIAL_USER_LINE = "userName=u\\:s\\=e\\#r\\!\\\\x y"

Snap = dict[str, Any]


def escape(value: str) -> str:
    """Escape a value the way java.util.Properties.store does, for the characters used here."""
    out: list[str] = []
    for index, char in enumerate(value):
        if char == "\\" or char in ":=#!":
            out.append("\\" + char)
        elif char == " " and index == 0:
            out.append("\\ ")
        else:
            out.append(char)
    return "".join(out)


def raw_lines(store: BuiltStore, key: str) -> list[str]:
    """Return the lines of a store file read from disk."""
    return (store.home / key).read_bytes().decode("utf-8").split("\n")


def prop_keys(snap: Snap) -> list[str]:
    """Return the properties file keys of a snapshot."""
    return [k for k in snap["files"] if k.endswith(".properties")]


def conn_prop_keys(snap: Snap) -> list[str]:
    """Return the dbtools.properties file keys of a snapshot."""
    return [k for k in prop_keys(snap) if k.endswith("/dbtools.properties")]


def key_order(snap: Snap, name: str) -> list[list[str]]:
    """Return the key order of every dbtools.properties file holding the connection name."""
    ids = ids_by_name(snap).get(name, [])
    assert ids, f"connection {name} not found"
    return [snap["files"][f"connections/{i}/dbtools.properties"]["key_order"] for i in ids]


def expect_only(
    release: str,
    what: str,
    pair: tuple[Snap, Snap],
    created: set[str],
    changed: set[str],
    deleted: set[str],
) -> None:
    """Check that the snapshot pair differs by exactly the given file sets."""
    got = file_changes(*pair)
    assert_format(got[0] == created, f"{what}: created files {sorted(got[0])}", release)
    assert_format(got[1] == changed, f"{what}: changed files {sorted(got[1])}", release)
    assert_format(got[2] == deleted, f"{what}: deleted files {sorted(got[2])}", release)


def one_id(snap: Snap, name: str, release: str) -> str:
    """Return the id of the single connection with the name."""
    ids = ids_by_name(snap).get(name, [])
    assert_format(len(ids) == 1, f"{name} is not exactly one connection", release)
    return ids[0]


def check_ids(store: BuiltStore, release: str) -> None:
    """Check the connection id rule for every directory of the final snapshot."""
    for name in sorted(conn_dirs(store.snapshots[-1])):
        ok = ID_PATTERN.fullmatch(name) is not None
        assert_format(ok, f"id {name!r} is not 22 URL-safe characters", release)
        try:
            raw = base64.urlsafe_b64decode(name + "==")
        except (binascii.Error, ValueError):
            raw = b""
        assert_format(len(raw) == 16, f"id {name!r} does not decode to 16 bytes", release)
        again = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
        assert_format(again == name, f"id {name!r} is not canonical Base64", release)


@pytest.mark.parametrize("fixture_name", DB_FREE_STORES)
def test_id_rule(request: pytest.FixtureRequest, sqlcl_release: str, fixture_name: str) -> None:
    check_ids(request.getfixturevalue(fixture_name), sqlcl_release)


def test_id_rule_saved_store(saved_pw_store: BuiltStore, sqlcl_release: str) -> None:
    check_ids(saved_pw_store, sqlcl_release)


def test_files_import(folder_store: BuiltStore, sqlcl_release: str) -> None:
    before, after = folder_store.snapshots[0], folder_store.snapshots[1]
    dirs = conn_dirs(after)
    expected = {f for d in dirs for f in conn_files(d)}
    assert_format(len(dirs) == 3, f"import created {len(dirs)} directories", sqlcl_release)
    expect_only(sqlcl_release, "import", (before, after), expected, set(), set())
    assert_format(FOLDERS_KEY not in after["files"], "import wrote folders.json", sqlcl_release)


def test_files_add_folder(folder_store: BuiltStore, sqlcl_release: str) -> None:
    pair = (folder_store.snapshots[1], folder_store.snapshots[2])
    expect_only(sqlcl_release, "add -folder", pair, {FOLDERS_KEY}, set(), set())


def test_files_move_conn(conn_ops_store: BuiltStore, sqlcl_release: str) -> None:
    pair = (conn_ops_store.snapshots[1], conn_ops_store.snapshots[2])
    expect_only(sqlcl_release, "move -conn", pair, set(), {FOLDERS_KEY}, set())


def test_files_clone(conn_ops_store: BuiltStore, sqlcl_release: str) -> None:
    before, after = conn_ops_store.snapshots[2], conn_ops_store.snapshots[3]
    new_dirs = conn_dirs(after) - conn_dirs(before)
    assert_format(len(new_dirs) == 1, f"clone created {len(new_dirs)} directories", sqlcl_release)
    expected = {f for d in new_dirs for f in conn_files(d)}
    expect_only(sqlcl_release, "clone", (before, after), expected, set(), set())


def test_files_rename_conn(conn_ops_store: BuiltStore, sqlcl_release: str) -> None:
    before, after = conn_ops_store.snapshots[3], conn_ops_store.snapshots[4]
    conn_id = one_id(after, "c_renamed", sqlcl_release)
    changed = {f"connections/{conn_id}/dbtools.properties"}
    expect_only(sqlcl_release, "rename -conn", (before, after), set(), changed, set())


def test_files_delete_conn(conn_ops_store: BuiltStore, sqlcl_release: str) -> None:
    before, after = conn_ops_store.snapshots[4], conn_ops_store.snapshots[5]
    conn_id = one_id(before, "c_doomed", sqlcl_release)
    deleted = conn_files(conn_id)
    expect_only(sqlcl_release, "delete -conn", (before, after), set(), set(), deleted)


def test_files_delete_folder_force(folder_delete_store: BuiltStore, sqlcl_release: str) -> None:
    before, after = folder_delete_store.snapshots[2], folder_delete_store.snapshots[3]
    deleted = conn_files(one_id(before, "imp1", sqlcl_release))
    pair = (before, after)
    expect_only(sqlcl_release, "delete -folder -force", pair, set(), {FOLDERS_KEY}, deleted)


def test_files_connect_save(saved_pw_store: BuiltStore, sqlcl_release: str) -> None:
    before, after = saved_pw_store.snapshots[0], saved_pw_store.snapshots[1]
    dirs = conn_dirs(after)
    expected = {f for d in dirs for f in conn_files(d)}
    assert_format(len(dirs) == 4, f"connect -save created {len(dirs)} directories", sqlcl_release)
    expect_only(sqlcl_release, "connect -save", (before, after), expected, set(), set())
    wrote = FOLDERS_KEY in after["files"]
    assert_format(not wrote, "connect -save wrote folders.json", sqlcl_release)


@pytest.mark.parametrize("stage", [2, 3])
def test_files_connect_save_replace(
    saved_pw_store: BuiltStore, sqlcl_release: str, stage: int
) -> None:
    before, after = saved_pw_store.snapshots[stage - 1], saved_pw_store.snapshots[stage]
    conn_id = one_id(after, "p_replace", sqlcl_release)
    changed = {f"connections/{conn_id}/credentials.sso"}
    expect_only(sqlcl_release, "connect -save -replace", (before, after), set(), changed, set())


@pytest.mark.parametrize("fixture_name", DB_FREE_STORES)
def test_properties_facts(
    request: pytest.FixtureRequest, sqlcl_release: str, fixture_name: str
) -> None:
    store: BuiltStore = request.getfixturevalue(fixture_name)
    snap = store.snapshots[-1]
    assert_format(bool(prop_keys(snap)), "store holds no properties file", sqlcl_release)
    for key in prop_keys(snap):
        entry = snap["files"][key]
        assert_format(not entry["comment_lines"], f"{key} has comment lines", sqlcl_release)
        assert_format(entry["line_ending"] == "LF", f"{key} line ending", sqlcl_release)
        assert_format(entry["trailing_newline"] is True, f"{key} trailing newline", sqlcl_release)
        assert_format(entry["encoding_ok_utf8"] is True, f"{key} UTF-8 encoding", sqlcl_release)
    for key in conn_prop_keys(snap):
        lines = [x for x in raw_lines(store, key) if x]
        shaped = all(re.match(r"[A-Za-z]+=", x) for x in lines)
        assert_format(shaped, f"{key} line shape key=value", sqlcl_release)
        escaped = any("\\u" in x for x in lines)
        assert_format(not escaped, f"{key} has unicode escapes", sqlcl_release)


def raw_prefixed(store: BuiltStore, prefix: str) -> list[str]:
    """Return every raw line starting with the prefix across the dbtools.properties files."""
    found: list[str] = []
    for key in conn_prop_keys(store.snapshots[-1]):
        found.extend(x for x in raw_lines(store, key) if x.startswith(prefix))
    return found


@pytest.mark.parametrize("value", EDGE_NAMES)
def test_edge_name_line(edge_store: BuiltStore, sqlcl_release: str, value: str) -> None:
    ok = "name=" + escape(value) in raw_prefixed(edge_store, "name=")
    assert_format(ok, f"name line for {value!r}", sqlcl_release)


def test_edge_special_user_line(edge_store: BuiltStore, sqlcl_release: str) -> None:
    assert escape(SPECIAL_USER) == SPECIAL_USER_LINE.removeprefix("userName=")
    ok = SPECIAL_USER_LINE in raw_prefixed(edge_store, "userName=")
    assert_format(ok, "special user line", sqlcl_release)


@pytest.mark.parametrize("value", ["caf\u00e91", "\u00fcber1"])
def test_edge_raw_utf8(edge_store: BuiltStore, sqlcl_release: str, value: str) -> None:
    needle = b"name=" + value.encode("utf-8") + b"\n"
    found = any(
        needle in (edge_store.home / key).read_bytes()
        for key in conn_prop_keys(edge_store.snapshots[-1])
    )
    assert_format(found, f"raw UTF-8 bytes of {value!r}", sqlcl_release)


def check_order(snap: Snap, names: list[str], order: list[str], release: str) -> None:
    """Check the key order of the files holding each connection name."""
    for name in names:
        for got in key_order(snap, name):
            assert_format(got == order, f"key order of {name}: {got}", release)


def test_key_order_import(import_store: BuiltStore, sqlcl_release: str) -> None:
    check_order(import_store.snapshots[2], ["imp1", "imp1_1"], IMPORT_ORDER, sqlcl_release)


def test_key_order_reread(conn_ops_store: BuiltStore, sqlcl_release: str) -> None:
    names = ["c_renamed", "c_user", "c_nopwd", "c_from_folder"]
    check_order(conn_ops_store.snapshots[-1], names, REREAD_IMPORT_ORDER, sqlcl_release)


def test_key_order_connect_save(saved_pw_store: BuiltStore, sqlcl_release: str) -> None:
    names = ["p_saved", "p_nopwd", "p_desc"]
    check_order(saved_pw_store.snapshots[1], names, SAVE_ORDER, sqlcl_release)


def test_key_order_clone_saved(saved_pw_store: BuiltStore, sqlcl_release: str) -> None:
    names = ["p_clone", "p_clone_user", "p_clone_nopwd"]
    check_order(saved_pw_store.snapshots[-1], names, REREAD_SAVE_ORDER, sqlcl_release)


def test_saved_connection_string_lines(
    saved_pw_store: BuiltStore, sqlcl_release: str, db_settings: DbSettings
) -> None:
    lines = raw_prefixed(saved_pw_store, "connectionString=")
    plain = "connectionString=" + escape(db_settings.connect)
    assert_format(plain in lines, "escaped connectionString of p_saved", sqlcl_release)
    desc_id = one_id(saved_pw_store.snapshots[1], "p_desc", sqlcl_release)
    desc_lines = raw_lines(saved_pw_store, f"connections/{desc_id}/dbtools.properties")
    desc = [x for x in desc_lines if x.startswith("connectionString=")]
    assert_format(len(desc) == 1, "p_desc connectionString line", sqlcl_release)
    value = desc[0].removeprefix("connectionString=")
    assert_format("=" in value, "descriptor holds equals signs", sqlcl_release)
    assert_format(value.count("\\=") == value.count("="), "descriptor escapes", sqlcl_release)


def folders_text(store: BuiltStore) -> str:
    """Return the raw folders.json text of a store on disk."""
    return (store.home / FOLDERS_KEY).read_bytes().decode("utf-8")


def check_level(nodes: list[dict[str, Any]], release: str) -> None:
    """Check keys and sibling order at every level of a folder tree."""
    for node in nodes:
        assert_format(list(node) == FOLDER_KEYS, f"folder keys {list(node)}", release)
        check_level(node["folders"], release)
    names = [n["name"] for n in nodes]
    ordered = sorted(names, key=lambda n: n.encode("utf-16-be"))
    assert_format(names == ordered, f"sibling order {names}", release)


@pytest.mark.parametrize("fixture_name", ["folder_store", "conn_ops_store", "edge_store"])
def test_folders_json_format(
    request: pytest.FixtureRequest, sqlcl_release: str, fixture_name: str
) -> None:
    store: BuiltStore = request.getfixturevalue(fixture_name)
    text = folders_text(store)
    data = json.loads(text)
    compact = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    assert_format(text == compact, "compact serialisation", sqlcl_release)
    assert_format(not text.endswith("\n"), "final newline", sqlcl_release)
    assert_format(list(data) == ["folders"], f"top-level keys {list(data)}", sqlcl_release)
    check_level(data["folders"], sqlcl_release)


def test_folders_json_edge_order(edge_store: BuiltStore, sqlcl_release: str) -> None:
    text = folders_text(edge_store)
    names = [n["name"] for n in json.loads(text)["folders"]]
    expected = ["DEV", "back\\slash", "dev", "lt<gt>"]
    assert_format(names == expected, f"edge order {names}", sqlcl_release)
    assert_format("lt<gt>" in text, "raw angle brackets", sqlcl_release)
    escaped = "\\u003c" in text or "\\u003e" in text
    assert_format(not escaped, "escaped angle brackets", sqlcl_release)


def test_folders_json_move_append_order(folder_store: BuiltStore, sqlcl_release: str) -> None:
    flat = raw_folder_ids(raw_folders(folder_store.snapshots[3]))
    expected = [
        one_id(folder_store.snapshots[1], "imp2", sqlcl_release),
        one_id(folder_store.snapshots[1], "imp3", sqlcl_release),
    ]
    assert_format(flat["/ops"] == expected, f"/ops list {flat['/ops']}", sqlcl_release)


def test_folders_json_last_folder_deleted(
    folder_delete_store: BuiltStore, sqlcl_release: str
) -> None:
    text = folders_text(folder_delete_store)
    assert_format(text == '{"folders":[]}', f"empty folders file {text!r}", sqlcl_release)


def test_assert_format_self_test(sqlcl_release: str) -> None:
    with pytest.raises(AssertionError) as info:
        assert_format(False, "self-test", sqlcl_release)
    assert sqlcl_release in str(info.value)
    assert "format drift" in str(info.value)
