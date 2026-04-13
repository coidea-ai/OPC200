"""Journal command: batch-task (create multiple async tasks at once)."""
import uuid
from datetime import datetime, timedelta
from typing import List


def generate_task_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TASK-{today}-{suffix}"


def run(customer_id: str, args: dict) -> dict:
    """Create multiple async task records at once."""
    descriptions = args.get("descriptions")
    task_type = args.get("type", "research")
    timeout_hours = args.get("timeout_hours", 8)

    if descriptions is None:
        return {"status": "error", "result": None, "message": "descriptions list is required"}

    if not isinstance(descriptions, list):
        descriptions = [descriptions]

    if not descriptions:
        return {"status": "error", "result": None, "message": "No valid task descriptions provided"}

    created_tasks = []
    now = datetime.now()
    eta = now + timedelta(hours=timeout_hours)

    for desc in descriptions:
        if not desc or not isinstance(desc, str):
            continue
        task_id = generate_task_id()
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "customer_id": customer_id,
            "description": desc,
            "status": "created",
            "created_at": now.isoformat(),
            "estimated_completion": eta.isoformat(),
            "timeout_hours": timeout_hours,
        }
        created_tasks.append(task)

    if not created_tasks:
        return {"status": "error", "result": None, "message": "No valid task descriptions provided"}

    return {
        "status": "success",
        "result": {
            "customer_id": customer_id,
            "tasks_created": len(created_tasks),
            "tasks": created_tasks,
            "task_type": task_type,
            "timeout_hours": timeout_hours,
        },
        "message": f"Created {len(created_tasks)} task(s)",
    }
