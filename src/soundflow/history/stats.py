"""Numbers for the home dashboard, worked out from saved dictations.

Everything comes from what History already stores for each dictation: when
it happened, how long you spoke and the text. Days are local days.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

# A typical typing speed, used for "faster than typing" and "time saved".
TYPING_WPM = 40
DAYS_SHOWN = 14
WEEKS_SHOWN = 18
# Daily word bands for the activity grid: 0, 1-249, 250-499, 500-749, 750+.
HEAT_BANDS = (1, 250, 500, 750)


@dataclass(frozen=True)
class Activity:
    """One saved dictation, reduced to what the dashboard needs."""

    when: datetime
    seconds: float
    words: int


@dataclass
class DashboardStats:
    today_words: int = 0
    today_dictations: int = 0
    week_words: int = 0
    previous_week_words: int = 0
    wpm: int | None = None
    week_minutes_saved: int = 0
    streak: int = 0
    longest_streak: int = 0
    total_words: int = 0
    total_dictations: int = 0
    # Oldest first; the last entry is today.
    daily: list[tuple[date, int]] = field(default_factory=list)
    # Monday-first weeks, oldest first: (day, words) or None for days after today.
    heat: list[list[tuple[date, int] | None]] = field(default_factory=list)

    @property
    def week_change(self) -> int | None:
        """Percent change on the week before, or None with nothing to compare."""
        if self.previous_week_words <= 0:
            return None
        return round((self.week_words - self.previous_week_words) / self.previous_week_words * 100)

    @property
    def speedup(self) -> float | None:
        return self.wpm / TYPING_WPM if self.wpm else None


def heat_level(words: int) -> int:
    """0 to 4, the shade of a day in the activity grid."""
    return sum(1 for band in HEAT_BANDS if words >= band)


def _streaks(days_with_words: set[date], today: date) -> tuple[int, int]:
    """(current, longest). The current streak survives a day with nothing yet."""
    longest = run = 0
    previous: date | None = None
    for day in sorted(days_with_words):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day
    end = today if today in days_with_words else today - timedelta(days=1)
    current = 0
    while end in days_with_words:
        current += 1
        end -= timedelta(days=1)
    return current, longest


def dashboard_stats(activity: list[Activity], today: date | None = None) -> DashboardStats:
    today = today or date.today()
    words_by_day: dict[date, int] = defaultdict(int)
    stats = DashboardStats()
    week_start = today - timedelta(days=6)
    previous_start = today - timedelta(days=13)
    speed_since = today - timedelta(days=29)
    week_seconds = speed_words = 0.0
    speed_seconds = 0.0
    for item in activity:
        day = item.when.date()
        words_by_day[day] += item.words
        stats.total_words += item.words
        stats.total_dictations += 1
        if day == today:
            stats.today_words += item.words
            stats.today_dictations += 1
        if week_start <= day <= today:
            stats.week_words += item.words
            week_seconds += item.seconds
        elif previous_start <= day < week_start:
            stats.previous_week_words += item.words
        if day >= speed_since and item.seconds > 0 and item.words > 0:
            speed_words += item.words
            speed_seconds += item.seconds
    # Speed needs a little speech to mean anything.
    if speed_seconds >= 20:
        stats.wpm = round(speed_words / (speed_seconds / 60))
    typing_minutes = stats.week_words / TYPING_WPM
    stats.week_minutes_saved = max(0, round(typing_minutes - week_seconds / 60))
    stats.streak, stats.longest_streak = _streaks(
        {day for day, words in words_by_day.items() if words > 0}, today
    )
    stats.daily = [
        (day, words_by_day.get(day, 0))
        for day in (today - timedelta(days=offset) for offset in range(DAYS_SHOWN - 1, -1, -1))
    ]
    this_monday = today - timedelta(days=today.weekday())
    first_monday = this_monday - timedelta(weeks=WEEKS_SHOWN - 1)
    for week in range(WEEKS_SHOWN):
        column: list[tuple[date, int] | None] = []
        for weekday in range(7):
            day = first_monday + timedelta(weeks=week, days=weekday)
            column.append(None if day > today else (day, words_by_day.get(day, 0)))
        stats.heat.append(column)
    return stats


def duration_text(minutes: int) -> str:
    """"2h 51m", "45m"."""
    hours, rest = divmod(max(0, int(minutes)), 60)
    if hours and rest:
        return f"{hours}h {rest}m"
    if hours:
        return f"{hours}h"
    return f"{rest}m"


__all__ = [
    "TYPING_WPM",
    "Activity",
    "DashboardStats",
    "dashboard_stats",
    "duration_text",
    "heat_level",
]
