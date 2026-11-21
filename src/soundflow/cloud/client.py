"""Minimal Supabase Auth (GoTrue) and PostgREST client over ``urllib``.

Kept dependency-free on purpose, matching :mod:`soundflow.core.llm`, so the
PyInstaller bundle does not grow. Only the endpoints Soundflow needs exist.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from soundflow.cloud.config import supabase_key, supabase_url

REQUEST_TIMEOUT_S = 20


class CloudError(RuntimeError):
    """Any failure talking to Supabase."""


class NetworkError(CloudError):
    """Supabase could not be reached (offline, DNS, timeout)."""


class AuthError(CloudError):
    """Credentials or tokens were rejected; the user must sign in again."""

    def __init__(self, message: str, code: str = "") -> None:
        super().__init__(message)
        self.code = code


class SchemaMissing(CloudError):
    """The Soundflow tables have not been created in the Supabase project."""


@dataclass
class CloudUser:
    id: str
    email: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def display_name(self) -> str:
        name = str(self.metadata.get("full_name") or self.metadata.get("name") or "")
        return name.strip() or self.email

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> CloudUser:
        return cls(
            id=str(payload.get("id", "")),
            email=str(payload.get("email", "") or ""),
            metadata=dict(payload.get("user_metadata") or payload.get("metadata") or {}),
        )

    def to_json(self) -> dict[str, Any]:
        return {"id": self.id, "email": self.email, "user_metadata": self.metadata}


@dataclass
class AuthSession:
    access_token: str
    refresh_token: str
    expires_at: float
    user: CloudUser

    def expires_soon(self, margin_s: float = 60.0) -> bool:
        return time.time() >= self.expires_at - margin_s

    @classmethod
    def from_token_response(cls, payload: dict[str, Any]) -> AuthSession:
        access = payload.get("access_token")
        refresh = payload.get("refresh_token")
        if not access or not refresh or not isinstance(payload.get("user"), dict):
            raise CloudError("Supabase returned an incomplete session.")
        expires_at = payload.get("expires_at")
        if not expires_at:
            expires_at = time.time() + float(payload.get("expires_in", 3600))
        return cls(
            access_token=str(access),
            refresh_token=str(refresh),
            expires_at=float(expires_at),
            user=CloudUser.from_json(payload["user"]),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
            "user": self.user.to_json(),
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> AuthSession:
        return cls(
            access_token=str(payload["access_token"]),
            refresh_token=str(payload["refresh_token"]),
            expires_at=float(payload["expires_at"]),
            user=CloudUser.from_json(payload["user"]),
        )


@dataclass
class SignUpResult:
    """``session`` is None when Supabase requires e-mail confirmation first."""

    session: AuthSession | None
    user: CloudUser | None
    already_registered: bool = False


# Messages shown to people instead of raw GoTrue codes.
_FRIENDLY = {
    "invalid_credentials": "Wrong email or password.",
    "email_not_confirmed": (
        "Please confirm your email first. Open the link we sent you, then sign in."
    ),
    "user_already_exists": "An account with this email already exists. Sign in instead.",
    "email_exists": "An account with this email already exists. Sign in instead.",
    "weak_password": "That password is too weak. Use at least 8 characters.",
    "over_email_send_rate_limit": "Too many emails sent. Wait a minute and try again.",
    "over_request_rate_limit": "Too many attempts. Wait a minute and try again.",
    "signup_disabled": "New sign-ups are currently disabled.",
    "validation_failed": "Please check the email address.",
    "refresh_token_not_found": "Your session expired. Please sign in again.",
    "refresh_token_already_used": "Your session expired. Please sign in again.",
    "session_not_found": "Your session expired. Please sign in again.",
}


def _error_from_http(exc: urllib.error.HTTPError, auth_endpoint: bool) -> CloudError:
    try:
        payload = json.loads(exc.read().decode("utf-8", errors="replace"))
    except (ValueError, OSError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    code = str(payload.get("error_code") or payload.get("code") or payload.get("error") or "")
    message = str(
        payload.get("msg")
        or payload.get("message")
        or payload.get("error_description")
        or f"HTTP {exc.code}"
    )[:300]
    if code in ("PGRST205", "42P01") or "Could not find the table" in message:
        return SchemaMissing(
            "Soundflow's cloud tables are missing. Run "
            "supabase/migrations/0001_soundflow_cloud.sql in the Supabase SQL editor."
        )
    friendly = _FRIENDLY.get(code)
    if auth_endpoint and (exc.code in (400, 401, 403, 422) or code in _FRIENDLY):
        return AuthError(friendly or message, code)
    if exc.code == 401:
        # PostgREST: the access token expired or was revoked.
        return AuthError("Your session expired. Please sign in again.", code or "jwt_expired")
    return CloudError(friendly or message)


class SupabaseClient:
    def __init__(self, url: str | None = None, key: str | None = None) -> None:
        self.url = (url or supabase_url()).rstrip("/")
        self.key = key or supabase_key()

    # -- transport --------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Any = None,
        token: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        data = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}{path}", data=data, method=method
        )
        request.add_header("apikey", self.key)
        request.add_header("Authorization", f"Bearer {token or self.key}")
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        for name, value in (headers or {}).items():
            request.add_header(name, value)
        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            raise _error_from_http(exc, path.startswith("/auth/")) from exc
        except urllib.error.URLError as exc:
            raise NetworkError(f"Could not reach Soundflow cloud: {exc.reason}") from exc
        except (TimeoutError, OSError) as exc:
            raise NetworkError(f"Could not reach Soundflow cloud: {exc}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError as exc:
            raise CloudError("Soundflow cloud sent an unreadable response.") from exc

    # -- auth -------------------------------------------------------------
    def sign_up(
        self, email: str, password: str, full_name: str, gender: str
    ) -> SignUpResult:
        payload = self._request(
            "POST",
            "/auth/v1/signup",
            body={
                "email": email,
                "password": password,
                "data": {"full_name": full_name, "gender": gender},
            },
        ) or {}
        if payload.get("access_token"):
            return SignUpResult(AuthSession.from_token_response(payload), None)
        user_json = payload.get("user") if isinstance(payload.get("user"), dict) else payload
        user = CloudUser.from_json(user_json) if user_json.get("id") else None
        # With e-mail confirmation on, GoTrue hides existing accounts by
        # returning a user with no identities instead of an error.
        already = isinstance(user_json.get("identities"), list) and not user_json["identities"]
        return SignUpResult(None, user, already_registered=already)

    def sign_in_with_password(self, email: str, password: str) -> AuthSession:
        payload = self._request(
            "POST",
            "/auth/v1/token?grant_type=password",
            body={"email": email, "password": password},
        )
        return AuthSession.from_token_response(payload or {})

    def refresh(self, refresh_token: str) -> AuthSession:
        payload = self._request(
            "POST",
            "/auth/v1/token?grant_type=refresh_token",
            body={"refresh_token": refresh_token},
        )
        return AuthSession.from_token_response(payload or {})

    def send_password_reset(self, email: str) -> None:
        self._request("POST", "/auth/v1/recover", body={"email": email})

    def resend_confirmation(self, email: str) -> None:
        self._request("POST", "/auth/v1/resend", body={"type": "signup", "email": email})

    def sign_out(self, access_token: str) -> None:
        self._request("POST", "/auth/v1/logout", token=access_token)

    def update_user_metadata(self, access_token: str, data: dict[str, Any]) -> CloudUser:
        payload = self._request("PUT", "/auth/v1/user", body={"data": data}, token=access_token)
        return CloudUser.from_json(payload or {})

    # -- data -------------------------------------------------------------
    def get_profile(self, access_token: str, user_id: str) -> dict[str, Any] | None:
        rows = self._request(
            "GET",
            f"/rest/v1/profiles?id=eq.{urllib.parse.quote(user_id)}&select=*",
            token=access_token,
        )
        return rows[0] if rows else None

    def upsert_profile(
        self, access_token: str, user_id: str, full_name: str, gender: str
    ) -> None:
        self._request(
            "POST",
            "/rest/v1/profiles?on_conflict=id",
            body=[{"id": user_id, "full_name": full_name, "gender": gender}],
            token=access_token,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    def upsert_transcripts(self, access_token: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self._request(
            "POST",
            "/rest/v1/transcripts?on_conflict=id",
            body=rows,
            token=access_token,
            headers={"Prefer": "resolution=merge-duplicates,return=minimal"},
        )

    def mark_transcripts_deleted(
        self, access_token: str, ids: list[str], deleted_at: str
    ) -> None:
        if not ids:
            return
        id_list = ",".join(urllib.parse.quote(i) for i in ids)
        self._request(
            "PATCH",
            f"/rest/v1/transcripts?id=in.({id_list})",
            body={"deleted_at": deleted_at},
            token=access_token,
            headers={"Prefer": "return=minimal"},
        )

    def transcripts_changed_since(
        self, access_token: str, cursor: str | None, limit: int = 500
    ) -> list[dict[str, Any]]:
        query = f"select=*&order=updated_at.asc,id.asc&limit={int(limit)}"
        if cursor:
            query += f"&updated_at=gt.{urllib.parse.quote(cursor)}"
        return self._request("GET", f"/rest/v1/transcripts?{query}", token=access_token) or []


__all__ = [
    "AuthError",
    "AuthSession",
    "CloudError",
    "CloudUser",
    "NetworkError",
    "SchemaMissing",
    "SignUpResult",
    "SupabaseClient",
]
