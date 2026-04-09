"""Tests for recall module."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from remi_lite.recall import Recall


class TestRecall:
    """Test recall functionality."""

    @pytest.fixture
    def temp_customer_dir(self, tmp_path):
        """Create a temporary customer directory with sample data."""
        customer_dir = tmp_path / "customers" / "TEST-001"
        remi_dir = customer_dir / ".remi"
        sessions_dir = remi_dir / "sessions"
        sessions_dir.mkdir(parents=True)

        # Create sample session files
        (sessions_dir / "2026-04-02.md").write_text("""## 10:00

今天完成了数据库优化，从2秒降到200毫秒

## 14:00

开始设计用户界面，选择了 React
""")

        (sessions_dir / "2026-04-01.md").write_text("""## 09:00

遇到了数据库性能问题，查询很慢

## 16:00

调研了几种优化方案，决定用索引
""")

        (sessions_dir / "2026-03-28.md").write_text("""## 11:00

完成了用户登录功能，用了 JWT
""")

        return customer_dir

    @pytest.fixture
    def recall(self, temp_customer_dir):
        """Create a recall instance with temp directory."""
        remi_path = temp_customer_dir / ".remi"

        with patch("remi_lite.recall.Path") as mock_path:
            mock_path.return_value.expanduser.return_value = remi_path
            return Recall("TEST-001")

    def test_extract_keywords_removes_stopwords(self):
        """Test keyword extraction removes stopwords."""
        recall = Recall("TEST-001")

        keywords = recall._extract_keywords("我怎么优化数据库的？")

        assert "我" not in keywords
        assert "怎么" not in keywords
        assert "的" not in keywords
        assert "优化" in keywords
        assert "数据库" in keywords

    def test_parse_time_range_last_week(self):
        """Test parsing 'last week' time range."""
        recall = Recall("TEST-001")

        start, end = recall._parse_time_range("上周做了什么？", 30)

        assert (end - start).days == 7

    def test_parse_time_range_default(self):
        """Test parsing default time range."""
        recall = Recall("TEST-001")

        start, end = recall._parse_time_range("数据库优化", 30)

        assert (end - start).days == 30

    def test_search_finds_matching_content(self, recall, temp_customer_dir):
        """Test search finds matching content."""
        results = recall.search("数据库优化", days=30)

        assert len(results) > 0
        assert any("数据库优化" in r["content"] for r in results)

    def test_search_respects_date_range(self, recall, temp_customer_dir):
        """Test search respects date range."""
        # Search with narrow range (1 day)
        results = recall.search("数据库", days=1)

        # Should only find recent entries
        for r in results:
            date = datetime.strptime(r["date"], "%Y-%m-%d")
            assert (datetime.now() - date).days <= 1

    def test_search_returns_empty_for_no_match(self, recall):
        """Test search returns empty list for no matches."""
        results = recall.search("不存在的主题 xyz123", days=30)

        assert len(results) == 0

    def test_search_limits_results(self, recall, temp_customer_dir):
        """Test search limits number of results."""
        # Add many session files
        sessions_dir = temp_customer_dir / ".remi" / "sessions"
        for i in range(10):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            (sessions_dir / f"{date}.md").write_text(f"## 10:00\n\n数据库优化记录 {i}\n")

        results = recall.search("数据库", days=30)

        assert len(results) <= 5  # Max 5 results

    def test_format_response_single_result(self):
        """Test formatting single result."""
        recall = Recall("TEST-001")
        results = [{"date": "2026-04-02", "content": "今天完成了登录功能"}]

        response = recall.format_response(results, "登录功能")

        assert "找到了" in response
        assert "2026-04-02" in response
        assert "登录功能" in response

    def test_format_response_multiple_results(self):
        """Test formatting multiple results."""
        recall = Recall("TEST-001")
        results = [
            {"date": "2026-04-02", "content": "完成了登录功能"},
            {"date": "2026-04-01", "content": "开始设计登录"},
            {"date": "2026-03-31", "content": "调研登录方案"},
        ]

        response = recall.format_response(results, "登录")

        assert "找到 3 条相关记录" in response
        assert "1." in response
        assert "2." in response

    def test_format_response_no_results(self):
        """Test formatting empty results."""
        recall = Recall("TEST-001")

        response = recall.format_response([], "不存在的主题")

        assert "没记住" in response

    def test_extract_relevant_paragraphs_finds_matches(self):
        """Test extracting paragraphs containing keywords."""
        recall = Recall("TEST-001")
        content = """## 10:00

今天完成了数据库优化

## 14:00

处理了前端问题

## 16:00

数据库查询快了很多
"""

        paragraphs = recall._extract_relevant_paragraphs(content, ["数据库"])

        assert len(paragraphs) == 2
        assert any("优化" in p["content"] for p in paragraphs)
        assert any("查询" in p["content"] for p in paragraphs)
