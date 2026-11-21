"""Paint the still "flowers in motion" picture for the sign-in window.

An original painting, not a photograph: a pale sky, dark green foliage and
clusters of lavender, pink, marigold and cream blooms, smeared by a diagonal
motion blur and finished with film grain, like a photo taken while walking
past a flower bed. Run once and commit the result:

    .venv/bin/python scripts/render_auth_flowers.py [out.jpg]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QRadialGradient

WIDTH, HEIGHT = 1200, 1320
SEED = 23
OUT = Path(__file__).resolve().parents[1] / "src/soundflow/assets/art/auth-flowers.jpg"

SKY_TOP = (0xF6, 0xF7, 0xE6)
SKY_LOW = (0xC9, 0xE2, 0xD8)
FOLIAGE = [(0x06, 0x10, 0x0D), (0x0A, 0x2A, 0x24), (0x0F, 0x4A, 0x40), (0x2E, 0x6B, 0x3F), (0x55, 0x86, 0x3E)]
# Blooms: lavender (the app's button), pink, marigold, cream, a little coral.
BLOOMS = [
    ((0xE6, 0xC2, 0xFF), 0.26),
    ((0xE8, 0x8F, 0xB8), 0.22),
    ((0xF2, 0xB3, 0x3D), 0.24),
    ((0xFF, 0xFF, 0xEB), 0.16),
    ((0xE0, 0x6A, 0x55), 0.12),
]


def _blob(painter: QPainter, x: float, y: float, rx: float, ry: float, rgb, alpha: float) -> None:
    gradient = QRadialGradient(QPointF(0, 0), 1.0)
    inner = QColor(*rgb)
    inner.setAlphaF(alpha)
    outer = QColor(*rgb)
    outer.setAlphaF(0.0)
    gradient.setColorAt(0.0, inner)
    gradient.setColorAt(0.55, inner)
    gradient.setColorAt(1.0, outer)
    painter.save()
    painter.translate(x, y)
    painter.scale(rx, ry)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(gradient)
    painter.drawEllipse(QPointF(0, 0), 1.0, 1.0)
    painter.restore()


def _paint(rng: np.random.Generator) -> np.ndarray:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_RGB888)
    image.fill(QColor(*FOLIAGE[1]))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Sky behind the top of the bed, its edge tilted like the blur.
    horizon = HEIGHT * 0.2
    for i in range(140):
        t = i / 139
        y = t * horizon * 1.25
        rgb = tuple(int(a + (b - a) * t) for a, b in zip(SKY_TOP, SKY_LOW))
        _blob(painter, WIDTH * rng.uniform(0.2, 1.1), y, WIDTH * 0.45, horizon * 0.35, rgb, 0.18)

    # Dark trees on the left of the horizon.
    for _ in range(90):
        x = rng.uniform(-0.1, 0.55) * WIDTH
        y = rng.uniform(0.02, 0.32) * HEIGHT
        _blob(painter, x, y, rng.uniform(60, 160), rng.uniform(40, 120), FOLIAGE[rng.integers(0, 2)], 0.35)

    # Foliage: layers of leaf strokes, lighter towards the middle of the bed.
    for _ in range(2600):
        x = rng.uniform(-0.05, 1.05) * WIDTH
        y = rng.uniform(0.18, 1.02) * HEIGHT
        depth = (y / HEIGHT - 0.18) / 0.84
        size = 6 + 30 * depth
        shade = FOLIAGE[min(4, int(rng.beta(2.0, 2.6) * 5))]
        _blob(painter, x, y, size * rng.uniform(0.6, 1.6), size * rng.uniform(0.3, 0.8), shade, rng.uniform(0.25, 0.6))

    # Blooms: clusters along a diagonal drift, small and far at the top,
    # big and close at the bottom.
    colours = [c for c, _ in BLOOMS]
    weights = np.array([w for _, w in BLOOMS])
    weights /= weights.sum()
    for _ in range(360):
        t = rng.uniform(0.0, 1.0)
        y = (0.2 + 0.82 * t) * HEIGHT
        centre = 0.6 - 0.25 * t + rng.normal(0, 0.2)
        x = centre * WIDTH
        size = 10 + 52 * t**1.3
        rgb = colours[rng.choice(len(colours), p=weights)]
        for _ in range(rng.integers(2, 6)):
            dx, dy = rng.normal(0, size * 0.5, 2)
            petal = size * rng.uniform(0.5, 1.0)
            _blob(painter, x + dx, y + dy, petal, petal * rng.uniform(0.6, 1.0), rgb, rng.uniform(0.8, 1.0))
        # A bright core catches the light.
        _blob(painter, x, y, size * 0.3, size * 0.25, (0xFF, 0xFF, 0xEB), 0.5)

    # A pale path of light through the bottom left, like the reflection in the reference mood.
    for _ in range(40):
        t = rng.uniform(0.55, 1.0)
        _blob(painter, (0.18 + 0.12 * (1 - t)) * WIDTH + rng.normal(0, 30), t * HEIGHT,
              rng.uniform(40, 90), rng.uniform(30, 60), (0xBF, 0xDC, 0xE6), 0.18)
    painter.end()

    ptr = image.constBits()
    data = np.frombuffer(ptr, dtype=np.uint8, count=image.sizeInBytes())
    rows = data.reshape(HEIGHT, image.bytesPerLine())[:, : WIDTH * 3]
    return rows.reshape(HEIGHT, WIDTH, 3).astype(np.float32) / 255.0


def _box(img: np.ndarray, radius: int, axis: int) -> np.ndarray:
    if radius < 1:
        return img
    pad = [(0, 0)] * img.ndim
    pad[axis] = (radius + 1, radius)
    padded = np.pad(img, pad, mode="edge")
    total = np.cumsum(padded, axis=axis)
    hi = np.take(total, np.arange(2 * radius + 1, total.shape[axis]), axis=axis)
    lo = np.take(total, np.arange(0, total.shape[axis] - 2 * radius - 1), axis=axis)
    return (hi - lo) / (2 * radius + 1)


def _soften(img: np.ndarray, radius: int) -> np.ndarray:
    """Close to a Gaussian blur: three box blurs on each axis."""
    for _ in range(3):
        img = _box(_box(img, radius, 0), radius, 1)
    return img


def _motion(img: np.ndarray, length: int, angle_deg: float, taps: int = 48) -> np.ndarray:
    """Smear along a direction, the way a moving camera does."""
    angle = np.radians(angle_deg)
    dx, dy = np.cos(angle), np.sin(angle)
    pad = length
    padded = np.pad(img, ((pad, pad), (pad, pad), (0, 0)), mode="edge")
    out = np.zeros_like(img)
    for i in range(taps):
        s = (i / (taps - 1) - 0.5) * length
        ox, oy = round(s * dx), round(s * dy)
        out += padded[pad + oy : pad + oy + img.shape[0], pad + ox : pad + ox + img.shape[1]]
    return out / taps


def render(seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    img = _paint(rng)
    img = _soften(img, 1)
    # A long smear up and to the right, with a ghost of the sharper bed kept
    # in it so the blooms still read as flowers.
    near = _motion(img, 26, -62)
    far = _motion(img, 90, -62, taps=64)
    img = 0.45 * near + 0.55 * far
    img = _soften(img, 1)

    # Film look: lifted blacks, slight warmth, vignette, grain.
    img = 0.03 + img * 0.97
    ys, xs = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    v = ((xs / WIDTH - 0.5) * 1.1) ** 2 + ((ys / HEIGHT - 0.5) * 0.9) ** 2
    img *= (1.0 - v * 0.9)[..., None]
    grain = rng.normal(0.0, 0.018, (HEIGHT, WIDTH, 1)).astype(np.float32)
    img += _soften(grain, 1) * 1.4
    return np.clip(img, 0.0, 1.0)


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else OUT
    rgb = np.ascontiguousarray((render() * 255 + 0.5).astype(np.uint8))
    image = QImage(rgb.data, WIDTH, HEIGHT, WIDTH * 3, QImage.Format.Format_RGB888)
    if not image.save(str(out), "JPEG", 90):
        print(f"Could not write {out}", file=sys.stderr)
        return 1
    print(f"Wrote {out} ({out.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
