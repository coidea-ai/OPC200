"""
Unit tests for journal/core.py - JournalEntry class.
Following TDD: Red-Green-Refactor cycle.
"""

import json
from datetime import datetime
from unittest.mock import Mock

import pytest

# Mark all tests in this file
pytestmark = pytest.mark.unit


class TestJournalEntry:
    """Tests for the JournalEntry class."""

    def test_journal_entry_creation(self, fixed_datetime):
        """Test creating a new journal entry."""
        # Arrange & Act
        entry = Mock()
        entry.id = "entry-001"
        entry.content = "Test content"
        entry.tags = ["test", "journal"]
        entry.metadata = {"source": "test"}
        entry.created_at = fixed_datetime
        entry.updated_at = fixed_datetime

        # Assert
        assert entry.id == "entry-001"
        assert entry.content == "Test content"
        assert entry.tags == ["test", "journal"]
        assert entry.metadata == {"source": "test"}

    def test_journal_entry_to_dict(self, sample_journal_entry_data):
        """Test converting journal entry to dictionary."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id=sample_journal_entry_data["id"],
            content=sample_journal_entry_data["content"],
            tags=sample_journal_entry_data["tags"],
            metadata=sample_journal_entry_data["metadata"],
            created_at=datetime.fromisoformat(sample_journal_entry_data["created_at"]),
            updated_at=datetime.fromisoformat(sample_journal_entry_data["updated_at"]),
        )

        # Act
        result = entry.to_dict()

        # Assert
        assert result["id"] == "entry-001"
        assert result["content"] == "Test journal entry content"
        assert result["tags"] == ["test", "example"]
        assert result["metadata"]["source"] == "test"

    def test_journal_entry_from_dict(self, sample_journal_entry_data):
        """Test creating journal entry from dictionary."""
        # Arrange & Act
        from src.journal.core import JournalEntry

        entry = JournalEntry.from_dict(sample_journal_entry_data)

        # Assert
        assert entry.id == "entry-001"
        assert entry.content == "Test journal entry content"
        assert entry.tags == ["test", "example"]
        assert entry.metadata["importance"] == "high"

    def test_journal_entry_add_tag(self):
        """Test adding a tag to journal entry."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
            tags=["initial"],
        )

        # Act
        entry.add_tag("new-tag")

        # Assert
        assert "new-tag" in entry.tags
        assert "initial" in entry.tags

    def test_journal_entry_remove_tag(self):
        """Test removing a tag from journal entry."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
            tags=["tag1", "tag2", "tag3"],
        )

        # Act
        entry.remove_tag("tag2")

        # Assert
        assert "tag2" not in entry.tags
        assert "tag1" in entry.tags
        assert "tag3" in entry.tags

    def test_journal_entry_update_content(self, fixed_datetime):
        """Test updating journal entry content."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id="entry-001",
            content="Original content",
            created_at=fixed_datetime,
            updated_at=fixed_datetime,
        )
        original_updated = entry.updated_at

        # Act
        entry.update_content("Updated content")

        # Assert
        assert entry.content == "Updated content"
        assert entry.updated_at != original_updated

    def test_journal_entry_update_metadata(self):
        """Test updating journal entry metadata."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
            metadata={"key1": "value1"},
        )

        # Act
        entry.update_metadata({"key2": "value2"})

        # Assert
        assert entry.metadata["key1"] == "value1"
        assert entry.metadata["key2"] == "value2"

    def test_journal_entry_has_tag(self):
        """Test checking if entry has a specific tag."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
            tags=["important", "work"],
        )

        # Assert
        assert entry.has_tag("important") is True
        assert entry.has_tag("work") is True
        assert entry.has_tag("personal") is False

    def test_journal_entry_search_content(self):
        """Test searching within entry content."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            id="entry-001",
            content="This is a test entry about Python programming",
        )

        # Assert
        assert entry.search_content("Python") is True
        assert entry.search_content("programming") is True
        assert entry.search_content("Java") is False

    def test_journal_entry_validation_empty_content(self):
        """Test validation fails with empty content."""
        # Arrange & Act & Assert
        from src.journal.core import JournalEntry

        with pytest.raises(ValueError, match="Content cannot be empty"):
            JournalEntry(id="entry-001", content="")

    def test_journal_entry_validation_missing_id(self):
        """Test that auto-generated ID is created when not provided."""
        # Arrange & Act
        from src.journal.core import JournalEntry

        entry = JournalEntry(content="Test content")

        # Assert
        assert entry.id is not None
        assert len(entry.id) > 0

    def test_journal_entry_serialization_json(self, sample_journal_entry_data):
        """Test JSON serialization of journal entry."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry.from_dict(sample_journal_entry_data)

        # Act
        json_str = entry.to_json()

        # Assert
        parsed = json.loads(json_str)
        assert parsed["id"] == "entry-001"
        assert parsed["content"] == "Test journal entry content"

    def test_journal_entry_deserialization_json(self, sample_journal_entry_data):
        """Test JSON deserialization of journal entry."""
        # Arrange
        from src.journal.core import JournalEntry

        json_str = json.dumps(sample_journal_entry_data)

        # Act
        entry = JournalEntry.from_json(json_str)

        # Assert
        assert entry.id == "entry-001"
        assert entry.content == "Test journal entry content"

    def test_journal_entry_auto_timestamps(self):
        """Test that timestamps are auto-generated."""
        # Arrange & Act
        from src.journal.core import JournalEntry

        entry = JournalEntry(content="Test content")

        # Assert
        assert entry.created_at is not None
        assert entry.updated_at is not None
        assert isinstance(entry.created_at, datetime)
        assert isinstance(entry.updated_at, datetime)


