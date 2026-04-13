"""Tests for init command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import init
from scripts.commands import _meta


def test_init_success_zh(tmp_path, monkeypatch):
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = init.run("OPC-001", {"day": 1, "goals": ["发布 MVP"]})
    assert result["status"] == "success"
    assert result["result"]["initialized"]
    assert result["result"]["day"] == 1
    assert "initialized" in result["message"].lower()
    assert result["result"]["language"] == "zh"


def test_init_success_en(tmp_path, monkeypatch):
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    result = init.run("OPC-001", {"day": 1, "goals": ["Launch product"]})
    assert result["status"] == "success"
    assert result["result"]["language"] == "en"
    assert "initialized" in result["message"].lower()


def test_init_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "OPC-001.md"
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(path))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    init.run("OPC-001", {"day": 1, "goals": ["发布 MVP"]})
    assert path.exists()
    content = path.read_text()
    assert "发布 MVP" in content
    assert "OPC Journal Charter" in content
    assert "Goals" in content
    assert "Preferences" in content


def test_init_writes_meta(tmp_path, monkeypatch):
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    init.run("OPC-001", {"day": 1, "goals": ["测试目标"]})
    meta_path = tmp_path / "OPC-001" / "journal_meta.json"
    assert meta_path.exists()
    import json
    meta = json.loads(meta_path.read_text())
    assert meta["language"] == "zh"
    assert meta["started_day"] == 1
