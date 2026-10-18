# AI-NAS V7.0.0 测试体系

## 测试架构

```
backend/tests/
├── __init__.py
├── conftest.py              # 全局 fixtures
├── run_tests.py             # 测试运行脚本
├── README.md                # 本文件
├── unit/                    # 单元测试 (Phase 3.2)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py         # 认证模块 (~20 测试)
│   ├── test_database.py     # 数据库模块 (~22 测试)
│   └── test_scanner.py      # 扫描模块 (~13 测试)
├── integration/             # 集成测试 (Phase 3.3)
│   ├── __init__.py
│   ├── conftest.py
│   └── test_api_integration.py  # API 集成 (~14 测试)
└── e2e/                     # E2E 测试 (Phase 3.4)
    ├── __init__.py
    ├── conftest.py
    ├── test_e2e_workflows.py      # 工作流测试 (~12 测试)
    └── test_e2e_performance.py    # 性能测试 (~4 测试)
```

## 测试统计

| 类型 | 文件数 | 测试数 | 状态 |
|------|--------|--------|------|
| 单元测试 | 3 | ~55 | ✅ 完成 |
| 集成测试 | 1 | ~14 | ✅ 完成 |
| E2E 测试 | 2 | ~16 | ✅ 完成 |
| **合计** | **6** | **~85** | |

## 快速开始

### 运行所有测试
```bash
cd backend
python tests/run_tests.py
# 或
python -m pytest tests/ -v
```

### 运行特定类型测试
```bash
# 单元测试
python tests/run_tests.py unit

# 集成测试
python tests/run_tests.py integration

# E2E 测试
python tests/run_tests.py e2e
```

### 生成覆盖率报告
```bash
python tests/run_tests.py --cov
# 报告位置: htmlcov/index.html
```

### 排除慢速测试
```bash
python tests/run_tests.py --markers="not slow"
```

## 测试详情

### 单元测试 (test/unit/)

**test_auth.py**
- AuthManager 初始化
- 密码哈希验证
- JWT token 创建和验证
- 用户认证流程

**test_database.py**
- Database 类初始化
- CRUD 操作
- 事务处理
- 连接管理

**test_scanner.py**
- 目录扫描
- 文件类型检测
- EXIF 提取
- 哈希计算

### 集成测试 (test/integration/)

**test_api_integration.py**
- 健康检查端点
- 认证端点 (login/me)
- 媒体端点 (list/upload/search)
- AI 端点 (status/tags)
- 相册端点
- 任务端点
- 监控端点

### E2E 测试 (test/e2e/)

**test_e2e_workflows.py**
- 用户登录工作流
- 媒体上传 → AI 分析 → 查看结果
- 创建相册 → 添加图片 → 分享
- 扫描目录 → 分类 → 生成报告
- 搜索和过滤
- 错误处理

**test_e2e_performance.py**
- 并发操作 (10并发列表查询)
- 大数据集分页
- 内存稳定性 (50次重复操作)
- 快速健康检查 (20次/2秒)

## 环境要求

- Python 3.8+
- pytest
- pytest-asyncio
- pytest-cov (可选，用于覆盖率)

```bash
pip install pytest pytest-asyncio pytest-cov
```

## 配置

测试使用内存数据库 (`:memory:`) 和临时目录，不会影响生产数据。

环境变量：
```bash
export AI_NAS_ENV=test
export AI_NAS_DB_PATH=:memory:
```

## CI/CD 集成

```yaml
# .github/workflows/test.yml 示例
- name: Run tests
  run: |
    cd backend
    python tests/run_tests.py --cov
    
- name: Upload coverage
  uses: codecov/codecov-action@v3
```

## 覆盖率目标

- 当前：~30%
- 目标：60%
- 差距：需要补充边界条件测试和异常处理测试

## 已知问题

1. **test_database.py 部分失败**：方法名与实际 db.py 不匹配
   - 解决：跳过或修复方法名映射

2. **E2E 测试依赖**：需要 FastAPI TestClient
   - 解决：已添加条件跳过逻辑

## 扩展测试

添加新测试：

```python
# tests/unit/test_new_module.py
import pytest

class TestNewModule:
    def test_feature_a(self):
        assert True
    
    def test_feature_b(self):
        assert True
```

运行：
```bash
python -m pytest tests/unit/test_new_module.py -v
```
