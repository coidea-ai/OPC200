"""opc-insights-generator daily_summary module.

This module generates daily summary insights.
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
from typing import Any

from src.journal.core import JournalManager
from src.journal.storage import SQLiteStorage
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Generate daily summary.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Generation parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-insights-generator.daily_summary")
    
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
        
        # Get date (default to today)
        date_str = input_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        logger.info(f"Generating daily summary for customer: {customer_id}", date=date_str)
        
        # Get storage paths
        journal_path = Path(
            config.get("journal_storage", {}).get("path", f"customers/{customer_id}/journal")
        )
        insights_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/insights")
        )
        
        # Load journal entries
        db_path = journal_path / "journal.db"
        entries = []
        if db_path.exists():
            storage = SQLiteStorage(db_path=db_path)
            conn = storage.connection
            manager = JournalManager(conn)
            all_entries = manager.list_entries(limit=10000)
            
            # Filter entries for target date
            start_of_day = target_date.replace(hour=0, minute=0, second=0)
            end_of_day = target_date.replace(hour=23, minute=59, second=59)
            entries = [
                e for e in all_entries
                if start_of_day <= e.created_at <= end_of_day
            ]
        
        # Generate summary
        summary = generate_summary(entries, target_date)
        
        # Save summary
        summary_file = insights_path / "daily" / f"{date_str}.json"
        summary_file.parent.mkdir(exist_ok=True)
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Daily summary generated",
                   customer_id=customer_id,
                   date=date_str,
                   entry_count=len(entries))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "date": date_str,
                "summary": summary,
                "entry_count": len(entries),
                "generated_at": datetime.now().isoformat()
            },
            "message": f"Daily summary generated for {date_str}"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate daily summary", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Generation failed: {str(e)}"
        }


def generate_summary(entries: list, target_date: datetime) -> dict:
    """Generate summary from entries."""
    from collections import Counter
    
    summary = {
        "date": target_date.strftime("%Y-%m-%d"),
        "total_entries": len(entries),
        "periods": {
            "morning": 0,   # 06-12
            "afternoon": 0, # 12-18
            "evening": 0,   # 18-22
            "night": 0      # 22-06
        },
        "tags": [],
        "agents_involved": [],
        "tasks_completed": [],
        "emotional_summary": {
            "dominant": "neutral",
            "variations": []
        },
        "energy_average": 0,
        "key_topics": [],
        "highlights": []
    }
    
    if not entries:
        summary["highlights"].append("今天没有记录")
        return summary
    
    # Analyze time periods
    for entry in entries:
        hour = entry.created_at.hour
        if 6 <= hour < 12:
            summary["periods"]["morning"] += 1
        elif 12 <= hour < 18:
            summary["periods"]["afternoon"] += 1
        elif 18 <= hour < 22:
            summary["periods"]["evening"] += 1
        else:
            summary["periods"]["night"] += 1
    
    # Collect tags
    all_tags = []
    for entry in entries:
        all_tags.extend(entry.tags)
    tag_counter = Counter(all_tags)
    summary["tags"] = [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(10)]
    
    # Collect agents and tasks
    all_agents = set()
    all_tasks = []
    energy_values = []
    emotional_states = []
    
    for entry in entries:
        agents = entry.metadata.get("agents_involved", [])
        all_agents.update(agents)
        
        tasks = entry.metadata.get("tasks_completed", [])
        all_tasks.extend(tasks)
        
        energy = entry.metadata.get("energy_level")
        if energy:
            energy_values.append(energy)
        
        emotion = entry.metadata.get("emotional_state")
        if emotion:
            emotional_states.append(emotion)
    
    summary["agents_involved"] = list(all_agents)
    summary["tasks_completed"] = all_tasks
    
    if energy_values:
        summary["energy_average"] = round(sum(energy_values) / len(energy_values), 1)
    
    if emotional_states:
        emotion_counter = Counter(emotional_states)
        summary["emotional_summary"]["dominant"] = emotion_counter.most_common(1)[0][0]
        summary["emotional_summary"]["variations"] = list(set(emotional_states))
    
    # Generate highlights
    if summary["tasks_completed"]:
        summary["highlights"].append(f"完成 {len(summary['tasks_completed'])} 个任务")
    
    if summary["periods"]["morning"] > 0:
        summary["highlights"].append(f"上午记录了 {summary['periods']['morning']} 条")
    if summary["periods"]["afternoon"] > 0:
        summary["highlights"].append(f"下午记录了 {summary['periods']['afternoon']} 条")
    
    peak_period = max(summary["periods"], key=summary["periods"].get)
    if summary["periods"][peak_period] > 0:
        summary["highlights"].append(f"活跃时段: {translate_period(peak_period)}")
    
    return summary


def translate_period(period: str) -> str:
    """Translate period name to Chinese."""
    translations = {
        "morning": "上午",
        "afternoon": "下午",
        "evening": "晚上",
        "night": "深夜"
    }
    return translations.get(period, period)


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "date": "2026-03-24"
        },
        "config": {
            "journal_storage": {"path": "test_customers/OPC-TEST-001/journal"},
            "storage": {"path": "test_customers/OPC-TEST-001/insights"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
