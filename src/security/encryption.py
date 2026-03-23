"""
Security Encryption Module - Encryption functionality.
"""
import base64
import hashlib
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


@dataclass
class EncryptionService:
    """Service for encrypting and decrypting data."""
    
    key: bytes
    
    def encrypt(self, plaintext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Encrypt data using AES-256-GCM."""
        aesgcm = AESGCM(self.key)
        nonce = os.urandom(12)
        
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext
    
    def decrypt(self, ciphertext: bytes, associated_data: Optional[bytes] = None) -> bytes:
        """Decrypt data using AES-256-GCM."""
        aesgcm = AESGCM(self.key)
        nonce = ciphertext[:12]
        encrypted_data = ciphertext[12:]
        
        return aesgcm.decrypt(nonce, encrypted_data, associated_data)
    
    @staticmethod
    def generate_key() -> bytes:
        """Generate a new 256-bit encryption key."""
        return AESGCM.generate_key(bit_length=256)
    
    def encrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """Encrypt a file."""
        plaintext = input_path.read_bytes()
        ciphertext = self.encrypt(plaintext)
        output_path.write_bytes(ciphertext)
        return True
    
    def decrypt_file(self, input_path: Path, output_path: Path) -> bool:
        """Decrypt a file."""
        ciphertext = input_path.read_bytes()
        plaintext = self.decrypt(ciphertext)
        output_path.write_bytes(plaintext)
        return True


class KeyDerivation:
    """Derive encryption keys from passwords."""
    
    @staticmethod
    def derive_from_password(password: str, salt: Optional[bytes] = None) -> tuple[bytes, bytes]:
        """Derive a key from a password using PBKDF2."""
        if salt is None:
            salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
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
        return secrets.token_urlsafe(length)[:length]
    
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
        salt = os.urandom(32)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,
        )
        
        key = kdf.derive(password.encode())
        
        # Store salt and key together
        return base64.urlsafe_b64encode(salt + key).decode()
    
    @staticmethod
    def verify(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        try:
            decoded = base64.urlsafe_b64decode(hashed.encode())
            salt = decoded[:32]
            stored_key = decoded[32:]
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=480000,
            )
            
            key = kdf.derive(password.encode())
            return key == stored_key
        except Exception:
            return False


class FileEncryption:
    """Encrypt and decrypt files and directories."""
    
    def __init__(self, key: bytes):
        self.encryption_service = EncryptionService(key=key)
    
    def encrypt_file_streaming(self, input_path: Path, output_path: Path, chunk_size: int = 64 * 1024) -> bool:
        """Encrypt file using streaming (for large files)."""
        nonce = os.urandom(12)
        aesgcm = AESGCM(self.encryption_service.key)
        
        with open(input_path, "rb") as infile, open(output_path, "wb") as outfile:
            outfile.write(nonce)
            
            while chunk := infile.read(chunk_size):
                # For simplicity, encrypt entire file at once
                # In production, use chunked encryption with proper AEAD handling
                encrypted = aesgcm.encrypt(nonce, chunk, None)
                outfile.write(encrypted)
        
        return True
    
    def decrypt_file_streaming(self, input_path: Path, output_path: Path, chunk_size: int = 64 * 1024) -> bool:
        """Decrypt file using streaming."""
        with open(input_path, "rb") as infile, open(output_path, "wb") as outfile:
            nonce = infile.read(12)
            aesgcm = AESGCM(self.encryption_service.key)
            
            ciphertext = infile.read()
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)
            outfile.write(plaintext)
        
        return True
    
    def encrypt_directory(self, source_dir: Path, output_dir: Path) -> bool:
        """Encrypt all files in a directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in source_dir.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(source_dir)
                output_path = output_dir / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.encryption_service.encrypt_file(file_path, output_path.with_suffix(".enc"))
        
        return True
    
    def decrypt_directory(self, source_dir: Path, output_dir: Path) -> bool:
        """Decrypt all files in a directory."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in source_dir.rglob("*.enc"):
            relative_path = file_path.relative_to(source_dir)
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
            "created_at": str(uuid.uuid4()),
        }
        
        if nonce:
            metadata["nonce"] = base64.b64encode(nonce).decode()
        
        metadata_file = self.metadata_path / f"{file_id}.meta.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))
        
        return True
    
    def load(self, file_id: str) -> Optional[dict]:
        """Load encryption metadata."""
        metadata_file = self.metadata_path / f"{file_id}.meta.json"
        
        if not metadata_file.exists():
            return None
        
        metadata = json.loads(metadata_file.read_text())
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
