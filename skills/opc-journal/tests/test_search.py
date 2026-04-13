"""Tests for search command with real local search."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import search, record, init
from scripts.commands import _meta


def test_search_basic(tmp_path, monkeypatch):
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(search, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "pricing strategy discussion", "day": 1})
    record.run("OPC-001", {"content": "design review meeting", "day": 1})

    result = search.run("OPC-001", {"query": "pricing"})
    assert result["status"] == "success"
    assert result["result"]["query"] == "pricing"
    assert result["result"]["total_matches"] == 1
    assert len(result["result"]["matches"]) == 1
    assert "pricing" in result["result"]["matches"][0]["body"]


def test_search_empty_query(tmp_path, monkeypatch):
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(search, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "entry one", "day": 1})
    record.run("OPC-001", {"content": "entry two", "day": 1})

    result = search.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["query"] == ""
    assert result["result"]["total_matches"] == 2


def test_search_no_memory_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(search, "build_customer_dir", lambda cid: str(tmp_path / cid))

    result = search.run("OPC-001", {"query": "test"})
    assert result["status"] == "success"
    assert result["result"]["matches"] == []
    assert result["result"]["total_matches"] == 0
