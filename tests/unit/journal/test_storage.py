"""
Unit tests for journal/storage.py - SQLite storage backend.
Following TDD: Red-Green-Refactor cycle.
"""

import json
import sqlite3
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit


class TestSQLiteStorage:
    """Tests for SQLite storage backend."""

    def test_storage_initialization(self, temp_db_path):
        """Test storage backend initialization."""
        # Arrange & Act
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)

        # Assert
        assert storage.db_path == temp_db_path
        assert temp_db_path.exists()

    def test_create_tables(self, in_memory_db):
        """Test creating database tables."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)

        # Act
        storage.create_tables()

        # Assert - Check tables exist
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        assert "journal_entries" in tables
        assert "tags" in tables
        assert "entry_tags" in tables

    def test_insert_entry(self, in_memory_db):
        """Test inserting a journal entry."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
            tags=["test", "example"],
            metadata={"source": "test"},
        )

        # Act
        result = storage.insert_entry(entry)

        # Assert
        assert result is True

        # Verify entry was inserted
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT * FROM journal_entries WHERE id = ?", ("entry-001",))
        row = cursor.fetchone()

        assert row is not None
        assert row["content"] == "Test content"

    def test_get_entry(self, in_memory_db):
        """Test retrieving an entry by ID."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
            tags=["test"],
        )
        storage.insert_entry(entry)

        # Act
        result = storage.get_entry("entry-001")

        # Assert
        assert result is not None
        assert result.id == "entry-001"
        assert result.content == "Test content"

    def test_get_nonexistent_entry(self, in_memory_db):
        """Test retrieving a non-existent entry returns None."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        result = storage.get_entry("nonexistent")

        # Assert
        assert result is None

    def test_update_entry(self, in_memory_db):
        """Test updating an existing entry."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entry = JournalEntry(
            id="entry-001",
            content="Original content",
            tags=["original"],
        )
        storage.insert_entry(entry)

        # Update entry
        entry.content = "Updated content"
        entry.tags = ["updated"]

        # Act
        result = storage.update_entry(entry)

        # Assert
        assert result is True

        updated = storage.get_entry("entry-001")
        assert updated.content == "Updated content"
        assert updated.tags == ["updated"]

    def test_delete_entry(self, in_memory_db):
        """Test deleting an entry."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
        )
        storage.insert_entry(entry)

        # Act
        result = storage.delete_entry("entry-001")

        # Assert
        assert result is True
        assert storage.get_entry("entry-001") is None

    def test_list_entries(self, in_memory_db):
        """Test listing all entries."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        for i in range(5):
            entry = JournalEntry(
                id=f"entry-{i:03d}",
                content=f"Content {i}",
            )
            storage.insert_entry(entry)

        # Act
        results = storage.list_entries()

        # Assert
        assert len(results) == 5

    def test_list_entries_pagination(self, in_memory_db):
        """Test listing entries with pagination."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        for i in range(10):
            entry = JournalEntry(
                id=f"entry-{i:03d}",
                content=f"Content {i}",
            )
            storage.insert_entry(entry)

        # Act
        results = storage.list_entries(limit=5, offset=0)

        # Assert
        assert len(results) == 5
        assert results[0].id == "entry-000"
        assert results[4].id == "entry-004"

    def test_search_by_content(self, in_memory_db):
        """Test searching entries by content."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entries = [
            JournalEntry(id="e1", content="Python programming"),
            JournalEntry(id="e2", content="Java development"),
            JournalEntry(id="e3", content="Python best practices"),
        ]

        for entry in entries:
            storage.insert_entry(entry)

        # Act
        results = storage.search_by_content("Python")

        # Assert
        assert len(results) == 2
        assert all("Python" in r.content for r in results)

    def test_list_by_tag(self, in_memory_db):
        """Test listing entries by tag."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entries = [
            JournalEntry(id="e1", content="Entry 1", tags=["work", "important"]),
            JournalEntry(id="e2", content="Entry 2", tags=["personal"]),
            JournalEntry(id="e3", content="Entry 3", tags=["work"]),
        ]

        for entry in entries:
            storage.insert_entry(entry)

        # Act
        results = storage.list_by_tag("work")

        # Assert
        assert len(results) == 2
        assert all("work" in r.tags for r in results)


