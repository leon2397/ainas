# AI-NAS 更新日志

所有重要的更改都将记录在此文件中。

## [V7.0.0] - 开发中（预计 2026-04-30 发布）

### 当前状态

**已完成**：Phase 1-3（基础设施、核心模块、测试体系）
**进行中**：Phase 4（Docker 化）
**待开始**：Phase 5-6（文档完善、发布准备）

**总体进度**：50% (3/6 Phases)

### 未完成工作清单

详见 `docs/01_项目总览/TODO.md` 和 `V7.0_升级计划.md`

#### 🔴 P0 - 最高优先级（阻塞发布）
- [ ] Dockerfile 编写
- [ ] docker-compose.yml 编写
- [ ] ECS 代码同步与部署验证

#### 🟡 P1 - 高优先级（功能完整）
- [ ] nginx 容器配置（HTTPS/反向代理）
- [ ] 数据卷映射配置
- [ ] Docker 本地测试验证
- [ ] 架构文档更新
- [ ] Docker 部署指南

#### 🟢 P2 - 中优先级（体验优化）
- [ ] API 文档完善
- [ ] 用户手册更新
- [ ] 版本号统一
- [ ] 发布包打包
- [ ] 回归测试

---

## [V7.0.0-rc1] - 2026-04-17

### Phase 2: 核心模块优化

#### 2.7 全局代码规范扫描与修复（⏳ 进行中）
- **P1 修复完成**（入口 + 路由）：
  - `main.py`：2 处 bare `except:` → `except Exception as e:` + logger.debug
  - `routes/settings.py`：2 处 `print()` → logger.warning
  - `routes/websocket.py`：4 处 `print()` → logger.debug/warning
- **全局扫描结果**：47 文件，116 print / 8 bare except / 17 logging.getLogger
- **剩余**：P2-P7 共 44 文件待处理

#### 2.6 重构 `core/auth.py`（✅ 完成）
- 9 处 `print()` → `logger.info/warning/debug`
- 1 处 `except Exception:` → `except Exception as e:` + logger
- 添加 `from core.logger import logger`
- 移除 emoji 输出（GBK 兼容）
- 保持原有功能不变

#### 2.5 检查 `routes/media.py`（✅ 无需修改）
- 检查结果：print 0 / bare except 0 / logging.getLogger 0 / db 无 await 0
- subprocess.run 已带 timeout=10
- 大文件上传已用 chunk 流式写入
- **结论：代码规范，无需修改**

#### 2.4 重构 `plugins/ai/cpu_engine.py`（✅ 完成）
- 7 处 `print()` → `logger.info/warning/debug/error`
- 添加 `from core.logger import logger`
- 所有异常处理添加日志记录
- 保持原有功能不变（ONNX 推理 / heuristic 降级 / 人脸检测）

#### 2.3 优化 `services/scanner.py`（✅ 完成）
- **BUG 修复**：`modified_at` 列不存在 → 移除该字段（schema 中无此列）
- `logging.getLogger` → `from core.logger import logger`
- 所有 `except Exception` 添加日志记录
- 文件去重（rglob 大小写可能重复）
- 修复 GPS 解析错误处理（None 判断）
- PIL ImportError 处理
- 扫描结束时输出统计日志
- **await db 调用**：3 处全部带 await ✅

#### 2.2 重构 `database/db.py`（✅ 完成）
- 移除 `print`，全部改为 `logger.info/warning`
- 移除裸 `except:`，改用具体异常
- 移除 `last_insert_rowid()` 的嵌套 await 调用，改用 `insert_id()` 独立方法
- 新增 `fetchval()` 标量查询方法
- 新增 `insert_id()` 获取最后插入 ID（替代混乱的嵌套 cursor）
- 设置 `row_factory = aiosqlite.Row`（dict 转换更可靠）
- 添加缺失的方法 docstring
- **无新增依赖**：纯重构

#### 2.1 重构 `routes/ai.py`（✅ 完成）
- **BUG-001 修复**：`detail:"1"` 根因消除
- 全部 db 调用改为 `await db.fetchone/fetchall/execute`
- 所有端点添加 `db: Database = Depends(get_db)` 参数
- 替换裸 `HTTPException`，异常由全局处理器捕获
- 添加 loguru 日志（33 处 logger 调用）
- 移除所有 `print`

### 新增
- **统一日志系统** (`core/logger.py`) — loguru 彩色控制台 + 文件轮转
- **异常类体系** (`core/exceptions.py`) — 16 个异常类，结构化错误输出
- **全局异常处理器** (`core/exception_handler.py`) — 消除 `detail:"1"` 问题
- **项目文档**
  - `.env.example` — 环境变量配置模板与说明
  - `BUGS.md` — BUG 记录模板 + 4 个已知问题
  - `DEVELOPMENT_RULES.md` — 编码规范、BUG 处理流程、卡点止损规则
  - `docs/01_项目总览/V7.0_升级计划.md` — 6 周升级规划
  - `docs/01_项目总览/开发环境启动指南.md`

### 变更
- 项目版本 V6.0.3 → V7.0.0，目录迁移到 `D:\project\NAS\AI-NAS-V7.0.0`
- `main.py` — 使用 loguru + 全局异常处理器
- `core/config_manager.py` — print 改为 loguru logger
- `requirements.txt` — 添加 `loguru==0.7.2`

### 计划改进（V7.0 目标）
- **日志系统**：引入 loguru，统一日志格式
- **异常处理**：定义异常类，消除 `detail:"1"` 错误
- **数据库接口**：统一 `fetchone`/`fetchall` 异步接口
- **测试覆盖**：单元测试覆盖率 > 60%
- **Docker 化**：统一本地和远程部署环境

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
- 错误信息不明确，调试困难

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

---

[格式基于 Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)
