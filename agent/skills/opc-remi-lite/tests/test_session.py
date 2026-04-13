"""Tests for session summarizer module."""

import re
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from remi_lite.session import SessionSummarizer


class TestSessionSummarizer:
    """Test session summarizer functionality."""

    @pytest.fixture
    def temp_customer_dir(self, tmp_path):
        """Create a temporary customer directory."""
        customer_dir = tmp_path / "customers" / "TEST-001"
        customer_dir.mkdir(parents=True)
        return customer_dir

    @pytest.fixture
    def summarizer(self, temp_customer_dir):
        """Create a summarizer with temp directory."""
        with patch("remi_lite.session.Path") as mock_path:
            mock_path.return_value.expanduser.return_value = temp_customer_dir / ".remi"
            return SessionSummarizer("TEST-001")

    def test_init_creates_directory(self, temp_customer_dir):
        """Test that initialization creates the .remi directory."""
        remi_path = temp_customer_dir / ".remi"

        with patch("remi_lite.session.Path") as mock_path:
            mock_path.return_value.expanduser.return_value = remi_path
            SessionSummarizer("TEST-001")

        assert remi_path.exists()

    def test_extract_summary_with_time_signal(self):
        """Test extraction of time-based signals."""
        summarizer = SessionSummarizer("TEST-001")

        test_cases = [
            ("今天完成了登录功能", True),
            ("刚才解决了数据库问题", True),
            ("早上优化了查询", True),
            ("hello world", False),  # 无信号
            ("你觉得怎么样？", False),  # 疑问句
            ("完成了", True),  # 动作信号
        ]

        for text, should_record in test_cases:
            result = summarizer._extract_summary(text, "")
            has_value = result is not None
            assert has_value == should_record, f"Failed for: {text}"

    def test_extract_summary_with_emotion_signal(self):
        """Test extraction of emotion-based signals."""
        summarizer = SessionSummarizer("TEST-001")

        test_cases = [
            ("很开心完成了这个功能", True),
            ("有点焦虑，进度落后了", True),
            ("困惑于这个设计", True),
        ]

        for text, should_record in test_cases:
            result = summarizer._extract_summary(text, "")
            has_value = result is not None
            assert has_value == should_record

    def test_extract_summary_cleans_content(self):
        """Test that extracted content is cleaned."""
        summarizer = SessionSummarizer("TEST-001")

        # 去掉客套话
        result = summarizer._extract_summary("帮我记录一下今天完成了登录功能", "")
        assert "帮我" not in result
        assert "记录" not in result
        assert "完成了登录功能" in result

    def test_extract_summary_truncates_long_content(self):
        """Test that long content is truncated."""
        summarizer = SessionSummarizer("TEST-001")

        long_text = "今天" + "x" * 500
        result = summarizer._extract_summary(long_text, "")

        assert len(result) <= 200

    def test_append_to_session_creates_file(self, summarizer, temp_customer_dir):
        """Test that appending creates session file."""
        summary = "今天完成了登录功能"

        summarizer._append_to_session(summary)

        today = datetime.now().strftime("%Y-%m-%d")
        session_file = temp_customer_dir / ".remi" / "sessions" / f"{today}.md"

        assert session_file.exists()
        content = session_file.read_text()
        assert summary in content
        assert "## " in content  # Has timestamp header

    def test_append_appends_to_existing_file(self, summarizer, temp_customer_dir):
        """Test that appending adds to existing file."""
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = temp_customer_dir / ".remi" / "sessions" / f"{today}.md"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        session_file.write_text("## 10:00\n\n之前的记录\n\n")

        summarizer._append_to_session("新的记录")

        content = session_file.read_text()
        assert "之前的记录" in content
        assert "新的记录" in content

    def test_summarize_turn_returns_none_for_chat(self):
        """Test that chat messages return None (not recorded)."""
        summarizer = SessionSummarizer("TEST-001")

        result = summarizer.summarize_turn("你好", "你好！有什么可以帮你的？")
        assert result is None

    def test_summarize_turn_records_valuable_content(self, summarizer, temp_customer_dir):
        """Test that valuable content is recorded."""
        result = summarizer.summarize_turn(
            "今天完成了数据库优化，从2秒降到200毫秒", "太棒了！怎么做到的？"
        )

        assert result is not None
        assert "数据库优化" in result

        # Verify file was written
        today = datetime.now().strftime("%Y-%m-%d")
        session_file = temp_customer_dir / ".remi" / "sessions" / f"{today}.md"
        assert session_file.exists()

    def test_get_session_files_returns_sorted_list(self, summarizer, temp_customer_dir):
        """Test getting list of session files."""
        sessions_dir = temp_customer_dir / ".remi" / "sessions"
        sessions_dir.mkdir(parents=True)

        # Create test files
        (sessions_dir / "2026-04-01.md").write_text("Day 1")
        (sessions_dir / "2026-04-02.md").write_text("Day 2")
        (sessions_dir / "2026-03-31.md").write_text("Day 0")

        files = summarizer._get_session_files(days=30)

        assert len(files) == 3
        # Should be sorted by date
        assert files[0].stem == "2026-03-31"
        assert files[2].stem == "2026-04-02"
