"""
Patterns Analyzer Module - Behavior pattern detection and analysis.

⚠️ REPOSITIONED (v2.4): The heavy statistical behavior analysis in this module
has been superseded by OpenClaw v2026.4.9+ native dreaming and memory compaction.

The skill-level pattern recognition is now an "Interpretation Layer" that reads
OpenClaw-generated dreams.md / memory/*.md and performs OPC-specific business
interpretation rather than raw statistical modeling.

This module is retained as a fallback / reference implementation but is no longer
the active path for routine pattern analysis in OPC200.
"""
import json
import math
import statistics
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import numpy as np

# Named constants for pattern detection thresholds
DAILY_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence for daily pattern detection
WEEKLY_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence for weekly pattern detection
PATTERN_BREAK_HOUR_DEVIATION = 6  # Hours deviation threshold for pattern break detection
OUTLIER_ZSCORE_THRESHOLD = 2.0  # Default z-score threshold for outlier detection

# Time-related constants
MINUTES_PER_HOUR = 60
HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7

# Statistical constants
MIN_SAMPLES_FOR_STD = 2  # Minimum samples needed for standard deviation calculation
MIN_SAMPLES_FOR_OUTLIERS = 3  # Minimum samples needed for outlier detection


@dataclass
class BehaviorAnalyzer:
    """Analyze behavior patterns."""
    
    patterns: Optional[dict[str, Any]] = None
    
    def __post_init__(self):
        if self.patterns is None:
            self.patterns = {}
    
    def detect_temporal_pattern(self, activities: list[dict], action_type: str) -> dict:
        """Detect temporal patterns in activities."""
        if not activities:
            return {"detected": False, "confidence": 0.0}
        
        # Extract hours and days
        hours = []
        days = []
        
        for activity in activities:
            timestamp = activity.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            if timestamp is not None:
                hours.append(timestamp.hour)
                days.append(timestamp.weekday())
        
        # Calculate patterns
        hour_counts = Counter(hours)
        day_counts = Counter(days)
        
        most_common_hour = hour_counts.most_common(1)[0]
        most_common_day = day_counts.most_common(1)[0]
        
        # Calculate confidence
        total = len(activities)
        hour_confidence = most_common_hour[1] / total
        day_confidence = most_common_day[1] / total
        
        # Determine pattern type
        # Weekly: activities consistently happen on same day of week
        # Daily: activities consistently happen at same hour
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Check weekly pattern first (if same day of week with high confidence)
        if day_confidence > WEEKLY_CONFIDENCE_THRESHOLD:
            return {
                "detected": True,
                "type": "weekly",
                "peak_day": day_names[most_common_day[0]],
                "confidence": day_confidence,
                "sample_size": total
            }
        # Then check daily pattern (same hour)
        elif hour_confidence > DAILY_CONFIDENCE_THRESHOLD:
            return {
                "detected": True,
                "type": "daily",
                "peak_hour": most_common_hour[0],
                "confidence": hour_confidence,
                "sample_size": total
            }
        
        return {
            "detected": False,
            "confidence": max(hour_confidence, day_confidence),
            "sample_size": total
        }


@dataclass
class TrendAnalyzer:
    """Analyze trends in data."""
    
    def detect_trend(self, values: list[float]) -> dict:
        """Detect trend direction and strength."""
        if len(values) < MIN_SAMPLES_FOR_STD:
            return {"direction": "stable", "strength": 0.0}
        
        # Calculate linear regression
        x = np.arange(len(values))
        y = np.array(values)
        
        # Simple slope calculation
        slope = np.polyfit(x, y, 1)[0]
        
        # Calculate R-squared
        correlation = np.corrcoef(x, y)[0, 1]
        r_squared = correlation ** 2 if not np.isnan(correlation) else 0
        
        # Determine direction using relative threshold
        # Use coefficient of variation to determine stability
        mean_val = np.mean(y)
        if mean_val != 0:
            relative_slope = abs(slope) / mean_val
        else:
            relative_slope = abs(slope)
        
        if relative_slope < 0.001:  # Relative threshold
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        return {
            "direction": direction,
            "slope": float(slope),
            "strength": float(r_squared),
            "correlation": float(correlation) if not np.isnan(correlation) else 0.0
        }
    
    def forecast(self, values: list[float], periods: int = 5) -> list[float]:
        """Forecast future values using linear trend."""
        if len(values) < MIN_SAMPLES_FOR_STD:
            return [values[-1]] * periods if values else [0.0] * periods
        
        x = np.arange(len(values))
        y = np.array(values)
        
        # Fit linear model
        slope, intercept = np.polyfit(x, y, 1)
        
        # Forecast
        forecasts = []
        for i in range(periods):
            next_x = len(values) + i
            forecast = slope * next_x + intercept
            forecasts.append(float(forecast))
        
        return forecasts


