# AI-NAS Media Manager - 测试体系

## 测试架构

```
tests/
├── unit/              # 单元测试 (pytest)
│   ├── conftest.py    # 共享fixture
│   ├── test_auth.py   # 认证模块测试
│   ├── test_media.py  # 媒体模块测试
│   └── test_services/ # 服务层测试
├── integration/       # 集成测试
│   ├── test_api_flow.py      # API流程测试
│   ├── test_websocket.py     # WebSocket测试
│   └── test_database.py      # 数据库测试
├── e2e/              # E2E测试 (Playwright)
│   ├── auth.spec.js  # 认证流程
│   ├── upload.spec.js # 上传流程
│   └── album.spec.js # 相册流程
└── performance/      # 性能测试 (Locust)
    └── locustfile.py
```

## 运行测试

```bash
# 单元测试
pytest tests/unit -v

# 集成测试
pytest tests/integration -v

# E2E测试
cd tests/e2e && npx playwright test

# 性能测试
locust -f tests/performance/locustfile.py

# 全部测试
pytest tests/ -v --cov=backend --cov-report=html
```

## 测试规范

1. **单元测试**: 每个函数/方法至少一个测试用例
2. **集成测试**: 每个API端点至少一个测试用例
3. **E2E测试**: 每个用户流程至少一个测试用例
4. **覆盖率目标**: 80%+
