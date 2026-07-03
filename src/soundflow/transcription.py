from __future__ import annotations

import hashlib
import json
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from soundflow.audio import AudioCapture
from soundflow.core.segmenter import EnergySegmenter, SegmenterConfig


class ModelUnavailable(RuntimeError):
    pass


class Transcriber(Protocol):
    def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str: ...


class FasterWhisperTranscriber:
    def __init__(
        self,
        model_path: Path,
        language: str = "auto",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_path = model_path
        self.language = None if language == "auto" else language
        self.device = device
        self.compute_type = compute_type
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        if not self.model_path.is_dir():
            raise ModelUnavailable(
                f"No offline model found at {self.model_path}. "
                "Choose a local faster-whisper model directory in Settings."
            )
        self._verify_manifest()
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ModelUnavailable(
                "faster-whisper is not installed. Install the project dependencies first."
            ) from exc
        self._model = WhisperModel(
            str(self.model_path),
            device=self.device,
            compute_type=self.compute_type,
            local_files_only=True,
        )
        return self._model

    def _verify_manifest(self) -> None:
        manifest_path = self.model_path / "soundflow-manifest.json"
        if not manifest_path.is_file():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest["files"]
            if not isinstance(files, dict):
                raise ValueError("files is not an object")
            for name, metadata in files.items():
                if Path(name).name != name:
                    raise ValueError(f"unsafe model filename: {name}")
                path = self.model_path / name
                expected = str(metadata["sha256"]).lower()
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != expected:
                    raise ValueError(f"checksum mismatch for {name}")
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModelUnavailable(f"Offline model integrity check failed: {exc}") from exc

    def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str:
        if sample_rate != 16_000:
            raise ValueError("The MVP transcriber expects 16 kHz PCM")
        try:
            import numpy as np
        except ImportError as exc:
            raise ModelUnavailable("NumPy is required for transcription") from exc
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._load().transcribe(
            audio,
            language=self.language,
            beam_size=5,
            condition_on_previous_text=False,
            vad_filter=True,
        )
        return " ".join(segment.text.strip() for segment in segments).strip()


class DemoTranscriber:
    """Explicit development backend; never selected without --demo."""

    def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str:
        seconds = len(pcm16) / (sample_rate * 2)
        return f"[Demo mode: captured {seconds:.1f} seconds of speech]"


@dataclass(frozen=True)
class _AudioCommand:
    kind: str
    session: int
    payload: bytes = b""


@dataclass(frozen=True)
class _InferenceCommand:
    kind: str
    session: int
    payload: bytes = b""


class DictationPipeline:
    """Capture, endpoint detection, and inference with bounded worker queues."""

    def __init__(
        self,
        transcriber: Transcriber,
        segmenter_config: SegmenterConfig,
        on_text: Callable[[str], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
        on_level: Callable[[float], None],
    ) -> None:
        self.transcriber = transcriber
        self.segmenter_config = segmenter_config
        self.on_text = on_text
        self.on_finished = on_finished
        self.on_error = on_error
        self._audio_queue: queue.Queue[_AudioCommand] = queue.Queue(maxsize=500)
        self._inference_queue: queue.Queue[_InferenceCommand] = queue.Queue(maxsize=32)
        self._session = 0
        self._running = True
        self._capture = AudioCapture(self._receive_frame, on_level, on_error)
        self._segment_thread = threading.Thread(
            target=self._segment_loop, name="soundflow-segmenter", daemon=True
        )
        self._inference_thread = threading.Thread(
            target=self._inference_loop, name="soundflow-inference", daemon=True
        )
        self._segment_thread.start()
        self._inference_thread.start()

    def start(self, device: int | None) -> None:
        self._session += 1
        self._put_audio(_AudioCommand("start", self._session))
        try:
            self._capture.start(device)
        except Exception:
            self._put_audio(_AudioCommand("stop", self._session))
            raise

    def stop(self) -> None:
        self._capture.stop()
        self._put_audio(_AudioCommand("stop", self._session))

    def close(self) -> None:
        self._capture.stop()
        self._running = False
        self._put_audio(_AudioCommand("quit", self._session))
        try:
            self._inference_queue.put_nowait(_InferenceCommand("quit", self._session))
        except queue.Full:
            pass

    def _receive_frame(self, payload: bytes) -> None:
        try:
            self._audio_queue.put_nowait(_AudioCommand("frame", self._session, payload))
        except queue.Full:
            self.on_error("Audio processing fell behind; a frame was dropped.")

    def _put_audio(self, command: _AudioCommand) -> None:
        try:
            self._audio_queue.put(command, timeout=1)
        except queue.Full:
            self.on_error("The audio queue is full.")

    def _segment_loop(self) -> None:
        segmenter = EnergySegmenter(self.segmenter_config)
        active_session = 0
        while self._running:
            command = self._audio_queue.get()
            if command.kind == "quit":
                return
            if command.kind == "start":
                active_session = command.session
                segmenter.reset()
                continue
            if command.session != active_session:
                continue
            if command.kind == "frame":
                for segment in segmenter.feed(command.payload):
                    self._inference_queue.put(
                        _InferenceCommand("segment", active_session, segment)
                    )
            elif command.kind == "stop":
                for segment in segmenter.flush():
                    self._inference_queue.put(
                        _InferenceCommand("segment", active_session, segment)
                    )
                self._inference_queue.put(_InferenceCommand("end", active_session))
                active_session = 0

    def _inference_loop(self) -> None:
        while self._running:
            command = self._inference_queue.get()
            if command.kind == "quit":
                return
            if command.kind == "end":
                self.on_finished()
                continue
            try:
                text = self.transcriber.transcribe_pcm(
                    command.payload, AudioCapture.SAMPLE_RATE
                )
                if text:
                    self.on_text(text)
            except Exception as exc:
                self.on_error(str(exc))
