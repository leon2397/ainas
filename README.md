# AI-NAS Media Manager

> NAS 上的图片视频，用 AI 管理海量私有资产——私有部署，数据不出户。

![Version](https://img.shields.io/badge/version-7.0.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![FastAPI](https://img.shields.io/badge/fastapi-0.115.5-orange)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 核心功能

- **AI 智能分类** —— 自动识别人物、场景、地点，无需手动整理
- **媒体扫描** —— 自动发现 NAS 上的图片和视频，提取 EXIF 信息
- **智能相册** —— 按时间、人物、场景自动生成相册
- **语义搜索** —— 用自然语言搜索图片，比如「去年夏天的海边」
- **Docker 单容器** —— 一键部署到任何 Linux 设备（群晖/威联通实测）
- **纯 CPU 推理** —— 无需 GPU，开箱即用

## 技术栈

```
┌─────────────────────────────────────────┐
│           Docker 单容器                  │
│  ┌─────────┐   ┌──────────┐   ┌──────────────────┐
│  │  Nginx  │ → │ FastAPI  │ → │ SQLite + ChromaDB │
│  └─────────┘   └──────────┘   └──────────────────┘
│                    ↓              ↓        │
│         ONNX Runtime(CPU)   媒体扫描 / AI 分类  │
│              + FFmpeg（视频处理）            │
│   NAS 媒体文件（本地 / SMB / SSH）           │
└─────────────────────────────────────────┘
```

- 后端：Python 3.12+ / FastAPI 0.115.5 / SQLite(WAL) / ChromaDB 向量检索
- AI：ONNX Runtime CPU 推理，无需 GPU
- 前端：原生 HTML/JS（Vue3 重构中）
- 部署：Docker Compose / K8s / systemd（deb/rpm 包）

## 快速开始

### Docker（推荐）

```bash
cp .env.example .env
# 编辑 .env：设置 NAS_PATH 为你的媒体文件目录，生成 AI_NAS_JWT_SECRET
docker compose up -d
```

访问 **http://localhost:8000**，默认账号 `admin` / `admin123`（**首次登录后请立即修改密码**）。

### 本地运行（开发/验证）

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r backend/requirements-min.txt          # 轻量依赖；完整 AI 依赖用 backend/requirements.txt
export NAS_PATH=./nas                                # Windows: set NAS_PATH=./nas
python backend/main.py
```

### 一键安装（Linux）

```bash
sudo bash deploy/install.sh
```

## 已测试环境

| 环境 | 状态 | 说明 |
|------|------|------|
| Ubuntu 20.04+ | ✅ Docker Compose | 推荐生产环境 |
| Debian 11+ | ✅ Docker Compose | |
| 群晖 DSM 7+ | ✅ Docker Compose | |
| 威联通 QTS 5+ | ✅ Docker Compose | |
| Windows Server + Docker | ✅ 开发测试 | |
| macOS | ⚠️ 可开箱 | 生产推荐 Linux |

## 目录结构

```
ainas/
├── backend/            # FastAPI 后端主体
│   ├── main.py         #   入口（端口 8000）
│   ├── routes/         #   API 路由（media/albums/auth/devices/ai/...）
│   ├── services/       #   业务逻辑（扫描/分类/去重/缩略图/OCR...）
│   ├── ai/             #   AI 引擎（人脸/场景/向量）
│   ├── core/           #   核心库（认证/缓存/配置/数据库）
│   ├── plugins/        #   插件体系（存储/AI 引擎）
│   ├── enterprise/     #   企业特性（RBAC/SSO/审计/多租户）
│   └── tests/          #   单元/集成/e2e 测试
├── frontend/           # Web 前端（HTML/JS/CSS）
├── config/             # YAML 配置（存储/云/设备/AI 引擎）
├── deploy/             # Linux 部署脚本（安装/更新/回滚/健康检查）
├── build/              # 打包资产（deb/rpm/systemd 模板）
├── k8s/                # Kubernetes 部署清单
├── docs/               # 项目文档（总览/用户/开发/运维/架构）
└── tests/              # 测试套件（unit/integration/e2e/performance）
```

## 开发

```bash
pip install -r backend/requirements.txt
pytest backend/tests/ -q          # 或 python backend/run_tests.py
```

- 开发规范：[DEVELOPMENT_RULES.md](DEVELOPMENT_RULES.md)
- 已知问题与修复记录：[BUGS.md](BUGS.md)
- 版本历史：[CHANGELOG.md](CHANGELOG.md)
- 部署后 API 文档：http://localhost:8000/docs

## 当前状态

- 代码基底：V7.0.0（群晖/威联通/Docker 生产验证版）
- 本仓库为 V7 重组基线：已清除开发杂物、运行时数据与敏感配置
- 已知问题：见 BUGS.md（12 条记录，9 条已修复闭环）
- 远端仓库：待定（GitHub / Gitee）

## License

MIT
