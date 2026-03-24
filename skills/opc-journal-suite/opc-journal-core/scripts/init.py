"""opc-journal-core initialization module.

This module handles the initialization of the journal core skill,
including configuration loading and database setup.
"""
# Add project root to path for imports (must be first)
import sys
from pathlib import Path
_script_dir = Path(__file__).parent.resolve()
_project_root = _script_dir.parent.parent.parent.parent.resolve()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import json
import os
import sqlite3
from typing import Any, Optional

# Try import with fallback to ensure src is found
try:
    from src.journal.core import JournalManager
    from src.journal.storage import SQLiteStorage
    from src.utils.logging import Logger, get_logger
except ImportError as e:
    # If import fails, try adding current working directory
    import os as _os
    _cwd = _os.getcwd()
    if _cwd not in sys.path:
        sys.path.insert(0, _cwd)
    from src.journal.core import JournalManager
    from src.journal.storage import SQLiteStorage
    from src.utils.logging import Logger, get_logger


def main(context: dict) -> dict:
    """Initialize the opc-journal-core skill.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Initialization parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-journal-core.init")
    
    try:
        customer_id = context.get("customer_id")
        input_data = context.get("input", {})
        config = context.get("config", {})
        memory = context.get("memory", {})
        
        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }
        
        logger.info(f"Initializing journal core for customer: {customer_id}")
        
        # Get storage path from input.data_dir, config.storage.path, or use default
        storage_config = config.get("storage", {})
        if input_data.get("data_dir"):
            base_path = Path(input_data["data_dir"]) / customer_id / "journal"
        elif storage_config.get("path"):
            base_path = Path(storage_config["path"])
        else:
            base_path = Path(f"customers/{customer_id}/journal")
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        db_path = base_path / "journal.db"
        storage = SQLiteStorage(db_path=db_path)
        storage.create_tables()
        
        # Create initial customer configuration
        customer_config = {
            "customer_id": customer_id,
            "initialized_at": memory.get("timestamp", ""),
            "storage_path": str(base_path),
            "privacy_level": config.get("privacy", {}).get("default_level", "normal"),
            "retention_days": config.get("retention_days", 365),
        }
        
        # Save customer configuration
        config_path = base_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(customer_config, f, indent=2)
        
        logger.info(f"Journal core initialized successfully", 
                   customer_id=customer_id, 
                   db_path=str(db_path))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "storage_path": str(base_path),
                "db_path": str(db_path),
                "initialized": True
            },
            "message": f"Journal core initialized for customer {customer_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize journal core", error=str(e))
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
            "storage": {"path": "test_customers/OPC-TEST-001/journal"},
            "privacy": {"default_level": "normal"},
            "retention_days": 365
        },
        "memory": {"timestamp": "2026-03-24T03:38:00Z"}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
