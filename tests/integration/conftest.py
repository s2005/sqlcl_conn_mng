"""Fixtures for the integration tests; every test skips when SQLcl is absent."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from tests.integration import harness
from tests.integration.harness import (
    EDGE_FOLDERS,
    EDGE_NAMES,
    IMPORT_FIXTURE,
    IMPORT_NAMES,
    SPECIAL_USER,
    BuiltStore,
    CliResult,
    DbSettings,
    Step,
    import_step,
)


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
        # Keep this frame out of tracebacks: pytest would print its arguments (the secret).
        __tracebackhide__ = True
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


@pytest.fixture(scope="session")
def folder_store(build_store: Callable[..., BuiltStore]) -> BuiltStore:
    """Build a store through folder add, move and rename; snapshots hold each stage.

    Stage 1 imports imp1..imp3 at the root. Stage 2 adds /team/a/b. Stage 3 adds
    /ops and /empty and moves imp1 to /team/a/b, imp2 and imp3 to /ops. Stage 4
    moves imp3 back to /, renames /ops to ops2 and moves /team/a/b under /empty.
    Final tree: /empty/b holds imp1, /ops2 holds imp2, /team/a is empty, imp3 is
    at the root.
    """
    stages: list[list[Step]] = [
        [import_step()],
        [("connmgr add -folder /team/a/b", "Folder /team/a/b has been added")],
        [
            ("connmgr add -folder /ops", "Folder /ops has been added"),
            ("connmgr add -folder /empty", "Folder /empty has been added"),
            ("connmgr move -conn imp1 /team/a/b", "Connection imp1 has been moved to /team/a/b"),
            ("connmgr move -conn imp2 /ops", "Connection imp2 has been moved to /ops"),
            ("connmgr move -conn imp3 /ops", "Connection imp3 has been moved to /ops"),
        ],
        [
            ("connmgr move -conn imp3 /", "Connection imp3 has been moved to /"),
            ("connmgr rename -folder /ops ops2", "Folder /ops has been renamed"),
            (
                "connmgr move -folder /team/a/b /empty",
                "Folder /team/a/b has been moved to /empty",
            ),
        ],
    ]
    return build_store("folders", stages)


@pytest.fixture(scope="session")
def folder_delete_store(build_store: Callable[..., BuiltStore]) -> BuiltStore:
    """Build a store through folder deletes; snapshots hold each stage.

    Stage 1 imports imp1..imp3, adds /keep_empty, /x and /last, and moves imp1
    to /x. Stage 2 deletes the empty /keep_empty. Stage 3 force-deletes /x with
    imp1 in it. Stage 4 deletes /last, leaving no folders.
    """
    stages: list[list[Step]] = [
        [
            import_step(),
            ("connmgr add -folder /keep_empty", "Folder /keep_empty has been added"),
            ("connmgr add -folder /x", "Folder /x has been added"),
            ("connmgr add -folder /last", "Folder /last has been added"),
            ("connmgr move -conn imp1 /x", "Connection imp1 has been moved to /x"),
        ],
        [("connmgr delete -folder /keep_empty", "Folder /keep_empty has been deleted")],
        [("connmgr delete -folder /x -force", "Folder /x has been deleted")],
        [("connmgr delete -folder /last", "Folder /last has been deleted")],
    ]
    return build_store("folder_deletes", stages)


@pytest.fixture(scope="session")
def import_store(build_store: Callable[..., BuiltStore]) -> BuiltStore:
    """Build a store through import and re-imports; snapshots hold each stage.

    Stage 1 imports imp1..imp3. Stage 2 re-imports with -duplicates RENAME
    (adds imp1_1, imp2_1, imp3_1). Stage 3 re-imports with -duplicates REPLACE.
    """
    path = IMPORT_FIXTURE.as_posix()

    def lines(suffix: str) -> tuple[str, ...]:
        return tuple(f"Importing connection {n}{suffix}: Success" for n in IMPORT_NAMES)

    stages: list[list[Step]] = [
        [import_step()],
        [(f'connmgr import -duplicates RENAME "{path}"', lines("_1"))],
        [(f'connmgr import -duplicates REPLACE "{path}"', lines(""))],
    ]
    return build_store("imports", stages)


@pytest.fixture(scope="session")
def conn_ops_store(build_store: Callable[..., BuiltStore]) -> BuiltStore:
    """Build a store through clone, move, rename and delete of connections.

    Stage 1 imports imp1..imp3, adds /f and clones imp1 as c_plain, c_user (user
    other_user), c_nopwd (no password), c1, C1 and c_doomed. Stage 2 moves imp2 to
    /f. Stage 3 clones imp2 as c_from_folder. Stage 4 renames c_plain to c_renamed.
    Stage 5 deletes c_doomed.
    """

    def cloned(name: str) -> str:
        return f"Connection {name} has been cloned"

    stages: list[list[Step]] = [
        [
            import_step(),
            ("connmgr add -folder /f", "Folder /f has been added"),
            ("connmgr clone -original imp1 c_plain", cloned("c_plain")),
            ("connmgr clone -original imp1 -username other_user c_user", cloned("c_user")),
            ("connmgr clone -original imp1 -nopwd c_nopwd", cloned("c_nopwd")),
            ("connmgr clone -original imp1 c1", cloned("c1")),
            ("connmgr clone -original imp1 C1", cloned("C1")),
            ("connmgr clone -original imp1 c_doomed", cloned("c_doomed")),
        ],
        [("connmgr move -conn imp2 /f", "Connection imp2 has been moved to /f")],
        [("connmgr clone -original imp2 c_from_folder", cloned("c_from_folder"))],
        [("connmgr rename -conn c_plain c_renamed", "Connection c_plain has been renamed")],
        [("connmgr delete -conn c_doomed", "Connection c_doomed has been deleted")],
    ]
    return build_store("conn_ops", stages)


@pytest.fixture(scope="session")
def edge_store(build_store: Callable[..., BuiltStore]) -> BuiltStore:
    """Build a store holding clones and folders with unusual names; one stage.

    Stage 1 imports imp1..imp3, clones imp1 under every name in EDGE_NAMES, clones
    imp1 as c_special_user with the user SPECIAL_USER and adds every EDGE_FOLDERS
    folder.
    """
    steps: list[Step] = [import_step()]
    for name in EDGE_NAMES:
        # SQLcl's console encoding differs by platform and it trims the echoed name,
        # so non-ASCII and space-padded names are checked by the generic part only.
        expected = (
            f"Connection {name} has been cloned"
            if name.isascii() and name == name.strip()
            else "has been cloned"
        )
        steps.append((f'connmgr clone -original imp1 "{name}"', expected))
    steps.append(
        (
            f'connmgr clone -original imp1 -username "{SPECIAL_USER}" c_special_user',
            "Connection c_special_user has been cloned",
        )
    )
    for folder in EDGE_FOLDERS:
        steps.append((f'connmgr add -folder "{folder}"', f"Folder {folder} has been added"))
    return build_store("edge_values", [steps])


@pytest.fixture(scope="session")
def saved_pw_store(build_store: Callable[..., BuiltStore], db_settings: DbSettings) -> BuiltStore:
    """Build a store of connections saved against the live database; needs the password.

    Stage 1 saves p_saved (-savepwd), p_nopwd (no -savepwd), p_replace (-savepwd) and
    p_desc (-savepwd, descriptor form of the connect string). Stage 2 re-saves p_replace
    with -replace and no -savepwd. Stage 3 re-saves p_replace with -replace -savepwd.
    Stage 4 clones p_saved as p_clone, as p_clone_user (user other_user) and as
    p_clone_nopwd (no password).
    """
    plain = db_settings.connect
    desc = harness.descriptor(plain)

    def saved(name: str, state: str) -> tuple[str, ...]:
        return (f"Name: {name}", f"Password: {state}")

    def cloned(name: str) -> str:
        return f"Connection {name} has been cloned"

    def save(name: str, connect: str, save_password: bool, replace: bool) -> str:
        return harness.save_command(name, db_settings, connect, save_password, replace)

    stages: list[list[Step]] = [
        [
            (save("p_saved", plain, True, False), saved("p_saved", "******")),
            (save("p_nopwd", plain, False, False), saved("p_nopwd", "not saved")),
            (save("p_replace", plain, True, False), saved("p_replace", "******")),
            (save("p_desc", desc, True, False), saved("p_desc", "******")),
        ],
        [(save("p_replace", plain, False, True), saved("p_replace", "not saved"))],
        [(save("p_replace", plain, True, True), saved("p_replace", "******"))],
        [
            ("connmgr clone -original p_saved p_clone", cloned("p_clone")),
            (
                "connmgr clone -original p_saved -username other_user p_clone_user",
                cloned("p_clone_user"),
            ),
            ("connmgr clone -original p_saved -nopwd p_clone_nopwd", cloned("p_clone_nopwd")),
        ],
    ]
    return build_store("saved_pw", stages, secret=db_settings.password)
