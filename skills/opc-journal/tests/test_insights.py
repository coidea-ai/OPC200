"""Tests for insights command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import insights


def test_insights_with_memory(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\nCompleted a feature today, very happy. Momentum is rising."
    )

    result = insights.run("OPC-001", {"day": 7, "days_back": 7})
    assert result["status"] == "success"
    assert "signal_counts" in result["result"]
    assert result["result"]["customer_id"] == "OPC-001"
    assert result["result"]["language"] == "en"


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
    assert "signal_counts" in result["result"]


def test_insights_empty_memory(tmp_path, monkeypatch):
    import scripts.commands.insights as ins_mod
    monkeypatch.setattr(ins_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001").mkdir(parents=True)

    result = insights.run("OPC-001", {"day": 1})
    assert result["status"] == "success"
    assert result["result"]["sources"] == []
    assert result["result"]["raw_text"] == ""
