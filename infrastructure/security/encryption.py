"""
Encryption Service

加密服务 - 处理数据加密、解密和安全哈希
"""

import hashlib
import secrets
import base64
import json
from typing import Dict, List, Any, Optional, Union
import structlog
from datetime import datetime
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization

from .security_manager import SecurityConfig

logger = structlog.get_logger(__name__)


@dataclass
class EncryptionKey:
    """加密密钥信息"""
    key_id: str
    algorithm: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True


@dataclass
class EncryptedData:
    """加密数据结构"""
    data: str
    algorithm: str
    key_id: str
    iv: Optional[str] = None
    encrypted_at: datetime = datetime.now()


class EncryptionService:
    """
    加密服务
    
    提供对称加密、非对称加密、哈希和密钥管理功能
    """
    
    def __init__(self, config: SecurityConfig):
        self.config = config
        self.symmetric_keys: Dict[str, bytes] = {}
        self.asymmetric_keys: Dict[str, Dict[str, Any]] = {}
        self.key_info: Dict[str, EncryptionKey] = {}
        
        # 初始化默认密钥
        self._initialize_default_keys()
        
        logger.info("加密服务初始化完成")
    
    def _initialize_default_keys(self):
        """初始化默认密钥"""
        try:
            # 生成默认对称密钥
            default_key = self._generate_symmetric_key()
            key_id = "default_symmetric"
            
            self.symmetric_keys[key_id] = default_key
            self.key_info[key_id] = EncryptionKey(
                key_id=key_id,
                algorithm="Fernet",
                created_at=datetime.now()
            )
            
            # 生成默认非对称密钥对
            private_key, public_key = self._generate_asymmetric_key_pair()
            key_pair_id = "default_asymmetric"
            
            self.asymmetric_keys[key_pair_id] = {
                "private_key": private_key,
                "public_key": public_key
            }
            self.key_info[key_pair_id] = EncryptionKey(
                key_id=key_pair_id,
                algorithm="RSA",
                created_at=datetime.now()
            )
            
            logger.info("默认加密密钥已生成")
            
        except Exception as e:
            logger.error(f"初始化默认密钥失败: {e}")
            raise
    
    def _generate_symmetric_key(self) -> bytes:
        """生成对称密钥"""
        return Fernet.generate_key()
    
    def _generate_asymmetric_key_pair(self) -> tuple:
        """生成非对称密钥对"""
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        return private_key, public_key
    
    def _derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """从密码派生密钥"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    async def encrypt_data_symmetric(
        self,
        data: str,
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """对称加密数据"""
        try:
            if key_id is None:
                key_id = "default_symmetric"
            
            if key_id not in self.symmetric_keys:
                raise ValueError(f"密钥不存在: {key_id}")
            
            key = self.symmetric_keys[key_id]
            fernet = Fernet(key)
            
            encrypted_bytes = fernet.encrypt(data.encode())
            encrypted_data = base64.b64encode(encrypted_bytes).decode()
            
            return EncryptedData(
                data=encrypted_data,
                algorithm="Fernet",
                key_id=key_id
            )
            
        except Exception as e:
            logger.error(f"对称加密失败: {e}")
            raise
    
    async def decrypt_data_symmetric(
        self,
        encrypted_data: EncryptedData
    ) -> str:
        """对称解密数据"""
        try:
            key_id = encrypted_data.key_id
            
            if key_id not in self.symmetric_keys:
                raise ValueError(f"密钥不存在: {key_id}")
            
            key = self.symmetric_keys[key_id]
            fernet = Fernet(key)
            
            encrypted_bytes = base64.b64decode(encrypted_data.data.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
            return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"对称解密失败: {e}")
            raise
    
    async def encrypt_data_asymmetric(
        self,
        data: str,
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """非对称加密数据"""
        try:
            if key_id is None:
                key_id = "default_asymmetric"
            
            if key_id not in self.asymmetric_keys:
                raise ValueError(f"密钥对不存在: {key_id}")
            
            public_key = self.asymmetric_keys[key_id]["public_key"]
            
            encrypted_bytes = public_key.encrypt(
                data.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            encrypted_data = base64.b64encode(encrypted_bytes).decode()
            
            return EncryptedData(
                data=encrypted_data,
                algorithm="RSA",
                key_id=key_id
            )
            
        except Exception as e:
            logger.error(f"非对称加密失败: {e}")
            raise
    
    async def decrypt_data_asymmetric(
        self,
        encrypted_data: EncryptedData
    ) -> str:
        """非对称解密数据"""
        try:
            key_id = encrypted_data.key_id
            
            if key_id not in self.asymmetric_keys:
                raise ValueError(f"密钥对不存在: {key_id}")
            
            private_key = self.asymmetric_keys[key_id]["private_key"]
            
            encrypted_bytes = base64.b64decode(encrypted_data.data.encode())
            
            decrypted_bytes = private_key.decrypt(
                encrypted_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None
                )
            )
            
            return decrypted_bytes.decode()
            
        except Exception as e:
            logger.error(f"非对称解密失败: {e}")
            raise
    
    async def encrypt_data(
        self,
        data: str,
        algorithm: str = "symmetric",
        key_id: Optional[str] = None
    ) -> EncryptedData:
        """加密数据（通用接口）"""
        if algorithm.lower() == "symmetric":
            return await self.encrypt_data_symmetric(data, key_id)
        elif algorithm.lower() == "asymmetric":
            return await self.encrypt_data_asymmetric(data, key_id)
        else:
            raise ValueError(f"不支持的加密算法: {algorithm}")
    
    async def decrypt_data(self, encrypted_data: EncryptedData) -> str:
        """解密数据（通用接口）"""
        if encrypted_data.algorithm == "Fernet":
            return await self.decrypt_data_symmetric(encrypted_data)
        elif encrypted_data.algorithm == "RSA":
            return await self.decrypt_data_asymmetric(encrypted_data)
        else:
            raise ValueError(f"不支持的解密算法: {encrypted_data.algorithm}")
    
    def hash_data(
        self,
        data: str,
        algorithm: str = "sha256",
        salt: Optional[str] = None
    ) -> str:
        """哈希数据"""
        try:
            if salt:
                data_to_hash = data + salt
            else:
                data_to_hash = data
            
            if algorithm.lower() == "sha256":
                return hashlib.sha256(data_to_hash.encode()).hexdigest()
            elif algorithm.lower() == "sha512":
                return hashlib.sha512(data_to_hash.encode()).hexdigest()
            elif algorithm.lower() == "md5":
                return hashlib.md5(data_to_hash.encode()).hexdigest()
            else:
                raise ValueError(f"不支持的哈希算法: {algorithm}")
                
        except Exception as e:
            logger.error(f"哈希数据失败: {e}")
            raise
    
    def hash_password(self, password: str) -> str:
        """哈希密码（带盐）"""
        try:
            salt = secrets.token_hex(16)
            password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return f"{salt}:{password_hash}"
        except Exception as e:
            logger.error(f"哈希密码失败: {e}")
            raise
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """验证密码"""
        try:
            salt, hash_part = password_hash.split(":", 1)
            expected_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return expected_hash == hash_part
        except Exception as e:
            logger.error(f"验证密码失败: {e}")
            return False
    
    def generate_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        try:
            return secrets.token_urlsafe(length)
        except Exception as e:
            logger.error(f"生成令牌失败: {e}")
            raise
    
    def generate_salt(self, length: int = 16) -> str:
        """生成盐值"""
        try:
            return secrets.token_hex(length)
        except Exception as e:
            logger.error(f"生成盐值失败: {e}")
            raise
    
    async def create_symmetric_key(self, key_id: str) -> bool:
        """创建对称密钥"""
        try:
            if key_id in self.symmetric_keys:
                raise ValueError(f"密钥已存在: {key_id}")
            
            key = self._generate_symmetric_key()
            
            self.symmetric_keys[key_id] = key
            self.key_info[key_id] = EncryptionKey(
                key_id=key_id,
                algorithm="Fernet",
                created_at=datetime.now()
            )
            
            logger.info(f"对称密钥已创建: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建对称密钥失败: {e}")
            return False
    
    async def create_asymmetric_key_pair(self, key_id: str) -> bool:
        """创建非对称密钥对"""
        try:
            if key_id in self.asymmetric_keys:
                raise ValueError(f"密钥对已存在: {key_id}")
            
            private_key, public_key = self._generate_asymmetric_key_pair()
            
            self.asymmetric_keys[key_id] = {
                "private_key": private_key,
                "public_key": public_key
            }
            self.key_info[key_id] = EncryptionKey(
                key_id=key_id,
                algorithm="RSA",
                created_at=datetime.now()
            )
            
            logger.info(f"非对称密钥对已创建: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"创建非对称密钥对失败: {e}")
            return False
    
    async def delete_key(self, key_id: str) -> bool:
        """删除密钥"""
        try:
            deleted = False
            
            if key_id in self.symmetric_keys:
                del self.symmetric_keys[key_id]
                deleted = True
            
            if key_id in self.asymmetric_keys:
                del self.asymmetric_keys[key_id]
                deleted = True
            
            if key_id in self.key_info:
                del self.key_info[key_id]
            
            if deleted:
                logger.info(f"密钥已删除: {key_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"删除密钥失败: {e}")
            return False
    
    async def export_public_key(self, key_id: str) -> Optional[str]:
        """导出公钥"""
        try:
            if key_id not in self.asymmetric_keys:
                return None
            
            public_key = self.asymmetric_keys[key_id]["public_key"]
            
            pem = public_key.public_key_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return pem.decode()
            
        except Exception as e:
            logger.error(f"导出公钥失败: {e}")
            return None
    
    async def import_public_key(self, key_id: str, pem_data: str) -> bool:
        """导入公钥"""
        try:
            if key_id in self.asymmetric_keys:
                raise ValueError(f"密钥已存在: {key_id}")
            
            public_key = serialization.load_pem_public_key(pem_data.encode())
            
            self.asymmetric_keys[key_id] = {
                "private_key": None,
                "public_key": public_key
            }
            self.key_info[key_id] = EncryptionKey(
                key_id=key_id,
                algorithm="RSA",
                created_at=datetime.now()
            )
            
            logger.info(f"公钥已导入: {key_id}")
            return True
            
        except Exception as e:
            logger.error(f"导入公钥失败: {e}")
            return False
    
    async def list_keys(self) -> List[EncryptionKey]:
        """列出所有密钥信息"""
        return list(self.key_info.values())
    
    async def get_key_info(self, key_id: str) -> Optional[EncryptionKey]:
        """获取密钥信息"""
        return self.key_info.get(key_id)
    
    async def encrypt_json(self, data: Dict[str, Any], **kwargs) -> EncryptedData:
        """加密JSON数据"""
        try:
            json_str = json.dumps(data, ensure_ascii=False)
            return await self.encrypt_data(json_str, **kwargs)
        except Exception as e:
            logger.error(f"加密JSON失败: {e}")
            raise
    
    async def decrypt_json(self, encrypted_data: EncryptedData) -> Dict[str, Any]:
        """解密JSON数据"""
        try:
            decrypted_str = await self.decrypt_data(encrypted_data)
            return json.loads(decrypted_str)
        except Exception as e:
            logger.error(f"解密JSON失败: {e}")
            raise
    
    async def get_encryption_statistics(self) -> Dict[str, Any]:
        """获取加密统计信息"""
        symmetric_keys_count = len(self.symmetric_keys)
        asymmetric_keys_count = len(self.asymmetric_keys)
        total_keys = len(self.key_info)
        
        # 按算法统计
        algorithm_stats = {}
        for key_info in self.key_info.values():
            algorithm_stats[key_info.algorithm] = algorithm_stats.get(key_info.algorithm, 0) + 1
        
        # 按状态统计
        active_keys = len([k for k in self.key_info.values() if k.is_active])
        inactive_keys = total_keys - active_keys
        
        return {
            "total_keys": total_keys,
            "symmetric_keys": symmetric_keys_count,
            "asymmetric_keys": asymmetric_keys_count,
            "active_keys": active_keys,
            "inactive_keys": inactive_keys,
            "algorithm_distribution": algorithm_stats
        }
