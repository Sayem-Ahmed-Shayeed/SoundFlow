import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from soundflow.transcription import FasterWhisperTranscriber, ModelUnavailable


class ModelIntegrityTests(unittest.TestCase):
    def test_valid_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b"model payload"
            (root / "model.bin").write_bytes(payload)
            manifest = {
                "files": {
                    "model.bin": {
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "bytes": len(payload),
                    }
                }
            }
            (root / "soundflow-manifest.json").write_text(json.dumps(manifest))
            FasterWhisperTranscriber(root)._verify_manifest()

    def test_corrupt_model_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "model.bin").write_bytes(b"changed")
            manifest = {"files": {"model.bin": {"sha256": "0" * 64}}}
            (root / "soundflow-manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ModelUnavailable, "checksum mismatch"):
                FasterWhisperTranscriber(root)._verify_manifest()


if __name__ == "__main__":
    unittest.main()

