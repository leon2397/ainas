"""
test_api.py - AI-NAS API 回归测试套件
=======================================
覆盖范围：
  1. 文档端点（/docs, /openapi.json）
  2. OpenAPI Schema 有效性
  3. 认证流程（登录/登出）
  4. 媒体扫描（POST /api/actions/scan）
  5. 迁移脚本全链路（--plan / --version / --history）
  6. 核心 API 冒烟测试

运行：
  cd backend
  pytest tests/test_api.py -v
"""

import pytest
import httpx
import subprocess
import sys
import os
import hashlib
import secrets
import tempfile
from pathlib import Path
from httpx import ASGITransport

# ═══════════════════════════════════════════════════════════════════════════
# 关键设计：环境变量必须在 import main 之前设置
# 因为 database/db.py 的全局单例在模块导入时就读取了 DATABASE_PATH
# ═══════════════════════════════════════════════════════════════════════════

# 临时测试数据库文件
_TEST_DB_TMP = None


def _init_test_env():
    global _TEST_DB_TMP
    if _TEST_DB_TMP is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        _TEST_DB_TMP = tmp.name
        tmp.close()
    os.environ["AI_NAS_DB_PATH"] = _TEST_DB_TMP
    os.environ.setdefault("AI_NAS_REDIS_URL", "")


_init_test_env()

# 现在可以安全 import app
from main import app
from database.db import db as app_db
from core.auth import auth_manager

# ═══════════════════════════════════════════════════════════════════════════
# 初始化测试数据库（在 pytest 会话开始时执行一次）
# ═══════════════════════════════════════════════════════════════════════════

