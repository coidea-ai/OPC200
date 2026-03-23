"""opc-pattern-recognition detect_outliers module.

This module detects anomalies and outliers in journal patterns.
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
from src.patterns.analyzer import AnomalyDetector, PatternStore
from src.utils.logging import get_logger


def main(context: dict) -> dict:
    """Detect outliers and anomalies in journal patterns.
    
    Args:
        context: Dictionary containing:
            - customer_id: The customer identifier
            - input: Detection parameters
            - config: Skill configuration
            - memory: Memory context
    
    Returns:
        Dictionary with status, result, and message
    """
    logger = get_logger("opc-pattern-recognition.detect_outliers")
    
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
        
        logger.info(f"Detecting outliers for customer: {customer_id}")
        
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
                "message": "Journal not initialized"
            }
        
        # Initialize storage
        storage = SQLiteStorage(db_path=db_path)
        conn = storage.connection
        manager = JournalManager(conn)
        pattern_store = PatternStore(storage_path=patterns_path)
        
        # Get detection parameters
        time_range = input_data.get("time_range", "last_30_days")
        threshold = input_data.get("threshold", 2.0)
        detection_types = input_data.get("types", ["energy_outliers", "frequency_outliers", "content_anomalies"])
        
        # Get entries
        entries = manager.list_entries(limit=10000)
        
        if time_range == "last_7_days":
            cutoff = datetime.now() - timedelta(days=7)
            entries = [e for e in entries if e.created_at >= cutoff]
        elif time_range == "last_30_days":
            cutoff = datetime.now() - timedelta(days=30)
            entries = [e for e in entries if e.created_at >= cutoff]
        
        if len(entries) < 3:
            return {
                "status": "success",
                "result": {
                    "customer_id": customer_id,
                    "outliers": [],
                    "message": "Insufficient data for outlier detection (minimum 3 entries)"
                },
                "message": "Need at least 3 entries to detect outliers"
            }
        
        # Initialize detector
        detector = AnomalyDetector()
        outliers = []
        
        # Detect energy level outliers
        if "energy_outliers" in detection_types:
            energy_values = []
            energy_entries = []
            for entry in entries:
                energy = entry.metadata.get("energy_level")
                if energy is not None:
                    energy_values.append(float(energy))
                    energy_entries.append(entry)
            
            if len(energy_values) >= 3:
                energy_outliers = detector.detect_outliers(energy_values, threshold=threshold)
                for outlier in energy_outliers:
                    idx = outlier["index"]
                    entry = energy_entries[idx]
                    outliers.append({
                        "type": "energy_outlier",
                        "entry_id": entry.id,
                        "date": entry.created_at.isoformat(),
                        "value": outlier["value"],
                        "z_score": round(outlier["z_score"], 2),
                        "mean": round(outlier["mean"], 2),
                        "description": f"Energy level {outlier['value']} deviates significantly from average {round(outlier['mean'], 1)}"
                    })
        
        # Detect frequency outliers (unusual gaps in entries)
        if "frequency_outliers" in detection_types and len(entries) >= 3:
            # Sort entries by date
            sorted_entries = sorted(entries, key=lambda e: e.created_at)
            
            # Calculate gaps between entries
            gaps = []
            for i in range(1, len(sorted_entries)):
                gap = (sorted_entries[i].created_at - sorted_entries[i-1].created_at).days
                gaps.append(gap)
            
            if len(gaps) >= 3:
                gap_outliers = detector.detect_outliers(gaps, threshold=threshold)
                for outlier in gap_outliers:
                    idx = outlier["index"]
                    entry = sorted_entries[idx + 1]  # +1 because gaps are between entries
                    outliers.append({
                        "type": "frequency_outlier",
                        "entry_id": entry.id,
                        "date": entry.created_at.isoformat(),
                        "gap_days": outlier["value"],
                        "z_score": round(outlier["z_score"], 2),
                        "description": f"Unusual {outlier['value']}-day gap since last entry"
                    })
        
        # Detect pattern breaks (unusual hour patterns)
        if "pattern_breaks" in detection_types:
            activities = []
            for entry in entries:
                activities.append({
                    "timestamp": entry.created_at.isoformat(),
                    "type": entry.metadata.get("topic_category", "general")
                })
            
            breaks = detector.detect_pattern_breaks(activities)
            for break_item in breaks:
                idx = break_item["index"]
                if idx < len(entries):
                    entry = entries[idx]
                    outliers.append({
                        "type": "pattern_break",
                        "entry_id": entry.id,
                        "date": entry.created_at.isoformat(),
                        "deviation_hours": break_item["deviation"],
                        "description": f"Activity at unusual hour ({entry.created_at.hour}:00), deviates {break_item['deviation']}h from typical pattern"
                    })
        
        # Detect emotional state anomalies
        if "emotional_anomalies" in detection_types:
            # Look for unusual emotional patterns
            emotional_entries = [e for e in entries if e.metadata.get("emotional_state")]
            
            if len(emotional_entries) >= 3:
                # Check for sudden emotional shifts
                sorted_emotional = sorted(emotional_entries, key=lambda e: e.created_at)
                
                for i in range(1, len(sorted_emotional)):
                    prev_state = sorted_emotional[i-1].metadata.get("emotional_state", "neutral")
                    curr_state = sorted_emotional[i].metadata.get("emotional_state", "neutral")
                    
                    # Check for drastic changes (e.g., confident -> frustrated)
                    positive_states = ["confident", "excited", "happy", "motivated"]
                    negative_states = ["frustrated", "anxious", "stuck", "burned_out"]
                    
                    if (prev_state in positive_states and curr_state in negative_states) or \
                       (prev_state in negative_states and curr_state in positive_states):
                        outliers.append({
                            "type": "emotional_shift",
                            "entry_id": sorted_emotional[i].id,
                            "date": sorted_emotional[i].created_at.isoformat(),
                            "from_state": prev_state,
                            "to_state": curr_state,
                            "description": f"Notable emotional shift from '{prev_state}' to '{curr_state}'"
                        })
        
        # Sort outliers by date
        outliers.sort(key=lambda x: x["date"])
        
        logger.info(f"Outlier detection completed",
                   customer_id=customer_id,
                   outlier_count=len(outliers),
                   entry_count=len(entries))
        
        return {
            "status": "success",
            "result": {
                "customer_id": customer_id,
                "outliers": outliers,
                "outlier_count": len(outliers),
                "entry_count": len(entries),
                "threshold": threshold,
                "detected_at": datetime.now().isoformat()
            },
            "message": f"Detected {len(outliers)} outliers from {len(entries)} entries"
        }
        
    except Exception as e:
        logger.error(f"Failed to detect outliers", error=str(e))
        return {
            "status": "error",
            "result": None,
            "message": f"Detection failed: {str(e)}"
        }


if __name__ == "__main__":
    # Test entry point
    test_context = {
        "customer_id": "OPC-TEST-001",
        "input": {
            "types": ["energy_outliers", "frequency_outliers", "emotional_anomalies"],
            "time_range": "last_30_days",
            "threshold": 2.0
        },
        "config": {
            "journal_storage": {"path": "test_customers/OPC-TEST-001/journal"},
            "storage": {"path": "test_customers/OPC-TEST-001/patterns"}
        },
        "memory": {}
    }
    
    result = main(test_context)
    print(json.dumps(result, indent=2, ensure_ascii=False))
