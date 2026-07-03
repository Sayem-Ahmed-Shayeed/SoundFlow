import unittest

from soundflow.hotkeys import (
    GlobalHotkeys,
    PortalGlobalHotkeys,
    canonical_hotkey,
    display_hotkey,
    parse_hotkey,
    portal_trigger,
)


class HotkeyTests(unittest.TestCase):
    def test_two_key_shortcut(self):
        self.assertEqual(parse_hotkey("ctrl+space"), frozenset({"ctrl", "space"}))

    def test_three_key_shortcut(self):
        self.assertEqual(
            parse_hotkey("ctrl+alt+space"),
            frozenset({"ctrl", "alt", "space"}),
        )
        self.assertEqual(canonical_hotkey("alt+ctrl+space"), "ctrl+alt+space")
        self.assertEqual(
            display_hotkey("ctrl+alt+space"), "Ctrl + Alt + SPACE"
        )

    def test_rejects_modifier_only_and_malformed_shortcuts(self):
        invalid = (
            "ctrl+alt",
            "ctrl++space",
            "ctrl+ctrl+space",
            "ctrl+space+d",
            "ctrl+mouse4",
        )
        for shortcut in invalid:
            with self.subTest(shortcut=shortcut), self.assertRaises(ValueError):
                parse_hotkey(shortcut)

    def test_portal_trigger_uses_xdg_format(self):
        self.assertEqual(portal_trigger("ctrl+space"), "CTRL+space")
        self.assertEqual(
            portal_trigger("ctrl+alt+space"), "CTRL+ALT+space"
        )
        self.assertEqual(portal_trigger("cmd+r"), "LOGO+r")
        self.assertEqual(portal_trigger("shift+tab"), "SHIFT+Tab")

    def test_three_key_press_and_release_callbacks(self):
        events: list[str] = []
        hotkey = GlobalHotkeys(
            "ctrl+alt+space",
            lambda: events.append("down"),
            lambda: events.append("up"),
        )
        hotkey._on_press("Key.ctrl_l")
        hotkey._on_press("Key.alt_l")
        self.assertEqual(events, [])
        hotkey._on_press("' '")
        self.assertEqual(events, ["down"])
        hotkey._on_release("' '")
        self.assertEqual(events, ["down", "up"])

    def test_portal_ignores_repeated_activation_and_release(self):
        events: list[str] = []
        hotkey = PortalGlobalHotkeys(
            "ctrl+alt+space",
            lambda: events.append("down"),
            lambda: events.append("up"),
        )
        hotkey._session_handle = "/org/freedesktop/portal/session/soundflow"

        for _ in range(12):
            hotkey._handle_shortcut_event(
                "Activated",
                hotkey._session_handle,
                "push_to_talk",
            )
        self.assertEqual(events, ["down"])

        for _ in range(3):
            hotkey._handle_shortcut_event(
                "Deactivated",
                hotkey._session_handle,
                "push_to_talk",
            )
        self.assertEqual(events, ["down", "up"])

    def test_portal_stop_releases_an_active_shortcut_once(self):
        events: list[str] = []
        hotkey = PortalGlobalHotkeys(
            "ctrl+alt+space",
            lambda: events.append("down"),
            lambda: events.append("up"),
        )
        hotkey._session_handle = "/org/freedesktop/portal/session/soundflow"
        hotkey._handle_shortcut_event(
            "Activated",
            hotkey._session_handle,
            "push_to_talk",
        )

        hotkey.stop()
        hotkey.stop()

        self.assertEqual(events, ["down", "up"])


if __name__ == "__main__":
    unittest.main()
