"""Shared paths and environment helpers for the gmail-mailbox plugin.

Imported by both the CLI/gateway side (__init__.py, tools.py, auth.py,
client.py, store.py) and the dashboard backend (dashboard/plugin_api.py),
so both halves of the plugin agree on where credentials and cached data
live on disk.
"""

from __future__ import annotations

import os
from pathlib import Path

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
]


def hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def plugin_dir() -> Path:
    path = hermes_home() / "plugins" / "gmail-mailbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def data_dir() -> Path:
    path = plugin_dir() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def token_path() -> Path:
    return plugin_dir() / "token.json"


def db_path() -> Path:
    return data_dir() / "mailbox.db"


def account_label() -> str:
    return os.environ.get("GMAIL_ACCOUNT_LABEL", "").strip() or "gmail"


def client_config() -> dict:
    client_id = os.environ.get("GMAIL_OAUTH_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GMAIL_OAUTH_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError(
            "GMAIL_OAUTH_CLIENT_ID / GMAIL_OAUTH_CLIENT_SECRET are not set. "
            "Follow docs/SETUP.md, then re-run `hermes plugins enable gmail-mailbox` "
            "or export both variables before starting Hermes."
        )
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
