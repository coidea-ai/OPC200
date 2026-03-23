"""opc-pattern-recognition initialization module.

This module handles the initialization of the pattern recognition skill.
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

from src.patterns.analyzer import PatternStore
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Initialize the opc-pattern-recognition skill.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Initialization parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-pattern-recognition.init")
    
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
        
        logger.info(f"Initializing pattern recognition for customer: {customer_id}")
        
        # Get storage path
        storage_config = config.get("storage", {})
        base_path = Path(storage_config.get("path", f"customers/{customer_id}/patterns"))
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize pattern store
        store = PatternStore(storage_path=base_path)
        
        # Create initial configuration
        customer_config = {
            "customer_id": customer_id,
            "initialized_at": memory.get("timestamp", ""),
            "storage_path": str(base_path),
            "analysis_frequency": config.get("analysis_frequency", "weekly"),
            "insight_depth": config.get("insight_depth", "detailed"),
            "dimensions": {
                "work_rhythm": True,
                "decision_patterns": True,
                "help_seeking": True,
                "growth_trajectory": True
            }
        }
        
        # Save configuration
        config_path = base_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(customer_config, f, indent=2)
        
        # Initialize empty patterns
        store.save_patterns(customer_id, {
            "work_rhythm": {},
            "decision_patterns": {},
            "help_seeking": {},
            "growth_trajectory": {},
            "detected_at": memory.get("timestamp", "")
        })
        
        logger.info(f"Pattern recognition initialized successfully",
                   customer_id=customer_id,
                   storage_path=str(base_path))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "storage_path": str(base_path),
                "initialized": True
            },
            "message": f"Pattern recognition initialized for customer {customer_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize pattern recognition", error=str(e))
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
            "storage": {"path": "test_customers/OPC-TEST-001/patterns"},
            "analysis_frequency": "weekly",
            "insight_depth": "detailed"
        },
        "memory": {"timestamp": "2026-03-24T03:38:00Z"}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
