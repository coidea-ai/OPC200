"""opc-insight-generator weekly_review module.

This module generates weekly review insights.
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

from src.insights.generator import InsightGenerator
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Generate weekly review insight.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Review parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-insight-generator.weekly_review")
    
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
        
        logger.info(f"Generating weekly review for customer: {customer_id}")
        
        # Get storage path
        insights_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/insights")
        )
        
        # Get week start date
        week_start_str = input_data.get("week_start")
        if week_start_str:
            week_start = datetime.fromisoformat(week_start_str)
        else:
            # Default to start of current week (Monday)
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Load daily summaries for the week
        daily_summaries = []
        daily_path = insights_path / "daily"
        
        for i in range(7):
            day = week_start + timedelta(days=i)
            day_str = day.strftime("%Y-%m-%d")
            summary_file = daily_path / f"summary_{day_str}.json"
            
            if summary_file.exists():
                with open(summary_file, "r", encoding="utf-8") as f:
                    daily_summaries.append(json.load(f))
            else:
                # Create empty summary for missing days
                daily_summaries.append({
                    "date": day_str,
                    "tasks_completed": 0,
                    "meetings": 0,
                    "total_activities": 0,
                    "focus_hours": 0
                })
        
        # Generate weekly review
        generator = InsightGenerator()
        review = generator.generate_weekly_review({
            "daily_summaries": daily_summaries,
            "week_start": week_start
        })
        
        # Enrich with additional analysis
        enriched_review = enrich_weekly_review(review, daily_summaries, week_start)
        
        # Save review
        week_str = week_start.strftime("%Y-W%W")
        review_file = insights_path / "weekly" / f"review_{week_str}.json"
        review_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(review_file, "w", encoding="utf-8") as f:
            json.dump(enriched_review, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Weekly review generated",
                   customer_id=customer_id,
                   week=week_str,
                   day_count=len(daily_summaries))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "review": enriched_review,
                "week": week_str,
                "week_start": week_start.strftime("%Y-%m-%d"),
                "daily_summaries_used": len([d for d in daily_summaries if d.get("total_activities", 0) > 0]),
                "generated_at": datetime.now().isoformat()
            },
            "message": f"Weekly review generated for {week_str}"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate weekly review", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Weekly review generation failed: {str(e)}"
        }


def enrich_weekly_review(review: dict, daily_summaries: list, week_start: datetime) -> dict:
    """Enrich weekly review with additional analysis."""
    enriched = review.copy()
    
    # Calculate day-by-day breakdown
    day_breakdown = []
    for i, summary in enumerate(daily_summaries):
        day = week_start + timedelta(days=i)
        day_breakdown.append({
            "day": day.strftime("%A"),
            "date": summary.get("date", day.strftime("%Y-%m-%d")),
            "tasks": summary.get("tasks_completed", 0),
            "activities": summary.get("total_activities", 0),
            "energy": summary.get("energy_metrics", {}).get("average")
        })
    enriched["day_breakdown"] = day_breakdown
    
    # Find best and worst days
    days_with_activity = [d for d in day_breakdown if d["activities"] > 0]
    if days_with_activity:
        best_day = max(days_with_activity, key=lambda x: x["tasks"])
        worst_day = min(days_with_activity, key=lambda x: x["tasks"])
        enriched["best_day"] = best_day
        enriched["worst_day"] = worst_day
    
    # Calculate work-life balance
    weekday_activity = sum(d["activities"] for d in day_breakdown[:5])
    weekend_activity = sum(d["activities"] for d in day_breakdown[5:])
    
    if weekend_activity > weekday_activity / 5:
        enriched["work_life_note"] = "Weekend activity detected. Consider taking more rest time."
    else:
        enriched["work_life_note"] = "Good work-life balance this week."
    
    # Identify patterns
    energy_trend = []
    for summary in daily_summaries:
        if "energy_metrics" in summary:
            energy_trend.append(summary["energy_metrics"]["average"])
    
    if len(energy_trend) >= 3:
        if energy_trend[-1] > energy_trend[0]:
            enriched["energy_trend"] = "improving"
        elif energy_trend[-1] < energy_trend[0]:
            enriched["energy_trend"] = "declining"
        else:
            enriched["energy_trend"] = "stable"
    
    # Generate highlights
    highlights = []
    total_tasks = sum(d.get("tasks_completed", 0) for d in daily_summaries)
    if total_tasks >= 10:
        highlights.append(f"Completed {total_tasks} tasks this week")
    
    active_days = len([d for d in daily_summaries if d.get("total_activities", 0) > 0])
    if active_days >= 5:
        highlights.append("Consistent activity throughout the week")
    
    enriched["highlights"] = highlights
    
    return enriched


if __name__ == "__main__":
    # Test entry point
    import sys
    sys.path.insert(0, '.')
    
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "week_start": "2026-03-17"
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/insights"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
