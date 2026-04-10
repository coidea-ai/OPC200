"""
PLAT-003: 指标推送协议定义测试
TDD: 先写测试，再写实现
"""
import pytest
import os
import re


class TestMetricsProtocolDocument:
    """测试指标推送协议文档存在且完整."""
    
    @pytest.fixture
    def protocol_doc(self):
        """读取协议文档内容."""
        doc_path = "docs/METRICS_PROTOCOL.md"
        if not os.path.exists(doc_path):
            pytest.fail(f"协议文档不存在: {doc_path}")
        with open(doc_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def test_protocol_document_exists(self):
        """测试协议文档存在."""
        assert os.path.exists("docs/METRICS_PROTOCOL.md"), "METRICS_PROTOCOL.md 不存在"
    
    def test_protocol_has_endpoint_section(self, protocol_doc):
        """测试文档包含 Endpoint 规范章节."""
        assert "## Endpoint" in protocol_doc or "## 推送地址" in protocol_doc, "缺少 Endpoint 章节"
        # 应该包含推送 URL 模板
        assert "/metrics/job/" in protocol_doc, "缺少推送 URL 模板"
    
    def test_protocol_has_authentication_section(self, protocol_doc):
        """测试文档包含认证章节."""
        assert "## 认证" in protocol_doc or "## Authentication" in protocol_doc, "缺少认证章节"
        # 应该提到 Bearer Token
        assert "Bearer" in protocol_doc or "bearer" in protocol_doc.lower(), "缺少 Bearer Token 说明"
    
    def test_protocol_has_metrics_format_section(self, protocol_doc):
        """测试文档包含指标格式章节."""
        assert "## 指标格式" in protocol_doc or "## Metrics Format" in protocol_doc, "缺少指标格式章节"
        # 应该提到 Prometheus text format
        assert "text/plain" in protocol_doc or "Prometheus" in protocol_doc, "缺少格式说明"
    
    def test_protocol_has_standard_labels(self, protocol_doc):
        """测试文档定义了标准 Labels."""
        # 应该包含这些标准 labels
        required_labels = ["tenant_id", "agent_version", "os"]
        for label in required_labels:
            assert label in protocol_doc, f"缺少标准 label: {label}"
    
    def test_protocol_has_standard_metrics(self, protocol_doc):
        """测试文档定义了标准指标."""
        required_metrics = ["agent_health", "cpu_usage", "memory_usage", "disk_usage"]
        for metric in required_metrics:
            assert metric in protocol_doc, f"缺少标准指标: {metric}"
    
    def test_protocol_has_error_handling(self, protocol_doc):
        """测试文档包含错误处理和重试策略."""
        assert "## 错误处理" in protocol_doc or "## Error Handling" in protocol_doc or "重试" in protocol_doc, "缺少错误处理章节"
    
    def test_protocol_has_single_and_batch_examples(self, protocol_doc):
        """测试文档包含单条和批量推送示例."""
        # 应该有 curl 示例
        assert "curl" in protocol_doc, "缺少 curl 示例"
        # 应该提到批量或 batch
        assert "批量" in protocol_doc or "batch" in protocol_doc.lower() or "多条" in protocol_doc, "缺少批量推送说明"
    
    def test_protocol_has_python_example(self, protocol_doc):
        """测试文档包含 Python 示例代码."""
        assert "```python" in protocol_doc or "python" in protocol_doc.lower(), "缺少 Python 示例"
    
    def test_protocol_has_offline_caching_mentioned(self, protocol_doc):
        """测试文档提到离线缓存机制（待协商）."""
        # 这个可能是待定项，但应该被提及
        assert "离线" in protocol_doc or "cache" in protocol_doc.lower() or "缓存" in protocol_doc or "TODO" in protocol_doc, "缺少离线缓存说明（或 TODO 标记）"


class TestProtocolForAgentTeam:
    """测试协议对 Agent 团队的可用性."""
    
    def test_protocol_location_documented(self):
        """测试协议文档位置在协作板中有记录."""
        # 检查 TASK_BOARD.md 是否引用了协议文档
        if os.path.exists("docs/TASK_BOARD.md"):
            with open("docs/TASK_BOARD.md", 'r', encoding='utf-8') as f:
                task_board = f.read()
            assert "METRICS_PROTOCOL" in task_board or "PLAT-003" in task_board, "TASK_BOARD.md 未引用协议文档"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
