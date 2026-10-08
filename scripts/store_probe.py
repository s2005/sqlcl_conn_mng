"""Snapshot and diff a SQLcl connection store to observe what SQLcl writes.

Usage (named options only)::

    python scripts/store_probe.py --command snapshot --home STORE --output SNAP.json
    python scripts/store_probe.py --command diff --before A.json --after B.json

Safety property: no byte of a ``credentials.sso`` file or of any file that is not a
``*.properties`` or ``folders.json`` file, and no value of a properties key whose name
contains ``password`` or ``pwd`` (case-insensitive), ever reaches stdout, stderr or the
snapshot file. Such files are recorded by relative path, size and a 12-digit SHA-256
prefix only; such values are recorded as size and hash prefix only.

This script is for scratch stores only. Never point it at ``<home>/.sqlcl`` (the real
saved connections) or at ``<repo-root>/.sqlcl``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

JsonDict = dict[str, Any]

_SRC_DIR = Path(__file__).resolve().parent.parent / "src"
_HASH_LEN = 12
_CHUNK = 1024 * 1024
_SECRET_MARKERS = ("password", "pwd")
_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_WHITESPACE = " \t\f"
_EXIT_OK = 0
_EXIT_ERROR = 1


def _load_parser() -> Callable[[str], dict[str, str]]:
    """Import parse_properties from the repository source tree."""
    if str(_SRC_DIR) not in sys.path:
        sys.path.insert(0, str(_SRC_DIR))
    module = importlib.import_module("sqlcl_conn_mng.properties")
    parser: Callable[[str], dict[str, str]] = module.parse_properties
    return parser


def _sha12(data: bytes) -> str:
    """Return the first 12 hex digits of the SHA-256 of data."""
    return hashlib.sha256(data).hexdigest()[:_HASH_LEN]


def _hash_file(path: Path) -> tuple[int, str]:
    """Return the size and hash prefix of a file without keeping its content."""
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()[:_HASH_LEN]


def _line_ending(raw: bytes) -> str:
    """Classify the line endings of a text file."""
    crlf = raw.count(b"\r\n")
    cr = raw.count(b"\r") - crlf
    lf = raw.count(b"\n") - crlf
    kinds = [name for name, count in (("CRLF", crlf), ("CR", cr), ("LF", lf)) if count]
    if not kinds:
        return "none"
    return kinds[0] if len(kinds) == 1 else "mixed"


def _trailing_newline(raw: bytes) -> bool:
    """Return True when the file ends with a line break."""
    return raw.endswith((b"\n", b"\r"))


def _is_secret_key(key: str) -> bool:
    """Return True when a properties key name marks a secret value."""
    lowered = key.lower()
    return any(marker in lowered for marker in _SECRET_MARKERS)


def _redact(value: str) -> JsonDict:
    """Describe a secret value by size and hash prefix only."""
    encoded = value.encode("utf-8", "replace")
    return {"redacted": True, "size": len(encoded), "sha12": _sha12(encoded)}


def _scan_lines(text: str) -> tuple[list[str], list[str]]:
    """Return logical lines and comment lines using the parser's line semantics."""
    logical: list[str] = []
    comments: list[str] = []
    pending: str | None = None
    for raw in _LINE_BREAK.split(text):
        line = raw.lstrip(_WHITESPACE)
        if pending is None and (not line or line[0] in "#!"):
            if line:
                comments.append(line)
            continue
        trailing = len(line) - len(line.rstrip("\\"))
        if trailing % 2 == 1:
            pending = (pending or "") + line[:-1]
            continue
        logical.append((pending or "") + line)
        pending = None
    if pending is not None:
        logical.append(pending)
    return logical, comments


def _properties_entry(raw: bytes, parse: Callable[[str], dict[str, str]]) -> JsonDict:
    """Build the snapshot facts for a properties file."""
    try:
        text = raw.decode("utf-8")
        utf8_ok = True
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
        utf8_ok = False
    logical, comments = _scan_lines(text)
    key_order: list[str] = []
    for line in logical:
        for key in parse(line):
            if key not in key_order:
                key_order.append(key)
    props: JsonDict = {}
    for key, value in parse(text).items():
        props[key] = _redact(value) if _is_secret_key(key) else value
    return {
        "properties": props,
        "line_ending": _line_ending(raw),
        "trailing_newline": _trailing_newline(raw),
        "encoding_ok_utf8": utf8_ok,
        "key_order": key_order,
        "comment_lines": comments,
    }


def _detect_indent(text: str) -> str:
    """Describe the indentation of the first indented line."""
    for line in _LINE_BREAK.split(text):
        if line[:1] == "\t":
            return "tab"
        stripped = line.lstrip(" ")
        if stripped and len(stripped) != len(line):
            return f"{len(line) - len(stripped)} spaces"
    return "none"


