"""opc-journal-core export module.

This module handles exporting journal entries to various formats.
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
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.journal.core import JournalManager
from src.journal.storage import SQLiteStorage
from src.utils.logging import get_logger


def export_to_markdown(entries: list, include_metadata: bool = True) -> str:
    """Export entries to Markdown format."""
    lines = []
    lines.append("# Journal Export")
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Total Entries: {len(entries)}")
    lines.append("")
    
    for i, entry in enumerate(entries, 1):
        lines.append(f"## Entry {i}: {entry.id}")
        lines.append(f"**Date:** {entry.created_at.strftime('%Y-%m-%d %H:%M')}")
        
        if entry.tags:
            lines.append(f"**Tags:** {', '.join(entry.tags)}")
        
        lines.append("")
        lines.append(entry.content)
        
        if include_metadata and entry.metadata:
            lines.append("")
            lines.append("**Metadata:**")
            for key, value in entry.metadata.items():
                if key not in ["entry_id", "customer_id"]:
                    lines.append(f"- {key}: {value}")
        
        lines.append("")
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def export_to_jsonl(entries: list) -> str:
    """Export entries to JSONL format."""
    lines = []
    for entry in entries:
        lines.append(json.dumps(entry.to_dict(), ensure_ascii=False))
    return "\n".join(lines)


def main(context: dict) -> dict:
    """Export journal entries.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Export parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-journal-core.export")
    
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
        
        # Get export parameters
        format_type = input_data.get("format", "json")  # json, markdown, jsonl
        time_range = input_data.get("time_range", "all")
        tags = input_data.get("tags", [])
        output_path = input_data.get("output_path")
        include_metadata = input_data.get("include_metadata", True)
        
        logger.info(f"Exporting journal entries for customer: {customer_id}", 
                   format=format_type)
        
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
        
        # Get entries
        if tags:
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
        else:
            entries = manager.list_entries(limit=10000)
        
        # Sort by created_at
        entries.sort(key=lambda e: e.created_at)
        
        # Generate export content
        if format_type == "markdown":
            content = export_to_markdown(entries, include_metadata)
            extension = "md"
        elif format_type == "jsonl":
            content = export_to_jsonl(entries)
            extension = "jsonl"
        else:  # json
            content = json.dumps(
                [e.to_dict() for e in entries], 
                indent=2, 
                ensure_ascii=False
            )
            extension = "json"
        
        # Determine output path
        if not output_path:
            export_dir = base_path / "export"
            export_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = export_dir / f"journal_export_{timestamp}.{extension}"
        else:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        logger.info(f"Export completed", 
                   customer_id=customer_id,
                   format=format_type,
                   entry_count=len(entries),
                   output_path=str(output_path))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "format": format_type,
                "entry_count": len(entries),
                "output_path": str(output_path),
                "exported_at": datetime.now().isoformat()
            },
            "message": f"Exported {len(entries)} entries to {output_path}"
        }
        
    except Exception as e:
        logger.error(f"Failed to export journal entries", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Export failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "format": "markdown",
            "include_metadata": True
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/journal"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
