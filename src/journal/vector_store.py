"""
Vector Store Module - Qdrant integration for semantic search.
"""
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional


# Retry configuration constants
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_RETRY_BACKOFF = 2.0  # exponential backoff multiplier


class QdrantConnectionError(ConnectionError):
    """Raised when Qdrant connection fails after all retries."""
    pass


def with_retry(
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: float = DEFAULT_RETRY_DELAY,
    backoff: float = DEFAULT_RETRY_BACKOFF,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable:
    """Decorator for adding retry logic to functions.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        backoff: Multiplier for exponential backoff
        exceptions: Tuple of exception types to catch and retry
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            delay = retry_delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(delay)
                        delay *= backoff
                    else:
                        raise QdrantConnectionError(
                            f"Failed after {max_retries + 1} attempts: {e}"
                        ) from e
            
            # This should never be reached, but just in case
            raise QdrantConnectionError(f"Unexpected error: {last_exception}")
        
        return wrapper
    return decorator


@dataclass
class VectorStore:
    """Vector store using Qdrant."""
    
    host: str = "localhost"
    port: int = 6333
    collection_name: str = "journal"
    client: Any = None
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    
    def __post_init__(self):
        """Initialize retry configuration."""
        # Ensure retry decorator has access to instance config
        self._retry_decorator = with_retry(
            max_retries=self.max_retries,
            retry_delay=self.retry_delay
        )
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def connect(self) -> bool:
        """Connect to Qdrant server with retry logic.
        
        Returns:
            True if connection successful
            
        Raises:
            QdrantConnectionError: If connection fails after all retries
            ImportError: If qdrant_client is not installed
        """
        try:
            from qdrant_client import QdrantClient
            self.client = QdrantClient(host=self.host, port=self.port)
            return True
        except ImportError:
            # Re-raise ImportError instead of using mock in production
            raise ImportError(
                "qdrant_client is required for production use. "
                "Install with: pip install qdrant-client"
            )
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def create_collection(self, vector_size: int = 384) -> bool:
        """Create a vector collection."""
        from qdrant_client.models import Distance, VectorParams
        
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        return True
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def delete_collection(self) -> bool:
        """Delete the vector collection."""
        self.client.delete_collection(collection_name=self.collection_name)
        return True
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def collection_exists(self) -> bool:
        """Check if collection exists."""
        return self.client.collection_exists(collection_name=self.collection_name)
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def upsert(self, id: str, vector: list[float], payload: dict) -> bool:
        """Upsert a single vector."""
        from qdrant_client.models import PointStruct
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=[PointStruct(id=id, vector=vector, payload=payload)]
        )
        return True
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
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
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
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
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def delete_by_id(self, id: str) -> bool:
        """Delete vector by ID."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=[id]
        )
        return True
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def delete_by_filter(self, filter_condition: dict) -> bool:
        """Delete vectors by filter."""
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=filter_condition
        )
        return True
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def get_by_id(self, id: str):
        """Get vector by ID."""
        results = self.client.retrieve(
            collection_name=self.collection_name,
            ids=[id]
        )
        return results[0] if results else None
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
    def count(self) -> int:
        """Count vectors in collection."""
        result = self.client.count(collection_name=self.collection_name)
        return result.count
    
    @with_retry(max_retries=DEFAULT_MAX_RETRIES, retry_delay=DEFAULT_RETRY_DELAY)
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


class EmbeddingGenerator:
    """Generate embeddings for text."""
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
    
    def _load_model(self):
        """Load the embedding model."""
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
    
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
        """Find entries similar to a given entry using stored vector.
        
        Uses the vector stored in Qdrant rather than regenerating from content,
        ensuring consistency with the indexed representation.
        """
        entry = self.vector_store.get_by_id(entry_id)
        if entry is None:
            return []
        
        # Use stored vector from Qdrant (not regenerated)
        # Qdrant's retrieve returns points that may have vectors disabled by default
        # We need to check if vector is available, otherwise fall back to regeneration
        stored_vector = None
        if hasattr(entry, 'vector') and entry.vector is not None:
            stored_vector = entry.vector
        
        if stored_vector:
            query_vector = stored_vector
        else:
            # Fallback: regenerate vector if not stored (with warning)
            import warnings
            warnings.warn(
                f"Stored vector not available for entry {entry_id}, "
                "regenerating from content. Consider enabling vector storage in Qdrant.",
                UserWarning
            )
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
