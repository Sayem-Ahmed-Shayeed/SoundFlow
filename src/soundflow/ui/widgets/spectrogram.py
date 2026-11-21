"""A live spectrogram of the voice: the one colourful thing in Soundflow.

:class:`SpectrumAnalyzer` turns 16 kHz mono PCM into columns of mel-spaced
energy between 0 and 1. :class:`SpectrogramView` scrolls those columns from
right to left and paints them through a fixed colour ramp, dark navy for
silence through teal to pale green for loud speech.

The view repaints only when audio arrives or while the "transcribing" sweep
runs; idle, it costs nothing.
"""

from __future__ import annotations

import math
import random
from collections import deque

import numpy as np
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from soundflow.design.fonts import BODY_FONT
from soundflow.design.motion import reduced_motion
from soundflow.design.theme import current_palette

BINS = 64
SAMPLE_RATE = 16_000
LOW_HZ = 70.0
HIGH_HZ = 7_600.0

# Silence to loud speech. Shared with the redesign prototype.
RAMP = (
    "#06100D", "#0A2A24", "#0F4A40", "#167064",
    "#2E9C86", "#7FD6BE", "#D9F2C9", "#FFFFEB",
)


def _build_lut() -> np.ndarray:
    stops = [QColor(value) for value in RAMP]
    lut = np.empty(256, dtype=np.uint32)
    for index in range(256):
        x = index / 255 * (len(stops) - 1)
        k = min(len(stops) - 2, int(x))
        f = x - k
        a, b = stops[k], stops[k + 1]
        r = round(a.red() + (b.red() - a.red()) * f)
        g = round(a.green() + (b.green() - a.green()) * f)
        bl = round(a.blue() + (b.blue() - a.blue()) * f)
        lut[index] = 0xFF000000 | (r << 16) | (g << 8) | bl
    return lut


LUT = _build_lut()


def _mel(hz: float) -> float:
    return 2595.0 * math.log10(1.0 + hz / 700.0)


def _hz(mel: float) -> float:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def frequency_to_row(hz: float) -> float:
    """Height of *hz* in the view, 0 at the bottom and 1 at the top."""
    return (_mel(hz) - _mel(LOW_HZ)) / (_mel(HIGH_HZ) - _mel(LOW_HZ))


class SpectrumAnalyzer:
    """Mel spectrogram columns from PCM16, about 62 per second."""

    N_FFT = 512
    HOP = 256
    # Power in dB mapped onto 0..1: a quiet room sits near the bottom, normal
    # speech reaches the upper colours. Tuned on a laptop microphone.
    FLOOR_DB = -42.0
    RANGE_DB = 58.0

    def __init__(self, sample_rate: int = SAMPLE_RATE) -> None:
        self.sample_rate = sample_rate
        self._window = np.hanning(self.N_FFT).astype(np.float32)
        self._buffer = np.zeros(0, dtype=np.float32)
        self._filters = self._mel_filters()

    def _mel_filters(self) -> np.ndarray:
        bins = self.N_FFT // 2 + 1
        freqs = np.linspace(0, self.sample_rate / 2, bins)
        edges = [_hz(m) for m in np.linspace(_mel(LOW_HZ), _mel(HIGH_HZ), BINS + 2)]
        filters = np.zeros((BINS, bins), dtype=np.float32)
        for i in range(BINS):
            lo, mid, hi = edges[i], edges[i + 1], edges[i + 2]
            rise = (freqs - lo) / max(mid - lo, 1e-6)
            fall = (hi - freqs) / max(hi - mid, 1e-6)
            filters[i] = np.clip(np.minimum(rise, fall), 0, None)
            total = filters[i].sum()
            if total > 0:
                filters[i] /= total
        return filters

    def reset(self) -> None:
        self._buffer = np.zeros(0, dtype=np.float32)

    def feed(self, pcm: bytes) -> list[np.ndarray]:
        """Add PCM16 mono samples; return any finished columns."""
        samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
        self._buffer = np.concatenate((self._buffer, samples))
        columns: list[np.ndarray] = []
        while self._buffer.size >= self.N_FFT:
            frame = self._buffer[: self.N_FFT] * self._window
            power = np.abs(np.fft.rfft(frame)) ** 2
            energy = self._filters @ power
            db = 10.0 * np.log10(energy + 1e-12)
            columns.append(np.clip((db - self.FLOOR_DB) / self.RANGE_DB, 0.0, 1.0))
            self._buffer = self._buffer[self.HOP:]
        return columns


