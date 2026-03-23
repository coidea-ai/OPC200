# OPC200 - 加密工具模块
# 提供通用加密/解密、哈希、签名功能

import os
import base64
import hashlib
import secrets
from typing import Optional, Union, Dict, Any
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend


class EncryptionError(Exception):
    """加密操作错误"""
    pass


class EncryptionManager:
    """
    加密管理器
    
    提供对称加密、非对称加密、哈希等常用加密功能
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Args:
            key: Fernet 密钥，为 None 则生成新密钥
        """
        if key is None:
            key = Fernet.generate_key()
        
        self._fernet = Fernet(key)
        self._key = key
    
    @classmethod
    def from_password(cls, password: str, salt: Optional[bytes] = None) -> tuple:
        """
        从密码派生密钥
        
        Returns:
            (EncryptionManager 实例, salt)
        """
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
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
    
    # ==================== 对称加密 ====================
    
    def encrypt(self, plaintext: Union[str, bytes]) -> bytes:
        """
        对称加密
        
        Args:
            plaintext: 明文内容
            
        Returns:
            加密后的密文
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        return self._fernet.encrypt(plaintext)
    
    def decrypt(self, ciphertext: bytes) -> str:
        """
        对称解密
        
        Args:
            ciphertext: 密文
            
        Returns:
            解密后的明文
            
        Raises:
            EncryptionError: 解密失败
        """
        try:
            return self._fernet.decrypt(ciphertext).decode('utf-8')
        except InvalidToken as e:
            raise EncryptionError("Invalid ciphertext or key") from e
    
    def encrypt_file(self, input_path: Union[str, Path], 
                    output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        加密文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径，默认为 input_path.enc
            
        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        
        if output_path is None:
            output_path = input_path.with_suffix(input_path.suffix + '.enc')
        else:
            output_path = Path(output_path)
        
        # 读取并加密
        with open(input_path, 'rb') as f:
            plaintext = f.read()
        
        ciphertext = self._fernet.encrypt(plaintext)
        
        # 写入
        with open(output_path, 'wb') as f:
            f.write(ciphertext)
        
        return output_path
    
    def decrypt_file(self, input_path: Union[str, Path],
                    output_path: Optional[Union[str, Path]] = None) -> Path:
        """
        解密文件
        
        Args:
            input_path: 加密文件路径
            output_path: 输出文件路径
            
        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        
        if output_path is None:
            # 移除 .enc 后缀
            if input_path.suffix == '.enc':
                output_path = input_path.with_suffix('')
            else:
                output_path = input_path.with_suffix('.dec')
        else:
            output_path = Path(output_path)
        
        # 读取并解密
        with open(input_path, 'rb') as f:
            ciphertext = f.read()
        
        plaintext = self._fernet.decrypt(ciphertext)
        
        # 写入
        with open(output_path, 'wb') as f:
            f.write(plaintext)
        
        return output_path


