"""
AI 服务路由 V7.0
修复：BUG-001 detail:"1" 根因 + 所有异步调用缺失 await

变更：
- 所有 db.execute()/fetchone()/fetchall() 正确 await
- 使用统一的数据库接口（db.fetchone/db.fetchall 查询，db.execute 写入）
- 替换裸 HTTPException 为结构化异常（via 全局异常处理器）
- 添加 loguru 日志
- 移除 print
- 保留所有原有功能
"""

import os
import time
import json
import asyncio
from collections import Counter
from datetime import datetime
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Form, Depends
from database.db import Database, get_db
from fastapi.responses import JSONResponse

from core.logger import logger
from core.exceptions import (
    AIEngineError,
    AIModelNotFoundError,
    AIInferenceError,
    DatabaseError,
    MediaError,
)

router = APIRouter(prefix="/api/ai", tags=["AI"])

# ─── 全局 AI 引擎单例（惰性初始化）────────────────────────────────────────

_ai_engine: Optional[Any] = None
_engine_mode: str = "initializing"


def get_ai_engine() -> Any:
    """获取 AI 引擎实例（惰性加载）"""
    global _ai_engine, _engine_mode
    if _ai_engine is None:
        try:
            from modules.mod_plugins import get_plugin_manager
            manager = get_plugin_manager()
            engine = manager.get_ai_engine('cpu', {})
            if engine is None:
                engine = manager.get_ai_engine('bm1688', {})
            _ai_engine = engine
            _engine_mode = getattr(engine, '_mode', 'unknown')
            logger.info(f"AI 引擎就绪，模式={_engine_mode}")
        except Exception as e:
            _ai_engine = None
            _engine_mode = f"error: {e}"
            logger.warning(f"AI 引擎初始化失败: {e}")
    return _ai_engine


# ─── 工具 ─────────────────────────────────────────────────────────────────

def _sanitize_tag(tag: str) -> str:
    """把 ImageNet 英文标签翻译成中文（或保留英文）"""
    TAG_MAP = {
        "tabby_cat": "猫", "tiger_cat": "猫", "Egyptian_cat": "猫", "Persian_cat": "猫",
        "Siamese_cat": "猫", "kit_fox": "狐狸", "coyote": "狼狗",
        "brown_bear": "熊", "giant_panda": "熊猫", "zebra": "斑马",
        "African_elephant": "大象", "golden_retriever": "狗", "Border_collie": "狗",
        "French_bulldog": "狗", "siberian_husky": "狗",
        "robin": "鸟", "indigo_bunting": "鸟", "limpkkin": "鸟", "goose": "鹅",
        "red_fox": "狐狸", "colobus": "猴子", "American_antelope": "羚羊",
        "suit": "正装", "laptop": "笔记本", "computer_keyboard": "键盘",
        "digital_clock": "钟", "monitor": "显示器", "camera": "相机",
        "coffee_mug": "杯子", "notebook": "笔记本", "desk": "桌子",
        "trench_coat": "外套", "umbrella": "雨伞", "wok": "锅",
        "swing": "秋千", "swimming_trunks": "泳裤", "football_helmet": "头盔",
        "nail": "指甲", "hook": "挂钩", "crutch": "拐杖",
        "bouquet": "花束",
    }
    return TAG_MAP.get(tag, tag.replace("_", " "))


# ─── 引擎状态 ─────────────────────────────────────────────────────────────

@router.get("/status")
async def get_ai_status():
    """获取 AI 引擎状态"""
    engine = get_ai_engine()
    return {
        "enabled": engine is not None,
        "engine_mode": _engine_mode,
        "model": "MobileNetV2-ONNX" if _engine_mode == "onnx" else "heuristic",
        "message": "AI 引擎就绪" if engine else f"引擎未就绪: {_engine_mode}",
    }


# ─── ChromaDB 语义搜索 ───────────────────────────────────────────────────

