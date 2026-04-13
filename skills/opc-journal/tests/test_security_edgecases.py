"""Tests for security and edge-case fixes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.storage import build_customer_dir, build_memory_path
from scripts.commands import status, record, init
from scripts.commands import _meta


def test_path_traversal_sanitization():
    result = build_customer_dir("../etc/passwd")
    assert ".." not in result
    # The path should still contain the base structure with /
    assert "~/.openclaw/customers/" in result

    result = build_customer_dir("a/b")
    assert result == "~/.openclaw/customers/ab"

    result = build_customer_dir("a\\b")
    assert result == "~/.openclaw/customers/ab"

    assert build_customer_dir("") == "~/.openclaw/customers/default"


def test_memory_path_sanitization():
    path = build_memory_path("../../admin", "01-01-25")
    assert ".." not in path
    assert "/" not in path.replace("~/.openclaw/customers/", "").replace("/memory/", "")


def test_status_first_entry_date_is_oldest(tmp_path, monkeypatch):
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(status, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "Entry on 13-04-26", "day": 1})

    # Create another memory file for a different date to test date range
    memory_dir = tmp_path / "OPC-001" / "memory"
    memory_dir.mkdir(parents=True, exist_ok=True)
    (memory_dir / "15-04-26.md").write_text("---\ntype: entry\n---\n\nLater entry\n")
    (memory_dir / "10-04-26.md").write_text("---\ntype: entry\n---\n\nEarlier entry\n")

    result = status.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["latest_entry_date"] == "15-04-26"
    assert result["result"]["first_entry_date"] == "10-04-26"
    assert result["result"]["total_entries"] == 3
