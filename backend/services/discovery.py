"""
Device Auto-Discovery Service
UDP broadcast-based device discovery for LAN
"""

import asyncio
import json
import socket
from loguru import logger
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
import struct

# 模块日志器
logger = logger.bind(name="ai_nas.discovery")


@dataclass
class DeviceInfo:
    """Discovered device information"""
    device_id: str
    device_name: str
    ip_address: str
    port: int
    npu_type: str
    mac_address: str
    version: str
    last_seen: datetime
    status: str = "online"


class DeviceDiscovery:
    """
    Device auto-discovery using UDP broadcast
    
    ARM devices broadcast their presence on startup
    Windows server listens for broadcasts and registers devices
    """
    
    # Broadcast settings
    BROADCAST_PORT = 45678
    BROADCAST_INTERVAL = 30  # seconds
    BROADCAST_MESSAGE = json.dumps({
        "type": "device_announce",
        "version": "1.0"
    }).encode('utf-8')
    
    def __init__(self, server_port: int = 8000):
        self.server_port = server_port
        self.discovered_devices: Dict[str, DeviceInfo] = {}
        self._running = False
        self._listening = False
        self._broadcasting = False
        self._listen_task: Optional[asyncio.Task] = None
        self._broadcast_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        
        # Callbacks
        self._on_device_found: Optional[Callable] = None
        self._on_device_lost: Optional[Callable] = None
    
    def set_callbacks(self, on_found: Callable = None, on_lost: Callable = None):
        """Set callbacks for device found/lost events"""
        self._on_device_found = on_found
        self._on_device_lost = on_lost
    
    async def start_listening(self):
        """Start listening for device broadcasts (Windows server side)"""
        if self._listening:
            return
        
        self._listening = True
        self._listen_task = asyncio.create_task(self._listen_loop())
        logger.info(f"Device discovery listening on port {self.BROADCAST_PORT}")
    
    async def stop_listening(self):
        """Stop listening for device broadcasts"""
        self._listening = False
        if self._listen_task:
            self._listen_task.cancel()
            self._listen_task = None
        logger.info("Device discovery stopped listening")
    
    async def _listen_loop(self):
        """Main listening loop"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        try:
            sock.bind(('', self.BROADCAST_PORT))
            sock.settimeout(1.0)  # Allow periodic checks
            
            while self._listening:
                try:
                    data, addr = sock.recvfrom(4096)
                    await self._handle_broadcast(data, addr[0])
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Discovery listen error: {e}")
                    await asyncio.sleep(1)
        
        finally:
            sock.close()
    
    async def _handle_broadcast(self, data: bytes, sender_ip: str):
        """Handle received device broadcast"""
        try:
            message = json.loads(data.decode('utf-8'))
            
            if message.get("type") != "device_announce":
                return
            
            device_info = DeviceInfo(
                device_id=message.get("device_id", f"unknown-{sender_ip}"),
                device_name=message.get("device_name", "Unknown Device"),
                ip_address=sender_ip,
                port=message.get("port", 8000),
                npu_type=message.get("npu_type", "unknown"),
                mac_address=message.get("mac_address", ""),
                version=message.get("version", "1.0"),
                last_seen=datetime.now(),
                status="online"
            )
            
            is_new = device_info.device_id not in self.discovered_devices
            self.discovered_devices[device_info.device_id] = device_info
            
            if is_new and self._on_device_found:
                await self._on_device_found(device_info)
                logger.info(f"Device discovered: {device_info.device_name} ({sender_ip})")
            else:
                logger.debug(f"Device heartbeat: {device_info.device_name} ({sender_ip})")
        
        except json.JSONDecodeError:
            pass
        except Exception as e:
            logger.error(f"Handle broadcast error: {e}")
    
    async def start_broadcasting(self, device_id: str, device_name: str, 
                                  npu_type: str = "unknown", port: int = 8000):
        """Start broadcasting device presence (ARM device side)"""
        if self._broadcasting:
            return
        
        self._broadcasting = True
        self._device_id = device_id
        self._device_name = device_name
        self._npu_type = npu_type
        self._device_port = port
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"Device broadcasting: {device_name}")
    
    async def stop_broadcasting(self):
        """Stop broadcasting device presence"""
        self._broadcasting = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
        logger.info("Device broadcasting stopped")
    
    async def _broadcast_loop(self):
        """Main broadcasting loop"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Get local IP
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
        except OSError:  # 网络不可用时降级到本地回环
            local_ip = "127.0.0.1"
        
        # Get MAC address
        mac_address = self._get_mac_address()
        
        message = json.dumps({
            "type": "device_announce",
            "device_id": self._device_id,
            "device_name": self._device_name,
            "npu_type": self._npu_type,
            "ip_address": local_ip,
            "port": self._device_port,
            "mac_address": mac_address,
            "version": "1.0"
        }).encode('utf-8')
        
        try:
            while self._broadcasting:
                try:
                    sock.sendto(message, ('<broadcast>', self.BROADCAST_PORT))
                    logger.debug(f"Broadcast sent: {self._device_id}")
                except Exception as e:
                    logger.error(f"Broadcast error: {e}")
                
                await asyncio.sleep(self.BROADCAST_INTERVAL)
        
        finally:
            sock.close()
    
    def _get_mac_address(self) -> str:
        """Get local MAC address"""
        try:
            import uuid
            mac = uuid.getnode()
            return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(0, 48, 8))
        except Exception:  # 硬件不支持时返回空 MAC
            return ""
    
    async def start_cleanup(self, timeout: int = 90):
        """Start periodic cleanup of offline devices"""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop(timeout))
    
    async def _cleanup_loop(self, timeout: int):
        """Clean up devices that haven't been seen recently"""
        while True:
            await asyncio.sleep(30)
            
            now = datetime.now()
            offline = []
            
            for device_id, device in self.discovered_devices.items():
                elapsed = (now - device.last_seen).total_seconds()
                if elapsed > timeout:
                    offline.append(device_id)
            
            for device_id in offline:
                device = self.discovered_devices.pop(device_id)
                device.status = "offline"
                if self._on_device_lost:
                    await self._on_device_lost(device)
                logger.info(f"Device offline: {device.device_name} ({device.device_id})")
    
    def get_devices(self) -> List[DeviceInfo]:
        """Get all discovered devices"""
        return list(self.discovered_devices.values())
    
    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        """Get a specific device"""
        return self.discovered_devices.get(device_id)
    
    def get_online_devices(self) -> List[DeviceInfo]:
        """Get all online devices"""
        return [d for d in self.discovered_devices.values() if d.status == "online"]


