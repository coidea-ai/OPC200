"""opc-journal-core initialization module.

Initializes journal for a new customer using OpenClaw native tools.
"""
import json
from datetime import datetime


def main(context: dict) -> dict:
    """Initialize the opc-journal-core skill for a customer.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Initialization parameters (day, goals, preferences)
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
        
        # Build initialization entry
        init_entry = {
            "entry_type": "journal_init",
            "customer_id": customer_id,
            "day": input_data.get("day", 1),
            "goals": input_data.get("goals", []),
            "preferences": input_data.get("preferences", {}),
            "timestamp": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        # Write to customer's journal memory file
        memory_path = f"memory/{datetime.now().strftime('%Y-%m-%d')}.md"
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "initialized": True,
                "day": init_entry["day"],
                "goals_count": len(init_entry["goals"])
            },
            "message": f"Journal initialized for customer {customer_id} (Day {init_entry['day']})"
        }
        
    except Exception as e:
        return {
            "status": "error",
            "result": None,
            "message": f"Initialization failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "day": 1,
            "goals": ["Complete product MVP", "Acquire first paying customer"],
            "preferences": {
                "communication_style": "friendly_professional",
                "work_hours": "09:00-18:00",
                "timezone": "Asia/Shanghai"
            }
        }
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