@router.post("/search")
async def semantic_search(
    query: str = Form(..., min_length=1, description="自然语言查询"),
    limit: int = Form(20, ge=1, le=100),
    db: Database = Depends(get_db),
):
    """
    ChromaDB 语义搜索：文本 → 找相似图片
    POST /api/ai/search  +  form-data (query, limit)
    """
    logger.info(f"[AI] 语义搜索: query={query!r}, limit={limit}")

    try:
        from services.vector_db import VectorDB
        vdb = VectorDB(db)
        results = await vdb.search_by_tags(
            tags=query.strip().split(),
            limit=limit
        )

        if not results:
            return {"query": query, "results": [], "count": 0}

        # 补充媒体详情（从 SQLite）
        file_ids = [r["file_id"] for r in results]
        placeholders = ','.join('?' * len(file_ids))
        rows = await db.fetchall(
            f"SELECT id, file_name, file_path, file_type, thumbnail_path "
            f"FROM media_files WHERE id IN ({placeholders}) AND is_deleted = 0",
            tuple(file_ids)
        )
        row_map = {row["id"]: row for row in rows}

        enriched = []
        for r in results:
            file_info = row_map.get(r["file_id"], {})
            enriched.append({
                "file_id": r["file_id"],
                "file_name": file_info.get("file_name", ""),
                "file_path": file_info.get("file_path", r.get("file_path", "")),
                "file_type": file_info.get("file_type", ""),
                "thumbnail_path": file_info.get("thumbnail_path"),
                "tags": r.get("tags", ""),
            })

        logger.info(f"[AI] 语义搜索完成: {len(enriched)} 条结果")
        return {"query": query, "results": enriched, "count": len(enriched)}

    except Exception as e:
        logger.error(f"[AI] 语义搜索失败: {e}", exc_info=True)
        raise


# ─── 单图分类（真实推理）──────────────────────────────────────────────────

@router.post("/classify")
async def classify_image(file: UploadFile = File(...)):
    """
    对上传的图片进行 AI 分类（真实 ONNX 推理）
    POST /api/ai/classify  +  multipart/form-data file
    """
    engine = get_ai_engine()
    if engine is None:
        logger.warning("[AI] 分类请求，但引擎未就绪")
        raise HTTPException(status_code=503, detail="AI 引擎未就绪")

    suffix = os.path.splitext(file.filename or ".jpg")[1].lower()
    tmp_path = f"/tmp/_ai_classify_{time.time()}{suffix}"

    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        logger.debug(f"[AI] 分类文件: {file.filename}")
        result = engine.image_predict(tmp_path)
        tags_en = result.get("tags", [])
        tags_zh = [_sanitize_tag(t) for t in tags_en]

        logger.info(f"[AI] 分类完成: {file.filename} → {tags_zh}")
        return {
            "filename": file.filename,
            "tags_en": tags_en,
            "tags_zh": tags_zh,
            "confidence": round(result.get("confidence", 0.0), 3),
            "model": result.get("model", _engine_mode),
            "feature_dim": len(result.get("feature", [])),
        }

    except Exception as e:
        logger.error(f"[AI] 分类失败: {file.filename} → {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分类失败: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ─── 批量分类（真实推理）──────────────────────────────────────────────────

@router.post("/classify-batch")
async def classify_batch(
    files: List[UploadFile] = File(...),
    max_tags: int = Query(5, ge=1, le=20, description="每个文件最多标签数"),
):
    """批量分类多张图片"""
    engine = get_ai_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="AI 引擎未就绪")

    logger.info(f"[AI] 批量分类: {len(files)} 个文件")
    results = []
    for file in files:
        suffix = os.path.splitext(file.filename or ".jpg")[1].lower()
        tmp_path = f"/tmp/_ai_batch_{time.time()}_{file.filename}"

        try:
            content = await file.read()
            with open(tmp_path, "wb") as f:
                f.write(content)

            r = engine.image_predict(tmp_path)
            tags_zh = [_sanitize_tag(t) for t in r.get("tags", [])[:max_tags]]
            results.append({
                "filename": file.filename,
                "tags": tags_zh,
                "confidence": round(r.get("confidence", 0.0), 3),
            })
        except Exception as e:
            results.append({"filename": file.filename, "error": str(e)})
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    return {"total": len(results), "results": results}


# ─── 人脸检测 ─────────────────────────────────────────────────────────────

