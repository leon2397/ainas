# AINAS 开发指南

> 版本：v1.0.0 | 更新日期：2026-10-18
> 本文由 V7 时代 `DEVELOPMENT_RULES.md` 迁移并持续维护，是当前开发规范。

---

# AI-NAS V7.0 开发规范

> 适用版本：V7.0.0+
> 最后更新：2026-04-17

---

## 🔴 最高级规则：模块化设计

**所有 AI-NAS 开发必须遵循模块化架构，这是不可妥协的最高原则。**

### 模块列表（8个）

| 优先级 | 模块 | 职责 |
|--------|------|------|
| P1 | mod_database | 数据库操作 + 迁移 |
| P1 | mod_auth | 认证 + 加密 |
| P1 | mod_ai | AI 引擎（CPU/BM1688/Face） |
| P1 | mod_media | 媒体扫描 + 格式处理 |
| P2 | mod_storage | 存储引擎（Local/SSH/SMB/NAS/Cloud） |
| P2 | mod_monitor | 系统监控 |
| P3 | mod_enterprise | 企业功能（租户/审计） |
| P3 | mod_plugins | 插件管理器 |

### 模块开发铁律

1. **新功能必须放入对应模块**，禁止在 routes/ services/ 直接添加代码
2. **模块间通过接口通信**，禁止直接访问其他模块内部实现
3. **每个模块必须有 README.md**，说明对外接口
4. **模块变更必须更新转发 shim**，保持向后兼容

### 模块导入规范

```python
# ✓ 正确：使用模块接口
from modules.mod_plugins import get_plugin_manager
from modules.mod_ai import AIEngine
from modules.mod_storage import FileStorage

# ✗ 错误：直接访问模块内部
from modules.mod_ai.cpu_engine import CPUEngine
from plugins.loader import get_plugin_loader  # 旧系统，已废弃
```

---

## 一、项目结构

```
AI-NAS-V7.0.0/
├── backend/                    # 后端（Python 3.12 + FastAPI）
│   ├── modules/                # 【核心】功能模块（P1-P3）
│   │   ├── mod_database/       # 数据库 + 迁移
│   │   ├── mod_auth/           # 认证 + 加密
│   │   ├── mod_ai/             # AI 引擎
│   │   ├── mod_media/          # 媒体扫描
│   │   ├── mod_storage/        # 存储引擎
│   │   ├── mod_monitor/        # 系统监控
│   │   ├── mod_enterprise/     # 企业功能
│   │   └── mod_plugins/        # 插件管理
│   ├── core/                   # 核心框架（非业务）
│   │   ├── logger.py           # 统一日志（loguru）
│   │   ├── exceptions.py       # 异常类体系
│   │   ├── exception_handler.py# 全局异常处理器
│   │   ├── config_manager.py   # YAML 配置管理器
│   │   ├── auth.py             # JWT 认证（转发到 mod_auth）
│   │   └── middleware.py       # 中间件
│   ├── database/               # 数据库层（转发到 mod_database）
│   ├── routes/                 # API 路由（薄层，调用 modules）
│   ├── services/               # 业务逻辑服务（逐步迁移到 modules）
│   ├── plugins/                # 【废弃】旧插件系统，过渡期保留
│   └── tests/                  # 测试
├── frontend/                   # 前端（React）
├── config/                     # YAML 配置文件
├── docs/                       # 项目文档（入口 docs/README.md）
│   ├── TROUBLESHOOTING.md      # 故障排查 + BUG 记录
│   ├── DEVELOPMENT.md          # 本文件
│   ├── adr/                    # 架构决策记录
│   └── archive/                # 历史归档
└── CHANGELOG.md                # 变更日志
```

---

## 二、配置管理

### 配置优先级

```
环境变量 > config/*.yaml > 代码默认值
```

### 规则

1. **敏感信息**（密钥、密码）→ `.env` 文件或环境变量，**绝不**写入 YAML
2. **运行时参数**（端口、路径）→ `config/*.yaml`
3. **代码常量**（默认值、魔法数字）→ 代码中定义，用大写命名

### 文件分工

| 文件 | 用途 | 谁改 |
|------|------|------|
| `config/global.yaml` | 全局设置（数据库、调试） | 开发者 |
| `config/web.yaml` | Web 服务（端口、CORS、认证） | 开发者 |
| `config/storage.yaml` | 存储路径、缩略图设置 | 部署者 |
| `config/ai_engine.yaml` | AI 模型配置 | 开发者 |
| `config/devices.yaml` | ARM 设备列表 | 部署者 |
| `config/cloud.yaml` | 云备份配置 | 用户自行配置 |
| `backend/.env` | 密钥、环境覆盖 | **不提交 Git** |

---

## 三、编码规范

### 日志

```python
from core.logger import logger, log_api_request, log_ai_operation

# ✓ 正确
logger.info("媒体扫描完成，共发现 {count} 个文件", count=result_count)
logger.debug("查询参数: params={}", params)
logger.error("数据库连接失败: {}", error, exc_info=True)  # 自动记录堆栈

# ✗ 错误
print("调试信息")           # 不要用 print
logger.info(f"发现了 {count} 个文件")  # 不要用 f-string，用 {} 占位符
```

