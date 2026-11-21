"""SQLite-backed persistent storage for transcript history.

The store lives at ``data_directory()/history.db``. List views use
lightweight previews (no full bodies) with LIMIT/OFFSET pagination so
long transcripts never stall the UI thread.

When constructed with ``user_id`` every read and write is limited to that
account's rows. Each row carries a ``uuid`` (its id in Supabase), a
``sync_state`` (``pending`` until uploaded) and a ``local_rev`` counter so the
sync worker never marks an edit made mid-upload as synced. Deleted rows leave
a tombstone so the deletion reaches the cloud too.
"""

from __future__ import annotations

import sqlite3
import uuid as uuidlib
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
CREATE TABLE IF NOT EXISTS sync_tombstones (
    uuid        TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    deleted_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sync_meta (
    user_id      TEXT PRIMARY KEY,
    pull_cursor  TEXT
);
"""

_SYNC_COLUMNS = (
    ("uuid", "TEXT"),
    ("user_id", "TEXT"),
    ("sync_state", "TEXT NOT NULL DEFAULT 'pending'"),
    ("local_rev", "INTEGER NOT NULL DEFAULT 0"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _local_to_utc(created_at: str) -> str:
    """Local naive ISO time (as stored) -> aware UTC ISO for Supabase."""
    return datetime.fromisoformat(created_at).astimezone(timezone.utc).isoformat()


def _remote_to_local(value: str) -> str:
    """Aware ISO time from Supabase -> local naive ISO (as stored locally)."""
    moment = datetime.fromisoformat(value)
    if moment.tzinfo is not None:
        moment = moment.astimezone().replace(tzinfo=None)
    return moment.isoformat(timespec="seconds")


class HistoryStore:
    """Thin wrapper around an SQLite connection for transcript rows."""

    PREVIEW_CHARS = 400

    def __init__(self, path: Path | None = None, user_id: str | None = None) -> None:
        self.path = path or (data_directory() / "history.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.user_id = user_id
        self._conn = sqlite3.connect(self.path, timeout=10)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(_SCHEMA)
        self._migrate()
        self._conn.commit()
        self.generation = 0
        #: Called after every local add/update/delete (used to wake sync).
        self.on_change: Callable[[], None] | None = None

    def _migrate(self) -> None:
        existing = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(transcripts)")
        }
        for name, decl in _SYNC_COLUMNS:
            if name not in existing:
                self._conn.execute(f"ALTER TABLE transcripts ADD COLUMN {name} {decl}")
        missing = self._conn.execute(
            "SELECT id FROM transcripts WHERE uuid IS NULL"
        ).fetchall()
        for row in missing:
            self._conn.execute(
                "UPDATE transcripts SET uuid = ? WHERE id = ?",
                (str(uuidlib.uuid4()), row["id"]),
            )
        self._conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_transcripts_uuid ON transcripts (uuid)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_transcripts_user ON transcripts (user_id)"
        )

    def _scope(self, parts: list[str], params: list) -> None:
        if self.user_id is not None:
            parts.append("user_id = ?")
            params.append(self.user_id)

    def _where(self, parts: list[str]) -> str:
        return f"WHERE {' AND '.join(parts)}" if parts else ""

    def _changed(self) -> None:
        self.generation += 1
        callback = self.on_change
        if callback is not None:
            callback()

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
                "INSERT INTO transcripts (created_at, duration_s, title, summary, body,"
                " uuid, user_id, sync_state)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')",
                (
                    created.isoformat(timespec="seconds"),
                    float(duration_s),
                    title,
                    summary,
                    body,
                    str(uuidlib.uuid4()),
                    self.user_id,
                ),
            )
            row_id = cur.lastrowid
        self._changed()
        return TranscriptEntry(
            id=row_id,
            created_at=created,
            duration_s=duration_s,
            title=title,
            summary=summary,
            body=body,
        )

    def list_entries(self, query: str = "") -> list[TranscriptEntry]:
        parts: list[str] = []
        params: list = []
        if query.strip():
            like = _like_pattern(query)
            parts.append("(body LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\')")
            params.extend([like, like])
        self._scope(parts, params)
        rows = self._conn.execute(
            f"SELECT * FROM transcripts {self._where(parts)}"
            " ORDER BY created_at DESC, id DESC",
            params,
        ).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def count(self, query: str = "", since: str | None = None) -> int:
        parts = []
        params: list = []
        if query.strip():
            like = _like_pattern(query)
            parts.append("(body LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\')")
            params.extend([like, like])
        if since:
            parts.append("date(created_at) >= date(?)")
            params.append(since)
        self._scope(parts, params)
        where = self._where(parts)
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
            like = _like_pattern(query)
            parts.append("(body LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\')")
            params.extend([like, like])
        if since:
            parts.append("date(created_at) >= date(?)")
            params.append(since)
        self._scope(parts, params)
        where = self._where(parts)
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
        row = self._row(entry_id)
        if row is None:
            return
        with self._conn:
            if row["user_id"]:
                self._conn.execute(
                    "INSERT OR REPLACE INTO sync_tombstones (uuid, user_id, deleted_at)"
                    " VALUES (?, ?, ?)",
                    (row["uuid"], row["user_id"], _utc_now()),
                )
            self._conn.execute("DELETE FROM transcripts WHERE id = ?", (entry_id,))
        self._changed()

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
                "UPDATE transcripts SET title = ?, summary = ?, body = ?,"
                " sync_state = 'pending', local_rev = local_rev + 1 WHERE id = ?",
                (title, summary, body, entry_id),
            )
        self._changed()
        return TranscriptEntry(
            id=current.id,
            created_at=current.created_at,
            duration_s=current.duration_s,
            title=title,
            summary=summary,
            body=body,
        )

    def _row(self, entry_id: int) -> sqlite3.Row | None:
        parts = ["id = ?"]
        params: list = [entry_id]
        self._scope(parts, params)
        return self._conn.execute(
            f"SELECT * FROM transcripts {self._where(parts)}", params
        ).fetchone()

    def get(self, entry_id: int) -> TranscriptEntry | None:
        row = self._row(entry_id)
        return self._row_to_entry(row) if row else None

    def sync_state(self, entry_id: int) -> str | None:
        """``pending`` or ``synced`` for a row this account can see, else None."""
        row = self._row(entry_id)
        return str(row["sync_state"]) if row is not None else None

    def today_stats(self) -> tuple[int, int, str, str]:
        """(dictation count, word count, latest preview, latest meta) for today."""
        parts = ["date(created_at) = date('now', 'localtime')"]
        params: list = []
        self._scope(parts, params)
        rows = self._conn.execute(
            f"SELECT body, created_at FROM transcripts {self._where(parts)}"
            " ORDER BY id DESC",
            params,
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

    def activity(self) -> list:
        """Every dictation as (local time, seconds spoken, words), oldest first."""
        from soundflow.history.stats import Activity

        parts: list[str] = []
        params: list = []
        self._scope(parts, params)
        rows = self._conn.execute(
            f"SELECT created_at, duration_s, body FROM transcripts {self._where(parts)}"
            " ORDER BY created_at",
            params,
        ).fetchall()
        result = []
        for row in rows:
            try:
                when = datetime.fromisoformat(row["created_at"])
            except (TypeError, ValueError):
                continue
            if when.tzinfo is not None:
                when = when.astimezone()
            result.append(
                Activity(when, float(row["duration_s"] or 0), len(str(row["body"]).split()))
            )
        return result

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

    # -- cloud sync -------------------------------------------------------
    def claim_unowned(self, user_id: str) -> int:
        """Attach transcripts saved before accounts existed to ``user_id``."""
        with self._conn:
            cur = self._conn.execute(
                "UPDATE transcripts SET user_id = ?, sync_state = 'pending'"
                " WHERE user_id IS NULL",
                (user_id,),
            )
        if cur.rowcount:
            self._changed()
        return cur.rowcount

    def pending_uploads(self, limit: int = 100) -> list[dict[str, Any]]:
        """Rows not yet in the cloud, as ``(payload, uuid, local_rev)`` dicts."""
        if self.user_id is None:
            return []
        rows = self._conn.execute(
            "SELECT * FROM transcripts WHERE user_id = ? AND sync_state = 'pending'"
            " ORDER BY id LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        return [
            {
                "uuid": row["uuid"],
                "local_rev": int(row["local_rev"]),
                "payload": {
                    "id": row["uuid"],
                    "user_id": self.user_id,
                    "created_at": _local_to_utc(row["created_at"]),
                    "duration_s": float(row["duration_s"]),
                    "title": row["title"],
                    "summary": row["summary"],
                    "body": row["body"],
                    "deleted_at": None,
                },
            }
            for row in rows
        ]

    def mark_uploaded(self, revisions: dict[str, int]) -> None:
        """Mark rows synced unless they were edited again during the upload."""
        with self._conn:
            self._conn.executemany(
                "UPDATE transcripts SET sync_state = 'synced'"
                " WHERE uuid = ? AND local_rev = ?",
                list(revisions.items()),
            )

    def pending_deletions(self, limit: int = 100) -> list[tuple[str, str]]:
        if self.user_id is None:
            return []
        rows = self._conn.execute(
            "SELECT uuid, deleted_at FROM sync_tombstones WHERE user_id = ? LIMIT ?",
            (self.user_id, limit),
        ).fetchall()
        return [(row["uuid"], row["deleted_at"]) for row in rows]

    def clear_deletions(self, uuids: list[str]) -> None:
        with self._conn:
            self._conn.executemany(
                "DELETE FROM sync_tombstones WHERE uuid = ?", [(u,) for u in uuids]
            )

    def pull_cursor(self) -> str | None:
        row = self._conn.execute(
            "SELECT pull_cursor FROM sync_meta WHERE user_id = ?", (self.user_id,)
        ).fetchone()
        return row["pull_cursor"] if row else None

    def set_pull_cursor(self, cursor: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO sync_meta (user_id, pull_cursor) VALUES (?, ?)"
                " ON CONFLICT(user_id) DO UPDATE SET pull_cursor = excluded.pull_cursor",
                (self.user_id, cursor),
            )

    def apply_remote(self, rows: list[dict[str, Any]]) -> int:
        """Merge rows pulled from Supabase. Local unsynced edits win."""
        if self.user_id is None:
            return 0
        changed = 0
        with self._conn:
            for remote in rows:
                uid = str(remote["id"])
                local = self._conn.execute(
                    "SELECT id, sync_state, created_at, duration_s, title, summary, body"
                    " FROM transcripts WHERE uuid = ?",
                    (uid,),
                ).fetchone()
                tombstoned = self._conn.execute(
                    "SELECT 1 FROM sync_tombstones WHERE uuid = ?", (uid,)
                ).fetchone()
                if remote.get("deleted_at"):
                    # An edit made here that hasn't uploaded yet wins: keep it,
                    # and its upload restores the transcript everywhere.
                    if local is not None and local["sync_state"] != "pending":
                        self._conn.execute("DELETE FROM transcripts WHERE id = ?", (local["id"],))
                        changed += 1
                    continue
                if tombstoned is not None:
                    continue  # deleted here; the deletion is about to be pushed
                values = (
                    _remote_to_local(str(remote["created_at"])),
                    float(remote.get("duration_s") or 0),
                    str(remote.get("title") or ""),
                    str(remote.get("summary") or ""),
                    str(remote.get("body") or ""),
                )
                if local is None:
                    self._conn.execute(
                        "INSERT INTO transcripts (created_at, duration_s, title, summary,"
                        " body, uuid, user_id, sync_state) VALUES (?, ?, ?, ?, ?, ?, ?, 'synced')",
                        (*values, uid, self.user_id),
                    )
                    changed += 1
                elif local["sync_state"] != "pending" and values != (
                    local["created_at"],
                    float(local["duration_s"]),
                    local["title"],
                    local["summary"],
                    local["body"],
                ):
                    self._conn.execute(
                        "UPDATE transcripts SET created_at = ?, duration_s = ?, title = ?,"
                        " summary = ?, body = ? WHERE id = ?",
                        (*values, local["id"]),
                    )
                    changed += 1
        return changed

    def as_dict(self, entry: TranscriptEntry) -> dict:
        d = asdict(entry)
        d["created_at"] = entry.created_at.isoformat(timespec="seconds")
        return d


__all__ = ["HistoryStore"]


def _like_pattern(query: str) -> str:
    """A LIKE pattern that matches ``query`` literally, including % and _."""
    escaped = (
        query.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    )
    return f"%{escaped}%"
