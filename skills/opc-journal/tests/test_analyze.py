"""Tests for analyze command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import analyze


def test_analyze_with_memory(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    monkeypatch.setattr(ana_mod, "get_language", lambda cid: "en")
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\nCompleted the login feature today, felt happy and satisfied. Decided to adopt JWT."
    )
    (tmp_path / "OPC-001" / "memory" / "12-04-26.md").write_text(
        "---\ntype: entry\ndate: 12-04-26\nday: 2\n---\n\nHit an API bottleneck, a bit anxious."
    )

    result = analyze.run("OPC-001", {"days": 7, "dimension": "general"})
    assert result["status"] == "success"
    assert "signal_summary" in result["result"]
    signals = result["result"]["signal_summary"]
    assert "emotion_mentions" in signals
    assert "decision_fragments" in signals
    assert "blocker_fragments" in signals
    assert result["result"]["language"] == "en"


def test_analyze_empty_memory(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001").mkdir(parents=True)

    result = analyze.run("OPC-001", {"days": 7})
    assert result["status"] == "success"
    assert result["result"]["files"] == []
    assert result["result"]["signal_summary"]["sources_count"] == 0
    assert result["result"]["raw_text"] == ""


def test_analyze_emotional_trends(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\nhappy\nexcited\nhappy\nfrustrated"
    )

    result = analyze.run("OPC-001", {"days": 7})
    signals = result["result"]["signal_summary"]
    emotions = signals["emotion_mentions"]
    assert emotions.get("happy", 0) == 2
    assert emotions.get("frustrated", 0) == 1
    assert emotions.get("excited", 0) == 1
