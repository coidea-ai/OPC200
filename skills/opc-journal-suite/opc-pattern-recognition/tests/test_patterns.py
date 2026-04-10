"""Tests for opc-pattern-recognition skill (v2.4-refactored).

TDD approach: tests define expected behavior.
v2.4: Now an interpretation layer over OpenClaw dreaming output.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from analyze import main as analyze_patterns


class TestAnalyzePatterns:
    """Test pattern interpretation from memory sources."""

    def test_analyze_no_memory_sources(self, monkeypatch, tmp_path):
        """Should return a note when no memory files exist yet."""
        monkeypatch.setenv("HOME", str(tmp_path))
        context = {
            "customer_id": "OPC-TEST-001",
            "input": {"days": 7, "type": "weekly"}
        }
        result = analyze_patterns(context)

        assert result["status"] == "success"
        assert result["result"]["interpretation"] is None
        assert "No dreams.md or memory files found" in result["result"]["note"]

    def test_analyze_with_dreams_md(self, monkeypatch, tmp_path):
        """Should interpret patterns from dreams.md."""
        customer_dir = tmp_path / ".openclaw" / "customers" / "OPC-TEST-002"
        customer_dir.mkdir(parents=True)
        dreams_file = customer_dir / "dreams.md"
        dreams_file.write_text(
            "周一上午完成了原型设计。下午感到焦虑，因为技术选型还没决定。"
            "晚上学会了 Docker 部署，感到满足。"
            "周二早晨发布了 MVP，很激动。"
        )
        monkeypatch.setenv("HOME", str(tmp_path))

        context = {
            "customer_id": "OPC-TEST-002",
            "input": {"days": 7, "type": "weekly"}
        }
        result = analyze_patterns(context)

        assert result["status"] == "success"
        assert result["result"]["data_source"] == "openclaw_dreams_memory"
        assert result["result"]["files_read"] >= 1

        interp = result["result"]["interpretation"]
        assert "work_rhythm" in interp
        assert "emotional_pattern" in interp
        assert "decision_style" in interp
        assert "milestone_velocity" in interp
        # Emotional signals: 焦虑 + 满足 + 激动 = 3 unique emotions
        assert interp["emotional_pattern"]["emotional_volatility"] >= 2
        # Milestones: 发布了 MVP should be detected
        assert interp["milestone_velocity"]["count"] >= 1

    def test_analyze_with_memory_dir(self, monkeypatch, tmp_path):
        """Should interpret patterns from memory/*.md."""
        customer_dir = tmp_path / ".openclaw" / "customers" / "OPC-TEST-003" / "memory"
        customer_dir.mkdir(parents=True)
        (customer_dir / "2026-04-01.md").write_text("今天咨询了定价策略，纠结了很久。")
        (customer_dir / "2026-04-02.md").write_text("晚上又讨论了营销方案，找人帮忙解决了 Facebook 广告的问题。")
        monkeypatch.setenv("HOME", str(tmp_path))

        context = {
            "customer_id": "OPC-TEST-003",
            "input": {"days": 7, "type": "weekly"}
        }
        result = analyze_patterns(context)

        assert result["status"] == "success"
        interp = result["result"]["interpretation"]
        # Decision style should detect hesitation signal (纠结)
        assert "谨慎型" in interp["decision_style"]["style_label"]
        # Help seeking count should be >= 1 (帮忙)
        assert interp["collaboration_pattern"]["help_seeking_frequency"] >= 1

    def test_analyze_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {"input": {"days": 7}}
        result = analyze_patterns(context)

        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
