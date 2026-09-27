"""OAuth2 login + credential refresh for the Gmail API.

Works identically for personal Gmail accounts and Google Workspace
accounts - both are the same Gmail API, just gated by different OAuth
consent-screen/org policies on Google's side. See docs/SETUP.md.
"""

from __future__ import annotations

import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from gmail_mailbox_config import SCOPES, client_config, token_path


class NotAuthenticatedError(RuntimeError):
    pass


def run_login_flow(port: int = 0) -> Credentials:
    """Interactive, browser-based OAuth login. Run once from a CLI with a
    browser available (``hermes gmail-mailbox login``); stores a refresh
    token so later runs are non-interactive.
    """
    flow = InstalledAppFlow.from_client_config(client_config(), SCOPES)
    creds = flow.run_local_server(port=port)
    token_path().write_text(creds.to_json())
    return creds


def load_credentials() -> Credentials:
    """Loaded, refreshed credentials, or raises NotAuthenticatedError."""
    path = token_path()
    if not path.exists():
        raise NotAuthenticatedError(
            "No Gmail credentials found. Run `hermes gmail-mailbox login` once "
            "to connect this mailbox."
        )
    creds = Credentials.from_authorized_user_info(json.loads(path.read_text()), SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.write_text(creds.to_json())
        return creds
    raise NotAuthenticatedError(
        "Stored Gmail credentials are invalid and cannot be refreshed. "
        "Run `hermes gmail-mailbox login` again."
    )


def is_authenticated() -> bool:
    try:
        load_credentials()
        return True
    except NotAuthenticatedError:
        return False
