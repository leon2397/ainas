"""
NPU加速服务
支持国产芯片(RK3588等)的AI加速
"""

import os
import json
import platform
import subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod
import time


class AcceleratorType(str, Enum):
    """加速器类型"""
    CPU = "cpu"
    CUDA = "cuda"           # NVIDIA GPU
    ROCM = "rocm"           # AMD GPU
    NPU_RK3588 = "rk3588"   # 瑞芯微RK3588
    NPU_NPU = "npu"         # 通用NPU
    OPENCL = "opencl"       # OpenCL
    METAL = "metal"         # Apple Metal
    AUTO = "auto"           # 自动检测


class TaskType(str, Enum):
    """AI任务类型"""
    FACE_DETECTION = "face_detection"
    FACE_RECOGNITION = "face_recognition"
    OBJECT_DETECTION = "object_detection"
    IMAGE_CLASSIFICATION = "image_classification"
    OCR = "ocr"
    SIMILARITY = "similarity"
    EMBEDDING = "embedding"


@dataclass
class AcceleratorInfo:
    """加速器信息"""
    type: AcceleratorType
    name: str
    available: bool
    memory_mb: Optional[int] = None
    compute_units: Optional[int] = None
    driver_version: Optional[str] = None
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['type'] = self.type.value
        return d


class AIEngine(ABC):
    """AI引擎基类"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查引擎是否可用"""
        pass
    
    @abstractmethod
    def get_info(self) -> AcceleratorInfo:
        """获取引擎信息"""
        pass
    
    @abstractmethod
    def process_image(self, image_path: str, task: TaskType) -> Dict[str, Any]:
        """处理图片"""
        pass
    
    @abstractmethod
    def batch_process(self, image_paths: List[str], task: TaskType) -> List[Dict[str, Any]]:
        """批量处理图片"""
        pass


class CPUEngine(AIEngine):
    """CPU引擎（后备方案）"""
    
    def __init__(self):
        self.name = f"{platform.processor() or 'Unknown CPU'}"
    
    def is_available(self) -> bool:
        return True  # CPU始终可用
    
    def get_info(self) -> AcceleratorInfo:
        return AcceleratorInfo(
            type=AcceleratorType.CPU,
            name=self.name,
            available=True,
            compute_units=os.cpu_count()
        )
    
    def process_image(self, image_path: str, task: TaskType) -> Dict[str, Any]:
        """CPU处理图片"""
        start_time = time.time()
        
        # 模拟处理（实际实现会使用OpenCV等库）
        result = {
            "status": "success",
            "task": task.value,
            "image_path": image_path,
            "accelerator": "cpu",
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }
        
        if task == TaskType.FACE_DETECTION:
            result["faces"] = []  # 人脸位置列表
        elif task == TaskType.OBJECT_DETECTION:
            result["objects"] = []  # 物体列表
        elif task == TaskType.IMAGE_CLASSIFICATION:
            result["labels"] = []  # 分类标签
        
        return result
    
    def batch_process(self, image_paths: List[str], task: TaskType) -> List[Dict[str, Any]]:
        """批量处理"""
        return [self.process_image(p, task) for p in image_paths]


