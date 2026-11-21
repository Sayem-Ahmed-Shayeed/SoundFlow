from __future__ import annotations

import hashlib
import logging
import json
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from soundflow.audio import AudioCapture
from soundflow.core.segmenter import EnergySegmenter, SegmenterConfig


class ModelUnavailable(RuntimeError):
    pass


class Transcriber(Protocol):
    def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str: ...


# Languages written in one Brahmic script. When one is chosen, only that
# script, ASCII (English words, digits) and common punctuation may be written.
# Weak models otherwise write Bangla in Hindi letters, or, with Hindi
# blocked, wander into Chinese, Japanese or Cyrillic.
# Values: allowed second bytes of the E0 xx yy three-byte sequences.
_NATIVE_SCRIPT: dict[str, frozenset[int]] = {
    "bn": frozenset({0xA6, 0xA7}),  # Bengali
    "as": frozenset({0xA6, 0xA7}),
    "hi": frozenset({0xA4, 0xA5}),  # Devanagari
    "mr": frozenset({0xA4, 0xA5}),
    "ne": frozenset({0xA4, 0xA5}),
}
_DANDA_TAILS = frozenset({0xA4, 0xA5})  # E0 A5 A4/A5: । ॥, shared by both
# Urdu: keep the Arabic script away from Indic letters.
_INDIC_SECOND_BYTES = frozenset(range(0xA4, 0xAC))

LOGGER = logging.getLogger(__name__)
_MODEL_CACHE: dict[tuple[str, str, str], object] = {}
_RESOLVED_DEVICES: dict[tuple[str, str, str], str] = {}
_MODEL_LOCK = threading.Lock()
_DEVICE_LOCK = threading.Lock()
_SUPPRESS_CACHE: dict[tuple[int, str], list[int]] = {}


def _byte_decoder() -> dict[str, int]:
    """Inverse of the GPT-2 byte-to-unicode table used by Whisper's BPE vocab."""
    visible = (
        list(range(ord("!"), ord("~") + 1))
        + list(range(ord("¡"), ord("¬") + 1))
        + list(range(ord("®"), ord("ÿ") + 1))
    )
    codes = visible[:]
    extra = 0
    for byte in range(256):
        if byte not in visible:
            visible.append(byte)
            codes.append(256 + extra)
            extra += 1
    return {chr(code): byte for byte, code in zip(visible, codes)}


def _token_allowed(raw: bytes, native: frozenset[int]) -> bool:
    """Whether a token's bytes stay within ``native`` script, ASCII and punctuation."""
    def second_ok(second: int, third: int | None) -> bool:
        if second in native:
            return True
        return second == 0xA5 and (third is None or third in _DANDA_TAILS)

    n = len(raw)
    i = 0
    # Leading continuation bytes finish a character begun in the previous
    # token. Two in a row mean the first is the script-selecting byte.
    if n and 0x80 <= raw[0] <= 0xBF:
        if n >= 2 and 0x80 <= raw[1] <= 0xBF:
            if not (second_ok(raw[0], raw[1]) or raw[0] == 0x80):
                return False
            i = 2
        else:
            i = 1
    while i < n:
        b = raw[i]
        if b < 0x80:
            i += 1
        elif b == 0xE0:
            if i + 1 < n and not second_ok(raw[i + 1], raw[i + 2] if i + 2 < n else None):
                return False
            i += 3
        elif b == 0xE2:  # general punctuation: quotes, dashes, ellipsis
            if i + 1 < n and raw[i + 1] != 0x80:
                return False
            i += 3
        elif 0x80 <= b <= 0xBF:
            i += 1  # stray continuation inside a token; already judged
        else:
            return False  # Latin accents, Cyrillic, Arabic, CJK, emoji, ...
    return True


