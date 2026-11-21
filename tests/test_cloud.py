import gc
import io
import json
import os
import sqlite3
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from soundflow.cloud.account import Account, SessionStore
from soundflow.cloud.client import (
    AuthError,
    AuthSession,
    CloudError,
    CloudUser,
    SchemaMissing,
    SupabaseClient,
)
from soundflow.cloud.sync import sync_once
from soundflow.history.store import HistoryStore

LEGACY_SCHEMA = """
CREATE TABLE transcripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
    duration_s REAL NOT NULL DEFAULT 0, title TEXT NOT NULL,
    summary TEXT NOT NULL, body TEXT NOT NULL);
"""


def make_session(user_id="u1", expires_in=3600.0, token="access") -> AuthSession:
    return AuthSession(
        access_token=token,
        refresh_token="refresh",
        expires_at=time.time() + expires_in,
        user=CloudUser(id=user_id, email=f"{user_id}@example.com", metadata={"full_name": "Ada"}),
    )


class FakeClient:
    def __init__(self):
        self.remote: dict[str, dict] = {}
        self.clock = 0
        self.refreshes = 0
        self.refresh_error: Exception | None = None

    def _stamp(self) -> str:
        self.clock += 1
        return f"2026-01-01T00:00:{self.clock:02d}+00:00"

    def refresh(self, _token):
        self.refreshes += 1
        if self.refresh_error:
            raise self.refresh_error
        return make_session(token=f"access{self.refreshes}")

    def upsert_transcripts(self, _token, rows):
        for row in rows:
            self.remote[row["id"]] = {**row, "updated_at": self._stamp()}

    def mark_transcripts_deleted(self, _token, ids, deleted_at):
        for uid in ids:
            if uid in self.remote:
                self.remote[uid].update(deleted_at=deleted_at, updated_at=self._stamp())

    def transcripts_changed_since(self, _token, cursor, limit=500):
        rows = sorted(self.remote.values(), key=lambda r: r["updated_at"])
        return [r for r in rows if cursor is None or r["updated_at"] > cursor][:limit]


class MemorySessionStore(SessionStore):
    def __init__(self, session=None):
        self._value = session

    def load(self):
        return self._value

    def save(self, session):
        self._value = session

    def clear(self):
        self._value = None


class HistoryStoreCloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "history.db"

    def tearDown(self):
        self.tmp.cleanup()

    def test_legacy_database_is_migrated_and_claimed(self):
        conn = sqlite3.connect(self.path)
        conn.executescript(LEGACY_SCHEMA)
        conn.execute(
            "INSERT INTO transcripts (created_at, duration_s, title, summary, body)"
            " VALUES ('2026-01-01T10:00:00', 3, 'Old', 'Old', 'Old note')"
        )
        conn.commit()
        conn.close()

        store = HistoryStore(self.path, user_id="u1")
        self.assertEqual(store.count(), 0)  # not yet owned by anyone
        self.assertEqual(store.claim_unowned("u1"), 1)
        self.assertEqual(store.count(), 1)
        pending = store.pending_uploads()
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(pending[0]["uuid"]), 36)
        self.assertTrue(pending[0]["payload"]["created_at"].endswith("+00:00"))
        self.assertEqual(store.claim_unowned("u2"), 0)
        store.close()

    def test_users_only_see_their_own_rows(self):
        a = HistoryStore(self.path, user_id="a")
        b = HistoryStore(self.path, user_id="b")
        entry = a.add("alpha words")
        b.add("bravo words")
        self.assertEqual([e.body for e in a.list_entries()], ["alpha words"])
        self.assertIsNone(b.get(entry.id))
        b.delete(entry.id)  # must not delete another user's row
        self.assertIsNotNone(a.get(entry.id))
        self.assertEqual(a.today_stats()[0], 1)
        a.close()
        b.close()

    def test_edit_during_upload_stays_pending(self):
        store = HistoryStore(self.path, user_id="u1")
        entry = store.add("first")
        snapshot = store.pending_uploads()
        store.update(entry.id, "second")
        store.mark_uploaded({i["uuid"]: i["local_rev"] for i in snapshot})
        again = store.pending_uploads()
        self.assertEqual([i["payload"]["body"] for i in again], ["second"])
        store.close()

    def test_change_callback_fires(self):
        store = HistoryStore(self.path, user_id="u1")
        calls = []
        store.on_change = lambda: calls.append(1)
        entry = store.add("x")
        store.update(entry.id, "y")
        store.delete(entry.id)
        self.assertEqual(len(calls), 3)
        store.close()


class SyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "history.db"
        self.client = FakeClient()

    def tearDown(self):
        self.tmp.cleanup()

    def account(self):
        return Account(self.client, MemorySessionStore(make_session()))

    def test_round_trip_between_two_devices(self):
        laptop = HistoryStore(self.path, user_id="u1")
        other_path = Path(self.tmp.name) / "other.db"
        desktop = HistoryStore(other_path, user_id="u1")
        account = self.account()

        kept = laptop.add("keep me")
        gone = laptop.add("delete me")
        report = sync_once(laptop, account)
        self.assertEqual(report.uploaded, 2)
        self.assertEqual(laptop.pending_uploads(), [])

        report = sync_once(desktop, account)
        self.assertEqual(report.pulled, 2)
        self.assertEqual(sorted(e.body for e in desktop.list_entries()), ["delete me", "keep me"])

        laptop.delete(gone.id)
        laptop.update(kept.id, "keep me, edited")
        sync_once(laptop, account)
        sync_once(desktop, account)
        self.assertEqual([e.body for e in desktop.list_entries()], ["keep me, edited"])
        self.assertEqual(sync_once(laptop, account).pulled, 0)  # own echo is not a change
        laptop.close()
        desktop.close()

    def test_pending_local_edit_wins_over_remote(self):
        store = HistoryStore(self.path, user_id="u1")
        entry = store.add("local")
        account = self.account()
        sync_once(store, account)
        uid = store.pending_uploads() or None
        self.assertIsNone(uid)
        store.update(entry.id, "local edit")
        remote_id = next(iter(self.client.remote))
        self.client.remote[remote_id].update(
            body="remote edit", updated_at="2026-01-01T00:00:59+00:00"
        )
        changed = store.apply_remote([self.client.remote[remote_id]])
        self.assertEqual(changed, 0)
        self.assertEqual(store.get(entry.id).body, "local edit")
        store.close()


class AccountTests(unittest.TestCase):
    def test_expired_token_is_refreshed(self):
        client = FakeClient()
        account = Account(client, MemorySessionStore(make_session(expires_in=-5)))
        self.assertEqual(account.access_token(), "access1")
        self.assertEqual(account.access_token(), "access1")
        self.assertEqual(client.refreshes, 1)

    def test_rejected_refresh_signs_out(self):
        client = FakeClient()
        client.refresh_error = AuthError("expired", "refresh_token_not_found")
        account = Account(client, MemorySessionStore(make_session(expires_in=-5)))
        self.assertFalse(account.restore())
        self.assertFalse(account.is_signed_in())

    def test_offline_keeps_cached_session(self):
        from soundflow.cloud.client import NetworkError

        client = FakeClient()
        client.refresh_error = NetworkError("offline")
        account = Account(client, MemorySessionStore(make_session(expires_in=-5)))
        self.assertTrue(account.restore())
        self.assertTrue(account.is_signed_in())

    @unittest.skipIf(os.name == "nt", "POSIX permissions")
    def test_session_file_is_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = SessionStore(Path(tmp) / "session.json")
            store.save(make_session())
            self.assertEqual(os.stat(store.path).st_mode & 0o777, 0o600)
            self.assertEqual(store.load().user.id, "u1")
            store.clear()
            self.assertIsNone(store.load())