# --- Synthetic voice, for still pictures (sign-in art, previews) -------------
def _speech_envelope(t: float) -> float:
    syllable = max(0.0, math.sin(t * 2 * math.pi * 4.1 + math.sin(t * 1.3) * 2.2))
    phrase = max(0.0, math.sin(t * 2 * math.pi * 0.28 + 0.6) + 0.35)
    return min(1.0, syllable ** 0.6 * min(1.0, phrase))


def synthetic_column(t: float, rng: random.Random, envelope: float | None = None) -> np.ndarray:
    env = _speech_envelope(t) if envelope is None else envelope
    f0 = 0.07 + 0.015 * math.sin(t * 3.1)
    formants = (
        0.17 + 0.05 * math.sin(t * 5.3),
        0.37 + 0.08 * math.sin(t * 3.7 + 1),
        0.60 + 0.06 * math.sin(t * 2.9 + 2),
    )
    fricative = 1.0 if math.sin(t * 6.7 + 1.1) > 0.85 else 0.0
    y = np.linspace(0.0, 1.0, BINS)
    form = sum(
        np.exp(-(((y - f) / (0.045 + 0.02 * k)) ** 2)) * (1 - 0.22 * k)
        for k, f in enumerate(formants)
    )
    harmonics = 0.55 + 0.45 * np.cos(y / f0 * 2 * math.pi)
    noise = np.array([rng.random() for _ in range(BINS)])
    value = 0.035 + 0.05 * noise
    value = value + env * (0.22 + 0.8 * form) * harmonics * (1 - 0.55 * y)
    value = value + env * fricative * 0.45 * y * noise
    return np.clip(value, 0.0, 1.0)


# Vowel formants (F1, F2, F3 in Hz), roughly a, e, i, o, u and schwa.
_VOWELS = (
    (750, 1220, 2600), (530, 1840, 2480), (300, 2300, 3000),
    (500, 900, 2500), (330, 950, 2400), (500, 1500, 2500),
)


def synthetic_speech(seconds: float, seed: int = 11, *, fade: bool = False) -> bytes:
    """A made-up spoken phrase as 16 kHz PCM16, for still pictures.

    Pitched syllables with vowel formants, a few "s" sounds and short
    pauses: run through :class:`SpectrumAnalyzer` it looks like real speech.
    """
    rng = np.random.default_rng(seed)
    total = int(SAMPLE_RATE * seconds)
    signal = np.zeros(total, dtype=np.float64)
    position = int(SAMPLE_RATE * 0.05)
    base = rng.uniform(115, 175)
    syllables = 0
    while position < total:
        length = int(SAMPLE_RATE * rng.uniform(0.11, 0.26))
        end = min(total, position + length)
        n = end - position
        t = np.arange(n) / SAMPLE_RATE
        if rng.random() < 0.18:
            # A fricative: shaped noise high in the spectrum.
            noise = np.fft.rfft(rng.normal(0, 1, n))
            freqs = np.fft.rfftfreq(n, 1 / SAMPLE_RATE)
            noise *= np.clip((freqs - 3200) / 1800, 0, 1)
            burst = np.fft.irfft(noise, n) * 0.35
            signal[position:end] += burst * np.hanning(n)
        else:
            f0 = base * (1 + rng.uniform(-0.12, 0.12)) * (1 - 0.18 * t / max(t[-1], 1e-3))
            phase = 2 * np.pi * np.cumsum(f0) / SAMPLE_RATE
            formants = _VOWELS[int(rng.integers(len(_VOWELS)))]
            mean_f0 = float(f0.mean())
            voice = np.zeros(n)
            for k in range(1, int(7600 / mean_f0)):
                hz = k * mean_f0
                gain = 0.025 + sum(
                    np.exp(-(((hz - f) / (90 + 40 * i)) ** 2)) * (1 - 0.3 * i)
                    for i, f in enumerate(formants)
                )
                voice += gain / k ** 0.9 * np.sin(k * phase)
            envelope = np.sin(np.pi * np.arange(n) / n) ** 0.5
            signal[position:end] += voice * envelope
        syllables += 1
        gap = rng.uniform(0.02, 0.08)
        if syllables % int(rng.integers(5, 9)) == 0:
            gap += rng.uniform(0.25, 0.45)  # between phrases
        position = end + int(SAMPLE_RATE * gap)
    rms = float(np.sqrt(np.mean(signal ** 2))) or 1.0
    signal = signal / rms * 0.06
    if fade:
        signal *= np.clip(np.linspace(1.6, -0.2, total), 0, 1)
    signal += rng.normal(0, 0.0015, total)
    return (np.clip(signal, -1, 1) * 32767).astype("<i2").tobytes()