@dataclass
class AnomalyDetector:
    """Detect anomalies in data."""
    
    def detect_outliers(self, values: list[float], threshold: float = OUTLIER_ZSCORE_THRESHOLD) -> list[dict]:
        """Detect statistical outliers using z-score.
        
        Args:
            values: List of values to analyze
            threshold: Z-score threshold for outlier detection (default: 2.0)
            
        Returns:
            List of outlier dictionaries with index, value, and statistics
        """
        # Check for empty list
        if not values:
            return []
        
        if len(values) < MIN_SAMPLES_FOR_OUTLIERS:
            return []
        
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        
        if std == 0:
            return []
        
        outliers = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > threshold:
                outliers.append({
                    "index": i,
                    "value": value,
                    "z_score": z_score,
                    "mean": mean,
                    "std": std
                })
        
        return outliers
    
    def detect_pattern_breaks(self, activities: list[dict]) -> list[dict]:
        """Detect breaks in activity patterns."""
        if len(activities) < MIN_SAMPLES_FOR_OUTLIERS:
            return []
        
        breaks = []
        
        # Calculate typical hour variance
        hours = []
        for activity in activities:
            timestamp = activity.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            if timestamp is not None and hasattr(timestamp, "hour"):
                hours.append(timestamp.hour)
        
        if not hours:
            return []
        
        mean_hour = statistics.mean(hours)
        
        # Find activities that deviate significantly
        for i, activity in enumerate(activities):
            timestamp = activity.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            
            if timestamp is not None and hasattr(timestamp, "hour"):
                hour_diff = abs(timestamp.hour - mean_hour)
                if hour_diff > PATTERN_BREAK_HOUR_DEVIATION:  # More than 6 hours deviation
                    breaks.append({
                        "index": i,
                        "timestamp": timestamp,
                        "activity": activity,
                        "deviation": hour_diff
                    })
        
        return breaks
    
    def calculate_anomaly_score(self, value: float, baseline: list[float]) -> float:
        """Calculate anomaly score for a value."""
        if not baseline:
            return 0.0
        
        mean = statistics.mean(baseline)
        std = statistics.stdev(baseline) if len(baseline) > 1 else 1
        
        if std == 0:
            return 0.0 if value == mean else 1.0
        
        z_score = abs((value - mean) / std)
        # Normalize to 0-1 range using sigmoid
        score = 1 / (1 + math.exp(-z_score + 2))
        
        return min(1.0, max(0.0, score))


@dataclass
class ProductivityAnalyzer:
    """Analyze productivity patterns."""
    
    def find_peak_productivity_hours(self, sessions: list[dict]) -> dict[int, float]:
        """Find most productive hours."""
        hour_outputs: dict[int, float] = {}
        hour_counts: dict[int, int] = {}
        
        for session in sessions:
            start = session.get("start")
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            
            if start is not None and hasattr(start, "hour"):
                hour = start.hour
                output = session.get("output", 0)
                
                hour_outputs[hour] = hour_outputs.get(hour, 0) + output
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        # Calculate average output per hour
        peak_hours: dict[int, float] = {}
        for hour in hour_outputs:
            if hour_counts.get(hour, 0) > 0:
                avg_output = hour_outputs[hour] / hour_counts[hour]
                peak_hours[hour] = avg_output
        
        return dict(sorted(peak_hours.items(), key=lambda x: x[1], reverse=True))
    
    def analyze_completion_patterns(self, tasks: list[dict]) -> dict[str, dict]:
        """Analyze task completion patterns."""
        type_stats: dict[str, dict[str, Any]] = {}
        
        for task in tasks:
            task_type = task.get("type", "unknown")
            created = task.get("created")
            completed = task.get("completed")
            
            if isinstance(created, str):
                created = datetime.fromisoformat(created)
            if isinstance(completed, str):
                completed = datetime.fromisoformat(completed)
            
            if created is None or completed is None:
                continue
                
            duration = (completed - created).total_seconds() / 3600  # hours
            
            if task_type not in type_stats:
                type_stats[task_type] = {"durations": [], "count": 0}
            
            type_stats[task_type]["durations"].append(duration)
            type_stats[task_type]["count"] += 1
        
        # Calculate averages
        patterns: dict[str, dict] = {}
        for task_type, stats in type_stats.items():
            durations = stats["durations"]
            patterns[task_type] = {
                "avg_duration": statistics.mean(durations) if durations else 0,
                "median_duration": statistics.median(durations) if durations else 0,
                "task_count": stats["count"]
            }
        
        return patterns
    
    def identify_distraction_patterns(self, activities: list[dict]) -> list[dict]:
        """Identify distraction patterns."""
        distractions = []
        
        for activity in activities:
            if activity.get("type") == "interruption":
                distractions.append(activity)
        
        return distractions


