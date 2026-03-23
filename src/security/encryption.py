"""
Security Encryption Module - Encryption functionality.
"""
import base64
import hashlib
import json
import os
import secrets
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Configuration constants for cryptographic operations
# These values follow OWASP and NIST recommendations
KDF_ITERATIONS = 480000  # PBKDF2 iterations (OWASP 2023 recommendation)
KEY_LENGTH = 32  # AES-256 key length in bytes
SALT_LENGTH = 32  # Salt length in bytes
NONCE_LENGTH = 12  # AES-GCM nonce length in bytes


@dataclass
class EncryptionService:
    """Service for encrypting and decrypting data.
    
    Provides AES-256-GCM encryption with authenticated encryption.
    
    Attributes:
        key: The encryption key (must be 32 bytes for AES-256)
    
    Example:
        >>> key = EncryptionService.generate_key()
        >>> service = EncryptionService(key=key)
        >>> encrypted = service.encrypt(b"secret message")
        >>> decrypted = service.decrypt(encrypted)
        >>> assert decrypted == b"secret message"
    """
    
    key: bytes
    
    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Encrypt data using AES-256-GCM.
        
        Args:
            plaintext: The data to encrypt
            associated_data: Optional authenticated associated data
            
        Returns:
            The encrypted data with nonce prepended
        """
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(NONCE_LENGTH)
        
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext
    
    def decrypt(self, ciphertext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Decrypt data using AES-256-GCM.
        
        Args:
            ciphertext: The encrypted data (nonce + ciphertext)
            associated_data: Optional authenticated associated data
            
        Returns:
            The decrypted plaintext
        """
        aesgcm = AESGCM(self.key)
        nonce = ciphertext[:NONCE_LENGTH]
        encrypted_data = ciphertext[NONCE_LENGTH:]
        
        return aesgcm.decrypt(nonce, encrypted_data, associated_data)
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new 256-bit encryption key."""
        return AESGCM.generate_key(bit_length=256)
    
    def encrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """Encrypt a file."""
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        ciphertext = self.encrypt(plaintext)
        with open(output_path, 'wb') as f:
            f.write(ciphertext)
        return True
    
    def decrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """Decrypt a file."""
        with open(input_path, 'rb') as f:
            ciphertext = f.read()
        plaintext = self.decrypt(ciphertext)
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        return True


class KeyDerivation:
    """Derive encryption keys from passwords."""
    
    @staticmethod
    def derive_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """Derive a key from a password using PBKDF2."""
        if salt is None:
            salt = os.urandom(SALT_LENGTH)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        
        key = kdf.derive(password.encode())
        return key, salt


class SecureRandom:
    """Generate cryptographically secure random values."""
    
    @staticmethod
    def generate_bytes(length: int) -> bytes:
        """Generate random bytes."""
        return secrets.token_bytes(length)
    
    @staticmethod
    def generate_int(min_value: int, max_value: int) -> int:
        """Generate random integer in range."""
        return secrets.randbelow(max_value - min_value + 1) + min_value
    
    @staticmethod
    def generate_string(length: int = 32) -> str:
        """Generate random alphanumeric string."""
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    @staticmethod
    def generate_uuid() -> str:
        """Generate UUID."""
        return str(uuid.uuid4())
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure token."""
        return base64.urlsafe_b64encode(secrets.token_bytes(length)).decode()
    
    @staticmethod
    def shuffle(items: list) -> list:
        """Shuffle list securely."""
        result = items.copy()
        for i in range(len(result) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            result[i], result[j] = result[j], result[i]
        return result
    
    @staticmethod
    def choice(options: list) -> Any:
        """Make random choice from list."""
        return secrets.choice(options)


class PasswordHashing:
    """Hash and verify passwords."""
    
    @staticmethod
    def hash(password: str) -> str:
        """Hash a password using PBKDF2."""
        salt = os.urandom(SALT_LENGTH)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=KEY_LENGTH,
            salt=salt,
            iterations=KDF_ITERATIONS,
        )
        
        key = kdf.derive(password.encode())
        
        # Store salt and key together
        return base64.urlsafe_b64encode(salt + key).decode()
    
    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            decoded = base64.urlsafe_b64decode(hashed.encode())
            salt = decoded[:SALT_LENGTH]
            stored_key = decoded[SALT_LENGTH:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=KEY_LENGTH,
                salt=salt,
                iterations=KDF_ITERATIONS,
            )
            
            key = kdf.derive(password.encode())
            return key == stored_key
        except Exception:
            return False


