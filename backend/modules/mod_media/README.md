# mod_media — 媒体管理模块

## 职责

媒体文件扫描、格式处理、缩略图生成。

## 对外接口

```python
from modules.mod_media import MediaScanner, MediaFormatHandler, get_media_handler
```

## MediaScanner

| 方法 | 说明 |
|------|------|
| `scan_directory(path)` | 扫描目录，提取 EXIF/GPS |
| `get_file_hash(filepath)` | 计算文件哈希 |
| `extract_exif(filepath)` | 提取 EXIF 元数据 |
| `extract_gps(filepath)` | 提取 GPS 信息 |

## MediaFormatHandler

| 方法 | 说明 |
|------|------|
| `get_thumbnail(filepath, size)` | 生成缩略图 |
| `get_media_info(filepath)` | 获取媒体信息 |
| `convert_format(filepath, fmt)` | 格式转换 |
| `get_video_frame(filepath, time)` | 提取视频帧 |

## 依赖

- `core.logger`
- `modules.mod_database`（数据持久化）
- `PIL`（图片处理）
