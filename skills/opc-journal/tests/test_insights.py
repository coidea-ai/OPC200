"""Tests for insights command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import insights


def test_insights_with_memory(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "2026-04-01.md").write_text(
        "今天完成了一个功能，非常开心。势能上升。"
    )

    result = insights.run("OPC-001", {"day": 7, "days_back": 7})
    assert result["status"] == "success"
    assert "theme" in result["result"]
    assert "recommendations" in result["result"]
    assert result["result"]["customer_id"] == "OPC-001"


def test_insights_empty_memory(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001").mkdir(parents=True)

    result = insights.run("OPC-001", {"day": 1})
    assert result["status"] == "success"
    assert "旅程开始" in result["result"]["theme"]
