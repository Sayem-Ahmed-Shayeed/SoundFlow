"""Signed-in account state shared by the UI and the sync worker."""

from __future__ import annotations

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from soundflow.cloud.client import (
    AuthError,
    AuthSession,
    CloudError,
    CloudUser,
    NetworkError,
    SupabaseClient,
)
from soundflow.core.settings import config_directory

log = logging.getLogger(__name__)

GENDERS = ("male", "female")


class SessionStore:
    """Persists the refresh token in a file only the current user can read."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (config_directory() / "session.json")

    def load(self) -> AuthSession | None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return AuthSession.from_json(payload)
        except FileNotFoundError:
            return None
        except (OSError, ValueError, KeyError, TypeError) as exc:
            log.warning("Ignoring unreadable session file %s: %s", self.path, exc)
            return None

    def save(self, session: AuthSession) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(session.to_json(), handle)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self.path)

    def clear(self) -> None:
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


class Account:
    """Thread-safe holder of the current session.

    ``access_token()`` refreshes transparently, so both the GUI thread and the
    sync thread can call it. Network failures leave the cached session in
    place so the app keeps working offline.
    """

    def __init__(
        self,
        client: SupabaseClient | None = None,
        store: SessionStore | None = None,
    ) -> None:
        self.client = client or SupabaseClient()
        self.store = store or SessionStore()
        self._lock = threading.RLock()
        self._session: AuthSession | None = self.store.load()

    # -- state ------------------------------------------------------------
    @property
    def session(self) -> AuthSession | None:
        with self._lock:
            return self._session

    @property
    def user(self) -> CloudUser | None:
        session = self.session
        return session.user if session else None

    @property
    def user_id(self) -> str | None:
        user = self.user
        return user.id if user else None

    def is_signed_in(self) -> bool:
        return self.session is not None

    def set_session(self, session: AuthSession) -> None:
        with self._lock:
            self._session = session
            self.store.save(session)

    # -- tokens -----------------------------------------------------------
    def restore(self) -> bool:
        """Validate a stored session at start-up.

        Returns False when there is no session or the server rejected it.
        Returns True when the session is fresh, was refreshed, or the network
        is unavailable (offline use with the cached account).
        """
        if self.session is None:
            return False
        try:
            self.access_token(force_refresh=self.session.expires_soon())
        except AuthError:
            return False
        except CloudError as exc:
            log.info("Using cached session while offline: %s", exc)
        return self.session is not None

    def access_token(self, force_refresh: bool = False) -> str:
        with self._lock:
            session = self._session
            if session is None:
                raise AuthError("Not signed in.", "not_signed_in")
            if not force_refresh and not session.expires_soon():
                return session.access_token
            try:
                fresh = self.client.refresh(session.refresh_token)
            except AuthError:
                self._forget()
                raise
            self._session = fresh
            self.store.save(fresh)
            return fresh.access_token

    def sign_out(self) -> None:
        with self._lock:
            session = self._session
            self._forget()
        if session is None:
            return
        try:
            self.client.sign_out(session.access_token)
        except CloudError as exc:  # local sign-out still succeeds
            log.info("Remote sign-out failed: %s", exc)

    def _forget(self) -> None:
        self._session = None
        self.store.clear()

    # -- profile ----------------------------------------------------------
    def fetch_profile(self) -> dict[str, Any] | None:
        user_id = self.user_id
        if not user_id:
            return None
        return self.client.get_profile(self.access_token(), user_id)

    def save_profile(self, full_name: str, gender: str) -> None:
        if gender not in GENDERS:
            raise ValueError("Choose male or female.")
        user_id = self.user_id
        if not user_id:
            raise AuthError("Not signed in.", "not_signed_in")
        token = self.access_token()
        self.client.upsert_profile(token, user_id, full_name, gender)
        user = self.client.update_user_metadata(
            token, {"full_name": full_name, "gender": gender}
        )
        with self._lock:
            if self._session is not None and user.id:
                self._session.user = user
                self.store.save(self._session)

    def ensure_profile(self) -> bool:
        """Create the profile row from sign-up details if it is missing.

        The database trigger normally creates it; this covers accounts made
        before ``0001_soundflow_cloud.sql`` was run. Returns True if a row was
        written. Raises CloudError on network or schema problems.
        """
        user = self.user
        if user is None:
            return False
        profile = self.fetch_profile()
        if profile is not None and profile.get("gender") in GENDERS:
            return False
        name = str(user.metadata.get("full_name") or "").strip()
        gender = str(user.metadata.get("gender") or "").strip().lower()
        if gender not in GENDERS:
            return False
        self.client.upsert_profile(self.access_token(), user.id, name, gender)
        return True


__all__ = ["GENDERS", "Account", "NetworkError", "SessionStore"]
