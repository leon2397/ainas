"""
NPU加速API路由
支持国产芯片(RK3588等)的AI加速
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from services.npu_accelerator import (
    get_npu_service,
    AcceleratorType,
    TaskType
)

router = APIRouter(prefix="/api/ai/accelerator", tags=["NPU Accelerator"])


# ============ Request Models ============

class ProcessRequest(BaseModel):
    image_path: str
    task: str  # face_detection / face_recognition / object_detection / image_classification / ocr / similarity / embedding
    accelerator: Optional[str] = None  # cpu / cuda / rk3588 / auto


class BatchProcessRequest(BaseModel):
    image_paths: List[str]
    task: str
    accelerator: Optional[str] = None


class SetAcceleratorRequest(BaseModel):
    accelerator_type: str  # cpu / cuda / rk3588 / auto


# ============ Routes ============

@router.get("/status")
async def get_accelerator_status():
    """
    获取NPU加速状态
    
    返回当前使用的加速器和所有可用加速器
    """
    service = get_npu_service()
    
    return {
        "current": service.get_current_accelerator().to_dict(),
        "available": [acc.to_dict() for acc in service.get_available_accelerators()],
        "auto_select": service.preferred_type == AcceleratorType.AUTO
    }


@router.get("/available")
async def list_available_accelerators():
    """列出所有可用的加速器"""
    service = get_npu_service()
    accelerators = service.get_available_accelerators()
    
    return {
        "accelerators": [acc.to_dict() for acc in accelerators],
        "count": len(accelerators),
        "recommendation": accelerators[0].type.value if accelerators else "cpu"
    }


@router.post("/set")
async def set_accelerator(request: SetAcceleratorRequest):
    """
    设置加速器
    
    可选值:
    - cpu: 使用CPU
    - cuda: 使用NVIDIA GPU
    - rk3588: 使用RK3588 NPU
    - auto: 自动选择最佳加速器
    """
    try:
        acc_type = AcceleratorType(request.accelerator_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的加速器类型: {request.accelerator_type}"
        )
    
    service = get_npu_service()
    
    if service.set_accelerator(acc_type):
        return {
            "status": "success",
            "accelerator": acc_type.value,
            "message": f"已切换到 {acc_type.value} 加速器"
        }
    else:
        raise HTTPException(
            status_code=400,
            detail=f"加速器 {acc_type.value} 不可用"
        )


@router.post("/process")
async def process_image(request: ProcessRequest):
    """
    使用NPU加速处理单张图片
    
    任务类型:
    - face_detection: 人脸检测
    - face_recognition: 人脸识别
    - object_detection: 物体检测
    - image_classification: 图像分类
    - ocr: 文字识别
    - similarity: 相似度计算
    - embedding: 特征向量提取
    """
    # 验证任务类型
    try:
        task = TaskType(request.task)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的任务类型: {request.task}"
        )
    
    # 验证加速器类型
    accelerator = None
    if request.accelerator:
        try:
            accelerator = AcceleratorType(request.accelerator)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的加速器类型: {request.accelerator}"
            )
    
    service = get_npu_service()
    
    try:
        result = service.process_image(
            image_path=request.image_path,
            task=task,
            accelerator=accelerator
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_process(request: BatchProcessRequest):
    """批量处理图片"""
    # 验证任务类型
    try:
        task = TaskType(request.task)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的任务类型: {request.task}"
        )
    
    # 验证加速器类型
    accelerator = None
    if request.accelerator:
        try:
            accelerator = AcceleratorType(request.accelerator)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"无效的加速器类型: {request.accelerator}"
            )
    
    service = get_npu_service()
    
    try:
        results = service.batch_process(
            image_paths=request.image_paths,
            task=task,
            accelerator=accelerator
        )
        
        return {
            "status": "success",
            "task": request.task,
            "processed_count": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/benchmark")
async def run_benchmark():
    """
    运行性能测试
    
    测试各加速器的处理速度
    """
    service = get_npu_service()
    
    try:
        results = service.benchmark()
        
        return {
            "status": "success",
            "benchmark_results": results,
            "best_accelerator": max(
                results.items(),
                key=lambda x: x[1].get("throughput_fps", 0) if x[1].get("available") else 0
            )[0] if results else "cpu"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"性能测试失败: {str(e)}")


@router.get("/tasks")
async def list_supported_tasks():
    """列出支持的任务类型"""
    tasks = [
        {"id": "face_detection", "name": "人脸检测", "description": "检测图片中的人脸位置"},
        {"id": "face_recognition", "name": "人脸识别", "description": "识别并匹配人脸"},
        {"id": "object_detection", "name": "物体检测", "description": "检测图片中的物体"},
        {"id": "image_classification", "name": "图像分类", "description": "对图片进行分类"},
        {"id": "ocr", "name": "文字识别", "description": "识别图片中的文字"},
        {"id": "similarity", "name": "相似度计算", "description": "计算图片相似度"},
        {"id": "embedding", "name": "特征向量", "description": "提取图片特征向量"}
    ]
    
    return {
        "tasks": tasks,
        "count": len(tasks)
    }


@router.get("/info/{accelerator_type}")
async def get_accelerator_info(accelerator_type: str):
    """
    获取指定加速器的详细信息
    
    可选值: cpu, cuda, rk3588, rocm, opencl, metal
    """
    try:
        acc_type = AcceleratorType(accelerator_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"无效的加速器类型: {accelerator_type}"
        )
    
    service = get_npu_service()
    
    if acc_type not in service.engines:
        raise HTTPException(status_code=404, detail="加速器未注册")
    
    engine = service.engines[acc_type]
    info = engine.get_info()
    
    return {
        "type": info.type.value,
        "name": info.name,
        "available": info.available,
        "memory_mb": info.memory_mb,
        "compute_units": info.compute_units,
        "driver_version": info.driver_version
    }


# ============ 兼容性接口 ============

@router.get("/rk3588/status")
async def get_rk3588_status():
    """RK3588 NPU状态（兼容性接口）"""
    service = get_npu_service()
    
    if AcceleratorType.NPU_RK3588 in service.engines:
        engine = service.engines[AcceleratorType.NPU_RK3588]
        info = engine.get_info()
        
        return {
            "available": info.available,
            "name": info.name,
            "cores": info.compute_units,
            "memory_mb": info.memory_mb
        }
    
    return {
        "available": False,
        "name": "RK3588 NPU",
        "cores": 0,
        "memory_mb": 0
    }


@router.post("/rk3588/enable")
async def enable_rk3588():
    """启用RK3588 NPU（兼容性接口）"""
    service = get_npu_service()
    
    if service.set_accelerator(AcceleratorType.NPU_RK3588):
        return {
            "status": "success",
            "message": "RK3588 NPU已启用"
        }
    else:
        raise HTTPException(
            status_code=400,
            detail="RK3588 NPU不可用，请检查硬件和驱动"
        )
