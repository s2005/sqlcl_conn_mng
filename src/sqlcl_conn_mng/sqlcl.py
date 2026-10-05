"""Drive Oracle SQLcl for every operation that writes the connection store.

SQLcl always exits 0, so success is detected from its output text. The script
text is fed on stdin and is never logged because it can carry a password.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SQLCL_ENV_VAR = "SQLCL_BIN"
DEFAULT_TIMEOUT = 120
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_PADDING = re.compile(r"[ \t]+")
_SAFE_TOKEN = re.compile(r"[A-Za-z0-9_./@:\\-]+")
_FORBIDDEN = ("\n", "\r", '"')
_SAVE_FAILURES = ("Connection failed", "Syntax error", "ORA-", "SP2-", "Usage")


class SqlclError(Exception):
    """Raised when SQLcl cannot be run or reports that an operation failed."""


@dataclass(frozen=True)
class ShowResult:
    """Fields reported by `connmgr show`."""

    name: str
    connect_string: str
    user: str
    password_saved: bool


def resolve_sql_path(option: str | None) -> str:
    """Find the sql executable: option, then SQLCL_BIN, then PATH."""
    candidate = option or os.environ.get(SQLCL_ENV_VAR) or shutil.which("sql")
    if not candidate:
        raise SqlclError("SQLcl not found: use --sqlcl, set SQLCL_BIN, or put sql on PATH")
    return candidate


def clean_output(text: str) -> str:
    """Strip ANSI escapes, collapse padding and drop empty lines."""
    stripped = _ANSI.sub("", text)
    lines = (_PADDING.sub(" ", line).strip() for line in stripped.splitlines())
    return "\n".join(line for line in lines if line)


def validate_value(value: str, what: str) -> str:
    """Reject empty values and values SQLcl cannot take safely."""
    if not value:
        raise ValueError(f"{what} must not be empty")
    if any(bad in value for bad in _FORBIDDEN):
        raise ValueError(f"{what} must not contain a newline, carriage return or double quote")
    return value


def quote_arg(value: str, what: str) -> str:
    """Validate a name, folder, user or connect string and quote it when needed."""
    validate_value(value, what)
    if _SAFE_TOKEN.fullmatch(value):
        return value
    return f'"{value}"'


def quote_password(password: str) -> str:
    """Quote a password for the connect command."""
    if not password:
        raise ValueError("password must not be empty")
    if "\n" in password or "\r" in password:
        raise ValueError("password must not contain a newline or carriage return")
    if '"' not in password:
        return f'"{password}"'
    if "'" not in password:
        return f"'{password}'"
    raise ValueError("password containing both double and single quotes is not supported")


def normalize_folder(folder: str) -> str:
    """Return a validated absolute folder path such as /dev/local."""
    validate_value(folder, "folder")
    path = "/" + folder.strip("/")
    if path == "/":
        raise ValueError("folder must name a folder below the root")
    return path


class SqlclRunner:
    """Run SQLcl scripts against a store root."""

    def __init__(
        self,
        sql_path: str,
        home: str,
        driver: str = "thin",
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        self.sql_path = sql_path
        self.home = home
        self.driver = driver
        self.timeout = timeout

    def argv(self) -> list[str]:
        """Build the SQLcl command line; it never carries a password."""
        args = [self.sql_path, "-S", "-nohistory", "-noupdates"]
        if self.driver == "thin":
            args.append("-thin")
        args.extend(["-home", self.home, "/nolog"])
        return args

    def run(self, script: str) -> str:
        """Feed the script on stdin and return cleaned output."""
        argv = self.argv()
        logger.debug("Running SQLcl: %s", argv)
        try:
            proc = subprocess.run(
                argv,
                input=script.rstrip("\n") + "\nexit\n",
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise SqlclError(f"SQLcl timed out after {self.timeout} seconds") from exc
        except OSError as exc:
            raise SqlclError(f"Cannot run SQLcl: {exc}") from exc
        output = clean_output((proc.stdout or "") + "\n" + (proc.stderr or ""))
        logger.debug("SQLcl output: %s", output)
        return output


def _expect(runner: SqlclRunner, script: str, marker: str) -> str:
    output = runner.run(script)
    if marker not in output:
        raise SqlclError(output or "SQLcl produced no output")
    return output


def add_folder(runner: SqlclRunner, folder: str) -> str:
    """Create a connection folder."""
    path = normalize_folder(folder)
    return _expect(runner, f"connmgr add -folder {quote_arg(path, 'folder')}", "has been added")


def delete_folder(runner: SqlclRunner, folder: str, force: bool = False) -> str:
    """Delete a folder; force also deletes the connections inside it."""
    path = normalize_folder(folder)
    flag = " -force" if force else ""
    script = f"connmgr delete -folder {quote_arg(path, 'folder')}{flag}"
    return _expect(runner, script, "has been deleted")


def delete_connection(runner: SqlclRunner, name: str) -> str:
    """Delete a saved connection."""
    return _expect(runner, f"connmgr delete -conn {quote_arg(name, 'name')}", "has been deleted")


def rename_connection(runner: SqlclRunner, name: str, new_name: str) -> str:
    """Rename a saved connection."""
    script = f"connmgr rename -conn {quote_arg(name, 'name')} {quote_arg(new_name, 'new name')}"
    return _expect(runner, script, "has been renamed")


def move_connection(runner: SqlclRunner, name: str, folder: str) -> str:
    """Move a saved connection into a folder."""
    path = normalize_folder(folder)
    script = f"connmgr move -conn {quote_arg(name, 'name')} {quote_arg(path, 'folder')}"
    return _expect(runner, script, "has been moved to")


def clone_connection(
    runner: SqlclRunner,
    name: str,
    new_name: str,
    user: str | None = None,
    no_password: bool = False,
) -> str:
    """Clone a saved connection."""
    parts = ["connmgr clone", f"-original {quote_arg(name, 'name')}"]
    if user is not None:
        parts.append(f"-username {quote_arg(user, 'user')}")
    if no_password:
        parts.append("-nopwd")
    parts.append(quote_arg(new_name, "new name"))
    return _expect(runner, " ".join(parts), "has been cloned")


def show_connection(runner: SqlclRunner, name: str) -> ShowResult:
    """Run `connmgr show` and parse its fields."""
    output = runner.run(f"connmgr show {quote_arg(name, 'name')}")
    fields: dict[str, str] = {}
    for line in output.splitlines():
        key, sep, value = line.partition(":")
        if sep and key in ("Name", "Connect String", "User", "Password"):
            fields[key] = value.strip()
    if "Password" not in fields:
        raise SqlclError(output or "SQLcl produced no output")
    # SQLcl 25.4.1 prints "Password: ******" when saved or "Password: not saved" otherwise
    password_value = fields["Password"].lower()
    password_saved = bool(password_value) and password_value != "not saved"
    return ShowResult(
        name=fields.get("Name", name),
        connect_string=fields.get("Connect String", ""),
        user=fields.get("User", ""),
        password_saved=password_saved,
    )


def check_connection(runner: SqlclRunner, name: str) -> str:
    """Run `connmgr test`; return SQLcl output on success."""
    output = runner.run(f"connmgr test {quote_arg(name, 'name')}")
    if "Connection Test Failed" in output or "success" not in output.lower():
        raise SqlclError(output or "SQLcl produced no output")
    return output


def save_connection(
    runner: SqlclRunner,
    name: str,
    user: str,
    connect_string: str,
    password: str,
    save_password: bool = True,
    replace: bool = False,
) -> str:
    """Connect and save a connection; SQLcl saves only after a successful connect."""
    target = f"{validate_value(user, 'user')}@{validate_value(connect_string, 'connect string')}"
    parts = ["connect", f"-save {quote_arg(name, 'name')}"]
    if save_password:
        parts.append("-savepwd")
    if replace:
        parts.append("-replace")
    parts.append(f"-password {quote_password(password)}")
    parts.append(quote_arg(target, "user and connect string"))
    output = runner.run(" ".join(parts))
    if any(marker in output for marker in _SAVE_FAILURES):
        raise SqlclError(_without_password(output, password))
    return _without_password(output, password)


def _without_password(output: str, password: str) -> str:
    """Make sure SQLcl output echoing the password is never surfaced."""
    return output.replace(password, "<hidden>") if password else output
