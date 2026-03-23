"""
Unit tests for insights/generator.py - Insight generation.
Following TDD: Red-Green-Refactor cycle.
"""
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

pytestmark = pytest.mark.unit


class TestInsightGenerator:
    """Tests for insight generator."""
    
    def test_generator_initialization(self):
        """Test insight generator initialization."""
        # Arrange & Act
        from src.insights.generator import InsightGenerator
        
        generator = InsightGenerator()
        
        # Assert
        assert generator is not None
    
    def test_generate_daily_summary(self):
        """Test generating daily summary insight."""
        # Arrange
        from src.insights.generator import InsightGenerator
        
        generator = InsightGenerator()
        
        activities = [
            {"type": "task_completed", "description": "Finished report"},
            {"type": "meeting", "description": "Team sync"},
            {"type": "task_completed", "description": "Code review"},
        ]
        
        # Act
        insight = generator.generate_daily_summary(activities, date=datetime(2024, 3, 15))
        
        # Assert
        assert insight["type"] == "daily_summary"
        assert insight["date"] == "2024-03-15"
        assert "tasks_completed" in insight
        assert insight["tasks_completed"] == 2
    
    def test_generate_weekly_review(self):
        """Test generating weekly review insight."""
        # Arrange
        from src.insights.generator import InsightGenerator
        
        generator = InsightGenerator()
        
        daily_summaries = [
            {"date": "2024-03-11", "tasks_completed": 5, "focus_hours": 6},
            {"date": "2024-03-12", "tasks_completed": 3, "focus_hours": 4},
            {"date": "2024-03-13", "tasks_completed": 7, "focus_hours": 8},
            {"date": "2024-03-14", "tasks_completed": 4, "focus_hours": 5},
            {"date": "2024-03-15", "tasks_completed": 6, "focus_hours": 7},
        ]
        
        # Act
        insight = generator.generate_weekly_review(
            daily_summaries,
            week_start=datetime(2024, 3, 11)
        )
        
        # Assert
        assert insight["type"] == "weekly_review"
        assert insight["total_tasks_completed"] == 25
        assert insight["avg_focus_hours_per_day"] == 6.0
        assert "productivity_trend" in insight
    
    def test_generate_milestone_insight(self):
        """Test generating milestone insight."""
        # Arrange
        from src.insights.generator import InsightGenerator
        
        generator = InsightGenerator()
        
        milestone = {
            "name": "First 100 Days",
            "date_achieved": datetime(2024, 3, 15),
            "metrics": {
                "tasks_completed": 500,
                "hours_logged": 800,
            }
        }
        
        # Act
        insight = generator.generate_milestone_insight(milestone)
        
        # Assert
        assert insight["type"] == "milestone"
        assert insight["milestone_name"] == "First 100 Days"
        assert "celebration_message" in insight
        assert "impact_assessment" in insight