async def _setup_test_db():
    """会话开始前：初始化 DB 并创建已知密码的测试用户"""
    await app_db.init()
    auth_manager.set_db(app_db)
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac(
        "sha256", "TestAdmin123!".encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()
    await app_db.execute(
        "INSERT OR IGNORE INTO users (username, hashed_password, salt, role) VALUES (?, ?, ?, ?)",
        ("test_admin", hashed, salt, "admin"),
    )
    await app_db.execute(
        "INSERT OR IGNORE INTO users (username, hashed_password, salt, role) VALUES (?, ?, ?, ?)",
        ("test_viewer", secrets.token_hex(16), secrets.token_hex(16), "viewer"),
    )
    await app_db._conn.commit()


# ═══════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
async def setup_session():
    """自动执行：整个测试会话只运行一次"""
    await _setup_test_db()
    yield
    # cleanup
    try:
        await app_db.close()
    except Exception:
        pass
    global _TEST_DB_TMP
    if _TEST_DB_TMP:
        try:
            os.unlink(_TEST_DB_TMP)
        except Exception:
            pass


@pytest.fixture(scope="module")
async def async_client():
    """HTTP ASGI 测试客户端（自动 follow redirects）"""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        yield client


@pytest.fixture
async def auth_token(async_client: httpx.AsyncClient) -> str:
    """通过 HTTP 登录获取 test_admin JWT token（每个测试独立获取）"""
    resp = await async_client.post(
        "/api/auth/login",
        data={"username": "test_admin", "password": "TestAdmin123!"},
    )
    assert resp.status_code == 200, \
        f"Login failed: {resp.status_code} {resp.text}\n" \
        f"DB path: {os.environ.get('AI_NAS_DB_PATH')}"
    return resp.json()["access_token"]


@pytest.fixture
def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


# ═══════════════════════════════════════════════════════════════════════════
# 测试组 1：文档 & OpenAPI Schema
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestDocEndpoints:
    """文档端点：确保 Swagger UI 和 OpenAPI Schema 正常"""

    async def test_docs_returns_200(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/docs")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    async def test_docs_contains_openapi(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/docs")
        assert "openapi" in r.text.lower()

    async def test_openapi_json_returns_200(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/openapi.json")
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"

    async def test_openapi_json_is_valid_schema(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/openapi.json")
        schema = r.json()
        assert "openapi" in schema, "Missing 'openapi' version key"
        assert "paths" in schema, "Missing 'paths' key"
        assert schema["openapi"].startswith("3."), f"Expected OpenAPI 3.x, got {schema['openapi']}"

    async def test_openapi_has_paths(self, async_client: httpx.AsyncClient):
        schema = (await async_client.get("/openapi.json")).json()
        assert len(schema["paths"]) > 0, "No paths found in OpenAPI schema"

    async def test_openapi_paths_have_responses(self, async_client: httpx.AsyncClient):
        schema = (await async_client.get("/openapi.json")).json()
        for path, methods in schema["paths"].items():
            for method, details in methods.items():
                if method in ("get", "post", "put", "delete", "patch"):
                    assert "responses" in details, \
                        f"Path '{path}' method '{method}' missing 'responses'"

    async def test_root_returns_200(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 测试组 2：认证流程
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestAuthFlow:
    """认证：登录 → 访问受保护资源 → 登出"""

    async def test_login_valid_credentials(self, async_client: httpx.AsyncClient):
        r = await async_client.post(
            "/api/auth/login",
            data={"username": "test_admin", "password": "TestAdmin123!"},
        )
        assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
        data = r.json()
        assert "access_token" in data, f"No access_token in: {data}"
        assert data["token_type"] == "bearer"

    async def test_login_invalid_password(self, async_client: httpx.AsyncClient):
        r = await async_client.post(
            "/api/auth/login",
            data={"username": "test_admin", "password": "WrongPassword!"},
        )
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    async def test_login_nonexistent_user(self, async_client: httpx.AsyncClient):
        r = await async_client.post(
            "/api/auth/login",
            data={"username": "nonexistent_xyz_123", "password": "Any"},
        )
        assert r.status_code in (401, 404), f"Expected 401/404, got {r.status_code}"

    async def test_protected_endpoint_without_token(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/api/auth/me")
        assert r.status_code == 401, f"Expected 401, got {r.status_code}"

    async def test_protected_endpoint_with_token(
        self, async_client: httpx.AsyncClient, auth_headers: dict
    ):
        r = await async_client.get("/api/auth/me", headers=auth_headers)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        assert "username" in r.json()

    async def test_logout(self, async_client: httpx.AsyncClient, auth_headers: dict):
        r = await async_client.post("/api/auth/logout", headers=auth_headers)
        assert r.status_code in (200, 204), f"Logout failed: {r.status_code}"


# ═══════════════════════════════════════════════════════════════════════════
# 测试组 3：媒体扫描
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestMediaScan:
    """媒体扫描：POST /api/actions/scan（无需认证）"""

    async def test_scan_sync_basic(self, async_client: httpx.AsyncClient, auth_headers: dict):
        """同步扫描：扫描不存在的路径返回 200（正常业务情况）"""
        r = await async_client.post(
            "/api/actions/scan/sync",
            headers=auth_headers,
            json={"path": "Z:/this/path/does/not/exist/12345", "recursive": True},
        )
        assert r.status_code == 200, f"Scan sync failed: {r.status_code} {r.text}"
        data = r.json()
        assert "status" in data or "result" in data

    async def test_scan_async_returns_task_id(self, async_client: httpx.AsyncClient, auth_headers: dict):
        """异步扫描：应返回 task_id，status 为 started"""
        r = await async_client.post(
            "/api/actions/scan",
            headers=auth_headers,
            json={"path": "Z:/non/existent", "recursive": True},
        )
        assert r.status_code == 200, f"Scan start failed: {r.status_code} {r.text}"
        data = r.json()
        assert "task_id" in data, f"No task_id in response: {data}"
        assert data["status"] == "started"


# ═══════════════════════════════════════════════════════════════════════════
# 测试组 4：迁移脚本
# ═══════════════════════════════════════════════════════════════════════════

class TestMigrations:
    """迁移脚本全链路（同步子进程，无须 async）"""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        backend_root = Path(__file__).parent.parent
        return subprocess.run(
            [sys.executable, str(backend_root / "migrations" / "run.py"), *args],
            capture_output=True,
            text=True,
            cwd=str(backend_root),
        )

    def test_migration_version(self):
        r = self._run("--version")
        assert r.returncode == 0, f"--version failed: {r.stderr}"
        assert any(k in r.stdout.lower() for k in ["version", "v0", "v1"])

    def test_migration_plan(self):
        r = self._run("--plan")
        assert r.returncode == 0, f"--plan failed: {r.stderr}"

    def test_migration_history(self):
        r = self._run("--history")
        assert r.returncode == 0, f"--history failed: {r.stderr}"

    def test_migration_help(self):
        r = self._run("--help")
        assert r.returncode == 0, f"--help failed: {r.stderr}"

    def test_migration_idempotent(self):
        """幂等性：迁移执行两次不应报错"""
        r1 = self._run()
        r2 = self._run()
        assert r1.returncode == 0, f"First run failed: {r1.stderr}"
        assert r2.returncode == 0, f"Second run failed: {r2.stderr}"


# ═══════════════════════════════════════════════════════════════════════════
# 测试组 5：核心 API 冒烟测试
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestCoreAPISmoke:
    """核心 API 冒烟测试：确保路由注册正确"""

    async def test_albums_list(self, async_client: httpx.AsyncClient, auth_headers: dict):
        r = await async_client.get("/api/albums", headers=auth_headers)
        assert r.status_code == 200, f"/api/albums failed: {r.status_code}"

    async def test_devices_list(self, async_client: httpx.AsyncClient, auth_headers: dict):
        r = await async_client.get("/api/devices", headers=auth_headers)
        assert r.status_code == 200

    async def test_media_list(self, async_client: httpx.AsyncClient, auth_headers: dict):
        r = await async_client.get("/api/media", headers=auth_headers)
        assert r.status_code == 200

    async def test_ai_status(self, async_client: httpx.AsyncClient, auth_headers: dict):
        r = await async_client.get("/api/ai/status", headers=auth_headers)
        assert r.status_code == 200, f"/api/ai/status failed: {r.status_code} {r.text}"
        data = r.json()
        assert "engine_mode" in data, f"Missing engine_mode in ai/status: {data}"

    async def test_health(self, async_client: httpx.AsyncClient):
        r = await async_client.get("/api/health")
        assert r.status_code in (200, 404, 401)
