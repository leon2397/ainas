"""
Load Balancer Service
Automatically routes tasks to the least loaded device
"""

import asyncio
from typing import List, Dict, Optional
from database.db import Database


class LoadBalancer:
    """
    Task load balancer for multi-device scenarios
    
    Routes tasks to:
    - Online devices only
    - Device with lowest current load
    - Device with required NPU type (if specified)
    """
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_best_device(
        self,
        npu_type: str = None,
        task_type: str = None
    ) -> Optional[Dict]:
        """
        Get the best device for a task
        
        Args:
            npu_type: Required NPU type (optional)
            task_type: Task type (affects load calculation)
        
        Returns:
            Best device info or None
        """
        # Get all online devices
        devices = await self._get_online_devices()
        
        if not devices:
            return None
        
        # Filter by NPU type if specified
        if npu_type:
            devices = [d for d in devices if d.get('npu_type') == npu_type]
            # Fall back to CPU devices if no NPU match
            if not devices:
                devices = await self._get_online_devices()
        
        if not devices:
            return None
        
        # Calculate load score for each device
        scored_devices = []
        for device in devices:
            score = self._calculate_load_score(device, task_type)
            scored_devices.append((score, device))
        
        # Sort by load score (lower is better)
        scored_devices.sort(key=lambda x: x[0])
        
        return scored_devices[0][1] if scored_devices else None
    
    def _calculate_load_score(self, device: Dict, task_type: str) -> float:
        """
        Calculate device load score
        
        Lower score = better for receiving tasks
        
        Factors:
        - CPU usage (weight: 0.3)
        - NPU usage (weight: 0.5, if applicable)
        - Current task count (weight: 0.2)
        """
        cpu_weight = 0.3
        npu_weight = 0.5
        task_weight = 0.2
        
        # CPU score (0-100)
        cpu_usage = device.get('cpu_usage', 0) or 0
        
        # NPU score (0-100), default to 0 for CPU-only devices
        npu_usage = device.get('npu_usage', 0) or 0
        
        # Task count (normalized)
        # Assume 10 tasks is 100% load
        active_tasks = device.get('active_tasks', 0) or 0
        task_load = min(active_tasks / 10 * 100, 100)
        
        # Calculate weighted score
        score = (
            cpu_usage * cpu_weight +
            npu_usage * npu_weight +
            task_load * task_weight
        )
        
        return score
    
    async def _get_online_devices(self) -> List[Dict]:
        """Get all online devices with current load info"""
        devices = await self.db.fetchall(
            """SELECT d.*, 
                      COUNT(t.id) as active_tasks
               FROM devices d
               LEFT JOIN tasks t ON d.device_id = t.device_id 
                   AND t.status IN ('pending', 'running')
               WHERE d.status = 'online'
               GROUP BY d.device_id"""
        )
        
        return devices
    
    async def get_device_loads(self) -> List[Dict]:
        """Get load information for all devices"""
        devices = await self._get_online_devices()
        
        result = []
        for device in devices:
            score = self._calculate_load_score(device, None)
            result.append({
                'device_id': device.get('device_id'),
                'device_name': device.get('device_name'),
                'status': device.get('status'),
                'npu_type': device.get('npu_type'),
                'cpu_usage': device.get('cpu_usage', 0),
                'npu_usage': device.get('npu_usage', 0),
                'active_tasks': device.get('active_tasks', 0),
                'load_score': round(score, 2),
                'recommendation': 'recommended' if score < 50 else 'busy'
            })
        
        # Sort by load score
        result.sort(key=lambda x: x['load_score'])
        
        return result
    
    async def is_npu_available(self, npu_type: str) -> bool:
        """Check if a specific NPU type is available online"""
        device = await self.get_best_device(npu_type=npu_type)
        return device is not None
    
    async def dispatch_task(
        self,
        task_id: str,
        task_type: str,
        npu_type: str = None,
        device_id: str = None
    ) -> Dict:
        """
        Dispatch a task to the best available device
        
        Args:
            task_id: Task ID
            task_type: Type of task
            npu_type: Required NPU type (optional)
            device_id: Specific device ID (optional, bypasses load balancing)
        
        Returns:
            Dispatch result with device info
        """
        # If specific device requested
        if device_id:
            device = await self.db.fetchone(
                "SELECT * FROM devices WHERE device_id = ? AND status = 'online'",
                (device_id,)
            )
            if not device:
                return {
                    'success': False,
                    'error': f'Device {device_id} is offline or not found'
                }
        else:
            # Find best device
            device = await self.get_best_device(npu_type=npu_type, task_type=task_type)
            
            if not device:
                return {
                    'success': False,
                    'error': 'No available devices found'
                }
        
        return {
            'success': True,
            'device': device,
            'task_id': task_id
        }


# Global load balancer instance
load_balancer: Optional[LoadBalancer] = None


async def get_load_balancer(db: Database) -> LoadBalancer:
    """Get or create load balancer instance"""
    global load_balancer
    if load_balancer is None:
        load_balancer = LoadBalancer(db)
    return load_balancer