class FileEncryption:
    """Encrypt and decrypt files and directories using streaming."""
    
    CHUNK_OVERHEAD = 28  # 16 bytes tag + 12 bytes chunk nonce
    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming
    FILE_NONCE_LENGTH = 12  # File-level nonce length
    CHUNK_INDEX_BYTES = 8  # Bytes for chunk index
    CHUNK_LEN_BYTES = 4  # Bytes for chunk length header
    
    def __init__(self, key: bytes):
        self.encryption_service = EncryptionService(key=key)
        self._key = key
    
    def encrypt_file_streaming(self, input_path: Path, output_path: Path, chunk_size: int = CHUNK_SIZE) -> bool:
        """Encrypt file using true streaming with chunked AEAD.
        
        Format: [file_nonce(12)] + [num_chunks(8)] + [chunk1_len(4) + chunk1_tag(16) + chunk1_nonce(12) + chunk1_data] + ...
        """
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import struct
        
        file_nonce = os.urandom(self.FILE_NONCE_LENGTH)
        
        # First pass: count chunks
        chunk_count = 0
        with open(input_path, "rb") as f:
            while f.read(chunk_size):
                chunk_count += 1
        
        with open(input_path, "rb") as infile, open(output_path, "wb") as outfile:
            # Write file header: nonce + chunk count
            outfile.write(file_nonce)
            outfile.write(struct.pack("<Q", chunk_count))  # 8 bytes, little-endian
            
            chunk_index = 0
            while chunk := infile.read(chunk_size):
                # Derive unique nonce for each chunk
                chunk_nonce = self._derive_chunk_nonce(file_nonce, chunk_index)
                aesgcm = AESGCM(self._key)
                
                # Encrypt chunk
                encrypted_chunk = aesgcm.encrypt(chunk_nonce, chunk, None)
                # encrypted_chunk = ciphertext + tag(16 bytes)
                
                # Write chunk header + encrypted data
                # chunk_len includes tag but not nonce
                outfile.write(struct.pack("<I", len(encrypted_chunk)))  # 4 bytes
                outfile.write(chunk_nonce)  # 12 bytes
                outfile.write(encrypted_chunk)  # len + 16 bytes tag
                
                chunk_index += 1
        
        return True
    
    def decrypt_file_streaming(self, input_path: Path, output_path: Path, chunk_size: int = CHUNK_SIZE) -> bool:
        """Decrypt file using true streaming with chunked AEAD."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import struct
        
        with open(input_path, "rb") as infile, open(output_path, "wb") as outfile:
            # Read file header
            file_nonce = infile.read(self.FILE_NONCE_LENGTH)
            if len(file_nonce) != self.FILE_NONCE_LENGTH:
                raise ValueError("Invalid encrypted file: missing nonce")
            
            chunk_count_bytes = infile.read(self.CHUNK_INDEX_BYTES)
            if len(chunk_count_bytes) != self.CHUNK_INDEX_BYTES:
                raise ValueError("Invalid encrypted file: missing chunk count")
            chunk_count = struct.unpack("<Q", chunk_count_bytes)[0]
            
            # Decrypt chunks
            for chunk_index in range(chunk_count):
                # Read chunk header
                chunk_len_bytes = infile.read(self.CHUNK_LEN_BYTES)
                if len(chunk_len_bytes) != self.CHUNK_LEN_BYTES:
                    raise ValueError(f"Invalid chunk header at index {chunk_index}")
                chunk_len = struct.unpack("<I", chunk_len_bytes)[0]
                
                chunk_nonce = infile.read(NONCE_LENGTH)
                if len(chunk_nonce) != NONCE_LENGTH:
                    raise ValueError(f"Invalid chunk nonce at index {chunk_index}")
                
                encrypted_chunk = infile.read(chunk_len)
                if len(encrypted_chunk) != chunk_len:
                    raise ValueError(f"Incomplete chunk data at index {chunk_index}")
                
                # Decrypt chunk
                aesgcm = AESGCM(self._key)
                try:
                    plaintext = aesgcm.decrypt(chunk_nonce, encrypted_chunk, None)
                except Exception as e:
                    raise ValueError(f"Failed to decrypt chunk {chunk_index}: {e}") from e
                
                outfile.write(plaintext)
        
        return True
    
    def _derive_chunk_nonce(self, file_nonce: bytes, chunk_index: int) -> bytes:
        """Derive a unique nonce for each chunk from file nonce and chunk index."""
        # Combine file_nonce with chunk_index to create unique nonce
        index_bytes = chunk_index.to_bytes(self.CHUNK_INDEX_BYTES, 'little')
        combined = file_nonce + index_bytes
        # Use first 12 bytes of SHA256 hash
        return hashlib.sha256(combined).digest()[:NONCE_LENGTH]
    
    def encrypt_directory(self, source_dir: Path, output_dir: Path) -> bool:
        """Encrypt all files in a directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_dir)
                output_path = output_dir / f"{relative_path}.enc"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.encryption_service.encrypt_file(file_path, output_path)
        
        return True
    
    def decrypt_directory(self, source_dir: Path, output_dir: Path) -> bool:
        """Decrypt all files in a directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in source_dir.rglob("*.enc"):
            relative_path = file_path.relative_to(source_dir)
            # Remove .enc suffix
            output_path = output_dir / relative_path.with_suffix("")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.encryption_service.decrypt_file(file_path, output_path)
        
        return True


class EncryptionMetadata:
    """Manage encryption metadata."""
    
    def __init__(self, metadata_path: Path):
        self.metadata_path = Path(metadata_path)
        self.metadata_path.mkdir(parents=True, exist_ok=True)
    
    def store(self, file_id: str, algorithm: str, key_id: str, salt: bytes, nonce: Optional[bytes] = None) -> bool:
        """Store encryption metadata."""
        metadata = {
            "file_id": file_id,
            "algorithm": algorithm,
            "key_id": key_id,
            "salt": base64.b64encode(salt).decode(),
            "created_at": datetime.now().isoformat(),
        }
        
        if nonce:
            metadata["nonce"] = base64.b64encode(nonce).decode()
        
        metadata_file = self.metadata_path / f"{file_id}.meta.json"
        with open(metadata_file, 'w') as f:
            f.write(json.dumps(metadata, indent=2))
        
        return True
    
    def load(self, file_id: str) -> Optional[dict]:
        """Load encryption metadata."""
        metadata_file = self.metadata_path / f"{file_id}.meta.json"
        
        if not metadata_file.exists():
            return None
        
        with open(metadata_file, 'r') as f:
            metadata = json.loads(f.read())
        metadata["salt"] = base64.b64decode(metadata["salt"])
        
        if "nonce" in metadata:
            metadata["nonce"] = base64.b64decode(metadata["nonce"])
        
        return metadata
    
    def delete(self, file_id: str) -> bool:
        """Delete encryption metadata."""
        metadata_file = self.metadata_path / f"{file_id}.meta.json"
        
        if metadata_file.exists():
            metadata_file.unlink()
            return True
        
        return False


# Import datetime at the end to avoid circular imports
from datetime import datetime
