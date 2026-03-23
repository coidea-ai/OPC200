"""opc-milestone-tracker detect module.

This module detects milestone events from journal entries.
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
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.journal.core import JournalManager
from src.journal.storage import SQLiteStorage
from src.utils.logging import get_logger


# Milestone detection patterns
MILESTONE_PATTERNS = {
    "first_deployment": {
        "category": "technical",
        "keywords": ["部署", "上线", "发布", "production", "go live", "launched"],
        "evidence_requirements": ["url_accessible"],
        "celebration": "🚀 里程碑: 首次部署！"
    },
    "first_sale": {
        "category": "business",
        "keywords": ["收款", "订单", "销售", "付费", "成交", "sold", "payment received"],
        "evidence_requirements": [],
        "celebration": "💰 里程碑: 首笔销售！商业模式验证成功！"
    },
    "mvp_complete": {
        "category": "business",
        "keywords": ["MVP完成", "MVP done", "最小可用产品", "prototype complete"],
        "evidence_requirements": [],
        "celebration": "✅ 里程碑: MVP 完成！"
    },
    "first_contribution": {
        "category": "technical",
        "keywords": ["PR合并", "开源贡献", "contribution merged", "open source"],
        "evidence_requirements": [],
        "celebration": "🌟 里程碑: 成为开源贡献者！"
    },
    "multi_agent_workflow": {
        "category": "growth",
        "keywords": ["多Agent协作", "multi-agent", "agent协作", "协作完成"],
        "evidence_requirements": ["multiple_agents"],
        "celebration": "🎭 里程碑: 首次多 Agent 协作完成任务！"
    },
    "first_agent_delegation": {
        "category": "growth",
        "keywords": ["委托Agent", "delegate", "让Agent", "交给Agent"],
        "evidence_requirements": [],
        "celebration": "🤖 里程碑: 首次 Agent 委托！"
    },
    "hundred_days": {
        "category": "growth",
        "keywords": ["100天", "百日", "100 days", "hundred days"],
        "evidence_requirements": [],
        "celebration": "🏆 里程碑: 百日坚持！"
    }
}


def main(context: dict) -> dict:
    """Detect milestone events from journal entries.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Detection parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-milestone-tracker.detect")
    
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
        
        logger.info(f"Detecting milestones for customer: {customer_id}")
        
        # Get storage paths
        journal_path = Path(
            config.get("journal_storage", {}).get("path", f"customers/{customer_id}/journal")
        )
        milestones_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/milestones")
        )
        
        # Load existing milestones
        milestones_file = milestones_path / "milestones.json"
        if milestones_file.exists():
            with open(milestones_file, "r", encoding="utf-8") as f:
                milestones_data = json.load(f)
        else:
            milestones_data = {"customer_id": customer_id, "milestones": [], "stats": {}}
        
        # Get already achieved milestones
        achieved_types = {m["type"] for m in milestones_data.get("milestones", []) if m.get("status") == "achieved"}
        
        # Load journal entries
        db_path = journal_path / "journal.db"
        entries = []
        if db_path.exists():
            storage = SQLiteStorage(db_path=db_path)
            conn = storage.connection
            manager = JournalManager(conn)
            entries = manager.list_entries(limit=10000)
        
        # Also check input for direct milestone detection
        content = input_data.get("content", "")
        agents_involved = input_data.get("agents_involved", [])
        
        detected_milestones = []
        
        # Detect from journal entries
        if entries:
            for entry in entries:
                entry_agents = entry.metadata.get("agents_involved", [])
                for milestone_type, pattern in MILESTONE_PATTERNS.items():
                    # Skip already achieved milestones
                    if milestone_type in achieved_types:
                        continue
                    
                    # Check keywords
                    if any(kw in entry.content for kw in pattern["keywords"]):
                        # Check additional requirements
                        meets_requirements = True
                        for req in pattern["evidence_requirements"]:
                            if req == "multiple_agents" and len(entry_agents) < 2:
                                meets_requirements = False
                                break
                        
                        if meets_requirements:
                            milestone = {
                                "type": milestone_type,
                                "category": pattern["category"],
                                "detected_from": "journal_entry",
                                "entry_id": entry.id,
                                "date": entry.created_at.isoformat(),
                                "confidence": calculate_confidence(entry.content, pattern["keywords"]),
                                "celebration": pattern["celebration"],
                                "status": "detected"
                            }
                            if not any(m["type"] == milestone_type for m in detected_milestones):
                                detected_milestones.append(milestone)
        
        # Detect from input content
        if content:
            for milestone_type, pattern in MILESTONE_PATTERNS.items():
                if milestone_type in achieved_types:
                    continue
                
                if any(kw in content for kw in pattern["keywords"]):
                    meets_requirements = True
                    for req in pattern["evidence_requirements"]:
                        if req == "multiple_agents" and len(agents_involved) < 2:
                            meets_requirements = False
                            break
                    
                    if meets_requirements:
                        milestone = {
                            "type": milestone_type,
                            "category": pattern["category"],
                            "detected_from": "input",
                            "content_preview": content[:100],
                            "date": datetime.now().isoformat(),
                            "confidence": calculate_confidence(content, pattern["keywords"]),
                            "celebration": pattern["celebration"],
                            "status": "detected"
                        }
                        if not any(m["type"] == milestone_type for m in detected_milestones):
                            detected_milestones.append(milestone)
        
        # Calculate day number if available
        day_number = input_data.get("day_number") or memory_day_number(context.get("memory", {}))
        
        # Add day context to detected milestones
        for milestone in detected_milestones:
            if day_number:
                milestone["day_number"] = day_number
        
        logger.info(f"Milestone detection completed",
                   customer_id=customer_id,
                   detected_count=len(detected_milestones))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "detected_milestones": detected_milestones,
                "already_achieved": list(achieved_types),
                "day_number": day_number,
                "detected_at": datetime.now().isoformat()
            },
            "message": f"Detected {len(detected_milestones)} potential milestones"
        }
        
    except Exception as e:
        logger.error(f"Failed to detect milestones", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Detection failed: {str(e)}"
        }


def calculate_confidence(content: str, keywords: list) -> float:
    """Calculate confidence score based on keyword matches."""
    content_lower = content.lower()
    matches = sum(1 for kw in keywords if kw.lower() in content_lower)
    return min(1.0, matches / max(1, len(keywords) * 0.5))


def memory_day_number(memory: dict) -> Optional[int]:
    """Extract day number from memory context."""
    # Try to find day number in memory
    day = memory.get("day")
    if day and isinstance(day, int):
        return day
    
    # Try to parse from session info
    session_info = memory.get("session_info", {})
    if isinstance(session_info, dict):
        day = session_info.get("day")
        if day and isinstance(day, int):
            return day
    
    return None


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "content": "终于把产品部署到生产环境了！上线成功！",
            "agents_involved": ["DevAgent", "DeployAgent"],
            "day_number": 45
        },
        "config": {
            "journal_storage": {"path": "test_customers/OPC-TEST-001/journal"},
            "storage": {"path": "test_customers/OPC-TEST-001/milestones"}
        },
        "memory": {"day": 45}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
