"""
CPU AI Engine Plugin
使用 ONNX Runtime 进行 CPU 推理（无 GPU 要求）
优先加载本地 .onnx 模型；本地不存在则自动下载 MobileNetV2
回退策略：ONNX → heuristic 颜色分类
"""

import os
import numpy as np
from typing import Dict, List, Any
from pathlib import Path
from PIL import Image

from modules.mod_ai.base import AIEngine
from core.logger import logger

# ONNX Model Zoo MobileNetV2 下载地址（首次运行自动下载，约 14MB）
_MOBILENETV2_URL = (
    "https://github.com/onnx/models/raw/main/vision/classification/mobilenet/model/mobilenetv2-7.onnx"
)
_IMAGENET_LABELS_URL = (
    "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
)


class CPUEngine(AIEngine):
    """CPU-based AI inference engine using ONNX Runtime"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # 从 YAML 配置读取
        self.model_path = config.get('model_path', 'models/mobilenetv2-7.onnx')
        self.input_size = tuple(config.get('input_size', [224, 224]))
        self.threshold = config.get('threshold', 0.3)
        self.batch_size = config.get('batch_size', 8)

        self._ort_session: Any = None
        self._input_name: str = ""
        self._output_name: str = ""
        self._labels: List[str] = []
        self._mode: str = "unknown"   # "onnx" | "heuristic"
        self._initialized: bool = False

    # ─── 初始化 ────────────────────────────────────────────────────────────

    def _initialize(self):
        if self._initialized:
            return

        # 策略1：本地 ONNX 模型
        if self._try_load_local_onnx():
            self._mode = "onnx"
            self._initialized = True
            return

        # 策略2：自动下载 MobileNetV2
        if self._try_download_mobilenetv2():
            self._mode = "onnx"
            self._initialized = True
            return

        # 策略3：降级到 heuristic
        self._mode = "heuristic"
        self._initialized = True
        logger.warning("[CPUEngine] No ONNX model available, using heuristic classification")

    def _try_load_local_onnx(self) -> bool:
        """尝试加载本地 ONNX 模型"""
        try:
            import onnxruntime as ort
        except ImportError:
            logger.debug("[CPUEngine] onnxruntime not installed")
            return False

        if not os.path.exists(self.model_path):
            logger.debug(f"[CPUEngine] Model not found: {self.model_path}")
            return False

        try:
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._ort_session = ort.InferenceSession(self.model_path, sess_options)
            self._input_name = self._ort_session.get_inputs()[0].name
            self._output_name = self._ort_session.get_outputs()[0].name
            self._load_imagenet_labels()
            logger.info(f"[CPUEngine] Loaded ONNX model: {self.model_path}")
            return True
        except Exception as e:
            logger.warning(f"[CPUEngine] Failed to load ONNX model {self.model_path}: {e}")
            return False

    def _get_model_dir(self) -> Path:
        """获取模型缓存目录"""
        base = Path.home() / ".cache" / "ai-nas"
        base.mkdir(parents=True, exist_ok=True)
        return base

    def _try_download_mobilenetv2(self) -> bool:
        """自动下载 MobileNetV2 ONNX 模型"""
        cached_path = self._get_model_dir() / "mobilenetv2-7.onnx"
        if cached_path.exists():
            # 缓存命中，复制到工作目录
            dest = Path(self.model_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists():
                import shutil
                shutil.copy2(cached_path, dest)
            return self._try_load_local_onnx()

        logger.info("[CPUEngine] Downloading MobileNetV2 ONNX model (~14MB)...")
        model_dir = Path(self.model_path).parent
        model_dir.mkdir(parents=True, exist_ok=True)

        try:
            import urllib.request
            urllib.request.urlretrieve(_MOBILENETV2_URL, str(cached_path))
            logger.info(f"[CPUEngine] MobileNetV2 downloaded to {cached_path}")
            # 复制到工作目录
            import shutil
            shutil.copy2(cached_path, self.model_path)
            self._load_imagenet_labels()
            return self._try_load_local_onnx()
        except Exception as e:
            logger.warning(f"[CPUEngine] Failed to download MobileNetV2: {e}")
            return False

    def _load_imagenet_labels(self):
        """加载 ImageNet 标签列表"""
        labels_path = self._get_model_dir() / "imagenet_classes.txt"
        if labels_path.exists():
            with open(labels_path, "r", encoding="utf-8") as f:
                self._labels = [line.strip() for line in f]
            return

        try:
            import urllib.request
            urllib.request.urlretrieve(_IMAGENET_LABELS_URL, str(labels_path))
            with open(labels_path, "r", encoding="utf-8") as f:
                self._labels = [line.strip() for line in f]
            logger.info("[CPUEngine] ImageNet labels loaded")
        except Exception as e:
            logger.debug(f"[CPUEngine] Failed to load ImageNet labels: {e}")
            self._labels = []

    # ─── 图像分类 ──────────────────────────────────────────────────────────

    def image_predict(self, filepath: str) -> Dict[str, Any]:
        """
        图像 AI 推理
        Returns: {"tags": [...], "feature": [...], "confidence": float}
        """
        self._initialize()

        try:
            img = Image.open(filepath).convert("RGB")

            if self._mode == "onnx":
                return self._onnx_predict(img, filepath)
            else:
                return self._heuristic_predict(img, filepath)

        except Exception as e:
            logger.error(f"[CPUEngine] image_predict error for {filepath}: {e}")
            return {"tags": ["error"], "feature": [], "confidence": 0.0, "error": str(e)}

    def _onnx_predict(self, img: Image.Image, filepath: str) -> Dict[str, Any]:
        """使用 ONNX MobileNetV2 推理"""
        # 预处理：resize + center crop + 归一化
        w, h = img.size
        size = self.input_size[0]
        # Center crop
        left = (w - size) // 2
        top = (h - size) // 2
        img_crop = img.crop((left, top, left + size, top + size))
        img_crop = img_crop.resize((size, size), Image.Resampling.LANCZOS)

        # ImageNet 标准化
        img_np = np.array(img_crop, dtype=np.float32)
        img_np = img_np / 255.0
        # Normalize: mean=[0.485,0.456,0.406], std=[0.229,0.224,0.225]
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        img_np = (img_np - mean) / std
        # HWC -> CHW
        img_np = np.transpose(img_np, (2, 0, 1))
        img_np = np.expand_dims(img_np, axis=0)

        # 推理
        output = self._ort_session.run(
            [self._output_name],
            {self._input_name: img_np.astype(np.float32)}
        )[0][0]  # softmax 输出

        # 取 Top-5
        probs = self._softmax(output)
        top_indices = np.argsort(probs)[-5:][::-1]

        tags = []
        for idx in top_indices:
            p = float(probs[idx])
            if p < self.threshold:
                continue
            label = self._labels[idx] if idx < len(self._labels) else f"class_{idx}"
            tags.append(label)

        confidence = float(probs[top_indices[0]]) if len(top_indices) > 0 else 0.0
        feature = self._extract_histogram_feature(img)

        return {
            "tags": tags[:5],
            "feature": feature,
            "confidence": confidence,
            "model": "MobileNetV2-ONNX",
        }

    def _heuristic_predict(self, img: Image.Image, filepath: str) -> Dict[str, Any]:
        """基于颜色/内容的启发式分类（无模型时使用）"""
        tags = []
        filename = os.path.basename(filepath).lower()

        # 文件名模式
        if any(x in filename for x in ["screen", "screenshot", "截图"]):
            tags.append("screenshot")
        elif any(x in filename for x in ["photo", "img", "pic", "dsc", "img_"]):
            tags.append("photo")
        elif any(x in filename for x in ["video", "vid", "mov", "avi", "mp4"]):
            tags.append("video")

        # 宽高比
        w, h = img.size
        ar = w / max(h, 1)
        if ar > 1.8:
            tags.append("panorama")
        elif ar < 0.6:
            tags.append("portrait")
        elif ar > 1.3:
            tags.append("landscape")

        # 主导色
        img_small = img.resize((50, 50))
        pixels = np.array(img_small).reshape(-1, 3)
        avg = pixels.mean(axis=0)
        r, g, b = avg[0], avg[1], avg[2]
        if r > g + 30 and r > b + 30:
            tags.append("warm_tone")
        elif b > r + 30 and b > g + 30:
            tags.append("cool_tone")
        elif g > r + 20 and g > b + 20:
            tags.append("nature_green")

        brightness = avg.mean()
        if brightness > 200:
            tags.append("bright")
        elif brightness < 70:
            tags.append("dark_scene")

        # 格式标签
        ext = Path(filepath).suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp"}:
            tags.append("image")
        elif ext in {".heic", ".heif"}:
            tags.append("image")
        elif ext in {".raw", ".cr2", ".nef", ".arw", ".dng"}:
            tags.append("raw_photo")
        elif ext in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
            tags.append("video")

        return {
            "tags": list(set(tags))[:5],
            "feature": self._extract_histogram_feature(img),
            "confidence": 0.6,
            "model": "heuristic",
        }

    def _extract_histogram_feature(self, img: Image.Image) -> List[float]:
        """提取颜色直方图特征向量（用于相似图检测）"""
        img_h = img.resize((64, 64))
        arr = np.array(img_h, dtype=np.float32)

        hist_r = np.histogram(arr[:, :, 0], bins=16, range=(0, 256))[0]
        hist_g = np.histogram(arr[:, :, 1], bins=16, range=(0, 256))[0]
        hist_b = np.histogram(arr[:, :, 2], bins=16, range=(0, 256))[0]

        hist_r = hist_r / (hist_r.sum() + 1e-8)
        hist_g = hist_g / (hist_g.sum() + 1e-8)
        hist_b = hist_b / (hist_b.sum() + 1e-8)

        return np.concatenate([hist_r, hist_g, hist_b]).tolist()

    @staticmethod
    def _softmax(x: np.ndarray) -> np.ndarray:
        e = np.exp(x - x.max())
        return e / e.sum()

    # ─── 视频推理 ──────────────────────────────────────────────────────────

    def video_predict(self, filepath: str) -> Dict[str, Any]:
        """视频推理：采样关键帧"""
        self._initialize()

        try:
            import cv2

            cap = cv2.VideoCapture(filepath)
            if not cap.isOpened():
                logger.warning(f"[CPUEngine] Cannot open video: {filepath}")
                return {"tags": ["video"], "audio_tags": [], "duration": 0, "feature": [], "error": "cannot open"}

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / max(fps, 1)

            # 每 5 秒采样一帧，最多 10 帧
            interval = max(1, int(duration / 5))
            frame_idx = 0
            frame_tags: List[str] = []
            features: List[List[float]] = []

            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx % interval == 0:
                    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                    result = self.image_predict_from_array(img)
                    frame_tags.extend(result.get("tags", []))
                    feat = result.get("feature", [])
                    if feat:
                        features.append(feat)
                frame_idx += 1

            cap.release()

            # 聚合：取出现最多的标签
            from collections import Counter
            tag_counts = Counter(frame_tags)
            top_tags = [t for t, _ in tag_counts.most_common(5)]

            avg_feature = np.mean(features, axis=0).tolist() if features else []

            return {
                "tags": top_tags or ["video"],
                "audio_tags": [],
                "duration": round(duration, 1),
                "feature": avg_feature,
                "frames_sampled": len(features),
            }

        except Exception as e:
            logger.error(f"[CPUEngine] video_predict error for {filepath}: {e}")
            return {"tags": ["video"], "audio_tags": [], "duration": 0, "feature": [], "error": str(e)}

    def image_predict_from_array(self, img: Image.Image) -> Dict[str, Any]:
        """从 PIL Image 数组推理"""
        self._initialize()
        try:
            if self._mode == "onnx":
                return self._onnx_predict(img, "")
            else:
                return self._heuristic_predict(img, "")
        except Exception as e:
            logger.debug(f"[CPUEngine] image_predict_from_array error: {e}")
            return {"tags": ["error"], "feature": [], "confidence": 0.0}

    # ─── 人脸检测 ──────────────────────────────────────────────────────────

    def face_detect(self, filepath: str) -> Dict[str, Any]:
        """人脸检测：使用 OpenCV Haar Cascade"""
        try:
            import cv2

            img_cv = cv2.imread(filepath)
            if img_cv is None:
                img_pil = Image.open(filepath).convert("RGB")
                arr = np.array(img_pil)
                img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            face_cascade = cv2.CascadeClassifier(cascade_path)

            faces = face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(40, 40),
            )

            result = []
            embeddings = []

            for x, y, w, h in faces:
                result.append({"x": int(x), "y": int(y), "width": int(w), "height": int(h)})
                # 简单颜色直方图作为人脸 embedding
                face_roi = img_cv[y:y+h, x:x+w]
                face_img = Image.fromarray(cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB))
                embeddings.append(self._extract_histogram_feature(face_img))

            logger.debug(f"[CPUEngine] face_detect: {len(result)} faces in {filepath}")
            return {"faces": result, "embeddings": embeddings, "count": len(result)}

        except Exception as e:
            logger.error(f"[CPUEngine] face_detect error for {filepath}: {e}")
            return {"faces": [], "embeddings": [], "count": 0, "error": str(e)}

    # ─── 相似图去重 ────────────────────────────────────────────────────────

    def deduplicate(self, feature: List[float], threshold: float = 0.8) -> List[str]:
        """相似图检测（返回相似文件路径）"""
        # 由外部 ChromaDB / vector_db.py 调用
        return []


def create_engine(config: Dict) -> CPUEngine:
    return CPUEngine(config)
