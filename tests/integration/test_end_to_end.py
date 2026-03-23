"""
End-to-end integration tests for OPC200.
These tests simulate complete user workflows.
"""

import pytest
from datetime import datetime

pytestmark = [pytest.mark.integration, pytest.mark.e2e]


class TestUserJourney:
    """End-to-end test simulating a complete user journey."""

    def test_complete_journal_workflow(self, in_memory_db):
        """Test the complete journal workflow from creation to insights."""
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        # Setup
        manager = JournalManager(in_memory_db)
        manager.create_table()
        storage = SQLiteStorage(connection=in_memory_db)

        # Day 1: User creates first journal entry
        entry1 = JournalEntry(
            content="Started my one-person company today! Excited but nervous.",
            tags=["milestone", "day1"],
            metadata={"mood": "excited"},
        )
        manager.create_entry(entry1)

        # Day 2: User adds more entries
        entry2 = JournalEntry(
            content="Finished the product prototype. Need to validate with customers.",
            tags=["product", "validation"],
            metadata={"mood": "productive"},
        )
        manager.create_entry(entry2)

        # User searches for entries
        results = manager.search_entries("product")
        assert len(results) == 1
        assert "prototype" in results[0].content

        # User filters by tag
        milestone_entries = manager.list_entries_by_tag("milestone")
        assert len(milestone_entries) == 1

        # User updates an entry
        entry1.add_tag("reviewed")
        manager.update_entry(entry1)

        # Verify update
        updated = manager.get_entry(entry1.id)
        assert "reviewed" in updated.tags

        # Export data
        import json
        from pathlib import Path

        all_entries = manager.list_entries(limit=100)
        export_data = [e.to_dict() for e in all_entries]

        assert len(export_data) == 2

        # Import data
        storage.import_from_json = lambda path: True  # Mock for test

    def test_security_workflow(self, temp_dir):
        """Test security workflow with vault and encryption."""
        from src.security.vault import DataVault, VaultAccessControl
        from src.security.encryption import EncryptionService, PasswordHashing

        # Setup vault
        vault = DataVault(base_path=temp_dir / "vault")

        # User stores sensitive data
        sensitive_data = b"API Key: sk-secret123"
        vault._access_control.grant_access("user1", "api-keys", ["write", "read"])
        vault.set_user_context("user1")

        vault.store_encrypted("api-keys", sensitive_data)

        # User retrieves data
        retrieved = vault.retrieve_decrypted("api-keys")
        assert retrieved == sensitive_data

        # Unauthorized access denied
        vault.set_user_context("user2")
        with pytest.raises(PermissionError):
            vault.retrieve_decrypted("api-keys")

        # Password protection
        password = "MySecurePassword123!"
        hashed = PasswordHashing.hash(password)
        assert PasswordHashing.verify(password, hashed)

    def test_task_scheduling_workflow(self):
        """Test async task scheduling workflow."""
        import asyncio
        from src.tasks.scheduler import TaskQueue, TaskScheduler

        async def run_test():
            # Setup
            scheduler = TaskScheduler()
            queue = TaskQueue()

            # Add a scheduled job
            def sample_task():
                return "task completed"

            job_id = scheduler.add_job(sample_task, "daily", "test-job")
            assert job_id in scheduler.jobs

            # Queue a task
            task_id = await queue.enqueue(sample_task, priority=1)
            assert task_id.startswith("task_")

            # Execute task
            async def async_sample_task():
                return sample_task()
            result = await queue.execute(async_sample_task)

        asyncio.run(run_test())


class TestDataFlow:
    """Test data flow between components."""

    def test_journal_to_storage_flow(self, in_memory_db, temp_dir):
        """Test data flow from journal to storage."""
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        # Create entry
        manager = JournalManager(in_memory_db)
        manager.create_table()

        entry = JournalEntry(content="Test entry for data flow", tags=["test", "dataflow"])
        manager.create_entry(entry)

        # Export via storage
        storage = SQLiteStorage(connection=in_memory_db)
        export_path = temp_dir / "export.json"

        # Mock export
        storage.export_to_json(export_path)
        assert export_path.exists()

        # Import and verify
        # This would typically import into a new database

    def test_encryption_to_vault_flow(self, temp_dir):
        """Test data flow from encryption to vault."""
        from src.security.encryption import EncryptionService, FileEncryption
        from src.security.vault import DataVault

        # Generate key
        key = EncryptionService.generate_key()
        service = EncryptionService(key)

        # Encrypt data
        plaintext = b"Sensitive business data"
        ciphertext = service.encrypt(plaintext)

        # Store in vault
        vault = DataVault(base_path=temp_dir / "vault")
        vault._access_control.grant_access("user1", "data-file", ["write", "read"])
        vault.set_user_context("user1")

        # Store encrypted data
        vault.store_encrypted("data-file", ciphertext)

        # Retrieve and decrypt
        retrieved_cipher = vault.retrieve_decrypted("data-file")
        decrypted = service.decrypt(retrieved_cipher)

        assert decrypted == plaintext