def _folders_entry(raw: bytes) -> JsonDict:
    """Build the snapshot facts for a folders.json file."""
    entry: JsonDict = {
        "line_ending": _line_ending(raw),
        "trailing_newline": _trailing_newline(raw),
    }
    try:
        text = raw.decode("utf-8")
        entry["json"] = json.loads(text)
        entry["indent"] = _detect_indent(text)
    except ValueError:
        entry["json"] = None
        entry["json_error"] = True
        entry["indent"] = "none"
    return entry


def _file_entry(path: Path, parse: Callable[[str], dict[str, str]]) -> JsonDict:
    """Build the snapshot entry for one file."""
    size, sha = _hash_file(path)
    entry: JsonDict = {"size": size, "sha12": sha}
    if path.name == "folders.json":
        entry.update(_folders_entry(path.read_bytes()))
    elif path.suffix == ".properties":
        entry.update(_properties_entry(path.read_bytes(), parse))
    return entry


def take_snapshot(home: Path) -> JsonDict:
    """Walk the store root and return a snapshot dictionary."""
    parse = _load_parser()
    files: JsonDict = {}
    paths = sorted(p for p in home.rglob("*") if p.is_file())
    for path in paths:
        files[path.relative_to(home).as_posix()] = _file_entry(path, parse)
    return {"home": str(home.resolve()), "files": files}


def _cmd_snapshot(home: Path, output: Path) -> int:
    """Run the snapshot command."""
    if not home.is_dir():
        print("error: --home is not an existing directory", file=sys.stderr)
        return _EXIT_ERROR
    snapshot = take_snapshot(home)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=True)
    output.write_text(text + "\n", encoding="utf-8")
    print(f"snapshot: {len(snapshot['files'])} files -> {_show(str(output))}")
    return _EXIT_OK


def _show(value: object) -> str:
    """Render a value as ASCII-safe text for the console."""
    return str(value).encode("ascii", "backslashreplace").decode("ascii")


def _fmt_value(value: object) -> str:
    """Format a property value, hiding redacted entries."""
    if isinstance(value, dict) and value.get("redacted"):
        return f"<redacted size={value['size']} sha12={value['sha12']}>"
    return _show(value)


def _diff_properties(before: JsonDict, after: JsonDict) -> None:
    """Print key-level differences between two properties entries."""
    old: JsonDict = before.get("properties", {})
    new: JsonDict = after.get("properties", {})
    for key in sorted(new.keys() - old.keys()):
        print(f"  key added {_show(key)} = {_fmt_value(new[key])}")
    for key in sorted(old.keys() - new.keys()):
        print(f"  key removed {_show(key)}")
    for key in sorted(old.keys() & new.keys()):
        if old[key] != new[key]:
            print(f"  key changed {_show(key)}: {_fmt_value(old[key])} -> {_fmt_value(new[key])}")
    old_common = [k for k in before.get("key_order", []) if k in new]
    new_common = [k for k in after.get("key_order", []) if k in old]
    if old_common != new_common:
        print("  key order changed")
    _diff_text_facts(before, after)
    old_comments: list[str] = before.get("comment_lines", [])
    new_comments: list[str] = after.get("comment_lines", [])
    if old_comments != new_comments:
        for line in new_comments:
            if line not in old_comments:
                print(f"  comment added {_show(line)}")
        for line in old_comments:
            if line not in new_comments:
                print(f"  comment removed {_show(line)}")
        if sorted(old_comments) == sorted(new_comments):
            print("  comment order changed")


def _diff_text_facts(before: JsonDict, after: JsonDict) -> None:
    """Print line-ending and trailing-newline changes."""
    for name in ("line_ending", "trailing_newline", "encoding_ok_utf8", "indent"):
        if name in before and name in after and before[name] != after[name]:
            print(f"  {name} changed {_show(before[name])} -> {_show(after[name])}")


def _print_added_properties(entry: JsonDict) -> None:
    """Print the keys of a newly added properties file."""
    props: JsonDict = entry.get("properties", {})
    for key in entry.get("key_order", sorted(props)):
        if key in props:
            print(f"  key {_show(key)} = {_fmt_value(props[key])}")
    for line in entry.get("comment_lines", []):
        print(f"  comment {_show(line)}")


def _flatten(data: object) -> dict[str, list[str]]:
    """Flatten a folders.json document into folder path -> connection ids."""
    result: dict[str, list[str]] = {}
    if not isinstance(data, dict):
        return result
    top = data.get("connections")
    if isinstance(top, list):
        result["/"] = [str(item) for item in top]

    def walk(folders: object, parent: str) -> None:
        if not isinstance(folders, list):
            return
        for folder in folders:
            if not isinstance(folder, dict):
                continue
            path = f"{parent}/{folder.get('name', '')}"
            conns = folder.get("connections")
            result[path] = [str(c) for c in conns] if isinstance(conns, list) else []
            walk(folder.get("folders"), path)

    walk(data.get("folders"), "")
    return result


