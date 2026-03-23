"""
Integration tests for security flow - Vault, encryption and access control.
Following TDD: Red-Green-Refactor cycle.
"""

from unittest.mock import Mock

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.security]


class TestSecurityVaultFlow:
    """Integration tests for security vault flow."""

    def test_store_retrieve_encrypted_file(self, temp_dir):
        """Test storing and retrieving encrypted file."""
        # Arrange
        from src.security.vault import DataVault
        from src.security.encryption import EncryptionService

        key = EncryptionService.generate_key()
        encryption_service = EncryptionService(key=key)

        vault = DataVault(base_path=temp_dir, encryption_service=encryption_service)

        content = b"Sensitive data that needs protection"

        # Act - Store
        store_result = vault.store_encrypted("sensitive.txt", content)

        # Act - Retrieve
        retrieved = vault.retrieve_decrypted("sensitive.txt")

        # Assert
        assert store_result is True
        assert retrieved == content

    def test_vault_with_access_control(self, temp_dir):
        """Test vault with access control integration."""
        # Arrange
        from src.security.vault import DataVault, VaultAccessControl
        from src.security.encryption import EncryptionService

        key = EncryptionService.generate_key()
        encryption_service = EncryptionService(key=key)

        vault = DataVault(base_path=temp_dir, encryption_service=encryption_service)

        access_control = VaultAccessControl(vault_path=temp_dir)

        # Grant access
        access_control.grant_access(user_id="user123", resource="secret.txt", permissions=["read", "write"])

        # Act & Assert
        assert access_control.check_access("user123", "secret.txt", "read") is True
        assert access_control.check_access("user123", "secret.txt", "write") is True
        assert access_control.check_access("user123", "secret.txt", "delete") is False
        assert access_control.check_access("user456", "secret.txt", "read") is False

    def test_vault_audit_logging(self, temp_dir):
        """Test vault audit logging."""
        # Arrange
        from src.security.vault import DataVault, VaultAudit
        from src.security.encryption import EncryptionService

        key = EncryptionService.generate_key()
        encryption_service = EncryptionService(key=key)

        vault = DataVault(base_path=temp_dir, encryption_service=encryption_service)

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Act - Store file
        vault.store_encrypted("test.txt", b"test data")
        audit.log_access(user_id="user123", action="write", resource="test.txt", success=True)

        # Act - Retrieve
        vault.retrieve_decrypted("test.txt")
        audit.log_access(user_id="user123", action="read", resource="test.txt", success=True)

        # Assert
        history = audit.get_access_history("user123")
        assert len(history) == 2
        assert history[0]["action"] == "write"
        assert history[1]["action"] == "read"


class TestEncryptionServiceFlow:
    """Integration tests for encryption service flow."""

    def test_encrypt_decrypt_file(self, temp_dir):
        """Test encrypting and decrypting a file."""
        # Arrange
        from src.security.encryption import EncryptionService

        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)

        input_file = temp_dir / "input.txt"
        encrypted_file = temp_dir / "encrypted.bin"
        decrypted_file = temp_dir / "decrypted.txt"

        original_content = "Secret message"
        input_file.write_text(original_content)

        # Act - Encrypt
        encrypt_result = service.encrypt_file(input_file, encrypted_file)

        # Act - Decrypt
        decrypt_result = service.decrypt_file(encrypted_file, decrypted_file)

        # Assert
        assert encrypt_result is True
        assert decrypt_result is True
        assert decrypted_file.read_text() == original_content

    def test_key_derivation_and_encryption(self, temp_dir):
        """Test key derivation and encryption integration."""
        # Arrange
        from src.security.encryption import EncryptionService, KeyDerivation

        password = "my_secure_password"
        key, salt = KeyDerivation.derive_from_password(password)

        service = EncryptionService(key=key)

        # Act
        plaintext = b"Data encrypted with password-derived key"
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)

        # Assert
        assert decrypted == plaintext

    def test_password_hashing_verification(self):
        """Test password hashing and verification."""
        # Arrange
        from src.security.encryption import PasswordHashing

        password = "user_password"

        # Act
        hashed = PasswordHashing.hash(password)

        # Assert - Correct password
        assert PasswordHashing.verify(password, hashed) is True

        # Assert - Wrong password
        assert PasswordHashing.verify("wrong_password", hashed) is False


