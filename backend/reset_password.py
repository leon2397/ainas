import hashlib
from loguru import logger
import secrets
import sqlite3

# 生成新的密码哈希
salt = secrets.token_hex(16)
hashed = hashlib.pbkdf2_hmac('sha256', b'admin123', salt.encode('utf-8'), 100000).hex()

logger.info(f"New salt: {salt}")
logger.info(f"New hash: {hashed}")

# 更新数据库
conn = sqlite3.connect('data/metadata.db')
cursor = conn.cursor()
cursor.execute('UPDATE users SET hashed_password=?, salt=? WHERE username=?', (hashed, salt, 'admin'))
conn.commit()
conn.close()
logger.info("Password reset to admin123")
