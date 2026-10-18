"""
相似图片检测模块
AI智能化 - Phase 3.4
基于感知哈希和特征相似度检测重复/相似图片
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from collections import defaultdict


@dataclass
class ImageHash:
    """图片哈希"""
    path: str
    phash: str  # 感知哈希
    dhash: str  # 差异哈希
    ahash: str  # 平均哈希
    features: np.ndarray  # 特征向量


@dataclass
class SimilarityResult:
    """相似度结果"""
    image1: str
    image2: str
    similarity: float  # 0-1
    hash_similarity: float
    feature_similarity: float
    is_duplicate: bool


class SimilarityDetector:
    """相似图片检测器"""
    
    def __init__(self, 
                 duplicate_threshold: float = 0.95,
                 similar_threshold: float = 0.80):
        self.duplicate_threshold = duplicate_threshold
        self.similar_threshold = similar_threshold
        self._hash_cache: Dict[str, ImageHash] = {}
    
    def _calculate_phash(self, image: np.ndarray, hash_size: int = 8) -> str:
        """计算感知哈希 (pHash)"""
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 缩放
        resized = cv2.resize(gray, (32, 32))
        
        # DCT变换
        dct = cv2.dct(np.float32(resized))
        
        # 取低频部分
        dct_low = dct[:hash_size, :hash_size]
        
        # 计算平均值 (排除DC分量)
        avg = (dct_low.sum() - dct_low[0, 0]) / (hash_size * hash_size - 1)
        
        # 生成哈希
        hash_bits = []
        for i in range(hash_size):
            for j in range(hash_size):
                if i == 0 and j == 0:
                    continue
                hash_bits.append('1' if dct_low[i, j] > avg else '0')
        
        return ''.join(hash_bits)
    
    def _calculate_dhash(self, image: np.ndarray, hash_size: int = 8) -> str:
        """计算差异哈希 (dHash)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 缩放 (宽度+1用于计算差异)
        resized = cv2.resize(gray, (hash_size + 1, hash_size))
        
        # 计算差异
        diff = resized[:, 1:] > resized[:, :-1]
        
        # 生成哈希
        return ''.join('1' if x else '0' for x in diff.flatten())
    
    def _calculate_ahash(self, image: np.ndarray, hash_size: int = 8) -> str:
        """计算平均哈希 (aHash)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 缩放
        resized = cv2.resize(gray, (hash_size, hash_size))
        
        # 计算平均值
        avg = resized.mean()
        
        # 生成哈希
        return ''.join('1' if x > avg else '0' for x in resized.flatten())
    
    def _extract_features(self, image: np.ndarray) -> np.ndarray:
        """提取图片特征"""
        # 使用颜色直方图作为特征
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 计算H和S的直方图
        h_hist = cv2.calcHist([hsv], [0], None, [32], [0, 180])
        s_hist = cv2.calcHist([hsv], [1], None, [32], [0, 256])
        
        # 归一化
        h_hist = cv2.normalize(h_hist, h_hist).flatten()
        s_hist = cv2.normalize(s_hist, s_hist).flatten()
        
        # 合并特征
        features = np.concatenate([h_hist, s_hist])
        
        return features
    
    def _hash_similarity(self, hash1: str, hash2: str) -> float:
        """计算哈希相似度 (汉明距离)"""
        if len(hash1) != len(hash2):
            return 0.0
        
        # 计算汉明距离
        distance = sum(c1 != c2 for c1, c2 in zip(hash1, hash2))
        max_distance = len(hash1)
        
        # 转换为相似度
        similarity = 1 - (distance / max_distance)
        
        return similarity
    
    def _feature_similarity(self, features1: np.ndarray, features2: np.ndarray) -> float:
        """计算特征相似度 (余弦相似度)"""
        dot_product = np.dot(features1, features2)
        norm1 = np.linalg.norm(features1)
        norm2 = np.linalg.norm(features2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    async def compute_hash(self, image_path: str) -> Optional[ImageHash]:
        """计算图片哈希"""
        # 检查缓存
        if image_path in self._hash_cache:
            return self._hash_cache[image_path]
        
        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            return None
        
        # 标准化大小
        image = cv2.resize(image, (256, 256))
        
        # 计算各种哈希
        phash = self._calculate_phash(image)
        dhash = self._calculate_dhash(image)
        ahash = self._calculate_ahash(image)
        features = self._extract_features(image)
        
        image_hash = ImageHash(
            path=image_path,
            phash=phash,
            dhash=dhash,
            ahash=ahash,
            features=features
        )
        
        # 缓存
        self._hash_cache[image_path] = image_hash
        
        return image_hash
    
    async def compare_images(self, image1_path: str, image2_path: str) -> SimilarityResult:
        """比较两张图片的相似度"""
        hash1 = await self.compute_hash(image1_path)
        hash2 = await self.compute_hash(image2_path)
        
        if hash1 is None or hash2 is None:
            return SimilarityResult(
                image1=image1_path,
                image2=image2_path,
                similarity=0.0,
                hash_similarity=0.0,
                feature_similarity=0.0,
                is_duplicate=False
            )
        
        # 计算哈希相似度 (综合三种哈希)
        phash_sim = self._hash_similarity(hash1.phash, hash2.phash)
        dhash_sim = self._hash_similarity(hash1.dhash, hash2.dhash)
        ahash_sim = self._hash_similarity(hash1.ahash, hash2.ahash)
        hash_sim = (phash_sim + dhash_sim + ahash_sim) / 3
        
        # 计算特征相似度
        feature_sim = self._feature_similarity(hash1.features, hash2.features)
        
        # 综合相似度
        similarity = hash_sim * 0.6 + feature_sim * 0.4
        
        # 判断是否重复
        is_duplicate = similarity >= self.duplicate_threshold
        
        return SimilarityResult(
            image1=image1_path,
            image2=image2_path,
            similarity=similarity,
            hash_similarity=hash_sim,
            feature_similarity=feature_sim,
            is_duplicate=is_duplicate
        )
    
    async def find_duplicates(self, image_paths: List[str]) -> List[List[str]]:
        """查找重复图片组"""
        # 计算所有图片的哈希
        hashes = []
        for path in image_paths:
            h = await self.compute_hash(path)
            if h:
                hashes.append(h)
        
        # 使用聚类找出重复组
        n = len(hashes)
        if n < 2:
            return []
        
        # 构建相似度矩阵
        groups = []
        visited = set()
        
        for i in range(n):
            if i in visited:
                continue
            
            group = [hashes[i].path]
            visited.add(i)
            
            for j in range(i + 1, n):
                if j in visited:
                    continue
                
                # 快速比较：先比较pHash
                phash_sim = self._hash_similarity(hashes[i].phash, hashes[j].phash)
                
                if phash_sim >= self.duplicate_threshold:
                    # 详细比较
                    result = await self.compare_images(hashes[i].path, hashes[j].path)
                    
                    if result.is_duplicate:
                        group.append(hashes[j].path)
                        visited.add(j)
            
            if len(group) > 1:
                groups.append(group)
        
        return groups
    
    async def find_similar(self, query_path: str, candidate_paths: List[str], 
                          top_k: int = 10) -> List[SimilarityResult]:
        """查找相似图片"""
        results = []
        
        for candidate_path in candidate_paths:
            if candidate_path == query_path:
                continue
            
            result = await self.compare_images(query_path, candidate_path)
            
            if result.similarity >= self.similar_threshold:
                results.append(result)
        
        # 按相似度排序
        results.sort(key=lambda x: x.similarity, reverse=True)
        
        return results[:top_k]
    
    async def batch_compare(self, image_paths: List[str]) -> List[SimilarityResult]:
        """批量比较所有图片对"""
        results = []
        n = len(image_paths)
        
        for i in range(n):
            for j in range(i + 1, n):
                result = await self.compare_images(image_paths[i], image_paths[j])
                
                if result.similarity >= self.similar_threshold:
                    results.append(result)
        
        # 按相似度排序
        results.sort(key=lambda x: x.similarity, reverse=True)
        
        return results
    
    def clear_cache(self):
        """清除哈希缓存"""
        self._hash_cache.clear()
    
    def save_cache(self, filepath: str):
        """保存哈希缓存"""
        data = {}
        for path, img_hash in self._hash_cache.items():
            data[path] = {
                "path": img_hash.path,
                "phash": img_hash.phash,
                "dhash": img_hash.dhash,
                "ahash": img_hash.ahash,
                "features": img_hash.features.tolist()
            }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_cache(self, filepath: str):
        """加载哈希缓存"""
        path = Path(filepath)
        if not path.exists():
            return
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for path_str, hash_data in data.items():
            image_hash = ImageHash(
                path=hash_data["path"],
                phash=hash_data["phash"],
                dhash=hash_data["dhash"],
                ahash=hash_data["ahash"],
                features=np.array(hash_data["features"])
            )
            self._hash_cache[path_str] = image_hash


# 全局相似度检测器实例
similarity_detector = SimilarityDetector()
