"""
Unit tests for journal/vector_store.py - Qdrant vector store integration.
Following TDD: Red-Green-Refactor cycle.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.qdrant]


class TestVectorStore:
    """Tests for vector store functionality."""

    def test_vector_store_initialization(self):
        """Test vector store initialization."""
        # Arrange & Act
        from src.journal.vector_store import VectorStore

        store = VectorStore(host="localhost", port=6333, collection_name="test_journal")

        # Assert
        assert store.host == "localhost"
        assert store.port == 6333
        assert store.collection_name == "test_journal"

    def test_connect_to_qdrant(self, mock_qdrant_client):
        """Test connecting to Qdrant server."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
        )

        # Act
        with patch("src.journal.vector_store.QdrantClient", return_value=mock_qdrant_client):
            result = store.connect()

        # Assert
        assert result is True
        assert store.client is not None

    def test_create_collection(self, mock_qdrant_client):
        """Test creating a vector collection."""
        # Arrange
        from src.journal.vector_store import VectorStore
        from qdrant_client.models import Distance, VectorParams

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client
        mock_qdrant_client.create_collection.return_value = None

        # Act
        result = store.create_collection(vector_size=384)

        # Assert
        assert result is True
        mock_qdrant_client.create_collection.assert_called_once()

        # Verify the call arguments
        call_kwargs = mock_qdrant_client.create_collection.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_collection"
        vectors_config = call_kwargs["vectors_config"]
        assert isinstance(vectors_config, VectorParams)
        assert vectors_config.size == 384
        assert vectors_config.distance == Distance.COSINE

    def test_delete_collection(self, mock_qdrant_client):
        """Test deleting a vector collection."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        # Act
        result = store.delete_collection()

        # Assert
        assert result is True
        mock_qdrant_client.delete_collection.assert_called_once_with("test_collection")

        # Verify no other methods were called
        mock_qdrant_client.create_collection.assert_not_called()
        mock_qdrant_client.upsert.assert_not_called()

    def test_collection_exists(self, mock_qdrant_client):
        """Test checking if collection exists."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client
        mock_qdrant_client.collection_exists.return_value = True

        # Act
        result = store.collection_exists()

        # Assert
        assert result is True
        mock_qdrant_client.collection_exists.assert_called_once_with("test_collection")

    def test_upsert_embedding(self, mock_qdrant_client, sample_embedding):
        """Test upserting a single embedding."""
        # Arrange
        from src.journal.vector_store import VectorStore
        from qdrant_client.models import PointStruct

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        # Act
        result = store.upsert(id="doc1", vector=sample_embedding, payload={"text": "Test document"})

        # Assert
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()

        # Verify call arguments
        call_kwargs = mock_qdrant_client.upsert.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_collection"
        points = call_kwargs["points"]
        assert len(points) == 1
        assert isinstance(points[0], PointStruct)
        assert points[0].id == "doc1"
        assert points[0].vector == sample_embedding
        assert points[0].payload == {"text": "Test document"}

    def test_upsert_multiple_embeddings(self, mock_qdrant_client, sample_embeddings):
        """Test upserting multiple embeddings."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        points = [{"id": f"doc{i}", "vector": vec, "payload": {"text": f"Doc {i}"}} for i, vec in enumerate(sample_embeddings)]

        # Act
        result = store.upsert_batch(points)

        # Assert
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()

    def test_search_similar(self, mock_qdrant_client, sample_embedding):
        """Test searching for similar vectors."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        # Act
        results = store.search(vector=sample_embedding, limit=5, score_threshold=0.7)

        # Assert
        assert len(results) == 2
        assert all(hasattr(r, "score") for r in results)
        mock_qdrant_client.search.assert_called_once()

        # Verify search parameters
        call_kwargs = mock_qdrant_client.search.call_args.kwargs
        assert call_kwargs["collection_name"] == "test_collection"
        assert call_kwargs["query_vector"] == sample_embedding
        assert call_kwargs["limit"] == 5
        assert call_kwargs["score_threshold"] == 0.7
        assert call_kwargs["query_filter"] is None

        # Verify call count
        assert mock_qdrant_client.search.call_count == 1

    def test_search_with_filter(self, mock_qdrant_client, sample_embedding):
        """Test searching with payload filter."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        filter_condition = {"must": [{"key": "tag", "match": {"value": "important"}}]}

        # Act
        results = store.search(vector=sample_embedding, query_filter=filter_condition, limit=10)

        # Assert
        assert len(results) == 2
        mock_qdrant_client.search.assert_called_once()

    def test_delete_by_id(self, mock_qdrant_client):
        """Test deleting a vector by ID."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        # Act
        result = store.delete_by_id("doc1")

        # Assert
        assert result is True
        mock_qdrant_client.delete.assert_called_once()

    def test_delete_by_filter(self, mock_qdrant_client):
        """Test deleting vectors by filter."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        filter_condition = {"must": [{"key": "status", "match": {"value": "archived"}}]}

        # Act
        result = store.delete_by_filter(filter_condition)

        # Assert
        assert result is True
        mock_qdrant_client.delete.assert_called_once()

    def test_get_by_id(self, mock_qdrant_client):
        """Test retrieving a vector by ID."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client
        mock_qdrant_client.retrieve.return_value = [Mock(id="doc1", payload={"text": "Test"})]

        # Act
        result = store.get_by_id("doc1")

        # Assert
        assert result is not None
        assert result.id == "doc1"
        mock_qdrant_client.retrieve.assert_called_once()

    def test_count_vectors(self, mock_qdrant_client):
        """Test counting vectors in collection."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client
        mock_qdrant_client.count.return_value = Mock(count=100)

        # Act
        result = store.count()

        # Assert
        assert result == 100
        mock_qdrant_client.count.assert_called_once()

    def test_scroll_vectors(self, mock_qdrant_client):
        """Test scrolling through vectors."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client
        mock_qdrant_client.scroll.return_value = ([Mock(id="doc1"), Mock(id="doc2")], "next_page_token")

        # Act
        results, next_page = store.scroll(limit=2)

        # Assert
        assert len(results) == 2
        assert next_page == "next_page_token"
        mock_qdrant_client.scroll.assert_called_once()


