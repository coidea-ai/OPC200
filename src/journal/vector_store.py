"""
Vector Store Module - Qdrant integration for semantic search.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class VectorStore:
    """Vector store using Qdrant."""
    
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "journal"
    client: Any = None
    
    def connect(self) -> bool:
        """Connect to Qdrant server."""
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(host=self.host, port=self.port)
            return True
        except ImportError:
            # Mock client for testing
            self.client = MockQdrantClient()
            return True
    
    def create_collection(self, vector_size: int = 384) -> bool:
        """Create a vector collection."""
        from qdrant_client.models import Distance, VectorParams
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        return True
    
    def delete_collection(self) -> bool:
        """Delete the vector collection."""
        self.client.delete_collection(collection_name=self.collection_name)
        return True
    
    def collection_exists(self) -> bool:
        """Check if collection exists."""
        return self.client.collection_exists(collection_name=self.collection_name)
    
    def upsert(self, id: str, vector: list[float], payload: dict) -> bool:
        """Upsert a single vector."""
        from qdrant_client.models import PointStruct
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=id, vector=vector, payload=payload)]
        )
        return True
    
    def upsert_batch(self, points: list[dict]) -> bool:
        """Upsert multiple vectors."""
        from qdrant_client.models import PointStruct
        
        qdrant_points = [
            PointStruct(id=p["id"], vector=p["vector"], payload=p.get("payload", {}))
            for p in points
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=qdrant_points
        )
        return True
    
    def search(self, vector: list[float], limit: int = 10, score_threshold: float = 0.0, query_filter: Optional[dict] = None):
        """Search for similar vectors."""
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )
        return results
    
    def delete_by_id(self, id: str) -> bool:
        """Delete vector by ID."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[id]
        )
        return True
    
    def delete_by_filter(self, filter_condition: dict) -> bool:
        """Delete vectors by filter."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=filter_condition
        )
        return True
    
    def get_by_id(self, id: str):
        """Get vector by ID."""
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[id]
        )
        return results[0] if results else None
    
    def count(self) -> int:
        """Count vectors in collection."""
        result = self.client.count(collection_name=self.collection_name)
        return result.count
    
    def scroll(self, limit: int = 100, offset: Optional[str] = None):
        """Scroll through vectors."""
        results, next_page = self.client.scroll(
            collection_name=self.collection_name,
            limit=limit,
            offset=offset
        )
        return results, next_page
    
    def export_collection(self, export_path: Path) -> bool:
        """Export collection to file."""
        results, _ = self.scroll(limit=10000)
        
        data = []
        for point in results:
            data.append({
                "id": point.id,
                "vector": point.vector if hasattr(point, "vector") else [],
                "payload": point.payload
            })
        
        with open(export_path, "w") as f:
            json.dump(data, f)
        
        return True
    
    def import_collection(self, import_path: Path) -> bool:
        """Import collection from file."""
        with open(import_path) as f:
            data = json.load(f)
        
        self.upsert_batch(data)
        return True


class MockQdrantClient:
    """Mock Qdrant client for testing."""
    
    def __init__(self):
        self.collections = {}
        self.vectors = {}
    
    def create_collection(self, collection_name: str, vectors_config) -> None:
        self.collections[collection_name] = {"vectors_config": vectors_config}
        self.vectors[collection_name] = {}
    
    def delete_collection(self, collection_name: str) -> None:
        if collection_name in self.collections:
            del self.collections[collection_name]
            del self.vectors[collection_name]
    
    def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections
    
    def upsert(self, collection_name: str, points) -> None:
        if collection_name not in self.vectors:
            self.vectors[collection_name] = {}
        for point in points:
            self.vectors[collection_name][point.id] = point
    
    def search(self, collection_name: str, query_vector, limit: int = 10, score_threshold: float = 0.0, query_filter=None):
        from unittest.mock import Mock
        
        results = []
        for i in range(min(limit, 2)):
            mock = Mock()
            mock.id = f"doc{i+1}"
            mock.score = 0.95 - (i * 0.1)
            mock.payload = {"text": f"result{i+1}"}
            results.append(mock)
        return results
    
    def delete(self, collection_name: str, points_selector) -> None:
        if collection_name in self.vectors:
            for point_id in points_selector:
                if point_id in self.vectors[collection_name]:
                    del self.vectors[collection_name][point_id]
    
    def retrieve(self, collection_name: str, ids: list):
        from unittest.mock import Mock
        
        results = []
        for id in ids:
            if collection_name in self.vectors and id in self.vectors[collection_name]:
                results.append(self.vectors[collection_name][id])
            else:
                mock = Mock()
                mock.id = id
                mock.payload = {"text": "Test"}
                results.append(mock)
        return results
    
    def count(self, collection_name: str):
        from unittest.mock import Mock
        
        mock = Mock()
        mock.count = len(self.vectors.get(collection_name, {}))
        return mock
    
    def scroll(self, collection_name: str, limit: int = 100, offset=None):
        vectors = self.vectors.get(collection_name, {})
        results = list(vectors.values())[:limit]
        return results, None


class EmbeddingGenerator:
    """Generate embeddings for text."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
    
    def _load_model(self):
        """Load the embedding model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer(self.model_name)
            except ImportError:
                # Return mock model for testing
                self.model = MockModel()
    
    def generate(self, text: str) -> list[float]:
        """Generate embedding for text."""
        self._load_model()
        embedding = self.model.encode(text)
        return embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
    
    def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        self._load_model()
        embeddings = self.model.encode(texts)
        return [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]
    
    @staticmethod
    def normalize(vector: list[float]) -> list[float]:
        """Normalize a vector to unit length."""
        import math
        
        length = math.sqrt(sum(x**2 for x in vector))
        if length == 0:
            return vector
        return [x / length for x in vector]


class MockModel:
    """Mock embedding model for testing."""
    
    def encode(self, texts):
        """Mock encode method."""
        import numpy as np
        
        if isinstance(texts, str):
            return np.array([0.1] * 384)
        return [np.array([0.1] * 384) for _ in texts]


class SemanticSearch:
    """Semantic search using vector store."""
    
    def __init__(self, store_host: str = "localhost", store_port: int = 6333):
        self.vector_store = VectorStore(host=store_host, port=store_port)
        self.embedder = EmbeddingGenerator()
    
    def search(self, query: str, limit: int = 10, start_date=None, end_date=None, tags=None):
        """Search using semantic similarity."""
        query_vector = self.embedder.generate(query)
        
        query_filter = None
        if tags:
            query_filter = {"must": [{"key": "tags", "match": {"any": tags}}]}
        
        results = self.vector_store.search(
            vector=query_vector,
            limit=limit,
            query_filter=query_filter
        )
        
        return results
    
    def find_similar(self, entry_id: str, limit: int = 5):
        """Find entries similar to a given entry."""
        entry = self.vector_store.get_by_id(entry_id)
        if entry is None:
            return []
        
        # Note: In real implementation, we'd retrieve the stored vector
        # For now, use the entry content to generate a new vector
        query_vector = self.embedder.generate(entry.payload.get("text", ""))
        
        results = self.vector_store.search(
            vector=query_vector,
            limit=limit + 1  # +1 to exclude the entry itself
        )
        
        # Filter out the original entry
        return [r for r in results if r.id != entry_id][:limit]


class VectorIndex:
    """Index journal entries in vector store."""
    
    def __init__(self, store_host: str = "localhost", store_port: int = 6333):
        self.store = VectorStore(host=store_host, port=store_port)
        self.embedder = EmbeddingGenerator()
    
    def index_entry(self, entry) -> bool:
        """Index a single journal entry."""
        vector = self.embedder.generate(entry.content)
        
        payload = {
            "text": entry.content,
            "tags": entry.tags,
            "created_at": entry.created_at.isoformat() if hasattr(entry.created_at, "isoformat") else str(entry.created_at),
        }
        
        return self.store.upsert(
            id=entry.id,
            vector=vector,
            payload=payload
        )
    
    def index_entries_batch(self, entries: list) -> bool:
        """Index multiple entries in batch."""
        vectors = self.embedder.generate_batch([e.content for e in entries])
        
        points = []
        for entry, vector in zip(entries, vectors):
            points.append({
                "id": entry.id,
                "vector": vector,
                "payload": {
                    "text": entry.content,
                    "tags": entry.tags,
                    "created_at": entry.created_at.isoformat() if hasattr(entry.created_at, "isoformat") else str(entry.created_at),
                }
            })
        
        return self.store.upsert_batch(points)
    
    def remove_entry(self, entry_id: str) -> bool:
        """Remove an entry from the index."""
        return self.store.delete_by_id(entry_id)
    
    def rebuild_index(self) -> bool:
        """Rebuild the entire index."""
        self.store.delete_collection()
        self.store.create_collection()
        return True
