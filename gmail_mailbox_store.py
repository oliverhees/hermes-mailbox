"""SQLite cache shared by the agent tools and the dashboard backend.

Holds three things the dashboard panel renders and the agent writes to:
- stats_snapshots: point-in-time inbox counters, for the sparkline/cards
- reports:         short human-readable summaries (e.g. the daily briefing)
- agent_requests:  a small queue ("please draft a reply to X") the user
                    creates by clicking a button in the dashboard, and the
                    agent drains via gmail_list_pending_requests /
                    gmail_complete_request (typically on a cron schedule).
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterator, Optional

from gmail_mailbox_config import db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS stats_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    unread_count INTEGER NOT NULL,
    total_today INTEGER NOT NULL,
    by_label_json TEXT NOT NULL,
    top_senders_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at REAL NOT NULL,
    completed_at REAL,
    message_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    instructions TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    result_note TEXT NOT NULL DEFAULT ''
);
"""


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_stats_snapshot(unread_count: int, total_today: int, by_label: dict, top_senders: list) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO stats_snapshots (created_at, unread_count, total_today, by_label_json, top_senders_json)"
            " VALUES (?, ?, ?, ?, ?)",
            (time.time(), unread_count, total_today, json.dumps(by_label), json.dumps(top_senders)),
        )
        return cur.lastrowid


def get_latest_stats() -> Optional[dict]:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM stats_snapshots ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:
            return None
        return _row_to_stats(row)


def get_stats_history(days: int = 14) -> list[dict]:
    cutoff = time.time() - days * 86400
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM stats_snapshots WHERE created_at >= ? ORDER BY created_at ASC", (cutoff,)
        ).fetchall()
        return [_row_to_stats(row) for row in rows]


def _row_to_stats(row: sqlite3.Row) -> dict:
    return {
        "created_at": row["created_at"],
        "unread_count": row["unread_count"],
        "total_today": row["total_today"],
        "by_label": json.loads(row["by_label_json"]),
        "top_senders": json.loads(row["top_senders_json"]),
    }


def save_report(title: str, body: str) -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO reports (created_at, title, body) VALUES (?, ?, ?)", (time.time(), title, body)
        )
        return cur.lastrowid


def get_recent_reports(limit: int = 5) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reports ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def add_pending_request(message_id: str, kind: str, instructions: str = "") -> int:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO agent_requests (created_at, message_id, kind, instructions) VALUES (?, ?, ?, ?)",
            (time.time(), message_id, kind, instructions),
        )
        return cur.lastrowid


def list_requests(status: Optional[str] = "pending") -> list[dict]:
    with _conn() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM agent_requests WHERE status = ? ORDER BY created_at ASC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM agent_requests ORDER BY created_at ASC").fetchall()
        return [dict(row) for row in rows]


def complete_request(request_id: int, result_note: str = "") -> bool:
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE agent_requests SET status = 'done', completed_at = ?, result_note = ? WHERE id = ?",
            (time.time(), result_note, request_id),
        )
        return cur.rowcount > 0
