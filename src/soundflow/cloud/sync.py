"""Two-way sync between the local SQLite history and Supabase.

Local SQLite stays the source the UI reads, so history works offline. A
background thread pushes new/edited rows and deletions, then pulls rows other
devices changed since the last cursor.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from soundflow.cloud.account import Account
from soundflow.cloud.client import AuthError, CloudError, NetworkError, SchemaMissing
from soundflow.history.store import HistoryStore

log = logging.getLogger(__name__)

SYNC_INTERVAL_S = 120.0
BATCH = 100


@dataclass
class SyncReport:
    uploaded: int = 0
    deleted: int = 0
    pulled: int = 0


def sync_once(store: HistoryStore, account: Account) -> SyncReport:
    """One full push + pull cycle. Raises CloudError subclasses on failure."""
    client = account.client
    report = SyncReport()

    while True:
        batch = store.pending_uploads(BATCH)
        if not batch:
            break
        token = account.access_token()
        client.upsert_transcripts(token, [item["payload"] for item in batch])
        store.mark_uploaded({item["uuid"]: item["local_rev"] for item in batch})
        report.uploaded += len(batch)
        if len(batch) < BATCH:
            break

    while True:
        deletions = store.pending_deletions(BATCH)
        if not deletions:
            break
        token = account.access_token()
        # One PATCH per distinct timestamp keeps the request count small.
        by_time: dict[str, list[str]] = {}
        for uid, deleted_at in deletions:
            by_time.setdefault(deleted_at, []).append(uid)
        for deleted_at, uids in by_time.items():
            client.mark_transcripts_deleted(token, uids, deleted_at)
        store.clear_deletions([uid for uid, _ in deletions])
        report.deleted += len(deletions)
        if len(deletions) < BATCH:
            break

    while True:
        token = account.access_token()
        rows = client.transcripts_changed_since(token, store.pull_cursor(), limit=500)
        if not rows:
            break
        report.pulled += store.apply_remote(rows)
        store.set_pull_cursor(str(rows[-1]["updated_at"]))
        if len(rows) < 500:
            break
    return report


class SyncService(QObject):
    """Owns the sync thread. Signals are delivered on the GUI thread."""

    #: number of rows changed locally by a pull (refresh views when > 0)
    pulled = Signal(int)
    #: short human-readable status for the sidebar
    status_changed = Signal(str)
    #: the refresh token was rejected; the user must sign in again
    auth_lost = Signal(str)

    def __init__(self, account: Account, db_path: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._account = account
        self._db_path = db_path
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="soundflow-sync", daemon=True)
        self._thread.start()

    def request_sync(self) -> None:
        self._wake.set()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout)
        self._thread = None

    def _run(self) -> None:
        user_id = self._account.user_id
        if not user_id:
            return
        store = HistoryStore(self._db_path, user_id=user_id)
        profile_checked = False
        try:
            while not self._stop.is_set():
                self.status_changed.emit("Syncing…")
                try:
                    if not profile_checked:
                        self._account.ensure_profile()
                        profile_checked = True
                    report = sync_once(store, self._account)
                except AuthError as exc:
                    self.status_changed.emit("Signed out")
                    self.auth_lost.emit(str(exc))
                    return
                except SchemaMissing as exc:
                    log.warning("%s", exc)
                    self.status_changed.emit("Cloud setup needed")
                except NetworkError:
                    self.status_changed.emit("Offline · will sync later")
                except CloudError as exc:
                    log.warning("Sync failed: %s", exc)
                    self.status_changed.emit("Sync failed · retrying")
                except Exception:  # never let the thread die silently
                    log.exception("Unexpected sync failure")
                    self.status_changed.emit("Sync failed · retrying")
                else:
                    self.status_changed.emit("Synced")
                    if report.pulled:
                        self.pulled.emit(report.pulled)
                self._wake.wait(SYNC_INTERVAL_S)
                self._wake.clear()
        finally:
            store.close()


__all__ = ["SyncReport", "SyncService", "sync_once"]
