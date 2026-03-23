"""
Integration tests for journal flow - Journal entry CRUD operations with storage.
Following TDD: Red-Green-Refactor cycle.
"""

import json
from datetime import datetime

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.database]


class TestJournalEntryFlow:
    """Integration tests for journal entry flow."""

    def test_create_and_retrieve_entry(self, temp_db_path):
        """Test creating and retrieving a journal entry."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        # Act - Create
        entry = JournalEntry(
            content="Integration test entry", tags=["integration", "test"], metadata={"source": "integration_test"}
        )
        created = manager.create_entry(entry)

        # Act - Retrieve
        retrieved = manager.get_entry(created.id)

        # Assert
        assert retrieved is not None
        assert retrieved.content == "Integration test entry"
        assert retrieved.tags == ["integration", "test"]

    def test_update_entry_flow(self, temp_db_path):
        """Test updating a journal entry through full flow."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        entry = JournalEntry(content="Original content")
        created = manager.create_entry(entry)

        # Act - Update
        created.content = "Updated content"
        created.add_tag("updated")
        manager.update_entry(created)

        # Act - Retrieve updated
        retrieved = manager.get_entry(created.id)

        # Assert
        assert retrieved.content == "Updated content"
        assert "updated" in retrieved.tags

    def test_delete_entry_flow(self, temp_db_path):
        """Test deleting a journal entry through full flow."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        entry = JournalEntry(content="To be deleted")
        created = manager.create_entry(entry)
        entry_id = created.id

        # Act - Delete
        result = manager.delete_entry(entry_id)

        # Act - Verify deletion
        retrieved = manager.get_entry(entry_id)

        # Assert
        assert result is True
        assert retrieved is None

    def test_search_entries_flow(self, temp_db_path):
        """Test searching entries through full flow."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

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
        assert all("Python" in e.content for e in results)

    def test_filter_by_tags_flow(self, temp_db_path):
        """Test filtering entries by tags."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        entries = [
            JournalEntry(content="Work entry 1", tags=["work", "important"]),
            JournalEntry(content="Personal entry", tags=["personal"]),
            JournalEntry(content="Work entry 2", tags=["work"]),
        ]

        for entry in entries:
            manager.create_entry(entry)

        # Act
        work_entries = manager.list_entries_by_tag("work")
        important_entries = manager.list_entries_by_tag("important")

        # Assert
        assert len(work_entries) == 2
        assert len(important_entries) == 1

    def test_entry_pagination(self, temp_db_path):
        """Test pagination of journal entries."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        for i in range(25):
            entry = JournalEntry(content=f"Entry {i}")
            manager.create_entry(entry)

        # Act - First page
        page1 = manager.list_entries(limit=10, offset=0)
        page2 = manager.list_entries(limit=10, offset=10)
        page3 = manager.list_entries(limit=10, offset=20)

        # Assert
        assert len(page1) == 10
        assert len(page2) == 10
        assert len(page3) == 5


class TestJournalBackupFlow:
    """Integration tests for journal backup and recovery."""

    def test_backup_and_restore(self, temp_db_path, temp_dir):
        """Test backing up and restoring journal data."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        # Create entries
        for i in range(5):
            entry = JournalEntry(content=f"Entry {i}", tags=["backup_test"], metadata={"index": i})
            manager.create_entry(entry)

        backup_path = temp_dir / "backup.db"

        # Act - Backup
        backup_result = storage.create_backup(backup_path)

        # Act - Delete original entries
        for entry in manager.list_entries():
            manager.delete_entry(entry.id)

        # Act - Restore
        restore_result = storage.restore_from_backup(backup_path)

        # Re-create manager with new connection after restore
        manager = JournalManager(storage.connection)

        # Assert
        assert backup_result is True
        assert restore_result is True
        assert len(manager.list_entries()) == 5

    def test_export_import_json(self, temp_db_path, temp_dir):
        """Test exporting and importing journal data as JSON."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        entry = JournalEntry(content="Export test entry", tags=["export", "test"], metadata={"test": True})
        manager.create_entry(entry)

        export_path = temp_dir / "export.json"

        # Act - Export
        export_result = storage.export_to_json(export_path)

        # Act - Import to new database
        new_db_path = temp_dir / "new.db"
        new_storage = SQLiteStorage(new_db_path)
        new_storage.create_tables()
        import_result = new_storage.import_from_json(export_path)

        new_manager = JournalManager(new_storage.connection)
        imported = new_manager.list_entries()

        # Assert
        assert export_result is True
        assert import_result is True
        assert len(imported) == 1
        assert imported[0].content == "Export test entry"


class TestJournalWithEncryption:
    """Integration tests for journal with encryption."""

    def test_encrypted_journal_storage(self, temp_dir):
        """Test storing journal entries with encryption."""
        # This test would require encryption service integration
        # Placeholder for the integration pattern
        pytest.skip("Encryption integration test - requires encryption service")

    def test_encrypted_backup_restore(self, temp_dir):
        """Test encrypted backup and restore."""
        pytest.skip("Encryption integration test - requires encryption service")


class TestJournalMigrationFlow:
    """Integration tests for journal database migrations."""

    def test_migration_from_v1_to_v2(self, temp_db_path):
        """Test migrating database from version 1 to 2."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()

        initial_version = storage.get_schema_version()
        assert initial_version == 1

        # Act
        migration_result = storage.migrate_to_version(2)

        # Assert
        assert migration_result is True
        assert storage.get_schema_version() == 2

    def test_migration_rollback(self, temp_db_path):
        """Test rolling back a migration."""
        # Arrange
        from src.journal.storage import SQLiteStorage

        storage = SQLiteStorage(temp_db_path)
        storage.create_tables()
        storage.migrate_to_version(2)

        # Act
        rollback_result = storage.rollback_migration(2)

        # Assert
        assert rollback_result is True
        assert storage.get_schema_version() == 1
