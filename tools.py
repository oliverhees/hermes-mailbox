"""Agent-facing tool schemas + handlers, registered on Hermes by __init__.py.

Every handler takes the tool-call params dict and returns a JSON string
(the convention Hermes plugin tools use), so the agent always gets a
predictable, model-readable result.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

import client
import store
from auth import NotAuthenticatedError
from config import account_label


def _ok(data) -> str:
    return json.dumps({"ok": True, "account": account_label(), "data": data}, ensure_ascii=False)


def _err(message: str) -> str:
    return json.dumps({"ok": False, "account": account_label(), "error": message}, ensure_ascii=False)


def _guarded(fn):
    def wrapped(params: dict, **_kwargs) -> str:
        try:
            return fn(params or {})
        except NotAuthenticatedError as exc:
            return _err(str(exc))
        except Exception as exc:  # noqa: BLE001 - surface any API error to the agent as data, not a crash
            return _err(f"{type(exc).__name__}: {exc}")

    return wrapped


@_guarded
def gmail_list_messages(params: dict) -> str:
    messages = client.list_messages(
        query=params.get("query", ""),
        label_ids=params.get("label_ids"),
        max_results=int(params.get("max_results", 25)),
    )
    return _ok(messages)


@_guarded
def gmail_search_messages(params: dict) -> str:
    query = params.get("query", "")
    if not query:
        return _err("query is required, e.g. 'is:unread newer_than:1d'")
    messages = client.list_messages(query=query, max_results=int(params.get("max_results", 25)))
    return _ok(messages)


@_guarded
def gmail_get_message(params: dict) -> str:
    message_id = params.get("message_id")
    if not message_id:
        return _err("message_id is required")
    return _ok(client.get_message(message_id))


@_guarded
def gmail_list_labels(params: dict) -> str:
    return _ok(client.list_labels())


@_guarded
def gmail_create_draft(params: dict) -> str:
    to = params.get("to")
    subject = params.get("subject", "")
    body = params.get("body", "")
    if not to or not body:
        return _err("to and body are required")
    result = client.create_draft(to, subject, body, in_reply_to_message_id=params.get("in_reply_to_message_id"))
    return _ok(result)


@_guarded
def gmail_reply(params: dict) -> str:
    message_id = params.get("message_id")
    body = params.get("body")
    if not message_id or not body:
        return _err("message_id and body are required")
    original = client.get_message(message_id)
    to = params.get("to") or original["from"]
    subject = original["subject"]
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    if params.get("send"):
        result = client.send_message(to, subject, body, in_reply_to_message_id=message_id)
    else:
        result = client.create_draft(to, subject, body, in_reply_to_message_id=message_id)
    return _ok(result)


@_guarded
def gmail_send_message(params: dict) -> str:
    to = params.get("to")
    subject = params.get("subject", "")
    body = params.get("body", "")
    if not to or not body:
        return _err("to and body are required")
    result = client.send_message(to, subject, body, in_reply_to_message_id=params.get("in_reply_to_message_id"))
    return _ok(result)


@_guarded
def gmail_sync_stats(params: dict) -> str:
    """Refresh the local cache the dashboard's Mailbox tab reads from.
    Call this before writing a report, and on a recurring cron job.
    """
    labels = client.list_labels()
    by_label = {label["name"]: label["messages_unread"] for label in labels}
    inbox = next((l for l in labels if l["id"] == "INBOX"), None)
    unread_count = inbox["messages_unread"] if inbox else 0

    today_messages = client.list_messages(query="newer_than:1d", max_results=200)
    total_today = len(today_messages)
    senders = Counter()
    for msg in today_messages:
        senders[msg["from"]] += 1
    top_senders = [{"from": sender, "count": count} for sender, count in senders.most_common(10)]

    store.save_stats_snapshot(unread_count, total_today, by_label, top_senders)
    return _ok(
        {
            "unread_count": unread_count,
            "total_today": total_today,
            "by_label": by_label,
            "top_senders": top_senders,
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@_guarded
def gmail_save_report(params: dict) -> str:
    """Store a written report (e.g. the daily briefing) so it shows up in
    the dashboard's Mailbox tab. Call gmail_sync_stats first so the report
    and the stats cards agree.
    """
    title = params.get("title", "").strip()
    body = params.get("body", "").strip()
    if not title or not body:
        return _err("title and body are required")
    report_id = store.save_report(title, body)
    return _ok({"report_id": report_id})


@_guarded
def gmail_list_pending_requests(params: dict) -> str:
    """Requests queued from the dashboard (e.g. a user clicked 'let the
    agent draft this'). Drain this list, act on each one, then call
    gmail_complete_request. Wire a cron job to do this periodically.
    """
    status = params.get("status", "pending")
    return _ok(store.list_requests(status=status if status != "all" else None))


@_guarded
def gmail_complete_request(params: dict) -> str:
    request_id = params.get("request_id")
    if request_id is None:
        return _err("request_id is required")
    note = params.get("result_note", "")
    done = store.complete_request(int(request_id), note)
    if not done:
        return _err(f"no pending request with id {request_id}")
    return _ok({"request_id": request_id, "status": "done"})


TOOL_SCHEMAS: dict[str, dict] = {
    "gmail_list_messages": {
        "name": "gmail_list_messages",
        "description": "List recent Gmail messages, optionally filtered by Gmail search query or label ids.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Gmail search syntax, e.g. 'is:unread from:boss@x.com'"},
                "label_ids": {"type": "array", "items": {"type": "string"}, "description": "e.g. ['INBOX']"},
                "max_results": {"type": "integer", "description": "Default 25"},
            },
        },
    },
    "gmail_search_messages": {
        "name": "gmail_search_messages",
        "description": "Search Gmail using Gmail's search syntax (is:, from:, newer_than:, has:attachment, ...).",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Required Gmail search query"},
                "max_results": {"type": "integer"},
            },
            "required": ["query"],
        },
    },
    "gmail_get_message": {
        "name": "gmail_get_message",
        "description": "Fetch the full content (headers, plain-text body, attachment list) of one message.",
        "parameters": {
            "type": "object",
            "properties": {"message_id": {"type": "string"}},
            "required": ["message_id"],
        },
    },
    "gmail_list_labels": {
        "name": "gmail_list_labels",
        "description": "List Gmail labels/categories with unread and total message counts.",
        "parameters": {"type": "object", "properties": {}},
    },
    "gmail_create_draft": {
        "name": "gmail_create_draft",
        "description": "Create a draft email. Pass in_reply_to_message_id to keep it threaded as a reply.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
                "in_reply_to_message_id": {"type": "string"},
            },
            "required": ["to", "body"],
        },
    },
    "gmail_reply": {
        "name": "gmail_reply",
        "description": (
            "Reply to an existing message, threaded correctly. Set send=true to send immediately, "
            "otherwise a draft is created for the user to review."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "body": {"type": "string"},
                "to": {"type": "string", "description": "Override recipient; defaults to the original sender."},
                "send": {"type": "boolean", "description": "Default false (creates a draft instead)."},
            },
            "required": ["message_id", "body"],
        },
    },
    "gmail_send_message": {
        "name": "gmail_send_message",
        "description": "Send a new email immediately (not a reply).",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "body"],
        },
    },
    "gmail_sync_stats": {
        "name": "gmail_sync_stats",
        "description": "Refresh unread/today/label counters that power the dashboard's Mailbox tab.",
        "parameters": {"type": "object", "properties": {}},
    },
    "gmail_save_report": {
        "name": "gmail_save_report",
        "description": "Save a written report (e.g. a daily briefing) so it appears in the dashboard's Mailbox tab.",
        "parameters": {
            "type": "object",
            "properties": {"title": {"type": "string"}, "body": {"type": "string"}},
            "required": ["title", "body"],
        },
    },
    "gmail_list_pending_requests": {
        "name": "gmail_list_pending_requests",
        "description": "List user-created requests from the dashboard (e.g. 'draft a reply to this'). Default: pending only.",
        "parameters": {
            "type": "object",
            "properties": {"status": {"type": "string", "description": "'pending' (default), 'done', or 'all'"}},
        },
    },
    "gmail_complete_request": {
        "name": "gmail_complete_request",
        "description": "Mark a dashboard request as handled after acting on it.",
        "parameters": {
            "type": "object",
            "properties": {
                "request_id": {"type": "integer"},
                "result_note": {"type": "string", "description": "e.g. 'created draft d123'"},
            },
            "required": ["request_id"],
        },
    },
}

TOOL_HANDLERS = {
    "gmail_list_messages": gmail_list_messages,
    "gmail_search_messages": gmail_search_messages,
    "gmail_get_message": gmail_get_message,
    "gmail_list_labels": gmail_list_labels,
    "gmail_create_draft": gmail_create_draft,
    "gmail_reply": gmail_reply,
    "gmail_send_message": gmail_send_message,
    "gmail_sync_stats": gmail_sync_stats,
    "gmail_save_report": gmail_save_report,
    "gmail_list_pending_requests": gmail_list_pending_requests,
    "gmail_complete_request": gmail_complete_request,
}
