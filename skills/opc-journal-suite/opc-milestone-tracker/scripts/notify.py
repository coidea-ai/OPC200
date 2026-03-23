"""opc-milestone-tracker notify module.

This module handles milestone notifications and celebrations.
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

from src.utils.logging import get_logger


def generate_milestone_report(milestone: dict, customer_id: str, previous_milestones: list) -> str:
    """Generate a formatted milestone celebration report."""
    lines = []
    
    # Header
    lines.append("🎉 恭喜！您达成了新里程碑！")
    lines.append("")
    
    # Milestone box
    lines.append("┌" + "─" * 57 + "┐")
    
    milestone_name = get_milestone_display_name(milestone["type"])
    lines.append(f"│  {milestone_name:<55}│")
    
    lines.append("├" + "─" * 57 + "┤")
    lines.append("│                                                         │")
    
    # Date and day
    date_str = milestone.get("date", datetime.now().isoformat())[:10]
    day_num = milestone.get("day_number", "N/A")
    lines.append(f"│  达成时间: {date_str} (Day {day_num:>3})                           │")
    
    # Stage
    stage = calculate_stage(day_num if isinstance(day_num, int) else 0)
    lines.append(f"│  旅程阶段: {stage:<48}│")
    
    lines.append("│                                                         │")
    
    # Previous milestones
    if previous_milestones:
        lines.append("│  🔄 里程碑历程                                          │")
        recent = sorted(previous_milestones, key=lambda x: x.get("date", ""))[-3:]
        for prev in recent:
            prev_name = get_milestone_display_name(prev.get("type", ""))
            prev_day = prev.get("day_number", "?")
            lines.append(f"│     Day {prev_day:>3}: {prev_name:<42}│")
        lines.append("│                                                         │")
    
    # Celebration
    lines.append("│  💪 继续前进！                                          │")
    lines.append("│                                                         │")
    lines.append("└" + "─" * 57 + "┘")
    
    return "\n".join(lines)


def get_milestone_display_name(milestone_type: str) -> str:
    """Get display name for milestone type."""
    names = {
        "first_deployment": "首次产品发布",
        "first_sale": "首笔销售",
        "mvp_complete": "MVP 完成",
        "first_contribution": "首次开源贡献",
        "multi_agent_workflow": "多 Agent 协作",
        "first_agent_delegation": "首次 Agent 委托",
        "hundred_days": "百日坚持",
        "technical_breakthrough": "技术突破"
    }
    return names.get(milestone_type, milestone_type.replace("_", " ").title())


def calculate_stage(day_number: int) -> str:
    """Calculate journey stage based on day number."""
    if day_number <= 7:
        return "启动期"
    elif day_number <= 30:
        return "探索期"
    elif day_number <= 60:
        return "建立期"
    elif day_number <= 100:
        return "加速期"
    else:
        return "成熟期"


def main(context: dict) -> dict:
    """Send milestone notifications.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Notification parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-milestone-tracker.notify")
    
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
        
        logger.info(f"Sending milestone notification for customer: {customer_id}")
        
        # Get milestone data
        milestone = input_data.get("milestone", {})
        if not milestone:
            return {
                "status": "error",
                "result": None,
                "message": "milestone data is required"
            }
        
        # Get storage path
        milestones_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/milestones")
        )
        
        # Load existing milestones
        milestones_file = milestones_path / "milestones.json"
        previous_milestones = []
        if milestones_file.exists():
            with open(milestones_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                previous_milestones = [m for m in data.get("milestones", []) if m.get("status") == "achieved"]
        
        # Generate celebration message
        celebration_message = milestone.get("celebration", "🎉 恭喜达成新里程碑！")
        detailed_report = generate_milestone_report(milestone, customer_id, previous_milestones)
        
        # Determine notification channels
        channels = input_data.get("channels", ["journal"])
        if config.get("celebration_enabled", True):
            channels = config.get("notification_channels", ["journal"])
        
        # Prepare notification payload
        notification = {
            "customer_id": customer_id,
            "milestone": milestone,
            "celebration_message": celebration_message,
            "detailed_report": detailed_report,
            "channels": channels,
            "notified_at": datetime.now().isoformat()
        }
        
        # Save milestone as achieved
        milestone["status"] = "achieved"
        milestone["notified_at"] = datetime.now().isoformat()
        
        # Update milestones data
        if milestones_file.exists():
            with open(milestones_file, "r", encoding="utf-8") as f:
                milestones_data = json.load(f)
        else:
            milestones_data = {"customer_id": customer_id, "milestones": [], "stats": {"total_achieved": 0, "by_category": {}}}
        
        # Add new milestone
        milestones_data["milestones"].append(milestone)
        
        # Update stats
        milestones_data["stats"]["total_achieved"] = len(
            [m for m in milestones_data["milestones"] if m.get("status") == "achieved"]
        )
        
        # Update category stats
        category = milestone.get("category", "other")
        if "by_category" not in milestones_data["stats"]:
            milestones_data["stats"]["by_category"] = {}
        if category not in milestones_data["stats"]["by_category"]:
            milestones_data["stats"]["by_category"][category] = 0
        milestones_data["stats"]["by_category"][category] += 1
        
        # Save updated data
        with open(milestones_file, "w", encoding="utf-8") as f:
            json.dump(milestones_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Milestone notification sent",
                   customer_id=customer_id,
                   milestone_type=milestone.get("type"),
                   channels=channels)
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "notification": notification,
                "milestone_saved": True,
                "total_milestones": milestones_data["stats"]["total_achieved"]
            },
            "message": f"Milestone notification sent: {milestone.get('type')}"
        }
        
    except Exception as e:
        logger.error(f"Failed to send milestone notification", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Notification failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "milestone": {
                "type": "first_deployment",
                "category": "technical",
                "date": "2026-03-24T10:00:00",
                "day_number": 45,
                "celebration": "🚀 里程碑: 首次部署！"
            },
            "channels": ["journal", "feishu"]
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/milestones"},
            "celebration_enabled": True,
            "notification_channels": ["journal", "feishu"]
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n" + "=" * 60)
    print("Celebration Report:")
    print(result["result"]["notification"]["detailed_report"])
