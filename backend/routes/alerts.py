"""
告警路由
提供告警查询和管理接口
"""

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from services.alert_manager import alert_manager, AlertLevel, AlertType

router = APIRouter(prefix="/api/alerts", tags=["告警"])


class AlertResponse(BaseModel):
    level: str
    type: str
    title: str
    message: str
    device_id: Optional[str] = None
    task_id: Optional[str] = None
    created_at: str


class AlertListResponse(BaseModel):
    total: int
    alerts: list


@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    level: Optional[str] = Query(None, description="告警级别: info/warning/error/critical"),
    alert_type: Optional[str] = Query(None, description="告警类型: system/task/device/security/database"),
    limit: int = Query(50, ge=1, le=200, description="返回数量")
):
    """
    获取告警列表
    
    - **level**: 告警级别过滤
    - **type**: 告警类型过滤
    - **limit**: 返回数量（默认50）
    """
    level_enum = None
    type_enum = None
    
    if level:
        try:
            level_enum = AlertLevel(level)
        except ValueError:
            pass
    
    if alert_type:
        try:
            type_enum = AlertType(alert_type)
        except ValueError:
            pass
    
    alerts = alert_manager.get_alerts(
        level=level_enum,
        alert_type=type_enum,
        limit=limit
    )
    
    return AlertListResponse(total=len(alerts), alerts=alerts)


@router.get("/counts")
async def get_alert_counts():
    """获取各级别告警数量"""
    return alert_manager.get_unread_count()


@router.delete("/")
async def clear_alerts():
    """清空所有告警"""
    alert_manager.clear_alerts()
    return {"message": "Alerts cleared"}


@router.post("/test")
async def test_alert():
    """测试告警（发送一条测试告警）"""
    alert_manager.send_alert(
        level=AlertLevel.INFO,
        alert_type=AlertType.SYSTEM,
        title="测试告警",
        message="这是一条测试告警"
    )
    return {"message": "Test alert sent"}
