"""
patch_fastapi.py — FastAPI 0.135.x Bug 补丁管理
=================================================
BUG:  FastAPI 0.135.x openapi/utils.py
      _get_openapi_path() 中局部变量 status_code 在两个独立 if 分支内赋值，
      当路由返回 StreamingResponse 时两分支均不满足 → UnboundLocalError
      → /openapi.json → 500 Internal Server Error

      StreamingResponse.__init__ signature 中 status_code=None（默认值，非int），
      导致进入 "status_code_param 不是 None 但 default 不是 int" 的分支。

PATCH（已注入 site-packages）:
    在 L352 后：
        if isinstance(status_code_param.default, int):
            status_code = str(status_code_param.default)
        else:                           ← 注入
            status_code = "200"         ← 注入
    在 L355 后：
        else:
            status_code = "200"         ← 注入

升级 FastAPI 后的还原步骤（手动）:
    1. pip install fastapi -U
    2. 启动服务，访问 /openapi.json 确认无 UnboundLocalError
    3. 若确认新版本已修复，运行 python -m core.patch_fastapi --restore
    4. 若仍有问题，重新运行 python -m core.patch_fastapi --apply

用法（在 main.py 最顶部 fastapi 导入前）：
    from core.patch_fastapi import ensure_fastapi_patch
    ensure_fastapi_patch()
"""

from __future__ import annotations

import sys
import logging
import os
from pathlib import Path
from loguru import logger

__all__ = ["ensure_fastapi_patch", "restore_fastapi", "is_patched"]

log = logger.bind(patch_fastapi=True)


# ─── 路径 ───────────────────────────────────────────────────────────────────

def _utils_path() -> Path:
    import fastapi as _f
    return Path(_f.__file__).parent / "openapi" / "utils.py"


# ─── Patch 检测 ─────────────────────────────────────────────────────────────

def is_patched() -> bool:
    """Site-packages 中的 FastAPI 是否已打 patch。"""
    try:
        return 'status_code = "200"' in _utils_path().read_text(encoding="utf-8")
    except Exception:
        return False


# ─── Patch 核心 ─────────────────────────────────────────────────────────────
#
# 当前已 patch 的 site-packages fastapi/openapi/utils.py（L351~L357）：
#
# L351  if isinstance(status_code_param.default, int):      # 20 spaces
# L352      status_code = str(status_code_param.default)    # 24 spaces
# L353      else:                                            # 20 spaces ← PATCH
# L354          status_code = "200"                         # 24 spaces ← PATCH
# L355  else:                                                # 16 spaces ← PATCH
# L356      status_code = "200"                             # 20 spaces ← PATCH
# L357  operation.setdefault("responses", {})...             # 12 spaces
#
# 原始（未 patch）状态：
#
# L350  if status_code_param is not None:                   # 16 spaces
# L351      if isinstance(status_code_param.default, int):  # 20 spaces
# L352          status_code = str(status_code_param.default) # 24 spaces
#                                                    ← 无 else，status_code 未定义
#       else:                                               # 16 spaces ← 无 body，status_code 未定义
# L357  operation.setdefault("responses", {})...

_PATCH_MARKER = 'status_code = "200"'  # 同时用于检测和日志


# ─── 公共 API ────────────────────────────────────────────────────────────────

def ensure_fastapi_patch() -> None:
    """
    确保 site-packages 中的 FastAPI 已打 patch。
    已打则跳过，未打则注入 patch 并写回文件。
    """
    path = _utils_path()

    try:
        src = path.read_text(encoding="utf-8")
    except PermissionError:
        _permission_error(path)
        return
    except Exception as exc:
        log.error(f"读取失败: {path}: {exc}")
        return

    if _PATCH_MARKER in src:
        log.info("✅ FastAPI patch 已存在，无需重复注入")
        return

    patched = _apply(src)
    if patched is None:
        log.error(
            "❌ 未找到 patch 目标。"
            "FastAPI 源码结构可能已变更（bug 可能在当前版本已修复）。"
            "请升级后测试 /openapi.json 是否正常。"
        )
        return

    try:
        path.write_text(patched, encoding="utf-8")
        log.info(f"✅ FastAPI patch 已写入: {path}")
    except PermissionError:
        _permission_error(path)


def restore_fastapi() -> None:
    """
    从 site-packages 移除 patch，恢复原始源码。

    ⚠️ 注意：由于嵌套 if/else 的 Python 缩进复杂性，
    自动还原可能不完整。强烈建议：
      1. pip install fastapi -U 升级
      2. 启动服务测试 /openapi.json
      3. 确认正常后再运行还原
    """
    path = _utils_path()

    try:
        src = path.read_text(encoding="utf-8")
    except Exception as exc:
        log.error(f"读取失败: {exc}")
        return

    if _PATCH_MARKER not in src:
        log.info("未检测到 patch，无需还原")
        return

    restored = _revert(src)
    if restored == src:
        log.warning("⚠️ 自动还原未能修改任何内容。请手动编辑 site-packages 中的文件，"
                    "删除 status_code = \"200\" 两处（或重新安装 FastAPI）。")
        return

    try:
        path.write_text(restored, encoding="utf-8")
        log.info(f"✅ FastAPI 已还原: {path}")
    except PermissionError:
        _permission_error(path)


