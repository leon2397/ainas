"""
内容自动标签模块
AI智能化 - Phase 3.3
基于图像内容自动打标签
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import cv2
import numpy as np
from collections import defaultdict


@dataclass
class TagPrediction:
    """标签预测结果"""
    tag: str
    confidence: float
    category: str  # object, scene, activity, attribute


class AutoTagger:
    """自动标签器"""
    
    # 预定义标签库
    TAG_LIBRARY = {
        "objects": [
            "person", "people", "family", "friends",
            "food", "meal", "dessert", "drink",
            "pet", "dog", "cat", "animal",
            "car", "vehicle", "building", "house",
            "flower", "plant", "tree", "nature",
            "book", "phone", "computer", "camera"
        ],
        "scenes": [
            "indoor", "outdoor",
            "home", "office", "restaurant", "cafe",
            "beach", "mountain", "park", "garden",
            "city", "street", "countryside",
            "sunset", "sunrise", "night", "day"
        ],
        "activities": [
            "eating", "cooking", "traveling", "shopping",
            "sports", "running", "swimming", "hiking",
            "party", "celebration", "wedding", "birthday",
            "meeting", "working", "studying",
            "selfie", "group_photo"
        ],
        "attributes": [
            "happy", "fun", "relaxing", "beautiful",
            "colorful", "bright", "dark", "blurry",
            "close_up", "landscape", "portrait"
        ]
    }
    
    def __init__(self):
        self._init_detectors()
    
    def _init_detectors(self):
        """初始化检测器"""
        self.detectors = {}
        
        # 颜色检测器
        self.detectors['color'] = self._detect_colors
        
        # 场景检测器 (基于简单特征)
        self.detectors['scene'] = self._detect_scene
        
        # 人脸检测器
        self.detectors['faces'] = self._detect_faces_simple
    
    async def tag_image(self, image_path: str) -> List[TagPrediction]:
        """为图片自动打标签"""
        predictions = []
        
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            return predictions
        
        # 颜色标签
        color_tags = await self._detect_colors(image)
        predictions.extend(color_tags)
        
        # 场景标签
        scene_tags = await self._detect_scene(image)
        predictions.extend(scene_tags)
        
        # 人脸标签
        face_tags = await self._detect_faces_simple(image)
        predictions.extend(face_tags)
        
        # 构图标签
        composition_tags = await self._detect_composition(image)
        predictions.extend(composition_tags)
        
        # 按置信度排序
        predictions.sort(key=lambda x: x.confidence, reverse=True)
        
        return predictions
    
    async def _detect_colors(self, image: np.ndarray) -> List[TagPrediction]:
        """检测颜色特征"""
        predictions = []
        
        # 计算平均颜色
        avg_color = np.mean(image, axis=(0, 1))
        b, g, r = avg_color
        
        # 判断整体色调
        if r > 150 and g > 150 and b < 100:
            predictions.append(TagPrediction("warm", 0.7, "attribute"))
            predictions.append(TagPrediction("sunset", 0.5, "scene"))
        elif b > 150 and r < 100:
            predictions.append(TagPrediction("cool", 0.7, "attribute"))
        
        # 计算亮度
        brightness = np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY))
        if brightness > 180:
            predictions.append(TagPrediction("bright", 0.8, "attribute"))
        elif brightness < 60:
            predictions.append(TagPrediction("dark", 0.8, "attribute"))
            predictions.append(TagPrediction("night", 0.6, "scene"))
        
        # 颜色丰富度
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        saturation = np.mean(hsv[:, :, 1])
        if saturation > 100:
            predictions.append(TagPrediction("colorful", 0.7, "attribute"))
        else:
            predictions.append(TagPrediction("monochrome", 0.6, "attribute"))
        
        return predictions
    
    async def _detect_scene(self, image: np.ndarray) -> List[TagPrediction]:
        """检测场景类型"""
        predictions = []
        h, w = image.shape[:2]
        
        # 检测天空 (上半部分蓝色区域)
        top_half = image[:h//2, :]
        hsv_top = cv2.cvtColor(top_half, cv2.COLOR_BGR2HSV)
        
        # 蓝色范围
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        blue_mask = cv2.inRange(hsv_top, lower_blue, upper_blue)
        blue_ratio = np.sum(blue_mask > 0) / (h * w / 2)
        
        if blue_ratio > 0.3:
            predictions.append(TagPrediction("outdoor", 0.8, "scene"))
            predictions.append(TagPrediction("sky", 0.7, "scene"))
        
        # 检测绿色 (植被)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        green_ratio = np.sum(green_mask > 0) / (h * w)
        
        if green_ratio > 0.2:
            predictions.append(TagPrediction("nature", 0.7, "scene"))
            predictions.append(TagPrediction("plant", 0.6, "object"))
        
        # 检测建筑 (垂直线条)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        if lines is not None and len(lines) > 20:
            vertical_lines = sum(1 for line in lines if abs(line[0][0] - line[0][2]) < 20)
            if vertical_lines > len(lines) * 0.3:
                predictions.append(TagPrediction("building", 0.6, "object"))
                predictions.append(TagPrediction("city", 0.5, "scene"))
        
        # 室内/室外判断
        if blue_ratio < 0.1 and green_ratio < 0.1:
            predictions.append(TagPrediction("indoor", 0.6, "scene"))
        
        return predictions
    
    async def _detect_faces_simple(self, image: np.ndarray) -> List[TagPrediction]:
        """简单人脸检测"""
        predictions = []
        
        try:
            # 使用Haar级联
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(30, 30)
            )
            
            face_count = len(faces)
            
            if face_count == 1:
                predictions.append(TagPrediction("person", 0.9, "object"))
                predictions.append(TagPrediction("portrait", 0.8, "attribute"))
            elif face_count == 2:
                predictions.append(TagPrediction("people", 0.9, "object"))
                predictions.append(TagPrediction("couple", 0.7, "object"))
            elif face_count > 2:
                predictions.append(TagPrediction("people", 0.9, "object"))
                predictions.append(TagPrediction("group_photo", 0.8, "activity"))
                if face_count >= 5:
                    predictions.append(TagPrediction("family", 0.6, "object"))
                    predictions.append(TagPrediction("friends", 0.6, "object"))
            
            # 检测自拍 (大脸在画面中央)
            if face_count == 1:
                x, y, w, h = faces[0]
                face_area = w * h
                image_area = image.shape[0] * image.shape[1]
                face_ratio = face_area / image_area
                
                if face_ratio > 0.15:
                    predictions.append(TagPrediction("selfie", 0.8, "activity"))
                    predictions.append(TagPrediction("close_up", 0.7, "attribute"))
        
        except Exception as e:
            pass
        
        return predictions
    
    async def _detect_composition(self, image: np.ndarray) -> List[TagPrediction]:
        """检测构图特征"""
        predictions = []
        h, w = image.shape[:2]
        aspect_ratio = w / h
        
        # 判断横竖构图
        if aspect_ratio > 1.5:
            predictions.append(TagPrediction("landscape", 0.9, "attribute"))
            predictions.append(TagPrediction("panorama", 0.6, "attribute"))
        elif aspect_ratio < 0.8:
            predictions.append(TagPrediction("portrait", 0.9, "attribute"))
        
        # 判断清晰度 (使用拉普拉斯算子)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        if laplacian_var < 100:
            predictions.append(TagPrediction("blurry", 0.7, "attribute"))
        else:
            predictions.append(TagPrediction("sharp", 0.7, "attribute"))
        
        return predictions
    
    async def batch_tag(self, image_paths: List[str]) -> Dict[str, List[TagPrediction]]:
        """批量打标签"""
        results = {}
        
        for path in image_paths:
            tags = await self.tag_image(path)
            results[path] = tags
        
        return results
    
    def get_top_tags(self, predictions: List[TagPrediction], limit: int = 5) -> List[str]:
        """获取 top N 标签"""
        # 去重并保留最高置信度
        tag_dict = {}
        for pred in predictions:
            if pred.tag not in tag_dict or pred.confidence > tag_dict[pred.tag]:
                tag_dict[pred.tag] = pred.confidence
        
        # 排序
        sorted_tags = sorted(tag_dict.items(), key=lambda x: x[1], reverse=True)
        
        return [tag for tag, conf in sorted_tags[:limit]]
    
    def get_tags_by_category(self, predictions: List[TagPrediction], category: str) -> List[str]:
        """按类别获取标签"""
        return [p.tag for p in predictions if p.category == category]


# 全局自动标签器实例
auto_tagger = AutoTagger()