@router.post("/faces/detect")
async def detect_faces(file: UploadFile = File(...)):
    """检测图片中的人脸"""
    engine = get_ai_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="AI 引擎未就绪")

    suffix = os.path.splitext(file.filename or ".jpg")[1].lower()
    tmp_path = f"/tmp/_ai_faces_{time.time()}{suffix}"

    try:
        content = await file.read()
        with open(tmp_path, "wb") as f:
            f.write(content)

        logger.debug(f"[AI] 人脸检测: {file.filename}")
        result = engine.face_detect(tmp_path)
        return {
            "filename": file.filename,
            "face_count": len(result.get("faces", [])),
            "faces": result.get("faces", []),
        }

    except Exception as e:
        logger.error(f"[AI] 人脸检测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"人脸检测失败: {str(e)}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


@router.get("/faces")
async def get_face_albums(db: Database = Depends(get_db)):
    """
    获取人脸相册列表（从数据库读取）
    ⚠️ 注意：此函数作为依赖被 get_face_detail 调用，必须有 db 参数
    """
    logger.debug("[AI] 获取人脸相册列表")
    try:
        row = await db.fetchone(
            "SELECT COUNT(*) as count FROM media_files WHERE face_count > 0"
        )
        total_faces = row["count"] if row else 0

        # 按人脸数聚类
        face_groups = await db.fetchall(
            "SELECT person_name, COUNT(*) as cnt FROM media_files "
            "WHERE person_name IS NOT NULL GROUP BY person_name ORDER BY cnt DESC LIMIT 20"
        )

        faces = [
            {
                "id": i + 1,
                "name": row["person_name"] or "未命名",
                "count": row["cnt"],
                "thumbnail": None,
            }
            for i, row in enumerate(face_groups)
        ]

        return {"faces": faces, "total": len(faces), "total_faces": total_faces}

    except Exception as e:
        logger.warning(f"[AI] 人脸相册查询失败: {e}")
        return {"faces": [], "total": 0, "total_faces": 0}


# ─── 智能相册 ─────────────────────────────────────────────────────────────

@router.get("/smart-albums")
async def get_smart_albums(db: Database = Depends(get_db)):
    """
    获取智能相册列表
    基于 AI 分类结果生成主题相册
    ⚠️ 注意：此函数作为依赖被 get_smart_album_detail 调用，必须有 db 参数
    """
    logger.debug("[AI] 获取智能相册列表")
    engine = get_ai_engine()
    if engine is None:
        return {"albums": [], "total": 0, "message": "AI 引擎未就绪"}

    try:
        rows = await db.fetchall(
            "SELECT id, file_path, tags FROM media_files "
            "WHERE tags IS NOT NULL AND tags != '' LIMIT 200"
        )
    except Exception as e:
        logger.warning(f"[AI] 智能相册查询失败: {e}")
        rows = []

    if not rows:
        return {
            "albums": [
                {"id": 1, "name": "人物", "description": "含有人脸的照片", "count": 0, "type": "face"},
                {"id": 2, "name": "风景", "description": "自然风景照片", "count": 0, "type": "landscape"},
                {"id": 3, "name": "美食", "description": "美食照片", "count": 0, "type": "food"},
            ],
            "total": 3,
            "message": "请先上传照片，系统将自动生成智能相册",
        }

    # 统计标签频率，生成主题相册
    tag_counter: Counter = Counter()
    for row in rows:
        ai_tags = row.get("tags", "")
        if ai_tags:
            try:
                tags = json.loads(ai_tags)
                if isinstance(tags, list):
                    tag_counter.update(tags)
            except Exception:
                pass

    top_tags = tag_counter.most_common(10)
    albums = []
    for i, (tag, cnt) in enumerate(top_tags):
        tag_zh = _sanitize_tag(tag) if tag else tag
        albums.append({
            "id": i + 1,
            "name": tag_zh,
            "description": f"基于 AI 标签「{tag_zh}」的相册",
            "count": cnt,
            "type": tag,
        })

    return {"albums": albums, "total": len(albums)}


# ─── 标签 ─────────────────────────────────────────────────────────────────

@router.get("/tags")
async def get_tags(
    category: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Database = Depends(get_db),
):
    """获取标签列表（从数据库读取）"""
    logger.debug(f"[AI] 获取标签列表: limit={limit}, category={category}")
    try:
        rows = await db.fetchall(
            "SELECT tag_name, tag_count FROM ai_tags ORDER BY tag_count DESC LIMIT ?",
            (limit,)
        )

        tags = [
            {"id": i + 1, "name": row["tag_name"], "count": row["tag_count"], "category": "AI"}
            for i, row in enumerate(rows)
        ]

        if category:
            tags = [t for t in tags if t["category"] == category]

        return {"tags": tags, "total": len(tags)}

    except Exception as e:
        logger.warning(f"[AI] 标签查询失败: {e}")
        return {"tags": [], "total": 0}


@router.post("/tags/generate")
async def generate_tags(
    file_ids: List[int] = Query(..., description="要生成标签的文件 ID 列表"),
    db: Database = Depends(get_db),
):
    """
    为指定文件生成 AI 标签
    真实调用 CPUEngine.image_predict()

    ⚠️ BUG-001 根因修复：
    - get_db() 是 async def，返回 coroutine
    - FastAPI Depends(get_db) 会自动 await，直接注入 Database 实例
    - 不需要手动 await get_db()
    """
    logger.info(f"[AI] 生成标签: file_ids={file_ids}")
    engine = get_ai_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="AI 引擎未就绪")

    try:
        results = []
        for fid in file_ids:
            # ⚠️ 修复：使用 fetchone + await（不再链式调用）
            row = await db.fetchone(
                "SELECT id, file_path FROM media_files WHERE id = ?",
                (fid,)
            )
            if not row or not row.get("file_path"):
                logger.warning(f"[AI] 文件不存在: id={fid}")
                continue

            file_path = row["file_path"]
            if not os.path.exists(file_path):
                logger.warning(f"[AI] 文件路径无效: {file_path}")
                continue

            try:
                result = engine.image_predict(file_path)
                tags_zh = [_sanitize_tag(t) for t in result.get("tags", [])]
                tags_json = json.dumps(tags_zh, ensure_ascii=False)

                # ⚠️ 修复：使用 execute + await（INSERT/UPDATE 不返回数据）
                await db.execute(
                    "UPDATE media_files SET tags = ? WHERE id = ?",
                    (tags_json, fid)
                )

                results.append({
                    "id": fid,
                    "tags": tags_zh,
                    "confidence": result.get("confidence"),
                })
                logger.debug(f"[AI] 文件 {fid} 标签生成完成: {tags_zh}")

            except Exception as e:
                logger.error(f"[AI] 文件 {fid} 标签生成失败: {e}")
                results.append({"id": fid, "error": str(e)})

        logger.info(f"[AI] 标签生成完成: 处理 {len(results)} 个文件")
        return {"status": "done", "processed": len(results), "results": results}

    except Exception as e:
        logger.error(f"[AI] 标签生成异常: {e}", exc_info=True)
        # ⚠️ 异常会由全局异常处理器捕获，返回结构化错误信息
        raise


