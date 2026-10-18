# AINAS 部署运维

> 三种形态：Docker（推荐）/ Linux 一键安装 / K8s。全部于 2026-10 随 v1.0.0 基线整理验证。

## 一、Docker 部署（推荐）

### 快速开始

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
# 必改：JWT 签名密钥（openssl rand -hex 32 生成）
AI_NAS_JWT_SECRET=<随机长字符串>

# 要纳入管理的媒体目录（宿主机路径），容器内对应 /nas
NAS_PATH=E:/pic
```

```bash
docker compose up -d
docker compose logs -f        # 查看启动日志（含首次 admin 随机密码）
```

访问 http://localhost:8000 。

### 镜像布局说明（重要）

`backend/Dockerfile` 保留 `backend/` 目录层级、`frontend/` 与 backend 同级、`CMD python backend/main.py`——因为代码里前端路径按 `backend/../frontend` 解析。**改动 Dockerfile 时不要把这个相对结构压平**，否则容器内前端 404、UI 全坏（V7 镜像曾中招，2026-10-18 已修）。

### 挂载规则

| 宿主要求 | 挂载写法 |
|----------|----------|
| 管理 `E:/pic` | `NAS_PATH=E:/pic` → 容器内 `/nas` → 扫描路径填 `/nas` |
| 多个目录 | 改 docker-compose.yml 的 volumes，加挂载点 |
| 只读保护原文件 | 挂载加 `:ro`（扫描不需要回写原文件） |

### Docker 形态的能力优势

chromadb（向量检索/AI 功能）的 C++ 依赖 chroma-hnswlib 在 Linux 有预编译 wheel、Windows py3.13 没有——**要用人脸识别/语义搜索，必须用 Docker**。

## 二、Linux 一键安装

```bash
sudo bash deploy/install.sh
```

脚本完成：创建 `ainas` 用户与数据目录 → 安装依赖 → 注册 systemd 服务 → 配置 Nginx 反向代理。

```bash
systemctl status ainas      # 状态
systemctl restart ainas     # 重启
journalctl -u ainas -f      # 日志
```

数据目录默认 `/var/lib/ainas`（`DATA_DIR`，install.sh 顶部可改）。

### Nginx

deploy/ 下带现成配置：静态资源缓存、`/api` 与 `/ws` 反代到 8000。HTTPS 用 certbot 或自有证书。

## 三、K8s

```bash
helm install ainas ./k8s
```

Helm Chart 含 Deployment + Service + PVC（数据卷挂 `metadata.db` 所在目录）。媒体目录用 hostPath 或 NFS PV 挂载。

## 四、配置项速查（.env）

| 变量 | 必填 | 说明 |
|------|------|------|
| `AI_NAS_JWT_SECRET` | ✅ | JWT 签名密钥，随机长字符串 |
| `NAS_PATH` | Docker 必需 | 宿主机媒体目录 → 容器 `/nas` |
| `DATA_DIR` | 可选 | 数据目录（默认按进程 CWD 的 `data/`） |
| `PORT` | 可选 | 服务端口（默认 8000） |

完整模板见 [.env.example](../.env.example)。

## 五、升级流程

1. `git pull` 新版本
2. 停服务（`systemctl stop ainas` 或 `docker compose down`）
3. **备份 `data/metadata.db`**
4. 更新依赖（Docker 重新 build；本地 `pip install -r backend/requirements-min.txt`）
5. 启动，确认 `/health` 200、仪表盘数据正常
6. 数据库 schema 迁移自动执行（mod_database 启动时检查）

## 六、健康检查

```bash
curl http://localhost:8000/health        # 存活探针
curl http://localhost:8000/openapi.json  # 应用完整性（500 说明有路由级故障）
```

K8s 探针和 docker-compose healthcheck 已配置 `/health`。

## 七、备份（运维必读）

- **必须备份**：`data/metadata.db`（唯一权威数据源）
- 停服备份最简单；不停服用 `sqlite3 data/metadata.db ".backup backup.db"`
- thumbnails/logs/venv 不用备份
- `.env` 含密钥，单独妥善保管，**不要进 git**

详见 [ADMIN_GUIDE.md](ADMIN_GUIDE.md#三数据与备份)。
