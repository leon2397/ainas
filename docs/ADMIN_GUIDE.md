# AINAS 管理员手册

> 面向部署与运维者：账号体系、系统配置、备份恢复、安全加固。

## 一、账号与权限

### 默认管理员

- 首次启动自动创建 `admin`，密码**随机生成并打在启动日志**（V7 起的既定行为，防止默认弱口令）
- 重设密码：停止服务 → `python backend/reset_password.py` → 重启

### 角色

| 角色 | 能力 |
|------|------|
| admin | 全部功能：用户管理、设置、审计日志 |
| user | 媒体浏览、上传、相册（无管理功能） |

### 用户管理（用户页）

- 创建用户：分配角色，初始密码由管理员设定
- 禁用/删除用户
- 密码策略在设置页维护

## 二、系统配置（设置页）

| 配置项 | 说明 |
|--------|------|
| JWT 密钥 | `.env` 的 `AI_NAS_JWT_SECRET`，**必须修改为随机长字符串**；改了之后旧 token 全部失效 |
| 扫描参数 | 并发数、哈希算法、排除规则 |
| 存储后端 | Local / SSH / SMB / Cloud（mod_storage） |
| 监控告警 | 阈值与通知方式 |

配置文件优先级：环境变量 > `.env` > `config/` 默认值。

## 三、数据与备份

### 数据在哪

| 数据 | 位置 | 说明 |
|------|------|------|
| 元数据库 | `data/metadata.db` | **唯一权威数据源**，必须备份 |
| 缩略图缓存 | `data/thumbnails/` | 可随时重建，不用备份 |
| 上传的文件 | `data/uploads/` | 按上传时间归档 |
| 日志 | `logs/`、`data/logs/` | 轮转，可清理 |
| 媒体原文件 | 你扫描的目录（如 `E:/pic`） | **系统从不改动原文件** |

### 备份策略

1. **必备份**：`data/metadata.db`（丢了它等于丢了整个媒体库索引）
2. **建议备份**：`.env`（含密钥，单独妥善保管）、`config/`
3. **不用备份**：thumbnails、logs、venv
4. 备份数据库前先停服务（或用 sqlite3 的 `.backup` 命令做在线备份），直接拷贝 .db 文件有 WAL 不一致风险

### 恢复

1. 停服务
2. 用备份的 `metadata.db` 替换 `data/metadata.db`
3. 启动服务，扫描一遍原媒体目录做一致性校验（增量语义不会重复入库）

## 四、安全清单（上线前逐项过）

- [ ] `AI_NAS_JWT_SECRET` 已改为随机长密钥（`openssl rand -hex 32`）
- [ ] admin 密码已修改
- [ ] `.env` 不在 git 里（.gitignore 已含），不在 Web 可访问目录
- [ ] 服务不直接裸奔公网：前面挂 Nginx + HTTPS，或只监听内网
- [ ] `data/` 与 `logs/` 不做 Web 静态目录
- [ ] 定期轮换密钥（轮换后所有用户需重新登录）
- [ ] Docker 部署时 `NAS_PATH` 只挂载需要的目录，按只读挂载更安全（如果不需要回写）

## 五、运维操作

### 查看服务状态

```bash
# systemd（一键安装方式）
systemctl status ainas
journalctl -u ainas -f          # 实时日志

# Docker
docker compose logs -f
```

### 日志位置

- 应用日志：`logs/`（loguru 轮转）
- 首次启动的 admin 随机密码只在控制台/首次日志里出现，**改完密码后这份日志可清**

### 升级

1. 拉取新版本代码
2. 停服务 → 备份 `data/metadata.db` → 更新依赖 → 重启
3. 数据库迁移由 `mod_database` 自动执行（启动时检查 schema 版本）

## 六、审计

审计日志记录：登录成功/失败、用户增删、权限变更、扫描/删除等关键操作。在「审计日志」页查看，按时间/操作人筛选。

## 七、故障速查

见 [TROUBLESHOOTING.md](TROUBLESHOOTING.md)。管理员高频项：

- 登录 401 → 密钥是否改过、token 是否过期
- 端口占用 → `netstat -ano | findstr 8000`
- 磁盘增长 → thumbnails 和 logs 可定期清理
