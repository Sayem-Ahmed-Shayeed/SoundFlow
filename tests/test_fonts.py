import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFont, QFontDatabase, QFontInfo
from PySide6.QtWidgets import QApplication

from soundflow.design.fonts import (
    BODY_FONT,
    COVER_FONT,
    DISPLAY_FONT,
    HOME_DISPLAY_FONT,
    MONO_FONT,
    register_application_fonts,
    tabular,
)


class FontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_figtree_and_eb_garamond_are_the_bundled_fonts(self):
        font_ids = register_application_fonts()

        self.assertEqual(BODY_FONT, "Figtree")
        self.assertEqual(DISPLAY_FONT, "EB Garamond")
        self.assertEqual(HOME_DISPLAY_FONT, "EB Garamond")
        self.assertEqual(MONO_FONT, "Figtree")
        self.assertEqual(len(font_ids), 12)
        families = QFontDatabase.families()
        for family in ("Figtree", "EB Garamond", "Noto Sans Bengali"):
            self.assertIn(family, families)
        # Real weights, not synthesized bold.
        self.assertTrue(
            {"Regular", "Medium", "SemiBold", "Bold"} <= set(QFontDatabase.styles("Figtree"))
        )
        self.assertTrue({"Regular", "Medium", "Italic"} <= set(QFontDatabase.styles("EB Garamond")))

    def test_bodoni_moda_is_registered_for_the_sign_in_cover(self):
        register_application_fonts()
        self.assertEqual(COVER_FONT, "Bodoni Moda")
        self.assertIn("Bodoni Moda", QFontDatabase.families())
        italic = QFont(COVER_FONT)
        italic.setItalic(True)
        self.assertEqual(QFontInfo(italic).family(), "Bodoni Moda")
        self.assertTrue(QFontInfo(italic).italic())

    def test_bangla_falls_back_to_noto_sans_bengali(self):
        register_application_fonts()
        body = [name.lower() for name in QFont.substitutes(BODY_FONT)]
        self.assertEqual(body[0], "noto sans bengali")
        # Headings pair Bangla with a serif so it matches EB Garamond.
        display = [name.lower() for name in QFont.substitutes(DISPLAY_FONT)]
        self.assertEqual(display[0], "noto serif bengali")
        self.assertIn("Noto Serif Bengali", QFontDatabase.families())

    def test_tabular_turns_on_equal_width_digits(self):
        font = tabular(QFont(BODY_FONT))
        self.assertEqual(font.featureValue(QFont.Tag("tnum")), 1)

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
                "FIGTREE-OFL.txt",
                "Figtree-Regular.ttf",
                "Figtree-Medium.ttf",
                "Figtree-SemiBold.ttf",
                "Figtree-Bold.ttf",
                "EBGARAMOND-OFL.txt",
                "EBGaramond-Regular.ttf",
                "EBGaramond-Medium.ttf",
                "EBGaramond-Italic.ttf",
                "NOTO-SANS-BENGALI-OFL.txt",
                "NotoSansBengali-Variable.ttf",
                "NOTO-SERIF-BENGALI-OFL.txt",
                "NotoSerifBengali-Regular.ttf",
                "NotoSerifBengali-Medium.ttf",
                "BODONI-MODA-OFL.txt",
                "BodoniModa-Medium.ttf",
                "BodoniModa-Italic.ttf",
            },
        )


if __name__ == "__main__":
    unittest.main()