def silence_column(rng: random.Random) -> np.ndarray:
    y = np.linspace(0.0, 1.0, BINS)
    return np.array([0.02 + 0.06 * rng.random() for _ in range(BINS)]) * (1 - y * 0.9)


class SpectrogramView(QWidget):
    """Scrolling spectrogram strip.

    States: ``idle`` (quiet texture and a hint), ``live`` (columns scroll in),
    ``frozen`` (the recording stretched to fill the strip) and ``scanning``
    (frozen, with a light sweeping across while Whisper reads it).
    """

    SCAN_MS = 1500

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        columns: int = 320,
        compact: bool = False,
        hint: str = "",
    ) -> None:
        super().__init__(parent)
        self.setObjectName("spectrogram")
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._capacity = columns
        self._compact = compact
        self._hint = hint
        self._gain = 1.0
        self._analyzer = SpectrumAnalyzer()
        self._rng = random.Random(7)
        self._columns: deque[np.ndarray] = deque(maxlen=columns)
        self._recorded = 0
        self._state = "idle"
        self._scan = 0.0
        self._image: QImage | None = None
        self._image_dirty = True
        self._scan_animation = QVariantAnimation(self)
        self._scan_animation.setStartValue(0.0)
        self._scan_animation.setEndValue(1.0)
        self._scan_animation.setDuration(self.SCAN_MS)
        self._scan_animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._scan_animation.setLoopCount(-1)
        self._scan_animation.valueChanged.connect(self._set_scan)
        self.reset()

    # -- public API ---------------------------------------------------------
    @property
    def state(self) -> str:
        return self._state

    def set_hint(self, text: str) -> None:
        self._hint = text
        self.update()

    def set_gain(self, gain: float) -> None:
        """Brighten small views, where faint columns would read as empty."""
        self._gain = gain

    def reset(self) -> None:
        """Back to the idle texture."""
        self._scan_animation.stop()
        self._analyzer.reset()
        self._columns.clear()
        for _ in range(self._capacity):
            self._columns.append(silence_column(self._rng))
        self._recorded = 0
        self._state = "idle"
        self._image_dirty = True
        self.update()

    def start_live(self) -> None:
        """Begin a recording: new audio scrolls in from the right."""
        self.reset()
        self._state = "live"
        self.update()

    def push_audio(self, pcm: bytes) -> None:
        if self._state != "live":
            return
        columns = self._analyzer.feed(pcm)
        if columns:
            self.push_columns(columns)

    def push_columns(self, columns) -> None:
        for column in columns:
            self._columns.append(np.clip(np.asarray(column, dtype=float) * self._gain, 0, 1))
        self._recorded = min(self._capacity, self._recorded + len(columns))
        self._image_dirty = True
        self.update()

    def freeze(self) -> None:
        """Keep the recording on screen, stretched to fill the strip."""
        if self._state == "idle":
            return
        self._scan_animation.stop()
        self._state = "frozen"
        self._image_dirty = True
        self.update()

    def set_scanning(self, scanning: bool) -> None:
        if scanning:
            if self._state == "idle":
                return
            self._state = "scanning"
            self._image_dirty = True
            if reduced_motion():
                self._scan = 0.62
                self.update()
            else:
                self._scan_animation.start()
        else:
            self._scan_animation.stop()
            if self._state == "scanning":
                self._state = "frozen"
            self.update()

    def fill_synthetic(self, seed: int = 11, *, fade: bool = False) -> None:
        """Show a made-up spoken sentence (sign-in art, previews)."""
        analyzer = SpectrumAnalyzer()
        seconds = (self._capacity + 4) * SpectrumAnalyzer.HOP / SAMPLE_RATE
        columns = analyzer.feed(synthetic_speech(seconds, seed, fade=fade))
        self._columns.clear()
        for column in columns[-self._capacity:]:
            self._columns.append(np.clip(column * self._gain, 0, 1))
        while len(self._columns) < self._capacity:
            self._columns.appendleft(silence_column(self._rng))
        self._recorded = self._capacity
        self._state = "frozen"
        self._image_dirty = True
        self.update()

    def visible_columns(self) -> list[np.ndarray]:
        """The columns the view shows now (frozen views drop leading silence)."""
        columns = list(self._columns)
        if self._state in {"frozen", "scanning"} and self._recorded:
            columns = columns[-self._recorded:]
            loud = [i for i, c in enumerate(columns) if float(c.max()) > 0.32]
            if loud:
                start = max(0, loud[0] - 6)
                end = min(len(columns), loud[-1] + 7)
                columns = columns[start:end]
            if len(columns) < 24:
                columns = list(self._columns)[-24:]
        return columns

    # -- painting -----------------------------------------------------------
    def _set_scan(self, value) -> None:
        self._scan = float(value)
        self.update()

    def _render_image(self) -> QImage:
        columns = self.visible_columns()
        values = np.stack(columns, axis=1)  # BINS x width, row 0 = lowest
        values = np.flipud(values)
        indices = np.clip((np.power(values, 0.85) * 255).astype(np.int32), 0, 255)
        pixels = np.ascontiguousarray(LUT[indices])
        height, width = pixels.shape
        image = QImage(pixels.data, width, height, width * 4, QImage.Format.Format_RGB32)
        return image.copy()

    def paintEvent(self, event) -> None:
        del event
        if self._image is None or self._image_dirty:
            self._image = self._render_image()
            self._image_dirty = False
        colors = current_palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = QRectF(self.rect())
        radius = 5.0 if self._compact else 12.0
        path = QPainterPath()
        path.addRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
        painter.setClipPath(path)
        painter.fillRect(rect, QColor(colors["spectrum_bg"]))
        painter.drawImage(rect, self._image)

        if not self._compact:
            painter.setPen(Qt.PenStyle.NoPen)
            grid = QColor(255, 255, 255, 13)
            for fraction in (0.25, 0.5, 0.75):
                y = round(rect.height() * fraction)
                painter.fillRect(QRectF(0, y, rect.width(), 1), grid)

        if self._state == "scanning":
            painter.fillRect(rect, QColor(4, 6, 10, 115))
            x = rect.width() * self._scan
            glow = QLinearGradient(QPointF(x - 26, 0), QPointF(x + 26, 0))
            glow.setColorAt(0.0, QColor(63, 224, 197, 0))
            glow.setColorAt(0.5, QColor(63, 224, 197, 110))
            glow.setColorAt(1.0, QColor(63, 224, 197, 0))
            painter.fillRect(QRectF(x - 26, 0, 52, rect.height()), glow)
            painter.fillRect(QRectF(x - 1, 0, 2, rect.height()), QColor("#E8FFF9"))

        painter.setClipping(False)
        if not self._compact:
            self._paint_labels(painter, rect, colors)
            painter.setPen(QPen(QColor(colors["spectrum_border"]), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(path)

    def _paint_labels(self, painter: QPainter, rect: QRectF, colors: dict) -> None:
        font = QFont(BODY_FONT)
        font.setPixelSize(11)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        metrics = painter.fontMetrics()
        for label, hz in (("8 kHz", 7_400.0), ("2 kHz", 2_000.0), ("500 Hz", 500.0)):
            y = rect.height() * (1 - frequency_to_row(hz))
            y = min(max(y, 14.0), rect.height() - 14.0)
            width = metrics.horizontalAdvance(label) + 10
            box = QRectF(rect.width() - width - 10, y - 9, width, 18)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(4, 6, 10, 190))
            painter.drawRoundedRect(box, 5, 5)
            painter.setPen(QColor(colors["spectrum_text"]))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label)
        if self._hint and self._state == "idle":
            hint_font = QFont(BODY_FONT)
            hint_font.setPixelSize(13)
            painter.setFont(hint_font)
            painter.setPen(QColor(colors["spectrum_text"]))
            painter.drawText(
                QRectF(18, rect.height() - 34, rect.width() - 120, 22),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                self._hint,
            )


__all__ = [
    "BINS",
    "LUT",
    "RAMP",
    "SpectrogramView",
    "SpectrumAnalyzer",
    "frequency_to_row",
    "silence_column",
    "synthetic_column",
    "synthetic_speech",
]
