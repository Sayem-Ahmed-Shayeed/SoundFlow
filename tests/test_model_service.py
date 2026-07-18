import json
import tempfile
import threading
import unittest
from pathlib import Path

from soundflow.models import ModelDownloadCancelled, ModelManagerError, ModelService


def valid_model(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "model.bin").write_bytes(b"weights")
    (target / "config.json").write_text("{}", encoding="utf-8")
    (target / "tokenizer.json").write_text("{}", encoding="utf-8")


class ModelServiceTests(unittest.TestCase):
    def test_install_manifests_and_promotes_partial_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            events = []

            def downloader(spec, target, progress, cancel_event):
                self.assertEqual(spec.model_id, "tiny")
                self.assertTrue(target.name.endswith(".partial"))
                valid_model(target)
                progress("Downloading", 80)

            service = ModelService(root=root, downloader=downloader)
            installed = service.install(
                "tiny",
                progress=lambda phase, value: events.append((phase, value)),
                cancel_event=threading.Event(),
            )
            self.assertEqual(installed, root / "faster-whisper-tiny")
            self.assertFalse((root / "faster-whisper-tiny.partial").exists())
            manifest = json.loads(
                (installed / "soundflow-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["model"], "tiny")
            self.assertIn("model.bin", manifest["files"])
            self.assertEqual(events[-1], ("Ready", 100))

    def test_cancel_and_validation_failure_clean_partial_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def cancelled(spec, target, progress, cancel_event):
                target.mkdir(parents=True)
                (target / "partial.bin").write_bytes(b"partial")
                raise ModelDownloadCancelled("Download cancelled")

            service = ModelService(root=root, downloader=cancelled)
            with self.assertRaises(ModelDownloadCancelled):
                service.install("base", progress=lambda *_: None)
            self.assertFalse((root / "faster-whisper-base.partial").exists())

            def incomplete(spec, target, progress, cancel_event):
                target.mkdir(parents=True)
                (target / "config.json").write_text("{}", encoding="utf-8")

            service = ModelService(root=root, downloader=incomplete)
            with self.assertRaisesRegex(ModelManagerError, "model.bin"):
                service.install("medium", progress=lambda *_: None)
            self.assertFalse((root / "faster-whisper-medium.partial").exists())

    def test_delete_refuses_active_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "faster-whisper-tiny"
            valid_model(target)
            service = ModelService(root=root)
            with self.assertRaisesRegex(ModelManagerError, "active"):
                service.delete("tiny", active_path=target)
            service.delete("tiny", active_path=root / "faster-whisper-small")
            self.assertFalse(target.exists())
