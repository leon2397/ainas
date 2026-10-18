#!/usr/bin/env python3
"""
AI-NAS Media Manager - Syntax Check Script
"""

import os
import sys
import py_compile
from pathlib import Path

def check_syntax(filepath):
    try:
        py_compile.compile(filepath, doraise=True)
        return True, None
    except py_compile.PyCompileError as e:
        return False, str(e)

def find_python_files(directory):
    py_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git']]
        for f in files:
            if f.endswith('.py'):
                py_files.append(os.path.join(root, f))
    return py_files

def main():
    backend_dir = Path(__file__).parent / 'backend'
    print("=" * 50)
    print("  AI-NAS - Syntax Check")
    print("=" * 50)
    print()
    
    if not backend_dir.exists():
        print(f"ERROR: {backend_dir} not found")
        sys.exit(1)
    
    py_files = find_python_files(backend_dir)
    print(f"Found {len(py_files)} Python files")
    print()
    
    errors = []
    ok_count = 0
    
    for filepath in sorted(py_files):
        rel_path = os.path.relpath(filepath, backend_dir)
        success, error = check_syntax(filepath)
        
        if success:
            print(f"  OK   {rel_path}")
            ok_count += 1
        else:
            print(f"  FAIL {rel_path}")
            errors.append(filepath)
    
    print()
    print(f"Results: {ok_count}/{len(py_files)} OK")
    if errors:
        print(f"Errors: {len(errors)}")
        for f in errors:
            print(f"  - {os.path.relpath(f, backend_dir)}")
        return 1
    else:
        print("All passed!")
    return 0

if __name__ == '__main__':
    sys.exit(main())
