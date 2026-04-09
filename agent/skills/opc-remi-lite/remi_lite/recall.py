"""Recall module - L2: Natural language memory retrieval."""

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple


class Recall:
    """Retrieve memories using natural language queries.

    Simple text-based search - no complex indexing.
    Suitable for small to medium data volumes (<1000 entries).
    """

    # Common Chinese stopwords to remove
    STOPWORDS = {
        "我",
        "你",
        "的",
        "了",
        "是",
        "在",
        "有",
        "和",
        "就",
        "不",
        "人",
        "都",
        "一",
        "一个",
        "上",
        "也",
        "很",
        "到",
        "说",
        "要",
        "去",
        "你",
        "会",
        "着",
        "没有",
        "看",
        "好",
        "自己",
        "这",
        "那",
        "怎么",
        "什么",
        "为什么",
        "哪里",
        "哪个",
        "那些",
        "这些",
        "这个",
        "那个",
        "时候",
        "之前",
        "上次",
        "曾经",
    }

    def __init__(self, customer_id: str):
        """Initialize recall for a customer.

        Args:
            customer_id: Unique customer identifier
        """
        self.customer_id = customer_id
        self.base_path = Path(f"~/.openclaw/customers/{customer_id}/.remi").expanduser()

    def search(self, query: str, days: int = 30) -> List[dict]:
        """Search memories matching query.

        Args:
            query: Natural language query
            days: How many days back to search

        Returns:
            List of matching memory entries, sorted by date (newest first)
        """
        keywords = self._extract_keywords(query)
        date_range = self._parse_time_range(query, days)

        results = []
        for session_file in self._get_session_files(date_range):
            content = session_file.read_text(encoding="utf-8")

            # Check if any keyword matches
            if any(kw in content.lower() for kw in keywords):
                paragraphs = self._extract_relevant_paragraphs(content, keywords)
                results.extend(paragraphs)

        # Sort by date (newest first) and limit
        results.sort(key=lambda x: x["date"], reverse=True)
        return results[:5]  # Max 5 results

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from query."""
        # Extract Chinese phrases and English words
        words = re.findall(r"[\u4e00-\u9fff]+|[a-zA-Z]+", query.lower())

        # For Chinese text, also extract substrings to improve matching
        all_keywords = []
        for word in words:
            if len(word) <= 1:
                continue
            if word not in self.STOPWORDS:
                all_keywords.append(word)
            # For longer Chinese phrases, also add substrings
            if len(word) >= 2:
                for i in range(len(word) - 1):
                    for j in range(i + 2, min(i + 5, len(word) + 1)):
                        substr = word[i:j]
                        if substr not in self.STOPWORDS and substr not in all_keywords:
                            all_keywords.append(substr)

        return all_keywords

    def _parse_time_range(self, query: str, default_days: int) -> Tuple[datetime, datetime]:
        """Parse time range from query."""
        end = datetime.now()

        # Check for specific time references
        if "上周" in query or "last week" in query.lower():
            start = end - timedelta(days=7)
        elif "上周" in query or "last week" in query.lower():
            start = end - timedelta(days=7)
        elif "上个月" in query or "last month" in query.lower():
            start = end - timedelta(days=30)
        elif "昨天" in query or "yesterday" in query.lower():
            start = end - timedelta(days=1)
        elif "前天" in query:
            start = end - timedelta(days=2)
        else:
            start = end - timedelta(days=default_days)

        return (start, end)

    def _get_session_files(self, date_range: Tuple[datetime, datetime]) -> List[Path]:
        """Get session files within date range."""
        sessions_dir = self.base_path / "sessions"
        if not sessions_dir.exists():
            return []

        start, end = date_range
        files = []

        for file_path in sessions_dir.glob("*.md"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d")
                if start <= file_date <= end:
                    files.append(file_path)
            except ValueError:
                continue

        return sorted(files)

    def _extract_relevant_paragraphs(self, content: str, keywords: List[str]) -> List[dict]:
        """Extract paragraphs containing keywords."""
        paragraphs = []
        current_date = None

        for line in content.split("\n"):
            # Extract date from header
            if line.startswith("## "):
                # This is a timestamp, date is in filename
                continue

            # Check if line contains any keyword
            if any(kw in line.lower() for kw in keywords):
                # Extract date from filename (we need to pass it in)
                paragraphs.append(
                    {
                        "date": self._extract_date_from_content(content),
                        "content": line.strip(),
                    }
                )

        return paragraphs

    def _extract_date_from_content(self, content: str) -> str:
        """Extract date from content header or return today."""
        # This is a simplified version - in practice, we'd track the filename
        lines = content.split("\n")
        for line in lines:
            if line.startswith("# ") and "20" in line:
                # Try to extract date
                match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
                if match:
                    return match.group(1)
        return datetime.now().strftime("%Y-%m-%d")

    def format_response(self, results: List[dict], query: str) -> str:
        """Format search results as natural language response.

        Args:
            results: List of memory entries
            query: Original query

        Returns:
            Formatted response string
        """
        if not results:
            return "我好像没记住这个。要不你现在讲讲？"

        if len(results) == 1:
            r = results[0]
            return f"找到了！{r['date']} 你说：{r['content'][:150]}..."

        response = f"找到 {len(results)} 条相关记录：\n\n"
        for i, r in enumerate(results[:3], 1):
            content_preview = r["content"][:80]
            response += f"{i}. **{r['date']}** - {content_preview}...\n"

        if len(results) > 3:
            response += f"\n...还有 {len(results)-3} 条，要我展开吗？"

        return response
