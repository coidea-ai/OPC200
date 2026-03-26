"""Unit tests for opc-insight-generator skill.

TDD Approach: Tests cover daily summary generation
"""
import sys
from pathlib import Path

import pytest

# Add skill scripts to path
SKILL_DIR = Path(__file__).parent.parent.parent.parent / "skills" / "opc-journal-suite" / "opc-insight-generator" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from daily_summary import main as generate_daily_summary


class TestDailySummary:
    """Test daily summary generation."""
    
    def test_generate_success(self):
        """Should generate summary for a day."""
        context = {
            "customer_id": "OPC-001",
            "input": {
                "day": 7,
                "entries": [
                    {"content": "Worked on feature A"},
                    {"content": "Met with customer"}
                ]
            }
        }
        
        result = generate_daily_summary(context)
        
        assert result["status"] == "success"
        assert result["result"]["day"] == 7
        assert result["result"]["customer_id"] == "OPC-001"
        assert result["result"]["entry_count"] == 2
    
    def test_generate_default_day(self):
        """Should use day=1 as default."""
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
