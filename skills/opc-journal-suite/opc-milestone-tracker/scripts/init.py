"""opc-milestone-tracker initialization module.

This module handles the initialization of the milestone tracker skill.
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
    """Initialize the opc-milestone-tracker skill.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Initialization parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-milestone-tracker.init")
    
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
        
        logger.info(f"Initializing milestone tracker for customer: {customer_id}")
        
        # Get storage path
        storage_config = config.get("storage", {})
        base_path = Path(storage_config.get("path", f"customers/{customer_id}/milestones"))
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (base_path / "achieved").mkdir(exist_ok=True)
        (base_path / "pending").mkdir(exist_ok=True)
        (base_path / "predicted").mkdir(exist_ok=True)
        
        # Create initial configuration
        customer_config = {
            "customer_id": customer_id,
            "initialized_at": memory.get("timestamp", ""),
            "storage_path": str(base_path),
            "auto_detection": config.get("auto_detection", True),
            "celebration_enabled": config.get("celebration_enabled", True),
            "milestone_types": {
                "technical": ["first_deployment", "first_contribution", "technical_breakthrough"],
                "business": ["first_sale", "revenue_targets", "customer_targets", "product_milestones"],
                "growth": ["ai_collaboration", "personal_development", "community"]
            }
        }
        
        # Save configuration
        config_path = base_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(customer_config, f, indent=2)
        
        # Initialize milestones tracking
        milestones_data = {
            "customer_id": customer_id,
            "milestones": [],
            "stats": {
                "total_achieved": 0,
                "total_pending": 0,
                "by_category": {}
            }
        }
        
        milestones_path = base_path / "milestones.json"
        with open(milestones_path, "w", encoding="utf-8") as f:
            json.dump(milestones_data, f, indent=2)
        
        logger.info(f"Milestone tracker initialized successfully",
                   customer_id=customer_id,
                   storage_path=str(base_path))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "storage_path": str(base_path),
                "initialized": True
            },
            "message": f"Milestone tracker initialized for customer {customer_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize milestone tracker", error=str(e))
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
            "storage": {"path": "test_customers/OPC-TEST-001/milestones"},
            "auto_detection": True,
            "celebration_enabled": True
        },
        "memory": {"timestamp": "2026-03-24T03:38:00Z"}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
