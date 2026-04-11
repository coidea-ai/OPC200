"""Journal command: task (legacy async task tracking)."""
import uuid
from datetime import datetime, timedelta


def generate_task_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TASK-{today}-{suffix}"


def run(customer_id: str, args: dict) -> dict:
    """Create an async task."""
    task_type = args.get("type", "research")
    description = args.get("description", "")
    timeout_hours = args.get("timeout_hours", 8)

    if not description:
        return {"status": "error", "result": None, "message": "description is required"}

    task_id = generate_task_id()
    now = datetime.now()
    eta = now + timedelta(hours=timeout_hours)

    task = {
        "task_id": task_id,
        "task_type": task_type,
        "customer_id": customer_id,
        "description": description,
        "status": "created",
        "created_at": now.isoformat(),
        "estimated_completion": eta.isoformat(),
        "timeout_hours": timeout_hours
    }

    return {
        "status": "success",
        "result": {"task_id": task_id, "task": task},
        "message": f"Task {task_id} created, ETA: {eta.strftime('%Y-%m-%d %H:%M')}"
    }
