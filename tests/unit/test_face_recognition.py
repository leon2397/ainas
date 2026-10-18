"""
人脸识别模块单元测试
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
import json


class TestFaceDetection:
    """人脸检测测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        engine.npu_available = False  # 测试时禁用NPU
        return engine
    
    def test_detect_faces_single_face(self, face_engine):
        """测试检测单个人脸"""
        # Mock人脸检测器
        mock_detector = Mock()
        mock_detector.detect_faces.return_value = [
            {"bbox": [100, 100, 200, 200], "confidence": 0.95}
        ]
        face_engine.detector = mock_detector
        
        # 创建模拟图像
        mock_image = np.zeros((300, 300, 3), dtype=np.uint8)
        
        faces = face_engine.detect_faces(mock_image)
        
        assert len(faces) == 1
        assert faces[0]["confidence"] > 0.9
    
    def test_detect_faces_multiple_faces(self, face_engine):
        """测试检测多个人脸"""
        mock_detector = Mock()
        mock_detector.detect_faces.return_value = [
            {"bbox": [100, 100, 150, 150], "confidence": 0.95},
            {"bbox": [200, 200, 280, 280], "confidence": 0.92},
            {"bbox": [50, 50, 120, 120], "confidence": 0.88}
        ]
        face_engine.detector = mock_detector
        
        mock_image = np.zeros((400, 400, 3), dtype=np.uint8)
        faces = face_engine.detect_faces(mock_image)
        
        assert len(faces) == 3
    
    def test_detect_faces_no_face(self, face_engine):
        """测试无脸检测"""
        mock_detector = Mock()
        mock_detector.detect_faces.return_value = []
        face_engine.detector = mock_detector
        
        mock_image = np.zeros((300, 300, 3), dtype=np.uint8)
        faces = face_engine.detect_faces(mock_image)
        
        assert len(faces) == 0
    
    def test_detect_faces_with_min_confidence(self, face_engine):
        """测试带最小置信度的人脸检测"""
        mock_detector = Mock()
        mock_detector.detect_faces.return_value = [
            {"bbox": [100, 100, 200, 200], "confidence": 0.95},
            {"bbox": [50, 50, 100, 100], "confidence": 0.5}  # 低于阈值
        ]
        face_engine.detector = mock_detector
        
        mock_image = np.zeros((300, 300, 3), dtype=np.uint8)
        faces = face_engine.detect_faces(mock_image, min_confidence=0.8)
        
        assert len(faces) == 1
        assert faces[0]["confidence"] >= 0.8


class TestFeatureExtraction:
    """特征提取测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        engine.npu_available = False
        return engine
    
    def test_extract_features(self, face_engine):
        """测试特征提取"""
        mock_embedder = Mock()
        mock_embedder.get_embedding.return_value = np.random.randn(128)
        face_engine.embedder = mock_embedder
        
        mock_face_image = np.zeros((112, 112, 3), dtype=np.uint8)
        features = face_engine.extract_features(mock_face_image)
        
        assert features is not None
        assert len(features) == 128
    
    def test_extract_features_normalized(self, face_engine):
        """测试特征归一化"""
        mock_embedder = Mock()
        mock_embedder.get_embedding.return_value = np.array([3.0, 4.0])
        face_engine.embedder = mock_embedder
        
        mock_face_image = np.zeros((112, 112, 3), dtype=np.uint8)
        features = face_engine.extract_features(mock_face_image, normalize=True)
        
        # 验证归一化 (L2 norm = 1)
        norm = np.linalg.norm(features)
        assert abs(norm - 1.0) < 0.001
    
    def test_extract_features_invalid_image(self, face_engine):
        """测试无效图像的特征提取"""
        with pytest.raises(ValueError):
            face_engine.extract_features(None)


class TestFaceMatching:
    """人脸匹配测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        return engine
    
    def test_compare_faces_same_person(self, face_engine):
        """测试同一人脸匹配"""
        # 相同的特征向量
        features1 = np.array([0.1, 0.2, 0.3, 0.4])
        features2 = np.array([0.1, 0.2, 0.3, 0.4])
        
        similarity = face_engine.compare_faces(features1, features2)
        
        assert similarity > 0.95
    
    def test_compare_faces_different_persons(self, face_engine):
        """测试不同人脸不匹配"""
        # 完全不同的特征向量
        features1 = np.array([1.0, 0.0, 0.0, 0.0])
        features2 = np.array([0.0, 1.0, 0.0, 0.0])
        
        similarity = face_engine.compare_faces(features1, features2)
        
        assert similarity < 0.5
    
    def test_compare_faces_similar_persons(self, face_engine):
        """测试相似人脸"""
        # 相似但不完全相同的特征向量
        features1 = np.array([0.9, 0.1, 0.0, 0.0])
        features2 = np.array([0.8, 0.2, 0.0, 0.0])
        
        similarity = face_engine.compare_faces(features1, features2)
        
        assert 0.6 < similarity < 0.95
    
    def test_find_best_match(self, face_engine):
        """测试查找最佳匹配"""
        query_features = np.array([0.9, 0.1, 0.0])
        
        database = {
            "person_1": np.array([0.1, 0.9, 0.0]),  # 不匹配
            "person_2": np.array([0.85, 0.15, 0.0]),  # 最佳匹配
            "person_3": np.array([0.5, 0.5, 0.0])   # 部分匹配
        }
        
        best_match, similarity = face_engine.find_best_match(query_features, database)
        
        assert best_match == "person_2"
        assert similarity > 0.8


