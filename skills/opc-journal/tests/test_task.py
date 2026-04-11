"""Tests for task command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import task


def test_create_task():
    result = task.run("OPC-001", {"type": "research", "description": "Competitor analysis", "timeout_hours": 4})
    assert result["status"] == "success"
    assert result["result"]["task_id"].startswith("TASK-")
    assert result["result"]["task"]["status"] == "created"


def test_missing_description():
    result = task.run("OPC-001", {})
    assert result["status"] == "error"
    assert "description is required" in result["message"]
