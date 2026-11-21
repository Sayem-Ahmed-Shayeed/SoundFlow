import io
import json
import unittest
import urllib.error
from unittest.mock import patch

from soundflow.core.llm import (
    LlmError,
    build_messages,
    polish_text,
)
from soundflow.core.settings import Settings


def _settings(**overrides):
    values = {
        "ai_cleanup_enabled": True,
        "ai_provider": "openrouter",
        "openrouter_api_key": "sk-or-test",
        "openrouter_model": "openai/gpt-oss-20b:free",
        "gemini_api_key": "AIza-test",
        "gemini_model": "gemini-2.5-flash",
        "ai_preset": "clean",
        "ai_custom_instruction": "",
        "language": "bn",
    }
    values.update(overrides)
    return Settings(**{k: v for k, v in values.items() if k in Settings.__dataclass_fields__})


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _ok_payload(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}]}


class PolishTextTests(unittest.TestCase):
    def test_success_returns_trimmed_text(self):
        settings = _settings()
        with patch(
            "urllib.request.urlopen", return_value=FakeResponse(_ok_payload("  Clean. "))
        ) as opened:
            result = polish_text("raw um text", settings)
        self.assertEqual(result, "Clean.")
        request = opened.call_args[0][0]
        self.assertIn("openrouter.ai", request.full_url)
        self.assertTrue(request.get_header("Authorization").startswith("Bearer "))
        sent = json.loads(request.data.decode("utf-8"))
        self.assertEqual(sent["model"], "openai/gpt-oss-20b:free")
        self.assertEqual(len(sent["messages"]), 2)

    def test_missing_key_and_model_rejected_locally(self):
        with self.assertRaises(LlmError):
            polish_text("hello", _settings(openrouter_api_key=""))
        with self.assertRaises(LlmError):
            polish_text("hello", _settings(openrouter_model=""))
        with self.assertRaises(LlmError):
            polish_text("   ", _settings())

    def test_http_error_maps_to_friendly_message(self):
        settings = _settings()
        body = json.dumps({"error": {"message": "No auth"}}).encode("utf-8")
        error = urllib.error.HTTPError(
            "https://x", 401, "Unauthorized", {}, io.BytesIO(body)
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(LlmError) as raised:
                polish_text("hello", settings)
        self.assertIn("No auth", str(raised.exception))

    def test_empty_content_rejected(self):
        settings = _settings()
        with patch(
            "urllib.request.urlopen", return_value=FakeResponse(_ok_payload("   "))
        ):
            with self.assertRaises(LlmError):
                polish_text("hello", settings)


def _gemini_payload(text: str) -> dict:
    return {
        "candidates": [{"content": {"parts": [{"text": text}]}}],
    }


class GeminiTests(unittest.TestCase):
    def test_gemini_is_default_provider(self):
        settings = _settings(ai_provider="gemini")
        with patch(
            "urllib.request.urlopen",
            return_value=FakeResponse(_gemini_payload("Clean.")),
        ) as opened:
            result = polish_text("raw um text", settings)
        self.assertEqual(result, "Clean.")
        request = opened.call_args[0][0]
        self.assertIn("generativelanguage.googleapis.com", request.full_url)
        self.assertIn("gemini-2.5-flash", request.full_url)
        self.assertEqual(request.get_header("X-goog-api-key"), "AIza-test")
        sent = json.loads(request.data.decode("utf-8"))
        self.assertIn("system_instruction", sent)
        self.assertIn("contents", sent)

    def test_gemini_missing_key_rejected_locally(self):
        with self.assertRaises(LlmError):
            polish_text("hello", _settings(ai_provider="gemini", gemini_api_key=""))

    def test_gemini_error_maps_to_friendly_message(self):
        settings = _settings(ai_provider="gemini")
        body = json.dumps({"error": {"message": "API key expired"}}).encode("utf-8")
        error = urllib.error.HTTPError(
            "https://x", 400, "Bad Request", {}, io.BytesIO(body)
        )
        with patch("urllib.request.urlopen", side_effect=error):
            with self.assertRaises(LlmError) as raised:
                polish_text("hello", settings)
        self.assertIn("API key expired", str(raised.exception))

    def test_openrouter_still_routes_when_selected(self):
        settings = _settings(ai_provider="openrouter")
        with patch(
            "urllib.request.urlopen", return_value=FakeResponse(_ok_payload("Clean."))
        ) as opened:
            self.assertEqual(polish_text("raw", settings), "Clean.")
        self.assertIn("openrouter.ai", opened.call_args[0][0].full_url)


class MessageTests(unittest.TestCase):
    def test_clean_preset_mentions_fillers(self):
        messages = build_messages("hello", _settings(ai_preset="clean"))
        self.assertIn("filler", messages[0]["content"].lower())

    def test_language_hint_included(self):
        messages = build_messages("hello", _settings(language="bn"))
        self.assertIn("Bangla", messages[0]["content"])

    def test_custom_instruction_used(self):
        messages = build_messages(
            "hello", _settings(ai_preset="custom", ai_custom_instruction="Bullet it.")
        )
        self.assertIn("Bullet it.", messages[0]["content"])


if __name__ == "__main__":
    unittest.main()
