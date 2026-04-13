"""Tests for delete command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import delete, record, init
from scripts.commands import _meta
from utils import storage
from utils.parsing import extract_entries


def test_delete_entry_success(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "build_memory_path", lambda cid, date=None: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(delete, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})  # creates memory/13-04-26.md with charter
    rec_result = record.run("OPC-001", {"content": "First entry", "day": 1})
    entry_id = rec_result["result"]["entry_id"]

    result = delete.run("OPC-001", {"entry_id": entry_id, "force": True})
    assert result["status"] == "success"
    assert result["result"]["entry_id"] == entry_id
    # Charter remains, so file is not removed
    assert result["result"]["file_removed"] is False

    path = tmp_path / "OPC-001" / "memory" / "13-04-26.md"
    content = path.read_text()
    assert entry_id not in content
    assert "type: charter" in content


def test_delete_requires_force(tmp_path, monkeypatch):
    """Delete without --force should be rejected."""
    monkeypatch.setattr(delete, "build_customer_dir", lambda cid: str(tmp_path / cid))
    
    result = delete.run("OPC-001", {"entry_id": "JE-TEST-123456", "force": False})
    assert result["status"] == "error"
    assert "--force" in result["message"]


def test_delete_entry_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr(delete, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)

    result = delete.run("OPC-001", {"entry_id": "JE-NOTFOUND-000000", "force": True})
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_delete_missing_entry_id():
    result = delete.run("OPC-001", {})
    assert result["status"] == "error"
    assert "entry_id is required" in result["message"]


def test_delete_multi_entry_file(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "build_memory_path", lambda cid, date=None: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(delete, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    rec1 = record.run("OPC-001", {"content": "Entry one", "day": 1})
    rec2 = record.run("OPC-001", {"content": "Entry two", "day": 1})
    eid1 = rec1["result"]["entry_id"]
    eid2 = rec2["result"]["entry_id"]

    result = delete.run("OPC-001", {"entry_id": eid1, "force": True})
    assert result["status"] == "success"
    assert result["result"]["file_removed"] is False

    path = tmp_path / "OPC-001" / "memory" / "13-04-26.md"
    content = path.read_text()
    assert eid1 not in content
    assert eid2 in content

    # CRITICAL-1 regression test: remaining entries must still be parsable
    entries = extract_entries(content)
    assert len(entries) == 1
    assert entries[0]["entry_id"] == eid2
