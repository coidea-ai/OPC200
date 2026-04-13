"""Tests for export command with real local export."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import export, record, init
from scripts.commands import _meta


def test_export_markdown(tmp_path, monkeypatch):
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(export, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "First weekly entry", "day": 1})

    result = export.run("OPC-001", {"format": "markdown", "time_range": "weekly"})
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "markdown"
    assert result["result"]["time_range"] == "weekly"
    assert result["result"]["entry_count"] == 1
    assert Path(result["result"]["output_path"]).exists()


def test_export_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(export, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "Default export entry", "day": 1})

    result = export.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "markdown"
    assert result["result"]["time_range"] == "all"
    assert result["result"]["entry_count"] == 1


def test_export_json(tmp_path, monkeypatch):
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(export, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "JSON export entry", "day": 1})

    result = export.run("OPC-001", {"format": "json"})
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "json"
    assert result["result"]["entry_count"] == 1
    assert result["result"]["output_path"].endswith(".json")
    assert Path(result["result"]["output_path"]).exists()


def test_export_empty_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)

    result = export.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["entry_count"] == 0
    assert result["result"]["time_range"] == "all"


def test_export_no_memory_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(export, "build_customer_dir", lambda cid: str(tmp_path / cid))

    result = export.run("OPC-001", {})
    assert result["status"] == "error"
    assert "No memory directory found" in result["message"]
