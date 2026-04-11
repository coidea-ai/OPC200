"""Journal command: initialize."""
import json
from datetime import datetime

from utils.storage import build_memory_path, write_memory_file


def run(customer_id: str, args: dict) -> dict:
    """Initialize journal for customer."""
    day = args.get("day", 1)
    goals = args.get("goals", [])
    preferences = args.get("preferences", {})

    init_entry = {
        "entry_type": "journal_init",
        "customer_id": customer_id,
        "day": day,
        "goals": goals,
        "preferences": preferences,
        "timestamp": datetime.now().isoformat(),
        "version": "2.4.0"
    }

    goals_md = "\n".join(f"- {g}" for g in goals)
    prefs_json = json.dumps(preferences, indent=2, ensure_ascii=False)

    content = f"""# Journal Init - {init_entry['timestamp'][:10]}

**Entry Type**: {init_entry['entry_type']}  
**Customer**: {customer_id}  
**Day**: {day}

## Goals
{goals_md}

## Preferences
```json
{prefs_json}
```
"""

    memory_path = build_memory_path(customer_id)
    write_result = write_memory_file(memory_path, content)

    if write_result["success"]:
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "initialized": True,
                "day": day,
                "goals_count": len(goals),
                "memory_path": memory_path
            },
            "message": f"Journal initialized for {customer_id} (Day {day})"
        }
    return {
        "status": "error",
        "result": None,
        "message": f"Failed to write memory: {write_result.get('error')}"
    }
