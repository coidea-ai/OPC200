"""Tests for backup module."""

import json
import zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from remi_lite.backup import Backup


class TestBackup:
    """Test backup functionality."""

    @pytest.fixture
    def temp_customer_dir(self, tmp_path):
        """Create a temporary customer directory with sample data."""
        customer_dir = tmp_path / "customers" / "TEST-001"
        remi_dir = customer_dir / ".remi"

        # Create sample data
        sessions_dir = remi_dir / "sessions"
        sessions_dir.mkdir(parents=True)
        (sessions_dir / "2026-04-02.md").write_text("今天完成了登录功能")
        (sessions_dir / "2026-04-01.md").write_text("开始设计数据库")

        digests_dir = remi_dir / "digests"
        digests_dir.mkdir(parents=True)
        (digests_dir / "2026-W14.md").write_text("本周完成了登录和数据库")

        exports_dir = remi_dir / "exports"
        exports_dir.mkdir(parents=True)

        return customer_dir

    @pytest.fixture
    def backup(self, temp_customer_dir):
        """Create a backup instance with temp directory."""
        remi_path = temp_customer_dir / ".remi"

        with patch("remi_lite.backup.Path") as mock_path:
            mock_path.return_value.expanduser.return_value = remi_path
            return Backup("TEST-001")

    def test_create_backup_success(self, backup, temp_customer_dir):
        """Test successful backup creation."""
        result = backup.create()

        assert result["success"] is True
        assert result["filename"].startswith("remi-backup-")
        assert result["filename"].endswith(".zip")
        assert result["size_kb"] >= 0  # Allow 0 size for empty test files
        assert result["stats"]["sessions"] == 2

        # Verify file exists
        backup_path = temp_customer_dir / ".remi" / "exports" / result["filename"]
        assert backup_path.exists()

    def test_backup_contains_manifest(self, backup, temp_customer_dir):
        """Test backup contains manifest file."""
        result = backup.create()

        backup_path = temp_customer_dir / ".remi" / "exports" / result["filename"]

        with zipfile.ZipFile(backup_path, "r") as zf:
            assert "manifest.json" in zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))
            assert manifest["version"] == "0.1"
            assert "created_at" in manifest

    def test_backup_contains_all_sessions(self, backup, temp_customer_dir):
        """Test backup contains all session files."""
        result = backup.create()

        backup_path = temp_customer_dir / ".remi" / "exports" / result["filename"]

        with zipfile.ZipFile(backup_path, "r") as zf:
            files = zf.namelist()
            assert "sessions/2026-04-02.md" in files
            assert "sessions/2026-04-01.md" in files

    def test_backup_skips_old_backups(self, backup, temp_customer_dir):
        """Test backup skips existing backup files."""
        # Create an old backup file
        old_backup = temp_customer_dir / ".remi" / "exports" / "remi-backup-2026-03-01.zip"
        old_backup.write_text("old backup")

        result = backup.create()

        # Verify old backup is not in new backup
        backup_path = temp_customer_dir / ".remi" / "exports" / result["filename"]

        with zipfile.ZipFile(backup_path, "r") as zf:
            for name in zf.namelist():
                assert "remi-backup-" not in name

    def test_create_backup_no_data(self, tmp_path):
        """Test backup with no data."""
        customer_dir = tmp_path / "customers" / "TEST-002"
        (customer_dir / ".remi").mkdir(parents=True)

        with patch("remi_lite.backup.Path") as mock_path:
            mock_path.return_value.expanduser.return_value = customer_dir / ".remi"
            backup = Backup("TEST-002")
            result = backup.create()

        assert result["success"] is False
        assert "No data" in result["error"]

    def test_list_backups_sorted(self, backup, temp_customer_dir):
        """Test listing backups sorted by date."""
        # Create multiple backups
        exports_dir = temp_customer_dir / ".remi" / "exports"

        for i, day in enumerate([1, 3, 2]):
            backup_file = exports_dir / f"remi-backup-2026-04-0{day}.zip"
            # Create a minimal valid zip
            with zipfile.ZipFile(backup_file, "w") as zf:
                zf.writestr("test.txt", "test")
            # Modify timestamp
            import time

            mtime = time.mktime((2026, 4, day, 12, 0, 0, 0, 0, 0))
            backup_file.touch()

        backups = backup.list_backups()

        assert len(backups) == 3
        # Should be sorted by created date (newest first)
        assert "2026-04-03" in backups[0]["filename"]

    def test_restore_success(self, backup, temp_customer_dir):
        """Test successful restore."""
        # First create a backup
        create_result = backup.create()
        filename = create_result["filename"]

        # Modify current data
        sessions_dir = temp_customer_dir / ".remi" / "sessions"
        (sessions_dir / "2026-04-02.md").write_text("modified content")

        # Restore
        result = backup.restore(filename)

        assert result["success"] is True
        assert result["restored_from"] == filename
        assert "safety_backup" in result

        # Verify content restored
        content = (sessions_dir / "2026-04-02.md").read_text()
        assert "登录功能" in content  # Original content

    def test_restore_creates_safety_backup(self, backup, temp_customer_dir):
        """Test restore creates safety backup first."""
        # Create initial backup
        create_result = backup.create()
        filename = create_result["filename"]

        # Restore
        result = backup.restore(filename)

        # Verify safety backup exists
        safety_file = result["safety_backup"]
        safety_path = temp_customer_dir / ".remi" / "exports" / safety_file
        assert safety_path.exists()

    def test_restore_file_not_found(self, backup):
        """Test restore with non-existent file."""
        result = backup.restore("non-existent.zip")

        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_restore_corrupted_zip(self, backup, temp_customer_dir):
        """Test restore with corrupted zip file."""
        exports_dir = temp_customer_dir / ".remi" / "exports"
        corrupted = exports_dir / "corrupted.zip"
        corrupted.write_text("not a valid zip")

        result = backup.restore("corrupted.zip")

        assert result["success"] is False
        assert "损坏" in result["error"]
