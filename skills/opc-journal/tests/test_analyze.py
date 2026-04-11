"""Tests for analyze command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import analyze


def test_analyze_with_memory(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\n今天完成了登录功能，感到开心和满足。决定采用JWT方案。"
    )
    (tmp_path / "OPC-001" / "memory" / "12-04-26.md").write_text(
        "---\ntype: entry\ndate: 12-04-26\nday: 2\n---\n\n遇到了API瓶颈，有点焦虑。"
    )

    result = analyze.run("OPC-001", {"days": 7, "dimension": "general"})
    assert result["status"] == "success"
    assert "interpretation" in result["result"]
    interp = result["result"]["interpretation"]
    assert "emotional_pattern" in interp
    assert "decision_style" in interp


def test_analyze_empty_memory(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001").mkdir(parents=True)

    result = analyze.run("OPC-001", {"days": 7})
    assert result["status"] == "success"
    assert "note" in result["result"]


def test_analyze_emotional_trends(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\n开心\n兴奋\n开心\n沮丧"
    )

    result = analyze.run("OPC-001", {"days": 7})

    interp = result["result"]["interpretation"]
    emotions = interp["emotional_pattern"]
    assert emotions["dominant_emotion"] == "开心"
    assert emotions["emotion_distribution"]["开心"] == 2
    assert emotions["emotion_distribution"]["沮丧"] == 1
    assert emotions["emotion_distribution"]["兴奋"] == 1
