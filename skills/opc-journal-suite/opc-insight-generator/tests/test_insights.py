"""Tests for opc-insight-generator skill (v2.4-refactored).

TDD approach: tests define expected behavior.
v2.4: Now generates insights from OpenClaw dreaming output.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from daily_summary import main as generate_daily_summary


class TestDailySummary:
    """Test daily insight generation from memory sources."""

    def test_generate_success_with_memory(self, monkeypatch, tmp_path):
        """Should generate insight when memory files exist."""
        customer_dir = tmp_path / ".openclaw" / "customers" / "OPC-TEST-001" / "memory"
        customer_dir.mkdir(parents=True)
        (customer_dir / "2026-04-01.md").write_text(
            "今天完成了产品原型的最终迭代，感觉很满足。"
        )
        monkeypatch.setenv("HOME", str(tmp_path))

        context = {
            "customer_id": "OPC-TEST-001",
            "input": {"day": 7, "days_back": 7}
        }
        result = generate_daily_summary(context)

        assert result["status"] == "success"
        assert result["result"]["day"] == 7
        assert result["result"]["customer_id"] == "OPC-TEST-001"
        assert result["result"]["data_source"] == "openclaw_dreams_memory"
        assert "theme" in result["result"]
        assert "summary" in result["result"]
        assert len(result["result"]["recommendations"]) >= 1

    def test_generate_no_memory_yet(self, monkeypatch, tmp_path):
        """Should return encouraging starter insight when no memory exists."""
        monkeypatch.setenv("HOME", str(tmp_path))
        context = {
            "customer_id": "OPC-TEST-002",
            "input": {"day": 1, "days_back": 7}
        }
        result = generate_daily_summary(context)

        assert result["status"] == "success"
        assert result["result"]["day"] == 1
        assert result["result"]["customer_id"] == "OPC-TEST-002"
        assert "旅程开始" in result["result"]["theme"]
        assert len(result["result"]["recommendations"]) >= 1

    def test_generate_default_day(self, monkeypatch, tmp_path):
        """Should use day=1 as default."""
        monkeypatch.setenv("HOME", str(tmp_path))
        context = {
            "customer_id": "OPC-TEST-003",
            "input": {}
        }
        result = generate_daily_summary(context)

        assert result["result"]["day"] == 1

    def test_generate_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {"input": {"day": 5}}
        result = generate_daily_summary(context)

        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
