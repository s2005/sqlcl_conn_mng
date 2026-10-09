"""Tests for the Java properties parser and writer."""

from __future__ import annotations

import pytest

from sqlcl_conn_mng.properties import format_properties, parse_properties


@pytest.mark.unit
def test_basic_pairs_and_comments() -> None:
    text = "# comment\n! other\n\nname=x\ntype : T\nkey value\n"
    assert parse_properties(text) == {"name": "x", "type": "T", "key": "value"}


@pytest.mark.unit
def test_escaped_colon_in_value() -> None:
    assert parse_properties("connectionString=//host\\:1521/svc\n") == {
        "connectionString": "//host:1521/svc"
    }


@pytest.mark.unit
def test_escapes() -> None:
    result = parse_properties("a=1\\t2\\n3\\r4\\f5\\\\6\\=7\n")
    assert result["a"] == "1\t2\n3\r4\f5\\6=7"


@pytest.mark.unit
def test_unicode_escape_and_surrogate_pair() -> None:
    assert parse_properties("a=\\u0041\\u00e9\n")["a"] == "A\u00e9"
    assert parse_properties("a=\\ud83d\\ude00\n")["a"] == "\U0001f600"


@pytest.mark.unit
def test_malformed_unicode_escape() -> None:
    with pytest.raises(ValueError, match="unicode"):
        parse_properties("a=\\u12\n")


@pytest.mark.unit
def test_line_continuation_strips_leading_whitespace() -> None:
    assert parse_properties("a=one \\\n    two\\\n three\n") == {"a": "one twothree"}


@pytest.mark.unit
def test_even_backslashes_do_not_continue() -> None:
    assert parse_properties("a=x\\\\\nb=y\n") == {"a": "x\\", "b": "y"}


@pytest.mark.unit
def test_escaped_separator_in_key_and_whitespace_trimming() -> None:
    result = parse_properties("  my\\:key  =   spaced value  \n")
    assert result == {"my:key": "spaced value  "}


@pytest.mark.unit
def test_empty_value_and_crlf_and_duplicates() -> None:
    result = parse_properties("a=\r\nb=1\r\nb=2\r\n")
    assert result == {"a": "", "b": "2"}


@pytest.mark.unit
def test_comment_marker_inside_value_is_kept() -> None:
    assert parse_properties("a=x # y\n") == {"a": "x # y"}


@pytest.mark.unit
def test_trailing_continuation_at_eof() -> None:
    assert parse_properties("a=abc\\") == {"a": "abc"}


@pytest.mark.unit
@pytest.mark.parametrize(
    "value",
    [
        "plain",
        "back\\slash",
        "a:b=c#d!e",
        " leading space",
        "inner  spaces",
        "tab\tnl\ncr\rff\f",
        "ctl\x01\x1f",
        "caf\\u00e9 \\u00fcber",
        "",
    ],
)
def test_format_round_trip(value: str) -> None:
    props = {"name": value, "k e:y": value, "last": "x"}
    assert parse_properties(format_properties(props)) == props


@pytest.mark.unit
def test_format_layout_and_escapes() -> None:
    text = format_properties({"connectionString": "//h:1521/s", "name": " a\\b"})
    assert text == "connectionString=//h\\:1521/s\nname=\\ a\\\\b\n"
    assert format_properties({}) == ""


@pytest.mark.unit
def test_format_keeps_key_order() -> None:
    text = format_properties({"b": "1", "a": "2", "c": "3"})
    assert text.splitlines() == ["b=1", "a=2", "c=3"]
