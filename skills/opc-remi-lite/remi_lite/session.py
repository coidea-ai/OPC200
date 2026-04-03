"""Session summarizer module - L1: Auto-record valuable content."""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional


class SessionSummarizer:
    """Summarize and record session content.

    Automatically detects valuable content based on signals:
    - Time references (today, just now, morning)
    - Action words (completed, solved, encountered)
    - Emotion words (happy, anxious, confused)
    """

    # Signals that indicate valuable content
    RECORD_SIGNALS = [
        r"(今天|刚才|早上|上午|中午|下午|晚上)",  # Time reference alone
        r"(完成|解决|做了|遇到|优化|修改)",  # Action words alone
        r"(开心|高兴|兴奋|焦虑|困惑|担心|累|爽)",  # Emotion alone
        r"(决定|选择|放弃)",  # Decision words
    ]

    # Phrases to remove from recorded content
    CLEAN_PATTERNS = [
        r"^(帮我|请|麻烦)\s*",
        r"^(记录|记一下|记下来)\s*",
    ]

    def __init__(self, customer_id: str):
        """Initialize summarizer for a customer.

        Args:
            customer_id: Unique customer identifier
        """
        self.customer_id = customer_id
        self.base_path = Path(f"~/.openclaw/customers/{customer_id}/.remi").expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def summarize_turn(
        self, user_msg: str, assistant_msg: str = "", context: Optional[dict] = None
    ) -> Optional[str]:
        """Summarize a conversation turn.

        Args:
            user_msg: User's message
            assistant_msg: Assistant's response (optional)
            context: Additional context (optional)

        Returns:
            Extracted summary if valuable, None otherwise
        """
        summary = self._extract_summary(user_msg, assistant_msg)

        if summary:
            self._append_to_session(summary)

        return summary

    def _extract_summary(self, user_msg: str, assistant_msg: str) -> Optional[str]:
        """Extract summary from user message.

        Uses heuristic signals to detect valuable content.
        No LLM call - fast and deterministic.
        """
        text_lower = user_msg.lower()

        # Check for recording signals
        has_value = any(re.search(pattern, text_lower) for pattern in self.RECORD_SIGNALS)

        if not has_value:
            return None

        # Clean and truncate
        content = self._clean_content(user_msg)
        content = content[:200]  # Max 200 chars

        return content.strip() if content else None

    def _clean_content(self, text: str) -> str:
        """Remove polite phrases and clean content."""
        for pattern in self.CLEAN_PATTERNS:
            text = re.sub(pattern, "", text)
        return text.strip()

    def _append_to_session(self, summary: str) -> None:
        """Append summary to today's session file with deduplication."""
        today = datetime.now().strftime("%Y-%m-%d")
        sessions_dir = self.base_path / "sessions"
        sessions_dir.mkdir(exist_ok=True)

        session_file = sessions_dir / f"{today}.md"

        # Check for duplicates in recent entries (last 5 minutes)
        if self._is_duplicate(summary, session_file):
            return

        timestamp = datetime.now().strftime("%H:%M")
        entry = f"## {timestamp}\n\n{summary}\n\n---\n\n"

        with open(session_file, "a", encoding="utf-8") as f:
            f.write(entry)

    def _is_duplicate(self, summary: str, session_file: Path) -> bool:
        """Check if summary is a duplicate of recent entries."""
        if not session_file.exists():
            return False

        content = session_file.read_text(encoding="utf-8")
        # Extract recent entries (last 3)
        entries = content.split("---\n\n")[-4:-1]  # Skip empty last element

        for entry in entries:
            # Extract content after timestamp header (skip empty lines)
            lines = entry.strip().split("\n")
            for i, line in enumerate(lines):
                if line.startswith("## "):
                    # Find next non-empty line
                    for j in range(i + 1, len(lines)):
                        entry_text = lines[j].strip()
                        if entry_text:
                            if self._similarity(summary, entry_text) > 0.8:
                                return True
                            break

        return False

    def _similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using character overlap for Chinese."""
        # Use character sets for Chinese text
        chars1 = set(text1.lower())
        chars2 = set(text2.lower())

        # Remove common punctuation and whitespace
        chars1 = {c for c in chars1 if c.strip() and not c.isspace()}
        chars2 = {c for c in chars2 if c.strip() and not c.isspace()}

        if not chars1 or not chars2:
            return 0.0

        intersection = chars1 & chars2
        union = chars1 | chars2

        return len(intersection) / len(union)

    def _get_session_files(self, days: int = 30) -> list:
        """Get list of session files within date range.

        Returns:
            List of Path objects, sorted by date
        """
        sessions_dir = self.base_path / "sessions"
        if not sessions_dir.exists():
            return []

        cutoff = datetime.now() - __import__("datetime").timedelta(days=days)
        files = []

        for file_path in sessions_dir.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if file_date >= cutoff:
                    files.append(file_path)
            except ValueError:
                continue

        return sorted(files)
