"""Unified storage utilities for OPC Journal."""

import os
from datetime import datetime
from typing import Dict, List, Any, Optional


def build_memory_path(customer_id: str, date: str = None) -> str:
    """Build standard memory file path."""
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")
    return f"~/.openclaw/customers/{customer_id}/memory/{date}.md"


def build_customer_dir(customer_id: str) -> str:
    """Build customer base directory path."""
    return f"~/.openclaw/customers/{customer_id}"


def write_memory_file(path: str, content: str, mode: str = "a") -> Dict[str, Any]:
    """Write content to memory file."""
    try:
        full_path = os.path.expanduser(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, mode) as f:
            if mode == "a" and f.tell() > 0:
                f.write("\n\n")
            f.write(content)
        return {
            "success": True,
            "path": full_path,
            "bytes_written": len(content.encode("utf-8"))
        }
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": "storage_error"}


def read_memory_file(path: str) -> Dict[str, Any]:
    """Read content from memory file."""
    try:
        full_path = os.path.expanduser(path)
        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File not found: {path}",
                "error_type": "file_not_found"
            }
        with open(full_path, "r") as f:
            content = f.read()
        return {"success": True, "content": content, "path": full_path}
    except Exception as e:
        return {"success": False, "error": str(e), "error_type": "storage_error"}


def create_tool_call(tool: str, params: dict, sequence: int = 1) -> dict:
    """Create standardized tool call."""
    return {"tool": tool, "params": params, "sequence": sequence}


def format_result(status: str, result: Any, message: str) -> dict:
    """Format standardized result."""
    return {
        "status": status,
        "result": result,
        "message": message,
        "_schema_version": "1.0"
    }
