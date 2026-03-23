"""
End-to-end tests for complete user journeys.
Following TDD: Red-Green-Refactor cycle.
"""

import pytest

pytestmark = pytest.mark.e2e


class TestUserJourney:
    """End-to-end tests for complete user journeys."""

    def test_complete_journal_workflow(self, temp_dir):
        """Test complete journal workflow from creation to insight generation."""
        # Arrange - Setup all components
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage
        from src.patterns.analyzer import BehaviorAnalyzer
        from src.insights.generator import InsightGenerator

        db_path = temp_dir / "journal.db"
        storage = SQLiteStorage(db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)
        analyzer = BehaviorAnalyzer()
        insight_generator = InsightGenerator()

        # Act - User creates multiple journal entries
        entries = [
            JournalEntry(content="Started learning Python today", tags=["learning", "python"], metadata={"mood": "excited"}),
            JournalEntry(content="Completed first Python project", tags=["achievement", "python"], metadata={"mood": "proud"}),
            JournalEntry(
                content="Struggled with Python async programming",
                tags=["learning", "python", "challenge"],
                metadata={"mood": "frustrated"},
            ),
        ]

        for entry in entries:
            manager.create_entry(entry)

        # Act - User searches entries
        python_entries = manager.search_entries("Python")

        # Act - User analyzes patterns
        activities = [
            {"timestamp": entry.created_at, "action": "journal_entry", "tags": entry.tags} for entry in manager.list_entries()
        ]
        patterns = analyzer.detect_temporal_pattern(activities, "journal_entry")

        # Act - Generate insights
        insights = insight_generator.generate_daily_summary({"activities": activities})

        # Assert
        assert len(python_entries) == 3
        assert patterns["detected"] is True
        assert insights["type"] == "daily_summary"

    def test_secure_journal_workflow(self, temp_dir):
        """Test secure journal workflow with encryption."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage
        from src.security.vault import DataVault, VaultAccessControl
        from src.security.encryption import EncryptionService

        # Setup security components
        key = EncryptionService.generate_key()
        encryption_service = EncryptionService(key=key)

        vault = DataVault(base_path=temp_dir / "vault", encryption_service=encryption_service)

        access_control = VaultAccessControl(vault_path=temp_dir / "vault")
        access_control.grant_access(user_id="user123", resource="journal.db", permissions=["read", "write"])

        # Setup journal with encrypted storage
        db_path = temp_dir / "journal.db"
        storage = SQLiteStorage(db_path)
        storage.create_tables()
        manager = JournalManager(storage.connection)

        # Act - Create and encrypt entry
        entry = JournalEntry(content="Very private thoughts", tags=["private"], metadata={"sensitivity": "high"})
        created = manager.create_entry(entry)

        # Encrypt database backup
        backup_path = temp_dir / "backup.db"
        storage.create_backup(backup_path)

        encrypted_backup = encryption_service.encrypt(backup_path.read_bytes())
        vault.store_encrypted("journal_backup.db", encrypted_backup)

        # Act - Retrieve and decrypt (if authorized)
        if access_control.check_access("user123", "journal.db", "read"):
            retrieved_encrypted = vault.retrieve_decrypted("journal_backup.db")
            decrypted_data = encryption_service.decrypt(retrieved_encrypted)
            assert decrypted_data is not None

        # Assert
        assert created.id is not None
        assert (temp_dir / "vault" / "encrypted" / "journal_backup.db.enc").exists()

    def test_scheduled_insight_generation(self, temp_dir):
        """Test scheduled insight generation workflow."""
        # Arrange
        from datetime import datetime, timedelta
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage
        from src.tasks.scheduler import TaskScheduler, CronParser
        from src.insights.generator import InsightGenerator

        db_path = temp_dir / "journal.db"
        storage = SQLiteStorage(db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)
        scheduler = TaskScheduler()
        insight_generator = InsightGenerator()

        # Create journal entries over multiple days
        base_date = datetime(2024, 3, 1)
        for i in range(30):
            entry = JournalEntry(content=f"Day {i + 1} entry", tags=["daily"], created_at=base_date + timedelta(days=i))
            manager.create_entry(entry)

        # Act - Schedule weekly insight generation
        def generate_weekly_insight():
            entries = manager.list_entries()
            activities = [{"content": e.content, "date": e.created_at} for e in entries]
            return insight_generator.generate_weekly_review(
                [{"date": (base_date + timedelta(days=i)).isoformat(), "content": f"Day {i+1}"} for i in range(7)],
                week_start=base_date,
            )

        job_id = scheduler.add_job(
            func=generate_weekly_insight, trigger="cron", cron="0 9 * * 0", job_id="weekly_insights"  # Every Monday at 9 AM (0=Monday in this implementation)
        )

        # Act - Check next run time
        cron_parser = CronParser()
        next_run = cron_parser.get_next_run("0 9 * * 0", base_date + timedelta(days=6))

        # Assert
        assert job_id == "weekly_insights"
        assert next_run.weekday() == 0  # Monday

    def test_pattern_detection_to_recommendation(self, temp_dir):
        """Test full flow from pattern detection to recommendation."""
        # Arrange
        from datetime import datetime, timedelta
        from src.patterns.analyzer import BehaviorAnalyzer, TrendAnalyzer, PatternRecommender

        analyzer = BehaviorAnalyzer()
        trend_analyzer = TrendAnalyzer()
        recommender = PatternRecommender()

        # Simulate 30 days of work data
        work_sessions = []
        base_date = datetime(2024, 3, 1)

        for i in range(30):
            # Productivity increases over time
            productivity = 5 + (i * 0.5)
            work_sessions.append(
                {
                    "timestamp": base_date + timedelta(days=i, hours=9),
                    "action": "deep_work",
                    "output": productivity,
                    "duration": 120,
                }
            )

        # Act - Detect patterns
        temporal_pattern = analyzer.detect_temporal_pattern(work_sessions, "deep_work")

        # Act - Analyze trends
        outputs = [s["output"] for s in work_sessions]
        trend = trend_analyzer.detect_trend(outputs)

        # Act - Generate recommendations
        productivity_data = {
            "peak_hours": [9, 10, 14, 15],
            "focus_sessions": len(work_sessions),
            "improvement_trend": trend["direction"],
        }
        recommendations = recommender.generate_schedule_recommendations(productivity_data)

        # Assert
        assert temporal_pattern["detected"] is True
        assert trend["direction"] == "increasing"
        assert len(recommendations) > 0

    def test_backup_restore_recovery(self, temp_dir):
        """Test complete backup, restore, and recovery workflow."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage
        from src.security.vault import DataVault
        from src.security.encryption import EncryptionService

        db_path = temp_dir / "journal.db"
        storage = SQLiteStorage(db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        # Create important data
        for i in range(10):
            entry = JournalEntry(content=f"Important entry {i}", tags=["important"], metadata={"priority": "high"})
            manager.create_entry(entry)

        # Setup encrypted backup
        key = EncryptionService.generate_key()
        encryption_service = EncryptionService(key=key)
        vault = DataVault(base_path=temp_dir / "vault", encryption_service=encryption_service)

        # Act - Create encrypted backup
        backup_path = temp_dir / "backup.db"
        storage.create_backup(backup_path)

        encrypted_backup = encryption_service.encrypt(backup_path.read_bytes())
        vault.store_encrypted("journal_backup.db", encrypted_backup)

        # Act - Simulate data loss
        for entry in manager.list_entries():
            manager.delete_entry(entry.id)

        assert len(manager.list_entries()) == 0

        # Act - Restore from encrypted backup
        retrieved_encrypted = vault.retrieve_decrypted("journal_backup.db")
        decrypted_data = encryption_service.decrypt(retrieved_encrypted)

        # Write decrypted backup and restore
        restore_path = temp_dir / "restore.db"
        restore_path.write_bytes(decrypted_data)

        restore_result = storage.restore_from_backup(restore_path)

        # Re-create manager with new connection after restore
        manager = JournalManager(storage.connection)

        # Assert
        assert restore_result is True
        assert len(manager.list_entries()) == 10

    def test_multi_user_access_control(self, temp_dir):
        """Test multi-user access control workflow."""
        # Arrange
        from src.security.vault import DataVault, VaultAccessControl
        from src.security.encryption import EncryptionService

        key = EncryptionService.generate_key()
        encryption_service = EncryptionService(key=key)

        vault = DataVault(base_path=temp_dir, encryption_service=encryption_service)

        access_control = VaultAccessControl(vault_path=temp_dir)

        # Setup users with different permissions
        access_control.grant_access(user_id="admin", resource="sensitive_data.txt", permissions=["read", "write", "delete"])

        access_control.grant_access(user_id="user1", resource="sensitive_data.txt", permissions=["read"])

        access_control.grant_access(user_id="user2", resource="public_data.txt", permissions=["read", "write"])

        # Act & Assert
        # Admin should have full access
        assert access_control.check_access("admin", "sensitive_data.txt", "read") is True
        assert access_control.check_access("admin", "sensitive_data.txt", "delete") is True

        # User1 should only have read access
        assert access_control.check_access("user1", "sensitive_data.txt", "read") is True
        assert access_control.check_access("user1", "sensitive_data.txt", "write") is False

        # User2 should not have access to sensitive data
        assert access_control.check_access("user2", "sensitive_data.txt", "read") is False

        # User2 should have access to public data
        assert access_control.check_access("user2", "public_data.txt", "write") is True

    def test_data_migration_workflow(self, temp_dir):
        """Test data migration workflow across versions."""
        # Arrange
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage

        db_path = temp_dir / "journal.db"
        storage = SQLiteStorage(db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)

        # Create entries in current version
        for i in range(5):
            entry = JournalEntry(content=f"Entry {i}")
            manager.create_entry(entry)

        initial_version = storage.get_schema_version()

        # Act - Migrate to new version
        migration_result = storage.migrate_to_version(2)
        new_version = storage.get_schema_version()

        # Act - Verify data integrity after migration
        entries_after_migration = manager.list_entries()

        # Assert
        assert initial_version == 1
        assert migration_result is True
        assert new_version == 2
        assert len(entries_after_migration) == 5

    def test_complete_analytics_workflow(self, temp_dir):
        """Test complete analytics workflow from data to report."""
        # Arrange
        from datetime import datetime, timedelta
        from src.journal.core import JournalEntry, JournalManager
        from src.journal.storage import SQLiteStorage
        from src.patterns.analyzer import ProductivityAnalyzer, PatternRecommender
        from src.insights.generator import ReportGenerator

        db_path = temp_dir / "journal.db"
        storage = SQLiteStorage(db_path)
        storage.create_tables()

        manager = JournalManager(storage.connection)
        productivity_analyzer = ProductivityAnalyzer()
        recommender = PatternRecommender()
        report_generator = ReportGenerator()

        # Create 30 days of work sessions
        base_date = datetime(2024, 3, 1)
        work_sessions = []

        for i in range(30):
            entry = JournalEntry(
                content=f"Work session {i + 1}",
                tags=["work"],
                created_at=base_date + timedelta(days=i),
                metadata={"duration": 120, "productivity_score": 5 + (i % 5)},
            )
            manager.create_entry(entry)

            work_sessions.append(
                {
                    "start": base_date + timedelta(days=i, hours=9),
                    "end": base_date + timedelta(days=i, hours=11),
                    "output": 5 + (i % 5),
                }
            )

        # Act - Analyze productivity
        peak_hours = productivity_analyzer.find_peak_productivity_hours(work_sessions)

        # Act - Generate recommendations
        productivity_data = {"peak_hours": list(peak_hours.keys())[:3]}
        recommendations = recommender.generate_schedule_recommendations(productivity_data)

        # Act - Generate report
        goals = [
            {
                "name": "Increase Productivity",
                "target": 100,
                "current": sum(s["output"] for s in work_sessions),
                "unit": "points",
            }
        ]

        report = report_generator.generate_progress_report(
            goals, period_start=base_date, period_end=base_date + timedelta(days=30)
        )

        # Act - Export report
        report_path = temp_dir / "report.json"
        report_generator.export_to_json(report, report_path)

        # Assert
        assert len(peak_hours) > 0
        assert len(recommendations) > 0
        assert report["type"] == "progress_report"
        assert report_path.exists()
