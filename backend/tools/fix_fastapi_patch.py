from loguru import logger
#!/usr/bin/env python3
"""
FastAPI 0.115.x UnboundLocalError Bug Patch
============================================
BUG: /openapi.json returns HTTP 500 UnboundLocalError: status_code

ROOT CAUSE:
    In fastapi/openapi/utils.py, the status_code variable is not defined
    in all branches of the conditional logic.

PATCH:
    Add else clauses to ensure status_code is always defined.

Apply: python fix_fastapi_patch.py
Check: python fix_fastapi_patch.py --check
"""

import sys
from pathlib import Path


def get_utils_path():
    import fastapi
    return Path(fastapi.__file__).parent / "openapi" / "utils.py"


def check():
    """Check if patch is applied"""
    path = get_utils_path()
    src = path.read_text(encoding="utf-8")
    
    # Count occurrences of status_code = "200" (our patch marker)
    count = src.count('status_code = "200"')
    
    if count >= 2:
        logger.info("✅ FastAPI patch already applied")
        return True
    else:
        logger.info("❌ FastAPI patch NOT applied")
        logger.info(f"   Found {count} occurrences of 'status_code = \"200\"' (expected 2)")
        return False


def apply():
    """Apply the patch"""
    path = get_utils_path()
    src = path.read_text(encoding="utf-8")
    
    # Check if already patched
    if check():
        return
    
    # Pattern to find (lines 325-328 approximately)
    OLD_PATTERN = '''                if status_code_param is not None:
                    if isinstance(status_code_param.default, int):
                        status_code = str(status_code_param.default)
            operation.setdefault'''
    
    NEW_PATTERN = '''                if status_code_param is not None:
                    if isinstance(status_code_param.default, int):
                        status_code = str(status_code_param.default)
                    else:
                        status_code = "200"
                else:
                    status_code = "200"
            operation.setdefault'''
    
    if OLD_PATTERN not in src:
        logger.info("❌ Could not find patch target!")
        logger.info("   FastAPI version may be different than expected.")
        logger.info("   Please manually check the source file.")
        sys.exit(1)
    
    patched = src.replace(OLD_PATTERN, NEW_PATTERN, 1)
    
    try:
        path.write_text(patched, encoding="utf-8")
        logger.info("✅ FastAPI patch applied successfully!")
    except PermissionError:
        logger.info("❌ Permission denied!")
        logger.info("   Please run as administrator or use sudo.")
        sys.exit(1)


if __name__ == "__main__":
    if "--check" in sys.argv:
        check()
    else:
        apply()
