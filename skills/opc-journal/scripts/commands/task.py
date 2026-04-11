"""Journal command: task (legacy async task tracking)."""
import uuid
from datetime import datetime, timedelta

from scripts.commands._meta import get_language


def generate_task_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"TASK-{today}-{suffix}"


def run(customer_id: str, args: dict) -> dict:
    """Create an async task."""
    task_type = args.get("type", "research")
    description = args.get("description", "")
    timeout_hours = args.get("timeout_hours", 8)
    lang = get_language(customer_id)

    if not description:
        return {"status": "error", "result": None, "message": ("description is required" if lang == "en" else "请提供任务描述（description 不能为空）")}

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

    msg = f"Task {task_id} created, ETA: {eta.strftime('%Y-%m-%d %H:%M')}" if lang == "en" else f"任务 {task_id} 已创建，预计完成时间：{eta.strftime('%Y-%m-%d %H:%M')}"
    return {
        "status": "success",
        "result": {"task_id": task_id, "task": task},
        "message": msg
    }
