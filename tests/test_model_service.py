import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from soundflow.models import ModelDownloadCancelled, ModelManagerError, ModelService
from soundflow.models import service as model_service


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
                cancel_event.set()

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

    def test_cancel_at_verifying_never_promotes_partial_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / "faster-whisper-base"
            final.mkdir()
            marker = final / "active-custom-marker.txt"
            marker.write_text("keep", encoding="utf-8")
            cancel = threading.Event()

            def downloader(spec, target, progress, cancel_event):
                valid_model(target)

            def progress(phase, value):
                del value
                if phase == "Verifying":
                    cancel.set()

            service = ModelService(root=root, downloader=downloader)
            with self.assertRaises(ModelDownloadCancelled):
                service.install(
                    "base",
                    progress=progress,
                    cancel_event=cancel,
                )

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertFalse((root / "faster-whisper-base.partial").exists())
            self.assertFalse((final / "model.bin").exists())

    def test_cancel_after_manifest_keeps_previous_target_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / "faster-whisper-base"
            final.mkdir()
            marker = final / "active-custom-marker.txt"
            marker.write_text("keep", encoding="utf-8")
            cancel = threading.Event()

            def downloader(spec, target, progress, cancel_event):
                valid_model(target)

            original_write_manifest = model_service._write_manifest

            def write_manifest_then_cancel(path, model_id):
                original_write_manifest(path, model_id)
                cancel.set()

            service = ModelService(root=root, downloader=downloader)
            with patch.object(
                model_service,
                "_write_manifest",
                side_effect=write_manifest_then_cancel,
            ):
                with self.assertRaises(ModelDownloadCancelled):
                    service.install(
                        "base",
                        progress=lambda *_: None,
                        cancel_event=cancel,
                    )

            self.assertEqual(marker.read_text(encoding="utf-8"), "keep")
            self.assertFalse((root / "faster-whisper-base.partial").exists())
            self.assertFalse((final / "model.bin").exists())

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

    def test_delete_refuses_managed_parent_of_active_custom_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "faster-whisper-tiny"
            valid_model(target)
            active = target / "custom-active"
            valid_model(active)

            service = ModelService(root=root)
            with self.assertRaisesRegex(ModelManagerError, "active"):
                service.delete("tiny", active_path=active)

            self.assertTrue((target / "model.bin").is_file())
            self.assertTrue((active / "model.bin").is_file())

    def test_delete_refuses_managed_parent_containing_active_symlink_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "models"
            target = root / "faster-whisper-tiny"
            valid_model(target)
            external = Path(directory) / "external-active"
            valid_model(external)
            alias = target / "active-alias"
            alias.symlink_to(external, target_is_directory=True)

            service = ModelService(root=root)
            with self.assertRaisesRegex(ModelManagerError, "active"):
                service.delete("tiny", active_path=alias)

            self.assertTrue((target / "model.bin").is_file())
            self.assertTrue(alias.is_symlink())
            self.assertTrue((external / "model.bin").is_file())

    def test_delete_rejects_symlinked_catalog_entry_without_deleting_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            custom = root / "custom-model"
            valid_model(custom)
            target = root / "faster-whisper-tiny"
            target.symlink_to(custom, target_is_directory=True)

            service = ModelService(root=root)
            with self.assertRaisesRegex(ModelManagerError, "managed models"):
                service.delete("tiny", active_path=root / "faster-whisper-small")

            self.assertTrue(target.is_symlink())
            self.assertTrue((custom / "model.bin").is_file())

    def test_install_restores_invalid_existing_directory_when_promotion_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / "faster-whisper-base"
            final.mkdir()
            marker = final / "keep-me.txt"
            marker.write_text("previous content", encoding="utf-8")

            def downloader(spec, target, progress, cancel_event):
                valid_model(target)

            original_replace = Path.replace

            def fail_partial_promotion(source, target):
                if source.name.endswith(".partial"):
                    raise OSError("simulated promotion failure")
                return original_replace(source, target)

            service = ModelService(root=root, downloader=downloader)
            with patch.object(Path, "replace", new=fail_partial_promotion):
                with self.assertRaisesRegex(ModelManagerError, "promotion failure"):
                    service.install("base", progress=lambda *_: None)

            self.assertEqual(marker.read_text(encoding="utf-8"), "previous content")
            self.assertFalse((root / "faster-whisper-base.partial").exists())
            self.assertEqual(list(root.glob("faster-whisper-base.backup-*")), [])

    def test_install_does_not_overwrite_valid_existing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            final = root / "faster-whisper-medium"
            valid_model(final)
            (final / "model.bin").write_bytes(b"existing weights")

            def downloader(spec, target, progress, cancel_event):
                self.fail("downloader must not run for an installed valid model")

            events = []
            service = ModelService(root=root, downloader=downloader)
            installed = service.install(
                "medium",
                progress=lambda phase, value: events.append((phase, value)),
            )

            self.assertEqual(installed, final)
            self.assertEqual((final / "model.bin").read_bytes(), b"existing weights")
            self.assertEqual(events[-1], ("Ready", 100))
