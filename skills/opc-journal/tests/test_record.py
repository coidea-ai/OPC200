"""Tests for record command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import record


def test_record_success(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = record.run("OPC-001", {"content": "Shipped MVP today", "day": 5})
    assert result["status"] == "success"
    assert result["result"]["day"] == 5
    assert result["result"]["entry_id"].startswith("JE-")
    assert result["result"]["emotion"] == "neutral"


def test_record_auto_emotion(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = record.run("OPC-001", {"content": "感到很开心，终于搞定了", "day": 2})
    assert result["result"]["emotion"] == "开心"


def test_record_missing_content():
    result = record.run("OPC-001", {})
    assert result["status"] == "error"
    assert "content is required" in result["message"]


def test_record_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "OPC-001.md"
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(path))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    record.run("OPC-001", {"content": "Fixed bug", "day": 2})
    assert path.exists()
    assert "Fixed bug" in path.read_text()
    assert "Emotion" in path.read_text()
