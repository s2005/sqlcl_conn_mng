"""Helpers for building real SQLcl connection stores and driving the CLI over them."""

from __future__ import annotations

import contextlib
import functools
import importlib.util
import io
import itertools
import json
import logging
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from sqlcl_conn_mng import cli
from sqlcl_conn_mng.sqlcl import SqlclError, SqlclRunner

SQLCL_ENV_VAR = "SQLCL_BIN"
SQLCL_TIMEOUT = 600
DB_VARS = ("SQLCL_ITEST_CONNECT", "SQLCL_ITEST_USER", "SQLCL_ITEST_PASSWORD")
DATA_DIR = Path(__file__).resolve().parent / "data"
IMPORT_FIXTURE = DATA_DIR / "sqldev_export.json"
IMPORT_NAMES = ("imp1", "imp2", "imp3")
PROBE_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "store_probe.py"

# A SQLcl command and the success line(s) it must print; a tuple means "all of
# these, in any order"; an empty string means nothing is checked.
Expected = str | tuple[str, ...]
Step = tuple[str, Expected]


class StoreBuildError(AssertionError):
    """Raised when a store-building stage does not print its expected lines."""


@dataclass(frozen=True)
class BuiltStore:
    """A store built by SQLcl plus a snapshot before and after every stage."""

    name: str
    home: Path
    snapshots: list[dict[str, Any]]
    outputs: list[str]


@dataclass(frozen=True)
class CliResult:
    """Outcome of one in-process CLI call."""

    code: int
    stdout: str
    stderr: str
    data: Any


@dataclass(frozen=True)
class DbSettings:
    """Database coordinates for scenarios that need a live database."""

    connect: str
    user: str
    password: str = field(repr=False)


def import_step() -> Step:
    """Return the step that imports the SQL Developer export fixture."""
    return (
        f'connmgr import "{IMPORT_FIXTURE.as_posix()}"',
        tuple(f"Importing connection {n}: Success" for n in IMPORT_NAMES),
    )


def mask(text: str, secret: str | None) -> str:
    """Replace the secret in the text with a placeholder."""
    if secret:
        return text.replace(secret, "<hidden>")
    return text


def check_steps(
    name: str,
    stage_no: int,
    steps: Sequence[Step],
    output: str,
    secret: str | None,
) -> None:
    """Check that the output holds every step's expected lines, step by step."""
    pos = 0
    for step_no, (_command, expected) in enumerate(steps, start=1):
        lines = (expected,) if isinstance(expected, str) else expected
        end = pos
        for line in lines:
            if not line:
                continue
            found = output.find(line, pos)
            if found < 0:
                raise StoreBuildError(
                    f"store {name!r}, stage {stage_no}, step {step_no}: "
                    f"expected line not found: {line!r}\n"
                    f"--- SQLcl output (password masked) ---\n{mask(output, secret)}"
                )
            end = max(end, found + len(line))
        pos = end


@functools.cache
def load_probe() -> ModuleType:
    """Import scripts/store_probe.py as a module."""
    spec = importlib.util.spec_from_file_location("store_probe", PROBE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load the store probe script")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def snapshot(store: Path) -> dict[str, Any]:
    """Snapshot a store, leaving out the sqlcl/ subtree."""
    snap: dict[str, Any] = load_probe().take_snapshot(store)
    snap["files"] = {k: v for k, v in snap["files"].items() if not k.startswith("sqlcl/")}
    return snap


def copy_store(store: Path, dest_root: Path) -> Path:
    """Copy a store directory under dest_root and return the copy."""
    return Path(shutil.copytree(store, dest_root / f"{store.name}_copy"))


def raw_folders(snap: Mapping[str, Any]) -> dict[str, Any]:
    """Return the parsed connection_folders/folders.json of a snapshot."""
    raw: dict[str, Any] = snap["files"]["connection_folders/folders.json"]["json"]
    return raw


def raw_folder_ids(raw: Mapping[str, Any]) -> dict[str, list[str]]:
    """Flatten a raw folders.json dict into {folder path: [connection ids]}."""
    flat: dict[str, list[str]] = {}

    def walk(nodes: Sequence[Mapping[str, Any]], parent: str) -> None:
        for item in nodes:
            path = f"{parent}/{item['name']}"
            flat[path] = list(item.get("connections", []))
            walk(item.get("folders", []), path)

    walk(raw.get("folders", []), "")
    return flat


def assert_no_password(password: str, *texts: str) -> None:
    """Fail without echoing anything when the password occurs in any text."""
    if not password:
        return
    leaked = any(password in text for text in texts)
    if leaked:
        pytest.fail("database password found in tool output", pytrace=False)


def read_release(sql_path: str) -> str:
    """Read the SQLcl release from version.txt next to the executable."""
    version_file = Path(sql_path).parent / "version.txt"
    try:
        text = version_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "unknown"
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("RELEASE="):
            return line.removeprefix("RELEASE=").strip() or "unknown"
    return "unknown"


def run_cli(store: Path, sqlcl_path: str, *args: str) -> CliResult:
    """Run the CLI in process against a store and capture its output."""
    argv = [*args, "--home", str(store), "--sqlcl", sqlcl_path, "--timeout", str(SQLCL_TIMEOUT)]
    out = io.StringIO()
    err = io.StringIO()
    log = io.StringIO()
    handler = logging.StreamHandler(log)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger = logging.getLogger("sqlcl_conn_mng")
    logger.addHandler(handler)
    code = 0
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = cli.main(argv)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 2
    finally:
        logger.removeHandler(handler)
    stdout = out.getvalue()
    data: Any = None
    wants_json = any(a == "--format" and b == "json" for a, b in itertools.pairwise(args))
    if wants_json and code == 0:
        data = json.loads(stdout)
    return CliResult(code=code, stdout=stdout, stderr=err.getvalue() + log.getvalue(), data=data)


def build_stages(
    sqlcl_path: str,
    home: Path,
    name: str,
    stages: Sequence[Sequence[Step]],
    secret: str | None = None,
) -> BuiltStore:
    """Run each stage's commands in one SQLcl process, checking and snapshotting."""
    snapshots = [snapshot(home)]
    outputs: list[str] = []
    runner = SqlclRunner(sqlcl_path, str(home), "thin", SQLCL_TIMEOUT)
    for stage_no, steps in enumerate(stages, start=1):
        script = "\n".join(command for command, _expected in steps)
        try:
            output = runner.run(script)
        except SqlclError as exc:
            raise StoreBuildError(
                mask(f"store {name!r}, stage {stage_no}: {exc}", secret)
            ) from None
        check_steps(name, stage_no, steps, output, secret)
        outputs.append(mask(output, secret))
        snapshots.append(snapshot(home))
    return BuiltStore(name=name, home=home, snapshots=snapshots, outputs=outputs)


def db_settings_from_env(env: Mapping[str, str]) -> DbSettings | list[str]:
    """Return the database settings, or the names of missing variables."""
    missing = [v for v in DB_VARS if not env.get(v)]
    if missing:
        return missing
    return DbSettings(
        connect=env.get(DB_VARS[0], ""),
        user=env.get(DB_VARS[1], ""),
        password=env.get(DB_VARS[2], ""),
    )
