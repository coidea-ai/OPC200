"""opc-async-task-manager status module.

This module handles querying async task status.
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
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Query async task status.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Query parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-async-task-manager.status")
    
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
        list_all = input_data.get("list_all", False)
        status_filter = input_data.get("status")  # pending, running, completed, failed, all
        
        logger.info(f"Querying task status for customer: {customer_id}",
                   task_id=task_id, list_all=list_all)
        
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
        
        tasks = queue_data.get("tasks", [])
        
        # Filter by task_id
        if task_id:
            task = None
            for t in tasks:
                if t["id"] == task_id:
                    task = t
                    break
            
            if not task:
                # Check archived tasks
                for archive_status in ["completed", "failed"]:
                    archive_file = storage_path / archive_status / f"{task_id}.json"
                    if archive_file.exists():
                        with open(archive_file, "r", encoding="utf-8") as f:
                            task = json.load(f)
                        break
            
            if not task:
                return {
                    "status": "error",
                    "result": None,
                    "message": f"Task not found: {task_id}"
                }
            
            # Calculate progress for running tasks
            progress = calculate_progress(task)
            
            # Calculate time metrics
            time_metrics = calculate_time_metrics(task)
            
            logger.info(f"Task status retrieved",
                       customer_id=customer_id,
                       task_id=task_id,
                       status=task["status"])
            
            return {
                "status": "success",
                "result": {
                    "task_id": task_id,
                    "customer_id": customer_id,
                    "task": sanitize_task_for_output(task),
                    "progress": progress,
                    "time_metrics": time_metrics,
                    "queried_at": datetime.now().isoformat()
                },
                "message": f"Task {task_id} status: {task['status']}"
            }
        
        # List all tasks
        if list_all or status_filter:
            filtered_tasks = tasks
            
            if status_filter and status_filter != "all":
                filtered_tasks = [t for t in tasks if t["status"] == status_filter]
            
            # Sort by created_at (newest first)
            filtered_tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
            
            # Limit results
            limit = input_data.get("limit", 50)
            offset = input_data.get("offset", 0)
            total_count = len(filtered_tasks)
            filtered_tasks = filtered_tasks[offset:offset + limit]
            
            # Sanitize output
            sanitized_tasks = [sanitize_task_for_output(t) for t in filtered_tasks]
            
            # Get queue stats
            stats = queue_data.get("stats", {})
            
            logger.info(f"Task list retrieved",
                       customer_id=customer_id,
                       total_count=total_count,
                       returned_count=len(sanitized_tasks))
            
            return {
                "status": "success",
                "result": {
                    "customer_id": customer_id,
                    "tasks": sanitized_tasks,
                    "total_count": total_count,
                    "returned_count": len(sanitized_tasks),
                    "stats": {
                        "pending": stats.get("pending_count", 0),
                        "completed": stats.get("total_completed", 0),
                        "failed": stats.get("total_failed", 0),
                        "total_created": stats.get("total_created", 0)
                    },
                    "filter": status_filter,
                    "queried_at": datetime.now().isoformat()
                },
                "message": f"Found {total_count} tasks, returned {len(sanitized_tasks)}"
            }
        
        # No specific query - return queue stats
        stats = queue_data.get("stats", {})
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "queue_stats": stats,
                "pending_tasks": len([t for t in tasks if t["status"] == "pending"]),
                "running_tasks": len([t for t in tasks if t["status"] == "running"]),
                "queried_at": datetime.now().isoformat()
            },
            "message": "Queue statistics retrieved"
        }
        
    except Exception as e:
        logger.error(f"Failed to query task status", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Status query failed: {str(e)}"
        }


def calculate_progress(task: dict) -> dict:
    """Calculate task progress for running tasks."""
    if task["status"] == "pending":
        return {"percentage": 0, "status": "Waiting in queue"}
    
    if task["status"] == "completed":
        return {"percentage": 100, "status": "Completed"}
    
    if task["status"] == "failed":
        return {"percentage": 0, "status": "Failed"}
    
    if task["status"] == "running":
        # Estimate progress based on time elapsed vs estimated duration
        started_at = datetime.fromisoformat(task.get("started_at", datetime.now().isoformat()))
        elapsed = (datetime.now() - started_at).total_seconds() / 3600  # hours
        
        # Parse estimated duration
        duration_str = task.get("estimated_duration", "4h")
        try:
            if duration_str.endswith("h"):
                estimated = float(duration_str[:-1])
            elif duration_str.endswith("m"):
                estimated = float(duration_str[:-1]) / 60
            else:
                estimated = float(duration_str)
        except ValueError:
            estimated = 4
        
        percentage = min(95, int((elapsed / max(0.1, estimated)) * 100))
        
        return {
            "percentage": percentage,
            "elapsed_hours": round(elapsed, 2),
            "estimated_hours": estimated,
            "status": "Running"
        }
    
    return {"percentage": 0, "status": "Unknown"}


def calculate_time_metrics(task: dict) -> dict:
    """Calculate time-related metrics for a task."""
    metrics = {}
    
    created_at = task.get("created_at")
    started_at = task.get("started_at")
    completed_at = task.get("completed_at")
    deadline_str = task.get("deadline")
    
    if created_at:
        metrics["created_at"] = created_at
        created = datetime.fromisoformat(created_at)
        
        if completed_at:
            completed = datetime.fromisoformat(completed_at)
            metrics["total_duration"] = round((completed - created).total_seconds() / 3600, 2)
        
        if started_at:
            started = datetime.fromisoformat(started_at)
            metrics["queue_wait_time"] = round((started - created).total_seconds() / 60, 2)  # minutes
            
            if completed_at:
                completed = datetime.fromisoformat(completed_at)
                metrics["execution_time"] = round((completed - started).total_seconds() / 3600, 2)
    
    if deadline_str:
        deadline = datetime.fromisoformat(deadline_str)
        now = datetime.now()
        
        if task["status"] in ["completed", "failed"]:
            if completed_at:
                completed = datetime.fromisoformat(completed_at)
                metrics["completed_on_time"] = completed <= deadline
                if completed > deadline:
                    metrics["overdue_by_hours"] = round((completed - deadline).total_seconds() / 3600, 2)
        else:
            if now > deadline:
                metrics["overdue"] = True
                metrics["overdue_by_hours"] = round((now - deadline).total_seconds() / 3600, 2)
            else:
                metrics["overdue"] = False
                metrics["time_remaining_hours"] = round((deadline - now).total_seconds() / 3600, 2)
    
    return metrics


def sanitize_task_for_output(task: dict) -> dict:
    """Sanitize task for output (remove internal fields)."""
    return {
        "id": task.get("id"),
        "title": task.get("title"),
        "description": task.get("description", "")[:200],
        "task_type": task.get("task_type"),
        "agent": task.get("agent"),
        "status": task.get("status"),
        "priority": task.get("priority"),
        "created_at": task.get("created_at"),
        "started_at": task.get("started_at"),
        "completed_at": task.get("completed_at"),
        "deadline": task.get("deadline"),
        "retry_count": task.get("retry_count", 0)
    }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "list_all": True,
            "status": "all",
            "limit": 10
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/tasks"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
