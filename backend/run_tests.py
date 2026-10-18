#!/usr/bin/env python3
"""AI-NAS Media Manager - Test Runner"""
import subprocess
from loguru import logger
import sys
from pathlib import Path

def main():
    venv_python = Path(__file__).parent / "venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        logger.info("[ERROR] Virtual environment not found.")
        logger.info("Run: python -m venv venv && venv\\Scripts\\pip install -r requirements.txt")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("  AI-NAS Media Manager - Running Tests")
    logger.info("=" * 50)
    
    result = subprocess.run(
        [str(venv_python), "-m", "pytest", "tests/", "-v", "--tb=short"],
        cwd=str(Path(__file__).parent),
    )
    
    logger.info("=" * 50)
    logger.info("  Tests Complete")
    logger.info("=" * 50)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()