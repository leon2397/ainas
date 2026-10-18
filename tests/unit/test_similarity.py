"""
相似图片检测模块单元测试
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch
from PIL import Image
import io


class TestPerceptualHash:
    """感知哈希测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        return SimilarityDetector()
    
    def test_phash_calculation(self, detector):
        """测试pHash计算"""
        # 创建测试图像
        img = Image.new('RGB', (100, 100), color='red')
        
        hash_value = detector.calculate_phash(img)
        
        assert hash_value is not None
        assert isinstance(hash_value, str)
        assert len(hash_value) > 0
    
    def test_phash_consistency(self, detector):
        """测试pHash一致性"""
        img = Image.new('RGB', (100, 100), color='blue')
        
        hash1 = detector.calculate_phash(img)
        hash2 = detector.calculate_phash(img)
        
        assert hash1 == hash2
    
    def test_phash_similar_images(self, detector):
        """测试相似图像的pHash"""
        # 创建两张几乎相同的图像
        img1 = Image.new('RGB', (100, 100), color='green')
        img2 = Image.new('RGB', (100, 100), color='green')
        
        hash1 = detector.calculate_phash(img1)
        hash2 = detector.calculate_phash(img2)
        
        # 相同图像的哈希应该相同
        assert hash1 == hash2
    
    def test_phash_different_images(self, detector):
        """测试不同图像的pHash"""
        img1 = Image.new('RGB', (100, 100), color='red')
        img2 = Image.new('RGB', (100, 100), color='blue')
        
        hash1 = detector.calculate_phash(img1)
        hash2 = detector.calculate_phash(img2)
        
        # 不同图像的哈希应该不同
        assert hash1 != hash2


class TestAverageHash:
    """平均哈希测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        return SimilarityDetector()
    
    def test_ahash_calculation(self, detector):
        """测试aHash计算"""
        img = Image.new('RGB', (100, 100), color='white')
        
        hash_value = detector.calculate_ahash(img)
        
        assert hash_value is not None
        assert isinstance(hash_value, str)
    
    def test_ahash_fast_calculation(self, detector):
        """测试aHash快速计算"""
        img = Image.new('RGB', (1000, 1000), color='black')
        
        import time
        start = time.time()
        hash_value = detector.calculate_ahash(img)
        elapsed = time.time() - start
        
        assert hash_value is not None
        assert elapsed < 0.1  # 应该在100ms内完成


class TestDifferenceHash:
    """差值哈希测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        return SimilarityDetector()
    
    def test_dhash_calculation(self, detector):
        """测试dHash计算"""
        img = Image.new('RGB', (100, 100), color='gray')
        
        hash_value = detector.calculate_dhash(img)
        
        assert hash_value is not None
        assert isinstance(hash_value, str)
    
    def test_dhash_detects_gradients(self, detector):
        """测试dHash检测渐变"""
        # 创建渐变图像
        img = Image.new('RGB', (100, 100))
        pixels = img.load()
        for i in range(100):
            for j in range(100):
                pixels[i, j] = (i, i, i)  # 水平渐变
        
        hash_value = detector.calculate_dhash(img)
        
        assert hash_value is not None


class TestHashComparison:
    """哈希比较测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        return SimilarityDetector()
    
    def test_hamming_distance_identical(self, detector):
        """测试相同哈希的汉明距离"""
        hash1 = "aabbccdd"
        hash2 = "aabbccdd"
        
        distance = detector.hamming_distance(hash1, hash2)
        
        assert distance == 0
    
    def test_hamming_distance_completely_different(self, detector):
        """测试完全不同的哈希"""
        hash1 = "00000000"
        hash2 = "ffffffff"
        
        distance = detector.hamming_distance(hash1, hash2)
        
        assert distance == 32  # 32位完全不同
    
    def test_hamming_distance_similar(self, detector):
        """测试相似哈希的汉明距离"""
        hash1 = "aabbccdd"
        hash2 = "aabbccde"  # 只有最后一位不同
        
        distance = detector.hamming_distance(hash1, hash2)
        
        assert distance == 1
    
    def test_similarity_score_identical(self, detector):
        """测试相同图像的相似度分数"""
        img = Image.new('RGB', (100, 100), color='red')
        
        similarity = detector.calculate_similarity(img, img)
        
        assert similarity == 1.0
    
    def test_similarity_score_different(self, detector):
        """测试不同图像的相似度分数"""
        img1 = Image.new('RGB', (100, 100), color='red')
        img2 = Image.new('RGB', (100, 100), color='blue')
        
        similarity = detector.calculate_similarity(img1, img2)
        
        assert similarity < 0.5


class TestDuplicateDetection:
    """重复检测测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        detector = SimilarityDetector()
        detector.db = Mock()
        return detector
    
    def test_detect_exact_duplicate(self, detector):
        """测试检测完全重复"""
        img = Image.new('RGB', (100, 100), color='green')
        
        # 模拟数据库中没有重复
        detector.db.fetch_all = Mock(return_value=[])
        
        is_duplicate, similarity = detector.check_duplicate(img)
        
        assert is_duplicate is False
    
    def test_detect_near_duplicate(self, detector):
        """测试检测近似重复"""
        img = Image.new('RGB', (100, 100), color='yellow')
        
        # 模拟数据库中有非常相似的图片
        detector.db.fetch_all = Mock(return_value=[
            {"id": 1, "phash": detector.calculate_phash(img), "file_path": "/path/to/similar.jpg"}
        ])
        
        is_duplicate, similarity = detector.check_duplicate(img, threshold=0.95)
        
        assert is_duplicate is True
        assert similarity > 0.95
    
    def test_detect_not_duplicate(self, detector):
        """测试检测非重复"""
        img = Image.new('RGB', (100, 100), color='purple')
        
        # 模拟数据库中只有不同的图片
        detector.db.fetch_all = Mock(return_value=[
            {"id": 1, "phash": "aabbccdd", "file_path": "/path/to/different.jpg"}
        ])
        
        is_duplicate, similarity = detector.check_duplicate(img)
        
        assert is_duplicate is False


