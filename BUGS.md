# AI-NAS BUGS.md — 问题记录

> **规则**：遇到 BUG 先记录，后修复。测试阶段边测边记，测试完成后批量处理。
> 详见 `DEVELOPMENT_RULES.md` 中的「BUG 处理流程」。

---

## 当前未修复

### BUG-001: `/api/ai/tags/generate` 返回 `detail: "1"`
- **优先级**：🔴 P0（阻断功能）
- **模块**：routes/ai.py
- **发现日期**：2026-04-15
- **复现步骤**：`curl -X POST "http://localhost:8000/api/ai/tags/generate?file_ids=1"`
- **预期**：返回生成的标签列表
- **实际**：HTTP 500 `{"detail": "1"}`
- **根因**：
  1. `db.execute().fetchone()` 链式调用无效（aiosqlite 不支持）
  2. 多处 `db.execute()` 未加 await
  3. `get_face_albums()` / `get_smart_albums()` 缺少 `db: Depends(get_db)`
  4. 裸 `HTTPException(detail=str(e))` 吞掉堆栈
- **修复方案**：V7.0 Phase 2 重构 ai.py（已完成）
- **状态**：✅ 已修复（2026-04-16）
- **修复内容**：
  - 全部改为 `await db.fetchone()` / `await db.fetchall()` / `await db.execute()`
  - 所有端点添加 `db: Database = Depends(get_db)` 参数
  - 替换裸 HTTPException，异常由全局处理器捕获
  - 添加 loguru 日志

### BUG-002: ChromaDB 向量搜索不可用
- **优先级**：🟡 P1（功能降级）
- **模块**：plugins/ai/vector_db.py
- **发现日期**：2026-04-15
- **复现步骤**：调用任何向量搜索相关 API
- **预期**：返回相似图片
- **实际**：sqlite3 版本 < 3.35.0，ChromaDB 无法初始化
- **状态**：⏸ 已知限制

### BUG-003: Redis 缺失导致缓存降级
- **优先级**：🟢 P2（功能可用但性能受影响）
- **模块**：core/cache.py
- **发现日期**：2026-04-15
- **复现步骤**：无 Redis 服务器时启动服务
- **预期**：使用 Redis 缓存
- **实际**：降级为内存缓存（进程重启后丢失）
- **状态**：⏸ 已知限制

### BUG-004: ai.py 多处异步调用缺少 await
- **优先级**：🔴 P0（代码缺陷）
- **模块**：routes/ai.py
- **发现日期**：2026-04-15
- **状态**：✅ 已修复（2026-04-16，随 BUG-001 一起修复）

### BUG-005: FastAPI /openapi.json 返回 UnboundLocalError
- **优先级**：🔴 P0（阻断测试）
- **模块**：site-packages/fastapi/openapi/utils.py
- **发现日期**：2026-04-16
- **复现步骤**：访问 `/openapi.json` 端点
- **预期**：返回 OpenAPI schema
- **实际**：HTTP 500 `UnboundLocalError: cannot access local variable 'status_code'`
- **根因**：FastAPI 0.115.5 的 `utils.py` 中 `status_code` 变量在条件分支中未定义
- **修复方案**：手动 patch site-packages 中的 `fastapi/openapi/utils.py`
- **状态**：✅ 已修复（2026-04-16）
- **修复内容**：
  - 在 `if status_code_param is not None:` 块内添加 `else: status_code = "200"`
  - 在 `if status_code_param is not None:` 块外添加 `else: status_code = "200"`
  - 补丁脚本：`D:\temp\fix_fastapi_115.py`

### BUG-006: 测试 auth_token + python-jose 缺失
- **优先级**：🔴 P0（测试阻断）
- **模块**：tests/test_api.py + requirements.txt
- **发现日期**：2026-04-16
- **复现步骤**：`pytest tests/test_api.py`
- **预期**：所有认证测试通过
- **实际**：认证测试返回 401，token 为 "jwt-not-available"
- **根因**：
  1. `python-jose[cryptography]` 未在 requirements.txt 中
  2. `auth_token` fixture 是 `scope="module"`，被多个测试共享
- **修复方案**：
  1. 添加 `python-jose[cryptography]==3.3.0` 到 requirements.txt
  2. 将 `auth_token` fixture 从 `scope="module"` 改为默认（function）作用域
- **状态**：✅ 已修复（2026-04-16）

### BUG-008: 首页图片统计显示为零
- **优先级**：🟡 P1（误导用户）
- **模块**：后端 routes/media.py
- **发现日期**：2026-04-18
- **复现步骤**：登录后查看首页
- **预期**：显示实际图片数量
- **实际**：显示 0，但媒体库中有大量照片
- **根因**：FastAPI 路由顺序问题 - `/{file_id}` 在 `/count/by-type` 之前，导致 `/count/by-type` 被错误匹配
- **修复方案**：调整路由顺序，`/count/by-type` 积到 `/{file_id}` 之前
- **状态**：✅ 已修复（2026-04-18）
- **修复文件**：`/root/ai-nas/backend/routes/media.py`
- **验证**：API 返回 `{"images":200,"videos":0}`