class RK3588Engine(AIEngine):
    """RK3588 NPU引擎"""
    
    def __init__(self):
        self.name = "Rockchip RK3588 NPU"
        self.rknpu_available = False
        self._check_rknpu()
    
    def _check_rknpu(self):
        """检查RKNN SDK是否可用"""
        try:
            # 尝试导入rknn API
            # 实际部署时需要安装 rknn-toolkit2
            import importlib
            importlib.import_module('rknn.api')
            self.rknpu_available = True
        except ImportError:
            self.rknpu_available = False
    
    def is_available(self) -> bool:
        # 检查是否在RK3588平台上
        if not self.rknpu_available:
            return False
        
        try:
            # 检查设备树信息
            with open('/sys/firmware/devicetree/base/compatible', 'r') as f:
                compatible = f.read()
                return 'rk3588' in compatible.lower()
        except (IOError, OSError):  # 设备树不可用时返回 False
            return False
    
    def get_info(self) -> AcceleratorInfo:
        return AcceleratorInfo(
            type=AcceleratorType.NPU_RK3588,
            name=self.name,
            available=self.is_available(),
            compute_units=3,  # RK3588有3个NPU核心
            memory_mb=1024
        )
    
    def process_image(self, image_path: str, task: TaskType) -> Dict[str, Any]:
        """RK3588 NPU处理"""
        if not self.is_available():
            raise RuntimeError("RK3588 NPU不可用")
        
        start_time = time.time()
        
        # 实际实现会使用RKNN进行推理
        # 这里是简化版本
        
        result = {
            "status": "success",
            "task": task.value,
            "image_path": image_path,
            "accelerator": "rk3588_npu",
            "processing_time_ms": int((time.time() - start_time) * 1000),
            "npu_cores_used": 1
        }
        
        return result
    
    def batch_process(self, image_paths: List[str], task: TaskType) -> List[Dict[str, Any]]:
        """批量处理 - RK3588可以利用多NPU核心"""
        if not self.is_available():
            raise RuntimeError("RK3588 NPU不可用")
        
        # RK3588可以使用多核心并行处理
        results = []
        for i, path in enumerate(image_paths):
            core_id = i % 3  # 轮询使用3个核心
            result = self.process_image(path, task)
            result["npu_core"] = core_id
            results.append(result)
        
        return results


class CUDAEngine(AIEngine):
    """NVIDIA CUDA引擎"""
    
    def __init__(self):
        self.name = "NVIDIA GPU"
        self.cuda_available = False
        self.device_name = None
        self.device_memory = None
        self._check_cuda()
    
    def _check_cuda(self):
        """检查CUDA是否可用"""
        try:
            import torch
            if torch.cuda.is_available():
                self.cuda_available = True
                self.device_name = torch.cuda.get_device_name(0)
                self.device_memory = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
        except ImportError:
            self.cuda_available = False
    
    def is_available(self) -> bool:
        return self.cuda_available
    
    def get_info(self) -> AcceleratorInfo:
        return AcceleratorInfo(
            type=AcceleratorType.CUDA,
            name=self.device_name or "NVIDIA GPU",
            available=self.cuda_available,
            memory_mb=self.device_memory,
            driver_version=self._get_driver_version()
        )
    
    def _get_driver_version(self) -> Optional[str]:
        try:
            import torch
            return torch.version.cuda
        except ImportError:  # PyTorch 未安装时返回 None
            return None
    
    def process_image(self, image_path: str, task: TaskType) -> Dict[str, Any]:
        """CUDA处理"""
        if not self.cuda_available:
            raise RuntimeError("CUDA不可用")
        
        start_time = time.time()
        
        result = {
            "status": "success",
            "task": task.value,
            "image_path": image_path,
            "accelerator": "cuda",
            "device": self.device_name,
            "processing_time_ms": int((time.time() - start_time) * 1000)
        }
        
        return result
    
    def batch_process(self, image_paths: List[str], task: TaskType) -> List[Dict[str, Any]]:
        """批量处理"""
        return [self.process_image(p, task) for p in image_paths]


