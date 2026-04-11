"""Tests for init command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import init


def test_init_success(tmp_path, monkeypatch):
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(tmp_path / f"{cid}.md"))
    result = init.run("OPC-001", {"day": 1, "goals": ["Ship MVP"]})
    assert result["status"] == "success"
    assert result["result"]["initialized"]
    assert result["result"]["day"] == 1


def test_init_writes_file(tmp_path, monkeypatch):
    path = tmp_path / "OPC-001.md"
    monkeypatch.setattr(init, "build_memory_path", lambda cid: str(path))
    init.run("OPC-001", {"day": 1, "goals": ["Ship MVP"]})
    assert path.exists()
    content = path.read_text()
    assert "Ship MVP" in content
    assert "Journal Init" in content
