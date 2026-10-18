"""
性能测试 - Locust 测试脚本
"""
from locust import HttpUser, task, between, events
import random
import json


class AI_NAS_User(HttpUser):
    """模拟用户行为"""
    
    wait_time = between(1, 5)  # 请求间隔 1-5 秒
    
    def on_start(self):
        """用户启动时登录"""
        self.login()
    
    def login(self):
        """登录获取token"""
        response = self.client.post("/api/auth/login", json={
            "username": "admin",
            "password": "admin123"
        })
        
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(10)
    def get_media_list(self):
        """获取媒体列表 - 高频操作"""
        params = {
            "skip": random.randint(0, 100),
            "limit": random.choice([20, 50, 100])
        }
        
        with self.client.get(
            "/api/media/",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    response.success()
                else:
                    response.failure("Invalid response format")
            elif response.status_code == 401:
                self.login()  # Token过期，重新登录
            else:
                response.failure(f"Status code: {response.status_code}")
    
    @task(5)
    def search_media(self):
        """搜索媒体 - 中频操作"""
        keywords = ["风景", "人物", "旅行", "家庭", "2024", "jpg"]
        keyword = random.choice(keywords)
        
        with self.client.get(
            f"/api/media/search/?keyword={keyword}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Search failed: {response.status_code}")
    
    @task(5)
    def get_albums(self):
        """获取相册列表"""
        with self.client.get(
            "/api/albums/",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get albums failed: {response.status_code}")
    
    @task(3)
    def get_media_detail(self):
        """获取媒体详情"""
        media_id = random.randint(1, 1000)
        
        with self.client.get(
            f"/api/media/{media_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                response.success()  # 媒体不存在也是正常情况
            else:
                response.failure(f"Get media detail failed: {response.status_code}")
    
    @task(2)
    def get_system_status(self):
        """获取系统状态"""
        with self.client.get(
            "/status",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Get status failed: {response.status_code}")
    
    @task(1)
    def scan_directory(self):
        """扫描目录 - 低频操作（重操作）"""
        paths = ["/test/pictures", "/test/photos", "/test/images"]
        
        with self.client.post(
            "/api/actions/scan",
            headers=self.headers,
            json={
                "path": random.choice(paths),
                "recursive": True
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Scan failed: {response.status_code}")
    
    @task(1)
    def classify_media(self):
        """AI分类 - 低频操作（重操作）"""
        with self.client.post(
            "/api/actions/classify",
            headers=self.headers,
            json={
                "file_id": None,
                "device_id": None,
                "force": False
            },
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Classify failed: {response.status_code}")


class AI_NAS_ReadOnly_User(HttpUser):
    """只读用户 - 模拟浏览行为"""
    
    wait_time = between(2, 8)
    
    def on_start(self):
        """匿名用户不需要登录"""
        self.headers = {}
    
    @task(10)
    def health_check(self):
        """健康检查"""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure("Unhealthy status")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(5)
    def get_frontend(self):
        """获取前端页面"""
        with self.client.get("/", catch_response=True) as response:
            if response.status_code == 200:
                if "AI-NAS" in response.text or "登录" in response.text:
                    response.success()
                else:
                    response.failure("Page content invalid")
            else:
                response.failure(f"Get frontend failed: {response.status_code}")


# 自定义事件监听
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, **kwargs):
    """记录慢请求"""
    if response_time > 1000:  # 超过1秒的请求
        print(f"⚠️  Slow request: {request_type} {name} took {response_time}ms")


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """测试结束时输出统计"""
    print("\n" + "="*50)
    print("性能测试完成")
    print("="*50)
    
    stats = environment.runner.stats
    
    print(f"总请求数: {stats.total.num_requests}")
    print(f"失败请求: {stats.total.num_failures}")
    print(f"平均响应时间: {stats.total.avg_response_time:.2f}ms")
    print(f"95%响应时间: {stats.total.get_response_time_percentile(0.95):.2f}ms")
    print(f"RPS: {stats.total.total_rps:.2f}")


# 运行命令:
# locust -f tests/performance/locustfile.py --host=http://localhost:8000
# 
# 参数说明:
# -u 100        # 100个并发用户
# -r 10         # 每秒启动10个用户
# -t 5m         # 运行5分钟
