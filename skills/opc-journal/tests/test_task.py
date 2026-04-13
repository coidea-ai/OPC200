"""Tests for task command with persistence."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import task
from utils import task_storage


def test_task_success(tmp_path, monkeypatch):
    monkeypatch.setattr(task_storage, "_get_tasks_path", lambda cid: str(tmp_path / f"{cid}_tasks.json"))

    result = task.run("OPC-001", {"type": "research", "description": "Test task", "timeout_hours": 4})
    assert result["status"] == "success"
    task_id = result["result"]["task_id"]
    assert task_id.startswith("TASK-")

    # Verify persistence
    tasks = task_storage.read_tasks("OPC-001")
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == task_id
    assert tasks[0]["description"] == "Test task"


def test_task_missing_description():
    result = task.run("OPC-001", {"type": "research", "timeout_hours": 4})
    assert result["status"] == "error"
    assert "description is required" in result["message"]


def test_task_persistence_read_back(tmp_path, monkeypatch):
    monkeypatch.setattr(task_storage, "_get_tasks_path", lambda cid: str(tmp_path / f"{cid}_tasks.json"))

    result = task.run("OPC-001", {"type": "analysis", "description": "Persisted task", "timeout_hours": 8})
    assert result["status"] == "success"

    # Simulate process restart by reading directly
    path = tmp_path / "OPC-001_tasks.json"
    assert path.exists()

    persisted = task_storage.get_task("OPC-001", result["result"]["task_id"])
    assert persisted is not None
    assert persisted["description"] == "Persisted task"
    assert persisted["task_type"] == "analysis"
    assert persisted["status"] == "created"


def test_task_storage_crud(tmp_path, monkeypatch):
    monkeypatch.setattr(task_storage, "_get_tasks_path", lambda cid: str(tmp_path / f"{cid}_tasks.json"))

    # Create
    task_storage.add_task("OPC-001", {"task_id": "T-1", "description": "First"})
    task_storage.add_task("OPC-001", {"task_id": "T-2", "description": "Second"})
    assert len(task_storage.read_tasks("OPC-001")) == 2

    # Update
    task_storage.update_task("OPC-001", "T-1", {"status": "done"})
    t1 = task_storage.get_task("OPC-001", "T-1")
    assert t1["status"] == "done"

    # Delete
    task_storage.delete_task("OPC-001", "T-1")
    assert len(task_storage.read_tasks("OPC-001")) == 1
    assert task_storage.get_task("OPC-001", "T-1") is None

    # List
    all_tasks = task_storage.list_tasks("OPC-001")
    assert len(all_tasks) == 1
    assert all_tasks[0]["task_id"] == "T-2"
