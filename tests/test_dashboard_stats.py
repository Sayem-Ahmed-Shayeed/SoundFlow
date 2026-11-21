import unittest
from datetime import date, datetime, timedelta

from soundflow.history.stats import (
    Activity,
    dashboard_stats,
    duration_text,
    heat_level,
)

TODAY = date(2026, 11, 20)  # a Friday


def at(days_ago: int, words: int, seconds: float = 0.0) -> Activity:
    when = datetime(2026, 11, 20, 10, 0) - timedelta(days=days_ago)
    return Activity(when, seconds, words)


class DashboardStatsTests(unittest.TestCase):
    def test_empty_history_gives_zeros_and_full_charts(self):
        stats = dashboard_stats([], TODAY)
        self.assertEqual((stats.today_words, stats.week_words, stats.streak), (0, 0, 0))
        self.assertIsNone(stats.wpm)
        self.assertIsNone(stats.week_change)
        self.assertEqual(len(stats.daily), 14)
        self.assertEqual(stats.daily[-1], (TODAY, 0))
        self.assertEqual(len(stats.heat), 18)
        # Friday: Saturday and Sunday of this week are still to come.
        self.assertEqual(stats.heat[-1][4], (TODAY, 0))
        self.assertIsNone(stats.heat[-1][5])
        self.assertIsNone(stats.heat[-1][6])

    def test_week_totals_and_change(self):
        stats = dashboard_stats([at(0, 100), at(6, 50), at(7, 60), at(13, 40), at(14, 999)], TODAY)
        self.assertEqual(stats.week_words, 150)
        self.assertEqual(stats.previous_week_words, 100)
        self.assertEqual(stats.week_change, 50)
        self.assertEqual(stats.total_words, 1249)
        self.assertEqual(stats.total_dictations, 5)

    def test_speed_needs_enough_speech(self):
        self.assertIsNone(dashboard_stats([at(0, 30, 10.0)], TODAY).wpm)
        stats = dashboard_stats([at(0, 140, 60.0)], TODAY)
        self.assertEqual(stats.wpm, 140)
        self.assertAlmostEqual(stats.speedup, 3.5)

    def test_time_saved_compares_with_typing(self):
        # 400 words take 10 minutes to type; speaking them took 3.
        stats = dashboard_stats([at(1, 400, 180.0)], TODAY)
        self.assertEqual(stats.week_minutes_saved, 7)
        self.assertEqual(duration_text(171), "2h 51m")
        self.assertEqual(duration_text(120), "2h")
        self.assertEqual(duration_text(46), "46m")

    def test_streak_survives_a_day_not_started_yet(self):
        activity = [at(1, 10), at(2, 10), at(3, 10), at(6, 10), at(7, 10), at(8, 10), at(9, 10)]
        stats = dashboard_stats(activity, TODAY)
        self.assertEqual(stats.streak, 3)
        self.assertEqual(stats.longest_streak, 4)
        stats = dashboard_stats([at(2, 10)], TODAY)
        self.assertEqual(stats.streak, 0)

    def test_heat_bands(self):
        self.assertEqual([heat_level(w) for w in (0, 1, 249, 250, 500, 749, 750)], [0, 1, 1, 2, 3, 3, 4])


if __name__ == "__main__":
    unittest.main()