class TestKeyManagementFlow:
    """Integration tests for key management flow."""

    def test_generate_store_load_key(self, temp_dir):
        """Test generating, storing, and loading a key."""
        # Arrange
        from src.security.vault import KeyManager

        manager = KeyManager(keys_path=temp_dir / "keys")

        # Act - Generate
        key_id, original_key = manager.generate_key(key_type="master")

        # Act - Load
        loaded_key = manager.load_key(key_id)

        # Assert
        assert loaded_key == original_key

    def test_key_rotation(self, temp_dir):
        """Test key rotation process."""
        # Arrange
        from src.security.vault import KeyManager

        manager = KeyManager(keys_path=temp_dir / "keys")
        old_key_id, old_key = manager.generate_key(key_type="data")

        # Act - Rotate
        new_key_id, new_key = manager.rotate_key(old_key_id)

        # Assert
        assert new_key_id != old_key_id
        assert new_key != old_key

        # Old key should be backed up
        assert (temp_dir / "keys" / f"{old_key_id}.key.old").exists()

    def test_list_and_delete_keys(self, temp_dir):
        """Test listing and deleting keys."""
        # Arrange
        from src.security.vault import KeyManager

        manager = KeyManager(keys_path=temp_dir / "keys")

        key1_id, _ = manager.generate_key(key_type="master")
        key2_id, _ = manager.generate_key(key_type="data")

        # Act - List
        keys = manager.list_keys()

        # Assert
        assert len(keys) == 2

        # Act - Delete
        manager.delete_key(key1_id)
        keys = manager.list_keys()

        # Assert
        assert len(keys) == 1
        assert key1_id not in keys


class TestSecurityAuditFlow:
    """Integration tests for security audit flow."""

    def test_access_logging_and_retrieval(self, temp_dir):
        """Test access logging and history retrieval."""
        # Arrange
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Act - Log multiple access events
        audit.log_access("user1", "read", "file1.txt", True)
        audit.log_access("user1", "write", "file1.txt", True)
        audit.log_access("user2", "read", "file2.txt", False, "Access denied")

        # Assert
        user1_history = audit.get_access_history("user1")
        assert len(user1_history) == 2

        file1_history = audit.get_resource_access_log("file1.txt")
        assert len(file1_history) == 2

    def test_audit_log_cleanup(self, temp_dir):
        """Test audit log cleanup based on retention."""
        # Arrange
        from datetime import datetime, timedelta
        from src.security.vault import VaultAudit

        audit = VaultAudit(audit_path=temp_dir / "audit")

        # Create old log file
        old_date = datetime.now() - timedelta(days=100)
        old_log_file = temp_dir / "audit" / f"{old_date.strftime('%Y-%m-%d')}.log"
        old_log_file.parent.mkdir(parents=True, exist_ok=True)
        old_log_file.write_text("Old log entry")

        # Act
        result = audit.cleanup_old_logs(retention_days=30)

        # Assert
        assert result is True
        assert not old_log_file.exists()


class TestEndToEndEncryptionFlow:
    """End-to-end encryption flow tests."""

    def test_full_encryption_workflow(self, temp_dir):
        """Test full encryption workflow from file to vault."""
        # Arrange
        from src.security.vault import DataVault
        from src.security.encryption import EncryptionService, KeyManager

        # Setup
        key_manager = KeyManager(keys_path=temp_dir / "keys")
        key_id, key = key_manager.generate_key(key_type="master")

        encryption_service = EncryptionService(key=key)
        vault = DataVault(base_path=temp_dir, encryption_service=encryption_service)

        # Create sensitive file
        sensitive_file = temp_dir / "sensitive.txt"
        sensitive_file.write_text("Top secret information")

        # Act - Encrypt and store in vault
        encrypted_content = encryption_service.encrypt(sensitive_file.read_bytes())
        vault.store_encrypted("sensitive.txt", encrypted_content)

        # Act - Retrieve and decrypt
        retrieved_encrypted = vault.retrieve_decrypted("sensitive.txt")
        decrypted_content = encryption_service.decrypt(retrieved_encrypted)

        # Assert
        assert decrypted_content.decode() == "Top secret information"
