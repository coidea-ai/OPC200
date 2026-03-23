# OPC200 - Journal 存储管理模块
# 处理本地存储、加密、备份

import os
import json
import shutil
import hashlib
import gzip
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import logging
import asyncio
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logger = logging.getLogger(__name__)


class StorageManager:
    """
    存储管理器
    
    功能：
    - 文件系统操作
    - 目录结构管理
    - 存储配额管理
    """
    
    def __init__(self, base_path: str, quota_mb: int = 10240):
        """
        Args:
            base_path: 存储根目录
            quota_mb: 配额限制（MB）
        """
        self.base_path = Path(base_path)
        self.quota_mb = quota_mb
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def get_path(self, *parts: str) -> Path:
        """获取相对于 base_path 的路径"""
        return self.base_path.joinpath(*parts)
    
    def ensure_dir(self, *parts: str) -> Path:
        """确保目录存在"""
        path = self.get_path(*parts)
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    def write_file(self, 
                   path: str, 
                   content: str,
                   encoding: str = 'utf-8') -> Path:
        """写入文本文件"""
        file_path = self.get_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        return file_path
    
    def read_file(self, path: str, encoding: str = 'utf-8') -> Optional[str]:
        """读取文本文件"""
        file_path = self.get_path(path)
        if not file_path.exists():
            return None
        
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    
    def write_json(self, path: str, data: Dict[str, Any]) -> Path:
        """写入 JSON 文件"""
        return self.write_file(path, json.dumps(data, ensure_ascii=False, indent=2))
    
    def read_json(self, path: str) -> Optional[Dict[str, Any]]:
        """读取 JSON 文件"""
        content = self.read_file(path)
        if content:
            return json.loads(content)
        return None
    
    def get_size_mb(self, path: Optional[str] = None) -> float:
        """获取目录或文件大小（MB）"""
        target = self.get_path(path) if path else self.base_path
        
        if target.is_file():
            return target.stat().st_size / (1024 * 1024)
        
        total = 0
        for item in target.rglob('*'):
            if item.is_file():
                total += item.stat().st_size
        
        return total / (1024 * 1024)
    
    def check_quota(self) -> Tuple[bool, float]:
        """
        检查配额
        
        Returns:
            (是否超出配额, 当前使用 MB)
        """
        used = self.get_size_mb()
        return used < self.quota_mb, used
    
    def list_files(self, pattern: str = "**/*") -> List[Path]:
        """列出文件"""
        return list(self.base_path.glob(pattern))
    
    def delete(self, path: str, recursive: bool = False) -> bool:
        """删除文件或目录"""
        target = self.get_path(path)
        
        if not target.exists():
            return False
        
        if target.is_file():
            target.unlink()
        elif recursive:
            shutil.rmtree(target)
        else:
            return False
        
        return True
    
    def move(self, src: str, dst: str) -> Path:
        """移动文件"""
        src_path = self.get_path(src)
        dst_path = self.get_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.move(str(src_path), str(dst_path))
        return dst_path
    
    def copy(self, src: str, dst: str) -> Path:
        """复制文件"""
        src_path = self.get_path(src)
        dst_path = self.get_path(dst)
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        
        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        
        return dst_path


