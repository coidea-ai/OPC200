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
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\nCompleted the login feature today! VERY EXCITED. Decided to adopt JWT."
    )
    (tmp_path / "OPC-001" / "memory" / "12-04-26.md").write_text(
        "---\ntype: entry\ndate: 12-04-26\nday: 2\n---\n\nHit an API bottleneck, a bit stuck."
    )

    result = analyze.run("OPC-001", {"days": 7, "dimension": "general"})
    assert result["status"] == "success"
    assert "signal_summary" in result["result"]
    signals = result["result"]["signal_summary"]
    assert "structural_signals" in signals
    assert signals["structural_signals"]["exclamation_marks"] >= 1
    assert "action_fragments" in signals
    assert "obstacle_fragments" in signals
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


def test_analyze_structural_signals(tmp_path, monkeypatch):
    import scripts.commands.analyze as ana_mod
    monkeypatch.setattr(ana_mod, "build_customer_dir", lambda cid: str(tmp_path / cid))
    (tmp_path / "OPC-001" / "memory").mkdir(parents=True)
    (tmp_path / "OPC-001" / "memory" / "11-04-26.md").write_text(
        "---\ntype: entry\ndate: 11-04-26\nday: 1\n---\n\nWOW!! This is AMAZING?!?\n\"Great progress\" today."
    )

    result = analyze.run("OPC-001", {"days": 7})
    signals = result["result"]["signal_summary"]
    struct = signals["structural_signals"]
    assert struct["exclamation_marks"] >= 1
    assert struct["question_marks"] >= 1
    assert struct["all_caps_words"] >= 2
    assert struct["repeated_punctuation"] >= 1
    assert struct["quoted_phrases"] >= 1
