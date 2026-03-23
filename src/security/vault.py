# OPC200 - 数据保险箱模块
# 实现 Agent-Blind Credentials 安全架构

import os
import json
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, asdict
import logging
import asyncio

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


@dataclass
class CredentialEntry:
    """
    凭证条目
    
    注意：凭证值在存储前已加密，Agent 无法直接访问明文
    """
    id: str
    name: str
    credential_type: str  # api_key, password, token, certificate
    encrypted_value: bytes  # 加密后的值
    metadata: Dict[str, Any]  # 元数据（不敏感信息）
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None
    rotation_hint: Optional[str] = None  # 轮换提示
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'credential_type': self.credential_type,
            'encrypted_value': base64.b64encode(self.encrypted_value).decode(),
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'rotation_hint': self.rotation_hint
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CredentialEntry':
        return cls(
            id=data['id'],
            name=data['name'],
            credential_type=data['credential_type'],
            encrypted_value=base64.b64decode(data['encrypted_value']),
            metadata=data.get('metadata', {}),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            expires_at=datetime.fromisoformat(data['expires_at']) if data.get('expires_at') else None,
            rotation_hint=data.get('rotation_hint')
        )


class VaultKeyManager:
    """
    保险箱密钥管理器
    
    职责：
    - 主密钥派生
    - 密钥轮换
    - 安全的内存处理
    """
    
    def __init__(self, master_key: Optional[bytes] = None):
        """
        Args:
            master_key: 主密钥，如果为 None 则生成新密钥
        """
        if master_key is None:
            master_key = Fernet.generate_key()
        
        self._master_key = master_key
        self._cipher = Fernet(master_key)
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> Tuple['VaultKeyManager', bytes]:
        """
        从密码派生密钥
        
        Returns:
            (KeyManager 实例, salt)
        """
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        
        return cls(key), salt
    
    def encrypt(self, plaintext: str) -> bytes:
        """加密明文"""
        return self._cipher.encrypt(plaintext.encode('utf-8'))
    
    def decrypt(self, ciphertext: bytes) -> str:
        """解密为明文"""
        return self._cipher.decrypt(ciphertext).decode('utf-8')
    
    def rotate_key(self) -> 'VaultKeyManager':
        """生成新密钥（需要手动重新加密所有凭证）"""
        return VaultKeyManager()
    
    def clear(self):
        """清除内存中的密钥"""
        self._master_key = None
        self._cipher = None


