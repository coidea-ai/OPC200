"""
Unit tests for patterns/analyzer.py - Behavior pattern analysis.
Following TDD: Red-Green-Refactor cycle.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit


class TestBehaviorAnalyzer:
    """Tests for behavior pattern analyzer."""

    def test_analyzer_initialization(self):
        """Test analyzer initialization."""
        # Arrange & Act
        from src.patterns.analyzer import BehaviorAnalyzer

        analyzer = BehaviorAnalyzer()

        # Assert
        assert analyzer is not None
        assert analyzer.patterns == {}

    def test_detect_daily_pattern(self):
        """Test detecting daily behavior pattern."""
        # Arrange
        from src.patterns.analyzer import BehaviorAnalyzer

        analyzer = BehaviorAnalyzer()

        # Create hourly activity data
        activities = [
            {"timestamp": datetime(2024, 3, 1, 9, 0), "action": "login"},
            {"timestamp": datetime(2024, 3, 2, 9, 5), "action": "login"},
            {"timestamp": datetime(2024, 3, 3, 9, 3), "action": "login"},
            {"timestamp": datetime(2024, 3, 4, 9, 7), "action": "login"},
            {"timestamp": datetime(2024, 3, 5, 9, 2), "action": "login"},
        ]

        # Act
        pattern = analyzer.detect_temporal_pattern(activities, "login")

        # Assert
        assert pattern["detected"] is True
        assert pattern["type"] == "daily"
        assert 8 <= pattern["peak_hour"] <= 10

    def test_detect_weekly_pattern(self):
        """Test detecting weekly behavior pattern."""
        # Arrange
        from src.patterns.analyzer import BehaviorAnalyzer

        analyzer = BehaviorAnalyzer()

        # Create weekly activity data (Monday focus)
        activities = [
            {"timestamp": datetime(2024, 3, 4, 10, 0), "action": "planning"},  # Monday
            {"timestamp": datetime(2024, 3, 11, 10, 0), "action": "planning"},  # Monday
            {"timestamp": datetime(2024, 3, 18, 10, 0), "action": "planning"},  # Monday
        ]

        # Act
        pattern = analyzer.detect_temporal_pattern(activities, "planning")

        # Assert
        assert pattern["detected"] is True
        assert pattern["type"] == "weekly"
        assert pattern["peak_day"] == "Monday"

    def test_no_pattern_detected(self):
        """Test when no clear pattern exists."""
        # Arrange
        from src.patterns.analyzer import BehaviorAnalyzer

        analyzer = BehaviorAnalyzer()

        # Random activities without pattern
        activities = [
            {"timestamp": datetime(2024, 3, 1, 3, 0), "action": "random"},
            {"timestamp": datetime(2024, 3, 2, 15, 0), "action": "random"},
            {"timestamp": datetime(2024, 3, 3, 22, 0), "action": "random"},
        ]

        # Act
        pattern = analyzer.detect_temporal_pattern(activities, "random")

        # Assert
        assert pattern["detected"] is False
        assert pattern["confidence"] < 0.5


class TestTrendAnalysis:
    """Tests for trend analysis."""

    def test_detect_increasing_trend(self):
        """Test detecting increasing trend."""
        # Arrange
        from src.patterns.analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer()

        # Increasing values
        values = [10, 12, 15, 18, 22, 28, 35]

        # Act
        trend = analyzer.detect_trend(values)

        # Assert
        assert trend["direction"] == "increasing"
        assert trend["strength"] > 0

    def test_detect_decreasing_trend(self):
        """Test detecting decreasing trend."""
        # Arrange
        from src.patterns.analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer()

        # Decreasing values
        values = [100, 95, 88, 82, 75, 70, 65]

        # Act
        trend = analyzer.detect_trend(values)

        # Assert
        assert trend["direction"] == "decreasing"
        assert trend["strength"] > 0

    def test_detect_stable_trend(self):
        """Test detecting stable trend."""
        # Arrange
        from src.patterns.analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer()

        # Stable values with small variation
        values = [50, 51, 49, 52, 50, 51, 50]

        # Act
        trend = analyzer.detect_trend(values)

        # Assert
        assert trend["direction"] == "stable"
        assert trend["strength"] < 0.3

    def test_forecast_future_values(self):
        """Test forecasting future values."""
        # Arrange
        from src.patterns.analyzer import TrendAnalyzer

        analyzer = TrendAnalyzer()

        values = [10, 12, 14, 16, 18, 20]  # Linear increase

        # Act
        forecast = analyzer.forecast(values, periods=3)

        # Assert
        assert len(forecast) == 3
        assert forecast[0] > 20  # Should continue increasing
        assert forecast[1] > forecast[0]


class TestAnomalyDetection:
    """Tests for anomaly detection."""

    def test_detect_statistical_outlier(self):
        """Test detecting statistical outliers."""
        # Arrange
        from src.patterns.analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Normal values with one outlier
        values = [10, 12, 11, 13, 12, 11, 100, 12, 11]

        # Act
        anomalies = detector.detect_outliers(values)

        # Assert
        assert len(anomalies) == 1
        assert anomalies[0]["index"] == 6  # Position of 100
        assert anomalies[0]["value"] == 100

    def test_detect_no_anomalies(self):
        """Test when no anomalies exist."""
        # Arrange
        from src.patterns.analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Normal values without outliers
        values = [10, 12, 11, 13, 12, 11, 12, 13, 11]

        # Act
        anomalies = detector.detect_outliers(values)

        # Assert
        assert len(anomalies) == 0

    def test_detect_pattern_break(self):
        """Test detecting pattern breaks."""
        # Arrange
        from src.patterns.analyzer import AnomalyDetector

        detector = AnomalyDetector()

        # Activity times - most at 9 AM, one at 1 AM (8 hours difference from 9)
        activities = [
            {"timestamp": datetime(2024, 3, 1, 9, 0), "action": "work"},
            {"timestamp": datetime(2024, 3, 2, 9, 0), "action": "work"},
            {"timestamp": datetime(2024, 3, 3, 9, 0), "action": "work"},
            {"timestamp": datetime(2024, 3, 4, 1, 0), "action": "work"},  # Anomaly - 8 hours early
            {"timestamp": datetime(2024, 3, 5, 9, 0), "action": "work"},
        ]

        # Act
        breaks = detector.detect_pattern_breaks(activities)

        # Assert
        assert len(breaks) == 1
        assert breaks[0]["timestamp"] == datetime(2024, 3, 4, 1, 0)

    def test_calculate_anomaly_score(self):
        """Test calculating anomaly score."""
        # Arrange
        from src.patterns.analyzer import AnomalyDetector

        detector = AnomalyDetector()

        baseline = [10, 12, 11, 13, 12, 11]

        # Act - Normal value
        score1 = detector.calculate_anomaly_score(12, baseline)

        # Act - Anomalous value
        score2 = detector.calculate_anomaly_score(100, baseline)

        # Assert
        assert 0 <= score1 < 0.5  # Low score for normal
        assert score2 > 0.5  # High score for anomaly


class TestProductivityPatterns:
    """Tests for productivity pattern analysis."""

    def test_analyze_productivity_hours(self):
        """Test analyzing most productive hours."""
        # Arrange
        from src.patterns.analyzer import ProductivityAnalyzer

        analyzer = ProductivityAnalyzer()

        # Work sessions with output measures
        sessions = [
            {"start": datetime(2024, 3, 1, 9, 0), "end": datetime(2024, 3, 1, 10, 0), "output": 10},
            {"start": datetime(2024, 3, 1, 14, 0), "end": datetime(2024, 3, 1, 15, 0), "output": 15},
            {"start": datetime(2024, 3, 2, 9, 0), "end": datetime(2024, 3, 2, 10, 0), "output": 12},
            {"start": datetime(2024, 3, 2, 14, 0), "end": datetime(2024, 3, 2, 15, 0), "output": 18},
        ]

        # Act
        peak_hours = analyzer.find_peak_productivity_hours(sessions)

        # Assert
        assert 14 in peak_hours  # 2 PM is more productive
        assert peak_hours[14] > peak_hours[9]

    def test_analyze_task_completion_patterns(self):
        """Test analyzing task completion patterns."""
        # Arrange
        from src.patterns.analyzer import ProductivityAnalyzer

        analyzer = ProductivityAnalyzer()

        tasks = [
            {"created": datetime(2024, 3, 1, 9, 0), "completed": datetime(2024, 3, 1, 10, 0), "type": "quick"},
            {"created": datetime(2024, 3, 1, 10, 0), "completed": datetime(2024, 3, 1, 14, 0), "type": "deep"},
            {"created": datetime(2024, 3, 2, 9, 0), "completed": datetime(2024, 3, 2, 9, 30), "type": "quick"},
        ]

        # Act
        patterns = analyzer.analyze_completion_patterns(tasks)

        # Assert
        assert "quick" in patterns
        assert "deep" in patterns
        assert patterns["quick"]["avg_duration"] < patterns["deep"]["avg_duration"]

    def test_identify_distraction_patterns(self):
        """Test identifying distraction patterns."""
        # Arrange
        from src.patterns.analyzer import ProductivityAnalyzer

        analyzer = ProductivityAnalyzer()

        # Work pattern with interruptions
        activities = [
            {"time": datetime(2024, 3, 1, 9, 0), "type": "focus", "duration": 25},
            {"time": datetime(2024, 3, 1, 9, 30), "type": "interruption", "duration": 10},
            {"time": datetime(2024, 3, 1, 9, 45), "type": "focus", "duration": 20},
            {"time": datetime(2024, 3, 1, 10, 10), "type": "interruption", "duration": 15},
        ]

        # Act
        distractions = analyzer.identify_distraction_patterns(activities)

        # Assert
        assert len(distractions) == 2
        assert all(d["type"] == "interruption" for d in distractions)


class TestPatternPersistence:
    """Tests for pattern persistence."""

    def test_save_patterns(self, temp_dir):
        """Test saving detected patterns."""
        # Arrange
        from src.patterns.analyzer import PatternStore

        store = PatternStore(storage_path=temp_dir)

        patterns = {
            "daily_login": {"type": "daily", "peak_hour": 9, "confidence": 0.85},
            "weekly_planning": {"type": "weekly", "peak_day": "Monday", "confidence": 0.90},
        }

        # Act
        result = store.save_patterns("user123", patterns)

        # Assert
        assert result is True
        assert (temp_dir / "user123_patterns.json").exists()

    def test_load_patterns(self, temp_dir):
        """Test loading saved patterns."""
        # Arrange
        from src.patterns.analyzer import PatternStore

        store = PatternStore(storage_path=temp_dir)

        patterns = {
            "daily_login": {"type": "daily", "peak_hour": 9, "confidence": 0.85},
        }
        store.save_patterns("user123", patterns)

        # Act
        loaded = store.load_patterns("user123")

        # Assert
        assert loaded["daily_login"]["peak_hour"] == 9
        assert loaded["daily_login"]["confidence"] == 0.85

    def test_delete_old_patterns(self, temp_dir):
        """Test deleting patterns older than threshold."""
        # Arrange
        from datetime import datetime, timedelta
        from src.patterns.analyzer import PatternStore

        store = PatternStore(storage_path=temp_dir)

        # Use ISO format string instead of datetime object
        patterns = {"test": {"detected_at": (datetime.now() - timedelta(days=100)).isoformat()}}
        store.save_patterns("user123", patterns)

        # Act
        result = store.delete_old_patterns(days=30)

        # Assert
        assert result is True
        loaded = store.load_patterns("user123")
        assert len(loaded) == 0


class TestPatternRecommendations:
    """Tests for pattern-based recommendations."""

    def test_generate_schedule_recommendation(self):
        """Test generating schedule recommendations based on patterns."""
        # Arrange
        from src.patterns.analyzer import PatternRecommender

        recommender = PatternRecommender()

        # Pass data with peak_hours at root level as expected by function
        patterns = {
            "peak_hours": [9, 10, 14, 15],
            "focus_sessions": 2,
        }

        # Act
        recommendations = recommender.generate_schedule_recommendations(patterns)

        # Assert
        assert len(recommendations) > 0
        assert any("deep work" in r.lower() for r in recommendations)

    def test_suggest_break_times(self):
        """Test suggesting optimal break times."""
        # Arrange
        from src.patterns.analyzer import PatternRecommender

        recommender = PatternRecommender()

        fatigue_pattern = {
            "focus_durations": [45, 40, 35, 30, 25],  # Decreasing
            "productivity_drops": [11, 15, 16],  # Times when productivity drops
        }

        # Act
        breaks = recommender.suggest_break_times(fatigue_pattern)

        # Assert
        assert len(breaks) > 0
        # Should suggest breaks when productivity drops
        assert any(11 <= b <= 16 for b in breaks)

    def test_recommend_task_batching(self):
        """Test recommending task batching based on patterns."""
        # Arrange
        from src.patterns.analyzer import PatternRecommender

        recommender = PatternRecommender()

        task_patterns = {
            "email": {"frequency": "high", "avg_duration": 5, "context_switch_cost": 10},
            "coding": {"frequency": "medium", "avg_duration": 120, "context_switch_cost": 30},
        }

        # Act
        batching = recommender.recommend_task_batching(task_patterns)

        # Assert
        assert "email" in batching
        # High frequency, short tasks should be batched
        assert batching["email"]["should_batch"] is True