# Global discovery instance
device_discovery = DeviceDiscovery()


# ============ Discovery API Routes ============

from fastapi import APIRouter, HTTPException

discovery_router = APIRouter(prefix="/api/discovery", tags=["Discovery"])


@discovery_router.get("/devices")
async def list_discovered_devices():
    """List all discovered devices"""
    devices = device_discovery.get_devices()
    return {
        "count": len(devices),
        "devices": [asdict(d) for d in devices]
    }


@discovery_router.get("/devices/online")
async def list_online_devices():
    """List all online devices"""
    devices = device_discovery.get_online_devices()
    return {
        "count": len(devices),
        "devices": [asdict(d) for d in devices]
    }


@discovery_router.post("/devices/{device_id}/register")
async def register_device(device_id: str):
    """Register a discovered device to the main system (持久化到数据库)"""
    from database.db import db
    
    device = device_discovery.get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # 注册到数据库
    await db.register_device(
        device_id=device.device_id,
        device_name=device.device_name,
        ip_address=device.ip,
        port=device.port,
        npu_type=device.npu_type
    )
    
    return {
        "status": "registered",
        "device_id": device_id,
        "device_name": device.device_name,
        "ip": device.ip
    }


@discovery_router.post("/start")
async def start_discovery():
    """Start device discovery service"""
    if not device_discovery._listening:
        await device_discovery.start_listening()
        await device_discovery.start_cleanup()
    return {"status": "started"}


@discovery_router.post("/stop")
async def stop_discovery():
    """Stop device discovery service"""
    await device_discovery.stop_listening()
    return {"status": "stopped"}
