"""Thin wrapper around the Gmail REST API (v1) used by both the agent
tools (tools.py) and the dashboard backend (dashboard/plugin_api.py).
"""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from typing import Any, Optional

from googleapiclient.discovery import build

from gmail_mailbox_auth import load_credentials

_HEADER_KEYS = ("Subject", "From", "To", "Date", "Message-Id", "References")


def _service():
    return build("gmail", "v1", credentials=load_credentials(), cache_discovery=False)


def _headers_dict(payload: dict) -> dict:
    out = {}
    for h in payload.get("headers", []):
        name = h.get("name", "")
        if name in _HEADER_KEYS:
            out[name] = h.get("value", "")
    return out


def _extract_plain_text(payload: dict) -> str:
    """Walk the MIME tree and return the first text/plain part, falling
    back to a stripped text/html part if no plain-text part exists.
    """
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    html_fallback = None
    for part in payload.get("parts", []) or []:
        text = _extract_plain_text(part)
        if text:
            if part.get("mimeType") == "text/html" and html_fallback is None:
                html_fallback = text
            else:
                return text

    if mime_type == "text/html" and body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")

    return html_fallback or ""


def _attachments(payload: dict) -> list[dict]:
    found = []
    for part in payload.get("parts", []) or []:
        filename = part.get("filename")
        body = part.get("body", {})
        if filename and body.get("attachmentId"):
            found.append(
                {
                    "filename": filename,
                    "mime_type": part.get("mimeType", ""),
                    "attachment_id": body["attachmentId"],
                    "size_bytes": body.get("size", 0),
                }
            )
        found.extend(_attachments(part))
    return found


def list_labels() -> list[dict]:
    service = _service()
    resp = service.users().labels().list(userId="me").execute()
    labels = []
    for label in resp.get("labels", []):
        detail = (
            service.users()
            .labels()
            .get(userId="me", id=label["id"])
            .execute()
        )
        labels.append(
            {
                "id": detail["id"],
                "name": detail["name"],
                "type": detail.get("type", "user"),
                "messages_total": detail.get("messagesTotal", 0),
                "messages_unread": detail.get("messagesUnread", 0),
            }
        )
    return labels


def list_messages(query: str = "", label_ids: Optional[list[str]] = None, max_results: int = 25) -> list[dict]:
    service = _service()
    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query or None, labelIds=label_ids or None, maxResults=max_results)
        .execute()
    )
    items = []
    for ref in resp.get("messages", []):
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="metadata", metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        headers = _headers_dict(msg["payload"])
        items.append(
            {
                "id": msg["id"],
                "thread_id": msg["threadId"],
                "subject": headers.get("Subject", "(no subject)"),
                "from": headers.get("From", ""),
                "date": headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
                "unread": "UNREAD" in msg.get("labelIds", []),
                "labels": msg.get("labelIds", []),
            }
        )
    return items


def get_message(message_id: str) -> dict:
    service = _service()
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = _headers_dict(msg["payload"])
    return {
        "id": msg["id"],
        "thread_id": msg["threadId"],
        "subject": headers.get("Subject", "(no subject)"),
        "from": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "message_id_header": headers.get("Message-Id", ""),
        "references_header": headers.get("References", ""),
        "unread": "UNREAD" in msg.get("labelIds", []),
        "labels": msg.get("labelIds", []),
        "body_text": _extract_plain_text(msg["payload"]),
        "attachments": _attachments(msg["payload"]),
    }


def _build_raw_message(
    to: str,
    subject: str,
    body_text: str,
    thread_headers: Optional[dict] = None,
) -> dict:
    mime_msg = MIMEText(body_text)
    mime_msg["to"] = to
    mime_msg["subject"] = subject
    if thread_headers:
        if thread_headers.get("message_id_header"):
            mime_msg["In-Reply-To"] = thread_headers["message_id_header"]
            refs = f"{thread_headers.get('references_header', '')} {thread_headers['message_id_header']}".strip()
            mime_msg["References"] = refs
    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode()
    payload: dict[str, Any] = {"raw": raw}
    if thread_headers and thread_headers.get("thread_id"):
        payload["threadId"] = thread_headers["thread_id"]
    return payload


def create_draft(to: str, subject: str, body_text: str, in_reply_to_message_id: Optional[str] = None) -> dict:
    thread_headers = get_message(in_reply_to_message_id) if in_reply_to_message_id else None
    payload = _build_raw_message(to, subject, body_text, thread_headers)
    service = _service()
    draft = service.users().drafts().create(userId="me", body={"message": payload}).execute()
    return {"draft_id": draft["id"], "message_id": draft["message"]["id"]}


def send_draft(draft_id: str) -> dict:
    service = _service()
    sent = service.users().drafts().send(userId="me", body={"id": draft_id}).execute()
    return {"message_id": sent["id"], "thread_id": sent["threadId"]}


def send_message(to: str, subject: str, body_text: str, in_reply_to_message_id: Optional[str] = None) -> dict:
    thread_headers = get_message(in_reply_to_message_id) if in_reply_to_message_id else None
    payload = _build_raw_message(to, subject, body_text, thread_headers)
    service = _service()
    sent = service.users().messages().send(userId="me", body=payload).execute()
    return {"message_id": sent["id"], "thread_id": sent["threadId"]}
