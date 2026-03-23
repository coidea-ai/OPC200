"""
Insights Generator Module - Generate insights and recommendations.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, NotRequired, Optional, TypedDict


# Date format constants
DATE_FORMAT_ISO = "%Y-%m-%d"  # ISO 8601 date format
DATE_FORMAT_DISPLAY = "%B %d, %Y"  # Human-readable date format
DATE_FORMAT_FILENAME = "%Y%m%d_%H%M%S"  # Filename-safe date format


# TypedDict definitions for structured parameters
class DailySummaryParams(TypedDict):
    """Parameters for daily summary generation."""
    activities: list[dict]
    date: NotRequired[Optional[datetime]]


class WeeklyReviewParams(TypedDict):
    """Parameters for weekly review generation."""
    daily_summaries: list[dict]
    week_start: datetime


class MilestoneParams(TypedDict):
    """Parameters for milestone insight generation."""
    name: str
    date_achieved: datetime | str
    metrics: NotRequired[dict]


class ProductivityData(TypedDict):
    """Productivity data structure for recommendations."""
    peak_hours: list[int]
    avg_focus_session: float
    interruption_frequency: str


class WorkPatterns(TypedDict):
    """Work patterns structure for recommendations."""
    avg_daily_hours: float
    weekend_work_frequency: float
    break_frequency: str


@dataclass
class InsightGenerator:
    """Generate insights from journal data."""
    
    def generate_daily_summary(self, params: DailySummaryParams) -> dict[str, Any]:
        """Generate daily summary insight."""
        activities: list[dict] = params["activities"]
        date: datetime = params.get("date") or datetime.now()
        
        tasks_completed = sum(1 for a in activities if a.get("type") == "task_completed")
        meetings = sum(1 for a in activities if a.get("type") == "meeting")
        
        return {
            "type": "daily_summary",
            "date": date.strftime(DATE_FORMAT_ISO),
            "tasks_completed": tasks_completed,
            "meetings": meetings,
            "total_activities": len(activities),
            "summary": f"Completed {tasks_completed} tasks and attended {meetings} meetings today."
        }
    
    def generate_weekly_review(self, params: WeeklyReviewParams) -> dict[str, Any]:
        """Generate weekly review insight."""
        daily_summaries: list[dict] = params["daily_summaries"]
        week_start: datetime = params["week_start"]
        
        total_tasks = sum(d.get("tasks_completed", 0) for d in daily_summaries)
        total_focus_hours = sum(d.get("focus_hours", 0) for d in daily_summaries)
        
        # Calculate trend
        if len(daily_summaries) >= 2:
            first_half = sum(d.get("tasks_completed", 0) for d in daily_summaries[:len(daily_summaries)//2])
            second_half = sum(d.get("tasks_completed", 0) for d in daily_summaries[len(daily_summaries)//2:])
            
            if second_half > first_half:
                trend = "improving"
            elif second_half < first_half:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "type": "weekly_review",
            "week_start": week_start.strftime(DATE_FORMAT_ISO),
            "total_tasks_completed": total_tasks,
            "avg_focus_hours_per_day": total_focus_hours / len(daily_summaries) if daily_summaries else 0,
            "productivity_trend": trend,
            "summary": f"This week you completed {total_tasks} tasks with a {trend} trend."
        }
    
    def generate_milestone_insight(self, milestone: MilestoneParams) -> dict[str, Any]:
        """Generate milestone achievement insight."""
        metrics = milestone.get("metrics", {})
        
        return {
            "type": "milestone",
            "milestone_name": milestone["name"],
            "date_achieved": milestone["date_achieved"].strftime(DATE_FORMAT_ISO) if isinstance(milestone["date_achieved"], datetime) else milestone["date_achieved"],
            "celebration_message": f"🎉 Congratulations on achieving {milestone['name']}!",
            "metrics_achieved": metrics,
            "impact_assessment": self._assess_impact(metrics)
        }
    
    def _assess_impact(self, metrics: dict) -> str:
        """Assess the impact of milestone metrics."""
        tasks = metrics.get("tasks_completed", 0)
        hours = metrics.get("hours_logged", 0)
        
        if tasks > 100:
            return "Exceptional productivity demonstrated."
        elif tasks > 50:
            return "Strong consistent effort maintained."
        else:
            return "Good progress on your journey."


@dataclass
class RecommendationEngine:
    """Generate personalized recommendations."""
    
    def generate_productivity_recommendations(self, productivity_data: dict) -> list[str]:
        """Generate productivity recommendations."""
        recommendations = []
        
        peak_hours = productivity_data.get("peak_hours", [])
        if peak_hours:
            hour_str = ", ".join(f"{h}:00" for h in peak_hours[:3])
            recommendations.append(
                f"Schedule deep work during your peak productivity hours: {hour_str}"
            )
        
        avg_session = productivity_data.get("avg_focus_session", 0)
        if avg_session < 25:
            recommendations.append(
                "Try the Pomodoro technique: 25 minutes focus, 5 minutes break"
            )
        
        interruptions = productivity_data.get("interruption_frequency", "low")
        if interruptions == "high":
            recommendations.append(
                "Consider using 'Do Not Disturb' mode during focus hours"
            )
        
        return recommendations
    
    def generate_work_life_balance_recommendations(self, work_patterns: dict) -> list[str]:
        """Generate work-life balance recommendations."""
        recommendations = []
        
        daily_hours = work_patterns.get("avg_daily_hours", 8)
        if daily_hours > 10:
            recommendations.append(
                "Your workday is quite long. Consider setting clearer boundaries."
            )
        
        weekend_work = work_patterns.get("weekend_work_frequency", 0)
        if weekend_work > 0.5:
            recommendations.append(
                "Try to protect your weekends for rest and recovery."
            )
        
        break_freq = work_patterns.get("break_frequency", "normal")
        if break_freq == "low":
            recommendations.append(
                "Remember to take regular breaks throughout the day."
            )
        
        return recommendations
    
    def generate_skill_development_recommendations(self, skill_data: dict) -> list[str]:
        """Generate skill development recommendations."""
        recommendations = []
        
        gaps = skill_data.get("skill_gaps", [])
        if gaps:
            gap_str = ", ".join(gaps[:3])
            recommendations.append(
                f"Consider learning these skills: {gap_str}"
            )
        
        current = skill_data.get("current_skills", [])
        if len(current) < 3:
            recommendations.append(
                "Building a diverse skill set will help your career growth."
            )
        
        return recommendations
    
    def prioritize(self, recommendations: list[dict]) -> list[dict]:
        """Prioritize recommendations by impact and effort."""
        # Score: high impact + low effort = high priority
        def score(rec):
            impact_scores = {"high": 3, "medium": 2, "low": 1}
            effort_scores = {"low": 3, "medium": 2, "high": 1}
            
            impact = impact_scores.get(rec.get("impact", "medium"), 2)
            effort = effort_scores.get(rec.get("effort", "medium"), 2)
            
            return impact + effort
        
        return sorted(recommendations, key=score, reverse=True)


@dataclass
class ReportGenerator:
    """Generate progress reports."""
    
    def generate_progress_report(self, goals: list[dict], period_start: datetime, period_end: datetime) -> dict:
        """Generate progress report for goals."""
        goal_progress = []
        
        for goal in goals:
            progress_pct = (goal["current"] / goal["target"]) * 100 if goal["target"] > 0 else 0
            
            goal_progress.append({
                "name": goal["name"],
                "target": goal["target"],
                "current": goal["current"],
                "unit": goal.get("unit", "items"),
                "progress_percentage": round(progress_pct, 1),
                "status": "completed" if progress_pct >= 100 else "in_progress"
            })
        
        return {
            "type": "progress_report",
            "period_start": period_start.strftime(DATE_FORMAT_ISO),
            "period_end": period_end.strftime(DATE_FORMAT_ISO),
            "goals": goal_progress,
            "overall_progress": round(
                sum(g["progress_percentage"] for g in goal_progress) / len(goal_progress), 1
            ) if goal_progress else 0
        }
    
    def generate_comparison_report(self, period1: dict, period2: dict) -> dict:
        """Generate comparison report between two periods."""
        tasks1 = period1.get("tasks_completed", 0)
        tasks2 = period2.get("tasks_completed", 0)
        task_change = ((tasks2 - tasks1) / tasks1 * 100) if tasks1 > 0 else 0
        
        hours1 = period1.get("focus_hours", 0)
        hours2 = period2.get("focus_hours", 0)
        hours_change = ((hours2 - hours1) / hours1 * 100) if hours1 > 0 else 0
        
        return {
            "type": "comparison",
            "period1": period1.get("name", "Period 1"),
            "period2": period2.get("name", "Period 2"),
            "task_change_percentage": round(task_change, 1),
            "focus_hours_change_percentage": round(hours_change, 1),
            "summary": self._generate_comparison_summary(task_change, hours_change)
        }
    
    def _generate_comparison_summary(self, task_change: float, hours_change: float) -> str:
        """Generate human-readable comparison summary."""
        if task_change > 10 and hours_change > 10:
            return "Significant improvement in both tasks and focus time."
        elif task_change > 10:
            return "Improved task completion with maintained focus."
        elif task_change < -10:
            return "Decreased output. Consider reviewing workload or priorities."
        else:
            return "Stable performance between periods."
    
    def export_to_json(self, report: dict, output_path: Path) -> bool:
        """Export report to JSON."""
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)
        return True
    
    def export_to_markdown(self, report: dict, output_path: Path) -> bool:
        """Export report to Markdown."""
        lines = []
        
        if "title" in report:
            lines.append(f"# {report['title']}\n")
        
        if "sections" in report:
            for section in report["sections"]:
                lines.append(f"## {section['heading']}\n")
                content = section["content"]
                if isinstance(content, list):
                    for item in content:
                        lines.append(f"- {item}")
                else:
                    lines.append(content)
                lines.append("")
        
        output_path.write_text("\n".join(lines))
        return True


@dataclass
class PatternInsightGenerator:
    """Generate insights from patterns."""
    
    def detect_productivity_patterns(self, work_sessions: list[dict]) -> dict:
        """Detect productivity patterns from work sessions."""
        hour_outputs: dict[int, list[int]] = {}
        
        for session in work_sessions:
            start = session.get("start")
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            
            if start is not None and hasattr(start, "hour"):
                hour = start.hour
            else:
                hour = 9
            output = session.get("output", 0)
            
            if hour not in hour_outputs:
                hour_outputs[hour] = []
            hour_outputs[hour].append(output)
        
        # Calculate average output per hour
        peak_hours = {}
        for hour, outputs in hour_outputs.items():
            peak_hours[hour] = sum(outputs) / len(outputs)
        
        return {
            "peak_hours": dict(sorted(peak_hours.items(), key=lambda x: x[1], reverse=True)[:3]),
            "pattern_type": "productivity_by_hour"
        }
    
    def identify_improvement_areas(self, metrics: dict) -> list[str]:
        """Identify areas for improvement based on metrics."""
        areas = []
        
        completion_rate = metrics.get("task_completion_rate", 1.0)
        if completion_rate < 0.7:
            areas.append("Task completion rate - consider better prioritization")
        
        on_time = metrics.get("on_time_delivery", 1.0)
        if on_time < 0.8:
            areas.append("On-time delivery - review estimation accuracy")
        
        focus_sessions = metrics.get("focus_sessions_per_day", 5)
        if focus_sessions < 3:
            areas.append("Focus sessions - try to increase deep work time")
        
        interruptions = metrics.get("interruptions_per_hour", 0)
        if interruptions > 3:
            areas.append("Interruptions - implement better focus protection")
        
        return areas
    
    def calculate_streaks(self, activity_log: list[dict]) -> dict:
        """Calculate activity streaks."""
        streaks: dict[str, dict] = {}
        
        # Group by activity type
        by_activity: dict[str, list[dict]] = {}
        for entry in activity_log:
            activity = entry.get("activity", "unknown")
            if activity not in by_activity:
                by_activity[activity] = []
            by_activity[activity].append(entry)
        
        # Calculate streaks for each activity
        for activity, entries in by_activity.items():
            # Sort by date
            entries.sort(key=lambda x: x.get("date", datetime.now()))
            
            current_streak = 0
            longest_streak = 0
            last_date = None
            
            for entry in entries:
                if entry.get("completed", False):
                    entry_date = entry.get("date")
                    if isinstance(entry_date, str):
                        entry_date = datetime.fromisoformat(entry_date)
                    
                    if last_date is None or (entry_date - last_date).days <= 1:
                        current_streak += 1
                        longest_streak = max(longest_streak, current_streak)
                    else:
                        current_streak = 1
                    
                    last_date = entry_date
                else:
                    current_streak = 0
            
            streaks[activity] = {
                "current": current_streak,
                "longest": longest_streak
            }
        
        return streaks


@dataclass
class PersonalizedInsightGenerator:
    """Generate personalized insights."""
    
    def personalize(self, insight: dict, user_profile: dict) -> dict:
        """Personalize insight for a specific user."""
        personalized = insight.copy()
        
        name = user_profile.get("name", "there")
        style = user_profile.get("preferences", {}).get("communication_style", "formal")
        
        content = insight.get("content", "")
        
        if style == "casual":
            personalized["content"] = f"Hey {name}! {content}"
        else:
            personalized["content"] = f"Dear {name}, {content}"
        
        personalized["personalized"] = True
        return personalized
    
    def select_tone(self, context: dict) -> str:
        """Select appropriate tone based on context."""
        stress = context.get("stress_level", "normal")
        celebration = context.get("celebration_worthy", False)
        
        if celebration:
            return "celebratory"
        elif stress == "high":
            return "supportive"
        elif stress == "low":
            return "encouraging"
        else:
            return "neutral"