### BUG-009: 首页无上传窗口
- **优先级**：🟡 P1（功能缺失）
- **模块**：前端 Dashboard
- **发现日期**：2026-04-18
- **复现步骤**：登录后查看首页
- **预期**：有上传按钮/窗口
- **实际**：找不到上传入口
- **根因**：前端完全没有上传相关代码
- **修复方案**：
  1. api.js 添加 `upload()` 方法
  2. index.html 添加上传按钮和弹窗
  3. dashboard.js 添加 `showUploadModal()` 和 `uploadFiles()` 方法
- **状态**：✅ 已修复（2026-04-18）
- **修复文件**：`/var/www/ai-nas/js/api.js`, `/var/www/ai-nas/index.html`, `/var/www/ai-nas/js/pages/dashboard.js`

### BUG-010: 媒体库图片无"移入相册"功能
- **优先级**：🟡 P1（功能缺失）
- **模块**：前端 Media 详情页
- **发现日期**：2026-04-18
- **复现步骤**：媒体库 → 打开单张图片
- **预期**：有"移入相册"按钮
- **实际**：无此功能
- **根因**：媒体详情弹窗缺少移入相册功能
- **修复方案**：
  1. index.html 添加"移入相册"按钮
  2. app.js 添加 `moveToAlbum()` 函数
  3. media.js 添加 `currentFileId` 属性
- **状态**：✅ 已修复（2026-04-18）
- **修复文件**：`/var/www/ai-nas/index.html`, `/var/www/ai-nas/js/app.js`, `/var/www/ai-nas/js/pages/media.js`

### BUG-011: 图片无法下载
- **优先级**：🟡 P1（功能缺失）
- **模块**：前端 Media 详情页
- **发现日期**：2026-04-18
- **复现步骤**：媒体库 → 打开单张图片 → 点击下载
- **预期**：下载图片文件
- **实际**：无下载功能或下载失败
- **根因**：前端 downloadCurrent() 只显示 toast，后端无下载路由
- **修复方案**：
  1. media.py 添加 `GET /{file_id}/download` 路由
  2. api.js 添加 `download()` 方法
  3. media.js 实现 `downloadCurrent()` 方法
- **状态**：✅ 已修复（2026-04-18）
- **修复文件**：`/root/ai-nas/backend/routes/media.py`, `/var/www/ai-nas/js/api.js`, `/var/www/ai-nas/js/pages/media.js`

### BUG-012: 相册打不开
- **优先级**：🔴 P0（阻断功能）
- **模块**：前端 Albums
- **发现日期**：2026-04-18
- **复现步骤**：进入相册模块 → 点击相册
- **预期**：打开相册，显示相册内照片
- **实际**：无法打开
- **根因**：`openAlbum()` 只显示 toast "功能开发中"，未实现实际功能
- **修复方案**：
  1. 实现 `openAlbum()` - 调用 API 获取相册详情和文件
  2. 实现 `showAlbumDetail()` - 动态创建相册详情视图
  3. 实现 `closeAlbum()` - 返回相册列表
  4. 实现 `deleteCurrentAlbum()` - 删除相册
- **状态**：✅ 已修复（2026-04-18）
- **修复文件**：`/var/www/ai-nas/js/pages/albums.js`

---

## 已修复

| # | 标题 | 修复日期 | 修复方式 |
|---|------|---------|---------|
| F001 | E1 表缺失（ai_tags/media_similar） | 2026-04-15 | db.py 补全表定义 |
| F002 | E3 VectorDB 参数缺失 | 2026-04-15 | VectorDB(db) |
| F003 | F4 face_count 类型错误 | 2026-04-15 | len(result.get('faces', [])) |
| F004 | G3 大文件 OOM | 2026-04-15 | chunk 流式写入 |
| F005 | 列名 ai_tags → tags | 2026-04-15 | 修正 SQL |
| F006 | urllib.loads → json.loads | 2026-04-15 | 修正 import |
| F007 | 全局异常返回 detail:"1" | 2026-04-16 | V7.0 exception_handler.py |

---

## BUG 模板

```markdown
### BUG-XXX: 标题
- **优先级**：🔴 P0 / 🟡 P1 / 🟢 P2
- **模块**：文件路径
- **发现日期**：YYYY-MM-DD
- **复现步骤**：
  1. 步骤1
  2. 步骤2
- **预期行为**：...
- **实际行为**：...
- **错误信息**：```
  完整错误堆栈
  ```
- **根因分析**：（可选）
- **修复方案**：（可选）
- **状态**：📋 待修复 / 🔄 修复中 / ✅ 已修复 / ⏸ 已知限制 / ❌ 无法修复
```

### 优先级定义

| 级别 | 标准 | 响应时间 |
|------|------|---------|
| 🔴 P0 | 阻断核心功能，无法绕过 | 立即 |
| 🟡 P1 | 功能异常但可绕过，或影响数据 | 当天 |
| 🟢 P2 | 体验问题，不影响核心流程 | 下个迭代 |
