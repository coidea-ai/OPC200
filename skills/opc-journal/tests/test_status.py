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


def test_status_with_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(status, "build_customer_dir", lambda cid: str(tmp_path / cid))
    memory = tmp_path / "OPC-001" / "memory"
    memory.mkdir(parents=True)
    (memory / "2026-04-01.md").write_text("Entry 1")
    (memory / "2026-04-02.md").write_text("Entry 2")

    result = status.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["total_entries"] == 2
    assert result["result"]["latest_entry_date"] == "2026-04-02"
    assert result["result"]["journal_active"] is True
