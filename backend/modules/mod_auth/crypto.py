"""
密码加密工具
用于加密配置文件中的敏感信息
"""

import base64
import hashlib
from loguru import logger
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigCrypto:
    """配置加密工具"""
    
    def __init__(self, master_key: str = None):
        """
        初始化加密工具
        
        Args:
            master_key: 主密钥，用于派生加密密钥
        """
        if master_key is None:
            # 默认密钥（生产环境必须修改）
            master_key = "ai-nas-default-key-change-in-production"
        
        self.master_key = master_key.encode()
        self._init_cipher()
    
    def _init_cipher(self):
        """初始化加密器"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'ai-nas-salt',  # 生产环境应使用随机盐
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        加密字符串
        
        Args:
            plaintext: 明文
            
        Returns:
            加密后的字符串（base64编码）
        """
        if plaintext.startswith("encrypted:"):
            return plaintext  # 已经是加密格式
        
        encrypted = self.cipher.encrypt(plaintext.encode())
        return f"encrypted:{encrypted.decode()}"
    
    def decrypt(self, ciphertext: str) -> str:
        """
        解密字符串
        
        Args:
            ciphertext: 密文（格式：encrypted:xxx）
            
        Returns:
            解密后的明文
        """
        if not ciphertext.startswith("encrypted:"):
            return ciphertext  # 未加密，直接返回
        
        encrypted_data = ciphertext[10:].encode()  # 去掉 "encrypted:" 前缀
        decrypted = self.cipher.decrypt(encrypted_data)
        return decrypted.decode()
    
    def is_encrypted(self, text: str) -> bool:
        """检查是否已加密"""
        return text.startswith("encrypted:")


# 全局加密工具实例
config_crypto = ConfigCrypto()


def encrypt_password(password: str) -> str:
    """加密密码（便捷函数）"""
    return config_crypto.encrypt(password)


def decrypt_password(encrypted: str) -> str:
    """解密密码（便捷函数）"""
    return config_crypto.decrypt(encrypted)


# 测试
if __name__ == "__main__":
    # 测试加密解密
    test_password = "my-secret-password"
    encrypted = encrypt_password(test_password)
    logger.info(f"Original: {test_password}")
    logger.info(f"Encrypted: {encrypted}")
    decrypted = decrypt_password(encrypted)
    logger.info(f"Decrypted: {decrypted}")
    logger.info(f"Match: {test_password == decrypted}")