class NPUAcceleratorService:
    """NPU加速服务"""
    
    def __init__(self, preferred_type: AcceleratorType = AcceleratorType.AUTO):
        self.preferred_type = preferred_type
        self.engines: Dict[AcceleratorType, AIEngine] = {}
        self.current_engine: Optional[AIEngine] = None
        
        # 注册所有引擎
        self._register_engines()
        
        # 自动选择最佳引擎
        if preferred_type == AcceleratorType.AUTO:
            self._auto_select_engine()
        else:
            self._select_engine(preferred_type)
    
    def _register_engines(self):
        """注册所有引擎"""
        self.engines[AcceleratorType.CPU] = CPUEngine()
        self.engines[AcceleratorType.NPU_RK3588] = RK3588Engine()
        self.engines[AcceleratorType.CUDA] = CUDAEngine()
    
    def _auto_select_engine(self):
        """自动选择最佳引擎"""
        priority = [
            AcceleratorType.CUDA,      # 优先使用CUDA
            AcceleratorType.NPU_RK3588, # 然后是RK3588 NPU
            AcceleratorType.CPU        # 最后是CPU
        ]
        
        for acc_type in priority:
            if acc_type in self.engines and self.engines[acc_type].is_available():
                self.current_engine = self.engines[acc_type]
                logger.info(f"NPU加速服务: 使用 {acc_type.value} 引擎")
                return
        
        # 默认使用CPU
        self.current_engine = self.engines[AcceleratorType.CPU]
    
    def _select_engine(self, acc_type: AcceleratorType):
        """选择指定引擎"""
        if acc_type in self.engines:
            engine = self.engines[acc_type]
            if engine.is_available():
                self.current_engine = engine
                return
        
        raise ValueError(f"加速器 {acc_type.value} 不可用")
    
    def get_available_accelerators(self) -> List[AcceleratorInfo]:
        """获取所有可用的加速器"""
        return [engine.get_info() for engine in self.engines.values() if engine.is_available()]
    
    def get_current_accelerator(self) -> AcceleratorInfo:
        """获取当前使用的加速器"""
        if self.current_engine:
            return self.current_engine.get_info()
        return self.engines[AcceleratorType.CPU].get_info()
    
    def set_accelerator(self, acc_type: AcceleratorType) -> bool:
        """设置加速器"""
        try:
            self._select_engine(acc_type)
            return True
        except ValueError:
            return False
    
    def process_image(
        self,
        image_path: str,
        task: TaskType,
        accelerator: Optional[AcceleratorType] = None
    ) -> Dict[str, Any]:
        """
        处理单张图片
        
        Args:
            image_path: 图片路径
            task: 任务类型
            accelerator: 指定加速器（可选）
            
        Returns:
            处理结果
        """
        engine = self.current_engine
        if accelerator and accelerator in self.engines:
            acc_engine = self.engines[accelerator]
            if acc_engine.is_available():
                engine = acc_engine
        
        return engine.process_image(image_path, task)
    
    def batch_process(
        self,
        image_paths: List[str],
        task: TaskType,
        accelerator: Optional[AcceleratorType] = None
    ) -> List[Dict[str, Any]]:
        """批量处理图片"""
        engine = self.current_engine
        if accelerator and accelerator in self.engines:
            acc_engine = self.engines[accelerator]
            if acc_engine.is_available():
                engine = acc_engine
        
        return engine.batch_process(image_paths, task)
    
    def benchmark(self) -> Dict[str, Any]:
        """性能测试"""
        from loguru import logger
        import tempfile
        from PIL import Image
        
        results = {}
        
        # 创建测试图片
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            test_image = f.name
            img = Image.new('RGB', (1920, 1080), color='blue')
            img.save(test_image, 'JPEG')
        
        try:
            for acc_type, engine in self.engines.items():
                if engine.is_available():
                    start = time.time()
                    for _ in range(10):
                        engine.process_image(test_image, TaskType.FACE_DETECTION)
                    elapsed = time.time() - start
                    
                    results[acc_type.value] = {
                        "available": True,
                        "avg_time_ms": int(elapsed * 1000 / 10),
                        "throughput_fps": round(10 / elapsed, 2)
                    }
                else:
                    results[acc_type.value] = {
                        "available": False,
                        "avg_time_ms": None,
                        "throughput_fps": None
                    }
        finally:
            os.unlink(test_image)
        
        return results


# 单例
_npu_service = None

def get_npu_service() -> NPUAcceleratorService:
    """获取NPU加速服务单例"""
    global _npu_service
    if _npu_service is None:
        _npu_service = NPUAcceleratorService()
    return _npu_service
