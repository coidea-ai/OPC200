"""
pytest configuration and fixtures.
"""

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Generator
from unittest.mock import Mock

import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """Provide a temporary directory for tests."""
    return tmp_path


@pytest.fixture
def temp_db_path(tmp_path: Path) -> Path:
    """Provide a temporary database path for tests."""
    return tmp_path / "test.db"


@pytest.fixture
def in_memory_db() -> Generator[sqlite3.Connection, None, None]:
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def sample_journal_entry_data() -> dict:
    """Sample journal entry data for testing."""
    return {
        "id": "entry-001",
        "content": "Test journal entry content",
        "tags": ["test", "example"],
        "metadata": {"importance": "high", "source": "test"},
        "created_at": "2024-03-24T10:00:00",
        "updated_at": "2024-03-24T10:00:00",
    }


@pytest.fixture
def sample_journal_entries() -> list[dict]:
    """Generate sample journal entries for testing."""
    entries = []
    for i in range(10):
        entries.append(
            {
                "id": f"entry-{i:03d}",
                "content": f"Test entry content {i}",
                "tags": ["test"] if i % 2 == 0 else ["example"],
                "metadata": {"index": i},
                "created_at": f"2024-03-{i+1:02d}T10:00:00",
                "updated_at": f"2024-03-{i+1:02d}T10:00:00",
            }
        )
    return entries


@pytest.fixture
def fixed_datetime() -> datetime:
    """Return a fixed datetime for testing."""
    return datetime(2024, 3, 24, 10, 0, 0)


@pytest.fixture
def mock_encryption_service():
    """Mock encryption service for testing."""
    service = Mock()
    service.encrypt = Mock(return_value=b"encrypted_data")
    service.decrypt = Mock(return_value=b"decrypted_data")
    return service


@pytest.fixture
def sample_embedding() -> list[float]:
    """Generate a sample embedding vector."""
    return [0.1] * 384


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    """Generate sample embedding vectors."""
    return [[0.1] * 384 for _ in range(5)]


# Import mock fixtures for Qdrant
pytest_plugins = ["tests.fixtures.mocks"]
