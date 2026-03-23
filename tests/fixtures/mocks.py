"""
Mock fixtures for testing.
"""

import pytest
from unittest.mock import Mock, MagicMock
import numpy as np


class MockQdrantClient:
    """Mock Qdrant client for testing."""

    def __init__(self):
        self.collections = {}
        self.vectors = {}
        # Wrap methods with MagicMock for call tracking
        self.create_collection = MagicMock(side_effect=self._create_collection)
        self.delete_collection = MagicMock(side_effect=self._delete_collection)
        self.collection_exists = MagicMock(side_effect=self._collection_exists)
        self.upsert = MagicMock(side_effect=self._upsert)
        self.search = MagicMock(side_effect=self._search)
        self.delete = MagicMock(side_effect=self._delete)
        # These methods can be overridden by tests
        self._retrieve_impl = self._retrieve
        self._count_impl = self._count
        self._scroll_impl = self._scroll
        self.retrieve = MagicMock(side_effect=lambda *args, **kwargs: self._retrieve_impl(*args, **kwargs))
        self.count = MagicMock(side_effect=lambda *args, **kwargs: self._count_impl(*args, **kwargs))
        self.scroll = MagicMock(side_effect=lambda *args, **kwargs: self._scroll_impl(*args, **kwargs))

    def _create_collection(self, collection_name: str, vectors_config) -> None:
        self.collections[collection_name] = {"vectors_config": vectors_config}
        self.vectors[collection_name] = {}

    def _delete_collection(self, collection_name: str) -> None:
        if collection_name in self.collections:
            del self.collections[collection_name]
            del self.vectors[collection_name]

    def _collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    def _upsert(self, collection_name: str, points) -> None:
        if collection_name not in self.vectors:
            self.vectors[collection_name] = {}
        for point in points:
            self.vectors[collection_name][point.id] = point

    def _search(self, collection_name: str, query_vector, limit: int = 10, score_threshold: float = 0.0, query_filter=None):
        results = []
        for i in range(min(limit, 2)):
            mock = Mock()
            mock.id = f"doc{i+1}"
            mock.score = 0.95 - (i * 0.1)
            mock.payload = {"text": f"result{i+1}"}
            results.append(mock)
        return results

    def _delete(self, collection_name: str, points_selector) -> None:
        if collection_name in self.vectors:
            for point_id in points_selector:
                if point_id in self.vectors[collection_name]:
                    del self.vectors[collection_name][point_id]

    def _retrieve(self, collection_name: str, ids: list):
        results = []
        for id in ids:
            if collection_name in self.vectors and id in self.vectors[collection_name]:
                results.append(self.vectors[collection_name][id])
            else:
                mock = Mock()
                mock.id = id
                mock.payload = {"text": "Test"}
                mock.vector = [0.1] * 384
                results.append(mock)
        return results

    def _count(self, collection_name: str):
        mock = Mock()
        mock.count = len(self.vectors.get(collection_name, {}))
        return mock

    def _scroll(self, collection_name: str, limit: int = 100, offset=None):
        vectors = self.vectors.get(collection_name, {})
        results = list(vectors.values())[:limit]
        return results, None


class MockEmbeddingModel:
    """Mock embedding model for testing."""

    def encode(self, texts):
        """Mock encode method."""
        if isinstance(texts, str):
            return np.array([0.1] * 384)
        return [np.array([0.1] * 384) for _ in texts]


@pytest.fixture
def mock_qdrant_client():
    """Provide a mock Qdrant client."""
    return MockQdrantClient()


@pytest.fixture
def mock_model():
    """Provide a mock embedding model."""
    return MockEmbeddingModel()
