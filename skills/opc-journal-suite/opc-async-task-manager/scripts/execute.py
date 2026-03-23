"""opc-async-task-manager execute module.

This module handles executing async tasks.
"""

# Add project root to path for imports (must be first)
import sys
from pathlib import Path
_script_dir = Path(__file__).parent.resolve()
_project_root = _script_dir.parent.parent.parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import sys
from pathlib import Path
_script_dir = Path(__file__).parent.resolve()
_project_root = _script_dir.parent.parent.parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Execute an async task.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Execution parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-async-task-manager.execute")
    
    try:
        customer_id = context.get("customer_id")
        input_data = context.get("input", {})
        config = context.get("config", {})
        
        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }
        
        task_id = input_data.get("task_id")
        if not task_id:
            return {
                "status": "error",
                "result": None,
                "message": "task_id is required"
            }
        
        logger.info(f"Executing task for customer: {customer_id}", task_id=task_id)
        
        # Get storage path
        storage_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/tasks")
        )
        
        # Load tasks
        queue_path = storage_path / "queue" / "tasks.json"
        if not queue_path.exists():
            return {
                "status": "error",
                "result": None,
                "message": "Task queue not initialized"
            }
        
        with open(queue_path, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
        
        # Find task
        task = None
        for t in queue_data["tasks"]:
            if t["id"] == task_id:
                task = t
                break
        
        if not task:
            return {
                "status": "error",
                "result": None,
                "message": f"Task not found: {task_id}"
            }
        
        # Check if already completed or failed
        if task["status"] in ["completed", "failed"]:
            return {
                "status": "success",
                "result": {
                    "task_id": task_id,
                    "status": task["status"],
                    "result": task.get("result", {})
                },
                "message": f"Task already {task['status']}"
            }
        
        # Update status to running
        task["status"] = "running"
        task["started_at"] = datetime.now().isoformat()
        
        # Save updated status
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        
        # Simulate task execution (in real implementation, this would call the actual agent)
        execution_result = simulate_task_execution(task)
        
        # Update task with result
        task["status"] = execution_result["status"]
        task["completed_at"] = datetime.now().isoformat()
        task["result"] = execution_result.get("output", {})
        task["execution_log"] = execution_result.get("log", [])
        
        if execution_result["status"] == "failed":
            task["retry_count"] = task.get("retry_count", 0) + 1
            task["error"] = execution_result.get("error", "Unknown error")
        
        # Update stats
        if execution_result["status"] == "completed":
            queue_data["stats"]["total_completed"] = queue_data["stats"].get("total_completed", 0) + 1
        elif execution_result["status"] == "failed":
            queue_data["stats"]["total_failed"] = queue_data["stats"].get("total_failed", 0) + 1
        
        queue_data["stats"]["pending_count"] = len([t for t in queue_data["tasks"] if t["status"] == "pending"])
        
        # Save updated queue
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        
        # Move to completed/failed folder if done
        if execution_result["status"] in ["completed", "failed"]:
            move_to_archive(storage_path, task)
        
        logger.info(f"Task execution completed",
                   customer_id=customer_id,
                   task_id=task_id,
                   status=execution_result["status"])
        
        return {
            "status": "success",
            "result": {
                "task_id": task_id,
                "customer_id": customer_id,
                "status": execution_result["status"],
                "result": execution_result.get("output", {}),
                "execution_time": execution_result.get("execution_time", 0),
                "completed_at": task["completed_at"]
            },
            "message": f"Task {task_id} {execution_result['status']}"
        }
        
    except Exception as e:
        logger.error(f"Failed to execute task", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Task execution failed: {str(e)}"
        }


def simulate_task_execution(task: dict) -> dict:
    """Simulate task execution (placeholder for actual agent execution)."""
    start_time = time.time()
    
    # Simulate processing time
    time.sleep(0.1)
    
    task_type = task.get("task_type", "standard")
    
    # Simulate different outcomes based on task type
    success_rate = 0.9  # 90% success rate
    
    if random.random() < success_rate:
        # Success
        output = generate_task_output(task)
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "output": output,
            "execution_time": round(execution_time, 2),
            "log": [
                {"time": datetime.now().isoformat(), "level": "info", "message": "Task started"},
                {"time": datetime.now().isoformat(), "level": "info", "message": "Processing data"},
                {"time": datetime.now().isoformat(), "level": "info", "message": "Generating output"},
                {"time": datetime.now().isoformat(), "level": "info", "message": "Task completed"}
            ]
        }
    else:
        # Failure
        execution_time = time.time() - start_time
        
        return {
            "status": "failed",
            "error": "Simulated execution failure",
            "execution_time": round(execution_time, 2),
            "log": [
                {"time": datetime.now().isoformat(), "level": "info", "message": "Task started"},
                {"time": datetime.now().isoformat(), "level": "error", "message": "Execution failed"}
            ]
        }


def generate_task_output(task: dict) -> dict:
    """Generate simulated task output based on task type."""
    task_type = task.get("task_type", "standard")
    
    if task_type == "research":
        return {
            "summary": f"Research completed for: {task.get('title', '')}",
            "findings": [
                "Finding 1: Key insight from research",
                "Finding 2: Important trend identified",
                "Finding 3: Recommendation based on data"
            ],
            "sources": ["Source A", "Source B", "Source C"],
            "confidence": 0.85
        }
    elif task_type == "analysis":
        return {
            "summary": f"Analysis completed for: {task.get('title', '')}",
            "metrics": {
                "total_items": 100,
                "average_score": 7.5,
                "top_performer": "Item X"
            },
            "recommendations": ["Recommendation 1", "Recommendation 2"]
        }
    elif task_type == "writing":
        return {
            "summary": f"Document created: {task.get('title', '')}",
            "word_count": 1250,
            "sections": ["Introduction", "Main Content", "Conclusion"],
            "file_path": task.get("output_location", "output.md")
        }
    else:
        return {
            "summary": f"Task completed: {task.get('title', '')}",
            "status": "success"
        }


def move_to_archive(storage_path: Path, task: dict) -> None:
    """Move completed/failed task to archive folder."""
    status = task["status"]
    archive_folder = storage_path / status
    archive_folder.mkdir(exist_ok=True)
    
    archive_file = archive_folder / f"{task['id']}.json"
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(task, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "task_id": "TASK-20260324-ABC123"
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/tasks"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