class AESGCMEncryption:
    """
    AES-GCM 加密（认证加密）
    
    适用于需要同时保证机密性和完整性的场景
    """
    
    def __init__(self, key: Optional[bytes] = None):
        """
        Args:
            key: 256-bit 密钥，为 None 则生成
        """
        if key is None:
            key = os.urandom(32)  # 256-bit
        
        if len(key) != 32:
            raise ValueError("Key must be 256 bits (32 bytes)")
        
        self._key = key
    
    def encrypt(self, plaintext: Union[str, bytes], 
                associated_data: Optional[bytes] = None) -> Dict[str, bytes]:
        """
        加密（带认证）
        
        Returns:
            {'ciphertext': ..., 'nonce': ..., 'tag': ...}
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)  # 96-bit nonce
        
        ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data)
        
        # AES-GCM 返回的 ciphertext 包含 auth tag
        return {
            'ciphertext': ciphertext,
            'nonce': nonce
        }
    
    def decrypt(self, ciphertext: bytes, nonce: bytes,
                associated_data: Optional[bytes] = None) -> bytes:
        """
        解密
        
        Raises:
            EncryptionError: 认证失败
        """
        aesgcm = AESGCM(self._key)
        
        try:
            return aesgcm.decrypt(nonce, ciphertext, associated_data)
        except Exception as e:
            raise EncryptionError("Decryption failed - data may be tampered") from e


class AsymmetricEncryption:
    """
    非对称加密（RSA）
    
    适用于密钥交换、数字签名等场景
    """
    
    def __init__(self, private_key: Optional[rsa.RSAPrivateKey] = None):
        """
        Args:
            private_key: RSA 私钥，为 None 则生成新密钥对
        """
        if private_key is None:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
        
        self._private_key = private_key
        self._public_key = private_key.public_key()
    
    @classmethod
    def from_file(cls, key_path: Union[str, Path], password: Optional[str] = None):
        """从文件加载密钥"""
        key_path = Path(key_path)
        
        with open(key_path, 'rb') as f:
            key_data = f.read()
        
        # 尝试 PEM 格式
        if b'-----BEGIN' in key_data:
            if b'PRIVATE' in key_data:
                private_key = serialization.load_pem_private_key(
                    key_data,
                    password=password.encode() if password else None,
                    backend=default_backend()
                )
                return cls(private_key)
        
        # 尝试 DER 格式
        private_key = serialization.load_der_private_key(
            key_data,
            password=password.encode() if password else None,
            backend=default_backend()
        )
        return cls(private_key)
    
    def save_private_key(self, path: Union[str, Path], 
                        password: Optional[str] = None):
        """保存私钥"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if password:
            encryption = serialization.BestAvailableEncryption(password.encode())
        else:
            encryption = serialization.NoEncryption()
        
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=encryption
        )
        
        with open(path, 'wb') as f:
            f.write(pem)
    
    def save_public_key(self, path: Union[str, Path]):
        """保存公钥"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with open(path, 'wb') as f:
            f.write(pem)
    
    def encrypt(self, plaintext: Union[str, bytes]) -> bytes:
        """
        使用公钥加密
        
        注意：RSA 不适合加密大量数据，通常用于加密对称密钥
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode('utf-8')
        
        return self._public_key.encrypt(
            plaintext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
    
    def decrypt(self, ciphertext: bytes) -> str:
        """使用私钥解密"""
        plaintext = self._private_key.decrypt(
            ciphertext,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return plaintext.decode('utf-8')
    
    def sign(self, message: Union[str, bytes]) -> bytes:
        """使用私钥签名"""
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        return self._private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def verify(self, message: Union[str, bytes], signature: bytes) -> bool:
        """使用公钥验证签名"""
        if isinstance(message, str):
            message = message.encode('utf-8')
        
        try:
            self._public_key.verify(
                signature,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False


class HashUtility:
    """
    哈希工具类
    """
    
    @staticmethod
    def sha256(data: Union[str, bytes]) -> str:
        """计算 SHA-256 哈希"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()
    
    @staticmethod
    def sha512(data: Union[str, bytes]) -> str:
        """计算 SHA-512 哈希"""
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        return hashlib.sha512(data).hexdigest()
    
    @staticmethod
    def file_hash(path: Union[str, Path], algorithm: str = 'sha256') -> str:
        """
        计算文件哈希
        
        Args:
            path: 文件路径
            algorithm: 哈希算法 (sha256, sha512, md5)
        """
        h = hashlib.new(algorithm)
        
        with open(path, 'rb') as f:
            while chunk := f.read(8192):
                h.update(chunk)
        
        return h.hexdigest()
    
    @staticmethod
    def verify_file(path: Union[str, Path], expected_hash: str, 
                   algorithm: str = 'sha256') -> bool:
        """验证文件哈希"""
        actual_hash = HashUtility.file_hash(path, algorithm)
        return secrets.compare_digest(actual_hash, expected_hash)


class SecureRandom:
    """
    安全随机数生成
    """
    
    @staticmethod
    def token_hex(length: int = 32) -> str:
        """生成十六进制随机令牌"""
        return secrets.token_hex(length)
    
    @staticmethod
    def token_urlsafe(length: int = 32) -> str:
        """生成 URL 安全随机令牌"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def random_bytes(length: int = 32) -> bytes:
        """生成随机字节"""
        return os.urandom(length)
    
    @staticmethod
    def choice(seq: list) -> Any:
        """从序列中随机选择"""
        return secrets.choice(seq)
    
    @staticmethod
    def randbelow(n: int) -> int:
        """生成 [0, n) 范围内的随机整数"""
        return secrets.randbelow(n)


# 便捷函数
def quick_encrypt(plaintext: str, password: str) -> bytes:
    """快速加密（使用密码）"""
    manager, _ = EncryptionManager.from_password(password)
    return manager.encrypt(plaintext)


def quick_decrypt(ciphertext: bytes, password: str, salt: bytes) -> str:
    """快速解密"""
    manager, _ = EncryptionManager.from_password(password, salt)
    return manager.decrypt(ciphertext)


def generate_secure_key() -> str:
    """生成安全的 API 密钥格式"""
    prefix = "opc"
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"
