"""Digest generator - Swiss Army Knife style: minimal but complete."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class DigestGenerator:
    """Generate weekly digest from sessions."""

    def __init__(self, customer_id: str):
        self.base_path = Path(f"~/.openclaw/customers/{customer_id}/.remi").expanduser()

    def generate_weekly_digest(self, week_offset: int = 0) -> Optional[Path]:
        """Generate simple weekly digest."""
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday(), weeks=-week_offset)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Collect entries
        entries = []
        sessions_dir = self.base_path / "sessions"

        if not sessions_dir.exists():
            return None

        for file_path in sessions_dir.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if week_start <= file_date < week_end:
                    content = file_path.read_text(encoding="utf-8")
                    # Parse entries
                    for line in content.split("\n"):
                        if line.strip() and not line.startswith("#") and not line.startswith("---"):
                            entries.append((file_date.strftime("%m-%d"), line.strip()))
            except ValueError:
                continue

        if not entries:
            return None

        # Generate simple digest
        week_str = week_start.strftime("%Y-W%W")
        digests_dir = self.base_path / "digests"
        digests_dir.mkdir(exist_ok=True)
        digest_file = digests_dir / f"{week_str}.md"

        lines = [f"# Week {week_str} - {len(entries)} entries\n"]

        current_date = None
        for date, content in entries:
            if date != current_date:
                lines.append(f"\n## {date}")
                current_date = date
            lines.append(f"- {content[:80]}{'...' if len(content) > 80 else ''}")

        digest_file.write_text("\n".join(lines), encoding="utf-8")
        return digest_file
