"""Supabase project used for Soundflow accounts and transcript sync.

The publishable key is designed to ship inside client apps; access to data is
enforced by the row-level-security policies in
``supabase/migrations/0001_soundflow_cloud.sql``. Never put a secret or
service-role key here.
"""

from __future__ import annotations

import os

DEFAULT_SUPABASE_URL = "https://iuqahybtopiftsfhjbuy.supabase.co"
DEFAULT_SUPABASE_KEY = "sb_publishable_p5Uw1dGj7fsO2riG7vdneA_oko4tQWL"


def supabase_url() -> str:
    return os.environ.get("SOUNDFLOW_SUPABASE_URL", DEFAULT_SUPABASE_URL).rstrip("/")


def supabase_key() -> str:
    return os.environ.get("SOUNDFLOW_SUPABASE_KEY", DEFAULT_SUPABASE_KEY)


__all__ = [
    "supabase_key",
    "supabase_url",
]
