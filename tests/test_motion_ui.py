import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import QAbstractAnimation, QCoreApplication, QEvent
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.design.spacing import ANIMATION_NORMAL
    from soundflow.ui import MainWindow
    from soundflow.ui.pages import DictationPage
    from soundflow.ui.widgets import StatusBar, WaveformRing

    HAS_QT = True
except ImportError:
    HAS_QT = False


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class MotionUiTests(unittest.TestCase):
    _windows = []

    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])
        cls.application.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        windows = list(self._windows)
        self._windows.clear()
        for window in windows:
            window.no_hotkeys = True
        self.application.processEvents()
        for window in windows:
            window.shutdown()
            window.hide()
        self.application.processEvents()
        for window in windows:
            window.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    def test_navigation_uses_a_short_fade_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            window.show()
            self.application.processEvents()

            window.navigate("history")

            self.assertEqual(window.pages.currentWidget(), window.history_page)
            self.assertEqual(window._page_animation.duration(), ANIMATION_NORMAL)
            self.assertEqual(
                window._page_animation.state(),
                QAbstractAnimation.State.Running,
            )

    def test_navigation_remains_safe_after_the_previous_fade_finishes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            window.show()
            self.application.processEvents()

            window.navigate("history")
            QTest.qWait(ANIMATION_NORMAL + 60)
            window.navigate("preferences")

            self.assertEqual(
                window.pages.currentWidget(), window.preferences_page
            )

    def test_status_dot_pulses_only_for_active_work(self):
        status = StatusBar()
        status.set_status("Listening", "recording")
        self.assertEqual(
            status._pulse_animation.state(),
            QAbstractAnimation.State.Running,
        )
        status.set_status("System Ready", "ready")
        self.assertEqual(
            status._pulse_animation.state(),
            QAbstractAnimation.State.Stopped,
        )
        self.assertEqual(status._status_effect.opacity(), 1.0)

    def test_dictation_copy_and_badge_follow_runtime_state(self):
        page = DictationPage()
        page.set_state("recording")
        self.assertEqual(page._state_badge.text(), "●  LIVE")
        self.assertEqual(page._prompt.text(), "Speak naturally")
        self.assertIn("listening", page._hero.text().lower())
        page.set_state("draining")
        self.assertEqual(page._state_badge.text(), "✦  PROCESSING")
        self.assertEqual(page._prompt.text(), "Creating your transcript")

    def test_waveform_has_continuous_ambient_motion(self):
        ring = WaveformRing()
        before = ring._phase
        QTest.qWait(ring.FRAME_MS * 2 + 10)
        self.assertGreater(ring._phase, before)


if __name__ == "__main__":
    unittest.main()
