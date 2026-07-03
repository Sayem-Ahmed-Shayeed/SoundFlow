import unittest

from soundflow.hotkeys import parse_hotkey, portal_trigger


class HotkeyTests(unittest.TestCase):
    def test_two_key_shortcut(self):
        self.assertEqual(parse_hotkey("ctrl+space"), frozenset({"ctrl", "space"}))

    def test_rejects_three_key_shortcut(self):
        with self.assertRaisesRegex(ValueError, "exactly two"):
            parse_hotkey("ctrl+alt+space")

    def test_portal_trigger_uses_xdg_format(self):
        self.assertEqual(portal_trigger("ctrl+space"), "CTRL+space")
        self.assertEqual(portal_trigger("cmd+r"), "LOGO+r")


if __name__ == "__main__":
    unittest.main()
