# AINAS 更新日志

所有重要的更改都将记录在此文件中。
格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

> **版本线说明**：2026-10-18 项目以 V7.0.0（生产验证版）为基底重组，版本号重置为 **v1.0.0**。
> 以下 v1.0.0 之前的历史记录（V1.0.0–V7.0.0）为重组前开发时期的原始流水，保留仅供追溯。

---

## [v1.0.0] - 2026-10-18 —— 重建基线（Re baseline）

> 从 V7.0.0 拣选产品文件重组为干净可运行的产品仓库，冒烟 + 端到端验证通过。

### 重组（Reorganization）

- 从 V7.0.0 组装产品：372 个受版本管理文件（原目录含约 150 个开发一次性脚本、venv-test、截图、部署 zip 及数 GB 杂物）
- 剔除运行时数据（metadata.db / chroma / 日志）与敏感配置（.env / 私钥）
- 建立 git 仓库与 `.gitignore`，完成工程基线（3 个初始 commit）
- 文档体系重建：docs/ 八大分区（快速开始/用户/管理员/部署/架构/开发/API/排查）+ adr/ 决策记录 + archive/ 历史归档

### 修复（Fixed）—— 9 个 V7 遗留缺陷

| # | 问题 | 影响 |
|---|------|------|
| 1 | `main.py` venv 警告中的 `input()` 在 uvicorn worker 子进程 stdin EOF 时崩溃循环 | 服务无法启动 |
| 2 | FastAPI 0.115.x `status_code` UnboundLocalError；补丁只匹配 0.135.x 结构静默失效 | `/openapi.json` 500 |
| 3 | `routes/frontend.py` 未注册 `/css/` `/js/` 等静态路由 | 前端全部 404，页面只剩裸 HTML |
| 4 | Dockerfile 将 frontend COPY 到 `/app/static`，代码解析 `/frontend` | 镜像内 UI 全坏 |
| 5 | 前端依赖 jsdelivr CDN | 内网部署白屏；已本地化 Bootstrap/FA 到 `frontend/vendor/` |
| 6 | `loadPageModule` 对单例对象执行 `new` | 13 个页面模块全部加载失败，所有数据渲染从不执行 |
| 7 | app.js 20+ 个全局事件委托引用从未 import 的页面单例 | 所有按钮点击 ReferenceError |
| 8 | 仪表盘元素 ID 不符（`recent-tasks-list` vs `recent-tasks`） | 任务/设备卡片 TypeError |
| 9 | 仪表盘无轮询无可见性刷新 | 页面开着数据永不更新 |

### 新增（Added）

- 媒体库「扫描目录」UI（此前只能手调 API）：路径输入 / 递归选项 / 任务轮询 / 完成自动刷新 / 记住上次路径
- 仪表盘 30 秒自动刷新 + 切回标签页立即刷新 + 手动刷新按钮
- `bindPageMethods`：页面模块加载后公共方法自动绑定 window，内联事件全覆盖
- 页面资源全量审计（30/30 资源 200）与 24 个 JS 文件语法校验纳入验证流程

### 验证（Verified）

- `/` `/docs` `/openapi.json` `/health` 全部 200；197 个 API 路径
- 登录 → me → media → ai/stats → cache/stats 全链路通过
- E:\pic 实测：8,418 图片 + 244 视频扫描入库（约 3 分钟），增量重扫零重复
- Edge 无头浏览器端到端：控制台零错误，仪表盘与媒体库真实渲染
- 路径穿越攻击 4 种模式全部 404

### 已知限制（Known limitations）

- Windows 本地无 chromadb wheel（chroma-hnswlib 不支持 py3.13）→ AI 功能需 Docker 部署
- rawpy 未随轻量依赖安装 → RAW 格式需完整依赖集

---

## [V7.0.0] - 2026-04（重组前历史记录，开发中状态）

### 当时状态

**已完成**：Phase 1-3（基础设施、核心模块、测试体系）
**进行中**：Phase 4（Docker 化）
**待开始**：Phase 5-6（文档完善、发布准备）

### Phase 2: 核心模块优化（节选）

- 全局代码规范扫描与修复（47 文件，116 print / 8 bare except）
- 重构 `core/auth.py`、`database/db.py`、`routes/ai.py`、`services/scanner.py`、`plugins/ai/cpu_engine.py`
- 修复 BUG-001（`detail:"1"`）：统一 `await db.fetchone/fetchall/execute`
- 新增统一日志系统（loguru）、16 个异常类、全局异常处理器
- 新增 `.env.example`、`BUGS.md`、`DEVELOPMENT_RULES.md`（后迁移至 docs/）

---

## [V6.0.3] - 2026-04-11

### 新增
- 完整的后端 API（~200 个端点）
- 前端界面（Bootstrap 5 SPA）
- AI 引擎框架（CPU + NPU）
- 存储插件系统（5 种）
- 用户权限管理（JWT + 三级角色）
- 系统监控和告警

### 已知问题
- AI 标签生成端点返回 `detail:"1"` 错误
- ChromaDB 依赖未安装（sqlite3 版本低）
- Docker 部署环境不统一

---

## [V5.0.0] - 2026-04-09

### 新增
- ARM 设备适配模块
- 一键部署脚本
- K8s 部署配置

---

## [V4.0.0] - 2026-04-07

### 新增
- WebSocket 实时通信
- 设备自动发现
- 任务调度系统

---

## [V3.0.0] - 2026-04-05

### 新增
- AI 分类服务
- 人脸检测引擎
- 缩略图缓存

---

## [V2.0.0] - 2026-04-04

### 新增
- 媒体扫描服务
- 相册管理
- 批量操作

---

## [V1.0.0] - 2026-04-03

### 新增
- 项目初始化
- FastAPI 后端框架
- SQLite 数据库
- 基础 API 端点
