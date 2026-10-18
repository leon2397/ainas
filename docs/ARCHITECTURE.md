# AINAS 架构文档

> 版本：v1.0.0 | 更新日期：2026-10-18
> 本文描述当前代码库的真实结构（替代 V6 时代旧架构文档，旧版见 archive/07_架构文档/）

---

## 一、产品定位

隐私优先的本地 AI NAS 媒体管理系统：媒体文件留在自己的磁盘上，AI 分析（人脸、标签、语义搜索）在本地完成，不依赖云服务。目标设备为 NAS（群晖/威联通）、x86 服务器与边缘盒子。

## 二、技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 后端 | Python 3.11+ / FastAPI 0.115.x / Uvicorn | 197 个 API 路径（101 GET + 96 POST） |
| 数据库 | SQLite（aiosqlite）+ ChromaDB 向量库 | 元数据 `data/metadata.db`；ChromaDB 懒加载 |
| 前端 | 原生 HTML/CSS/JS（ES Module，无构建） | 13 个页面模块按需懒加载 |
| UI 框架 | Bootstrap 5.3.0 + FontAwesome 6.4.0 | 已本地化到 `frontend/vendor/`（1.4MB），不依赖外网 CDN |
| AI 推理 | ONNX Runtime + CPU Fallback | 人脸/标签/相似度 |
| 媒体处理 | Pillow / OpenCV / FFmpeg（外部依赖） | 缩略图按需生成 |
| 容器化 | Docker + Docker Compose + K8s(Helm) | 见 DEPLOYMENT.md |
| 部署 | systemd + Nginx | deploy/install.sh 一键安装 |

## 三、目录结构

```
ainas/
├── backend/                 FastAPI 应用主体
│   ├── main.py              入口（uvicorn，端口 8000）
│   ├── routes/              30+ 路由模块（auth/media/ai/devices/actions/settings...）
│   ├── services/            业务服务（扫描器、向量库、存储引擎...）
│   ├── modules/             8 大核心模块（见第四节）
│   ├── core/                基础设施（配置/补丁/缓存/补丁管理）
│   ├── database/            数据库层（兼容层，新代码用 modules/mod_database）
│   ├── plugins/             插件运行时
│   └── reset_password.py    管理员密码重设工具
├── frontend/                原生前端
│   ├── index.html           单页应用外壳（13 个页面区块内联）
│   ├── css/ js/             样式与脚本（js/pages/ 为懒加载页面模块）
│   └── vendor/              本地化的 Bootstrap/FontAwesome
├── config/                  配置文件
├── deploy/                  Linux 部署资产（install.sh / nginx / systemd）
├── build/                   打包资产（deb/rpm 模板）
├── k8s/                     Helm Chart
├── tests/                   测试套件（pytest）
├── scripts/                 运维脚本
├── docs/                    文档（本文档所在）
├── data/                    运行时数据（git 忽略）：metadata.db / uploads / 日志
└── docker-compose.yml       Docker 编排
```

## 四、后端八大模块（DEVELOPMENT.md 有铁律）

| 优先级 | 模块 | 职责 |
|--------|------|------|
| P1 | mod_database | SQLite 操作 + 迁移 + 默认管理员播种 |
| P1 | mod_auth | JWT 认证 + 密码加密 |
| P1 | mod_ai | AI 引擎（标签/人脸/相似度，重依赖懒加载） |
| P1 | mod_media | 媒体扫描 + 格式处理 + EXIF |
| P2 | mod_storage | 存储引擎（Local/SSH/SMB/NAS/Cloud） |
| P2 | mod_monitor | 系统监控 |
| P3 | mod_enterprise | 企业功能（租户/审计） |
| P3 | mod_plugins | 插件管理器 |

模块间只准通过公共 API 交互，禁止跨模块直接摸对方内部（详见 DEVELOPMENT.md）。

## 五、关键数据流

### 媒体扫描入库（核心链路）

```
用户点击「扫描目录」(POST /api/actions/scan {path, recursive, file_type})
  → MediaScanner 单次 os.walk 全树遍历（后缀统一小写比较，Linux 安全）
  → 逐文件：比对 file_size → 新文件提取 EXIF/GPS 写入 data/metadata.db
  → 对账清理：扫描范围内、磁盘上已消失的记录自动软删除（is_deleted=TRUE，可恢复）
  → 返回 task_id，前端轮询 /api/tasks/{id} 直到 success
  → 任务 result 回传统计：new / updated / unchanged / removed / errors
  → 计数对账（dry-run）：GET /api/media/count/reconcile?path=...
```

设计要点（计数准确性，2026-10-18 加固）：

- **单次遍历**：早期实现按扩展名逐个 rglob（26 扩展名 × 大小写 = 52 次全树遍历），已改为一次 `os.walk`
- **消失文件自动软删除**：只增不删会导致计数永久虚高；软删除可逆，绝不负物理删除行
- **清理范围隔离**：仅处理本次扫描根目录之内、且后缀落在本次允许范围内的记录；非递归扫描不执行清理（避免误判子目录现存文件）；上传目录/其他盘不受影响
- **`.ts` 刻意排除**：与 TypeScript 源码歧义，扫到代码目录会误索引为视频；如有需求可通过 `scan_directory(extensions={...})` 显式指定
- **增量语义**：`file_size` 一致且未被软删除 → `unchanged`（不刷新 `updated_at`）；体积变化或软删除记录重新出现 → `updated`（复活）

### 缩略图（按需生成）

```
GET /api/media/{id}/thumbnail
  → 若缓存存在（data/thumbnails/）直接返回
  → 否则从原文件路径读取 → Pillow/OpenCV 生成 → 缓存 → 返回
```

### 认证链路

```
POST /api/auth/login（form 编码）→ JWT(access_token)
  → 前端存 localStorage.token
  → 后续请求 Authorization: Bearer <token>
  → mod_auth 校验，角色：admin/user
```

### 前端页面加载

```
index.html 加载 app.js（ES Module）
  → checkAuth() 通过后 showPage('dashboard')
  → loadPageModule(name) 动态 import js/pages/<name>.js
  → 取模块单例 → 实例方法自动绑定到 window（供内联 onclick）
  → page.load() 拉取数据渲染
```

## 六、部署形态

| 形态 | 入口 | 说明 |
|------|------|------|
| Docker 单容器 | docker-compose.yml | 生产推荐，AI 依赖完整 |
| Linux 一键安装 | deploy/install.sh | systemd + nginx |
| K8s | k8s/ Helm Chart | 集群部署 |
| 本地运行 | python backend/main.py | 开发/体验 |

## 七、已知架构债（按优先级）

1. `backend/database/` 与 `modules/mod_database/` 双库层并存（启动有 DeprecationWarning，迁移未完成）
2. 数据库路径按进程 CWD 解析（`data/metadata.db`），本地跑与容器跑落点不同——已在 .gitignore 屏蔽，长期应改为基于项目根解析
3. 前端为无构建单页应用，页面区块全部内联在 index.html（约 700 行），`pages/*.html` 是死文件
4. 微服务版蓝图（integrated-platform）未纳入本仓，属二期方向

完整开发中的决策记录见 [adr/](adr/)。
