# mod_storage — 存储模块

## 职责

多协议存储支持：本地、SSH/SFTP、SMB/CIFS、NAS、云存储。

## 对外接口

```python
from modules.mod_storage import (
    FileStorage,      # 抽象基类
    LocalStorage,     # 本地文件系统
    SSHStorage,       # SSH/SFTP
    SMBStorage,       # SMB/CIFS
    NasStorage,       # NAS 专用
    CloudStorage,     # 云存储
    get_storage,      # 获取存储实例
    get_storage_status,
)
```

## FileStorage 抽象方法

| 方法 | 说明 |
|------|------|
| `connect()` | 连接存储 |
| `disconnect()` | 断开连接 |
| `list_files(path)` | 列出文件 |
| `upload_file(src, dst)` | 上传文件 |
| `download_file(src, dst)` | 下载文件 |
| `delete_file(path)` | 删除文件 |
| `get_exif(filepath)` | 读取 EXIF |
| `get_thumbnail(filepath, size)` | 生成缩略图 |

## 获取存储实例

```python
from modules.mod_storage import get_storage

storage = get_storage('local', {'root_path': '/data'})
storage = get_storage('ssh', {'host': '192.168.1.100', 'user': 'admin'})
storage = get_storage('smb', {'server': 'NAS', 'share': 'photos'})
```

## 依赖

- `core.logger`
- `paramiko` (SSH, 可选)
- `pysmb` (SMB, 可选)
