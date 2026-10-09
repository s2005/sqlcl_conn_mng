"""Parser and writer for Java .properties files as written by java.util.Properties."""

from __future__ import annotations

import re

_LINE_BREAK = re.compile(r"\r\n|\r|\n")
_WHITESPACE = " \t\f"
_SEPARATORS = "=:"
_SIMPLE_ESCAPES = {"t": "\t", "n": "\n", "r": "\r", "f": "\f"}
_HEX_DIGITS = 4
_HEX_PATTERN = re.compile(r"[0-9a-fA-F]{4}")
_WRITE_ESCAPES = {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r", "\f": "\\f"}
_SPECIAL_CHARS = "=:#!"
_FIRST_PRINTABLE = 0x20


def _logical_lines(text: str) -> list[str]:
    """Join continuation lines and drop comments and blank lines."""
    result: list[str] = []
    pending: str | None = None
    for raw in _LINE_BREAK.split(text):
        line = raw.lstrip(_WHITESPACE)
        if pending is None and (not line or line[0] in "#!"):
            continue
        trailing = len(line) - len(line.rstrip("\\"))
        if trailing % 2 == 1:
            pending = (pending or "") + line[:-1]
            continue
        result.append((pending or "") + line)
        pending = None
    if pending is not None:
        result.append(pending)
    return result


def _unescape(raw: str) -> str:
    """Resolve backslash escapes in a key or value."""
    out: list[str] = []
    i = 0
    while i < len(raw):
        char = raw[i]
        if char != "\\":
            out.append(char)
            i += 1
            continue
        i += 1
        if i >= len(raw):
            break
        nxt = raw[i]
        if nxt == "u":
            digits = raw[i + 1 : i + 1 + _HEX_DIGITS]
            if not _HEX_PATTERN.fullmatch(digits):
                raise ValueError(f"Malformed unicode escape in properties text: \\u{digits}")
            out.append(chr(int(digits, 16)))
            i += 1 + _HEX_DIGITS
            continue
        out.append(_SIMPLE_ESCAPES.get(nxt, nxt))
        i += 1
    joined = "".join(out)
    try:
        return joined.encode("utf-16", "surrogatepass").decode("utf-16")
    except UnicodeError:
        return joined


def _split_key_value(line: str) -> tuple[str, str]:
    """Split one logical line into an unescaped key and value."""
    i = 0
    while i < len(line):
        char = line[i]
        if char == "\\":
            i += 2
            continue
        if char in _SEPARATORS or char in _WHITESPACE:
            break
        i += 1
    key_raw = line[:i]
    while i < len(line) and line[i] in _WHITESPACE:
        i += 1
    if i < len(line) and line[i] in _SEPARATORS:
        i += 1
    while i < len(line) and line[i] in _WHITESPACE:
        i += 1
    return _unescape(key_raw), _unescape(line[i:])


def parse_properties(text: str) -> dict[str, str]:
    """Parse Java properties text into a dict; later duplicates win."""
    result: dict[str, str] = {}
    for line in _logical_lines(text):
        key, value = _split_key_value(line)
        result[key] = value
    return result


def _escape(text: str, is_key: bool) -> str:
    """Escape one key or value the way java.util.Properties.store does."""
    out: list[str] = []
    for index, char in enumerate(text):
        if char in _WRITE_ESCAPES:
            out.append(_WRITE_ESCAPES[char])
        elif char == " " and (is_key or index == 0):
            out.append("\\ ")
        elif char in _SPECIAL_CHARS:
            out.append("\\" + char)
        elif ord(char) < _FIRST_PRINTABLE:
            out.append(f"\\u{ord(char):04x}")
        else:
            out.append(char)
    return "".join(out)


def format_properties(props: dict[str, str]) -> str:
    """Render a dict as Java properties text: key=value lines, LF endings, final LF, no header."""
    return "".join(
        f"{_escape(key, True)}={_escape(value, False)}\n" for key, value in props.items()
    )
