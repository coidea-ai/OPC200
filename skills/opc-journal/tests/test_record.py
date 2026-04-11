"""Tests for record command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import record


def test_record_success(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    result = record.run("OPC-001", {"content": "Shipped MVP today", "day": 5})
    assert result["status"] == "success"
    assert result["result"]["day"] == 5
    assert result["result"]["entry_id"].startswith("JE-")


def test_record_missing_content():
    result = record.run("OPC-001", {})
    assert result["status"] == "error"
    assert "content is required" in result["message"]


def test_record_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "OPC-001.md"
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(path))
    record.run("OPC-001", {"content": "Fixed bug", "day": 2})
    assert path.exists()
    assert "Fixed bug" in path.read_text()
