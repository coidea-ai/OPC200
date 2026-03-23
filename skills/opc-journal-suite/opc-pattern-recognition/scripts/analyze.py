"""opc-pattern-recognition analyze module.

This module analyzes journal patterns and generates insights.
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
from src.patterns.analyzer import (
    BehaviorAnalyzer,
    PatternStore,
    ProductivityAnalyzer,
    TrendAnalyzer
)
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Analyze patterns in journal entries.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Analysis parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-pattern-recognition.analyze")
    
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
        
        logger.info(f"Analyzing patterns for customer: {customer_id}")
        
        # Get storage paths
        journal_path = Path(
            config.get("journal_storage", {}).get("path", f"customers/{customer_id}/journal")
        )
        patterns_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/patterns")
        )
        
        db_path = journal_path / "journal.db"
        if not db_path.exists():
            return {
                "status": "error",
                "result": None,
                "message": "Journal not initialized. Please run journal init first."
            }
        
        # Initialize storage
        storage = SQLiteStorage(db_path=db_path)
        conn = storage.connection
        manager = JournalManager(conn)
        pattern_store = PatternStore(storage_path=patterns_path)
        
        # Get analysis parameters
        dimensions = input_data.get("dimensions", ["work_rhythm", "decision_patterns"])
        time_range = input_data.get("time_range", "last_30_days")
        
        # Get entries based on time range
        entries = manager.list_entries(limit=10000)
        
        if time_range == "last_7_days":
            cutoff = datetime.now() - timedelta(days=7)
            entries = [e for e in entries if e.created_at >= cutoff]
        elif time_range == "last_30_days":
            cutoff = datetime.now() - timedelta(days=30)
            entries = [e for e in entries if e.created_at >= cutoff]
        elif time_range == "last_90_days":
            cutoff = datetime.now() - timedelta(days=90)
            entries = [e for e in entries if e.created_at >= cutoff]
        
        if not entries:
            return {
                "status": "success",
                "result": {
                    "customer_id": customer_id,
                    "patterns": {},
                    "entry_count": 0,
                    "message": "No entries found for analysis"
                },
                "message": "No journal entries found for the specified time range"
            }
        
        # Prepare activities for analysis
        activities = []
        for entry in entries:
            activities.append({
                "timestamp": entry.created_at.isoformat(),
                "type": entry.metadata.get("topic_category", "general"),
                "energy_level": entry.metadata.get("energy_level", 5),
                "emotional_state": entry.metadata.get("emotional_state", "neutral"),
                "content_length": len(entry.content)
            })
        
        # Analyze patterns
        patterns = {}
        
        if "work_rhythm" in dimensions:
            analyzer = BehaviorAnalyzer()
            temporal_pattern = analyzer.detect_temporal_pattern(activities, "journal_entry")
            
            # Analyze peak productivity hours
            sessions = []
            for entry in entries:
                sessions.append({
                    "start": entry.created_at.isoformat(),
                    "output": len(entry.content)  # Use content length as proxy for output
                })
            
            prod_analyzer = ProductivityAnalyzer()
            peak_hours = prod_analyzer.find_peak_productivity_hours(sessions)
            
            patterns["work_rhythm"] = {
                "temporal_pattern": temporal_pattern,
                "peak_hours": peak_hours,
                "entry_count": len(entries)
            }
        
        if "decision_patterns" in dimensions:
            # Analyze decision-related entries
            decision_entries = [e for e in entries if "决策" in e.content or "决定" in e.content or "选择" in e.content]
            
            patterns["decision_patterns"] = {
                "total_decisions": len(decision_entries),
                "avg_decision_time": "N/A",  # Would need more detailed tracking
                "common_topics": extract_common_topics(decision_entries),
                "risk_appetite": analyze_risk_appetite(decision_entries)
            }
        
        if "growth_trajectory" in dimensions:
            # Analyze growth over time
            trend_analyzer = TrendAnalyzer()
            
            # Track energy levels over time
            energy_values = [a["energy_level"] for a in activities if "energy_level" in a]
            if len(energy_values) >= 2:
                energy_trend = trend_analyzer.detect_trend(energy_values)
            else:
                energy_trend = {"direction": "stable", "strength": 0}
            
            patterns["growth_trajectory"] = {
                "energy_trend": energy_trend,
                "entry_frequency": calculate_entry_frequency(entries),
                "content_depth_trend": analyze_content_depth(entries)
            }
        
        # Save patterns
        pattern_store.save_patterns(customer_id, patterns)
        
        logger.info(f"Pattern analysis completed",
                   customer_id=customer_id,
                   entry_count=len(entries),
                   dimensions=dimensions)
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "patterns": patterns,
                "entry_count": len(entries),
                "time_range": time_range,
                "analyzed_at": datetime.now().isoformat()
            },
            "message": f"Analyzed {len(entries)} entries across {len(dimensions)} dimensions"
        }
        
    except Exception as e:
        logger.error(f"Failed to analyze patterns", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Analysis failed: {str(e)}"
        }


def extract_common_topics(entries: list) -> list:
    """Extract common topics from entries."""
    from collections import Counter
    
    all_tags = []
    for entry in entries:
        all_tags.extend(entry.tags)
    
    counter = Counter(all_tags)
    return [tag for tag, count in counter.most_common(5)]


def analyze_risk_appetite(entries: list) -> str:
    """Analyze risk appetite based on entry content."""
    conservative_keywords = ["保守", "安全", "稳妥", "谨慎", "风险低"]
    aggressive_keywords = ["激进", "快速", "大胆", "冒险", "突破"]
    
    conservative_count = sum(1 for e in entries if any(kw in e.content for kw in conservative_keywords))
    aggressive_count = sum(1 for e in entries if any(kw in e.content for kw in aggressive_keywords))
    
    if conservative_count > aggressive_count:
        return "conservative"
    elif aggressive_count > conservative_count:
        return "aggressive"
    return "balanced"


def calculate_entry_frequency(entries: list) -> dict:
    """Calculate entry frequency statistics."""
    if not entries:
        return {"entries_per_day": 0}
    
    dates = set(e.created_at.date() for e in entries)
    days_span = (max(dates) - min(dates)).days + 1 if len(dates) > 1 else 1
    
    return {
        "entries_per_day": round(len(entries) / days_span, 2),
        "active_days": len(dates),
        "total_days": days_span
    }


def analyze_content_depth(entries: list) -> dict:
    """Analyze content depth trends."""
    if not entries:
        return {"trend": "stable"}
    
    # Sort by date
    sorted_entries = sorted(entries, key=lambda e: e.created_at)
    
    # Calculate average content length
    lengths = [len(e.content) for e in sorted_entries]
    
    if len(lengths) >= 2:
        first_half = sum(lengths[:len(lengths)//2]) / max(1, len(lengths)//2)
        second_half = sum(lengths[len(lengths)//2:]) / max(1, len(lengths) - len(lengths)//2)
        
        if second_half > first_half * 1.2:
            trend = "increasing"
        elif second_half < first_half * 0.8:
            trend = "decreasing"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "avg_length_first_half": round(first_half, 1),
            "avg_length_second_half": round(second_half, 1)
        }
    
    return {"trend": "stable", "avg_length": sum(lengths) / len(lengths)}


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "dimensions": ["work_rhythm", "decision_patterns", "growth_trajectory"],
            "time_range": "last_30_days"
        },
        "config": {
            "journal_storage": {"path": "test_customers/OPC-TEST-001/journal"},
            "storage": {"path": "test_customers/OPC-TEST-001/patterns"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
