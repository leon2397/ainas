"""
OCR 识别路由
提供图片文字识别接口
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from core.auth import get_current_user, require_editor
from services.ocr_service import ocr_service

router = APIRouter(prefix="/api/ocr", tags=["OCR识别"])


class OCRRequest(BaseModel):
    file_path: str  # 本地文件路径
    lang: Optional[str] = None  # 语言，如 "chi_sim+eng"


@router.post("/recognize")
async def recognize_image(request: OCRRequest, current_user: dict = Depends(get_current_user)):
    """识别图片中的文字"""
    if not ocr_service.is_available():
        raise HTTPException(status_code=400, detail="OCR 引擎不可用。安装: pip install paddleocr 或 pip install pytesseract")
    result = ocr_service.recognize(request.file_path, request.lang)
    if "error" in result and result["error"]:
        raise HTTPException(status_code=500, detail=result["error"])
    return result


@router.post("/media/{file_id}")
async def recognize_media(file_id: int, current_user: dict = Depends(get_current_user)):
    """识别媒体文件中的文字"""
    from database.db import db
    media = await db.fetchone("SELECT * FROM media_files WHERE id = ?", (file_id,))
    if not media:
        raise HTTPException(status_code=404, detail="文件不存在")

    file_path = media.get("original_path") or media.get("file_path")
    if not file_path:
        raise HTTPException(status_code=400, detail="文件路径为空")

    import os
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail="文件不存在于本地: " + file_path)

    if not ocr_service.is_available():
        raise HTTPException(status_code=400, detail="OCR 引擎不可用。安装: pip install paddleocr 或 pip install pytesseract")

    result = ocr_service.recognize(file_path)
    if "error" in result and result["error"]:
        raise HTTPException(status_code=500, detail=result["error"])

    # 将识别结果存入 tags（前100字符作为摘要标签）
    if result.get("text"):
        import json
        summary = result["text"][:100].replace("\n", " ").strip()
        if summary:
            existing_tags = media.get("tags")
            if existing_tags:
                try:
                    tags = json.loads(existing_tags) if isinstance(existing_tags, str) else existing_tags
                except Exception:
                    tags = []
            else:
                tags = []
            if "OCR" not in tags:
                tags.append("OCR")
            if summary not in tags:
                tags.append(summary)
            await db.execute(
                "UPDATE media_files SET tags = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (json.dumps(tags, ensure_ascii=False), file_id)
            )

    return {"file_id": file_id, "file_name": media.get("file_name"), **result}


@router.get("/status")
async def ocr_status(current_user: dict = Depends(get_current_user)):
    """获取 OCR 服务状态"""
    return {
        "available": ocr_service.is_available(),
        "engine": ocr_service.engine_name,
        "message": "可用" if ocr_service.is_available() else "请安装: pip install paddleocr 或 pip install pytesseract"
    }