class TestStorageBackup:
    """Tests for storage backup and recovery."""

    def test_create_backup(self, temp_db_path, temp_dir):
        """Test creating a database backup."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        entry = JournalEntry(
            id="entry-001",
            content="Test content",
        )
        storage.insert_entry(entry)

        backup_path = temp_dir / "backup.db"

        # Act
        result = storage.create_backup(backup_path)

        # Assert
        assert result is True
        assert backup_path.exists()

        # Verify backup contains data
        backup_storage = SQLiteStorage(backup_path)
        backup_entry = backup_storage.get_entry("entry-001")
        assert backup_entry is not None
        assert backup_entry.content == "Test content"

    def test_restore_from_backup(self, temp_db_path, temp_dir):
        """Test restoring from a backup."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        # Create original database
        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        entry = JournalEntry(
            id="entry-001",
            content="Original content",
        )
        storage.insert_entry(entry)

        # Create backup
        backup_path = temp_dir / "backup.db"
        storage.create_backup(backup_path)

        # Corrupt original database
        storage.delete_entry("entry-001")

        # Act - Restore
        result = storage.restore_from_backup(backup_path)

        # Assert
        assert result is True

        restored = storage.get_entry("entry-001")
        assert restored is not None
        assert restored.content == "Original content"

    def test_export_to_json(self, in_memory_db, temp_dir):
        """Test exporting entries to JSON."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        entries = [
            JournalEntry(id="e1", content="Entry 1", tags=["tag1"]),
            JournalEntry(id="e2", content="Entry 2", tags=["tag2"]),
        ]

        for entry in entries:
            storage.insert_entry(entry)

        export_path = temp_dir / "export.json"

        # Act
        result = storage.export_to_json(export_path)

        # Assert
        assert result is True
        assert export_path.exists()

        # Verify exported content
        with open(export_path) as f:
            data = json.load(f)
            assert len(data) == 2
            assert data[0]["content"] == "Entry 1"

    def test_import_from_json(self, in_memory_db, temp_dir):
        """Test importing entries from JSON."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Create import file
        data = [
            {"id": "e1", "content": "Imported 1", "tags": ["imported"]},
            {"id": "e2", "content": "Imported 2", "tags": ["imported"]},
        ]

        import_path = temp_dir / "import.json"
        with open(import_path, "w") as f:
            json.dump(data, f)

        # Act
        result = storage.import_from_json(import_path)

        # Assert
        assert result is True

        entries = storage.list_entries()
        assert len(entries) == 2
        assert entries[0].content == "Imported 1"


class TestStorageMigration:
    """Tests for database migrations."""

    def test_get_schema_version(self, in_memory_db):
        """Test getting current schema version."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        version = storage.get_schema_version()

        # Assert
        assert version == 1  # Initial version

    def test_migrate_to_version(self, in_memory_db):
        """Test migrating to a specific version."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        result = storage.migrate_to_version(2)

        # Assert
        assert result is True
        assert storage.get_schema_version() == 2

    def test_migration_rollback(self, in_memory_db):
        """Test rolling back a migration."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()
        storage.migrate_to_version(2)

        # Act
        result = storage.rollback_migration(2)

        # Assert
        assert result is True
        assert storage.get_schema_version() == 1

    def test_check_migration_needed(self, in_memory_db):
        """Test checking if migration is needed."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        needed = storage.check_migration_needed(target_version=2)

        # Assert
        assert needed is True

        # After migration
        storage.migrate_to_version(2)
        needed = storage.check_migration_needed(target_version=2)
        assert needed is False


class TestStorageIntegrity:
    """Tests for storage integrity checks."""

    def test_check_integrity(self, in_memory_db):
        """Test database integrity check."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        result = storage.check_integrity()

        # Assert
        assert result is True

    def test_rebuild_indexes(self, in_memory_db):
        """Test rebuilding database indexes."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        result = storage.rebuild_indexes()

        # Assert
        assert result is True

    def test_vacuum_database(self, in_memory_db):
        """Test vacuuming the database."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        result = storage.vacuum()

        # Assert
        assert result is True

    def test_optimize_database(self, in_memory_db):
        """Test optimizing the database."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        result = storage.optimize()

        # Assert
        assert result is True


class TestStorageTransactions:
    """Tests for storage transaction handling."""

    def test_transaction_commit(self, in_memory_db):
        """Test successful transaction commit."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act
        with storage.transaction() as tx:
            entry = JournalEntry(id="e1", content="Test")
            tx.insert_entry(entry)
        # Transaction commits on exit

        # Assert
        result = storage.get_entry("e1")
        assert result is not None

    def test_transaction_rollback(self, in_memory_db):
        """Test transaction rollback on error."""
        # Arrange
        from src.journal.storage import SQLiteStorage
        from src.journal.core import JournalEntry

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act & Assert
        try:
            with storage.transaction() as tx:
                entry = JournalEntry(id="e1", content="Test")
                tx.insert_entry(entry)
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # Assert - Entry should not exist
        result = storage.get_entry("e1")
        assert result is None

    def test_nested_transactions(self, in_memory_db):
        """Test nested transaction handling."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(connection=in_memory_db)
        storage.create_tables()

        # Act - SQLite doesn't support true nested transactions
        # It uses SAVEPOINTS for nested transactions
        with storage.transaction() as outer:
            # Nested transaction should use savepoint
            with storage.transaction() as inner:
                pass

        # Assert - No exception means success
        assert True
