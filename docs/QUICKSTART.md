# 5 分钟运行 AINAS

> 本文所有步骤均于 2026-10-18 在 Windows + Python 3.13 环境实测通过。
> 目标：让产品跑起来，能看到仪表盘和媒体库。

## 方式一：本地直接运行（适合体验/开发）

```bash
# 1. 创建虚拟环境（Python 3.11+，实测 3.13）
python -m venv .venv
.venv/Scripts/activate        # Windows；Linux/macOS: source .venv/bin/activate

# 2. 安装依赖（轻量集；完整 AI 依赖见下方说明）
pip install -r backend/requirements-min.txt

# 3. 启动
python backend/main.py
```

启动成功后访问 **http://localhost:8000**。

### 首次登录

- 账号：`admin`
- 密码：**首次启动时随机生成，打印在启动日志里**（不是固定的 admin123）
- 忘记密码：停止服务后运行 `python backend/reset_password.py` 重设

## 方式二：Docker（推荐的生产形态）

```bash
cp .env.example .env           # 生成并编辑 AI_NAS_JWT_SECRET
docker compose up -d
```

访问 **http://localhost:8000**。Docker 形态附带完整 AI 依赖（chromadb 等），Windows 本地缺失的 AI 功能在容器内可用。

## 接入你的媒体目录（核心功能）

产品通过"扫描"把媒体目录纳入管理——**只建索引，不移动、不复制原文件**：

1. 登录后进入「媒体库」
2. 点工具栏的 **扫描目录**
3. 输入目录路径（如 `E:/pic`），勾选"包含子目录"，点开始扫描
4. 等待任务完成，仪表盘与媒体库自动更新（约 30 秒内）

重复扫描是增量的：已入库文件只更新记录，不会重复（实测 8,662 个文件重扫零重复）。

### 各部署方式的路径规则

| 部署方式 | 扫描路径怎么写 |
|----------|----------------|
| 本地运行 | 宿主机的真实路径，如 `E:/pic`、`D:\Photos` |
| Docker | 容器内路径。先把宿主目录挂载进容器（docker-compose 默认把 `NAS_PATH` 挂到 `/nas`），再扫 `/nas` |

### 支持的格式

- 图片：jpg / jpeg / png / gif / webp / bmp / heic
- 视频：mp4 / mov / avi / mkv / webm
- RAW（cr2/nef/arw 等）：需安装完整依赖集（懒加载）

扫描会提取 EXIF（拍摄时间、相机型号、GPS）并计算文件哈希（用于去重）。

## 已知限制（不挡使用）

| 限制 | 影响 | 规避 |
|------|------|------|
| Windows 本地无 chromadb wheel（chroma-hnswlib 不支持 py3.13） | 向量检索/语义搜索不可用，懒加载不影响其他功能 | 用 Docker 部署（Linux 有 wheel） |
| rawpy 未随轻量集安装 | RAW 格式读取 | 装完整依赖集 `backend/requirements.txt` |

## 下一步

- [用户手册](USER_GUIDE.md)——媒体库怎么用
- [部署运维](DEPLOYMENT.md)——上线到服务器
- [故障排查](TROUBLESHOOTING.md)——遇到问题先看这里