### 异常

```python
from core.exceptions import AIEngineError, DatabaseError

# ✓ 正确：使用自定义异常
raise AIEngineError("模型文件不存在", model_path=path, model_name=name)

# ✓ 正确：捕获特定异常
try:
    result = await db.fetchall(sql, params)
except DatabaseError as e:
    logger.error("数据库查询失败: {}", e)
    raise

# ✗ 错误：裸 except + HTTPException(status_code=500, detail=str(e))
# 这就是 detail:"1" 的来源！
```

### 异步编程

```python
# ✓ 正确：使用 FastAPI Depends 注入
@router.post("/tags/generate")
async def generate_tags(
    file_ids: List[int] = Query(...),
    db: Database = Depends(get_db)
):
    ...

# ✗ 错误：手动调用 get_db()
async def generate_tags(...):
    db = await get_db()  # 缺少请求上下文！
    ...

# ✗ 错误：链式调用 aiosqlite
result = await db.execute(sql).fetchall()  # fetchall 在 coroutine 上调用！
```

### 模块导入（V7.0+ 强制）

```python
# ✓ 正确：使用模块化接口
from modules.mod_plugins import get_plugin_manager
from modules.mod_database import Database
from modules.mod_auth import AuthManager

manager = get_plugin_manager()
engine = manager.get_ai_engine('cpu', config)

# ✗ 错误：使用旧插件系统（已废弃）
from plugins.loader import get_plugin_loader  # 废弃！
from database.db import db  # 请使用 Depends(get_db)

# ✗ 错误：直接访问模块内部
from modules.mod_ai.cpu_engine import CPUEngine  # 使用 get_plugin_manager()
from modules.mod_storage.local_storage import LocalStorage  # 使用模块接口
```

### 数据库操作

```python
# ✓ 正确
row = await db.fetchone("SELECT * FROM media WHERE id = ?", (file_id,))
rows = await db.fetchall("SELECT * FROM media WHERE type = ?", ("image",))

# ✗ 错误：字符串拼接 SQL（SQL 注入风险）
rows = await db.fetchall(f"SELECT * FROM media WHERE type = '{type_name}'")
```

---

## 四、BUG 处理流程

> 这是**最高级规则**，所有开发必须遵守。

### 流程

```
发现 BUG
  │
  ├─ 阻断型 BUG（无法继续测试）→ 立即修复
  │
  └─ 非阻断型 BUG → 记录到 docs/TROUBLESHOOTING.md → 继续测试
                                      │
                                      ▼
                               测试完成后
                                      │
                                      ▼
                              按优先级批量修复
```

### 记录要求

每条 BUG 必须包含：
1. **复现步骤**（能让别人重现）
2. **预期 vs 实际**（不要只说"坏了"）
3. **错误信息**（完整堆栈，不要省略）
4. **优先级**（P0/P1/P2）

### 修复要求

1. **先理解根因**，不要只改表面
2. **修复后验证**，确认没有回归
3. **更新 docs/TROUBLESHOOTING.md 状态**，从「待修复」改为「已修复」
4. **写 CHANGELOG**，记录修复内容

---

## 五、卡点止损规则

> 当一个问题超过 **2 小时**仍无法解决时：

1. **停止**当前尝试
2. **独立验证**：创建最小复现脚本，隔离问题
3. **记录跳步**：将问题和当前进度写入 docs/TROUBLESHOOTING.md，标记状态
4. **切换任务**：做其他能推进的事
5. **寻求帮助**：如果独立验证也失败，向 leon 报告

---

## 六、Git 规范

### 分支

```
main          ← 稳定发布分支
develop       ← 开发分支
feature/XXX   ← 功能分支
fix/XXX       ← 修复分支
```

### 提交格式

```
<type>(<scope>): <描述>

type: feat / fix / docs / refactor / test / chore
scope: core / routes/ai / database / config / plugins

示例：
feat(core): 引入 loguru 日志系统
fix(routes/ai): 修复 tags/generate Depends 注入
docs(readme): 更新部署文档
```

---

## 七、测试规范

### 运行测试

```bash
cd backend
pytest tests/ -v                    # 运行所有测试
pytest tests/unit/ -v               # 仅单元测试
pytest tests/integration/ -v        # 仅集成测试
pytest --cov=. --cov-report=html    # 覆盖率报告
```

### 编写测试

```python
import pytest
from httpx import AsyncClient
from main import app

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
```

---

## 八、部署检查清单

部署前确认：

- [ ] `.env` 已配置（JWT_SECRET 已设置）
- [ ] `config/storage.yaml` 路径正确
- [ ] 日志目录有写权限
- [ ] 数据库文件路径可访问
- [ ] CORS 域名已配置
- [ ] `pytest tests/` 全部通过
- [ ] CHANGELOG.md 已更新