@dataclass
class PatternStore:
    """Store and retrieve detected patterns."""
    
    storage_path: Path
    
    def __post_init__(self):
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_patterns(self, user_id: str, patterns: dict) -> bool:
        """Save patterns for a user."""
        pattern_file = self.storage_path / f"{user_id}_patterns.json"
        
        data = {
            "user_id": user_id,
            "patterns": patterns,
            "saved_at": datetime.now().isoformat()
        }
        
        pattern_file.write_text(json.dumps(data, indent=2))
        return True
    
    def load_patterns(self, user_id: str) -> dict[str, Any]:
        """Load patterns for a user."""
        pattern_file = self.storage_path / f"{user_id}_patterns.json"
        
        if not pattern_file.exists():
            return {}
        
        data: dict[str, Any] = json.loads(pattern_file.read_text())
        patterns: dict[str, Any] = data.get("patterns", {})
        return patterns
    
    def delete_old_patterns(self, days: int = 30) -> bool:
        """Delete patterns older than specified days."""
        cutoff = datetime.now() - timedelta(days=days)
        
        for pattern_file in self.storage_path.glob("*_patterns.json"):
            try:
                data = json.loads(pattern_file.read_text())
                saved_at = datetime.fromisoformat(data.get("saved_at", "2000-01-01"))
                
                # Check if any pattern in the file has an old detected_at
                patterns = data.get("patterns", {})
                has_old_pattern = False
                for pattern_name, pattern_data in patterns.items():
                    detected_at_str = pattern_data.get("detected_at")
                    if detected_at_str:
                        try:
                            detected_at = datetime.fromisoformat(detected_at_str)
                            if detected_at < cutoff:
                                has_old_pattern = True
                                break
                        except (ValueError, TypeError):
                            continue
                
                # Delete if saved_at is old OR has an old pattern
                if saved_at < cutoff or has_old_pattern:
                    pattern_file.unlink()
            except (json.JSONDecodeError, ValueError):
                continue
        
        return True


@dataclass
class PatternRecommender:
    """Generate recommendations based on patterns."""
    
    def generate_schedule_recommendations(self, productivity_data: dict) -> list[str]:
        """Generate schedule recommendations."""
        recommendations = []
        
        peak_hours = productivity_data.get("peak_hours", [])
        
        if peak_hours:
            hour_str = ", ".join(f"{h}:00" for h in peak_hours[:3])
            recommendations.append(
                f"Schedule deep work during your peak productivity hours: {hour_str}"
            )
        
        focus_sessions = productivity_data.get("focus_sessions", 0)
        if focus_sessions < 3:
            recommendations.append(
                "Try to increase your daily focus sessions for better productivity"
            )
        
        trend = productivity_data.get("improvement_trend")
        if trend == "decreasing":
            recommendations.append(
                "Your productivity has been declining. Consider reviewing your workload."
            )
        
        return recommendations
    
    def suggest_break_times(self, fatigue_pattern: dict) -> list[int]:
        """Suggest optimal break times."""
        productivity_drops = fatigue_pattern.get("productivity_drops", [])
        
        # Suggest breaks 30 minutes before typical drop times
        break_times = []
        for drop_time in productivity_drops:
            break_time = max(0, drop_time - 0.5)
            break_times.append(int(break_time))
        
        return list(set(break_times))
    
    def recommend_task_batching(self, task_patterns: dict) -> dict[str, dict]:
        """Recommend task batching strategies."""
        recommendations = {}
        
        for task_type, pattern in task_patterns.items():
            frequency = pattern.get("frequency", "low")
            duration = pattern.get("avg_duration", 30)
            context_switch = pattern.get("context_switch_cost", 10)
            
            should_batch = frequency == "high" and duration < 15
            
            recommendations[task_type] = {
                "should_batch": should_batch,
                "reason": "High frequency, short duration tasks benefit from batching" if should_batch else "Task characteristics don't suggest batching",
                "suggested_batch_size": 5 if should_batch else 1
            }
        
        return recommendations
