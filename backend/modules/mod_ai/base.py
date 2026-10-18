# AI Engine Abstract Base Class

from abc import ABC, abstractmethod
from typing import Dict, List, Any

class AIEngine(ABC):
    """AI 引擎抽象基类，所有 NPU 引擎必须实现此类方法"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化引擎（加载模型、配置参数）"""
        self.config = config
    
    @abstractmethod
    def image_predict(self, filepath: str) -> Dict[str, Any]:
        """
        图像 AI 推理
        返回：{"tags": [标签列表], "feature": 特征向量, "confidence": 置信度}
        """
        pass
    
    @abstractmethod
    def video_predict(self, filepath: str) -> Dict[str, Any]:
        """
        视频 AI 推理
        返回：{"tags": [标签列表], "audio_tags": [音频标签], "duration": 时长, "feature": 特征向量}
        """
        pass
    
    @abstractmethod
    def face_detect(self, filepath: str) -> Dict[str, Any]:
        """
        人脸检测与特征提取
        返回：{"faces": [人脸坐标列表], "embeddings": [人脸特征向量列表]}
        """
        pass
    
    @abstractmethod
    def deduplicate(self, feature: List[float], threshold: float = 0.8) -> List[str]:
        """
        相似性去重（根据特征向量）
        返回：相似文件的路径列表
        """
        pass