class TestRecommendationEngine:
    """Tests for recommendation engine."""
    
    def test_generate_productivity_recommendations(self):
        """Test generating productivity recommendations."""
        # Arrange
        from src.insights.generator import RecommendationEngine
        
        engine = RecommendationEngine()
        
        productivity_data = {
            "peak_hours": [9, 10, 14, 15],
            "low_hours": [13, 16, 17],
            "avg_focus_session": 25,
            "interruption_frequency": "high",
        }
        
        # Act
        recommendations = engine.generate_productivity_recommendations(productivity_data)
        
        # Assert
        assert len(recommendations) > 0
        assert any("deep work" in r.lower() for r in recommendations)
    
    def test_generate_work_life_balance_recommendations(self):
        """Test generating work-life balance recommendations."""
        # Arrange
        from src.insights.generator import RecommendationEngine
        
        engine = RecommendationEngine()
        
        work_patterns = {
            "avg_daily_hours": 10,
            "weekend_work_frequency": 0.8,
            "late_night_sessions": 5,
            "break_frequency": "low",
        }
        
        # Act
        recommendations = engine.generate_work_life_balance_recommendations(work_patterns)
        
        # Assert
        assert len(recommendations) > 0
        assert any("break" in r.lower() for r in recommendations)
    
    def test_generate_skill_development_recommendations(self):
        """Test generating skill development recommendations."""
        # Arrange
        from src.insights.generator import RecommendationEngine
        
        engine = RecommendationEngine()
        
        skill_data = {
            "current_skills": ["Python", "SQL"],
            "frequent_tasks": ["data_analysis", "api_development"],
            "skill_gaps": ["machine_learning", "cloud_architecture"],
        }
        
        # Act
        recommendations = engine.generate_skill_development_recommendations(skill_data)
        
        # Assert
        assert len(recommendations) > 0
        assert any("learn" in r.lower() or "skill" in r.lower() for r in recommendations)
    
    def test_prioritize_recommendations(self):
        """Test prioritizing recommendations by impact."""
        # Arrange
        from src.insights.generator import RecommendationEngine
        
        engine = RecommendationEngine()
        
        recommendations = [
            {"text": "Take more breaks", "impact": "medium", "effort": "low"},
            {"text": "Learn new skill", "impact": "high", "effort": "high"},
            {"text": "Adjust schedule", "impact": "high", "effort": "low"},
        ]
        
        # Act
        prioritized = engine.prioritize(recommendations)
        
        # Assert
        # High impact, low effort should come first
        assert prioritized[0]["text"] == "Adjust schedule"


class TestReportGenerator:
    """Tests for report generation."""
    
    def test_generate_progress_report(self):
        """Test generating progress report."""
        # Arrange
        from src.insights.generator import ReportGenerator
        
        generator = ReportGenerator()
        
        goals = [
            {"name": "Learn Python", "target": 100, "current": 75, "unit": "hours"},
            {"name": "Complete Project", "target": 1, "current": 0.5, "unit": "projects"},
        ]
        
        # Act
        report = generator.generate_progress_report(
            goals,
            period_start=datetime(2024, 3, 1),
            period_end=datetime(2024, 3, 31)
        )
        
        # Assert
        assert report["type"] == "progress_report"
        assert len(report["goals"]) == 2
        assert report["goals"][0]["progress_percentage"] == 75.0
    
    def test_generate_comparison_report(self):
        """Test generating period comparison report."""
        # Arrange
        from src.insights.generator import ReportGenerator
        
        generator = ReportGenerator()
        
        period1 = {"name": "January", "tasks_completed": 50, "focus_hours": 120}
        period2 = {"name": "February", "tasks_completed": 65, "focus_hours": 140}
        
        # Act
        report = generator.generate_comparison_report(period1, period2)
        
        # Assert
        assert report["type"] == "comparison"
        assert report["task_change_percentage"] == 30.0  # (65-50)/50 * 100
        assert report["focus_hours_change_percentage"] > 0
    
    def test_export_report_to_json(self, temp_dir):
        """Test exporting report to JSON."""
        # Arrange
        import json
        from src.insights.generator import ReportGenerator
        
        generator = ReportGenerator()
        
        report = {
            "type": "test_report",
            "data": {"key": "value"}
        }
        
        output_path = temp_dir / "report.json"
        
        # Act
        result = generator.export_to_json(report, output_path)
        
        # Assert
        assert result is True
        assert output_path.exists()
        
        with open(output_path) as f:
            loaded = json.load(f)
            assert loaded["type"] == "test_report"
    
    def test_export_report_to_markdown(self, temp_dir):
        """Test exporting report to Markdown."""
        # Arrange
        from src.insights.generator import ReportGenerator
        
        generator = ReportGenerator()
        
        report = {
            "title": "Weekly Report",
            "sections": [
                {"heading": "Summary", "content": "This was a productive week."},
                {"heading": "Achievements", "content": ["Completed project", "Learned new skill"]},
            ]
        }
        
        output_path = temp_dir / "report.md"
        
        # Act
        result = generator.export_to_markdown(report, output_path)
        
        # Assert
        assert result is True
        assert output_path.exists()
        
        content = output_path.read_text()
        assert "# Weekly Report" in content
        assert "## Summary" in content


