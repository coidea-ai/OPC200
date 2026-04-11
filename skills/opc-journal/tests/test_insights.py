"""Tests for insights command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import insights


def test_insights_with_memory_zh(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\n今天完成了一个功能，非常开心。势能上升。"
    )

    result = insights.run("OPC-001", {"day": 7, "days_back": 7})
    assert result["status"] == "success"
    assert "theme" in result["result"]
    assert "recommendations" in result["result"]
    assert result["result"]["customer_id"] == "OPC-001"
    assert "已为第 7 天生成洞察" in result["message"]


def test_insights_with_memory_en(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\nToday I finished a feature and felt very happy."
    )
    monkeypatch.setattr(ins_mod, "get_language", lambda cid: "en")

    result = insights.run("OPC-001", {"day": 7, "days_back": 7})
    assert result["status"] == "success"
    assert "Insight generated for Day 7" in result["message"]


def test_insights_empty_memory_zh(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001").mkdir(parents=True)

    result = insights.run("OPC-001", {"day": 1})
    assert result["status"] == "success"
    assert "旅程开始" in result["result"]["theme"]
    assert "路标" in result["result"]["summary"]


def test_insights_empty_memory_en(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001").mkdir(parents=True)
    monkeypatch.setattr(ins_mod, "get_language", lambda cid: "en")

    result = insights.run("OPC-001", {"day": 1})
    assert result["status"] == "success"
    assert "Journey Begins" in result["result"]["theme"]
    assert "Every great story begins" in result["result"]["summary"]
