"""opc-journal-core record module.

Records journal entries using OpenClaw native tools.
"""
import json
import uuid
from datetime import datetime


def generate_entry_id(customer_id: str) -> str:
    """Generate a unique entry ID."""
    today = datetime.now().strftime("%Y%m%d")
    suffix = uuid.uuid4().hex[:6].upper()
    return f"JE-{today}-{suffix}"


def main(context: dict) -> dict:
    """Record a journal entry.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Entry content and metadata
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    try:
        customer_id = context.get("customer_id")
        input_data = context.get("input", {})
        
        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }
        
        content = input_data.get("content")
        if not content:
            return {
                "status": "error",
                "result": None,
                "message": "content is required"
            }
        
        # Build entry
        entry_id = generate_entry_id(customer_id)
        entry = {
            "entry_id": entry_id,
            "entry_type": "journal_entry",
            "customer_id": customer_id,
            "content": content,
            "metadata": input_data.get("metadata", {}),
            "timestamp": datetime.now().isoformat(),
            "day": input_data.get("day", 1)
        }
        
        # Return entry for caller to store via memory tools
        return {
            "status": "success",
            "result": {
                "entry_id": entry_id,
                "entry": entry,
                "storage_hint": f"Write entry to memory file using 'write' tool"
            },
            "message": f"Entry {entry_id} created successfully"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Failed to record entry: {str(e)}"
        }


if __name__ == "__main__":
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "content": "Completed user registration feature today, but encountered database connection issues",
            "day": 1,
            "metadata": {
                "agents_involved": ["DevAgent"],
                "emotional_state": "frustrated_but_determined"
            }
        }
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
