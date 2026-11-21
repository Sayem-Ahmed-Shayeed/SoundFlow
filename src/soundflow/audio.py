from __future__ import annotations

import gc
import importlib
import sys
from collections.abc import Callable
from pathlib import Path
from threading import Event, RLock, Thread
from typing import Any

from soundflow.core.segmenter import pcm16_rms


# PortAudio is not safe to initialise from two threads at once; a second
# device scan waits for the first instead of racing it (that crashed).
_DEVICE_SCAN_LOCK = RLock()


class AudioCaptureError(RuntimeError):
    pass


def _import_sounddevice():
    """Let frozen Linux builds resolve the bundled PortAudio shared library."""
    if getattr(sys, "frozen", False) and sys.platform.startswith("linux"):
        import ctypes.util

        bundled = Path(getattr(sys, "_MEIPASS")) / "libportaudio.so.2"
        if bundled.is_file():
            original = ctypes.util.find_library
            ctypes.util.find_library = (
                lambda name: str(bundled) if name == "portaudio" else original(name)
            )
            try:
                return importlib.import_module("sounddevice")
            finally:
                ctypes.util.find_library = original
    return importlib.import_module("sounddevice")


class AudioCapture:
    SAMPLE_RATE = 16_000
    FRAME_MS = 30

    def __init__(
        self,
        on_frame: Callable[[bytes], None],
        on_level: Callable[[float], None],
        on_error: Callable[[str], None],
    ) -> None:
        self.on_frame = on_frame
        self.on_level = on_level
        self.on_error = on_error
        self._stream: Any = None
        self._lock = RLock()

    @staticmethod
    def list_input_devices() -> list[tuple[int, str]]:
        devices: list[tuple[int, str]] = []
        finished = Event()

        def enumerate_devices() -> None:
            try:
                with _DEVICE_SCAN_LOCK:
                    sd = _import_sounddevice()
                    for index, device in enumerate(sd.query_devices()):
                        if int(device.get("max_input_channels", 0)) > 0:
                            devices.append(
                                (index, str(device.get("name", f"Input {index}")))
                            )
            except Exception:
                pass
            finally:
                finished.set()

        # Collect garbage here, on the calling (UI) thread. Otherwise the scan
        # thread's allocations can trigger a collection there, and Shiboken
        # crashes deleting Qt widgets off the main thread.
        gc.collect()
        Thread(target=enumerate_devices, name="soundflow-device-scan", daemon=True).start()
        finished.wait(1.5)
        return list(devices)

    def start(self, device: int | None = None) -> None:
        try:
            sd = _import_sounddevice()
        except Exception as exc:
            raise AudioCaptureError(
                "Audio support could not start. Install the PortAudio runtime "
                "(libportaudio2 on Ubuntu) and the project dependencies."
            ) from exc

        with self._lock:
            if self._stream is not None:
                return
            stream = None

            def callback(indata: bytes, frames: int, time: Any, status: Any) -> None:
                del frames, time
                if status:
                    self.on_error(str(status))
                payload = bytes(indata)
                self.on_frame(payload)
                try:
                    self.on_level(min(pcm16_rms(payload) * 7.0, 1.0))
                except Exception:
                    pass

            try:
                stream = sd.RawInputStream(
                    samplerate=self.SAMPLE_RATE,
                    blocksize=self.SAMPLE_RATE * self.FRAME_MS // 1000,
                    device=device,
                    channels=1,
                    dtype="int16",
                    callback=callback,
                )
                stream.start()
                self._stream = stream
            except Exception as exc:
                self._stream = None
                if stream is not None:
                    try:
                        stream.close()
                    except Exception:
                        pass
                raise AudioCaptureError(
                    f"Could not open the microphone at 16 kHz mono: {exc}"
                ) from exc

    def stop(self) -> None:
        with self._lock:
            stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
        self.on_level(0.0)
