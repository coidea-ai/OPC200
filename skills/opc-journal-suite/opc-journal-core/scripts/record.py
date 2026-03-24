"""opc-journal-core record module.

This module handles recording journal entries with full context.
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
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.journal.core import JournalEntry, JournalManager
from src.journal.storage import SQLiteStorage
from src.utils.logging import get_logger


def generate_entry_id(customer_id: str) -> str:
    """Generate a unique entry ID in format JE-{YYYYMMDD}-{SEQ}."""
    today = datetime.now().strftime("%Y%m%d")
    # Use UUID suffix for uniqueness
    suffix = uuid.uuid4().hex[:6].upper()
    return f"JE-{today}-{suffix}"


def main(context: dict) -> dict:
    """Record a journal entry.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Entry content and metadata
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-journal-core.record")
    
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
        
        # Get content from input
        content = input_data.get("content", "")
        if not content:
            return {
                "status": "error",
                "result": None,
                "message": "content is required"
            }
        
        logger.info(f"Recording journal entry for customer: {customer_id}")
        
        # Get storage path from input.data_dir, config.storage.path, or use default
        storage_config = config.get("storage", {})
        if input_data.get("data_dir"):
            base_path = Path(input_data["data_dir"]) / customer_id / "journal"
        elif storage_config.get("path"):
            base_path = Path(storage_config["path"])
        else:
            base_path = Path(f"customers/{customer_id}/journal")
        db_path = base_path / "journal.db"
        
        if not db_path.exists():
            return {
                "status": "error",
                "result": None,
                "message": "Journal not initialized. Please run init first."
            }
        
        # Initialize storage and manager
        storage = SQLiteStorage(db_path=db_path)
        conn = storage.connection
        manager = JournalManager(conn)
        
        # Prepare metadata
        metadata = input_data.get("metadata", {})
        metadata.update({
            "entry_id": generate_entry_id(customer_id),
            "customer_id": customer_id,
            "session_id": memory.get("session_id", ""),
            "timestamp": datetime.now().isoformat(),
            "agents_involved": input_data.get("agents_involved", []),
            "tasks_created": input_data.get("tasks_created", []),
            "tasks_completed": input_data.get("tasks_completed", []),
            "emotional_state": input_data.get("emotional_state", "neutral"),
            "energy_level": input_data.get("energy_level", 5),
            "urgency": input_data.get("urgency", "normal"),
            "topic_category": input_data.get("topic_category", "general"),
        })
        
        # Create entry
        tags = input_data.get("tags", [])
        if input_data.get("topic_category"):
            tags.append(input_data["topic_category"])
        
        entry = JournalEntry(
            id=metadata["entry_id"],
            content=content,
            tags=tags,
            metadata=metadata
        )
        
        # Save entry
        manager.create_entry(entry)
        
        logger.info(f"Journal entry recorded", 
                   customer_id=customer_id,
                   entry_id=entry.id,
                   content_length=len(content))
        
        return {
            "status": "success",
            "result": {
                "entry_id": entry.id,
                "customer_id": customer_id,
                "created_at": entry.created_at.isoformat(),
                "tags": tags,
                "metadata": {k: v for k, v in metadata.items() if k not in ["entry_id", "customer_id"]}
            },
            "message": f"Journal entry recorded successfully: {entry.id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to record journal entry", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Recording failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "content": "今天完成了用户注册功能，但遇到数据库连接问题",
            "tags": ["development", "database"],
            "metadata": {
                "agents_involved": ["DevAgent"],
                "tasks_completed": ["FEAT-001"],
                "emotional_state": "frustrated_but_determined",
                "energy_level": 6
            }
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/journal"}
        },
        "memory": {"session_id": "test-session-001"}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
