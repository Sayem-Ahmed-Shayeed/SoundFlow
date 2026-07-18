import tempfile
import unittest
from pathlib import Path

from soundflow.models.catalog import MODEL_CATALOG, managed_model_path, model_spec


class ModelCatalogTests(unittest.TestCase):
    def test_catalog_is_curated_and_small_is_recommended(self):
        self.assertEqual(
            [item.model_id for item in MODEL_CATALOG],
            ["tiny", "base", "small", "medium", "large-v3-turbo"],
        )
        self.assertEqual(
            [item.model_id for item in MODEL_CATALOG if item.recommended],
            ["small"],
        )
        self.assertEqual(
            model_spec("large-v3-turbo").repo_id,
            "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
        )
        self.assertEqual(
            [item.download_size for item in MODEL_CATALOG],
            ["78 MB", "148 MB", "486 MB", "1.53 GB", "1.62 GB"],
        )

    def test_managed_path_is_catalog_derived(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(
                managed_model_path(model_spec("tiny"), root),
                root / "faster-whisper-tiny",
            )

    def test_unknown_model_is_rejected(self):
        with self.assertRaisesRegex(KeyError, "unknown Whisper model"):
            model_spec("large")