def script_suppress_tokens(vocab: dict[str, int], language: str | None) -> list[int]:
    """Token ids that would write ``language`` in a script it doesn't use."""
    language = language or ""
    native = _NATIVE_SCRIPT.get(language)
    if native is None and language != "ur":
        return []
    decoder = _byte_decoder()
    ids: list[int] = []
    for token, token_id in vocab.items():
        if token.startswith("<|"):
            continue
        try:
            raw = bytes(decoder[ch] for ch in token)
        except KeyError:
            continue
        if native is not None:
            if not _token_allowed(raw, native):
                ids.append(token_id)
        elif any(
            raw[i] == 0xE0 and i + 1 < len(raw) and raw[i + 1] in _INDIC_SECOND_BYTES
            for i in range(len(raw))
        ):
            ids.append(token_id)
    return sorted(ids)


def parse_language(value: str) -> tuple[str | None, tuple[str, ...]]:
    """Split a language setting into (forced language, auto-detect candidates).

    ``"bn"`` forces Bangla; ``"auto"`` detects freely; ``"auto:en+bn"``
    detects only between English and Bangla.
    """
    value = (value or "auto").strip().lower()
    if value == "auto":
        return None, ()
    if value.startswith("auto:"):
        candidates = tuple(c for c in value[5:].split("+") if c)
        return None, candidates
    return value, ()


def _cuda_device_count() -> int:
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:
        return 0


