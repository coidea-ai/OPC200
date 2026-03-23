"""
Unit tests for security/vault.py - Data vault functionality.
Following TDD: Red-Green-Refactor cycle.
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit


class TestDataVault:
    """Tests for data vault functionality."""

    def test_vault_initialization(self, temp_dir):
        """Test data vault initialization."""
        # Arrange & Act
        from src.security.vault import DataVault

        vault = DataVault(base_path=temp_dir)

        # Assert
        assert vault.base_path == temp_dir
        assert (temp_dir / "encrypted").exists()
        assert (temp_dir / "keys").exists()
        assert (temp_dir / "audit").exists()

    def test_vault_create_directories(self, temp_dir):
        """Test vault creates required directories."""
        # Arrange
        from src.security.vault import DataVault

        vault = DataVault(base_path=temp_dir)

        # Act
        vault._create_directories()

        # Assert
        assert (temp_dir / "encrypted").is_dir()
        assert (temp_dir / "keys").is_dir()
        assert (temp_dir / "audit").is_dir()
        assert (temp_dir / "temp").is_dir()

    def test_store_encrypted_file(self, temp_dir, mock_encryption_service):
        """Test storing an encrypted file."""
        # Arrange
        from src.security.vault import DataVault

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        content = b"Sensitive data to encrypt"

        # Act
        result = vault.store_encrypted("test_file.txt", content)

        # Assert
        assert result is True
        mock_encryption_service.encrypt.assert_called_once()

        # Verify file was created
        encrypted_file = temp_dir / "encrypted" / "test_file.txt.enc"
        assert encrypted_file.exists()

    def test_retrieve_decrypted_file(self, temp_dir, mock_encryption_service):
        """Test retrieving and decrypting a file."""
        # Arrange
        from src.security.vault import DataVault

        mock_encryption_service.decrypt.return_value = b"Decrypted content"

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        # Create encrypted file
        encrypted_path = temp_dir / "encrypted" / "test_file.txt.enc"
        encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted_path.write_bytes(b"encrypted_data")

        # Act
        result = vault.retrieve_decrypted("test_file.txt")

        # Assert
        assert result == b"Decrypted content"
        mock_encryption_service.decrypt.assert_called_once()

    def test_retrieve_nonexistent_file(self, temp_dir, mock_encryption_service):
        """Test retrieving a non-existent file returns None."""
        # Arrange
        from src.security.vault import DataVault

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        # Act
        result = vault.retrieve_decrypted("nonexistent.txt")

        # Assert
        assert result is None

    def test_delete_encrypted_file(self, temp_dir, mock_encryption_service):
        """Test deleting an encrypted file."""
        # Arrange
        from src.security.vault import DataVault

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        # Create file to delete
        encrypted_path = temp_dir / "encrypted" / "test_file.txt.enc"
        encrypted_path.parent.mkdir(parents=True, exist_ok=True)
        encrypted_path.write_bytes(b"encrypted_data")

        # Act
        result = vault.delete("test_file.txt")

        # Assert
        assert result is True
        assert not encrypted_path.exists()

    def test_list_encrypted_files(self, temp_dir, mock_encryption_service):
        """Test listing encrypted files."""
        # Arrange
        from src.security.vault import DataVault

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        # Create test files
        encrypted_dir = temp_dir / "encrypted"
        (encrypted_dir / "file1.txt.enc").write_bytes(b"data1")
        (encrypted_dir / "file2.txt.enc").write_bytes(b"data2")
        (encrypted_dir / "not_encrypted.txt").write_bytes(b"data3")

        # Act
        results = vault.list_files()

        # Assert
        assert len(results) == 2
        assert "file1.txt" in results
        assert "file2.txt" in results
        assert "not_encrypted.txt" not in results


class TestVaultAccessControl:
    """Tests for vault access control."""

    def test_access_control_initialization(self, temp_dir):
        """Test access control initialization."""
        # Arrange & Act
        from src.security.vault import VaultAccessControl

        ac = VaultAccessControl(vault_path=temp_dir)

        # Assert
        assert ac.vault_path == temp_dir
        assert (temp_dir / "access_policy.json").exists()

    def test_grant_access(self, temp_dir):
        """Test granting access to a user."""
        # Arrange
        from src.security.vault import VaultAccessControl

        ac = VaultAccessControl(vault_path=temp_dir)

        # Act
        result = ac.grant_access(user_id="user123", resource="sensitive_data.txt", permissions=["read", "write"])

        # Assert
        assert result is True

        perms = ac.get_permissions("user123", "sensitive_data.txt")
        assert "read" in perms
        assert "write" in perms

    def test_revoke_access(self, temp_dir):
        """Test revoking access from a user."""
        # Arrange
        from src.security.vault import VaultAccessControl

        ac = VaultAccessControl(vault_path=temp_dir)
        ac.grant_access(user_id="user123", resource="sensitive_data.txt", permissions=["read", "write"])

        # Act
        result = ac.revoke_access("user123", "sensitive_data.txt")

        # Assert
        assert result is True

        perms = ac.get_permissions("user123", "sensitive_data.txt")
        assert len(perms) == 0

    def test_check_access_allowed(self, temp_dir):
        """Test checking allowed access."""
        # Arrange
        from src.security.vault import VaultAccessControl

        ac = VaultAccessControl(vault_path=temp_dir)
        ac.grant_access(user_id="user123", resource="sensitive_data.txt", permissions=["read"])

        # Act & Assert
        assert ac.check_access("user123", "sensitive_data.txt", "read") is True
        assert ac.check_access("user123", "sensitive_data.txt", "write") is False

    def test_check_access_denied(self, temp_dir):
        """Test checking denied access."""
        # Arrange
        from src.security.vault import VaultAccessControl

        ac = VaultAccessControl(vault_path=temp_dir)

        # Act & Assert
        assert ac.check_access("unknown_user", "sensitive_data.txt", "read") is False

    def test_time_based_access_restriction(self, temp_dir):
        """Test time-based access restrictions."""
        # Arrange
        from datetime import datetime, time
        from src.security.vault import VaultAccessControl

        ac = VaultAccessControl(vault_path=temp_dir)
        ac.grant_access(
            user_id="user123",
            resource="sensitive_data.txt",
            permissions=["read"],
            time_restrictions={"start_time": "09:00", "end_time": "17:00"},
        )

        # Act & Assert - Check within allowed hours
        with patch("src.security.vault.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 3, 15, 12, 0)  # 12:00 PM
            assert ac.check_access("user123", "sensitive_data.txt", "read") is True

        # Check outside allowed hours
        with patch("src.security.vault.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2024, 3, 15, 20, 0)  # 8:00 PM
            assert ac.check_access("user123", "sensitive_data.txt", "read") is False


class TestVaultKeyManagement:
    """Tests for vault key management."""

    def test_key_manager_initialization(self, temp_dir):
        """Test key manager initialization."""
        # Arrange & Act
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")

        # Assert
        assert km.keys_path == temp_dir / "keys"
        assert km.keys_path.exists()

    def test_generate_key(self, temp_dir):
        """Test generating a new key."""
        # Arrange
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")

        # Act
        key_id, key = km.generate_key(key_type="master")

        # Assert
        assert key_id is not None
        assert len(key) > 0
        assert (temp_dir / "keys" / f"{key_id}.key").exists()

    def test_load_key(self, temp_dir):
        """Test loading a saved key."""
        # Arrange
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")
        key_id, original_key = km.generate_key(key_type="master")

        # Act
        loaded_key = km.load_key(key_id)

        # Assert
        assert loaded_key == original_key

    def test_load_nonexistent_key(self, temp_dir):
        """Test loading a non-existent key returns None."""
        # Arrange
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")

        # Act
        result = km.load_key("nonexistent")

        # Assert
        assert result is None

    def test_rotate_key(self, temp_dir):
        """Test key rotation."""
        # Arrange
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")
        old_key_id, old_key = km.generate_key(key_type="master")

        # Act
        new_key_id, new_key = km.rotate_key(old_key_id)

        # Assert
        assert new_key_id != old_key_id
        assert new_key != old_key
        assert (temp_dir / "keys" / f"{old_key_id}.key.old").exists()

    def test_delete_key(self, temp_dir):
        """Test deleting a key."""
        # Arrange
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")
        key_id, key = km.generate_key(key_type="master")

        # Act
        result = km.delete_key(key_id)

        # Assert
        assert result is True
        assert not (temp_dir / "keys" / f"{key_id}.key").exists()

    def test_list_keys(self, temp_dir):
        """Test listing all keys."""
        # Arrange
        from src.security.vault import KeyManager

        km = KeyManager(keys_path=temp_dir / "keys")
        km.generate_key(key_type="master")
        km.generate_key(key_type="data")

        # Act
        keys = km.list_keys()

        # Assert
        assert len(keys) == 2


class TestVaultAudit:
    """Tests for vault audit logging."""

    def test_audit_logger_initialization(self, temp_dir):
        """Test audit logger initialization."""
        # Arrange & Act
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Assert
        assert audit.audit_path == temp_dir / "audit"
        assert audit.audit_path.exists()

    def test_log_access(self, temp_dir):
        """Test logging access event."""
        # Arrange
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Act
        result = audit.log_access(user_id="user123", action="read", resource="sensitive_data.txt", success=True)

        # Assert
        assert result is True

        # Verify log file was created
        log_files = list((temp_dir / "audit").glob("*.log"))
        assert len(log_files) > 0

    def test_log_access_failure(self, temp_dir):
        """Test logging failed access attempt."""
        # Arrange
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Act
        result = audit.log_access(
            user_id="user456", action="write", resource="protected.txt", success=False, reason="Insufficient permissions"
        )

        # Assert
        assert result is True

    def test_get_access_history(self, temp_dir):
        """Test retrieving access history."""
        # Arrange
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")
        audit.log_access("user123", "read", "file1.txt", True)
        audit.log_access("user123", "write", "file1.txt", True)
        audit.log_access("user456", "read", "file1.txt", False)

        # Act
        history = audit.get_access_history(user_id="user123")

        # Assert
        assert len(history) == 2
        assert all(h["user_id"] == "user123" for h in history)

    def test_get_resource_access_log(self, temp_dir):
        """Test retrieving access log for a specific resource."""
        # Arrange
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")
        audit.log_access("user123", "read", "file1.txt", True)
        audit.log_access("user123", "read", "file2.txt", True)
        audit.log_access("user456", "read", "file1.txt", False)

        # Act
        history = audit.get_resource_access_log("file1.txt")

        # Assert
        assert len(history) == 2
        assert all(h["resource"] == "file1.txt" for h in history)

    def test_audit_retention_cleanup(self, temp_dir):
        """Test cleanup of old audit logs."""
        # Arrange
        from datetime import datetime, timedelta
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Create old log file
        old_log = temp_dir / "audit" / "2024-01-01.log"
        old_log.write_text("Old log entry")

        # Act
        result = audit.cleanup_old_logs(retention_days=30)

        # Assert
        assert result is True
        assert not old_log.exists()


class TestVaultIntegrity:
    """Tests for vault integrity verification."""

    def test_integrity_verification(self, temp_dir, mock_encryption_service):
        """Test vault integrity verification."""
        # Arrange
        from src.security.vault import DataVault, VaultIntegrity

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        integrity = VaultIntegrity(vault)

        # Create test file
        vault.store_encrypted("test.txt", b"test data")

        # Act
        result = integrity.verify_all_files()

        # Assert
        assert result is True

    def test_detect_tampering(self, temp_dir, mock_encryption_service):
        """Test detecting tampered files."""
        # Arrange
        from src.security.vault import DataVault, VaultIntegrity

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        integrity = VaultIntegrity(vault)

        # Create test file
        vault.store_encrypted("test.txt", b"test data")

        # Tamper with file
        encrypted_file = temp_dir / "encrypted" / "test.txt.enc"
        content = encrypted_file.read_bytes()
        encrypted_file.write_bytes(content[:-5] + b"TAMPERED")

        # Act
        result = integrity.verify_all_files()

        # Assert
        assert result is False

    def test_repair_integrity(self, temp_dir, mock_encryption_service):
        """Test repairing vault integrity."""
        # Arrange
        from src.security.vault import DataVault, VaultIntegrity

        vault = DataVault(base_path=temp_dir, encryption_service=mock_encryption_service)

        integrity = VaultIntegrity(vault)

        # Create backup
        vault.store_encrypted("test.txt", b"test data")
        integrity.create_backup_checksums()

        # Act
        result = integrity.repair_from_backup()

        # Assert
        assert result is True
