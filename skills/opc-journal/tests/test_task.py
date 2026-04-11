"""Tests for task command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import task


def test_create_task_zh():
    result = task.run("OPC-001", {"description": "Research competitors", "timeout_hours": 4})
    assert result["status"] == "success"
    assert result["result"]["task_id"].startswith("TASK-")
    assert result["result"]["task"]["status"] == "created"
    assert "已创建" in result["message"]


def test_create_task_en():
    import scripts.commands.task as task_mod
    orig_lang = task_mod.get_language
    task_mod.get_language = lambda cid: "en"
    try:
        result = task.run("OPC-001", {"description": "Research competitors", "timeout_hours": 4})
        assert result["status"] == "success"
        assert "created" in result["message"]
    finally:
        task_mod.get_language = orig_lang


def test_missing_description():
    result = task.run("OPC-001", {})
    assert result["status"] == "error"
    assert "请提供任务描述" in result["message"]
