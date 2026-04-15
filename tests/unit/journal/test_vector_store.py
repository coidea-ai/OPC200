"""Journal Vector Store tests - DISABLED (组件已移除，保留代码供参考)"""

import pytest

# 标记整个模块跳过 - Journal 组件已不在当前部署中
pytestmark = pytest.mark.skip(reason="Journal 组件已移除 (精简部署)，测试暂停")

# 保留原始导入和测试代码供参考
"""
from unittest.mock import patch, MagicMock
import pytest
from src.journal.vector_store import VectorStore, QdrantConnectionError


class TestVectorStore:
    def test_create_collection(self):
        ...

    def test_upsert_embedding(self):
        ...

    def test_upsert_multiple_embeddings(self):
        ...


class TestVectorStoreIndexing:
    def test_index_journal_entry(self):
        ...

    def test_batch_index_entries(self):
        ...

    def test_rebuild_index(self):
        ...


class TestVectorStoreBackup:
    def test_import_collection(self):
        ...
"""
