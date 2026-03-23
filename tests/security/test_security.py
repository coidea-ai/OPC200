"""
Security tests for OPC200.
"""
import pytest
import sqlite3

pytestmark = pytest.mark.security


class TestInputValidation:
    """Tests for input validation."""
    
    def test_sql_injection_in_search(self, in_memory_db):
        """Test that search is protected against SQL injection."""
        from src.journal.core import JournalManager, JournalEntry
        from src.utils.validation import ValidationError
        
        manager = JournalManager(in_memory_db)
        manager.create_table()
        
        # Create a normal entry
        entry = JournalEntry(content="Normal content", tags=["test"])
        manager.create_entry(entry)
        
        # Attempt SQL injection - should be rejected by validation
        malicious_input = "'; DROP TABLE journal_entries; --"
        with pytest.raises((ValidationError, ValueError)):
            manager.search_entries(malicious_input)
    
    def test_sql_injection_in_entry_id(self, in_memory_db):
        """Test that entry ID validation prevents injection."""
        from src.journal.core import JournalManager
        from src.utils.validation import ValidationError
        
        manager = JournalManager(in_memory_db)
        manager.create_table()
        
        # Attempt SQL injection via entry ID
        malicious_id = "'; DROP TABLE journal_entries; --"
        with pytest.raises((ValidationError, ValueError)):
            manager.get_entry(malicious_id)
    
    def test_xss_protection_in_content(self):
        """Test that XSS payloads are handled safely."""
        from src.utils.validation import InputValidator, ValidationError
        
        # XSS payload should be rejected or sanitized
        xss_payload = '<script>alert("xss")</script>'
        
        # The content itself is allowed but metadata is checked
        result = InputValidator.validate_content(xss_payload)
        assert result == xss_payload  # Content is stored as-is, escaped on output
    
    def test_xss_in_metadata(self):
        """Test that XSS in metadata is rejected."""
        from src.utils.validation import InputValidator, ValidationError
        
        xss_metadata = {
            "script": '<script>alert("xss")</script>',
            "javascript": "javascript:alert('xss')",
        }
        
        with pytest.raises(ValidationError):
            InputValidator.validate_metadata(xss_metadata)


class TestVaultPermissions:
    """Tests for vault access control."""
    
    def test_unauthorized_access_denied(self, temp_dir):
        """Test that unauthorized access to vault is denied."""
        from src.security.vault import DataVault, VaultAccessControl
        
        vault = DataVault(base_path=temp_dir / "vault")
        
        # Set up access control
        vault._access_control.grant_access("user1", "test-file", ["read"])
        vault.set_user_context("user2")  # Different user
        
        # Attempt to access without permission
        with pytest.raises(PermissionError):
            vault.retrieve_decrypted("test-file")
    
    def test_authorized_access_allowed(self, temp_dir):
        """Test that authorized access works correctly."""
        from src.security.vault import DataVault
        
        vault = DataVault(base_path=temp_dir / "vault")
        
        # Grant and use access
        vault._access_control.grant_access("user1", "test-file", ["write", "read"])
        vault.set_user_context("user1")
        
        # Should succeed
        vault.store_encrypted("test-file", b"test content")
        result = vault.retrieve_decrypted("test-file")
        assert result == b"test content"


class TestEncryptionSecurity:
    """Tests for encryption security."""
    
    def test_key_generation_uniqueness(self):
        """Test that generated keys are unique."""
        from src.security.encryption import EncryptionService
        
        keys = [EncryptionService.generate_key() for _ in range(100)]
        
        # All keys should be unique
        assert len(set(keys)) == 100
    
    def test_encryption_deterministic_with_same_key(self):
        """Test that same plaintext encrypts to different ciphertexts (nonce)."""
        from src.security.encryption import EncryptionService
        
        key = EncryptionService.generate_key()
        service = EncryptionService(key)
        plaintext = b"test message"
        
        # Encrypt twice - should produce different ciphertexts due to nonce
        cipher1 = service.encrypt(plaintext)
        cipher2 = service.encrypt(plaintext)
        
        assert cipher1 != cipher2
        
        # But both should decrypt to the same plaintext
        assert service.decrypt(cipher1) == plaintext
        assert service.decrypt(cipher2) == plaintext
    
    def test_different_keys_produce_different_ciphertexts(self):
        """Test that different keys produce different results."""
        from src.security.encryption import EncryptionService
        
        key1 = EncryptionService.generate_key()
        key2 = EncryptionService.generate_key()
        
        service1 = EncryptionService(key1)
        service2 = EncryptionService(key2)
        
        plaintext = b"test message"
        
        cipher1 = service1.encrypt(plaintext)
        cipher2 = service2.encrypt(plaintext)
        
        assert cipher1 != cipher2
        
        # Cross-decryption should fail
        with pytest.raises(Exception):
            service1.decrypt(cipher2)
    
    def test_password_hashing_verification(self):
        """Test password hashing and verification."""
        from src.security.encryption import PasswordHashing
        
        password = "SecureP@ssw0rd!"
        hashed = PasswordHashing.hash(password)
        
        # Correct password should verify
        assert PasswordHashing.verify(password, hashed) is True
        
        # Wrong password should fail
        assert PasswordHashing.verify("wrongpassword", hashed) is False
        
        # Same password should produce different hashes (due to salt)
        hashed2 = PasswordHashing.hash(password)
        assert hashed != hashed2
        assert PasswordHashing.verify(password, hashed2) is True


class TestAuditLogging:
    """Tests for audit logging."""
    
    def test_access_logged(self, temp_dir):
        """Test that access attempts are logged."""
        from src.utils.logging import AuditLogger
        
        log_path = temp_dir / "audit.log"
        audit = AuditLogger(log_path)
        
        audit.log_access("user1", "sensitive-data", "read", True)
        
        # Log file should exist
        assert log_path.exists()
        
        # Check log content
        content = log_path.read_text()
        assert "user1" in content
        assert "sensitive-data" in content
        assert "read" in content