class TestBatchDuplicateDetection:
    """批量重复检测测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        detector = SimilarityDetector()
        detector.db = Mock()
        return detector
    
    def test_find_duplicates_in_batch(self, detector):
        """测试批量查找重复"""
        # 模拟数据库中的图片
        detector.db.fetch_all = Mock(return_value=[
            {"id": 1, "phash": "hash1", "file_path": "/path/1.jpg"},
            {"id": 2, "phash": "hash2", "file_path": "/path/2.jpg"},
            {"id": 3, "phash": "hash1", "file_path": "/path/3.jpg"}  # 与id=1重复
        ])
        
        duplicates = detector.find_duplicates()
        
        # 应该找到一对重复
        assert len(duplicates) >= 1
    
    def test_find_duplicates_by_hash(self, detector):
        """测试按哈希查找重复"""
        target_hash = "aabbccdd"
        
        detector.db.fetch_all = Mock(return_value=[
            {"id": 1, "phash": target_hash, "file_path": "/path/dup1.jpg"},
            {"id": 2, "phash": target_hash, "file_path": "/path/dup2.jpg"}
        ])
        
        duplicates = detector.find_duplicates_by_hash(target_hash)
        
        assert len(duplicates) == 2
    
    def test_find_similar_images(self, detector):
        """测试查找相似图片"""
        img = Image.new('RGB', (100, 100), color='orange')
        target_hash = detector.calculate_phash(img)
        
        # 模拟有相似图片
        detector.db.fetch_all = Mock(return_value=[
            {"id": 1, "phash": target_hash, "file_path": "/path/similar1.jpg", "similarity": 0.95},
            {"id": 2, "phash": "aabbccde", "file_path": "/path/similar2.jpg", "similarity": 0.90}
        ])
        
        similar = detector.find_similar_images(img, threshold=0.85, limit=10)
        
        assert len(similar) == 2
        assert all(s["similarity"] >= 0.85 for s in similar)


class TestFeatureVectorSimilarity:
    """特征向量相似度测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        detector = SimilarityDetector()
        detector.feature_extractor = Mock()
        return detector
    
    def test_extract_features(self, detector):
        """测试特征提取"""
        detector.feature_extractor.extract.return_value = np.array([0.1, 0.2, 0.3, 0.4])
        
        img = Image.new('RGB', (100, 100))
        features = detector.extract_features(img)
        
        assert features is not None
        assert len(features) == 4
    
    def test_cosine_similarity_identical(self, detector):
        """测试相同向量的余弦相似度"""
        vec1 = np.array([1.0, 2.0, 3.0])
        vec2 = np.array([1.0, 2.0, 3.0])
        
        similarity = detector.cosine_similarity(vec1, vec2)
        
        assert abs(similarity - 1.0) < 0.001
    
    def test_cosine_similarity_orthogonal(self, detector):
        """测试正交向量的余弦相似度"""
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        
        similarity = detector.cosine_similarity(vec1, vec2)
        
        assert abs(similarity - 0.0) < 0.001
    
    def test_euclidean_distance_similarity(self, detector):
        """测试欧氏距离相似度"""
        vec1 = np.array([0.0, 0.0])
        vec2 = np.array([3.0, 4.0])
        
        distance = detector.euclidean_distance(vec1, vec2)
        
        assert abs(distance - 5.0) < 0.001