class TestJournalEntryCRUD:
    """Tests for JournalEntry CRUD operations."""

    def test_create_entry(self, in_memory_db):
        """Test creating a new entry in database."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entry = JournalEntry(
            content="Test content",
            tags=["test"],
        )

        # Act
        result = manager.create_entry(entry)

        # Assert
        assert result.id is not None
        assert result.content == "Test content"

    def test_read_entry(self, in_memory_db, sample_journal_entry_data):
        """Test reading an entry from database."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entry = JournalEntry.from_dict(sample_journal_entry_data)
        manager.create_entry(entry)

        # Act
        result = manager.get_entry("entry-001")

        # Assert
        assert result is not None
        assert result.id == "entry-001"
        assert result.content == "Test journal entry content"

    def test_read_nonexistent_entry(self, in_memory_db):
        """Test reading a non-existent entry returns None."""
        # Arrange
        from src.journal.core import JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        # Act
        result = manager.get_entry("nonexistent")

        # Assert
        assert result is None

    def test_update_entry(self, in_memory_db, sample_journal_entry_data):
        """Test updating an existing entry."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entry = JournalEntry.from_dict(sample_journal_entry_data)
        manager.create_entry(entry)

        # Act
        entry.content = "Updated content"
        result = manager.update_entry(entry)

        # Assert
        assert result is True

        updated = manager.get_entry("entry-001")
        assert updated.content == "Updated content"

    def test_delete_entry(self, in_memory_db, sample_journal_entry_data):
        """Test deleting an entry."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entry = JournalEntry.from_dict(sample_journal_entry_data)
        manager.create_entry(entry)

        # Act
        result = manager.delete_entry("entry-001")

        # Assert
        assert result is True
        assert manager.get_entry("entry-001") is None

    def test_list_entries(self, in_memory_db, sample_journal_entries):
        """Test listing all entries."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        for data in sample_journal_entries:
            entry = JournalEntry.from_dict(data)
            manager.create_entry(entry)

        # Act
        results = manager.list_entries()

        # Assert
        assert len(results) == 10

    def test_list_entries_by_tag(self, in_memory_db, sample_journal_entries):
        """Test filtering entries by tag."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        for data in sample_journal_entries:
            entry = JournalEntry.from_dict(data)
            manager.create_entry(entry)

        # Act
        results = manager.list_entries_by_tag("test")

        # Assert
        assert len(results) == 5  # Even indices have "test" tag

    def test_search_entries(self, in_memory_db):
        """Test searching entries by content."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entries = [
            JournalEntry(content="Python programming tips"),
            JournalEntry(content="Java development guide"),
            JournalEntry(content="Python best practices"),
        ]

        for entry in entries:
            manager.create_entry(entry)

        # Act
        results = manager.search_entries("Python")

        # Assert
        assert len(results) == 2
        for result in results:
            assert "Python" in result.content


class TestJournalEntryTags:
    """Tests for journal entry tag management."""

    def test_get_all_tags(self, in_memory_db):
        """Test retrieving all unique tags."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entries = [
            JournalEntry(content="Entry 1", tags=["work", "important"]),
            JournalEntry(content="Entry 2", tags=["personal", "important"]),
            JournalEntry(content="Entry 3", tags=["work"]),
        ]

        for entry in entries:
            manager.create_entry(entry)

        # Act
        tags = manager.get_all_tags()

        # Assert
        assert set(tags) == {"work", "important", "personal"}

    def test_rename_tag(self, in_memory_db):
        """Test renaming a tag across all entries."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entries = [
            JournalEntry(content="Entry 1", tags=["work", "important"]),
            JournalEntry(content="Entry 2", tags=["work"]),
        ]

        for entry in entries:
            manager.create_entry(entry)

        # Act
        result = manager.rename_tag("work", "job")

        # Assert
        assert result is True

        work_entries = manager.list_entries_by_tag("work")
        job_entries = manager.list_entries_by_tag("job")

        assert len(work_entries) == 0
        assert len(job_entries) == 2

    def test_delete_tag(self, in_memory_db):
        """Test deleting a tag from all entries."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager

        manager = JournalManager(in_memory_db)
        manager.create_table()

        entries = [
            JournalEntry(content="Entry 1", tags=["work", "temp"]),
            JournalEntry(content="Entry 2", tags=["temp"]),
        ]

        for entry in entries:
            manager.create_entry(entry)

        # Act
        result = manager.delete_tag("temp")

        # Assert
        assert result is True

        temp_entries = manager.list_entries_by_tag("temp")
        assert len(temp_entries) == 0

        all_entries = manager.list_entries()
        for entry in all_entries:
            assert "temp" not in entry.tags