class EncryptedStorage:
    """
    加密存储
    
    使用 Fernet 对称加密，密钥从密码派生
    """
    
    def __init__(self, storage: StorageManager, password: str, salt: Optional[bytes] = None):
        """
        Args:
            storage: 基础存储管理器
            password: 加密密码
            salt: 盐值（可选，用于密钥派生）
        """
        self.storage = storage
        self.salt = salt or os.urandom(16)
        self.key = self._derive_key(password, self.salt)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """从密码派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    def encrypt(self, data: bytes) -> bytes:
        """加密数据"""
        return self.cipher.encrypt(data)
    
    def decrypt(self, token: bytes) -> bytes:
        """解密数据"""
        return self.cipher.decrypt(token)
    
    def write_encrypted(self, path: str, content: str):
        """写入加密文本"""
        encrypted = self.encrypt(content.encode('utf-8'))
        file_path = self.storage.get_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'wb') as f:
            f.write(self.salt + encrypted)
    
    def read_encrypted(self, path: str) -> Optional[str]:
        """读取并解密文本"""
        file_path = self.storage.get_path(path)
        if not file_path.exists():
            return None
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # 分离 salt 和加密数据
        stored_salt = data[:16]
        encrypted = data[16:]
        
        # 如果 salt 不同，需要重新初始化 cipher
        if stored_salt != self.salt:
            key = self._derive_key(self.cipher._encryption_key.decode(), stored_salt)
            cipher = Fernet(key)
        else:
            cipher = self.cipher
        
        decrypted = cipher.decrypt(encrypted)
        return decrypted.decode('utf-8')
    
    def write_encrypted_json(self, path: str, data: Dict[str, Any]):
        """写入加密 JSON"""
        self.write_encrypted(path, json.dumps(data, ensure_ascii=False))
    
    def read_encrypted_json(self, path: str) -> Optional[Dict[str, Any]]:
        """读取加密 JSON"""
        content = self.read_encrypted(path)
        if content:
            return json.loads(content)
        return None


class BackupManager:
    """
    备份管理器
    
    功能：
    - 创建备份（压缩）
    - 恢复备份
    - 自动清理旧备份
    """
    
    def __init__(self, storage: StorageManager, backup_dir: str = "backups"):
        self.storage = storage
        self.backup_dir = storage.ensure_dir(backup_dir)
    
    def create_backup(self, 
                     name: Optional[str] = None,
                     include_patterns: List[str] = None,
                     exclude_patterns: List[str] = None) -> Path:
        """
        创建备份
        
        Args:
            name: 备份名称，默认使用时间戳
            include_patterns: 包含的文件模式
            exclude_patterns: 排除的文件模式
        """
        if name is None:
            name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / f"{name}.tar.gz"
        
        # 创建 tar.gz 压缩包
        import tarfile
        
        with tarfile.open(backup_path, 'w:gz') as tar:
            base = self.storage.base_path
            
            for item in base.rglob('*'):
                if item.is_file():
                    # 检查排除模式
                    rel_path = item.relative_to(base)
                    
                    if exclude_patterns:
                        if any(rel_path.match(p) for p in exclude_patterns):
                            continue
                    
                    if include_patterns:
                        if not any(rel_path.match(p) for p in include_patterns):
                            continue
                    
                    tar.add(item, arcname=rel_path)
        
        logger.info(f"Backup created: {backup_path}")
        return backup_path
    
    def restore_backup(self, backup_path: str, target_dir: Optional[str] = None) -> bool:
        """
        恢复备份
        
        Args:
            backup_path: 备份文件路径
            target_dir: 恢复目标目录，默认使用 storage base
        """
        import tarfile
        
        target = Path(target_dir) if target_dir else self.storage.base_path
        target.mkdir(parents=True, exist_ok=True)
        
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(target)
            
            logger.info(f"Backup restored to: {target}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """列出所有备份"""
        backups = []
        
        for backup_file in self.backup_dir.glob('*.tar.gz'):
            stat = backup_file.stat()
            backups.append({
                'name': backup_file.stem,
                'path': str(backup_file),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return sorted(backups, key=lambda x: x['created'], reverse=True)
    
    def cleanup_old_backups(self, keep_days: int = 7, dry_run: bool = False) -> int:
        """
        清理旧备份
        
        Args:
            keep_days: 保留天数
            dry_run: 仅预览
            
        Returns:
            删除的备份数量
        """
        cutoff = datetime.now() - timedelta(days=keep_days)
        deleted = 0
        
        for backup_file in self.backup_dir.glob('*.tar.gz'):
            mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if mtime < cutoff:
                if not dry_run:
                    backup_file.unlink()
                deleted += 1
        
        logger.info(f"Cleaned up {deleted} old backups")
        return deleted
    
    async def auto_backup(self, 
                         interval_hours: int = 24,
                         keep_days: int = 7,
                         include_patterns: List[str] = None):
        """
        自动备份任务
        
        这是一个长期运行的协程，需要在 asyncio 事件中运行
        """
        while True:
            try:
                # 创建备份
                self.create_backup(include_patterns=include_patterns)
                
                # 清理旧备份
                self.cleanup_old_backups(keep_days=keep_days)
                
                logger.info(f"Auto backup completed. Next in {interval_hours} hours")
                
            except Exception as e:
                logger.error(f"Auto backup failed: {e}")
            
            await asyncio.sleep(interval_hours * 3600)


class DataVault:
    """
    数据保险箱
    
    OPC200 核心安全组件，实现数据分级存储
    
    存储层级：
    - local-only: 绝不上云，本地加密存储
    - encrypted: 可同步，但需要加密
    - normal: 普通存储
    """
    
    def __init__(self, 
                 base_path: str, 
                 vault_password: Optional[str] = None):
        """
        Args:
            base_path: 保险箱根目录
            vault_password: 保险箱密码（用于加密层）
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化各层存储
        self.local_storage = StorageManager(self.base_path / "local-only")
        self.normal_storage = StorageManager(self.base_path / "normal")
        
        # 加密层
        if vault_password:
            base_encrypted = StorageManager(self.base_path / "encrypted")
            self.encrypted_storage = EncryptedStorage(
                base_encrypted, vault_password
            )
        else:
            self.encrypted_storage = None
    
    def store(self, 
             tier: str, 
             path: str, 
             content: Any,
             encrypt: bool = False):
        """
        存储数据
        
        Args:
            tier: 存储层级 (local-only/encrypted/normal)
            path: 相对路径
            content: 内容（字符串或字典）
            encrypt: 是否加密（仅对 encrypted 层有效）
        """
        if tier == "local-only":
            if isinstance(content, dict):
                self.local_storage.write_json(path, content)
            else:
                self.local_storage.write_file(path, content)
        
        elif tier == "encrypted":
            if self.encrypted_storage is None:
                raise ValueError("Vault password required for encrypted tier")
            
            if isinstance(content, dict):
                self.encrypted_storage.write_encrypted_json(path, content)
            else:
                self.encrypted_storage.write_encrypted(path, content)
        
        else:  # normal
            if isinstance(content, dict):
                self.normal_storage.write_json(path, content)
            else:
                self.normal_storage.write_file(path, content)
    
    def retrieve(self, tier: str, path: str) -> Optional[Any]:
        """获取数据"""
        if tier == "local-only":
            return self.local_storage.read_json(path) or self.local_storage.read_file(path)
        
        elif tier == "encrypted":
            if self.encrypted_storage is None:
                raise ValueError("Vault password required for encrypted tier")
            
            result = self.encrypted_storage.read_encrypted_json(path)
            if result is None:
                result = self.encrypted_storage.read_encrypted(path)
            return result
        
        else:  # normal
            return self.normal_storage.read_json(path) or self.normal_storage.read_file(path)
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """获取审计日志"""
        log_path = self.base_path / "audit" / "access.log"
        if log_path.exists():
            with open(log_path, 'r') as f:
                return [json.loads(line) for line in f if line.strip()]
        return []
    
    def log_access(self, action: str, path: str, user: str):
        """记录访问日志"""
        log_dir = self.base_path / "audit"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'path': path,
            'user': user
        }
        
        with open(log_dir / "access.log", 'a') as f:
            f.write(json.dumps(entry) + '\n')
