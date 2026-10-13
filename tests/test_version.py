"""Tests for the package version fallback."""

from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Iterator

import pytest

import sqlcl_conn_mng


@pytest.fixture
def restore_package() -> Iterator[None]:
    """Reload the package after the test so later tests see the real version."""
    yield
    importlib.reload(sqlcl_conn_mng)


@pytest.mark.unit
def test_version_falls_back_when_not_installed(
    monkeypatch: pytest.MonkeyPatch, restore_package: None
) -> None:
    def missing(distribution_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError(distribution_name)

    monkeypatch.setattr(importlib.metadata, "version", missing)
    importlib.reload(sqlcl_conn_mng)
    assert sqlcl_conn_mng.__version__ == "0.0.0.dev0"
