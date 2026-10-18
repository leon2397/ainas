import sys
from loguru import logger
logger.info(f"Python: {sys.version}")

try:
    import fastapi
    logger.info(f"FastAPI: {fastapi.__version__}")
except ImportError as e:
    logger.info(f"FastAPI: MISSING - {e}")

try:
    import aiosqlite
    logger.info(f"aiosqlite: OK")
except ImportError as e:
    logger.info(f"aiosqlite: MISSING - {e}")

try:
    import PIL
    logger.info(f"Pillow: {PIL.__version__}")
except ImportError as e:
    logger.info(f"Pillow: MISSING - {e}")

try:
    import numpy
    logger.info(f"numpy: {numpy.__version__}")
except ImportError as e:
    logger.info(f"numpy: MISSING - {e}")

try:
    import psutil
    logger.info(f"psutil: {psutil.__version__}")
except ImportError as e:
    logger.info(f"psutil: MISSING - {e}")

try:
    import chromadb
    logger.info(f"chromadb: {chromadb.__version__}")
except ImportError as e:
    logger.info(f"chromadb: MISSING - {e}")

try:
    import pydantic
    logger.info(f"pydantic: {pydantic.__version__}")
except ImportError as e:
    logger.info(f"pydantic: MISSING - {e}")

logger.info("\n--- Testing imports from project ---")
sys.path.insert(0, ".")

try:
    from core.ai_engine import AIEngine
    logger.info("core.ai_engine: OK")
except ImportError as e:
    logger.info(f"core.ai_engine: ERROR - {e}")

try:
    from database.db import Database
    logger.info("database.db: OK")
except ImportError as e:
    logger.info(f"database.db: ERROR - {e}")

try:
    from routes.media import router as media_router
    logger.info("routes.media: OK")
except ImportError as e:
    logger.info(f"routes.media: ERROR - {e}")

try:
    from main import app
    logger.info("main.app: OK")
except ImportError as e:
    logger.info(f"main.app: ERROR - {e}")
