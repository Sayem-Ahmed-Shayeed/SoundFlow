import gc
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    import numpy as np
    from PySide6.QtCore import QCoreApplication, QEvent, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    from soundflow.ui import MainWindow  # Load the public UI surface first.  # noqa: F401
    from soundflow.ui.pages import DictationPage
    from soundflow.ui.pages.dictation_page import greeting
    from soundflow.ui.widgets.segmented import SegmentedControl
    from soundflow.ui.widgets.spectrogram import (
        BINS,
        SpectrogramView,
        SpectrumAnalyzer,
        frequency_to_row,
    )

    HAS_QT = True
except ImportError:
    HAS_QT = False


def _tone(hz: float, seconds: float = 0.5, level: float = 0.1) -> bytes:
    t = np.arange(int(16_000 * seconds)) / 16_000
    wave = np.sin(2 * np.pi * hz * t) * level
    return (wave * 32767).astype("<i2").tobytes()


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class SpectrogramTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_a_tone_lights_the_matching_row(self):
        columns = SpectrumAnalyzer().feed(_tone(1000))
        self.assertGreater(len(columns), 20)
        peak = int(np.argmax(columns[-1]))
        self.assertAlmostEqual(peak / (BINS - 1), frequency_to_row(1000), delta=0.05)

    def test_silence_stays_dark(self):
        columns = SpectrumAnalyzer().feed(bytes(16_000))
        self.assertLess(max(float(c.max()) for c in columns), 0.05)

    def test_frozen_view_stretches_only_the_recording(self):
        view = SpectrogramView(columns=200)
        view.start_live()
        view.push_columns([np.full(BINS, 0.8)] * 30)
        view.freeze()
        self.assertEqual(view.state, "frozen")
        shown = view.visible_columns()
        self.assertLessEqual(len(shown), 30)
        self.assertTrue(all(float(c.max()) > 0.5 for c in shown))

    def test_audio_is_ignored_unless_live(self):
        view = SpectrogramView(columns=50)
        view.push_audio(_tone(500))
        self.assertEqual(view.state, "idle")
        self.assertEqual(view._recorded, 0)

    def test_scanning_animates_only_while_transcribing(self):
        view = SpectrogramView(columns=50)
        view.start_live()
        view.push_columns([np.full(BINS, 0.6)] * 10)
        view.freeze()
        view.set_scanning(True)
        self.assertEqual(view.state, "scanning")
        view.set_scanning(False)
        self.assertEqual(view.state, "frozen")
        self.assertFalse(view._scan_animation.state() == view._scan_animation.State.Running)


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class SegmentedControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def test_emits_only_on_a_new_choice(self):
        control = SegmentedControl((("a", "A"), ("b", "B")), "a")
        seen = []
        control.changed.connect(seen.append)
        control.button("a").click()
        control.button("b").click()
        control.set_value("a")  # silent by default
        self.assertEqual(seen, ["b"])
        self.assertEqual(control.value(), "a")
        self.assertTrue(control.button("a").isChecked())


@unittest.skipUnless(HAS_QT, "PySide6 is not installed")
class DictationHomeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def tearDown(self):
        for widget in QApplication.topLevelWidgets():
            widget.close()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def test_greeting_follows_the_time_of_day(self):
        from datetime import datetime

        self.assertEqual(greeting(datetime(2026, 1, 1, 8)), "Good morning")
        self.assertEqual(greeting(datetime(2026, 1, 1, 14)), "Good afternoon")
        self.assertEqual(greeting(datetime(2026, 1, 1, 21)), "Good evening")

    def test_escape_cancels_only_while_listening(self):
        page = DictationPage()
        page.show()
        cancels = []
        page.cancel_requested.connect(lambda: cancels.append(True))
        QTest.keyClick(page, Qt.Key.Key_Escape)
        self.assertEqual(cancels, [])
        page.set_state("recording")
        QTest.keyClick(page, Qt.Key.Key_Escape)
        self.assertEqual(cancels, [True])

    def test_copy_only_mode_says_so(self):
        page = DictationPage()
        page.set_paste_on_stop(False)
        page.set_state("recording")
        self.assertEqual(page.record_button.text_label(), "Stop and copy")
        self.assertIn("without copying", page.hint_text())

    def test_recording_stays_on_screen_after_transcribing(self):
        page = DictationPage()
        page.set_state("recording")
        page.push_audio(_tone(400, 1.0))
        self.assertEqual(page.ribbon.state, "live")
        page.set_state("draining")
        self.assertEqual(page.ribbon.state, "scanning")
        page.set_state("idle")
        self.assertEqual(page.ribbon.state, "frozen")
        page.reset_ribbon()
        self.assertEqual(page.ribbon.state, "idle")

    def test_result_card_shows_outcome_length_and_words(self):
        page = DictationPage()
        page.show()
        page.set_polish_available(True)
        page.set_result("one two three", 9.6, "pasted")
        self.assertTrue(page._result.isVisible())
        self.assertEqual(page._outcome.text(), "Pasted where your cursor was")
        self.assertEqual(page._result_length.text(), "0:09")
        self.assertEqual(page._result_words.text(), "3 words")
        self.assertTrue(page.polish_button.isVisible())
        asked = []
        page.polish_requested.connect(asked.append)
        page.polish_button.click()
        self.assertEqual(asked, ["one two three"])
        page.set_state("recording")  # the next dictation clears it
        self.assertFalse(page._result.isVisible())

    def test_dashboard_numbers_and_recent_list(self):
        from datetime import date, datetime, timedelta

        from soundflow.history.stats import Activity, dashboard_stats

        today = date(2026, 11, 20)
        noon = datetime(2026, 11, 20, 12, 0)
        activity = [
            Activity(noon - timedelta(days=1), 60.0, 140),
            Activity(noon, 30.0, 70),
            Activity(noon, 30.0, 64),
        ]
        page = DictationPage()
        page.show()
        page.set_dashboard(dashboard_stats(activity, today))
        self.assertIn("134 words", page._today_line.text())
        self.assertEqual(page._week_tile.value.text(), "274")
        self.assertEqual(page._speed_tile.value.text(), "137")
        self.assertEqual(page._speed_tile.unit.text(), "wpm")
        self.assertEqual(page._streak_tile.value.text(), "2")
        self.assertEqual(page.daily_chart.values()[-2:], [140, 134])
        self.assertEqual(page._total_words.text(), "274")
        page.set_dashboard(dashboard_stats([], today))
        self.assertEqual(page._speed_tile.value.text(), "–")
        self.assertIn("Nothing dictated", page._today_line.text())
        page.set_recent([(3, "9:21 PM", "c"), (2, "8:02 PM", "b"), (1, "Yesterday", "a")])
        self.assertEqual(len(page._recent_rows), 3)
        copied = []
        page.recent_copy_requested.connect(copied.append)
        page._recent_rows[1].copy_button.click()
        self.assertEqual(copied, [2])

    def test_voice_bars_follow_loudness(self):
        import numpy as np

        page = DictationPage()
        page.set_state("recording")
        quiet = np.zeros(4800, dtype="<i2").tobytes()
        loud = (np.sin(np.arange(4800) / 5) * 12000).astype("<i2").tobytes()
        page.push_audio(quiet)
        page.push_audio(loud)
        levels = page.ribbon.levels()
        self.assertEqual(len(levels), 20)
        self.assertLess(max(levels[:10]), 0.05)
        self.assertGreater(min(levels[10:]), 0.6)
        page.set_state("idle")  # from recording: nothing kept
        self.assertEqual(page.ribbon.levels(), [])

if __name__ == "__main__":
    unittest.main()
