"""opc-async-task-manager create module.

This module handles creating async tasks.
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
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.utils.logging import get_logger


def generate_task_id() -> str:
    """Generate a unique task ID in format TASK-{YYYYMMDD}-{SEQ}."""
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TASK-{today}-{suffix}"


def parse_duration(duration_str: str) -> int:
    """Parse duration string to hours."""
    if not duration_str:
        return 8
    
    duration_str = duration_str.lower().strip()
    
    if duration_str.endswith("h"):
        return int(duration_str[:-1])
    elif duration_str.endswith("m"):
        return int(duration_str[:-1]) // 60
    elif duration_str.endswith("d"):
        return int(duration_str[:-1]) * 24
    
    # Try to parse as integer (assume hours)
    try:
        return int(duration_str)
    except ValueError:
        return 8


def main(context: dict) -> dict:
    """Create an async task.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Task parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-async-task-manager.create")
    
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
        
        # Validate required fields
        title = input_data.get("title", "")
        if not title:
            return {
                "status": "error",
                "result": None,
                "message": "title is required"
            }
        
        logger.info(f"Creating async task for customer: {customer_id}", title=title)
        
        # Get storage path
        storage_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/tasks")
        )
        
        # Load existing tasks
        queue_path = storage_path / "queue" / "tasks.json"
        if queue_path.exists():
            with open(queue_path, "r", encoding="utf-8") as f:
                queue_data = json.load(f)
        else:
            queue_data = {"customer_id": customer_id, "tasks": [], "stats": {}}
        
        # Generate task ID
        task_id = generate_task_id()
        
        # Parse parameters
        task_type = input_data.get("task_type", "standard")
        estimated_duration = input_data.get("estimated_duration", config.get("default_timeout", "8h"))
        deadline_str = input_data.get("deadline")
        agent = input_data.get("agent", "DefaultAgent")
        
        # Calculate deadline
        if deadline_str:
            # Handle relative deadlines like "tomorrow 08:00"
            if deadline_str.startswith("tomorrow"):
                tomorrow = datetime.now() + timedelta(days=1)
                time_part = deadline_str.replace("tomorrow", "").strip()
                if time_part:
                    try:
                        hour = int(time_part.split(":")[0])
                        deadline = tomorrow.replace(hour=hour, minute=0, second=0, microsecond=0)
                    except ValueError:
                        deadline = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
                else:
                    deadline = tomorrow.replace(hour=8, minute=0, second=0, microsecond=0)
            else:
                try:
                    deadline = datetime.fromisoformat(deadline_str)
                except ValueError:
                    deadline = datetime.now() + timedelta(hours=parse_duration(estimated_duration))
        else:
            deadline = datetime.now() + timedelta(hours=parse_duration(estimated_duration))
        
        # Create task object
        task = {
            "id": task_id,
            "title": title,
            "description": input_data.get("description", ""),
            "task_type": task_type,
            "agent": agent,
            "estimated_duration": estimated_duration,
            "deadline": deadline.isoformat(),
            "created_at": datetime.now().isoformat(),
            "status": "pending",
            "priority": input_data.get("priority", 5),
            "customer_id": customer_id,
            "notify_on_complete": input_data.get("notify_on_complete", True),
            "notify_channels": input_data.get("notify_channels", config.get("notification_channels", ["feishu"])),
            "output_format": input_data.get("output_format", "markdown"),
            "output_location": input_data.get("output_location"),
            "dependencies": input_data.get("dependencies", []),
            "retry_count": 0,
            "max_retries": input_data.get("max_retries", 3)
        }
        
        # Add to queue
        queue_data["tasks"].append(task)
        
        # Update stats
        queue_data["stats"]["total_created"] = queue_data["stats"].get("total_created", 0) + 1
        queue_data["stats"]["pending_count"] = len([t for t in queue_data["tasks"] if t["status"] == "pending"])
        
        # Save queue
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Async task created successfully",
                   customer_id=customer_id,
                   task_id=task_id,
                   task_type=task_type)
        
        # Generate execution plan
        execution_plan = generate_execution_plan(task)
        
        return {
            "status": "success",
            "result": {
                "task_id": task_id,
                "customer_id": customer_id,
                "title": title,
                "deadline": deadline.isoformat(),
                "agent": agent,
                "status": "pending",
                "execution_plan": execution_plan,
                "queue_position": queue_data["stats"]["pending_count"]
            },
            "message": f"Task created: {task_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to create async task", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Task creation failed: {str(e)}"
        }


def generate_execution_plan(task: dict) -> list:
    """Generate an execution plan for the task."""
    plan = []
    
    created_at = datetime.fromisoformat(task["created_at"])
    deadline = datetime.fromisoformat(task["deadline"])
    duration = parse_duration(task.get("estimated_duration", "4h"))
    
    # Start time
    start_time = created_at
    plan.append({
        "time": start_time.isoformat(),
        "phase": "queued",
        "description": "Task queued for execution"
    })
    
    # Execution phases
    if duration <= 1:
        phases = [
            ("execution", 0.5, "Task execution"),
            ("completion", 0.5, "Task completion and notification")
        ]
    elif duration <= 4:
        phases = [
            ("data_collection", 1, "Data collection and analysis"),
            ("processing", duration - 2, "Main processing"),
            ("completion", 1, "Result compilation and notification")
        ]
    else:
        phases = [
            ("data_collection", 2, "Data collection"),
            ("analysis", duration * 0.4, "Analysis phase"),
            ("processing", duration * 0.4, "Processing phase"),
            ("compilation", 1, "Result compilation"),
            ("notification", 0.5, "Notification and delivery")
        ]
    
    current_time = start_time
    for phase_name, duration_hours, description in phases:
        current_time += timedelta(hours=duration_hours)
        if current_time > deadline:
            current_time = deadline
        plan.append({
            "time": current_time.isoformat(),
            "phase": phase_name,
            "description": description
        })
    
    return plan


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "title": "竞品分析报告",
            "description": "分析 5 个主要竞争对手的产品功能、定价策略",
            "task_type": "research",
            "estimated_duration": "4h",
            "agent": "ResearchAgent",
            "deadline": "tomorrow 08:00",
            "priority": 5,
            "notify_on_complete": True,
            "output_format": "markdown_report"
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/tasks"},
            "default_timeout": "8h",
            "notification_channels": ["feishu"]
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
