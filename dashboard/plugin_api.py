"""Backend routes for the Mailbox dashboard tab.

Mounted by the Hermes dashboard process under /api/plugins/gmail-mailbox/.
Reuses the same auth/client/store modules the agent-side tools use (they
live one directory up, next to plugin.yaml), so the dashboard and the
agent always see the same mailbox and the same cached stats.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

_PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)
if _PLUGIN_ROOT not in sys.path:
    sys.path.insert(0, _PLUGIN_ROOT)

import client  # noqa: E402
import store  # noqa: E402
from auth import NotAuthenticatedError, is_authenticated  # noqa: E402
from config import account_label  # noqa: E402

router = APIRouter()


class NewRequest(BaseModel):
    message_id: str
    kind: str = "draft_reply"
    instructions: str = ""


@router.get("/status")
async def status():
    return {"authenticated": is_authenticated(), "account": account_label()}


@router.get("/stats")
async def stats(days: int = 14):
    return {
        "latest": store.get_latest_stats(),
        "history": store.get_stats_history(days=days),
    }


@router.get("/reports")
async def reports(limit: int = 5):
    return {"reports": store.get_recent_reports(limit=limit)}


@router.get("/messages")
async def messages(query: str = "", max_results: int = 25):
    try:
        return {"messages": client.list_messages(query=query, max_results=max_results)}
    except NotAuthenticatedError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/messages/{message_id}")
async def message_detail(message_id: str):
    try:
        return client.get_message(message_id)
    except NotAuthenticatedError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.get("/requests")
async def list_requests(status: Optional[str] = "pending"):
    return {"requests": store.list_requests(status=None if status == "all" else status)}


@router.post("/requests")
async def create_request(body: NewRequest):
    request_id = store.add_pending_request(body.message_id, body.kind, body.instructions)
    return {"request_id": request_id}
