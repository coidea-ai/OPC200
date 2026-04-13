"""Visualization - Swiss Army Knife style: heatmap only."""

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict


class Visualizer:
    """Generate text-based activity heatmap."""

    HEATMAP_CHARS = ["·", "░", "▒", "▓", "█"]

    def __init__(self, customer_id: str):
        self.base_path = Path(f"~/.openclaw/customers/{customer_id}/.remi").expanduser()

    def generate_activity_heatmap(self, days: int = 30) -> str:
        """Generate simple activity heatmap."""
        activity = self._get_daily_activity(days)

        if not activity:
            return "暂无数据"

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        lines = ["活动热力图 (最近 {} 天)".format(days), ""]
        lines.append("    一  二  三  四  五  六  日 ")

        # Find first Monday
        current = start_date
        while current.weekday() != 0:
            current -= timedelta(days=1)

        max_activity = max(activity.values()) if activity else 1
        max_activity = max(max_activity, 1)

        # Build 5 weeks
        for week in range(5):
            week_row = []
            for day in range(7):
                date_key = current.strftime("%Y-%m-%d")
                count = activity.get(date_key, 0)

                if count == 0:
                    char = self.HEATMAP_CHARS[0]
                else:
                    intensity = min(count / max(max_activity * 0.3, 1), 1.0)
                    idx = int(intensity * (len(self.HEATMAP_CHARS) - 1))
                    char = self.HEATMAP_CHARS[idx]

                week_row.append(char)
                current += timedelta(days=1)

            week_num = (start_date + timedelta(weeks=week)).strftime("W%W")
            lines.append(f"{week_num}  " + "  ".join(week_row))

        lines.append("\n图例: " + " ".join(self.HEATMAP_CHARS) + " = 无 → 高")
        return "\n".join(lines)

    def _get_daily_activity(self, days: int) -> Dict[str, int]:
        """Get daily activity counts."""
        activity = defaultdict(int)
        sessions_dir = self.base_path / "sessions"

        if not sessions_dir.exists():
            return activity

        cutoff = datetime.now() - timedelta(days=days)

        for file_path in sessions_dir.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if file_date >= cutoff:
                    content = file_path.read_text(encoding="utf-8")
                    # Count entries by counting timestamp headers
                    count = content.count("\n## ")
                    activity[file_path.stem] = max(count, 1)  # At least 1 if file exists
            except ValueError:
                continue

        return activity