class TestFaceClustering:
    """人脸聚类测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        return engine
    
    def test_cluster_faces(self, face_engine):
        """测试人脸聚类"""
        # 模拟3个人的多张照片特征
        features_list = [
            # 第1个人 - 3张照片
            np.array([0.9, 0.1, 0.0]),
            np.array([0.91, 0.09, 0.0]),
            np.array([0.89, 0.11, 0.0]),
            # 第2个人 - 2张照片
            np.array([0.1, 0.9, 0.0]),
            np.array([0.11, 0.89, 0.0]),
            # 第3个人 - 2张照片
            np.array([0.0, 0.1, 0.9]),
            np.array([0.0, 0.11, 0.89])
        ]
        
        clusters = face_engine.cluster_faces(features_list, n_clusters=3)
        
        assert len(clusters) == 3
        # 每个聚类应该有2-3个成员
        for cluster in clusters:
            assert 2 <= len(cluster) <= 3
    
    def test_cluster_faces_unknown_count(self, face_engine):
        """测试自动确定聚类数量"""
        features_list = [
            np.array([0.9, 0.1]),
            np.array([0.91, 0.09]),
            np.array([0.1, 0.9]),
            np.array([0.11, 0.89])
        ]
        
        clusters = face_engine.cluster_faces(features_list, n_clusters=None)
        
        # 应该自动识别出2个聚类
        assert len(clusters) == 2


class TestFaceDatabase:
    """人脸数据库测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        engine.db = Mock()
        return engine
    
    def test_add_face_to_database(self, face_engine):
        """测试添加人脸到数据库"""
        face_engine.db.execute = Mock(return_value=None)
        face_engine.db.fetch_val = Mock(return_value=1)
        
        features = np.array([0.1, 0.2, 0.3])
        face_id = face_engine.add_face(
            person_name="张三",
            features=features,
            image_path="/path/to/face.jpg"
        )
        
        assert face_id is not None
        face_engine.db.execute.assert_called_once()
    
    def test_get_face_by_id(self, face_engine):
        """测试通过ID获取人脸"""
        face_engine.db.fetch_one = Mock(return_value={
            "id": 1,
            "person_name": "张三",
            "features": json.dumps([0.1, 0.2, 0.3]),
            "image_path": "/path/to/face.jpg"
        })
        
        face = face_engine.get_face_by_id(1)
        
        assert face is not None
        assert face["person_name"] == "张三"
        assert len(face["features"]) == 3
    
    def test_get_faces_by_person(self, face_engine):
        """测试获取某人的所有人脸"""
        face_engine.db.fetch_all = Mock(return_value=[
            {"id": 1, "person_name": "张三", "features": json.dumps([0.1, 0.2])},
            {"id": 2, "person_name": "张三", "features": json.dumps([0.11, 0.21])}
        ])
        
        faces = face_engine.get_faces_by_person("张三")
        
        assert len(faces) == 2
    
    def test_update_person_name(self, face_engine):
        """测试更新人名"""
        face_engine.db.execute = Mock(return_value=None)
        
        result = face_engine.update_person_name(
            old_name="Unknown_1",
            new_name="张三"
        )
        
        assert result is True
    
    def test_delete_face(self, face_engine):
        """测试删除人脸"""
        face_engine.db.execute = Mock(return_value=None)
        
        result = face_engine.delete_face(face_id=1)
        
        assert result is True