def _apply(src: str) -> str | None:
    """
    向 FastAPI utils.py 源码注入 patch。
    返回新源码；目标未找到返回 None。
    """
    # ── Patch A: inner if 块末 → 插入 else ─────────────────────────────────
    # 原文片段（精确缩进）：
    #     if isinstance(status_code_param.default, int):
    #         status_code = str(status_code_param.default)
    # 替换为：
    #     if isinstance(status_code_param.default, int):
    #         status_code = str(status_code_param.default)
    #     else:
    #         status_code = "200"
    OLD_A = (
        '                    if isinstance(status_code_param.default, int):\n'
        '                        status_code = str(status_code_param.default)\n'
        '                else:\n'
        '            operation.setdefault("responses", {})'
    )
    NEW_A = (
        '                    if isinstance(status_code_param.default, int):\n'
        '                        status_code = str(status_code_param.default)\n'
        '                    else:\n'
        '                        status_code = "200"\n'
        '                else:\n'
        '            operation.setdefault("responses", {})'
    )

    # ── Patch B: outer else 追加 body ────────────────────────────────────────
    OLD_B = (
        '                else:\n'
        '            operation.setdefault("responses", {})'
    )
    NEW_B = (
        '                else:\n'
        '                    status_code = "200"\n'
        '            operation.setdefault("responses", {})'
    )

    result = src

    # Patch A
    if OLD_A not in result:
        log.debug(f"Patch A target not found in source")
        return None
    result = result.replace(OLD_A, NEW_A, 1)
    log.debug("Patch A applied")

    # Patch B
    if OLD_B not in result:
        log.debug("Patch B target not found")
        return None
    result = result.replace(OLD_B, NEW_B, 1)
    log.debug("Patch B applied")

    return result


def _revert(src: str) -> str:
    """
    从已 patch 的源码移除 patch。
    ⚠️ 简化实现：查找精确的 patch 字符串并删除。
    """
    # 移除 inner else: status_code = "200"（L353-L354）
    INNER_ELSE = (
        '                    if isinstance(status_code_param.default, int):\n'
        '                        status_code = str(status_code_param.default)\n'
        '                    else:\n'
        '                        status_code = "200"\n'
        '                else:\n'
        '            operation.setdefault("responses", {})'
    )
    INNER_ELSE_CLEAN = (
        '                    if isinstance(status_code_param.default, int):\n'
        '                        status_code = str(status_code_param.default)\n'
        '                else:\n'
        '            operation.setdefault("responses", {})'
    )

    # 移除 outer else: status_code = "200"（L355-L356）
    OUTER_ELSE = (
        '                else:\n'
        '                    status_code = "200"\n'
        '            operation.setdefault("responses", {})'
    )
    OUTER_ELSE_CLEAN = (
        '                else:\n'
        '            operation.setdefault("responses", {})'
    )

    result = src
    na = result.count(INNER_ELSE_CLEAN)
    if INNER_ELSE in result:
        result = result.replace(INNER_ELSE, INNER_ELSE_CLEAN, 1)
        log.debug(f"Reverted inner else block")
    elif INNER_ELSE_CLEAN not in result:
        log.debug("Inner else block pattern not found for revert")

    if OUTER_ELSE in result:
        result = result.replace(OUTER_ELSE, OUTER_ELSE_CLEAN, 1)
        log.debug("Reverted outer else block")
    elif OUTER_ELSE_CLEAN not in result:
        log.debug("Outer else block pattern not found for revert")

    return result


def _permission_error(path: Path) -> None:
    log.error(
        f"写入权限不足: {path}\n"
        "请以管理员身份运行 PowerShell / Terminal，然后重试。"
    )


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    import argparse
    p = argparse.ArgumentParser(
        description="FastAPI 0.135.x status_code bug patch 管理器",
        prog="python -m core.patch_fastapi",
    )
    p.add_argument("--check",  action="store_true", help="检查 patch 状态")
    p.add_argument("--apply",  action="store_true", help="应用 patch（默认）")
    p.add_argument("--restore",action="store_true", help="移除 patch（实验性）")
    args = p.parse_args(sys.argv[1:] or ["--check"])

    if args.check:
        status = is_patched()
        logger.info(f"FastAPI patched: {status}")
    elif args.restore:
        restore_fastapi()
    else:
        ensure_fastapi_patch()
