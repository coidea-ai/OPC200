"""Unit tests for opc-insight-generator skill (v2.4).

v2.4 Change: The skill now reads OpenClaw dreaming output (memory/dreams files)
instead of receiving raw entries. Tests use temporary memory files.
"""
import sys
from pathlib import Path

import pytest

# Add skill scripts to path
SKILL_DIR = Path(__file__).parent.parent.parent.parent / "skills" / "opc-journal-suite" / "opc-insight-generator" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

import daily_summary
from daily_summary import main as generate_daily_summary


class TestDailySummary:
    """Test daily insight generation from memory files."""

    def test_generate_success(self, monkeypatch, tmp_path):
        """Should generate insight for a day from memory files."""
        customer_dir = tmp_path / "OPC-001"
        memory_dir = customer_dir / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "2026-04-01.md").write_text(
            "Worked on feature A. Met with customer. 完成登录功能。"
        )

        monkeypatch.setattr(daily_summary, "build_customer_dir", lambda _cid: str(customer_dir))

        context = {
            "customer_id": "OPC-001",
            "input": {"day": 7}
        }

        result = generate_daily_summary(context)

        assert result["status"] == "success"
        assert result["result"]["day"] == 7
        assert result["result"]["customer_id"] == "OPC-001"
        assert "theme" in result["result"]
        assert "summary" in result["result"]
        assert "recommendations" in result["result"]
        assert result["result"]["data_source"] == "openclaw_dreams_memory"

    def test_generate_default_day(self, monkeypatch, tmp_path):
        """Should use day=1 as default."""
        customer_dir = tmp_path / "OPC-001"
        memory_dir = customer_dir / "memory"
        memory_dir.mkdir(parents=True)
        (memory_dir / "2026-04-01.md").write_text("Some work done.")

        monkeypatch.setattr(daily_summary, "build_customer_dir", lambda _cid: str(customer_dir))

        context = {
            "customer_id": "OPC-001",
            "input": {}
        }

        result = generate_daily_summary(context)

        assert result["result"]["day"] == 1

    def test_generate_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {
            "input": {"day": 5}
        }

        result = generate_daily_summary(context)

        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]

    def test_generate_insufficient_memory(self, monkeypatch):
        """Should handle empty memory gracefully."""
        monkeypatch.setattr(daily_summary, "_find_memory_sources", lambda _cid: [])

        context = {
            "customer_id": "OPC-001",
            "input": {"day": 1}
        }

        result = generate_daily_summary(context)

        assert result["status"] == "success"
        assert "旅程开始" in result["result"]["theme"]
