"""
System Monitor Service
Monitors system health and provides metrics
"""

import os
import time
import psutil
from typing import Dict, Optional
from datetime import datetime, timedelta
import asyncio


class SystemMonitor:
    """
    System health monitoring service
    """
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = 5  # seconds
    
    def get_system_info(self) -> Dict:
        """Get basic system information"""
        return {
            'platform': os.name,
            'platform_detail': os.uname().sysname if hasattr(os, 'uname') else 'Windows',
            'hostname': os.uname().node if hasattr(os, 'uname') else os.environ.get('COMPUTERNAME', 'unknown'),
            'python_version': os.environ.get('PYTHON_VERSION', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_cpu_info(self) -> Dict:
        """Get CPU information and usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Per-core usage
            per_core = psutil.cpu_percent(interval=0.1, percpu=True)
            
            return {
                'usage': cpu_percent,
                'count': cpu_count,
                'frequency_current': cpu_freq.current if cpu_freq else 0,
                'frequency_max': cpu_freq.max if cpu_freq else 0,
                'per_core': per_core
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_memory_info(self) -> Dict:
        """Get memory information"""
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            return {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'percent': mem.percent,
                'swap_total': swap.total,
                'swap_used': swap.used,
                'swap_percent': swap.percent,
                'total_formatted': self._format_bytes(mem.total),
                'available_formatted': self._format_bytes(mem.available),
                'used_formatted': self._format_bytes(mem.used)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_disk_info(self, path: str = None) -> Dict:
        """Get disk information"""
        try:
            if path is None:
                path = os.path.abspath('.')
            
            disk = psutil.disk_usage(path)
            
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent,
                'path': path,
                'total_formatted': self._format_bytes(disk.total),
                'free_formatted': self._format_bytes(disk.free)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_network_info(self) -> Dict:
        """Get network information"""
        try:
            net_io = psutil.net_io_counters()
            
            # Per-interface info
            interfaces = {}
            for iface, addrs in psutil.net_if_addrs().items():
                interfaces[iface] = {
                    'addresses': [
                        {
                            'family': str(addr.family),
                            'address': addr.address,
                            'netmask': getattr(addr, 'netmask', None)
                        }
                        for addr in addrs
                    ]
                }
            
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'interfaces': interfaces,
                'sent_formatted': self._format_bytes(net_io.bytes_sent),
                'recv_formatted': self._format_bytes(net_io.bytes_recv)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_process_info(self) -> Dict:
        """Get current process information"""
        try:
            process = psutil.Process()
            
            with process.oneshot():
                mem_info = process.memory_info()
                cpu_times = process.cpu_times()
                
                return {
                    'pid': process.pid,
                    'name': process.name(),
                    'status': process.status(),
                    'cpu_percent': process.cpu_percent(interval=0.1),
                    'memory_rss': mem_info.rss,
                    'memory_vms': mem_info.vms,
                    'memory_percent': process.memory_percent(),
                    'cpu_user': cpu_times.user,
                    'cpu_system': cpu_times.system,
                    'num_threads': process.num_threads(),
                    'create_time': datetime.fromtimestamp(process.create_time()).isoformat(),
                    'rss_formatted': self._format_bytes(mem_info.rss)
                }
        except Exception as e:
            return {'error': str(e)}
    
    def get_full_status(self, use_cache: bool = True) -> Dict:
        """Get complete system status"""
        # Check cache
        if use_cache and self._cache.get('full_status'):
            cached = self._cache['full_status']
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached
        
        status = {
            'system': self.get_system_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'process': self.get_process_info(),
            'collected_at': datetime.now().isoformat()
        }
        
        # Update cache
        self._cache['full_status'] = {
            **status,
            'timestamp': time.time()
        }
        
        return status
    
    def get_alerts(self) -> list:
        """Get system alerts based on thresholds"""
        alerts = []
        
        # CPU alert
        cpu = self.get_cpu_info()
        if 'usage' in cpu and cpu['usage'] > 90:
            alerts.append({
                'type': 'cpu',
                'level': 'warning' if cpu['usage'] < 95 else 'critical',
                'message': f"CPU使用率过高: {cpu['usage']}%"
            })
        
        # Memory alert
        mem = self.get_memory_info()
        if 'percent' in mem and mem['percent'] > 90:
            alerts.append({
                'type': 'memory',
                'level': 'warning' if mem['percent'] < 95 else 'critical',
                'message': f"内存使用率过高: {mem['percent']}%"
            })
        
        # Disk alert
        disk = self.get_disk_info()
        if 'percent' in disk and disk['percent'] > 90:
            alerts.append({
                'type': 'disk',
                'level': 'warning' if disk['percent'] < 95 else 'critical',
                'message': f"磁盘使用率过高: {disk['percent']}%"
            })
        
        return alerts
    
    def _format_bytes(self, size: int) -> str:
        """Format bytes to human readable"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} PB"
    
    async def monitor_loop(self, interval: int = 60, callback=None):
        """Run monitoring loop"""
        while True:
            status = self.get_full_status(use_cache=False)
            
            # Check for alerts
            alerts = self.get_alerts()
            if alerts:
                status['alerts'] = alerts
            
            if callback:
                await callback(status)
            
            await asyncio.sleep(interval)


# Global monitor instance
system_monitor = SystemMonitor()


def get_monitor() -> SystemMonitor:
    """Get monitor instance"""
    return system_monitor