class TestPatternInsights:
    """Tests for pattern-based insights."""
    
    def test_detect_productivity_patterns(self):
        """Test detecting productivity patterns."""
        # Arrange
        from src.insights.generator import PatternInsightGenerator
        
        generator = PatternInsightGenerator()
        
        work_sessions = [
            {"start": datetime(2024, 3, 1, 9, 0), "output": 10},
            {"start": datetime(2024, 3, 1, 14, 0), "output": 15},
            {"start": datetime(2024, 3, 2, 9, 0), "output": 12},
            {"start": datetime(2024, 3, 2, 14, 0), "output": 18},
        ]
        
        # Act
        patterns = generator.detect_productivity_patterns(work_sessions)
        
        # Assert
        assert "peak_hours" in patterns
        assert "afternoon" in str(patterns["peak_hours"]).lower()
    
    def test_identify_improvement_areas(self):
        """Test identifying areas for improvement."""
        # Arrange
        from src.insights.generator import PatternInsightGenerator
        
        generator = PatternInsightGenerator()
        
        metrics = {
            "task_completion_rate": 0.6,
            "on_time_delivery": 0.7,
            "focus_sessions_per_day": 2,
            "interruptions_per_hour": 5,
        }
        
        # Act
        areas = generator.identify_improvement_areas(metrics)
        
        # Assert
        assert len(areas) > 0
        # Low completion rate should be flagged
        assert any("completion" in a.lower() for a in areas)
    
    def test_generate_streak_insights(self):
        """Test generating streak-based insights."""
        # Arrange
        from src.insights.generator import PatternInsightGenerator
        
        generator = PatternInsightGenerator()
        
        activity_log = [
            {"date": datetime(2024, 3, 1), "activity": "coding", "completed": True},
            {"date": datetime(2024, 3, 2), "activity": "coding", "completed": True},
            {"date": datetime(2024, 3, 3), "activity": "coding", "completed": True},
            {"date": datetime(2024, 3, 4), "activity": "coding", "completed": False},
        ]
        
        # Act
        streaks = generator.calculate_streaks(activity_log)
        
        # Assert
        assert "coding" in streaks
        assert streaks["coding"]["current"] == 0  # Streak broken on March 4
        assert streaks["coding"]["longest"] == 3


class TestInsightPersonalization:
    """Tests for insight personalization."""
    
    def test_personalize_insight_for_user(self):
        """Test personalizing insight for specific user."""
        # Arrange
        from src.insights.generator import PersonalizedInsightGenerator
        
        generator = PersonalizedInsightGenerator()
        
        user_profile = {
            "name": "Alice",
            "preferences": {"communication_style": "casual"},
            "goals": ["improve productivity", "learn Python"],
        }
        
        insight = {
            "type": "productivity_tip",
            "content": "Consider taking more breaks.",
        }
        
        # Act
        personalized = generator.personalize(insight, user_profile)
        
        # Assert
        assert personalized["personalized"] is True
        assert "Alice" in personalized["content"] or "alice" in personalized["content"].lower()
    
    def test_adapt_tone_based_on_context(self):
        """Test adapting insight tone based on context."""
        # Arrange
        from src.insights.generator import PersonalizedInsightGenerator
        
        generator = PersonalizedInsightGenerator()
        
        # High stress context
        high_stress_context = {"stress_level": "high", "deadline_pressure": True}
        
        # Act
        tone = generator.select_tone(high_stress_context)
        
        # Assert
        assert tone in ["supportive", "encouraging"]
        
        # Low stress context
        low_stress_context = {"stress_level": "low", "celebration_worthy": True}
        tone = generator.select_tone(low_stress_context)
        assert tone in ["celebratory", "enthusiastic"]