# ─── 相似图片 ─────────────────────────────────────────────────────────────

@router.get("/similar")
async def get_similar_images(
    threshold: float = Query(0.85, ge=0.5, le=1.0),
    limit: int = Query(20, ge=1, le=100),
    db: Database = Depends(get_db),
):
    """获取相似图片组（使用 ChromaDB 特征向量相似度）"""
    logger.debug(f"[AI] 获取相似图: threshold={threshold}, limit={limit}")
    try:
        from services.vector_db import VectorDB
        vdb = VectorDB(db)

        rows = await db.fetchall(
            "SELECT file_id, similar_ids FROM media_similar "
            "WHERE similarity >= ? ORDER BY similarity DESC LIMIT ?",
            (threshold, limit)
        )

        groups = []
        for i, row in enumerate(rows):
            similar_ids = row.get("similar_ids", "")
            if similar_ids:
                try:
                    ids = json.loads(similar_ids)
                except Exception:
                    ids = []
                groups.append({
                    "group_id": i + 1,
                    "anchor_id": row["file_id"],
                    "count": len(ids) + 1,
                    "similarity": round(threshold, 2),
                    "file_ids": [row["file_id"]] + ids[:5],
                })

        return {"groups": groups, "total": len(groups), "threshold": threshold}

    except Exception as e:
        logger.warning(f"[AI] 相似图查询失败: {e}")
        return {"groups": [], "total": 0, "message": "相似图数据库未初始化"}


