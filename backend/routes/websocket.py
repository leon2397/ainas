"""
WebSocket Manager
Real-time communication for task progress and device status updates
"""

import asyncio
import json
from typing import Dict, Set, Optional, Callable
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from core.logger import logger


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Active connections grouped by type
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "task": set(),      # Task progress subscribers
            "device": set(),    # Device status subscribers
            "media": set(),     # Media sync subscribers
            "all": set(),       # All subscribers
        }
        
        # Client metadata
        self.client_info: Dict[WebSocket, dict] = {}
        
        # Event callbacks
        self._callbacks: Dict[str, Callable] = {}
    
    async def connect(self, websocket: WebSocket, client_type: str = "all"):
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        
        # Add to appropriate groups
        if client_type in self.active_connections:
            self.active_connections[client_type].add(websocket)
        self.active_connections["all"].add(websocket)
        
        # Store client info
        self.client_info[websocket] = {
            "type": client_type,
            "connected_at": datetime.now().isoformat()
        }
        
        logger.debug(f"WebSocket connected ({client_type}), total: {len(self.active_connections['all'])}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        for conn_set in self.active_connections.values():
            conn_set.discard(websocket)
        
        self.client_info.pop(websocket, None)
        logger.debug(f"WebSocket disconnected, remaining: {len(self.active_connections['all'])}")
    
    async def send_personal(self, websocket: WebSocket, message: dict):
        """Send message to a specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"WebSocket send failed: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict, client_type: str = "all"):
        """Broadcast message to all clients of a type"""
        connections = self.active_connections.get(client_type, set())
        disconnected = []
        
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)
        
        # Clean up disconnected
        for ws in disconnected:
            self.disconnect(ws)
    
    async def broadcast_task_update(self, task_id: str, status: str, 
                                    progress: int, result: dict = None):
        """Broadcast task progress update"""
        message = {
            "type": "task_update",
            "data": {
                "task_id": task_id,
                "status": status,
                "progress": progress,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.broadcast(message, "task")
    
    async def broadcast_device_status(self, device_id: str, status: str,
                                      cpu_usage: float = 0, npu_usage: float = 0):
        """Broadcast device status change"""
        message = {
            "type": "device_status",
            "data": {
                "device_id": device_id,
                "status": status,
                "cpu_usage": cpu_usage,
                "npu_usage": npu_usage,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.broadcast(message, "device")
    
    async def broadcast_media_update(self, action: str, file_data: dict):
        """Broadcast media library update"""
        message = {
            "type": "media_update",
            "data": {
                "action": action,  # add, delete, update
                "file": file_data,
                "timestamp": datetime.now().isoformat()
            }
        }
        await self.broadcast(message, "media")
    
    def register_callback(self, event: str, callback: Callable):
        """Register a callback for specific events"""
        self._callbacks[event] = callback
    
    @property
    def connection_count(self) -> int:
        """Get total active connection count"""
        return len(self.active_connections["all"])


# Global connection manager
manager = ConnectionManager()


# ============ WebSocket API Routes ============

from fastapi import APIRouter, WebSocket

ws_router = APIRouter(tags=["WebSocket"])


@ws_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Main WebSocket endpoint for real-time updates
    
    Client sends:
    {
        "type": "subscribe",
        "channel": "task" | "device" | "media" | "all"
    }
    
    Server sends:
    {
        "type": "task_update" | "device_status" | "media_update",
        "data": {...}
    }
    """
    await manager.connect(websocket, "all")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            if data.get("type") == "subscribe":
                # Handle subscription
                channel = data.get("channel", "all")
                # Reconnect to specific channel
                await websocket.send_json({
                    "type": "subscribed",
                    "channel": channel
                })
            
            elif data.get("type") == "ping":
                # Heartbeat
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "task_progress":
                # Task progress update from ARM device
                await manager.broadcast_task_update(
                    task_id=data.get("task_id"),
                    status=data.get("status"),
                    progress=data.get("progress", 0),
                    result=data.get("result")
                )
            
            elif data.get("type") == "device_heartbeat":
                # Device heartbeat update
                await manager.broadcast_device_status(
                    device_id=data.get("device_id"),
                    status=data.get("status", "online"),
                    cpu_usage=data.get("cpu_usage", 0),
                    npu_usage=data.get("npu_usage", 0)
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@ws_router.get("/ws/status")
async def websocket_status():
    """Get WebSocket connection status"""
    return {
        "status": "connected" if manager.connection_count > 0 else "disconnected",
        "connections": manager.connection_count,
        "channels": {
            "task": len(manager.active_connections["task"]),
            "device": len(manager.active_connections["device"]),
            "media": len(manager.active_connections["media"]),
            "all": len(manager.active_connections["all"])
        }
    }
