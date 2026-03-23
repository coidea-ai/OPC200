"""opc-insight-generator recommendations module.

This module generates personalized recommendations.
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
from typing import Any

from src.insights.generator import RecommendationEngine
from src.patterns.analyzer import PatternStore
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Generate personalized recommendations.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Recommendation parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-insight-generator.recommendations")
    
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
        
        logger.info(f"Generating recommendations for customer: {customer_id}")
        
        # Get storage paths
        insights_path = Path(
            config.get("storage", {}).get("path", f"customers/{customer_id}/insights")
        )
        patterns_path = Path(
            config.get("patterns_storage", {}).get("path", f"customers/{customer_id}/patterns")
        )
        
        # Get recommendation type
        rec_type = input_data.get("type", "all")  # productivity, work_life, growth, all
        
        # Initialize recommendation engine
        engine = RecommendationEngine()
        recommendations = []
        
        # Load patterns if available
        patterns = {}
        try:
            store = PatternStore(storage_path=patterns_path)
            patterns = store.load_patterns(customer_id)
        except Exception:
            pass  # Patterns might not exist yet
        
        # Generate productivity recommendations
        if rec_type in ["all", "productivity"]:
            productivity_data = input_data.get("productivity_data", {})
            
            # Use patterns data if available
            if patterns and "work_rhythm" in patterns:
                work_rhythm = patterns["work_rhythm"]
                if "peak_hours" in work_rhythm:
                    peak_hours = list(work_rhythm["peak_hours"].keys())
                    productivity_data["peak_hours"] = peak_hours
            
            productivity_recs = engine.generate_productivity_recommendations(productivity_data)
            for rec in productivity_recs:
                recommendations.append({
                    "type": "productivity",
                    "content": rec,
                    "priority": "medium",
                    "effort": "low"
                })
        
        # Generate work-life balance recommendations
        if rec_type in ["all", "work_life"]:
            work_patterns = input_data.get("work_patterns", {})
            
            # Default patterns if not provided
            if not work_patterns and patterns:
                work_patterns = {
                    "avg_daily_hours": 8,
                    "weekend_work_frequency": 0.2,
                    "break_frequency": "normal"
                }
            
            balance_recs = engine.generate_work_life_balance_recommendations(work_patterns)
            for rec in balance_recs:
                recommendations.append({
                    "type": "work_life",
                    "content": rec,
                    "priority": "high" if "boundary" in rec.lower() else "medium",
                    "effort": "medium"
                })
        
        # Generate skill development recommendations
        if rec_type in ["all", "growth"]:
            skill_data = input_data.get("skill_data", {})
            skill_recs = engine.generate_skill_development_recommendations(skill_data)
            for rec in skill_recs:
                recommendations.append({
                    "type": "growth",
                    "content": rec,
                    "priority": "medium",
                    "effort": "high"
                })
        
        # Prioritize recommendations
        prioritized = engine.prioritize(recommendations)
        
        # Calculate quality scores
        for rec in prioritized:
            rec["quality_score"] = calculate_quality_score(rec)
        
        # Filter by minimum quality score
        min_quality = config.get("proactive", {}).get("min_quality_score", 0.75)
        filtered_recs = [r for r in prioritized if r.get("quality_score", 0) >= min_quality]
        
        # Limit number of recommendations
        max_recs = config.get("proactive", {}).get("max_per_day", 3)
        final_recs = filtered_recs[:max_recs]
        
        # Save recommendations
        rec_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        rec_file = insights_path / "recommendations" / f"rec_{rec_id}.json"
        rec_file.parent.mkdir(parents=True, exist_ok=True)
        
        rec_data = {
            "id": rec_id,
            "customer_id": customer_id,
            "generated_at": datetime.now().isoformat(),
            "type": rec_type,
            "recommendations": final_recs,
            "total_considered": len(recommendations),
            "quality_threshold": min_quality
        }
        
        with open(rec_file, "w", encoding="utf-8") as f:
            json.dump(rec_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Recommendations generated",
                   customer_id=customer_id,
                   count=len(final_recs),
                   total_considered=len(recommendations))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "recommendations": final_recs,
                "total_considered": len(recommendations),
                "type": rec_type,
                "generated_at": datetime.now().isoformat()
            },
            "message": f"Generated {len(final_recs)} recommendations ({len(recommendations)} considered)"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate recommendations", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Recommendation generation failed: {str(e)}"
        }


def calculate_quality_score(recommendation: dict) -> float:
    """Calculate quality score for a recommendation."""
    score = 0.0
    
    # Base score
    score += 0.5
    
    # Priority bonus
    priority_scores = {"high": 0.2, "medium": 0.1, "low": 0.0}
    score += priority_scores.get(recommendation.get("priority", "medium"), 0)
    
    # Effort bonus (lower effort = higher score)
    effort_scores = {"low": 0.2, "medium": 0.1, "high": 0.0}
    score += effort_scores.get(recommendation.get("effort", "medium"), 0)
    
    # Content length bonus (more detailed = better)
    content = recommendation.get("content", "")
    if len(content) > 50:
        score += 0.1
    
    return min(1.0, score)


if __name__ == "__main__":
    # Test entry point
    import sys
    sys.path.insert(0, '.')
    
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "type": "all",
            "productivity_data": {
                "peak_hours": [9, 14, 20],
                "avg_focus_session": 25,
                "interruption_frequency": "medium"
            },
            "work_patterns": {
                "avg_daily_hours": 9,
                "weekend_work_frequency": 0.3,
                "break_frequency": "low"
            },
            "skill_data": {
                "skill_gaps": ["marketing", "sales"],
                "current_skills": ["programming", "product_design"]
            }
        },
        "config": {
            "storage": {"path": "test_customers/OPC-TEST-001/insights"},
            "patterns_storage": {"path": "test_customers/OPC-TEST-001/patterns"},
            "proactive": {
                "max_per_day": 3,
                "min_quality_score": 0.75
            }
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
