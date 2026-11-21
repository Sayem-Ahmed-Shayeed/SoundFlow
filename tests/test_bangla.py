import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from soundflow.transcription import (
    FasterWhisperTranscriber,
    _byte_decoder,
    script_suppress_tokens,
    split_at_pauses,
)


def _vocab(*texts: str) -> dict[str, int]:
    """A tiny BPE-style vocab: one token per text, in Whisper's byte alphabet."""
    encoder = {byte: ch for ch, byte in _byte_decoder().items()}
    return {
        "".join(encoder[b] for b in text.encode("utf-8")): i
        for i, text in enumerate(texts)
    }


class ScriptSuppressionTests(unittest.TestCase):
    def test_bangla_allows_only_bengali_ascii_and_punctuation(self):
        texts = ["আমি", " বাংলা", "।", " hello", " 3", "’", "हिंदी", " 就是", " или", "クロ"]
        blocked = set(script_suppress_tokens(_vocab(*texts), "bn"))
        self.assertEqual(sorted(blocked), [6, 7, 8, 9])

    def test_hindi_blocks_bengali(self):
        blocked = set(script_suppress_tokens(_vocab("আমি", "हिंदी", "।"), "hi"))
        self.assertEqual(blocked, {0})

    def test_english_and_auto_block_nothing(self):
        vocab = _vocab("আমি", "हिंदी")
        self.assertEqual(script_suppress_tokens(vocab, "en"), [])
        self.assertEqual(script_suppress_tokens(vocab, None), [])


class PreviewFilterTests(unittest.TestCase):
    def test_loops_are_hidden_but_real_text_is_not(self):
        from soundflow.transcription import _looks_degenerate

        for loop in ["কিনবাসবাসবাসবাসবাস", "la la la la la", "ༀༀༀༀༀༀ"]:
            self.assertTrue(_looks_degenerate(loop), loop)
        for text in ["আমি আজ বাজারে যাব এবং কিছু সবজি কিনব।", "ha ha ha", "mississippi"]:
            self.assertFalse(_looks_degenerate(text), text)

    def test_interim_token_budget_fits_whisper(self):
        # 448 tokens total; the prompt can take 223 plus 4 start tokens.
        self.assertLessEqual(FasterWhisperTranscriber.MAX_INTERIM_TOKENS, 448 - 227)


class SplitTests(unittest.TestCase):
    def test_short_audio_is_one_piece(self):
        pcm = np.zeros(16_000 * 5, dtype=np.int16).tobytes()
        self.assertEqual(split_at_pauses(pcm, 16_000, 12), [pcm])

    def test_long_audio_is_cut_at_the_pause(self):
        rate = 16_000
        loud = (np.sin(np.arange(rate * 10) * 0.3) * 8000).astype(np.int16)
        pause = np.zeros(rate // 2, dtype=np.int16)
        pcm = np.concatenate([loud, pause, loud]).tobytes()
        pieces = split_at_pauses(pcm, rate, 12)
        self.assertEqual(sum(len(p) for p in pieces), len(pcm))
        self.assertTrue(all(len(p) <= 12 * rate * 2 for p in pieces))
        first_end = len(pieces[0]) // 2
        self.assertTrue(rate * 10 <= first_end <= rate * 10 + rate // 2)


class BanglaModelTests(unittest.TestCase):
    def test_bangla_model_forces_bangla(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "soundflow-manifest.json").write_text(
                json.dumps({"model": "bangla-medium", "files": {}})
            )
            transcriber = FasterWhisperTranscriber(path, language="auto:en+bn")
            self.assertEqual((transcriber.language, transcriber.candidates), ("bn", ()))
            transcriber.set_language("en")
            self.assertEqual(transcriber.language, "bn")

    def test_multilingual_model_keeps_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            transcriber = FasterWhisperTranscriber(Path(directory), language="auto:en+bn")
            self.assertEqual(transcriber.candidates, ("en", "bn"))


if __name__ == "__main__":
    unittest.main()
