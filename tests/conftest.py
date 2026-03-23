"""
Pytest configuration and fixtures for OPC200 tests.
"""
import asyncio
import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, Mock

import pytest
import pytest_asyncio


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def data_dir(temp_dir: Path) -> Path:
    """Create a data directory within temp_dir."""
    data_path = temp_dir / "data"
    data_path.mkdir(exist_ok=True)
    return data_path


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def in_memory_db() -> sqlite3.Connection:
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


@pytest.fixture
def temp_db_path(temp_dir: Path) -> Path:
    """Create a temporary database file path."""
    return temp_dir / "test.db"


@pytest.fixture
def mock_db_connection() -> MagicMock:
    """Create a mock database connection for testing."""
    mock = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock.cursor.return_value = mock_cursor
    mock.commit.return_value = None
    return mock


# ============================================================================
# Time Fixtures
# ============================================================================

@pytest.fixture
def fixed_datetime() -> datetime:
    """Return a fixed datetime for consistent testing."""
    return datetime(2024, 3, 15, 10, 30, 0)


@pytest.fixture
def mock_datetime(monkeypatch, fixed_datetime: datetime):
    """Mock datetime to return a fixed value."""
    class MockDateTime:
        @classmethod
        def now(cls, tz=None):
            return fixed_datetime
        
        @classmethod
        def utcnow(cls):
            return fixed_datetime
    
    monkeypatch.setattr("datetime.datetime", MockDateTime)
    return fixed_datetime


# ============================================================================
# Encryption/Mock Security Fixtures
# ============================================================================

@pytest.fixture
def mock_encryption_key() -> bytes:
    """Provide a test encryption key."""
    return b"test-key-32-bytes-long-for-aes256"


@pytest.fixture
def mock_vault(temp_dir: Path) -> Path:
    """Create a mock vault directory."""
    vault_path = temp_dir / "vault"
    vault_path.mkdir(exist_ok=True)
    return vault_path


@pytest.fixture
def mock_encryption_service(mock_encryption_key: bytes):
    """Create a mock encryption service."""
    service = Mock()
    service.encrypt.return_value = b"encrypted_data"
    service.decrypt.return_value = b"decrypted_data"
    service.generate_key.return_value = mock_encryption_key
    return service


# ============================================================================
# Journal Fixtures
# ============================================================================

@pytest.fixture
def sample_journal_entry_data() -> dict:
    """Provide sample journal entry data."""
    return {
        "id": "entry-001",
        "content": "Test journal entry content",
        "tags": ["test", "example"],
        "metadata": {
            "source": "test",
            "importance": "high"
        },
        "created_at": datetime(2024, 3, 15, 10, 30, 0).isoformat(),
        "updated_at": datetime(2024, 3, 15, 10, 30, 0).isoformat(),
    }


@pytest.fixture
def sample_journal_entries() -> list[dict]:
    """Provide multiple sample journal entries."""
    return [
        {
            "id": f"entry-{i:03d}",
            "content": f"Test entry content {i}",
            "tags": ["test"] if i % 2 == 0 else ["example"],
            "metadata": {"index": i},
            "created_at": datetime(2024, 3, 15, 10, i, 0).isoformat(),
        }
        for i in range(10)
    ]


# ============================================================================
# Vector Store Fixtures
# ============================================================================

@pytest.fixture
def mock_qdrant_client():
    """Create a mock Qdrant client."""
    client = Mock()
    client.search.return_value = [
        Mock(id="doc1", score=0.95, payload={"text": "result1"}),
        Mock(id="doc2", score=0.85, payload={"text": "result2"}),
    ]
    client.upsert.return_value = None
    client.delete.return_value = None
    return client


@pytest.fixture
def sample_embedding() -> list[float]:
    """Provide a sample embedding vector."""
    # 384-dimensional embedding (typical for all-MiniLM-L6-v2)
    return [0.1] * 384


@pytest.fixture
def sample_embeddings() -> list[list[float]]:
    """Provide multiple sample embeddings."""
    return [[0.1 * (i + 1)] * 384 for i in range(5)]


# ============================================================================
# Task Scheduler Fixtures
# ============================================================================

@pytest.fixture
def sample_task_data() -> dict:
    """Provide sample task data."""
    return {
        "id": "task-001",
        "name": "test_task",
        "cron": "0 9 * * *",
        "command": "echo 'hello'",
        "enabled": True,
        "last_run": None,
        "next_run": None,
    }


@pytest.fixture
def mock_scheduler():
    """Create a mock task scheduler."""
    scheduler = Mock()
    scheduler.add_job.return_value = None
    scheduler.remove_job.return_value = None
    scheduler.get_jobs.return_value = []
    return scheduler


# ============================================================================
# Async Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def async_temp_dir() -> AsyncGenerator[Path, None]:
    """Create an async temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest_asyncio.fixture
async def async_mock_db():
    """Create an async mock database."""
    db = Mock()
    db.fetch_one = Mock(return_value={"id": 1, "name": "test"})
    db.fetch_all = Mock(return_value=[])
    db.execute = Mock(return_value=None)
    return db


# ============================================================================
# Event Loop Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_file(path: Path, content: str = "") -> Path:
    """Helper to create a test file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def create_test_json(path: Path, data: dict) -> Path:
    """Helper to create a test JSON file."""
    import json
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


# Make helper functions available to tests
pytest.create_test_file = create_test_file
pytest.create_test_json = create_test_json
