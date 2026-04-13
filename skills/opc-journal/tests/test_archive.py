"""Tests for archive command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import archive, record, init
from scripts.commands import _meta
from utils import storage


def test_archive_success(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "build_memory_path", lambda cid, date=None: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(archive, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "Entry one", "day": 1})

    result = archive.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["cleared"] is False
    assert len(result["result"]["archived_files"]) >= 1
    archive_path = Path(result["result"]["archive_path"])
    assert archive_path.exists()


def test_archive_with_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "build_memory_path", lambda cid, date=None: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(archive, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "Entry one", "day": 1})
    memory_dir = tmp_path / "OPC-001" / "memory"

    result = archive.run("OPC-001", {"clear": True, "force": True})
    assert result["status"] == "success"
    assert result["result"]["cleared"] is True
    assert not any(f.is_file() for f in memory_dir.iterdir())


def test_archive_clear_requires_force(tmp_path, monkeypatch):
    """Archive with --clear but without --force should be rejected."""
    monkeypatch.setattr(storage, "build_memory_path", lambda cid, date=None: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(record, "build_memory_path", lambda cid: str(tmp_path / cid / "memory" / "13-04-26.md"))
    monkeypatch.setattr(init, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(record, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(archive, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(_meta, "build_customer_dir", lambda cid: str(tmp_path / cid))

    init.run("OPC-001", {"day": 1, "goals": ["Launch"]})
    record.run("OPC-001", {"content": "Entry one", "day": 1})

    result = archive.run("OPC-001", {"clear": True, "force": False})
    assert result["status"] == "error"
    assert "--force" in result["message"]


def test_archive_empty_journal(tmp_path, monkeypatch):
    monkeypatch.setattr(archive, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)

    result = archive.run("OPC-001", {})
    assert result["status"] == "error"
    assert "No journal data to archive" in result["message"]