class SecureVault:
    """
    数据保险箱（Agent-Blind Credentials 实现）
    
    安全原则：
    1. Agent 只能看到凭证的元数据，不能直接访问凭证值
    2. 凭证值在存储前加密
    3. 解密需要明确的授权
    4. 所有访问操作都被审计
    5. 支持凭证轮换
    
    使用模式：
    ```python
    vault = SecureVault("/path/to/vault", key_manager)
    
    # Agent 存储凭证（只存储元数据）
    cred_id = vault.store_credential(
        name="openai_api_key",
        credential_type="api_key",
        value="sk-...",
        metadata={"service": "openai", "scope": "production"}
    )
    
    # Agent 获取凭证（只能看到元数据）
    cred = vault.get_credential_metadata(cred_id)
    # cred.encrypted_value 存在，但 Agent 无法解密
    
    # 服务层解密使用（需要额外授权）
    value = vault.decrypt_for_service(cred_id, service_auth)
    ```
    """
    
    def __init__(self, 
                 vault_path: str,
                 key_manager: VaultKeyManager,
                 audit_log_path: Optional[str] = None):
        """
        Args:
            vault_path: 保险箱存储路径
            key_manager: 密钥管理器
            audit_log_path: 审计日志路径
        """
        self.vault_path = Path(vault_path)
        self.vault_path.mkdir(parents=True, exist_ok=True)
        
        self.key_manager = key_manager
        self.audit_log_path = Path(audit_log_path) if audit_log_path else self.vault_path / "audit.log"
        
        self._credentials: Dict[str, CredentialEntry] = {}
        self._load_credentials()
    
    def _load_credentials(self):
        """加载凭证"""
        cred_file = self.vault_path / "credentials.json"
        if cred_file.exists():
            with open(cred_file, 'r') as f:
                data = json.load(f)
                self._credentials = {
                    k: CredentialEntry.from_dict(v) 
                    for k, v in data.items()
                }
    
    def _save_credentials(self):
        """保存凭证"""
        cred_file = self.vault_path / "credentials.json"
        data = {k: v.to_dict() for k, v in self._credentials.items()}
        with open(cred_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _log_access(self, 
                   action: str, 
                   credential_id: str, 
                   actor: str,
                   success: bool = True,
                   details: Optional[Dict] = None):
        """记录访问日志"""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'credential_id': credential_id,
            'actor': actor,
            'success': success,
            'details': details or {}
        }
        
        with open(self.audit_log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def store_credential(self,
                        name: str,
                        credential_type: str,
                        value: str,
                        metadata: Optional[Dict[str, Any]] = None,
                        expires_in_days: Optional[int] = None,
                        actor: str = "system") -> str:
        """
        存储凭证
        
        Args:
            name: 凭证名称
            credential_type: 凭证类型
            value: 凭证值（会被加密）
            metadata: 元数据（Agent 可见）
            expires_in_days: 过期天数
            actor: 执行者标识
            
        Returns:
            凭证 ID
        """
        credential_id = hashlib.sha256(
            f"{name}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        now = datetime.now()
        
        entry = CredentialEntry(
            id=credential_id,
            name=name,
            credential_type=credential_type,
            encrypted_value=self.key_manager.encrypt(value),
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
            expires_at=now + timedelta(days=expires_in_days) if expires_in_days else None
        )
        
        self._credentials[credential_id] = entry
        self._save_credentials()
        
        self._log_access("store", credential_id, actor, success=True)
        logger.info(f"Credential stored: {name} (ID: {credential_id})")
        
        return credential_id
    
    def get_credential_metadata(self, 
                               credential_id: str,
                               actor: str = "system") -> Optional[Dict[str, Any]]:
        """
        获取凭证元数据（Agent 可见）
        
        注意：返回的信息不包含凭证值
        """
        entry = self._credentials.get(credential_id)
        if not entry:
            self._log_access("get_metadata", credential_id, actor, success=False)
            return None
        
        # 只返回元数据，不包含加密值
        result = {
            'id': entry.id,
            'name': entry.name,
            'credential_type': entry.credential_type,
            'metadata': entry.metadata,
            'created_at': entry.created_at.isoformat(),
            'updated_at': entry.updated_at.isoformat(),
            'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
            'rotation_hint': entry.rotation_hint,
            'has_value': True  # 表示存在加密值
        }
        
        self._log_access("get_metadata", credential_id, actor, success=True)
        return result
    
    def list_credentials(self, 
                        credential_type: Optional[str] = None,
                        actor: str = "system") -> List[Dict[str, Any]]:
        """
        列出凭证（仅元数据）
        """
        results = []
        
        for entry in self._credentials.values():
            if credential_type and entry.credential_type != credential_type:
                continue
            
            results.append({
                'id': entry.id,
                'name': entry.name,
                'credential_type': entry.credential_type,
                'metadata': entry.metadata,
                'expires_at': entry.expires_at.isoformat() if entry.expires_at else None
            })
        
        self._log_access("list", "all", actor, success=True, 
                        details={'filter_type': credential_type, 'count': len(results)})
        
        return results
    
    def decrypt_for_service(self,
                           credential_id: str,
                           service_auth_token: str,
                           actor: str = "system") -> Optional[str]:
        """
        为服务层解密凭证
        
        这是唯一可以获取明文凭证的方法，需要服务层授权令牌。
        使用示例：当 OpenClaw 需要调用 API 时，通过此方法获取真实密钥。
        
        Args:
            credential_id: 凭证 ID
            service_auth_token: 服务授权令牌
            actor: 执行者标识
            
        Returns:
            明文凭证值，如果授权失败则返回 None
        """
        # 验证服务授权（简化实现，实际应调用 auth 服务）
        if not self._verify_service_auth(service_auth_token):
            self._log_access("decrypt", credential_id, actor, 
                           success=False, details={'reason': 'auth_failed'})
            logger.warning(f"Unauthorized decrypt attempt: {credential_id}")
            return None
        
        entry = self._credentials.get(credential_id)
        if not entry:
            self._log_access("decrypt", credential_id, actor, 
                           success=False, details={'reason': 'not_found'})
            return None
        
        # 检查是否过期
        if entry.expires_at and datetime.now() > entry.expires_at:
            self._log_access("decrypt", credential_id, actor,
                           success=False, details={'reason': 'expired'})
            logger.warning(f"Attempt to use expired credential: {credential_id}")
            return None
        
        try:
            plaintext = self.key_manager.decrypt(entry.encrypted_value)
            self._log_access("decrypt", credential_id, actor, success=True)
            return plaintext
        except Exception as e:
            self._log_access("decrypt", credential_id, actor,
                           success=False, details={'reason': 'decrypt_error', 'error': str(e)})
            logger.error(f"Failed to decrypt credential {credential_id}: {e}")
            return None
    
    def _verify_service_auth(self, token: str) -> bool:
        """
        验证服务授权
        
        简化实现，实际应调用专门的 auth 服务
        """
        # 实际实现应检查 JWT 或调用外部 auth 服务
        # 这里使用简单的常量比较作为示例
        expected_token = os.environ.get("OPC200_VAULT_SERVICE_TOKEN")
        if expected_token:
            return secrets.compare_digest(token, expected_token)
        return True  # 如果没有设置令牌，允许访问（仅用于开发）
    
    def update_credential(self,
                         credential_id: str,
                         new_value: Optional[str] = None,
                         new_metadata: Optional[Dict[str, Any]] = None,
                         actor: str = "system") -> bool:
        """
        更新凭证
        """
        entry = self._credentials.get(credential_id)
        if not entry:
            return False
        
        if new_value:
            entry.encrypted_value = self.key_manager.encrypt(new_value)
        
        if new_metadata:
            entry.metadata.update(new_metadata)
        
        entry.updated_at = datetime.now()
        
        self._save_credentials()
        self._log_access("update", credential_id, actor, success=True)
        
        return True
    
    def rotate_credential(self,
                         credential_id: str,
                         new_value: str,
                         actor: str = "system") -> bool:
        """
        轮换凭证
        
        更新凭证值并记录轮换历史
        """
        entry = self._credentials.get(credential_id)
        if not entry:
            return False
        
        # 加密新值
        entry.encrypted_value = self.key_manager.encrypt(new_value)
        entry.updated_at = datetime.now()
        
        # 更新轮换提示
        entry.rotation_hint = f"Rotated at {datetime.now().isoformat()}"
        
        self._save_credentials()
        self._log_access("rotate", credential_id, actor, success=True)
        
        logger.info(f"Credential rotated: {credential_id}")
        return True
    
    def delete_credential(self,
                         credential_id: str,
                         actor: str = "system") -> bool:
        """
        删除凭证
        """
        if credential_id not in self._credentials:
            return False
        
        del self._credentials[credential_id]
        self._save_credentials()
        
        self._log_access("delete", credential_id, actor, success=True)
        logger.info(f"Credential deleted: {credential_id}")
        
        return True
    
    def get_expired_credentials(self) -> List[Dict[str, Any]]:
        """获取已过期凭证列表"""
        now = datetime.now()
        expired = []
        
        for entry in self._credentials.values():
            if entry.expires_at and now > entry.expires_at:
                expired.append({
                    'id': entry.id,
                    'name': entry.name,
                    'expired_at': entry.expires_at.isoformat(),
                    'days_overdue': (now - entry.expires_at).days
                })
        
        return expired
    
    def get_audit_log(self, 
                     credential_id: Optional[str] = None,
                     since: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        获取审计日志
        """
        if not self.audit_log_path.exists():
            return []
        
        logs = []
        with open(self.audit_log_path, 'r') as f:
            for line in f:
                if not line.strip():
                    continue
                
                try:
                    entry = json.loads(line)
                    
                    # 过滤
                    if credential_id and entry.get('credential_id') != credential_id:
                        continue
                    
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    if since and entry_time < since:
                        continue
                    
                    logs.append(entry)
                except json.JSONDecodeError:
                    continue
        
        return logs


class VaultHealthChecker:
    """
    保险箱健康检查
    """
    
    def __init__(self, vault: SecureVault):
        self.vault = vault
    
    async def check_health(self) -> Dict[str, Any]:
        """执行健康检查"""
        checks = {
            'vault_accessible': self._check_vault_accessible(),
            'credentials_count': len(self.vault._credentials),
            'expired_credentials': len(self.vault.get_expired_credentials()),
            'audit_log_accessible': self.vault.audit_log_path.exists(),
            'timestamp': datetime.now().isoformat()
        }
        
        # 检查即将过期的凭证
        expiring_soon = []
        now = datetime.now()
        for entry in self.vault._credentials.values():
            if entry.expires_at:
                days_until = (entry.expires_at - now).days
                if 0 < days_until <= 7:
                    expiring_soon.append({
                        'id': entry.id,
                        'name': entry.name,
                        'expires_in_days': days_until
                    })
        
        checks['expiring_soon'] = expiring_soon
        checks['status'] = 'healthy' if all([
            checks['vault_accessible'],
            checks['audit_log_accessible']
        ]) else 'unhealthy'
        
        return checks
    
    def _check_vault_accessible(self) -> bool:
        """检查保险箱是否可访问"""
        try:
            return self.vault.vault_path.exists() and os.access(self.vault.vault_path, os.R_OK | os.W_OK)
        except Exception:
            return False
