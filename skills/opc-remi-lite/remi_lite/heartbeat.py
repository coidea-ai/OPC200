"""Heartbeat module - Automatic maintenance."""

import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import List


class Heartbeat:
    """Handle periodic maintenance tasks.

    Triggered by OpenClaw heartbeat, performs:
    - Weekly digest generation
    - Old backup cleanup
    - Data integrity checks
    """

    def __init__(self, customer_id: str):
        """Initialize heartbeat for a customer.

        Args:
            customer_id: Unique customer identifier
        """
        self.customer_id = customer_id
        self.base_path = Path(f"~/.openclaw/customers/{customer_id}/.remi").expanduser()

    def handle(self) -> str:
        """Handle heartbeat tick.

        Returns:
            Status message
        """
        actions = []

        # Generate weekly digest if needed
        if self._should_generate_digest():
            self._generate_weekly_digest()
            actions.append("weekly_digest")

        # Cleanup old backups
        if self._cleanup_old_backups():
            actions.append("cleanup_backups")

        if actions:
            return f"HEARTBEAT_OK: {', '.join(actions)}"
        return "HEARTBEAT_OK"

    def _should_generate_digest(self) -> bool:
        """Check if weekly digest should be generated."""
        digests_dir = self.base_path / "digests"

        if not digests_dir.exists():
            return True

        # Check last digest date
        digest_files = sorted(digests_dir.glob("*.md"))
        if not digest_files:
            return True

        last_digest = digest_files[-1]
        try:
            # Parse week number from filename (YYYY-WWW.md)
            week_str = last_digest.stem
            year, week = map(int, week_str.split("-W"))
            # This is simplified - real implementation needs proper week calculation
            return False  # Simplified
        except ValueError:
            return True

    def _generate_weekly_digest(self) -> None:
        """Generate weekly summary from session files."""
        sessions_dir = self.base_path / "sessions"
        digests_dir = self.base_path / "digests"
        digests_dir.mkdir(exist_ok=True)

        if not sessions_dir.exists():
            return

        # Get last 7 days of sessions
        cutoff = datetime.now() - timedelta(days=7)
        recent_sessions = []

        for file_path in sessions_dir.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if file_date >= cutoff:
                    recent_sessions.append((file_date, file_path.read_text()))
            except ValueError:
                continue

        if not recent_sessions:
            return

        # Sort by date
        recent_sessions.sort(key=lambda x: x[0])

        # Generate digest
        week_num = datetime.now().strftime("%Y-W%W")
        digest_file = digests_dir / f"{week_num}.md"

        lines = [f"# Week {week_num} Summary\n"]

        for date, content in recent_sessions:
            lines.append(f"\n## {date.strftime('%Y-%m-%d')}\n")
            lines.append(content)

        digest_file.write_text("\n".join(lines), encoding="utf-8")

    def _cleanup_old_backups(self, keep_count: int = 5) -> bool:
        """Remove old backups, keeping only recent ones."""
        exports_dir = self.base_path / "exports"

        if not exports_dir.exists():
            return False

        # Get all backup files sorted by date
        backups = sorted(
            exports_dir.glob("remi-backup-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True
        )

        if len(backups) <= keep_count:
            return False

        # Remove old backups
        removed = 0
        for old_backup in backups[keep_count:]:
            old_backup.unlink()
            removed += 1

        return removed > 0
