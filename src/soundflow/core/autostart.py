"""Turn "open Soundflow when you log in" on or off for a Linux install.

``install-linux.sh`` sets up one of two things: a systemd user service
(``soundflow.service``, enabled at login) or, without systemd, an XDG
autostart entry. Both are switched here. When neither exists, nothing is
installed and the call does nothing.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

LOGGER = logging.getLogger(__name__)
SERVICE_NAME = "soundflow.service"
AUTOSTART_NAME = "soundflow.desktop"
_RUN_TIMEOUT_S = 10

Runner = Callable[[list[str]], int]


@dataclass(frozen=True)
class AutostartPaths:
    config_home: Path

    @property
    def autostart_file(self) -> Path:
        return self.config_home / "autostart" / AUTOSTART_NAME

    @property
    def service_file(self) -> Path:
        return self.config_home / "systemd" / "user" / SERVICE_NAME


def default_paths() -> AutostartPaths:
    configured = os.environ.get("XDG_CONFIG_HOME")
    root = Path(configured) if configured else Path.home() / ".config"
    return AutostartPaths(config_home=root)


def _systemctl(args: list[str]) -> int:
    completed = subprocess.run(
        ["systemctl", "--user", *args],
        check=False,
        capture_output=True,
        timeout=_RUN_TIMEOUT_S,
    )
    return completed.returncode


def _set_hidden(path: Path, *, hidden: bool) -> bool:
    """Add or remove ``Hidden=true`` in an autostart entry."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        LOGGER.warning("Could not read autostart entry %s", path)
        return False
    kept = [line for line in lines if not line.strip().lower().startswith("hidden=")]
    if hidden:
        try:
            header = next(i for i, line in enumerate(kept) if line.strip() == "[Desktop Entry]")
        except StopIteration:
            kept.insert(0, "[Desktop Entry]")
            header = 0
        kept.insert(header + 1, "Hidden=true")
    temporary = path.with_suffix(".desktop.tmp")
    try:
        temporary.write_text("\n".join(kept) + "\n", encoding="utf-8")
        temporary.replace(path)
    except OSError:
        LOGGER.warning("Could not update autostart entry %s", path)
        return False
    return True


def set_open_at_login(
    enabled: bool,
    *,
    paths: AutostartPaths | None = None,
    run: Runner | None = None,
) -> bool:
    """Apply the login setting. Returns False only when a change failed.

    Nothing installed means nothing to change, so that counts as success.
    """
    if not sys.platform.startswith("linux"):
        return True
    paths = paths or default_paths()
    run = run or _systemctl
    ok = True
    if paths.service_file.exists():
        try:
            code = run(["enable" if enabled else "disable", SERVICE_NAME])
        except (OSError, subprocess.SubprocessError):
            LOGGER.warning("systemctl could not change %s", SERVICE_NAME, exc_info=True)
            code = 1
        if code != 0:
            LOGGER.warning("systemctl returned %s for %s", code, SERVICE_NAME)
            ok = False
    if paths.autostart_file.exists():
        ok = _set_hidden(paths.autostart_file, hidden=not enabled) and ok
    return ok


__all__ = [
    "AutostartPaths",
    "default_paths",
    "set_open_at_login",
]
