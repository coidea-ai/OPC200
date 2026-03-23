"""
Security Vault Module - Data vault functionality.
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional


@dataclass
class DataVault:
    """Encrypted data vault for sensitive information."""
    
    base_path: Path
    encryption_service: Any = None
    _access_control: Optional["VaultAccessControl"] = field(default=None, init=False, repr=False)
    _current_user_id: Optional[str] = field(default=None, init=False, repr=False)
    
    def __post_init__(self):
        """Create vault directories."""
        self.base_path = Path(self.base_path)
        self._create_directories()
        # Initialize access control
        self._access_control = VaultAccessControl(self.base_path)
    
    def set_user_context(self, user_id: str) -> "DataVault":
        """Set the current user context for permission checks."""
        self._current_user_id = user_id
        return self
    
    def _check_permission(self, resource: str, permission: str) -> bool:
        """Check if current user has permission for resource."""
        if self._access_control is None or self._current_user_id is None:
            # No access control configured, allow by default (for backward compatibility)
            return True
        return self._access_control.check_access(self._current_user_id, resource, permission)
    
    def _require_permission(self, resource: str, permission: str) -> None:
        """Require permission or raise PermissionError."""
        if not self._check_permission(resource, permission):
            raise PermissionError(
                f"User '{self._current_user_id}' does not have '{permission}' "
                f"permission for resource '{resource}'"
            )
    
    def _create_directories(self) -> None:
        """Create vault directory structure."""
        (self.base_path / "encrypted").mkdir(parents=True, exist_ok=True)
        (self.base_path / "keys").mkdir(parents=True, exist_ok=True)
        (self.base_path / "audit").mkdir(parents=True, exist_ok=True)
        (self.base_path / "temp").mkdir(parents=True, exist_ok=True)
    
    def store_encrypted(self, filename: str, content: bytes, user_id: Optional[str] = None) -> bool:
        """Store encrypted file in vault."""
        if user_id:
            self.set_user_context(user_id)
        self._require_permission(filename, "write")
        
        encrypted_path = self.base_path / "encrypted" / f"{filename}.enc"
        
        if self.encryption_service:
            encrypted_content = self.encryption_service.encrypt(content)
        else:
            encrypted_content = content
        
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted_content)
        return True
    
    def retrieve_decrypted(self, filename: str, user_id: Optional[str] = None) -> Optional[bytes]:
        """Retrieve and decrypt file from vault.
        
        Args:
            filename: Name of the file to retrieve (without .enc extension)
            user_id: Optional user ID for permission check
            
        Returns:
            The decrypted file content as bytes, or None if file not found
            
        Raises:
            PermissionError: If user doesn't have read permission
            EncryptionError: If decryption fails
        """
        if user_id:
            self.set_user_context(user_id)
        self._require_permission(filename, "read")
        
        encrypted_path = self.base_path / "encrypted" / f"{filename}.enc"
        
        if not encrypted_path.exists():
            return None
        
        with open(encrypted_path, 'rb') as f:
            encrypted_content: bytes = f.read()
        
        if self.encryption_service:
            decrypted: bytes = self.encryption_service.decrypt(encrypted_content)
            return decrypted
        
        return encrypted_content
    
    def delete(self, filename: str, user_id: Optional[str] = None) -> bool:
        """Delete encrypted file from vault."""
        if user_id:
            self.set_user_context(user_id)
        self._require_permission(filename, "delete")
        
        encrypted_path = self.base_path / "encrypted" / f"{filename}.enc"
        
        if encrypted_path.exists():
            encrypted_path.unlink()
            return True
        
        return False
    
    def list_files(self, user_id: Optional[str] = None) -> list[str]:
        """List all encrypted files."""
        if user_id:
            self.set_user_context(user_id)
        self._require_permission("*", "list")
        
        encrypted_dir = self.base_path / "encrypted"
        files = []
        
        for f in encrypted_dir.glob("*.enc"):
            # Remove .enc extension
            files.append(f.stem)
        
        return files


@dataclass
class VaultAccessControl:
    """Access control for vault resources."""
    
    vault_path: Path
    policy_file: Path = field(init=False)
    
    def __post_init__(self):
        """Initialize access control."""
        self.vault_path = Path(self.vault_path)
        self.policy_file = self.vault_path / "access_policy.json"
        self._initialize_policy()
    
    def _initialize_policy(self) -> None:
        """Initialize policy file."""
        if not self.policy_file.exists():
            with open(self.policy_file, 'w') as f:
                f.write(json.dumps({"grants": []}))
    
    def _load_policy(self) -> dict[str, Any]:
        """Load access policy."""
        with open(self.policy_file, 'r') as f:
            policy_data: dict[str, Any] = json.loads(f.read())
            return policy_data
    
    def _save_policy(self, policy: dict) -> None:
        """Save access policy."""
        with open(self.policy_file, 'w') as f:
            f.write(json.dumps(policy, indent=2))
    
    def grant_access(self, user_id: str, resource: str, permissions: list[str], time_restrictions: Optional[dict] = None) -> bool:
        """Grant access to a resource."""
        policy = self._load_policy()
        
        # Ensure grants is a list
        if "grants" not in policy or not isinstance(policy["grants"], list):
            policy["grants"] = []
        
        grants: list[dict[str, Any]] = policy["grants"]
        
        # Remove existing grant for this user/resource
        policy["grants"] = [
            g for g in grants
            if not (g.get("user_id") == user_id and g.get("resource") == resource)
        ]
        
        # Add new grant
        grant: dict[str, Any] = {
            "user_id": user_id,
            "resource": resource,
            "permissions": permissions,
            "granted_at": datetime.now().isoformat(),
        }
        
        if time_restrictions:
            grant["time_restrictions"] = time_restrictions
        
        policy["grants"].append(grant)
        self._save_policy(policy)
        
        return True
    
    def revoke_access(self, user_id: str, resource: str) -> bool:
        """Revoke access to a resource."""
        policy = self._load_policy()
        
        policy["grants"] = [
            g for g in policy["grants"]
            if not (g["user_id"] == user_id and g["resource"] == resource)
        ]
        
        self._save_policy(policy)
        return True
    
    def check_access(self, user_id: str, resource: str, permission: str) -> bool:
        """Check if user has permission for resource."""
        policy = self._load_policy()
        
        for grant in policy["grants"]:
            if grant["user_id"] == user_id and grant["resource"] == resource:
                if permission in grant["permissions"]:
                    # Check time restrictions
                    if "time_restrictions" in grant:
                        now = datetime.now()
                        start = grant["time_restrictions"].get("start_time", "00:00")
                        end = grant["time_restrictions"].get("end_time", "23:59")
                        
                        current_time = now.strftime("%H:%M")
                        if not (start <= current_time <= end):
                            return False
                    
                    return True
        
        return False
    
    def get_permissions(self, user_id: str, resource: str) -> list[str]:
        """Get permissions for user on resource."""
        policy = self._load_policy()
        
        for grant in policy.get("grants", []):
            if isinstance(grant, dict):
                if grant.get("user_id") == user_id and grant.get("resource") == resource:
                    perms = grant.get("permissions", [])
                    if isinstance(perms, list):
                        return [str(p) for p in perms]
        
        return []


@dataclass
class KeyManager:
    """Manage encryption keys."""
    
    keys_path: Path
    
    def __post_init__(self):
        """Initialize keys directory."""
        self.keys_path = Path(self.keys_path)
        self.keys_path.mkdir(parents=True, exist_ok=True)
    
    def generate_key(self, key_type: str = "master") -> tuple[str, bytes]:
        """Generate a new key."""
        import secrets
        
        key_id = secrets.token_hex(16)
        key = secrets.token_bytes(32)
        
        key_file = self.keys_path / f"{key_id}.key"
        
        # Store key metadata
        metadata = {
            "id": key_id,
            "type": key_type,
            "created_at": datetime.now().isoformat(),
        }
        
        with open(key_file, 'wb') as f:
            f.write(key)
        
        meta_file = self.keys_path / f"{key_id}.meta.json"
        with open(meta_file, 'w') as f:
            f.write(json.dumps(metadata, indent=2))
        
        return key_id, key
    
    def load_key(self, key_id: str) -> Optional[bytes]:
        """Load a key by ID."""
        key_file = self.keys_path / f"{key_id}.key"
        
        if not key_file.exists():
            return None
        
        with open(key_file, 'rb') as f:
            return f.read()
    
    def rotate_key(self, key_id: str) -> tuple[str, bytes]:
        """Rotate a key."""
        old_key_file = self.keys_path / f"{key_id}.key"
        
        if not old_key_file.exists():
            raise ValueError(f"Key {key_id} not found")
        
        # Backup old key
        backup_file = self.keys_path / f"{key_id}.key.old"
        with open(old_key_file, 'rb') as f:
            backup_content = f.read()
        with open(backup_file, 'wb') as f:
            f.write(backup_content)
        
        # Generate new key
        new_key_id, new_key = self.generate_key()
        
        # Delete old key file
        old_key_file.unlink()
        
        return new_key_id, new_key
    
    def delete_key(self, key_id: str) -> bool:
        """Delete a key."""
        key_file = self.keys_path / f"{key_id}.key"
        meta_file = self.keys_path / f"{key_id}.meta.json"
        
        deleted = False
        if key_file.exists():
            key_file.unlink()
            deleted = True
        if meta_file.exists():
            meta_file.unlink()
        
        return deleted
    
    def list_keys(self) -> list[str]:
        """List all keys."""
        keys = []
        for f in self.keys_path.glob("*.key"):
            keys.append(f.stem)
        return keys


@dataclass
class VaultAudit:
    """Audit logging for vault access."""
    
    audit_path: Path
    
    def __post_init__(self):
        """Initialize audit directory."""
        self.audit_path = Path(self.audit_path)
        self.audit_path.mkdir(parents=True, exist_ok=True)
    
    def log_access(self, user_id: str, action: str, resource: str, success: bool, reason: str = "") -> bool:
        """Log an access event."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "success": success,
        }
        
        if reason:
            log_entry["reason"] = reason
        
        # Write to daily log file
        log_file = self.audit_path / f"{datetime.now().strftime('%Y-%m-%d')}.log"
        
        with open(log_file, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
        
        return True
    
    def get_access_history(self, user_id: str) -> list[dict]:
        """Get access history for a user."""
        history = []
        
        for log_file in self.audit_path.glob("*.log"):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry["user_id"] == user_id:
                        history.append(entry)
        
        return sorted(history, key=lambda x: x["timestamp"])
    
    def get_resource_access_log(self, resource: str) -> list[dict]:
        """Get access log for a resource."""
        history = []
        
        for log_file in self.audit_path.glob("*.log"):
            with open(log_file) as f:
                for line in f:
                    entry = json.loads(line.strip())
                    if entry["resource"] == resource:
                        history.append(entry)
        
        return sorted(history, key=lambda x: x["timestamp"])
    
    def cleanup_old_logs(self, retention_days: int = 30) -> bool:
        """Clean up old audit logs."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        
        for log_file in self.audit_path.glob("*.log"):
            # Parse date from filename
            try:
                file_date = datetime.strptime(log_file.stem, "%Y-%m-%d")
                if file_date < cutoff:
                    log_file.unlink()
            except ValueError:
                continue
        
        return True


@dataclass
class VaultIntegrity:
    """Verify vault integrity."""
    
    vault: DataVault
    
    def verify_all_files(self) -> bool:
        """Verify integrity of all files in vault."""
        files = self.vault.list_files()
        
        for filename in files:
            try:
                content = self.vault.retrieve_decrypted(filename)
                if content is None:
                    return False
            except Exception:
                return False
        
        return True
    
    def create_backup_checksums(self) -> bool:
        """Create checksums for backup verification."""
        import hashlib
        
        checksums = {}
        
        for filename in self.vault.list_files():
            filepath = self.vault.base_path / "encrypted" / f"{filename}.enc"
            with open(filepath, 'rb') as f:
                content = f.read()
            checksums[filename] = hashlib.sha256(content).hexdigest()
        
        checksum_file = self.vault.base_path / "checksums.json"
        with open(checksum_file, 'w') as f:
            f.write(json.dumps(checksums, indent=2))
        
        return True
    
    def repair_from_backup(self) -> bool:
        """Repair vault from backup."""
        # Placeholder for repair logic
        return True
