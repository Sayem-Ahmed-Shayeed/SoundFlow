import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import (
        QAbstractAnimation,
        QCoreApplication,
        QEasingCurve,
        QEvent,
        Qt,
    )
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from soundflow.core.settings import Settings, SettingsStore
    from soundflow.design.motion import reduced_motion
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

    def test_navigation_switches_pages_instantly(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SettingsStore(Path(directory) / "settings.json")
            window = MainWindow(Settings(), store, demo_mode=True, no_hotkeys=True)
            self._windows.append(window)
            window.show()
            self.application.processEvents()

            window.navigate("history")

            self.assertEqual(window.pages.currentWidget(), window.history_page)
            self.assertIsNone(window.history_page.graphicsEffect())

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

    def test_new_status_message_fades_and_interruption_keeps_latest_text(self):
        status = StatusBar()
        status.show()
        self.application.processEvents()

        status.set_status("Listening", "recording")

        self.assertEqual(status._label_animation.duration(), ANIMATION_NORMAL)
        self.assertEqual(
            status._label_animation.easingCurve().type(),
            QEasingCurve.Type.OutCubic,
        )
        self.assertEqual(
            status._label_animation.state(),
            QAbstractAnimation.State.Running,
        )
        QTest.qWait(ANIMATION_NORMAL // 2)
        status.set_status("Creating transcript", "draining")
        QTest.qWait(ANIMATION_NORMAL + 30)

        self.assertEqual(status._status_label.text(), "Creating transcript")
        self.assertAlmostEqual(status._label_effect.opacity(), 1.0)
        self.assertEqual(
            status._label_animation.state(),
            QAbstractAnimation.State.Stopped,
        )

        status.set_status("Creating transcript", "ready")
        self.assertEqual(
            status._label_animation.state(),
            QAbstractAnimation.State.Stopped,
        )

    def test_dictation_copy_and_badge_follow_runtime_state(self):
        page = DictationPage()
        page.set_state("recording")
        self.assertEqual(page._hero.text(), "Listening")
        self.assertEqual(page._hero.property("state"), "recording")
        self.assertEqual(page.record_button.text_label(), "Stop and paste")
        page.set_state("draining")
        self.assertEqual(page._hero.text(), "Transcribing")
        self.assertFalse(page.record_button.isEnabled())
        page.set_state("idle")
        self.assertEqual(page.record_button.text_label(), "Start dictation")
        self.assertTrue(page.record_button.isEnabled())

    def test_waveform_only_animates_while_something_moves(self):
        ring = WaveformRing()
        ring.resize(600, 180)
        ring.show()
        self.application.processEvents()
        # A cursor left over by an earlier test may hover it; let that settle.
        QTest.qWait(300)
        self.assertFalse(ring._timer.isActive(), "idle waveform should not tick")
        ring.set_state("draining")
        self.assertTrue(ring._timer.isActive())
        before = ring._phase
        QTest.qWait(ring.FRAME_MS * 4 + 20)
        self.assertGreater(ring._phase, before)
        ring.set_state("idle")
        QTest.qWait(ring.CROSSFADE_MS + 120)
        self.assertFalse(ring._timer.isActive())
        ring.hide()

    def test_click_start_ripples_but_keyboard_start_does_not(self):
        ring = WaveformRing()
        ring.resize(600, 220)
        ring.show()
        self.application.processEvents()
        ring.set_state("recording")  # shortcut or Space: instant
        self.assertIsNone(ring._ripple_started)
        ring.set_state("idle")
        QTest.mousePress(ring, Qt.MouseButton.LeftButton)
        ring.release_press()
        ring.set_state("recording")
        if not reduced_motion():
            self.assertIsNotNone(ring._ripple_started)
        ring.push_level(0.8)
        QTest.qWait(ring.FRAME_MS * 6)
        self.assertGreater(ring._env, 0.0)
        ring.hide()

    def test_success_check_settles_back_to_idle(self):
        ring = WaveformRing()
        ring.resize(600, 220)
        ring.show()
        self.application.processEvents()
        ring.flash_success()
        self.assertEqual(ring._visual, "success")
        self.assertTrue(ring._timer.isActive())
        QTest.qWait(ring.SUCCESS_HOLD_MS + ring.CROSSFADE_MS + 150)
        self.assertEqual(ring._visual, "idle")
        self.assertFalse(ring._timer.isActive(), "settled ring should stop ticking")
        ring.set_state("recording")
        ring.flash_success()  # only after a dictation, never mid-recording
        self.assertEqual(ring._visual, "recording")
        ring.hide()


if __name__ == "__main__":
    unittest.main()
