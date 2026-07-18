import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

from soundflow.design.fonts import (
    BODY_FONT,
    DISPLAY_FONT,
    HOME_DISPLAY_FONT,
    MONO_FONT,
    register_application_fonts,
)


class FontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_geist_is_the_bundled_application_font(self):
        font_ids = register_application_fonts()

        self.assertEqual(BODY_FONT, "Geist")
        self.assertEqual(DISPLAY_FONT, "Geist")
        self.assertEqual(HOME_DISPLAY_FONT, "Outfit")
        self.assertEqual(MONO_FONT, "Geist Mono")
        self.assertEqual(len(font_ids), 7)
        self.assertIn("Geist", QFontDatabase.families())
        self.assertIn("Geist Mono", QFontDatabase.families())
        self.assertIn("Outfit", QFontDatabase.families())

    def test_only_approved_font_assets_are_bundled(self):
        font_dir = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "soundflow"
            / "assets"
            / "fonts"
        )
        names = {path.name for path in font_dir.iterdir()}

        self.assertEqual(
            names,
            {
                "GEIST-OFL.txt",
                "Geist-Regular.ttf",
                "Geist-Medium.ttf",
                "Geist-SemiBold.ttf",
                "Geist-Bold.ttf",
                "GeistMono-Regular.ttf",
                "GeistMono-Medium.ttf",
                "OUTFIT-OFL.txt",
                "Outfit-Variable.ttf",
            },
        )
        self.assertFalse(any("Roboto" in name for name in names))


if __name__ == "__main__":
    unittest.main()
