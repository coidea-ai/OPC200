"""Unit tests for opc-journal-core skill.

TDD Approach: Tests cover initialization, recording, searching, and exporting
"""
import sys
from pathlib import Path

import pytest

# Add skill scripts to path
SKILL_DIR = Path(__file__).parent.parent.parent.parent / "skills" / "opc-journal-suite" / "opc-journal-core" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from init import main as journal_init
from record import main as journal_record, generate_entry_id
from search import main as journal_search
from export import main as journal_export


@pytest.fixture
def customer_id():
    """Return a test customer ID."""
    return "OPC-TEST-001"


class TestJournalInit:
    """Test journal initialization."""

    def test_init_success(self, customer_id):
        """Test successful initialization."""
        context = {
            "customer_id": customer_id,
            "input": {
                "day": 1,
                "goals": ["Complete product MVP", "Acquire first paying customer"],
                "preferences": {
                    "communication_style": "friendly_professional",
                    "work_hours": "09:00-18:00",
                    "timezone": "Asia/Shanghai"
                }
            },
        }

        result = journal_init(context)

        assert result["status"] == "success"
        assert result["result"]["customer_id"] == customer_id
        assert result["result"]["initialized"] is True
        assert result["result"]["day"] == 1
        assert result["result"]["goals_count"] == 2

    def test_init_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {"input": {"day": 1}}
        
        result = journal_init(context)
        
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]

    def test_init_default_day(self, customer_id):
        """Should use day=1 as default."""
        context = {
            "customer_id": customer_id,
            "input": {}
        }
        
        result = journal_init(context)
        
        assert result["result"]["day"] == 1


class TestJournalRecord:
    """Test entry recording."""

    def test_record_success(self, customer_id):
        """Should create entry with valid content."""
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "Completed feature today",
                "day": 5,
                "metadata": {"emotional_state": "happy"}
            }
        }
        
        result = journal_record(context)
        
        assert result["status"] == "success"
        assert "entry_id" in result["result"]
        assert result["result"]["entry"]["content"] == "Completed feature today"
        assert result["result"]["entry"]["day"] == 5
        assert result["result"]["entry"]["metadata"]["emotional_state"] == "happy"

    def test_record_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {"input": {"content": "test"}}
        
        result = journal_record(context)
        
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]

    def test_record_missing_content(self, customer_id):
        """Should fail when content is missing."""
        context = {
            "customer_id": customer_id,
            "input": {"day": 1}
        }
        
        result = journal_record(context)
        
        assert result["status"] == "error"
        assert "content is required" in result["message"]

    def test_generate_entry_id_format(self):
        """Entry ID should follow JE-YYYYMMDD-XXXXXX format."""
        entry_id = generate_entry_id("OPC-001")
        
        assert entry_id.startswith("JE-")
        assert len(entry_id) == 18  # JE-YYYYMMDD-XXXXXX


class TestJournalSearch:
    """Test entry searching."""

    def test_search_success(self, customer_id):
        """Should return search parameters."""
        context = {
            "customer_id": customer_id,
            "input": {
                "query": "database issue",
                "filters": {"time_range": "last_7_days"}
            }
        }
        
        result = journal_search(context)
        
        assert result["status"] == "success"
        assert "search_params" in result["result"]
        assert "database issue" in result["result"]["search_params"]["query"]
        assert result["result"]["search_params"]["customer_id"] == customer_id

    def test_search_missing_customer_id(self):
        """Should fail when customer_id is missing."""
        context = {"input": {"query": "test"}}
        
        result = journal_search(context)
        
        assert result["status"] == "error"


class TestJournalExport:
    """Test entry export."""

    def test_export_success(self, customer_id):
        """Should return export parameters."""
        context = {
            "customer_id": customer_id,
            "input": {
                "format": "markdown",
                "time_range": "2026-W12",
                "sections": ["summary", "milestones"]
            }
        }
        
        result = journal_export(context)
        
        assert result["status"] == "success"
        assert result["result"]["export_format"] == "markdown"
        assert result["result"]["time_range"] == "2026-W12"
        assert "summary" in result["result"]["sections"]

    def test_export_default_format(self, customer_id):
        """Should use markdown as default format."""
        context = {
            "customer_id": customer_id,
            "input": {}
        }
        
        result = journal_export(context)
        
        assert result["result"]["export_format"] == "markdown"