def _locations(flat: dict[str, list[str]]) -> dict[str, set[str]]:
    """Map each connection id to the set of folders that list it."""
    where: dict[str, set[str]] = {}
    for path, ids in flat.items():
        for conn_id in ids:
            where.setdefault(conn_id, set()).add(path)
    return where


def _diff_folders(before: JsonDict, after: JsonDict) -> None:
    """Print a structural diff of two folders.json entries."""
    old_json = before.get("json")
    new_json = after.get("json")
    old_keys = set(old_json) if isinstance(old_json, dict) else set()
    new_keys = set(new_json) if isinstance(new_json, dict) else set()
    for key in sorted(new_keys - old_keys):
        print(f"  top-level key added {_show(key)}")
    for key in sorted(old_keys - new_keys):
        print(f"  top-level key removed {_show(key)}")
    old_flat = _flatten(old_json)
    new_flat = _flatten(new_json)
    for path in sorted(new_flat.keys() - old_flat.keys()):
        print(f"  folder added {_show(path)}")
    for path in sorted(old_flat.keys() - new_flat.keys()):
        print(f"  folder removed {_show(path)}")
    old_where = _locations(old_flat)
    new_where = _locations(new_flat)
    for conn_id in sorted(old_where.keys() | new_where.keys()):
        was = old_where.get(conn_id, set())
        now = new_where.get(conn_id, set())
        if was == now:
            continue
        if len(was) == 1 and len(now) == 1:
            print(
                f"  connection {conn_id} moved {_show(next(iter(was)))} -> {_show(next(iter(now)))}"
            )
            continue
        for path in sorted(now - was):
            print(f"  connection {conn_id} added to {_show(path)}")
        for path in sorted(was - now):
            print(f"  connection {conn_id} removed from {_show(path)}")
    for path in sorted(old_flat.keys() & new_flat.keys()):
        old_ids, new_ids = old_flat[path], new_flat[path]
        if old_ids != new_ids and sorted(old_ids) == sorted(new_ids):
            print(f"  order changed in {_show(path)}")
    _diff_text_facts(before, after)


def _diff_entry(name: str, before: JsonDict, after: JsonDict) -> None:
    """Print the details of one changed file."""
    if name.endswith(".properties"):
        _diff_properties(before, after)
    elif name.endswith("folders.json"):
        _diff_folders(before, after)


def _differs(old: JsonDict, new: JsonDict) -> bool:
    """Return True when two file entries differ in size or hash."""
    return bool(old["sha12"] != new["sha12"] or old["size"] != new["size"])


def diff_snapshots(before: JsonDict, after: JsonDict) -> None:
    """Print the differences between two snapshots."""
    old_files: JsonDict = before.get("files", {})
    new_files: JsonDict = after.get("files", {})
    unchanged = 0
    for name in sorted(old_files.keys() | new_files.keys()):
        old: JsonDict | None = old_files.get(name)
        new: JsonDict | None = new_files.get(name)
        if old is None and new is not None:
            print(f"added {_show(name)} (size {new['size']})")
            if name.endswith(".properties"):
                _print_added_properties(new)
            elif name.endswith("folders.json"):
                _diff_folders({}, new)
        elif old is not None and new is None:
            print(f"removed {_show(name)}")
        elif old is not None and new is not None and _differs(old, new):
            print(
                f"changed {_show(name)} size {old['size']} -> {new['size']} "
                f"sha12 {old['sha12']} -> {new['sha12']}"
            )
            _diff_entry(name, old, new)
        else:
            unchanged += 1
    print(f"unchanged {unchanged}")


def _load_snapshot(path: Path) -> JsonDict:
    """Load a snapshot file."""
    loaded: JsonDict = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _cmd_diff(before: Path, after: Path) -> int:
    """Run the diff command."""
    try:
        old = _load_snapshot(before)
        new = _load_snapshot(after)
    except (OSError, ValueError) as exc:
        print(f"error: cannot load snapshot ({type(exc).__name__})", file=sys.stderr)
        return _EXIT_ERROR
    diff_snapshots(old, new)
    return _EXIT_OK


def _build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(description="Snapshot and diff a SQLcl connection store.")
    parser.add_argument("--command", required=True, choices=["snapshot", "diff"])
    parser.add_argument("--home", type=Path, help="store root (snapshot)")
    parser.add_argument("--output", type=Path, help="snapshot file to write (snapshot)")
    parser.add_argument("--before", type=Path, help="earlier snapshot file (diff)")
    parser.add_argument("--after", type=Path, help="later snapshot file (diff)")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "snapshot":
        if args.home is None or args.output is None:
            parser.error("--command snapshot requires --home and --output")
        return _cmd_snapshot(args.home, args.output)
    if args.before is None or args.after is None:
        parser.error("--command diff requires --before and --after")
    return _cmd_diff(args.before, args.after)


if __name__ == "__main__":
    sys.exit(main())
