"""Journal command: record."""
import uuid
from datetime import datetime

from utils.storage import build_memory_path, write_memory_file


def generate_entry_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"JE-{today}-{suffix}"


def run(customer_id: str, args: dict) -> dict:
    """Record a journal entry."""
    content = args.get("content", "")
    if not content:
        return {"status": "error", "result": None, "message": "content is required"}

    entry_id = generate_entry_id()
    day = args.get("day", 1)
    metadata = args.get("metadata", {})

    entry_text = f"""## Journal Entry - {entry_id}

**Day**: {day}  
**Time**: {datetime.now().isoformat()}

{content}

**Metadata**: {metadata}
"""

    memory_path = build_memory_path(customer_id)
    write_result = write_memory_file(memory_path, entry_text)

    if write_result["success"]:
        return {
            "status": "success",
            "result": {
                "entry_id": entry_id,
                "customer_id": customer_id,
                "day": day,
                "memory_path": memory_path
            },
            "message": f"Entry {entry_id} recorded"
        }
    return {
        "status": "error",
        "result": None,
        "message": f"Failed to write entry: {write_result.get('error')}"
    }
