"""opc-async-task-manager initialization module.

This module handles the initialization of the async task manager skill.
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
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Initialize the opc-async-task-manager skill.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Initialization parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-async-task-manager.init")
    
    try:
        customer_id = context.get("customer_id")
        config = context.get("config", {})
        memory = context.get("memory", {})
        
        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }
        
        logger.info(f"Initializing async task manager for customer: {customer_id}")
        
        # Get storage path
        storage_config = config.get("storage", {})
        base_path = Path(storage_config.get("path", f"customers/{customer_id}/tasks"))
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (base_path / "queue").mkdir(exist_ok=True)
        (base_path / "completed").mkdir(exist_ok=True)
        (base_path / "failed").mkdir(exist_ok=True)
        
        # Create initial configuration
        customer_config = {
            "customer_id": customer_id,
            "initialized_at": memory.get("timestamp", ""),
            "storage_path": str(base_path),
            "max_concurrent": config.get("max_concurrent", 5),
            "default_timeout": config.get("default_timeout", "8h"),
            "notification_channels": config.get("notification_channels", ["feishu"]),
            "retry_policy": {
                "max_attempts": 3,
                "backoff_strategy": "exponential"
            }
        }
        
        # Save configuration
        config_path = base_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(customer_config, f, indent=2)
        
        # Initialize task queue
        queue_data = {
            "customer_id": customer_id,
            "tasks": [],
            "stats": {
                "total_created": 0,
                "total_completed": 0,
                "total_failed": 0,
                "pending_count": 0
            }
        }
        
        queue_path = base_path / "queue" / "tasks.json"
        with open(queue_path, "w", encoding="utf-8") as f:
            json.dump(queue_data, f, indent=2)
        
        logger.info(f"Async task manager initialized successfully",
                   customer_id=customer_id,
                   storage_path=str(base_path))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "storage_path": str(base_path),
                "initialized": True,
                "max_concurrent": customer_config["max_concurrent"]
            },
            "message": f"Async task manager initialized for customer {customer_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize async task manager", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Initialization failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {},
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/tasks"},
            "max_concurrent": 5,
            "default_timeout": "8h",
            "notification_channels": ["feishu"]
        },
        "memory": {"timestamp": "2026-03-24T03:38:00Z"}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