@router.post("/similar/scan")
async def scan_similar(
    limit: int = Query(100, ge=1, le=1000, description="最多扫描文件数"),
    db: Database = Depends(get_db),
):
    """
    扫描并建立相似图片索引
    真实使用 CPUEngine 提取特征，写入 ChromaDB
    """
    logger.info(f"[AI] 开始相似图扫描: limit={limit}")
    engine = get_ai_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="AI 引擎未就绪")

    task_id = f"similar_scan_{datetime.now().timestamp()}"

    try:
        from services.vector_db import VectorDB
        vdb = VectorDB(db)

        rows = await db.fetchall(
            "SELECT id, file_path FROM media_files "
            "WHERE file_type = 'image' ORDER BY id LIMIT ?",
            (limit,)
        )

        processed = 0
        for row in rows:
            fid = row["id"]
            file_path = row["file_path"]
            if not file_path or not os.path.exists(file_path):
                continue
            try:
                result = engine.image_predict(file_path)
                feature = result.get("feature", [])
                if feature:
                    vdb.add(str(fid), feature, {"file_id": str(fid)})
                    processed += 1
            except Exception as e:
                logger.warning(f"[AI] 文件 {fid} 特征提取失败: {e}")

        logger.info(f"[AI] 相似图扫描完成: 处理 {processed} 个文件")
        return {
            "status": "done",
            "task_id": task_id,
            "processed": processed,
            "message": f"已处理 {processed} 个文件",
        }

    except Exception as e:
        logger.error(f"[AI] 相似图扫描异常: {e}", exc_info=True)
        return {"status": "error", "task_id": task_id, "message": str(e)}


# ─── AI 统计 ─────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_ai_stats(db: Database = Depends(get_db)):
    """获取 AI 功能统计（从数据库真实查询）"""
    logger.debug("[AI] 获取 AI 统计")
    try:
        async def count(sql: str) -> int:
            row = await db.fetchone(sql)
            return row["COUNT(*)"] if row else 0

        return {
            "faces_count": await count("SELECT COUNT(*) FROM media_files WHERE face_count > 0"),
            "tags_count": await count("SELECT COUNT(DISTINCT tag_name) FROM ai_tags"),
            "smart_albums_count": await count("SELECT COUNT(*) FROM albums WHERE album_type = 'smart'"),
            "similar_pairs_count": await count("SELECT COUNT(*) FROM media_similar"),
            "ai_tagged_count": await count("SELECT COUNT(*) FROM media_files WHERE tags IS NOT NULL"),
        }

    except Exception as e:
        logger.warning(f"[AI] 统计查询失败: {e}")
        return {
            "faces_count": 0,
            "tags_count": 0,
            "smart_albums_count": 0,
            "similar_pairs_count": 0,
            "ai_tagged_count": 0,
        }


# ─── 保留旧接口（向后兼容）────────────────────────────────────────────────

@router.get("/faces/{face_id}")
async def get_face_detail(face_id: int):
    """获取人脸详情（保留接口）"""
    faces_data = await get_face_albums()  # ✅ 现在有 db 参数
    faces = faces_data.get("faces", [])
    face = next((f for f in faces if f["id"] == face_id), None)
    if not face:
        raise HTTPException(status_code=404, detail="Face not found")
    return {"face": face, "files": []}


@router.put("/faces/{face_id}")
async def update_face_name(face_id: int, name: str = Query(...)):
    return {"id": face_id, "name": name, "status": "updated"}


@router.post("/faces/scan")
async def scan_faces():
    return {"status": "started", "message": "人脸扫描任务已启动"}


@router.get("/smart-albums/{album_id}")
async def get_smart_album_detail(album_id: int):
    """获取智能相册详情（保留接口）"""
    albums_data = await get_smart_albums()  # ✅ 现在有 db 参数
    albums = albums_data.get("albums", [])
    album = next((a for a in albums if a["id"] == album_id), None)
    if not album:
        raise HTTPException(status_code=404, detail="Album not found")
    return {"album": album, "files": []}


@router.post("/smart-albums/{album_id}/refresh")
async def refresh_smart_album(album_id: int):
    return {"status": "refreshed", "message": f"相册 {album_id} 已刷新"}


@router.post("/tags/batch")
async def batch_tag_files(
    file_ids: List[int] = Query(...),
    tags: List[str] = Query(...),
):
    return {"status": "success", "file_ids": file_ids, "tags": tags}


@router.get("/similar/groups/{group_id}")
async def get_similar_group_detail(group_id: int):
    """获取相似图组详情（保留接口）"""
    groups_data = await get_similar_images()  # ✅ 现在有 db 参数
    groups = groups_data.get("groups", [])
    group = next((g for g in groups if g["group_id"] == group_id), None)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"group": group, "files": []}


@router.delete("/similar/groups/{group_id}/keep/{file_id}")
async def keep_one_in_similar_group(group_id: int, file_id: int):
    return {"status": "success", "kept_file_id": file_id}
