"""Tests for status command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import status


def test_status_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(status, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = status.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["total_entries"] == 0
    assert result["result"]["journal_active"] is False
    assert "还没有正式记录" in result["message"]


def test_status_with_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(status, "build_customer_dir", lambda cid: str(tmp_path / cid))
    memory = tmp_path / "OPC-001" / "memory"
    memory.mkdir(parents=True)
    # Write a charter (not counted as entry)
    (memory / "11-04-26.md").write_text("---\ntype: charter\ndate: 11-04-26\n---\n\n# Day 1 Charter")
    # Write an actual entry
    (memory / "12-04-26.md").write_text(
        "---\ntype: entry\ndate: 12-04-26\nday: 2\nentry_id: JE-20260412-AB12\n---\n\n## Journal Entry - JE-20260412-AB12"
    )

    result = status.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["total_entries"] == 1
    assert result["result"]["latest_entry_date"] == "12-04-26"
    assert result["result"]["journal_active"] is True
    assert "已经记录了 1 条" in result["message"]
