from __future__ import annotations

import math
from array import array
from collections import deque
from dataclasses import dataclass


@dataclass
class SegmenterConfig:
    sample_rate: int = 16_000
    frame_ms: int = 30
    threshold: float = 0.012
    silence_ms: int = 700
    min_speech_ms: int = 250
    max_speech_s: int = 20
    pre_roll_ms: int = 300


def pcm16_rms(frame: bytes) -> float:
    samples = array("h")
    samples.frombytes(frame)
    if not samples:
        return 0.0
    if samples.itemsize != 2:
        raise RuntimeError("This platform does not expose 16-bit signed shorts")
    total = sum(sample * sample for sample in samples)
    return math.sqrt(total / len(samples)) / 32768.0


class EnergySegmenter:
    """Low-cost endpoint detector. The model performs the final speech filtering."""

    def __init__(self, config: SegmenterConfig) -> None:
        self.config = config
        self._pre_roll: deque[bytes] = deque(maxlen=max(1, config.pre_roll_ms // config.frame_ms))
        self._segment = bytearray()
        self._speech_ms = 0
        self._silence_ms = 0
        self._active = False

    def reset(self) -> None:
        self._pre_roll.clear()
        self._segment.clear()
        self._speech_ms = 0
        self._silence_ms = 0
        self._active = False

    def feed(self, frame: bytes) -> list[bytes]:
        voiced = pcm16_rms(frame) >= self.config.threshold
        completed: list[bytes] = []

        if not self._active:
            self._pre_roll.append(frame)
            if voiced:
                self._active = True
                self._segment.extend(b"".join(self._pre_roll))
                self._pre_roll.clear()
                self._speech_ms = self.config.frame_ms
            return completed

        self._segment.extend(frame)
        if voiced:
            self._speech_ms += self.config.frame_ms
            self._silence_ms = 0
        else:
            self._silence_ms += self.config.frame_ms

        duration_s = len(self._segment) / (self.config.sample_rate * 2)
        if self._silence_ms >= self.config.silence_ms or duration_s >= self.config.max_speech_s:
            segment = self._finish()
            if segment:
                completed.append(segment)
        return completed

    def flush(self) -> list[bytes]:
        segment = self._finish()
        return [segment] if segment else []

    def snapshot(self) -> bytes:
        """Return in-progress speech without ending the phrase (for live interim)."""
        if not self._active or self._speech_ms < self.config.min_speech_ms:
            return b""
        return bytes(self._segment)

    def _finish(self) -> bytes | None:
        result = bytes(self._segment) if self._speech_ms >= self.config.min_speech_ms else None
        self.reset()
        return result