class TestImagePreprocessing:
    """图像预处理测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        return SimilarityDetector()
    
    def test_resize_image(self, detector):
        """测试图像缩放"""
        img = Image.new('RGB', (1000, 800), color='red')
        
        resized = detector.resize_image(img, target_size=(100, 100))
        
        assert resized.size == (100, 100)
    
    def test_convert_to_grayscale(self, detector):
        """测试转换为灰度"""
        img = Image.new('RGB', (100, 100), color='red')
        
        gray = detector.convert_to_grayscale(img)
        
        assert gray.mode == 'L'
    
    def test_normalize_image(self, detector):
        """测试图像归一化"""
        img_array = np.array([[0, 128, 255]], dtype=np.uint8)
        
        normalized = detector.normalize_image(img_array)
        
        assert normalized.min() >= 0.0
        assert normalized.max() <= 1.0


class TestSimilarityDatabase:
    """相似度数据库测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        detector = SimilarityDetector()
        detector.db = Mock()
        return detector
    
    def test_save_image_hash(self, detector):
        """测试保存图像哈希"""
        detector.db.execute = Mock(return_value=None)
        
        result = detector.save_hash(
            media_id=1,
            phash="aabbccdd",
            ahash="11223344",
            dhash="55667788"
        )
        
        assert result is True
    
    def test_get_image_hash(self, detector):
        """测试获取图像哈希"""
        detector.db.fetch_one = Mock(return_value={
            "media_id": 1,
            "phash": "aabbccdd",
            "ahash": "11223344",
            "dhash": "55667788"
        })
        
        hash_data = detector.get_hash(media_id=1)
        
        assert hash_data is not None
        assert hash_data["phash"] == "aabbccdd"
    
    def test_delete_image_hash(self, detector):
        """测试删除图像哈希"""
        detector.db.execute = Mock(return_value=None)
        
        result = detector.delete_hash(media_id=1)
        
        assert result is True
    
    def test_get_all_hashes(self, detector):
        """测试获取所有哈希"""
        detector.db.fetch_all = Mock(return_value=[
            {"media_id": 1, "phash": "hash1"},
            {"media_id": 2, "phash": "hash2"}
        ])
        
        hashes = detector.get_all_hashes()
        
        assert len(hashes) == 2


class TestSimilarityReport:
    """相似度报告测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        detector = SimilarityDetector()
        detector.db = Mock()
        return detector
    
    def test_generate_similarity_report(self, detector):
        """测试生成相似度报告"""
        detector.db.fetch_all = Mock(return_value=[
            {"id": 1, "phash": "hash1"},
            {"id": 2, "phash": "hash1"},  # 重复
            {"id": 3, "phash": "hash2"}
        ])
        
        report = detector.generate_similarity_report()
        
        assert "total_images" in report
        assert "duplicate_groups" in report
        assert "storage_wasted" in report
    
    def test_get_duplicate_statistics(self, detector):
        """测试获取重复统计"""
        detector.db.fetch_all = Mock(return_value=[
            {"phash": "hash1", "count": 3},
            {"phash": "hash2", "count": 2}
        ])
        
        stats = detector.get_duplicate_statistics()
        
        assert stats["total_duplicates"] == 5
        assert stats["duplicate_groups"] == 2


class TestSimilarityAPI:
    """相似度API测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        detector = SimilarityDetector()
        detector.db = Mock()
        return detector
    
    def test_check_similarity_api(self, detector):
        """测试相似度检查API"""
        img1 = Image.new('RGB', (100, 100), color='red')
        img2 = Image.new('RGB', (100, 100), color='red')
        
        result = detector.check_similarity(img1, img2)
        
        assert "similarity" in result
        assert "is_duplicate" in result
        assert "hash1" in result
        assert "hash2" in result
    
    def test_find_duplicates_api(self, detector):
        """测试查找重复API"""
        detector.db.fetch_all = Mock(return_value=[])
        
        result = detector.find_duplicates_api(threshold=0.95)
        
        assert "duplicates" in result
        assert "total_checked" in result
    
    def test_merge_duplicates_api(self, detector):
        """测试合并重复API"""
        detector.db.execute = Mock(return_value=None)
        
        result = detector.merge_duplicates(keep_id=1, remove_ids=[2, 3])
        
        assert result["success"] is True
        assert result["merged_count"] == 2


class TestPerformance:
    """性能测试"""
    
    @pytest.fixture
    def detector(self):
        """创建相似检测器实例"""
        from ai.similarity.detector import SimilarityDetector
        return SimilarityDetector()
    
    def test_hash_calculation_performance(self, detector):
        """测试哈希计算性能"""
        import time
        
        img = Image.new('RGB', (1000, 1000), color='white')
        
        start = time.time()
        for _ in range(100):
            detector.calculate_phash(img)
        elapsed = time.time() - start
        
        # 100张图片应该在1秒内完成
        assert elapsed < 1.0
    
    def test_batch_similarity_performance(self, detector):
        """测试批量相似度检测性能"""
        import time
        
        img = Image.new('RGB', (100, 100), color='black')
        images = [img] * 50
        
        start = time.time()
        detector.batch_check_duplicates(images)
        elapsed = time.time() - start
        
        # 50张图片应该在2秒内完成
        assert elapsed < 2.0
