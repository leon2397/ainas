"""
OCR 识别服务
支持 Tesseract（轻量级）和 PaddleOCR（高精度，可选）
引擎为可选依赖，缺少时降级提示
"""

from loguru import logger
from typing import Optional, List, Dict, Any
from pathlib import Path


class OCRService:
    """OCR 识别服务"""

    def __init__(self):
        self.engine = None
        self.engine_name = None
        self._init_engine()

    def _init_engine(self):
        """初始化 OCR 引擎（按优先级尝试）"""
        # 优先 PaddleOCR（高精度中文）
        try:
            from paddleocr import PaddleOCR
            self.engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
            self.engine_name = "paddleocr"
            logger.info("[OK] OCR Engine: PaddleOCR")
            return
        except ImportError:
            pass

        # 降级 Tesseract（轻量级）
        try:
            import pytesseract
            from PIL import Image
            self.engine = "tesseract"
            self.engine_name = "tesseract"
            logger.info("[OK] OCR Engine: Tesseract")
            return
        except ImportError:
            pass

        logger.info("[WARN] No OCR engine available. Install: pip install paddleocr OR pip install pytesseract")

    def is_available(self) -> bool:
        """检查 OCR 引擎是否可用"""
        return self.engine is not None

    def recognize(self, image_path: str, lang: str = None) -> Dict[str, Any]:
        """
        识别图片中的文字
        返回: { text: str, lines: List[{text, confidence}], engine: str }
        """
        if not self.is_available():
            return {"error": "OCR 引擎不可用，请安装 paddleocr 或 pytesseract", "text": "", "lines": []}

        if self.engine_name == "paddleocr":
            return self._recognize_paddle(image_path, lang)
        elif self.engine_name == "tesseract":
            return self._recognize_tesseract(image_path, lang)

        return {"error": "未知引擎", "text": "", "lines": []}

    def _recognize_paddle(self, image_path: str, lang: str = None) -> Dict:
        """PaddleOCR 识别"""
        try:
            result = self.engine.ocr(image_path, cls=True)
            lines = []
            full_text = []
            if result and result[0]:
                for line in result[0]:
                    text = line[1][0]
                    confidence = line[1][1]
                    lines.append({"text": text, "confidence": round(confidence, 3)})
                    full_text.append(text)
            return {
                "text": "\n".join(full_text),
                "lines": lines,
                "engine": "paddleocr",
                "line_count": len(lines)
            }
        except Exception as e:
            return {"error": str(e), "text": "", "lines": [], "engine": "paddleocr"}

    def _recognize_tesseract(self, image_path: str, lang: str = None) -> Dict:
        """Tesseract 识别"""
        from loguru import logger
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            lang_str = lang or "chi_sim+eng"  # 简体中文+英文
            text = pytesseract.image_to_string(img, lang=lang_str)
            # 逐行获取置信度
            data = pytesseract.image_to_data(img, lang=lang_str, output_type=pytesseract.Output.DICT)
            lines = []
            current_text = ""
            for i, t in enumerate(data["text"]):
                if t.strip():
                    current_text = t
                if data["block_num"][i] > 0 and current_text:
                    conf = data["conf"][i]
                    lines.append({"text": current_text, "confidence": round(conf / 100, 3) if conf >= 0 else 0})
            return {
                "text": text.strip(),
                "lines": lines,
                "engine": "tesseract",
                "line_count": len(lines)
            }
        except Exception as e:
            return {"error": str(e), "text": "", "lines": [], "engine": "tesseract"}


# 全局 OCR 服务实例
ocr_service = OCRService()