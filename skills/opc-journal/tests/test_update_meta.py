"""Tests for update-meta command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import update_meta, init, record
from scripts.commands import _meta


def test_update_meta_language_switch(tmp_path, monkeypatch):
    memory_file = str(tmp_path / "OPC-001" / "memory" / "12-04-26.md")
    monkeypatch.setattr(init, "build_memory_path", lambda cid: memory_file)
    monkeypatch.setattr(record, "build_memory_path", lambda cid: memory_file)
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(update_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch MVP"]})
    record.run("OPC-001", {"day": 1, "content": "Very excited today"})

    result = update_meta.run("OPC-001", {"language": "fr"})
    assert result["status"] == "success"
    assert result["result"]["language"] == "fr"
    assert result["result"]["changed"] is True

    # Verify meta
    meta = _meta.read_meta("OPC-001")
    assert meta["language"] == "fr"

    # Verify entry file preserves user content
    entry_path = tmp_path / "OPC-001" / "memory" / "12-04-26.md"
    content = entry_path.read_text()
    assert "Very excited today" in content
    assert "Launch MVP" in content


def test_update_meta_language_another_switch(tmp_path, monkeypatch):
    memory_file = str(tmp_path / "OPC-001" / "memory" / "12-04-26.md")
    monkeypatch.setattr(init, "build_memory_path", lambda cid: memory_file)
    monkeypatch.setattr(record, "build_memory_path", lambda cid: memory_file)
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(update_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch product"]})
    record.run("OPC-001", {"day": 1, "content": "excited today"})

    result = update_meta.run("OPC-001", {"language": "de"})
    assert result["status"] == "success"
    assert result["result"]["language"] == "de"
    assert result["result"]["changed"] is True

    # Verify entry file preserves user content
    entry_path = tmp_path / "OPC-001" / "memory" / "12-04-26.md"
    content = entry_path.read_text()
    assert "excited today" in content
    assert "Launch product" in content


def test_update_meta_no_change(tmp_path, monkeypatch):
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "12-04-26.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(update_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Test Goal"]})
    result = update_meta.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["changed"] is False
