"""Tests for core coordination module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from remi_lite.core import RemiLite


class TestRemiLite:
    """Test RemiLite core functionality."""

    @pytest.fixture
    def temp_customer_dir(self, tmp_path):
        """Create a temporary customer directory."""
        customer_dir = tmp_path / "customers" / "TEST-001"
        (customer_dir / ".remi" / "sessions").mkdir(parents=True)
        (customer_dir / ".remi" / "exports").mkdir(parents=True)
        return customer_dir

    @pytest.fixture
    def remi(self, temp_customer_dir):
        """Create a RemiLite instance with mocked dependencies."""
        remi_path = temp_customer_dir / ".remi"

        with patch("remi_lite.core.Path") as mock_path:
            mock_path.return_value.expanduser.return_value = remi_path
            return RemiLite("TEST-001")

    def test_hear_records_valuable_content(self, remi):
        """Test that valuable content is recorded."""
        with patch.object(remi.summarizer, "summarize_turn") as mock_summarize:
            mock_summarize.return_value = "完成了数据库优化"

            response = remi.hear("今天完成了数据库优化")

            assert "👍 记住了" in response
            mock_summarize.assert_called_once()

    def test_hear_returns_none_for_chat(self, remi):
        """Test that chat returns None (let OpenClaw handle)."""
        with patch.object(remi.summarizer, "summarize_turn") as mock_summarize:
            mock_summarize.return_value = None

            response = remi.hear("你好")

            assert response is None

    def test_hear_queries_with_question_words(self, remi):
        """Test that questions trigger search."""
        with patch.object(remi.recall, "search") as mock_search:
            mock_search.return_value = [{"date": "2026-04-02", "content": "完成了登录"}]

            with patch.object(remi.recall, "format_response") as mock_format:
                mock_format.return_value = "找到了！完成了登录"

                response = remi.hear("我登录功能怎么做的？")

                mock_search.assert_called_once()
                assert response == "找到了！完成了登录"

    def test_hear_queries_with_how(self, remi):
        """Test 'how' queries."""
        with patch.object(remi.recall, "search") as mock_search:
            mock_search.return_value = []

            with patch.object(remi.recall, "format_response") as mock_format:
                mock_format.return_value = "没记住"

                response = remi.hear("怎么优化数据库的？")

                mock_search.assert_called_once()

    def test_handle_command_backup(self, remi):
        """Test /remi backup command."""
        with patch.object(remi.backup, "create") as mock_create:
            mock_create.return_value = {
                "success": True,
                "filename": "remi-backup-2026-04-02.zip",
                "size_kb": 45,
                "stats": {"sessions": 5},
            }

            response = remi.hear("/remi backup")

            mock_create.assert_called_once()
            assert "📦 备份已生成" in response
            assert "remi-backup" in response

    def test_handle_command_status(self, remi):
        """Test /remi status command."""
        response = remi.hear("/remi status")

        assert "📊 Remi 状态" in response
        assert "会话记录" in response
        assert "备份文件" in response

    def test_handle_command_unknown(self, remi):
        """Test unknown command."""
        response = remi.hear("/remi unknown_command")

        assert "未知命令" in response

    def test_handle_command_imports(self, remi):
        """Test /remi imports command."""
        with patch.object(remi.backup, "list_importable") as mock_list:
            mock_list.return_value = [
                {"filename": "remi-backup-2026-04-02.zip", "size_kb": 45},
                {"filename": "remi-backup-2026-03-28.zip", "size_kb": 38},
            ]

            response = remi.hear("/remi imports")

            mock_list.assert_called_once()
            assert "备份" in response
            assert "remi-backup-2026-04-02.zip" in response

    def test_handle_command_import(self, remi):
        """Test /remi import command."""
        with patch.object(remi.backup, "restore") as mock_restore:
            mock_restore.return_value = {
                "success": True,
                "restored_from": "remi-backup-2026-03-28.zip",
                "safety_backup": "safety-xxx.zip",
            }

            response = remi.hear("/remi import remi-backup-2026-03-28.zip")

            mock_restore.assert_called_once_with("remi-backup-2026-03-28.zip")
            assert "✅ 已恢复" in response

    def test_hear_with_context(self, remi):
        """Test hearing with context."""
        with patch.object(remi.summarizer, "summarize_turn") as mock_summarize:
            mock_summarize.return_value = "记录内容"

            context = {"session_id": "sess-123", "timestamp": "2026-04-02T10:00:00"}
            response = remi.hear("今天完成了任务", context)

            mock_summarize.assert_called_once_with("今天完成了任务", "", context)

    def test_intent_detection_record(self, remi):
        """Test intent detection for recording."""
        # 这些应该被识别为记录意图
        record_inputs = [
            "今天完成了登录功能",
            "刚才解决了数据库问题",
            "很开心完成了这个功能",
        ]

        for text in record_inputs:
            intent = remi._detect_intent(text)
            assert intent == "record", f"Failed for: {text}"

    def test_intent_detection_query(self, remi):
        """Test intent detection for queries."""
        query_inputs = [
            "我登录功能怎么做的？",
            "之前数据库怎么优化的？",
            "怎么解决这个问题的？",
        ]

        for text in query_inputs:
            intent = remi._detect_intent(text)
            assert intent == "query", f"Failed for: {text}"

    def test_intent_detection_command(self, remi):
        """Test intent detection for commands."""
        command_inputs = [
            "/remi backup",
            "/remi status",
            "/remi imports",
        ]

        for text in command_inputs:
            intent = remi._detect_intent(text)
            assert intent == "command", f"Failed for: {text}"

    def test_intent_detection_chat(self, remi):
        """Test intent detection for chat."""
        chat_inputs = [
            "你好",
            "谢谢",
            "哈哈",
        ]

        for text in chat_inputs:
            intent = remi._detect_intent(text)
            assert intent == "chat", f"Failed for: {text}"