def _http_error(code: int, payload: dict) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://x", code, "err", {}, io.BytesIO(json.dumps(payload).encode())
    )


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.client = SupabaseClient("https://example.supabase.co", "sb_publishable_test")

    def test_wrong_password_is_friendly_auth_error(self):
        error = _http_error(400, {"code": 400, "error_code": "invalid_credentials", "msg": "x"})
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(AuthError) as ctx:
                self.client.sign_in_with_password("a@b.co", "pw")
        self.assertEqual(str(ctx.exception), "Wrong email or password.")

    def test_rest_400_is_not_treated_as_sign_out(self):
        error = _http_error(400, {"code": "22P02", "message": "bad uuid"})
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(CloudError) as ctx:
                self.client.upsert_transcripts("tok", [{"id": "x"}])
        self.assertNotIsInstance(ctx.exception, AuthError)

    def test_missing_table_is_reported(self):
        error = _http_error(404, {"code": "PGRST205", "message": "Could not find the table"})
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(SchemaMissing):
                self.client.transcripts_changed_since("tok", None)

    def test_sign_up_detects_existing_account(self):
        body = json.dumps({"id": "u9", "email": "a@b.co", "identities": []}).encode()
        with patch("urllib.request.urlopen", return_value=_Response(body)) as opened:
            result = self.client.sign_up("a@b.co", "password1", "Ada", "female")
        self.assertTrue(result.already_registered)
        self.assertIsNone(result.session)
        sent = json.loads(opened.call_args[0][0].data)
        self.assertEqual(sent["data"], {"full_name": "Ada", "gender": "female"})

    def test_sign_up_needing_confirmation(self):
        body = json.dumps({"id": "u9", "email": "a@b.co", "identities": [{"id": "i"}]}).encode()
        with patch("urllib.request.urlopen", return_value=_Response(body)):
            result = self.client.sign_up("a@b.co", "password1", "Ada", "male")
        self.assertFalse(result.already_registered)
        self.assertIsNone(result.session)
        self.assertEqual(result.user.id, "u9")


class ProfileRepairTests(unittest.TestCase):
    def make_account(self, profile, metadata):
        class Client(FakeClient):
            def __init__(self):
                super().__init__()
                self.upserts = []

            def get_profile(self, _token, _uid):
                return profile

            def upsert_profile(self, _token, uid, name, gender):
                self.upserts.append((uid, name, gender))

        session = make_session()
        session.user.metadata = metadata
        client = Client()
        return Account(client, MemorySessionStore(session)), client

    def test_missing_profile_is_created_from_sign_up_details(self):
        account, client = self.make_account(None, {"full_name": "Ada", "gender": "female"})
        self.assertTrue(account.ensure_profile())
        self.assertEqual(client.upserts, [("u1", "Ada", "female")])

    def test_complete_profile_is_left_alone(self):
        account, client = self.make_account(
            {"full_name": "Ada", "gender": "female"}, {"full_name": "Ada", "gender": "female"}
        )
        self.assertFalse(account.ensure_profile())
        self.assertEqual(client.upserts, [])


class _AuthStub:
    """Stands in for the Supabase client; records calls, never touches the network."""

    def __init__(self, session_on_sign_up=None):
        self.calls: list[tuple] = []
        self.session_on_sign_up = session_on_sign_up

    def sign_up(self, email, password, name, gender):
        from soundflow.cloud.client import SignUpResult

        self.calls.append(("sign_up", email, name, gender))
        return SignUpResult(self.session_on_sign_up, None)

    def send_password_reset(self, email):
        self.calls.append(("reset", email))

    def resend_confirmation(self, email):
        self.calls.append(("resend", email))


class AuthDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication

        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialogs = []

    def tearDown(self):
        from PySide6.QtCore import QCoreApplication, QEvent

        for dialog in self.dialogs:
            dialog.close()
            dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        gc.collect()

    def _dialog(self, client):
        from soundflow.auth import AuthDialog

        dialog = AuthDialog(Account(client, MemorySessionStore()))
        self.dialogs.append(dialog)
        return dialog

    def _wait_until(self, condition, seconds=3.0):
        import time

        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.app.processEvents()
            if condition():
                return True
            time.sleep(0.01)
        return False

    def test_sign_up_validates_before_network(self):
        client = _AuthStub()
        client.sign_up = lambda *a: self.fail("should not reach the network")
        dialog = self._dialog(client)
        dialog.up_name.setText("Ada")
        dialog.up_email.setText("ada@example.com")
        dialog.up_password.setText("password1")
        dialog.up_confirm.setText("password2")
        dialog._sign_up()
        self.assertIn("don't match", dialog.status.text())
        dialog.up_confirm.setText("password1")
        dialog._sign_up()
        self.assertIn("male or female", dialog.status.text())

    def test_gender_is_not_preselected(self):
        dialog = self._dialog(_AuthStub())
        self.assertEqual(dialog.up_gender.value(), "")
        dialog.up_gender.button("female").click()
        self.assertEqual(dialog.up_gender.value(), "female")

    def test_sign_up_without_session_shows_confirm_screen(self):
        client = _AuthStub(session_on_sign_up=None)
        dialog = self._dialog(client)
        dialog.up_name.setText("Ada")
        dialog.up_email.setText("Ada@Example.com")
        dialog.up_password.setText("password1")
        dialog.up_confirm.setText("password1")
        dialog.up_gender.button("female").click()
        dialog._sign_up()
        self.assertTrue(
            self._wait_until(lambda: dialog.pages.currentWidget() is dialog.check_email_page)
        )
        self.assertEqual(client.calls, [("sign_up", "ada@example.com", "Ada", "female")])
        self.assertIn("ada@example.com", dialog.check_email_label.text())

    def test_password_eye_shows_and_hides_the_password(self):
        from PySide6.QtWidgets import QLineEdit

        dialog = self._dialog(_AuthStub())
        for field in (dialog.in_password, dialog.up_password, dialog.up_confirm):
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
            field.reveal_action.trigger()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Normal)
            self.assertEqual(field.reveal_action.text(), "Hide password")
            field.reveal_action.trigger()
            self.assertEqual(field.echoMode(), QLineEdit.EchoMode.Password)
            self.assertEqual(field.reveal_action.text(), "Show password")

    def test_art_panel_is_a_still_magazine_cover(self):
        dialog = self._dialog(_AuthStub())
        art = dialog.art
        self.assertFalse(art.picture.isNull())
        self.assertEqual(art.masthead, "Soundflow")
        self.assertEqual(art.cover_line, ("Delulu ideas,", "perfectly spelled."))
        dialog.resize(1000, 640)
        dialog.show()
        self.app.processEvents()
        image = art.grab().toImage()
        self.assertGreater(image.width(), 300)
        # Painted, not black: the photo shows through behind the type.
        centre = image.pixelColor(image.width() // 2, image.height() // 2)
        self.assertGreater(centre.red() + centre.green() + centre.blue(), 60)

    def test_forgot_password_shows_reset_screen(self):
        client = _AuthStub()
        dialog = self._dialog(client)
        dialog.in_email.setText("ada@example.com")
        dialog._forgot_password()
        self.assertTrue(
            self._wait_until(lambda: dialog.pages.currentWidget() is dialog.reset_page)
        )
        self.assertEqual(client.calls, [("reset", "ada@example.com")])
        self.assertIn("ada@example.com", dialog.reset_email_label.text())

    def test_forgot_password_needs_an_email_first(self):
        client = _AuthStub()
        dialog = self._dialog(client)
        dialog._forgot_password()
        self.assertIn("Type your email", dialog.status.text())
        self.assertEqual(client.calls, [])


if __name__ == "__main__":
    unittest.main()
