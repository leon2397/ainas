#!/usr/bin/env python3
"""
AI-NAS Media Manager - Environment Check Script
"""

import os
import sys

def check_python():
    """Check Python version"""
    print("Checking Python...")
    try:
        v = sys.version_info
        if v.major >= 3 and v.minor >= 10:
            print(f"  OK: Python {v.major}.{v.minor}.{v.micro}")
            return True
        else:
            print(f"  FAIL: Python 3.10+ required, found {v.major}.{v.minor}")
            return False
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def check_pip():
    """Check pip"""
    print("Checking pip...")
    try:
        import pip
        print(f"  OK: pip {pip.__version__}")
        return True
    except Exception as e:
        print(f"  FAIL: {e}")
        return False

def check_packages():
    """Check required packages"""
    print("Checking required packages...")
    packages = [
        'fastapi',
        'uvicorn',
        'aiosqlite',
        'pillow',
        'numpy',
        'cv2',
        'paramiko',
        'pydantic',
        'psutil',
        'yaml'
    ]
    
    all_ok = True
    for pkg in packages:
        try:
            if pkg == 'cv2':
                import cv2
                print(f"  OK: opencv-python")
            elif pkg == 'yaml':
                import yaml
                print(f"  OK: pyyaml")
            else:
                __import__(pkg)
                print(f"  OK: {pkg}")
        except ImportError:
            print(f"  MISS: {pkg}")
            all_ok = False
    
    return all_ok

def check_files():
    """Check required files"""
    print("Checking project files...")
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend = os.path.join(base, 'backend')
    
    required = [
        'main.py',
        'requirements.txt',
        'core/ai_engine.py',
        'database/db.py',
        'routes/media.py',
    ]
    
    all_ok = True
    for f in required:
        path = os.path.join(backend, f)
        if os.path.exists(path):
            print(f"  OK: {f}")
        else:
            print(f"  MISS: {f}")
            all_ok = False
    
    return all_ok

def main():
    print("=" * 50)
    print("  AI-NAS Media Manager - Environment Check")
    print("=" * 50)
    print()
    
    results = []
    
    results.append(("Python", check_python()))
    results.append(("pip", check_pip()))
    results.append(("Packages", check_packages()))
    results.append(("Files", check_files()))
    
    print()
    print("=" * 50)
    print("  Summary")
    print("=" * 50)
    
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"  {name}: {status}")
    
    all_ok = all(ok for _, ok in results)
    print()
    if all_ok:
        print("  All checks passed! Ready to start.")
        print()
        print("  Run: python main.py")
    else:
        print("  Some checks failed. Please fix the issues above.")
        print()
        print("  Run: pip install -r requirements.txt")
    
    print("=" * 50)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())
