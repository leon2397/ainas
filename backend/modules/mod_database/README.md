# mod_database — 数据库模块

## 职责

统一数据库访问层，基于 aiosqlite + SQLite3 + FTS5。

## 对外接口

```python
from modules.mod_database import Database, get_db, db, DATABASE_PATH
```

| 接口 | 说明 |
|------|------|
| `Database` | 数据库类，异步 SQLite 连接 |
| `db` | 全局单例实例 |
| `get_db()` | FastAPI Depends 注入函数 |
| `DATABASE_PATH` | 默认数据库路径 |

## Database 方法

### 基础查询
| 方法 | 说明 |
|------|------|
| `init()` | 初始化连接 + 建表 |
| `close()` | 关闭连接 |
| `execute(sql, params)` | 执行写操作 |
| `fetchone(sql, params)` | 查一行 → dict |
| `fetchall(sql, params)` | 查多行 → list[dict] |
| `fetchval(sql, params)` | 查标量值 |
| `insert_id()` | 获取最后插入 ID |

### 业务方法
| 方法 | 说明 |
|------|------|
| `add_media_file(data)` | 添加媒体文件 |
| `update_ai_analysis(...)` | 更新 AI 分析结果 |
| `search_media(keyword, ...)` | FTS5 全文检索 |
| `get_media_by_date(year, month)` | 按日期查询 |
| `create_album(name, type)` | 创建相册 |
| `get_albums(type)` | 获取相册列表 |
| `create_task(...)` | 创建任务 |
| `update_task_status(...)` | 更新任务状态 |
| `register_device(...)` | 注册设备 |
| `update_device_status(...)` | 更新设备状态 |
| `get_online_devices()` | 获取在线设备 |
| `init_default_admin()` | 初始化默认管理员 |
| `get_user_by_username(name)` | 查询用户 |
| `get_all_users()` | 获取所有用户 |
| `create_user(...)` | 创建用户 |
| `update_user_role(...)` | 更新角色 |
| `update_user_password(...)` | 更新密码 |
| `toggle_user_disabled(...)` | 启用/禁用 |
| `delete_user(name)` | 删除用户 |

## 数据表

- `media_files` — 媒体文件元数据 + FTS5 全文索引
- `albums` / `album_files` — 相册
- `tasks` — 异步任务
- `users` — 用户管理
- `devices` — 设备注册
- `ai_tags` — AI 标签统计
- `media_similar` — 相似图片

## 迁移

使用 `migrations.py` 管理数据库 Schema 版本：

```bash
python -m modules.mod_database.migrations          # 执行迁移
python -m modules.mod_database.migrations --plan   # 查看待执行
python -m modules.mod_database.migrations --version # 当前版本
```

## 依赖

仅依赖 `core` 包：
- `core.logger` — 日志
- `core.exceptions` — 异常类
