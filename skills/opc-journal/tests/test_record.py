"""Tests for record command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import record


def test_record_success_zh(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = record.run("OPC-001", {"content": "Shipped MVP today", "day": 5})
    assert result["status"] == "success"
    assert result["result"]["day"] == 5
    assert result["result"]["entry_id"].startswith("JE-")
    assert isinstance(result["result"]["emotion"], str)
    assert len(result["result"]["emotion"]) > 0


def test_record_success_en(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "get_language", lambda cid: "en")
    result = record.run("OPC-001", {"content": "Shipped MVP today", "day": 5})
    assert result["status"] == "success"
    assert "Entry" in result["message"]
    assert result["result"]["entry_id"].startswith("JE-")


def test_record_auto_emotion_high(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = record.run("OPC-001", {"content": "感到很开心，终于搞定了，特别兴奋", "day": 2})
    emotion = result["result"]["emotion"]
    assert "高涨" in emotion or "行动力" in emotion or "平和" in emotion or "满足" in emotion


def test_record_auto_emotion_tense(tmp_path, monkeypatch):
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = record.run("OPC-001", {"content": "有点焦虑，压力很大，但还是很期待", "day": 2})
    emotion = result["result"]["emotion"]
    assert "紧绷" in emotion or "冲刺" in emotion or "向前" in emotion


def test_record_missing_content():
    result = record.run("OPC-001", {})
    assert result["status"] == "error"
    assert "请提供记录内容" in result["message"]


def test_record_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "OPC-001.md"
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(path))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    record.run("OPC-001", {"content": "Fixed bug", "day": 2})
    assert path.exists()
    assert "Fixed bug" in path.read_text()
    assert "情绪" in path.read_text()


def test_record_creates_bak(tmp_path, monkeypatch):
    path = tmp_path / "OPC-001.md"
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(path))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    record.run("OPC-001", {"content": "First version", "day": 1})
    assert path.exists()
    record.run("OPC-001", {"content": "Second version", "day": 1})
    bak_path = path.with_suffix(".md.bak")
    assert bak_path.exists()
    assert "First version" in bak_path.read_text()
    assert "Second version" in path.read_text()