class TestEmbeddingGenerator:
    """Tests for embedding generation."""

    def test_embedding_generator_initialization(self):
        """Test embedding generator initialization."""
        # Arrange & Act
        from src.journal.vector_store import EmbeddingGenerator

        generator = EmbeddingGenerator(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # Assert
        assert generator.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    def test_generate_embedding(self):
        """Test generating embedding for text."""
        # Arrange
        from src.journal.vector_store import EmbeddingGenerator

        generator = EmbeddingGenerator()

        with patch.object(generator, "model") as mock_model:
            mock_model.encode.return_value = [0.1] * 384

            # Act
            result = generator.generate("Test text")

        # Assert
        assert len(result) == 384
        assert all(v == 0.1 for v in result)

    def test_generate_batch_embeddings(self):
        """Test generating embeddings for multiple texts."""
        # Arrange
        from src.journal.vector_store import EmbeddingGenerator

        generator = EmbeddingGenerator()

        with patch.object(generator, "model") as mock_model:
            mock_model.encode.return_value = [[0.1] * 384 for _ in range(3)]

            # Act
            results = generator.generate_batch(["Text 1", "Text 2", "Text 3"])

        # Assert
        assert len(results) == 3
        assert all(len(r) == 384 for r in results)

    def test_embedding_normalization(self):
        """Test embedding vector normalization."""
        # Arrange
        from src.journal.vector_store import EmbeddingGenerator

        generator = EmbeddingGenerator()

        # Create unnormalized vector
        vector = [3.0, 4.0]  # Length should be 5

        # Act
        normalized = generator.normalize(vector)

        # Assert - Length should be 1 (normalized)
        import math

        length = math.sqrt(sum(x**2 for x in normalized))
        assert abs(length - 1.0) < 0.0001


class TestSemanticSearch:
    """Tests for semantic search functionality."""

    def test_semantic_search_with_query(self, mock_qdrant_client):
        """Test semantic search with text query."""
        # Arrange
        from src.journal.vector_store import SemanticSearch

        searcher = SemanticSearch(
            store_host="localhost",
            store_port=6333,
        )
        searcher.vector_store.client = mock_qdrant_client

        with patch.object(searcher.embedder, "generate") as mock_embed:
            mock_embed.return_value = [0.1] * 384

            # Act
            results = searcher.search("machine learning", limit=5)

        # Assert
        assert len(results) == 2
        mock_embed.assert_called_once_with("machine learning")

    def test_semantic_search_with_date_filter(self, mock_qdrant_client):
        """Test semantic search with date range filter."""
        # Arrange
        from datetime import datetime
        from src.journal.vector_store import SemanticSearch

        searcher = SemanticSearch(
            store_host="localhost",
            store_port=6333,
        )
        searcher.vector_store.client = mock_qdrant_client

        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        with patch.object(searcher.embedder, "generate") as mock_embed:
            mock_embed.return_value = [0.1] * 384

            # Act
            results = searcher.search("project updates", start_date=start_date, end_date=end_date, limit=10)

        # Assert
        assert len(results) == 2

    def test_semantic_search_with_tag_filter(self, mock_qdrant_client):
        """Test semantic search with tag filter."""
        # Arrange
        from src.journal.vector_store import SemanticSearch

        searcher = SemanticSearch(
            store_host="localhost",
            store_port=6333,
        )
        searcher.vector_store.client = mock_qdrant_client

        with patch.object(searcher.embedder, "generate") as mock_embed:
            mock_embed.return_value = [0.1] * 384

            # Act
            results = searcher.search("meeting notes", tags=["work", "important"], limit=5)

        # Assert
        assert len(results) == 2

    def test_find_similar_entries(self, mock_qdrant_client):
        """Test finding entries similar to a given entry."""
        # Arrange
        from src.journal.vector_store import SemanticSearch

        searcher = SemanticSearch(
            store_host="localhost",
            store_port=6333,
        )
        searcher.vector_store.client = mock_qdrant_client
        mock_qdrant_client.retrieve.return_value = [Mock(vector=[0.1] * 384, payload={"text": "Original"})]

        # Act
        results = searcher.find_similar("entry-id-001", limit=5)

        # Assert
        assert len(results) == 2
        mock_qdrant_client.retrieve.assert_called_once()


class TestVectorStoreIndexing:
    """Tests for vector store indexing operations."""

    def test_index_journal_entry(self, mock_qdrant_client, sample_embedding):
        """Test indexing a journal entry."""
        # Arrange
        from src.journal.vector_store import VectorIndex
        from src.journal.core import JournalEntry

        indexer = VectorIndex(
            store_host="localhost",
            store_port=6333,
        )
        indexer.store.client = mock_qdrant_client

        entry = JournalEntry(
            id="entry-001",
            content="Test journal entry content",
            tags=["test"],
        )

        with patch.object(indexer.embedder, "generate") as mock_embed:
            mock_embed.return_value = sample_embedding

            # Act
            result = indexer.index_entry(entry)

        # Assert
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()

    def test_batch_index_entries(self, mock_qdrant_client):
        """Test batch indexing multiple entries."""
        # Arrange
        from src.journal.vector_store import VectorIndex
        from src.journal.core import JournalEntry

        indexer = VectorIndex(
            store_host="localhost",
            store_port=6333,
        )
        indexer.store.client = mock_qdrant_client

        entries = [JournalEntry(id=f"entry-{i:03d}", content=f"Content {i}") for i in range(5)]

        with patch.object(indexer.embedder, "generate_batch") as mock_embed:
            mock_embed.return_value = [[0.1] * 384 for _ in range(5)]

            # Act
            result = indexer.index_entries_batch(entries)

        # Assert
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()

    def test_remove_entry_from_index(self, mock_qdrant_client):
        """Test removing an entry from the vector index."""
        # Arrange
        from src.journal.vector_store import VectorIndex

        indexer = VectorIndex(
            store_host="localhost",
            store_port=6333,
        )
        indexer.store.client = mock_qdrant_client

        # Act
        result = indexer.remove_entry("entry-001")

        # Assert
        assert result is True
        mock_qdrant_client.delete.assert_called_once()

    def test_rebuild_index(self, mock_qdrant_client):
        """Test rebuilding the entire vector index."""
        # Arrange
        from src.journal.vector_store import VectorIndex

        indexer = VectorIndex(
            store_host="localhost",
            store_port=6333,
        )
        indexer.store.client = mock_qdrant_client

        # Act
        result = indexer.rebuild_index()

        # Assert
        assert result is True
        mock_qdrant_client.delete_collection.assert_called_once()
        mock_qdrant_client.create_collection.assert_called_once()


class TestVectorStoreBackup:
    """Tests for vector store backup and recovery."""

    def test_export_collection(self, mock_qdrant_client, temp_dir):
        """Test exporting collection to file."""
        # Arrange
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client
        mock_qdrant_client.scroll.return_value = ([Mock(id="doc1", vector=[0.1] * 384, payload={"text": "Test"})], None)

        export_path = temp_dir / "vectors.json"

        # Act
        result = store.export_collection(export_path)

        # Assert
        assert result is True
        assert export_path.exists()

    def test_import_collection(self, mock_qdrant_client, temp_dir):
        """Test importing collection from file."""
        # Arrange
        import json
        from src.journal.vector_store import VectorStore

        store = VectorStore(
            host="localhost",
            port=6333,
            collection_name="test_collection",
        )
        store.client = mock_qdrant_client

        # Create import file
        data = [{"id": "doc1", "vector": [0.1] * 384, "payload": {"text": "Imported"}}]
        import_path = temp_dir / "import.json"
        with open(import_path, "w") as f:
            json.dump(data, f)

        # Act
        result = store.import_collection(import_path)

        # Assert
        assert result is True
        mock_qdrant_client.upsert.assert_called_once()