class FasterWhisperTranscriber:
    INTERIM_BEAM = 1
    FINAL_BEAM = 5
    PROMPT_CHARS = 220
    MAX_INTERIM_TOKENS = 200
    MAX_FINAL_TOKENS = 200

    def __init__(
        self,
        model_path: Path,
        language: str = "auto",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        self.model_path = model_path
        # "auto", "cuda" or "cpu". "auto" is resolved when the model loads.
        self.device = device
        self.compute_type = compute_type
        self._model = None
        self._active_device: str | None = None
        # A single-language model (e.g. the Bangla model) fixes the language.
        self.model_language = _model_language(model_path)
        self._session_language: str | None = None
        self._session_text = ""
        self.set_language(language)

    # -- language -------------------------------------------------------------
    def set_language(self, language: str) -> None:
        """Change the language without reloading the model."""
        self.language, self.candidates = parse_language(language)
        if self.model_language:
            self.language, self.candidates = self.model_language, ()
        self.reset_session()

    def reset_session(self) -> None:
        """Forget the detected language and context from the last dictation."""
        self._session_language = self.language
        self._session_text = ""

    def _resolve_language(self, model, audio) -> str | None:
        if self._session_language is not None:
            return self._session_language
        if not self.candidates:
            return None
        # Restricted auto-detect: pick the most likely allowed language and
        # keep it for the rest of this dictation.
        try:
            _, _, ranked = model.detect_language(audio)
        except Exception:
            return None
        allowed = [(lang, p) for lang, p in ranked if lang in self.candidates]
        if not allowed:
            return None
        return max(allowed, key=lambda item: item[1])[0]

    def _suppress(self, model, language: str | None) -> list[int]:
        key = (id(model), language or "")
        cached = _SUPPRESS_CACHE.get(key)
        if cached is None:
            try:
                vocab = model.hf_tokenizer.get_vocab()
            except Exception:
                vocab = {}
            cached = _SUPPRESS_CACHE[key] = script_suppress_tokens(vocab, language)
        # -1 keeps Whisper's default list of non-speech symbols.
        return [-1, *cached]

    # -- errors -------------------------------------------------------------------
    @property
    def active_device(self) -> str:
        """The device the loaded model runs on ("cuda" or "cpu")."""
        if self._active_device is not None:
            return self._active_device
        return "cuda" if self.device == "cuda" else "cpu"

    def _friendly_device_error(self, exc: Exception, device: str | None = None) -> str:
        detail = str(exc)
        lowered = detail.lower()
        if (device or self.device) == "cuda" and (
            "libcublas" in lowered or "libcudnn" in lowered or "libcuda" in lowered
        ):
            return (
                "GPU libraries are missing (CUDA/cuBLAS not found). "
                "Switch Processing to CPU in Preferences, Dictation, "
                "or install the NVIDIA CUDA runtime. "
                f"Details: {detail}"
            )
        if "out of memory" in lowered:
            return (
                "The GPU ran out of memory. Close GPU-heavy apps, use a smaller "
                "model, or switch Processing to CPU in Preferences, Dictation. "
                f"Details: {detail}"
            )
        return detail

    # -- model ----------------------------------------------------------------------
    def preload(self) -> None:
        """Load the model now so the first dictation starts without a pause.

        On a GPU the weights are parked in system RAM until recording starts,
        so an idle Soundflow holds no GPU memory."""
        self._load()
        self.release()

    # -- GPU residency ------------------------------------------------------------
    # Moving weights RAM <-> GPU takes 0.1-0.4 s, versus 2-4 s to load from
    # disk, so the GPU is freed after every dictation and refilled as the
    # next one starts, while the person is still speaking.
    def _on_gpu(self) -> bool:
        return self.active_device == "cuda" and self._model is not None

    def warm(self) -> None:
        """Put the model on the GPU (called as recording starts)."""
        model = self._load()
        if self._on_gpu():
            with _DEVICE_LOCK:
                inner = getattr(model, "model", None)
                if inner is not None and not getattr(inner, "model_is_loaded", True):
                    inner.load_model()

    def release(self) -> None:
        """Free GPU memory by moving the weights to system RAM."""
        if not self._on_gpu():
            return
        with _DEVICE_LOCK:
            inner = getattr(self._model, "model", None)
            if inner is not None and getattr(inner, "model_is_loaded", False):
                try:
                    inner.unload_model(to_cpu=True)
                except Exception:
                    pass  # keep it on the GPU rather than fail

    def _device_candidates(self) -> tuple[str, ...]:
        if self.device == "auto":
            # Try the GPU first; a GPU that is present but fails to load
            # (missing CUDA libraries, out of memory) falls back to the CPU.
            return ("cuda", "cpu") if _cuda_device_count() > 0 else ("cpu",)
        return (self.device,)

    def _load(self):
        if self._model is not None:
            return self._model
        requested = self.device
        key = (str(self.model_path.resolve()), requested, self.compute_type)
        with _MODEL_LOCK:
            cached = _MODEL_CACHE.get(key)
            if cached is not None:
                self._model = cached
                self._active_device = _RESOLVED_DEVICES.get(key, requested)
                return cached
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
            candidates = self._device_candidates()
            model = None
            for position, device in enumerate(candidates):
                try:
                    model = WhisperModel(
                        str(self.model_path),
                        device=device,
                        compute_type=self.compute_type,
                        local_files_only=True,
                    )
                except Exception as exc:
                    if isinstance(exc, ModelUnavailable):
                        raise
                    if position + 1 < len(candidates):
                        LOGGER.warning(
                            "Could not load the model on %s, using %s instead: %s",
                            device,
                            candidates[position + 1],
                            exc,
                        )
                        continue
                    raise ModelUnavailable(
                        self._friendly_device_error(exc, device)
                    ) from exc
                self._active_device = device
                break
            # One model per path/device: a language or settings change reuses it.
            _MODEL_CACHE.clear()
            _RESOLVED_DEVICES.clear()
            _MODEL_CACHE[key] = model
            _RESOLVED_DEVICES[key] = self._active_device
            self._model = model
            return model

    def _verify_manifest(self) -> None:
        manifest_path = self.model_path / "soundflow-manifest.json"
        if not manifest_path.is_file():
            return
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            files = manifest["files"]
            if not isinstance(files, dict):
                raise ValueError("files is not an object")
            stamp = {}
            for name in files:
                if Path(name).name != name:
                    raise ValueError(f"unsafe model filename: {name}")
                info = (self.model_path / name).stat()
                stamp[name] = [info.st_size, info.st_mtime_ns]
            if _verified_stamp(self.model_path) == stamp:
                return  # Same files as the last successful check; skip hashing.
            for name, metadata in files.items():
                path = self.model_path / name
                expected = str(metadata["sha256"]).lower()
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != expected:
                    raise ValueError(f"checksum mismatch for {name}")
            _save_verified_stamp(self.model_path, stamp)
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ModelUnavailable(f"Offline model integrity check failed: {exc}") from exc

    # -- decoding -------------------------------------------------------------------
    def _decode(self, pcm16: bytes, sample_rate: int, *, final: bool) -> str:
        if sample_rate != 16_000:
            raise ValueError("The MVP transcriber expects 16 kHz PCM")
        try:
            import numpy as np
        except ImportError as exc:
            raise ModelUnavailable("NumPy is required for transcription") from exc
        audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768.0
        try:
            model = self._load()
            self.warm()
            language = self._resolve_language(model, audio)
            options = dict(
                language=language,
                beam_size=self.FINAL_BEAM if final else self.INTERIM_BEAM,
                condition_on_previous_text=False,
                # Earlier text from this dictation keeps spelling and script
                # consistent across phrases.
                # Display-only previews skip it: on unclear audio the model
                # tends to echo the prompt back.
                initial_prompt=(self._session_text or None) if final else None,
                suppress_tokens=self._suppress(model, language),
                vad_filter=final,
                # Bound GPU memory: Whisper's fallback otherwise samples five
                # candidates up to 448 tokens each, which can exhaust a 2 GB GPU.
                best_of=2,
                max_new_tokens=self.MAX_FINAL_TOKENS,
            )
            if self.model_language:
                # Fine-tuned models don't reliably predict timestamp tokens,
                # and default VAD padding clips the first word.
                options.update(
                    without_timestamps=True,
                    vad_parameters={"speech_pad_ms": 500, "min_silence_duration_ms": 700},
                )
            if not final:
                # Live preview: one greedy pass, no temperature retries, and a
                # token budget tied to the audio length so noise can't stall
                # the final transcript queued behind it.
                seconds = len(audio) / 16_000
                options.update(
                    temperature=0.0,
                    without_timestamps=True,
                    # Whisper's limit is 448 tokens including the prompt
                    # (at most 223 + 4 start tokens), so stay under 448 - 227.
                    max_new_tokens=min(self.MAX_INTERIM_TOKENS, int(24 + seconds * 40)),
                )
            try:
                segments, info = model.transcribe(audio, **options)
                text = " ".join(segment.text.strip() for segment in segments).strip()
            except RuntimeError as exc:
                if "out of memory" not in str(exc).lower():
                    raise
                # Retry once with the smallest search instead of failing.
                options.update(beam_size=1, temperature=0.0)
                segments, info = model.transcribe(audio, **options)
                text = " ".join(segment.text.strip() for segment in segments).strip()
        except Exception as exc:
            if isinstance(exc, ModelUnavailable):
                raise
            raise ModelUnavailable(self._friendly_device_error(exc)) from exc
        if not final and (
            _looks_degenerate(text) or sum(ch.isalpha() for ch in text) < 2
        ):
            return ""  # loops and lone fragments like 'ত্' aren't worth showing
        if final and text:
            if self._session_language is None:
                if self.candidates:
                    self._session_language = language
                elif getattr(info, "language_probability", 0) >= 0.6:
                    # Lock a confident detection for the rest of the dictation.
                    self._session_language = getattr(info, "language", None)
            self._session_text = (self._session_text + " " + text)[-self.PROMPT_CHARS:].strip()
        return text

    # The Bangla model writes ~0.7 tokens per character, so a long phrase
    # can overflow Whisper's 224-token output; decode it in shorter pieces.
    SINGLE_LANGUAGE_MAX_S = 12.0

    def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str:
        if not self.model_language:
            return self._decode(pcm16, sample_rate, final=True)
        pieces = [
            self._decode(chunk, sample_rate, final=True)
            for chunk in split_at_pauses(pcm16, sample_rate, self.SINGLE_LANGUAGE_MAX_S)
        ]
        return " ".join(p for p in pieces if p).strip()

    def transcribe_interim(self, pcm16: bytes, sample_rate: int) -> str:
        """Fast display-only decode: no VAD gating, greedy search."""
        return self._decode(pcm16, sample_rate, final=False)


def _model_language(model_path: Path) -> str | None:
    """The fixed language of a downloaded single-language model, if any."""
    try:
        manifest = json.loads((Path(model_path) / "soundflow-manifest.json").read_text("utf-8"))
        from soundflow.models.catalog import model_spec

        return model_spec(str(manifest.get("model", ""))).language
    except Exception:
        return None


def split_at_pauses(pcm16: bytes, sample_rate: int, max_s: float) -> list[bytes]:
    """Split 16-bit PCM into pieces of at most ``max_s`` seconds, cutting at
    the quietest 100 ms in the last third of each piece so words stay whole."""
    import numpy as np

    samples = np.frombuffer(pcm16, dtype=np.int16)
    limit = int(max_s * sample_rate)
    if len(samples) <= limit:
        return [pcm16]
    frame = sample_rate // 10
    pieces: list[bytes] = []
    start = 0
    while len(samples) - start > limit:
        lo, hi = start + limit * 2 // 3, start + limit
        window = samples[lo:hi].astype(np.float32)
        frames = len(window) // frame
        energy = (window[: frames * frame].reshape(frames, frame) ** 2).mean(axis=1)
        cut = lo + int(energy.argmin()) * frame + frame // 2
        pieces.append(samples[start:cut].tobytes())
        start = cut
    pieces.append(samples[start:].tobytes())
    return pieces


def _looks_degenerate(text: str) -> bool:
    """True for decoder loops such as 'ༀༀༀༀ' or 'na na na na na na'."""
    if not text:
        return False
    run = 1
    for previous, current in zip(text, text[1:]):
        run = run + 1 if current == previous and not current.isspace() else 1
        if run >= 6:
            return True
    words = text.split()
    if len(words) >= 8 and len(set(words)) <= len(words) // 4:
        return True
    # A short chunk repeated back to back: 'বাসবাসবাসবাস', 'la la la la'.
    compact = "".join(words)
    for size in range(1, 9):
        for start in range(0, len(compact) - size * 4 + 1):
            unit = compact[start : start + size]
            if compact.startswith(unit * 4, start):
                return True
    return False


def _stamp_path():
    from soundflow.core.settings import config_directory

    return config_directory() / "model-checks.json"


def _verified_stamp(model_path: Path) -> dict | None:
    try:
        data = json.loads(_stamp_path().read_text(encoding="utf-8"))
        return data.get(str(model_path.resolve()))
    except (OSError, ValueError, AttributeError):
        return None


def _save_verified_stamp(model_path: Path, stamp: dict) -> None:
    path = _stamp_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data[str(model_path.resolve())] = stamp
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")
    except OSError:
        pass


class DemoTranscriber:
    """Explicit development backend; never selected without --demo."""

    def transcribe_pcm(self, pcm16: bytes, sample_rate: int) -> str:
        seconds = len(pcm16) / (sample_rate * 2)
        return f"[Demo mode: captured {seconds:.1f} seconds of speech]"

    def transcribe_interim(self, pcm16: bytes, sample_rate: int) -> str:
        seconds = len(pcm16) / (sample_rate * 2)
        return f"[Demo mode: listening… {seconds:.0f}s]"


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

    INTERIM_EVERY_S = 0.7
    INTERIM_MIN_S = 0.5

    def __init__(
        self,
        transcriber: Transcriber,
        segmenter_config: SegmenterConfig,
        on_text: Callable[[str], None],
        on_finished: Callable[[], None],
        on_error: Callable[[str], None],
        on_level: Callable[[float], None],
        on_interim: Callable[[str], None] | None = None,
        on_audio: Callable[[bytes], None] | None = None,
    ) -> None:
        self.transcriber = transcriber
        # Raw 16 kHz mono PCM for the spectrogram; called on the audio thread.
        self.on_audio = on_audio
        self.segmenter_config = segmenter_config
        self.on_text = on_text
        self.on_finished = on_finished
        self.on_error = on_error
        self.on_interim = on_interim
        self._interim_busy = False
        self._last_interim_sent = b""
        self._last_interim_time = 0.0
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

    _warm_pending = False

    def start(self, device: int | None) -> None:
        self._session += 1
        self._interim_busy = False
        self._last_interim_sent = b""
        self._last_interim_time = 0.0
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
        if self.on_audio is not None:
            try:
                self.on_audio(payload)
            except Exception:  # noqa: BLE001 - drawing must never stop capture
                pass

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
                # Refill the GPU while the person starts speaking.
                self._warm_pending = True
                self._inference_queue.put(_InferenceCommand("warm", active_session))
                continue
            if command.session != active_session:
                continue
            if command.kind == "frame":
                for segment in segmenter.feed(command.payload):
                    self._inference_queue.put(
                        _InferenceCommand("segment", active_session, segment)
                    )
                self._maybe_queue_interim(active_session, segmenter)
            elif command.kind == "stop":
                for segment in segmenter.flush():
                    self._inference_queue.put(
                        _InferenceCommand("segment", active_session, segment)
                    )
                self._inference_queue.put(_InferenceCommand("end", active_session))
                active_session = 0

    def _maybe_queue_interim(self, session: int, segmenter: EnergySegmenter) -> None:
        if self.on_interim is None:
            return
        if session <= 0 or self._interim_busy:
            return
        now = time.monotonic()
        if now - self._last_interim_time < self.INTERIM_EVERY_S:
            return
        # Skip while real work is queued; a pending GPU warm-up doesn't count.
        if self._inference_queue.qsize() > (1 if self._warm_pending else 0):
            return
        snapshot = segmenter.snapshot()
        min_bytes = int(self.INTERIM_MIN_S * AudioCapture.SAMPLE_RATE * 2)
        if len(snapshot) < min_bytes or snapshot == self._last_interim_sent:
            return
        try:
            self._inference_queue.put_nowait(
                _InferenceCommand("interim", session, snapshot)
            )
        except queue.Full:
            return
        self._interim_busy = True
        self._last_interim_sent = snapshot
        self._last_interim_time = now

    def _inference_loop(self) -> None:
        decoded_session = 0
        while self._running:
            command = self._inference_queue.get()
            if command.kind == "quit":
                return
            if command.session != decoded_session and command.kind != "end":
                # First audio of a new dictation: forget the previous one's
                # detected language and context.
                decoded_session = command.session
                reset = getattr(self.transcriber, "reset_session", None)
                if callable(reset):
                    reset()
            if command.kind == "end":
                self.on_finished()
                # Text is delivered; now give the GPU memory back.
                release = getattr(self.transcriber, "release", None)
                if callable(release) and self._inference_queue.empty():
                    try:
                        release()
                    except Exception:
                        pass
                continue
            if command.kind == "warm":
                self._warm_pending = False
                warm = getattr(self.transcriber, "warm", None)
                if callable(warm):
                    try:
                        warm()
                    except Exception:
                        pass  # a real error surfaces on the first decode
                continue

            if command.kind == "interim":
                self._interim_busy = False
                if command.session != self._session:
                    continue
                try:
                    quick = getattr(self.transcriber, "transcribe_interim", None)
                    if callable(quick):
                        text = quick(command.payload, AudioCapture.SAMPLE_RATE)
                    else:
                        text = self.transcriber.transcribe_pcm(
                            command.payload, AudioCapture.SAMPLE_RATE
                        )
                    if text and self.on_interim is not None:
                        self.on_interim(text)
                except Exception:
                    pass
                continue
            try:
                text = self.transcriber.transcribe_pcm(
                    command.payload, AudioCapture.SAMPLE_RATE
                )
                if text:
                    self.on_text(text)
            except Exception as exc:
                self.on_error(str(exc))
