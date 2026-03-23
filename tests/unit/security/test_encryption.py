"""
Unit tests for security/encryption.py - Encryption functionality.
Following TDD: Red-Green-Refactor cycle.
"""
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.security]


class TestEncryptionService:
    """Tests for encryption service."""
    
    def test_encryption_service_initialization(self):
        """Test encryption service initialization."""
        # Arrange & Act
        from src.security.encryption import EncryptionService
        
        service = EncryptionService(key=b"test-key-32-bytes-long-for-aes256")
        
        # Assert
        assert service.key == b"test-key-32-bytes-long-for-aes256"
    
    def test_generate_key(self):
        """Test key generation."""
        # Arrange
        from src.security.encryption import EncryptionService
        
        # Act
        key = EncryptionService.generate_key()
        
        # Assert
        assert len(key) == 32  # AES-256 key length
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption roundtrip."""
        # Arrange
        from src.security.encryption import EncryptionService
        
        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)
        plaintext = b"Sensitive data to encrypt"
        
        # Act
        encrypted = service.encrypt(plaintext)
        decrypted = service.decrypt(encrypted)
        
        # Assert
        assert decrypted == plaintext
        assert encrypted != plaintext
    
    def test_encrypt_with_aad(self):
        """Test encryption with additional authenticated data."""
        # Arrange
        from src.security.encryption import EncryptionService
        
        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)
        plaintext = b"Sensitive data"
        aad = b"additional-data"
        
        # Act
        encrypted = service.encrypt(plaintext, associated_data=aad)
        decrypted = service.decrypt(encrypted, associated_data=aad)
        
        # Assert
        assert decrypted == plaintext
    
    def test_decrypt_with_wrong_aad_fails(self):
        """Test decryption fails with wrong AAD."""
        # Arrange
        from src.security.encryption import EncryptionService
        
        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)
        plaintext = b"Sensitive data"
        
        # Act
        encrypted = service.encrypt(plaintext, associated_data=b"correct-aad")
        
        # Assert
        with pytest.raises(Exception):
            service.decrypt(encrypted, associated_data=b"wrong-aad")
    
    def test_encrypt_file(self, temp_dir):
        """Test encrypting a file."""
        # Arrange
        from src.security.encryption import EncryptionService
        
        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)
        
        input_file = temp_dir / "input.txt"
        output_file = temp_dir / "encrypted.bin"
        input_file.write_text("Sensitive file content")
        
        # Act
        result = service.encrypt_file(input_file, output_file)
        
        # Assert
        assert result is True
        assert output_file.exists()
        assert output_file.read_bytes() != input_file.read_bytes()
    
    def test_decrypt_file(self, temp_dir):
        """Test decrypting a file."""
        # Arrange
        from src.security.encryption import EncryptionService
        
        key = EncryptionService.generate_key()
        service = EncryptionService(key=key)
        
        original_content = "Sensitive file content"
        input_file = temp_dir / "input.txt"
        encrypted_file = temp_dir / "encrypted.bin"
        output_file = temp_dir / "decrypted.txt"
        
        input_file.write_text(original_content)
        service.encrypt_file(input_file, encrypted_file)
        
        # Act
        result = service.decrypt_file(encrypted_file, output_file)
        
        # Assert
        assert result is True
        assert output_file.read_text() == original_content


class TestKeyDerivation:
    """Tests for key derivation."""
    
    def test_derive_key_from_password(self):
        """Test deriving key from password."""
        # Arrange
        from src.security.encryption import KeyDerivation
        
        password = "my_secure_password"
        
        # Act
        key, salt = KeyDerivation.derive_from_password(password)
        
        # Assert
        assert len(key) == 32
        assert len(salt) == 32
    
    def test_derive_same_key_with_same_salt(self):
        """Test deriving the same key with same password and salt."""
        # Arrange
        from src.security.encryption import KeyDerivation
        
        password = "my_secure_password"
        salt = os.urandom(32)
        
        # Act
        key1 = KeyDerivation.derive_from_password(password, salt=salt)
        key2 = KeyDerivation.derive_from_password(password, salt=salt)
        
        # Assert
        assert key1[0] == key2[0]  # Keys should be identical
        assert key1[1] == salt
    
    def test_derive_different_keys_with_different_salts(self):
        """Test deriving different keys with different salts."""
        # Arrange
        from src.security.encryption import KeyDerivation
        
        password = "my_secure_password"
        
        # Act
        key1, salt1 = KeyDerivation.derive_from_password(password)
        key2, salt2 = KeyDerivation.derive_from_password(password)
        
        # Assert
        assert salt1 != salt2
        assert key1 != key2


class TestSecureRandom:
    """Tests for secure random number generation."""
    
    def test_generate_random_bytes(self):
        """Test generating random bytes."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        # Act
        random1 = SecureRandom.generate_bytes(32)
        random2 = SecureRandom.generate_bytes(32)
        
        # Assert
        assert len(random1) == 32
        assert len(random2) == 32
        assert random1 != random2  # Should be different each time
    
    def test_generate_random_int(self):
        """Test generating random integer."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        # Act
        random = SecureRandom.generate_int(1, 100)
        
        # Assert
        assert 1 <= random <= 100
    
    def test_generate_random_string(self):
        """Test generating random string."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        # Act
        random = SecureRandom.generate_string(16)
        
        # Assert
        assert len(random) == 16
        assert random.isalnum()
    
    def test_generate_uuid(self):
        """Test generating UUID."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        # Act
        uuid1 = SecureRandom.generate_uuid()
        uuid2 = SecureRandom.generate_uuid()
        
        # Assert
        assert len(uuid1) == 36  # Standard UUID length
        assert uuid1 != uuid2
    
    def test_generate_token(self):
        """Test generating secure token."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        # Act
        token = SecureRandom.generate_token(32)
        
        # Assert
        assert len(token) == 44  # Base64 encoded 32 bytes
    
    def test_shuffle_list(self):
        """Test securely shuffling a list."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        original = list(range(100))
        
        # Act
        shuffled = SecureRandom.shuffle(original.copy())
        
        # Assert
        assert len(shuffled) == len(original)
        assert set(shuffled) == set(original)
        assert shuffled != original  # Very unlikely to be the same
    
    def test_choice_from_list(self):
        """Test making a secure random choice."""
        # Arrange
        from src.security.encryption import SecureRandom
        
        options = ["a", "b", "c", "d", "e"]
        
        # Act
        choice = SecureRandom.choice(options)
        
        # Assert
        assert choice in options


class TestPasswordHashing:
    """Tests for password hashing."""
    
    def test_hash_password(self):
        """Test password hashing."""
        # Arrange
        from src.security.encryption import PasswordHashing
        
        password = "my_password"
        
        # Act
        hashed = PasswordHashing.hash(password)
        
        # Assert
        assert hashed != password
        assert len(hashed) > 0
    
    def test_verify_correct_password(self):
        """Test verifying correct password."""
        # Arrange
        from src.security.encryption import PasswordHashing
        
        password = "my_password"
        hashed = PasswordHashing.hash(password)
        
        # Act
        result = PasswordHashing.verify(password, hashed)
        
        # Assert
        assert result is True
    
    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        # Arrange
        from src.security.encryption import PasswordHashing
        
        password = "my_password"
        wrong_password = "wrong_password"
        hashed = PasswordHashing.hash(password)
        
        # Act
        result = PasswordHashing.verify(wrong_password, hashed)
        
        # Assert
        assert result is False
    
    def test_same_password_different_hashes(self):
        """Test that same password produces different hashes."""
        # Arrange
        from src.security.encryption import PasswordHashing
        
        password = "my_password"
        
        # Act
        hash1 = PasswordHashing.hash(password)
        hash2 = PasswordHashing.hash(password)
        
        # Assert
        assert hash1 != hash2  # Due to random salt
        assert PasswordHashing.verify(password, hash1) is True
        assert PasswordHashing.verify(password, hash2) is True


class TestFileEncryption:
    """Tests for file encryption operations."""
    
    def test_encrypt_file_streaming(self, temp_dir):
        """Test streaming file encryption."""
        # Arrange
        from src.security.encryption import FileEncryption
        
        key = os.urandom(32)
        input_file = temp_dir / "large_input.txt"
        output_file = temp_dir / "encrypted.bin"
        
        # Create large file
        input_file.write_bytes(b"A" * 1024 * 1024)  # 1MB
        
        file_enc = FileEncryption(key=key)
        
        # Act
        result = file_enc.encrypt_file_streaming(input_file, output_file)
        
        # Assert
        assert result is True
        assert output_file.exists()
        assert output_file.stat().st_size > 0
    
    def test_decrypt_file_streaming(self, temp_dir):
        """Test streaming file decryption."""
        # Arrange
        from src.security.encryption import FileEncryption
        
        key = os.urandom(32)
        input_file = temp_dir / "input.txt"
        encrypted_file = temp_dir / "encrypted.bin"
        output_file = temp_dir / "decrypted.txt"
        
        original_content = b"Original file content"
        input_file.write_bytes(original_content)
        
        file_enc = FileEncryption(key=key)
        file_enc.encrypt_file_streaming(input_file, encrypted_file)
        
        # Act
        result = file_enc.decrypt_file_streaming(encrypted_file, output_file)
        
        # Assert
        assert result is True
        assert output_file.read_bytes() == original_content
    
    def test_encrypt_directory(self, temp_dir):
        """Test encrypting entire directory."""
        # Arrange
        from src.security.encryption import FileEncryption
        
        key = os.urandom(32)
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        
        # Create test files
        (source_dir / "file1.txt").write_text("Content 1")
        (source_dir / "file2.txt").write_text("Content 2")
        (source_dir / "subdir").mkdir()
        (source_dir / "subdir" / "file3.txt").write_text("Content 3")
        
        output_dir = temp_dir / "encrypted"
        
        file_enc = FileEncryption(key=key)
        
        # Act
        result = file_enc.encrypt_directory(source_dir, output_dir)
        
        # Assert
        assert result is True
        assert (output_dir / "file1.txt.enc").exists()
        assert (output_dir / "file2.txt.enc").exists()
        assert (output_dir / "subdir" / "file3.txt.enc").exists()
    
    def test_decrypt_directory(self, temp_dir):
        """Test decrypting entire directory."""
        # Arrange
        from src.security.encryption import FileEncryption
        
        key = os.urandom(32)
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("Content 1")
        
        encrypted_dir = temp_dir / "encrypted"
        decrypted_dir = temp_dir / "decrypted"
        
        file_enc = FileEncryption(key=key)
        file_enc.encrypt_directory(source_dir, encrypted_dir)
        
        # Act
        result = file_enc.decrypt_directory(encrypted_dir, decrypted_dir)
        
        # Assert
        assert result is True
        assert (decrypted_dir / "file1.txt").exists()
        assert (decrypted_dir / "file1.txt").read_text() == "Content 1"


class TestEncryptionMetadata:
    """Tests for encryption metadata handling."""
    
    def test_store_encryption_metadata(self, temp_dir):
        """Test storing encryption metadata."""
        # Arrange
        from src.security.encryption import EncryptionMetadata
        
        metadata = EncryptionMetadata(metadata_path=temp_dir)
        
        # Act
        result = metadata.store(
            file_id="file1",
            algorithm="AES-256-GCM",
            key_id="key1",
            salt=b"random_salt",
            nonce=b"random_nonce"
        )
        
        # Assert
        assert result is True
        assert (temp_dir / "file1.meta.json").exists()
    
    def test_load_encryption_metadata(self, temp_dir):
        """Test loading encryption metadata."""
        # Arrange
        from src.security.encryption import EncryptionMetadata
        
        metadata = EncryptionMetadata(metadata_path=temp_dir)
        metadata.store(
            file_id="file1",
            algorithm="AES-256-GCM",
            key_id="key1",
            salt=b"random_salt",
            nonce=b"random_nonce"
        )
        
        # Act
        loaded = metadata.load("file1")
        
        # Assert
        assert loaded["algorithm"] == "AES-256-GCM"
        assert loaded["key_id"] == "key1"
    
    def test_delete_encryption_metadata(self, temp_dir):
        """Test deleting encryption metadata."""
        # Arrange
        from src.security.encryption import EncryptionMetadata
        
        metadata = EncryptionMetadata(metadata_path=temp_dir)
        metadata.store(
            file_id="file1",
            algorithm="AES-256-GCM",
            key_id="key1",
            salt=b"random_salt",
        )
        
        # Act
        result = metadata.delete("file1")
        
        # Assert
        assert result is True
        assert not (temp_dir / "file1.meta.json").exists()
