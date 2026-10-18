from loguru import logger
"""
Audit Analytics Module
V6.0 Phase 4: 企业增强 - 审计日志分析
提供可视化的审计日志分析和报表
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import statistics

logger = logger.bind(name="ai_nas.enterprise.audit_analytics")

try:
    from enterprise.multitenant import get_tenant_context
    MULTITENANT_AVAILABLE = True
except ImportError:
    MULTITENANT_AVAILABLE = False


class AuditCategory(Enum):
    """审计类别"""
    AUTH = "AUTH"
    USER = "USER"
    MEDIA = "MEDIA"
    ALBUM = "ALBUM"
    DEVICE = "DEVICE"
    SYSTEM = "SYSTEM"
    CONFIG = "CONFIG"
    SECURITY = "SECURITY"
    ADMIN = "ADMIN"
    PLUGIN = "PLUGIN"


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class AuditSummary:
    """审计摘要"""
    total_events: int = 0
    events_by_level: Dict[str, int] = field(default_factory=dict)
    events_by_category: Dict[str, int] = field(default_factory=dict)
    events_by_user: Dict[str, int] = field(default_factory=dict)
    top_users: List[Dict] = field(default_factory=list)
    top_actions: List[Dict] = field(default_factory=list)
    error_rate: float = 0.0
    security_alerts: int = 0


@dataclass
class AuditTrend:
    """审计趋势"""
    date: str
    total: int
    by_level: Dict[str, int]
    by_category: Dict[str, int]


@dataclass
class SecurityAlert:
    """安全告警"""
    id: str
    type: str
    severity: str
    description: str
    user: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    details: Dict


class AuditAnalytics:
    """审计日志分析引擎"""
    
    def __init__(self, db_path: str = "data/audit/audit.db"):
        self.db_path = db_path
        self._alerts: List[SecurityAlert] = []
    
    def get_summary(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: Optional[str] = None
    ) -> AuditSummary:
        """获取审计摘要"""
        # 从数据库读取审计日志
        logs = self._query_logs(start_date, end_date, tenant_id)
        
        summary = AuditSummary()
        summary.total_events = len(logs)
        
        # 按级别统计
        for log in logs:
            level = log.get("level", "INFO")
            summary.events_by_level[level] = summary.events_by_level.get(level, 0) + 1
            
            # 按类别统计
            category = log.get("category", "SYSTEM")
            summary.events_by_category[category] = summary.events_by_category.get(category, 0) + 1
            
            # 按用户统计
            user = log.get("username", "system")
            summary.events_by_user[user] = summary.events_by_user.get(user, 0) + 1
            
            # 安全告警
            if level in ["ERROR", "CRITICAL"] or category == "SECURITY":
                summary.security_alerts += 1
        
        # 计算错误率
        if summary.total_events > 0:
            error_count = summary.events_by_level.get("ERROR", 0) + summary.events_by_level.get("CRITICAL", 0)
            summary.error_rate = error_count / summary.total_events
        
        # Top 用户
        top_users = sorted(
            [{"user": k, "count": v} for k, v in summary.events_by_user.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        summary.top_users = top_users
        
        # Top 操作
        actions = defaultdict(int)
        for log in logs:
            action = log.get("action", "unknown")
            actions[action] += 1
        
        top_actions = sorted(
            [{"action": k, "count": v} for k, v in actions.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        summary.top_actions = top_actions
        
        return summary
    
    def get_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "day",
        tenant_id: Optional[str] = None
    ) -> List[AuditTrend]:
        """获取审计趋势"""
        logs = self._query_logs(start_date, end_date, tenant_id)
        
        trends = []
        current = start_date
        
        while current <= end_date:
            if granularity == "day":
                next_period = current + timedelta(days=1)
            else:
                next_period = current + timedelta(hours=1)
            
            # 过滤当前时段的数据
            period_logs = [
                log for log in logs
                if current <= datetime.fromisoformat(log.get("timestamp", current.isoformat())) < next_period
            ]
            
            trend = AuditTrend(
                date=current.strftime("%Y-%m-%d" if granularity == "day" else "%Y-%m-%d %H:00"),
                total=len(period_logs),
                by_level={},
                by_category={}
            )
            
            for log in period_logs:
                level = log.get("level", "INFO")
                category = log.get("category", "SYSTEM")
                trend.by_level[level] = trend.by_level.get(level, 0) + 1
                trend.by_category[category] = trend.by_category.get(category, 0) + 1
            
            trends.append(trend)
            current = next_period
        
        return trends
    
    def get_user_activity(
        self,
        username: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """获取用户活动详情"""
        logs = self._query_logs(start_date, end_date)
        user_logs = [log for log in logs if log.get("username") == username]
        
        # 活动统计
        activity = {
            "total_actions": len(user_logs),
            "actions_by_level": defaultdict(int),
            "actions_by_category": defaultdict(int),
            "actions_by_day": defaultdict(int),
            "unique_ips": set(),
            "first_activity": None,
            "last_activity": None
        }
        
        for log in user_logs:
            activity["actions_by_level"][log.get("level", "INFO")] += 1
            activity["actions_by_category"][log.get("category", "SYSTEM")] += 1
            
            timestamp = datetime.fromisoformat(log.get("timestamp", datetime.utcnow().isoformat()))
            day = timestamp.strftime("%Y-%m-%d")
            activity["actions_by_day"][day] += 1
            
            if log.get("ip_address"):
                activity["unique_ips"].add(log["ip_address"])
            
            if not activity["first_activity"] or timestamp < activity["first_activity"]:
                activity["first_activity"] = timestamp
            
            if not activity["last_activity"] or timestamp > activity["last_activity"]:
                activity["last_activity"] = timestamp
        
        # 转换为列表
        activity["actions_by_level"] = dict(activity["actions_by_level"])
        activity["actions_by_category"] = dict(activity["actions_by_category"])
        activity["actions_by_day"] = dict(activity["actions_by_day"])
        activity["unique_ips"] = list(activity["unique_ips"])
        activity["first_activity"] = activity["first_activity"].isoformat() if activity["first_activity"] else None
        activity["last_activity"] = activity["last_activity"].isoformat() if activity["last_activity"] else None
        
        return activity
    
    def detect_anomalies(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: Optional[str] = None
    ) -> List[SecurityAlert]:
        """异常检测"""
        alerts = []
        logs = self._query_logs(start_date, end_date, tenant_id)
        
        # 检测暴力破解
        failed_logins = defaultdict(list)
        for log in logs:
            if log.get("category") == "AUTH" and log.get("level") in ["WARNING", "ERROR"]:
                failed_logins[log.get("username", "unknown")].append(log)
        
        for username, fail_logs in failed_logins.items():
            if len(fail_logs) >= 5:  # 5次失败尝试
                # 检查时间窗口
                timestamps = [datetime.fromisoformat(l.get("timestamp", datetime.utcnow().isoformat())) for l in fail_logs]
                time_span = (max(timestamps) - min(timestamps)).total_seconds() / 3600
                
                if time_span <= 1:  # 1小时内
                    alert = SecurityAlert(
                        id=f"brute_force_{username}_{len(alerts)}",
                        type="BRUTE_FORCE",
                        severity="HIGH",
                        description=f"检测到用户 {username} 在 {time_span:.1f} 小时内连续 {len(fail_logs)} 次登录失败",
                        user=username,
                        ip_address=fail_logs[0].get("ip_address"),
                        timestamp=datetime.utcnow(),
                        details={
                            "failed_attempts": len(fail_logs),
                            "time_window_hours": time_span,
                            "last_attempt": timestamps[-1].isoformat()
                        }
                    )
                    alerts.append(alert)
        
        # 检测异常 IP 访问
        ip_activity = defaultdict(set)
        for log in logs:
            if log.get("ip_address"):
                ip_activity[log["ip_address"]].add(log.get("username", "unknown"))
        
        for ip, users in ip_activity.items():
            if len(users) >= 3:  # 同一 IP 多个用户
                alert = SecurityAlert(
                    id=f"shared_ip_{ip}_{len(alerts)}",
                    type="SHARED_IP",
                    severity="MEDIUM",
                    description=f"IP {ip} 被 {len(users)} 个不同用户使用",
                    user=None,
                    ip_address=ip,
                    timestamp=datetime.utcnow(),
                    details={"users": list(users)}
                )
                alerts.append(alert)
        
        # 检测敏感操作
        sensitive_actions = ["DELETE", "ADMIN", "SYSTEM_CONFIG"]
        for log in logs:
            if log.get("category") in sensitive_actions:
                alert = SecurityAlert(
                    id=f"sensitive_{log.get('action', 'unknown')}_{len(alerts)}",
                    type="SENSITIVE_ACTION",
                    severity="LOW",
                    description=f"敏感操作: {log.get('action', 'unknown')}",
                    user=log.get("username"),
                    ip_address=log.get("ip_address"),
                    timestamp=datetime.fromisoformat(log.get("timestamp", datetime.utcnow().isoformat())),
                    details={"action": log.get("action"), "details": log.get("details")}
                )
                alerts.append(alert)
        
        self._alerts = alerts
        return alerts
    
    def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> Dict:
        """生成审计报表"""
        summary = self.get_summary(start_date, end_date)
        trends = self.get_trends(start_date, end_date)
        alerts = self.detect_anomalies(start_date, end_date)
        
        report = {
            "report_info": {
                "generated_at": datetime.utcnow().isoformat(),
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat()
                },
                "format": format
            },
            "summary": {
                "total_events": summary.total_events,
                "events_by_level": summary.events_by_level,
                "events_by_category": summary.events_by_category,
                "error_rate": summary.error_rate,
                "security_alerts": summary.security_alerts,
                "top_users": summary.top_users,
                "top_actions": summary.top_actions
            },
            "trends": [
                {
                    "date": t.date,
                    "total": t.total,
                    "by_level": t.by_level,
                    "by_category": t.by_category
                }
                for t in trends
            ],
            "alerts": [
                {
                    "id": a.id,
                    "type": a.type,
                    "severity": a.severity,
                    "description": a.description,
                    "user": a.user,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in alerts
            ]
        }
        
        if format == "csv":
            # 转换为 CSV 格式
            return {"format": "csv", "data": self._to_csv(report)}
        
        return report
    
    def _query_logs(
        self,
        start_date: datetime,
        end_date: datetime,
        tenant_id: Optional[str] = None
    ) -> List[Dict]:
        """查询审计日志"""
        # 尝试从数据库读取
        logs = []
        
        audit_db = "data/audit/audit.db"
        if os.path.exists(audit_db):
            try:
                import sqlite3
                conn = sqlite3.connect(audit_db)
                cursor = conn.cursor()
                
                query = """
                    SELECT timestamp, level, category, username, action, ip_address, details
                    FROM audit_logs
                    WHERE timestamp BETWEEN ? AND ?
                """
                params = [start_date.isoformat(), end_date.isoformat()]
                
                if tenant_id:
                    query += " AND tenant_id = ?"
                    params.append(tenant_id)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                for row in rows:
                    logs.append({
                        "timestamp": row[0],
                        "level": row[1],
                        "category": row[2],
                        "username": row[3],
                        "action": row[4],
                        "ip_address": row[5],
                        "details": row[6]
                    })
                
                conn.close()
            except Exception as e:
                logger.error(f"Failed to query audit logs: {e}")
        
        # 如果数据库为空，生成模拟数据用于演示
        if not logs:
            logs = self._generate_demo_logs(start_date, end_date)
        
        return logs
    
    def _generate_demo_logs(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """生成演示日志数据"""
        import random
        
        users = ["admin", "user1", "user2", "user3"]
        categories = ["AUTH", "MEDIA", "ALBUM", "USER", "SYSTEM"]
        levels = ["INFO", "INFO", "INFO", "WARNING", "ERROR"]
        actions = {
            "AUTH": ["login", "logout", "login_failed"],
            "MEDIA": ["upload", "delete", "view", "share"],
            "ALBUM": ["create", "delete", "update", "share"],
            "USER": ["create", "update", "delete"],
            "SYSTEM": ["config_change", "backup", "restore"]
        }
        
        logs = []
        current = start_date
        
        while current <= end_date:
            # 每天生成 20-50 条日志
            num_logs = random.randint(20, 50)
            
            for _ in range(num_logs):
                category = random.choice(categories)
                level = random.choice(levels)
                action = random.choice(actions[category])
                
                logs.append({
                    "timestamp": current.isoformat(),
                    "level": level,
                    "category": category,
                    "username": random.choice(users),
                    "action": action,
                    "ip_address": f"192.168.1.{random.randint(1, 254)}",
                    "details": "{}"
                })
            
            current += timedelta(days=1)
        
        return logs
    
    def _to_csv(self, report: Dict) -> str:
        """转换为 CSV 格式"""
        lines = ["Category,Count"]
        
        for category, count in report["summary"]["events_by_category"].items():
            lines.append(f"{category},{count}")
        
        return "\n".join(lines)


# 全局实例
audit_analytics = AuditAnalytics()


def get_audit_analytics() -> AuditAnalytics:
    """获取审计分析引擎"""
    return audit_analytics


# 补充 Enum
from enum import Enum
