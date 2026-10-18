"""
设备负载监控模块
实时监控设备CPU/NPU/内存状态
"""

import psutil
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class DeviceLoad:
    """设备负载信息"""
    device_id: str
    device_name: str
    cpu_percent: float
    memory_percent: float
    memory_available: float  # GB
    disk_percent: float
    npu_percent: Optional[float] = None
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DeviceMonitor:
    """设备负载监控器"""
    
    def __init__(self, history_minutes: int = 60):
        self.history_minutes = history_minutes
        self.history: Dict[str, List[DeviceLoad]] = {}
        self._local_load = None
    
    def get_local_load(self) -> DeviceLoad:
        """获取本地设备负载"""
        cpu = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        load = DeviceLoad(
            device_id="local",
            device_name="Local Server",
            cpu_percent=cpu,
            memory_percent=memory.percent,
            memory_available=round(memory.available / (1024**3), 2),
            disk_percent=disk.percent
        )
        
        self._local_load = load
        return load
    
    def record_load(self, load: DeviceLoad):
        """记录负载到历史"""
        if load.device_id not in self.history:
            self.history[load.device_id] = []
        
        self.history[load.device_id].append(load)
        
        # 清理旧记录
        cutoff = datetime.now() - timedelta(minutes=self.history_minutes)
        self.history[load.device_id] = [
            l for l in self.history[load.device_id]
            if datetime.fromisoformat(l.timestamp) > cutoff
        ]
    
    def get_history(self, device_id: str, minutes: int = None) -> List[Dict]:
        """获取负载历史"""
        if minutes is None:
            minutes = self.history_minutes
        
        if device_id not in self.history:
            return []
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        records = [
            l for l in self.history[device_id]
            if datetime.fromisoformat(l.timestamp) > cutoff
        ]
        
        return [asdict(r) for r in records]
    
    def get_average_load(self, device_id: str, minutes: int = 5) -> Dict:
        """获取平均负载"""
        history = self.get_history(device_id, minutes)
        
        if not history:
            return {
                "cpu_avg": 0,
                "memory_avg": 0,
                "disk_avg": 0,
                "samples": 0
            }
        
        cpu_avg = sum(h["cpu_percent"] for h in history) / len(history)
        memory_avg = sum(h["memory_percent"] for h in history) / len(history)
        disk_avg = sum(h["disk_percent"] for h in history) / len(history)
        
        return {
            "cpu_avg": round(cpu_avg, 1),
            "memory_avg": round(memory_avg, 1),
            "disk_avg": round(disk_avg, 1),
            "samples": len(history)
        }
    
    def check_thresholds(self, device_id: str) -> List[Dict]:
        """检查阈值，返回告警"""
        warnings = []
        
        if device_id in self.history and self.history[device_id]:
            latest = self.history[device_id][-1]
            
            if latest.cpu_percent > 90:
                warnings.append({
                    "level": "critical",
                    "type": "cpu_high",
                    "message": f"CPU使用率过高: {latest.cpu_percent}%",
                    "value": latest.cpu_percent
                })
            elif latest.cpu_percent > 75:
                warnings.append({
                    "level": "warning",
                    "type": "cpu_high",
                    "message": f"CPU使用率较高: {latest.cpu_percent}%",
                    "value": latest.cpu_percent
                })
            
            if latest.memory_percent > 90:
                warnings.append({
                    "level": "critical",
                    "type": "memory_high",
                    "message": f"内存使用率过高: {latest.memory_percent}%",
                    "value": latest.memory_percent
                })
            elif latest.memory_percent > 80:
                warnings.append({
                    "level": "warning",
                    "type": "memory_high",
                    "message": f"内存使用率较高: {latest.memory_percent}%",
                    "value": latest.memory_percent
                })
            
            if latest.disk_percent > 95:
                warnings.append({
                    "level": "critical",
                    "type": "disk_high",
                    "message": f"磁盘空间不足: {latest.disk_percent}%",
                    "value": latest.disk_percent
                })
            elif latest.disk_percent > 85:
                warnings.append({
                    "level": "warning",
                    "type": "disk_high",
                    "message": f"磁盘使用率较高: {latest.disk_percent}%",
                    "value": latest.disk_percent
                })
        
        return warnings


# 全局监控器
device_monitor = DeviceMonitor(history_minutes=60)
