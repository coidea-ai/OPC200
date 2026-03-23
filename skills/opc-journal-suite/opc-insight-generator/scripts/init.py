"""opc-insights-generator initialization module.

This module handles the initialization of the insights generator skill.
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
    """Initialize the opc-insights-generator skill.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Initialization parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-insights-generator.init")
    
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
        
        logger.info(f"Initializing insights generator for customer: {customer_id}")
        
        # Get storage path
        storage_config = config.get("storage", {})
        base_path = Path(storage_config.get("path", f"customers/{customer_id}/insights"))
        base_path.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (base_path / "daily").mkdir(exist_ok=True)
        (base_path / "weekly").mkdir(exist_ok=True)
        (base_path / "recommendations").mkdir(exist_ok=True)
        
        # Create initial configuration
        customer_config = {
            "customer_id": customer_id,
            "initialized_at": memory.get("timestamp", ""),
            "storage_path": str(base_path),
            "generation_frequency": config.get("generation_frequency", "daily"),
            "include_recommendations": config.get("include_recommendations", True),
            "personalization_enabled": config.get("personalization_enabled", True)
        }
        
        # Save configuration
        config_path = base_path / "config.json"
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(customer_config, f, indent=2)
        
        logger.info(f"Insights generator initialized successfully",
                   customer_id=customer_id,
                   storage_path=str(base_path))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "storage_path": str(base_path),
                "initialized": True
            },
            "message": f"Insights generator initialized for customer {customer_id}"
        }
        
    except Exception as e:
        logger.error(f"Failed to initialize insights generator", error=str(e))
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
            "storage": {"path": "test_customers/OPC-TEST-001/insights"},
            "generation_frequency": "daily",
            "include_recommendations": True
        },
        "memory": {"timestamp": "2026-03-24T03:38:00Z"}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