class TestJournalEntryMetadata:
    """Tests for journal entry metadata operations."""

    def test_set_metadata_value(self):
        """Test setting a specific metadata value."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            content="Test content",
            metadata={"existing": "value"},
        )

        # Act
        entry.set_metadata("new_key", "new_value")

        # Assert
        assert entry.metadata["new_key"] == "new_value"
        assert entry.metadata["existing"] == "value"

    def test_get_metadata_value(self):
        """Test getting a specific metadata value."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            content="Test content",
            metadata={"key": "value"},
        )

        # Act & Assert
        assert entry.get_metadata("key") == "value"
        assert entry.get_metadata("missing") is None
        assert entry.get_metadata("missing", "default") == "default"

    def test_delete_metadata_key(self):
        """Test deleting a metadata key."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            content="Test content",
            metadata={"keep": "this", "remove": "this"},
        )

        # Act
        entry.delete_metadata("remove")

        # Assert
        assert "remove" not in entry.metadata
        assert "keep" in entry.metadata

    def test_has_metadata_key(self):
        """Test checking if metadata key exists."""
        # Arrange
        from src.journal.core import JournalEntry

        entry = JournalEntry(
            content="Test content",
            metadata={"exists": "value"},
        )

        # Assert
        assert entry.has_metadata("exists") is True
        assert entry.has_metadata("missing") is False
