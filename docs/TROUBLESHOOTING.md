# AINAS 故障排查与已知问题

> 遇到问题先查本文。历史 BUG 完整记录见 [archive/BUGS.md](archive/BUGS.md)（V7 时代）。

## 一、已知限制（产品边界，非缺陷）

| 限制 | 影响 | 规避 |
|------|------|------|
| Windows 本地无 chromadb wheel（chroma-hnswlib 不支持 py3.13） | AI 功能（人脸/语义搜索）不可用；懒加载不影响启动与其他功能 | Docker 部署（Linux 有 wheel） |
| rawpy 未随轻量依赖安装 | RAW 格式（cr2/nef/arw）读取 | 安装完整依赖 `backend/requirements.txt` |
| 数据库路径按进程 CWD 解析 | 从不同目录启动会建不同的 `data/metadata.db` | 固定从项目根启动；Docker 内已固定 |

## 二、高频问题

### 1. 登录 401 / token 失效

- 改过 `AI_NAS_JWT_SECRET`？→ 旧 token 全部失效，重新登录
- 忘记 admin 密码？→ 停服务，`python backend/reset_password.py`，重启
- 确认用的是表单格式（username/password 字段），不是 JSON body

### 2. 仪表盘统计不更新

- 正常机制：每 30 秒自动刷新；切走切回/切标签页立即刷新；标题右侧有手动刷新按钮
- 浏览器开了旧标签页 → **Ctrl+Shift+R 硬刷新**（旧缓存页面不会自愈）
- 还不行 → 按 F12 看 Console 有无红色错误，截图给开发

### 3. 页面样式丢失 / 按钮点了没反应

- 几乎一定是浏览器缓存了旧版静态资源 → Ctrl+Shift+R
- 内网环境确认前端 vendor 资源完整（`frontend/vendor/`，已本地化，不依赖 CDN）

### 4. 扫描不到文件 / 数量对不上

- **路径写法**：本地运行用宿主机路径（`E:/pic`）；Docker 必须用容器内路径（`/nas`）
- 格式不在支持列表（见 QUICKSTART.md；`.ts` 刻意不收，与 TypeScript 歧义）
- 子目录没勾"递归"
- **先用对账端点定位**（dry-run，不写库）：
  ```
  GET /api/media/count/reconcile?path=E:\pic
  ```
  - `consistent=true` → 计数与磁盘一致，问题在上层展示
  - `phantom>0` → 库有盘无（文件在 AINAS 外被删/移），同路径重扫一次即自动软删除、计数回落
  - `missing>0` → 盘有库无，重扫即自动索入
  - `revivable>0` → 之前软删除的文件回来了，重扫自动复活
  - `walk_errors>0` → 目录不可读（权限/外接盘离线），检查挂载
- 任务页看该次扫描任务的错误信息（`error_files` 明细在任务 result 中）

### 5. 缩略图慢或不出

- 首次按需生成，大图慢；之后有缓存（`data/thumbnails/`）
- 原文件被移动/删除 → 缩略图无法生成，重新扫描修复索引
- 视频缩略图依赖首帧提取（cv2 直接解码，不依赖 ffmpeg）；若仍失败，检查视频文件本身是否损坏

### 6. 端口 8000 被占用

```bash
# Windows
netstat -ano | findstr 8000
# Linux
ss -tlnp | grep 8000
```

换端口或杀掉占用进程。

### 7. Docker 起不来

- `docker compose logs` 看首屏：缺 `AI_NAS_JWT_SECRET` 会拒绝启动
- 前端 404 → Dockerfile 的目录层级被改平了（见 DEPLOYMENT.md 镜像布局说明）

## 三、v1.0.0 重建时修复的缺陷（2026-10-18）

这些问题在 V7.0.0 遗留代码里全部真实存在，已全部修复并提交。保留记录以防回归：

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | uvicorn worker 崩溃循环，服务起不来 | `main.py` venv 警告里的 `input()` 在 stdin EOF 时抛 EOFError | 改为仅交互式 TTY 暂停 |
| 2 | `/openapi.json` 500 | FastAPI 0.115.x 的 status_code UnboundLocalError；补丁只匹配 0.135.x 结构，静默未生效 | 补丁增加 0.115.x 结构匹配 |
| 3 | 前端只剩裸 HTML，样式逻辑全无 | `routes/frontend.py` 未注册 `/css/` `/js/` 等静态路由，全部 404 | 新增显式静态路由 + MIME + 路径穿越防护（不用 catch-all，避免遮蔽 API） |
| 4 | Docker 镜像 UI 全坏 | 前端被 COPY 到 `/app/static`，代码解析 `/frontend` | Dockerfile 保留 backend/ 层级 + frontend 同级 |
| 5 | 页面依赖外网 CDN，内网白屏 | Bootstrap/FontAwesome 走 jsdelivr | 本地化到 `frontend/vendor/`（1.4MB） |
| 6 | **所有页面数据渲染从不执行**（统计永远 0） | `loadPageModule` 对单例对象执行 `new`（`module['dashboardPage']` 是实例不是类）→ "PageClass is not a constructor"，13 个页面模块全部加载失败 | 单例优先 + 类兜底；页面方法自动绑定 window |
| 7 | 点任何按钮没反应 | app.js 20+ 个全局委托引用从未 import 的页面单例，每次点击 ReferenceError | 统一 `onPage()` 懒加载委托 |
| 8 | 仪表盘任务/设备卡片报错 | 元素 ID 不符（`recent-tasks-list` vs HTML 的 `recent-tasks`） | 修正 ID + 渲染函数空值防护 |
| 9 | 数据不自动更新 | 仪表盘只加载时取数一次，无轮询 | 30s 轮询 + visibilitychange + 手动刷新按钮 |
| 10 | **视频缩略图全部 500**（WinError 2 系统找不到指定的文件） | 提帧直接 `subprocess ffmpeg`，而 ffmpeg 既不在 Windows PATH 也不在 Docker 镜像里；Windows 直接运行和 Docker 部署两条路都坏 | cv2.VideoCapture 直接解码首帧（opencv 是硬依赖，无需外部二进制），ffmpeg 降级为备选 |
| 11 | uvicorn 父进程死后 worker 变孤儿继续占端口 | 父进程被 kill 时 worker 不退出，端口不释放、代码更新不生效 | 运维注意：重启前先 `netstat -ano \| findstr 8000` 找 LISTENING PID 杀干净再启动 |
| 12 | 内存认证模式下改角色/禁用/删除用户静默无效 | `mod_auth/service.py` 的 `update_user_role`/`toggle_user`/`delete_user` 只写了 DB 分支，漏了 fallback 分支（`update_password` 有对照） | 补全 else 分支，操作内存用户表 |
| 13 | **`/favicon.ico` 无认证泄露源码**（4,180 B frontend.py） | favicon 文件缺失时路由以 `__file__` 兜底返回 text/plain；浏览器自动请求 favicon，用户无感知 | 缺失返回 404；已生成 `frontend/favicon.ico` |

## 四、报告新问题

1. 记录：复现步骤、预期、实际、环境（本地/Docker、Python 版本）
2. 查 `logs/` 应用日志和浏览器 Console
3. 提交到团队 issue，按 DEVELOPMENT.md 的 BUG 流程处理
