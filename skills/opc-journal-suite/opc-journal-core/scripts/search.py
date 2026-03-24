"""opc-journal-core search module.

This module handles searching journal entries with various filters.
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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from src.journal.core import JournalManager
from src.journal.storage import SQLiteStorage
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Search journal entries.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Search parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-journal-core.search")
    
    try:
        customer_id = context.get("customer_id")
        input_data = context.get("input", {})
        config = context.get("config", {})
        
        if not customer_id:
            return {
                "status": "error",
                "result": None,
                "message": "customer_id is required"
            }
        
        logger.info(f"Searching journal entries for customer: {customer_id}")
        
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
        
        # Get search parameters
        query = input_data.get("query", "")
        tags = input_data.get("tags", [])
        time_range = input_data.get("time_range", "all")  # all, last_7_days, last_30_days
        limit = input_data.get("limit", 50)
        offset = input_data.get("offset", 0)
        
        entries = []
        
        # Search by query
        if query:
            entries = manager.search_entries(query)
            logger.info(f"Searched by query: {query}", count=len(entries))
        
        # Filter by tags
        elif tags:
            all_entries = []
            for tag in tags:
                tagged_entries = manager.list_entries_by_tag(tag)
                all_entries.extend(tagged_entries)
            # Remove duplicates
            seen_ids = set()
            entries = []
            for entry in all_entries:
                if entry.id not in seen_ids:
                    seen_ids.add(entry.id)
                    entries.append(entry)
            logger.info(f"Searched by tags: {tags}", count=len(entries))
        
        # List all entries
        else:
            entries = manager.list_entries(limit=10000)
            logger.info(f"Listed all entries", count=len(entries))
        
        # Filter by time range
        if time_range != "all":
            now = datetime.now()
            if time_range == "last_7_days":
                cutoff = now - timedelta(days=7)
            elif time_range == "last_30_days":
                cutoff = now - timedelta(days=30)
            elif time_range == "last_90_days":
                cutoff = now - timedelta(days=90)
            else:
                cutoff = None
            
            if cutoff:
                entries = [e for e in entries if e.created_at >= cutoff]
        
        # Apply pagination
        total_count = len(entries)
        entries = entries[offset:offset + limit]
        
        # Format results
        results = []
        for entry in entries:
            results.append({
                "id": entry.id,
                "content": entry.content[:200] + "..." if len(entry.content) > 200 else entry.content,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat()
            })
        
        logger.info(f"Search completed", 
                   customer_id=customer_id,
                   total_count=total_count,
                   returned_count=len(results))
        
        return {
            "status": "success",
            "result": {
                "entries": results,
                "total_count": total_count,
                "returned_count": len(results),
                "query": query,
                "tags": tags,
                "time_range": time_range
            },
            "message": f"Found {total_count} entries, returned {len(results)}"
        }
        
    except Exception as e:
        logger.error(f"Failed to search journal entries", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Search failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "query": "数据库",
            "time_range": "last_30_days",
            "limit": 10
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/journal"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
