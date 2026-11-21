"""Line icons drawn for Soundflow (24px grid, 1.75px stroke, round joins).

Icons are SVG strings rendered on demand in any colour, so one set serves
both themes and every state (muted, active, accent, danger).
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PATHS: dict[str, str] = {
    "brand": (
        '<path d="M4 10v4M8 7v10M12 4v16M16 8v8M20 11v2"/>'
    ),
    "mic": (
        '<rect x="9" y="3" width="6" height="11" rx="3"/>'
        '<path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>'
    ),
    "home": (
        '<path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z"/>'
    ),
    "history": (
        '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>'
    ),
    "playground": (
        '<path d="M4.5 19.5 14 10M15.5 4v3M14 5.5h3M19.5 9v2.5M18.25 10.25h2.5'
        'M8.5 4.5v2M7.5 5.5h2"/>'
    ),
    "settings": (
        '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/>'
        '<circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>'
    ),
    "copy": (
        '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/>'
        '<path d="M15.5 8.5V6.5a2 2 0 0 0-2-2h-7a2 2 0 0 0-2 2v7a2 2 0 0 0 2 2h2"/>'
    ),
    "edit": (
        '<path d="M4.5 19.5h3.75L19 8.75 15.25 5 4.5 15.75z"/><path d="m13 7.25 3.75 3.75"/>'
    ),
    "sparkle": (
        '<path d="M12 4l1.6 4.9L18.5 10.5l-4.9 1.6L12 17l-1.6-4.9-4.9-1.6 4.9-1.6z"/>'
        '<path d="M18.5 16v3M17 17.5h3"/>'
    ),
    "more": (
        '<circle cx="6" cy="12" r="1.1" fill="currentColor"/>'
        '<circle cx="12" cy="12" r="1.1" fill="currentColor"/>'
        '<circle cx="18" cy="12" r="1.1" fill="currentColor"/>'
    ),
    "trash": (
        '<path d="M4.5 7h15M9.5 7V4.5h5V7M6.5 7l.9 12.5h9.2L17.5 7M10 11v5M14 11v5"/>'
    ),
    "export": (
        '<path d="M12 4v10.5M7.5 10l4.5 4.5 4.5-4.5M5 19.5h14"/>'
    ),
    "logout": (
        '<path d="M9.5 4.5H6.5a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h3"/>'
        '<path d="m15 8 4 4-4 4M19 12H9.5"/>'
    ),
    "search": '<circle cx="11" cy="11" r="6.25"/><path d="m20 20-4.5-4.5"/>',
    "check": '<path d="m5 12.5 4.25 4.25L19 7"/>',
    "keyboard": (
        '<rect x="3" y="6.5" width="18" height="11" rx="2"/>'
        '<path d="M7 10.5h.01M10.5 10.5h.01M14 10.5h.01M17.5 10.5h.01M8 14h8"/>'
    ),
    "close": '<path d="M7 7l10 10M17 7 7 17"/>',
    "minimize": '<path d="M6.5 12h11"/>',
    "maximize": '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5"/>',
}


def _svg(name: str, color: str) -> bytes:
    body = _PATHS[name].replace("currentColor", color)
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.75" stroke-linecap="round" '
        f'stroke-linejoin="round">{body}</svg>'
    ).encode("utf-8")


@lru_cache(maxsize=256)
def icon_pixmap(name: str, color: str, size: int = 18, scale: float = 2.0) -> QPixmap:
    renderer = QSvgRenderer(QByteArray(_svg(name, color)))
    pixels = round(size * scale)
    pixmap = QPixmap(pixels, pixels)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    renderer.render(painter, QRectF(0, 0, pixels, pixels))
    painter.end()
    pixmap.setDevicePixelRatio(scale)
    return pixmap


def icon(name: str, color: str, size: int = 18) -> QIcon:
    return QIcon(icon_pixmap(name, color, size))


def icon_size(size: int = 18) -> QSize:
    return QSize(size, size)


ICON_NAMES = tuple(_PATHS)

__all__ = ["ICON_NAMES", "icon", "icon_pixmap", "icon_size"]