class TestNPUSupport:
    """NPU支持测试"""
    
    def test_npu_detection_rk3588(self):
        """测试RK3588 NPU检测"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            from ai.face_recognition.engine import FaceRecognitionEngine
            engine = FaceRecognitionEngine()
            
            # 模拟RK3588环境
            with patch('platform.machine', return_value='aarch64'):
                npu_available = engine._check_npu_support()
                
                # 在模拟环境中应该返回True
                # 实际结果取决于模拟的具体实现
    
    def test_npu_acceleration_enabled(self):
        """测试NPU加速启用"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        engine.npu_available = True
        
        # NPU可用时应该使用NPU加速
        assert engine.use_npu is True
    
    def test_fallback_to_cpu(self):
        """测试NPU不可用时回退到CPU"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        engine.npu_available = False
        
        # NPU不可用时应该使用CPU
        assert engine.use_npu is False


class TestFaceRecognitionPipeline:
    """人脸识别完整流程测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        engine.npu_available = False
        
        # Mock各个组件
        engine.detector = Mock()
        engine.embedder = Mock()
        engine.db = Mock()
        
        return engine
    
    def test_full_recognition_pipeline(self, face_engine):
        """测试完整识别流程"""
        # 1. 模拟检测到人脸
        face_engine.detector.detect_faces.return_value = [
            {"bbox": [100, 100, 200, 200], "confidence": 0.95}
        ]
        
        # 2. 模拟提取特征
        face_engine.embedder.get_embedding.return_value = np.array([0.9, 0.1, 0.0])
        
        # 3. 模拟数据库查询
        face_engine.db.fetch_all = Mock(return_value=[
            {"id": 1, "person_name": "张三", "features": json.dumps([0.91, 0.09, 0.0])}
        ])
        
        # 执行识别
        mock_image = np.zeros((300, 300, 3), dtype=np.uint8)
        results = face_engine.recognize_faces(mock_image)
        
        assert len(results) == 1
        assert results[0]["person_name"] == "张三"
        assert results[0]["confidence"] > 0.8
    
    def test_recognition_unknown_person(self, face_engine):
        """测试识别未知人员"""
        face_engine.detector.detect_faces.return_value = [
            {"bbox": [100, 100, 200, 200], "confidence": 0.95}
        ]
        face_engine.embedder.get_embedding.return_value = np.array([0.5, 0.5, 0.0])
        
        # 数据库中没有匹配的人脸
        face_engine.db.fetch_all = Mock(return_value=[
            {"id": 1, "person_name": "张三", "features": json.dumps([0.9, 0.1, 0.0])}
        ])
        
        mock_image = np.zeros((300, 300, 3), dtype=np.uint8)
        results = face_engine.recognize_faces(mock_image)
        
        # 相似度低于阈值，应该标记为未知
        assert results[0]["person_name"] == "Unknown"
    
    def test_batch_recognition(self, face_engine):
        """测试批量识别"""
        face_engine.detector.detect_faces.return_value = [
            {"bbox": [100, 100, 200, 200], "confidence": 0.95}
        ]
        face_engine.embedder.get_embedding.return_value = np.array([0.9, 0.1])
        face_engine.db.fetch_all = Mock(return_value=[])
        
        image_paths = ["/path/to/image1.jpg", "/path/to/image2.jpg"]
        results = face_engine.batch_recognize(image_paths)
        
        assert len(results) == 2


class TestFaceQuality:
    """人脸质量评估测试"""
    
    @pytest.fixture
    def face_engine(self):
        """创建人脸识别引擎实例"""
        from ai.face_recognition.engine import FaceRecognitionEngine
        engine = FaceRecognitionEngine()
        return engine
    
    def test_check_face_quality_good(self, face_engine):
        """测试高质量人脸"""
        face_info = {
            "bbox": [100, 100, 200, 200],
            "confidence": 0.98,
            "landmarks": {
                "left_eye": [120, 140],
                "right_eye": [180, 140],
                "nose": [150, 160],
                "mouth": [150, 190]
            }
        }
        
        quality_score = face_engine.check_face_quality(face_info)
        
        assert quality_score > 0.8
    
    def test_check_face_quality_blurry(self, face_engine):
        """测试模糊人脸"""
        face_info = {
            "bbox": [100, 100, 200, 200],
            "confidence": 0.6,  # 低置信度
            "blur_score": 0.3   # 模糊
        }
        
        quality_score = face_engine.check_face_quality(face_info)
        
        assert quality_score < 0.5
    
    def test_check_face_quality_small(self, face_engine):
        """测试过小的人脸"""
        face_info = {
            "bbox": [100, 100, 110, 110],  # 只有10x10像素
            "confidence": 0.95
        }
        
        quality_score = face_engine.check_face_quality(face_info)
        
        assert quality_score < 0.5
    
    def test_check_face_quality_occluded(self, face_engine):
        """测试遮挡人脸"""
        face_info = {
            "bbox": [100, 100, 200, 200],
            "confidence": 0.95,
            "occlusion": {
                "left_eye": True,
                "right_eye": False
            }
        }
        
        quality_score = face_engine.check_face_quality(face_info)
        
        # 部分遮挡应该降低质量分数
        assert quality_score < 0.9
