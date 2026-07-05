"""File-system helpers."""

from __future__ import annotations

from pathlib import Path

from soundflow.core.settings import data_directory


def open_data_folder() -> Path:
    """Open Soundflow's data directory in the system file manager.

    Returns the path that was opened so callers can show it in a status
    message if the desktop environment doesn't actually surface a window.
    """
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    folder = data_directory()
    folder.mkdir(parents=True, exist_ok=True)
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
    return folder


__all__ = ["open_data_folder"]