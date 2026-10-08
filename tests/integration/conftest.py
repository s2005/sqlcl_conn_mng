"""Fixtures for the integration tests; every test skips when SQLcl is absent."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from tests.integration import harness
from tests.integration.harness import BuiltStore, CliResult, DbSettings, Step


@pytest.fixture(scope="session")
def sqlcl_path() -> str:
    """Locate the SQLcl executable or skip."""
    found = shutil.which(os.environ.get(harness.SQLCL_ENV_VAR) or "sql")
    if found is None:
        pytest.skip("SQLcl not found: set SQLCL_BIN to sql.exe or put sql on PATH")
    return found


@pytest.fixture(scope="session")
def sqlcl_release(sqlcl_path: str) -> str:
    """Return the SQLcl release string."""
    return harness.read_release(sqlcl_path)


@pytest.fixture(autouse=True)
def _require_sqlcl(sqlcl_path: str) -> None:
    """Skip every test in the package when SQLcl is missing."""


@pytest.fixture(scope="session")
def build_store(
    sqlcl_path: str, tmp_path_factory: pytest.TempPathFactory
) -> Callable[..., BuiltStore]:
    """Return a callable that builds a store with real SQLcl."""

    def _build(
        name: str,
        stages: Sequence[Sequence[Step]],
        secret: str | None = None,
    ) -> BuiltStore:
        home = tmp_path_factory.mktemp(name)
        return harness.build_stages(sqlcl_path, home, name, stages, secret)

    return _build


@pytest.fixture(scope="session")
def run_cli(sqlcl_path: str) -> Callable[..., CliResult]:
    """Return a callable that runs the CLI against a store."""

    def _run(store: Path, *args: str) -> CliResult:
        return harness.run_cli(store, sqlcl_path, *args)

    return _run


@pytest.fixture(scope="session")
def db_settings() -> DbSettings:
    """Return database settings from the environment or skip."""
    result = harness.db_settings_from_env(os.environ)
    if isinstance(result, list):
        pytest.skip(f"database scenarios need {', '.join(result)}")
    return result
