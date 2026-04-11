"""Unit tests for opc-pattern-recognition skill (v2.4).

v2.4 Change: The skill now reads OpenClaw dreaming output (memory/dreams files)
instead of receiving raw entries. Tests use temporary memory files.
"""
import sys
from pathlib import Path

import pytest

# Add skill scripts to path
SKILL_DIR = Path(__file__).parent.parent.parent.parent / "skills" / "opc-journal-suite" / "opc-pattern-recognition" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

import analyze
from analyze import main as analyze_patterns


class TestAnalyzePatterns:
    """Test pattern analysis from memory files."""

    def test_analyze_with_memory_files(self, monkeypatch, tmp_path):
        """Should interpret patterns from customer memory files."""
        customer_dir = tmp_path / "OPC-001"
        memory_dir = customer_dir / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "2026-04-01.md").write_text(
            "今天完成了登录功能，感到开心和满足。决定采用JWT方案。"
        )
        (memory_dir / "2026-04-02.md").write_text(
            "遇到了API瓶颈，有点焦虑。完成了数据库优化。"
        )

        monkeypatch.setattr(analyze, "build_customer_dir", lambda _cid: str(customer_dir))

        context = {
            "customer_id": "OPC-001",
            "input": {"days": 7, "type": "weekly"}
        }

        result = analyze_patterns(context)

        assert result["status"] == "success"
        assert "interpretation" in result["result"]
        interp = result["result"]["interpretation"]
        assert "emotional_pattern" in interp
        assert "decision_style" in interp
        assert "milestone_velocity" in interp
        assert "work_rhythm" in interp

    def test_analyze_empty_memory(self, monkeypatch):
        """Should return a helpful note when no memory files exist."""
        monkeypatch.setattr(analyze, "_find_dreams_source", lambda _cid: [])

        context = {
            "customer_id": "OPC-001",
            "input": {"days": 7, "type": "weekly"}
        }

        result = analyze_patterns(context)

        assert result["status"] == "success"
        assert "note" in result["result"]

    def test_analyze_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {
            "input": {
                "entries": [{"metadata": {}}]
            }
        }

        result = analyze_patterns(context)

        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]

    def test_analyze_emotional_trends(self, monkeypatch, tmp_path):
        """Should detect emotional patterns from memory text."""
        customer_dir = tmp_path / "OPC-001"
        memory_dir = customer_dir / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "2026-04-01.md").write_text("开心\n兴奋\n开心\n沮丧")

        monkeypatch.setattr(analyze, "build_customer_dir", lambda _cid: str(customer_dir))

        context = {
            "customer_id": "OPC-001",
            "input": {"days": 7}
        }

        result = analyze_patterns(context)

        interp = result["result"]["interpretation"]
        emotions = interp["emotional_pattern"]
        assert emotions["dominant_emotion"] == "开心"
        assert emotions["emotion_distribution"]["开心"] == 2
        assert emotions["emotion_distribution"]["沮丧"] == 1
        assert emotions["emotion_distribution"]["兴奋"] == 1
