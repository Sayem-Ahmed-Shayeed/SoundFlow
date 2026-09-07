"""SQLite-backed persistent storage for transcript history.

The store lives at ``data_directory()/history.db``. List views use
lightweight previews (no full bodies) with LIMIT/OFFSET pagination so
long transcripts never stall the UI thread.
"""

from __future__ import annotations

import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from soundflow.core.settings import data_directory
from soundflow.history.models import TranscriptEntry


_SCHEMA = """
CREATE TABLE IF NOT EXISTS transcripts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at  TEXT NOT NULL,
    duration_s  REAL NOT NULL DEFAULT 0,
    title       TEXT NOT NULL,
    summary     TEXT NOT NULL,
    body        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transcripts_created_at
    ON transcripts (created_at DESC);
"""


class HistoryStore:
    """Thin wrapper around an SQLite connection for transcript rows."""

    PREVIEW_CHARS = 400

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (data_directory() / "history.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self.generation = 0

    # ------------------------------------------------------------------
    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def add(self, body: str, duration_s: float = 0.0) -> TranscriptEntry:
        body = body.strip()
        title = TranscriptEntry.make_title(body)
        summary = TranscriptEntry.make_summary(body)
        created = datetime.now()
        with self._conn:
            cur = self._conn.execute(
                "INSERT INTO transcripts (created_at, duration_s, title, summary, body)"
                " VALUES (?, ?, ?, ?, ?)",
                (created.isoformat(timespec="seconds"), float(duration_s), title, summary, body),
            )
            row_id = cur.lastrowid
        self.generation += 1
        return TranscriptEntry(
            id=row_id,
            created_at=created,
            duration_s=duration_s,
            title=title,
            summary=summary,
            body=body,
        )

    def list_entries(self, query: str = "") -> list[TranscriptEntry]:
        like = f"%{query.strip()}%"
        if query.strip():
            rows = self._conn.execute(
                "SELECT * FROM transcripts WHERE body LIKE ? OR title LIKE ?"
                " ORDER BY created_at DESC, id DESC",
                (like, like),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM transcripts ORDER BY created_at DESC, id DESC"
            ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count(self, query: str = "", since: str | None = None) -> int:
        parts = []
        params: list = []
        if query.strip():
            like = f"%{query.strip()}%"
            parts.append("(body LIKE ? OR title LIKE ?)")
            params.extend([like, like])
        if since:
            parts.append("date(created_at) >= date(?)")
            params.append(since)
        where = f"WHERE {' AND '.join(parts)}" if parts else ""
        row = self._conn.execute(
            f"SELECT COUNT(*) AS n FROM transcripts {where}", params
        ).fetchone()
        return int(row["n"])

    def list_previews(
        self,
        query: str = "",
        limit: int = 20,
        offset: int = 0,
        since: str | None = None,
    ) -> tuple[list[TranscriptEntry], list[bool]]:
        """Lightweight rows for list views: full body replaced by a preview."""
        parts = []
        params: list = []
        if query.strip():
            like = f"%{query.strip()}%"
            parts.append("(body LIKE ? OR title LIKE ?)")
            params.extend([like, like])
        if since:
            parts.append("date(created_at) >= date(?)")
            params.append(since)
        where = f"WHERE {' AND '.join(parts)}" if parts else ""
        params.extend([limit, offset])
        rows = self._conn.execute(
            "SELECT id, created_at, duration_s, title, summary,"
            f" substr(body, 1, {self.PREVIEW_CHARS + 1}) AS preview,"
            " length(body) AS body_len FROM transcripts"
            f" {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            params,
        ).fetchall()
        entries = []
        truncated: list[bool] = []
        for row in rows:
            preview = str(row["preview"])
            cut = int(row["body_len"]) > self.PREVIEW_CHARS
            if cut:
                preview = preview[: self.PREVIEW_CHARS].rstrip() + "…"
            entries.append(
                TranscriptEntry(
                    id=int(row["id"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    duration_s=float(row["duration_s"]),
                    title=str(row["title"]),
                    summary=str(row["summary"]),
                    body=preview,
                )
            )
            truncated.append(cut)
        return entries, truncated

    def delete(self, entry_id: int) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM transcripts WHERE id = ?", (entry_id,))
        self.generation += 1

    def update(self, entry_id: int, body: str) -> TranscriptEntry:
        body = body.strip()
        if not body:
            raise ValueError("Transcript text cannot be empty")
        current = self.get(entry_id)
        if current is None:
            raise KeyError(entry_id)
        title = TranscriptEntry.make_title(body)
        summary = TranscriptEntry.make_summary(body)
        with self._conn:
            self._conn.execute(
                "UPDATE transcripts SET title = ?, summary = ?, body = ? WHERE id = ?",
                (title, summary, body, entry_id),
            )
        self.generation += 1
        return TranscriptEntry(
            id=current.id,
            created_at=current.created_at,
            duration_s=current.duration_s,
            title=title,
            summary=summary,
            body=body,
        )

    def get(self, entry_id: int) -> TranscriptEntry | None:
        row = self._conn.execute(
            "SELECT * FROM transcripts WHERE id = ?", (entry_id,)
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def today_stats(self) -> tuple[int, int, str, str]:
        """(dictation count, word count, latest preview, latest meta) for today."""
        rows = self._conn.execute(
            "SELECT body, created_at FROM transcripts"
            " WHERE date(created_at) = date('now', 'localtime')"
            " ORDER BY id DESC"
        ).fetchall()
        words = sum(len(str(row["body"]).split()) for row in rows)
        if not rows:
            return 0, 0, "", ""
        latest_body = str(rows[0]["body"])
        created = datetime.fromisoformat(rows[0]["created_at"])
        meta = (
            f"{created.strftime('%I:%M %p').lstrip('0')}"
            f" · {len(latest_body.split())} words"
        )
        return len(rows), words, latest_body, meta

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> TranscriptEntry:
        return TranscriptEntry(
            id=int(row["id"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            duration_s=float(row["duration_s"]),
            title=str(row["title"]),
            summary=str(row["summary"]),
            body=str(row["body"]),
        )

    def as_dict(self, entry: TranscriptEntry) -> dict:
        d = asdict(entry)
        d["created_at"] = entry.created_at.isoformat(timespec="seconds")
        return d


__all__ = ["HistoryStore"]
