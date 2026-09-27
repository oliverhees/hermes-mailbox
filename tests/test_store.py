"""Smoke tests for store.py - the only module with no Google API dependency,
so it can run without credentials or network access.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _fresh_home(tmp_path):
    os.environ["HERMES_HOME"] = str(tmp_path)
    import importlib

    import gmail_mailbox_config as config
    import gmail_mailbox_store as store

    importlib.reload(config)
    importlib.reload(store)
    return store


def test_stats_snapshot_roundtrip(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    store = _fresh_home(tmp_path)

    assert store.get_latest_stats() is None

    store.save_stats_snapshot(unread_count=3, total_today=12, by_label={"INBOX": 3}, top_senders=[{"from": "a@b.com", "count": 2}])
    latest = store.get_latest_stats()
    assert latest["unread_count"] == 3
    assert latest["total_today"] == 12
    assert latest["by_label"] == {"INBOX": 3}

    history = store.get_stats_history(days=1)
    assert len(history) == 1


def test_request_queue_lifecycle(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    store = _fresh_home(tmp_path)

    request_id = store.add_pending_request("msg-1", "draft_reply", "be polite")
    pending = store.list_requests(status="pending")
    assert len(pending) == 1
    assert pending[0]["message_id"] == "msg-1"

    assert store.complete_request(request_id, "created draft d1") is True
    assert store.list_requests(status="pending") == []
    done = store.list_requests(status="done")
    assert len(done) == 1
    assert done[0]["result_note"] == "created draft d1"

    assert store.complete_request(9999) is False


def test_reports_roundtrip(tmp_path=None):
    tmp_path = tmp_path or Path(tempfile.mkdtemp())
    store = _fresh_home(tmp_path)

    store.save_report("Mailbox-Bericht", "5 neue Mails, 2 wichtig.")
    reports = store.get_recent_reports(limit=5)
    assert len(reports) == 1
    assert reports[0]["title"] == "Mailbox-Bericht"


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
