"""Tests for batch_task command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import batch_task


def test_batch_task_success():
    result = batch_task.run("OPC-001", {"descriptions": ["Task A", "Task B", "Task C"], "type": "research", "timeout_hours": 8})
    assert result["status"] == "success"
    assert result["result"]["tasks_created"] == 3
    assert len(result["result"]["tasks"]) == 3
    assert all(t["task_type"] == "research" for t in result["result"]["tasks"])
    assert all(t["customer_id"] == "OPC-001" for t in result["result"]["tasks"])


def test_batch_task_empty_descriptions():
    result = batch_task.run("OPC-001", {"descriptions": [], "type": "research"})
    assert result["status"] == "error"
    assert "No valid task descriptions provided" in result["message"]


def test_batch_task_missing_descriptions():
    result = batch_task.run("OPC-001", {"type": "research"})
    assert result["status"] == "error"
    assert "descriptions list is required" in result["message"]


def test_batch_task_single_description():
    result = batch_task.run("OPC-001", {"descriptions": ["Only one task"], "type": "analysis"})
    assert result["status"] == "success"
    assert result["result"]["tasks_created"] == 1
    assert result["result"]["tasks"][0]["description"] == "Only one task"
    assert result["result"]["tasks"][0]["task_type"] == "analysis"


def test_batch_task_skips_invalid_descriptions():
    result = batch_task.run("OPC-001", {"descriptions": ["Valid", "", "Another", None], "type": "research"})
    assert result["status"] == "success"
    assert result["result"]["tasks_created"] == 2
    descriptions = [t["description"] for t in result["result"]["tasks"]]
    assert "Valid" in descriptions
    assert "Another" in descriptions
