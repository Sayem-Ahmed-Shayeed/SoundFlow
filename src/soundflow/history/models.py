"""Data model for a single transcript entry."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class TranscriptEntry:
    """One dictation session saved by the History store."""

    id: int
    created_at: datetime
    duration_s: float
    title: str
    summary: str
    body: str

    def is_today(self) -> bool:
        return self.created_at.date() == datetime.now().date()

    def is_yesterday(self) -> bool:
        from datetime import timedelta
        return self.created_at.date() == (datetime.now().date() - timedelta(days=1))

    @staticmethod
    def make_title(body: str, fallback: str = "Untitled") -> str:
        first = body.strip().splitlines()[0] if body.strip() else ""
        # Cap to a sentence-ish chunk for the card title.
        for end in (". ", "! ", "? "):
            if end in first:
                first = first.split(end, 1)[0]
                break
        first = first.strip().strip('"\u201C\u201D')
        return first[:80] if first else fallback

    @staticmethod
    def make_summary(body: str, max_chars: int = 140) -> str:
        cleaned = " ".join(body.split())
        if len(cleaned) <= max_chars:
            return cleaned
        return cleaned[: max_chars - 1].rstrip() + "\u2026"


__all__ = ["TranscriptEntry"]