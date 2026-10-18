"""
run_tests.py - 测试运行脚本
=========================
用法:
  python run_tests.py              # 运行所有测试
  python run_tests.py unit         # 只运行单元测试
  python run_tests.py integration  # 只运行集成测试
  python run_tests.py --cov        # 生成覆盖率报告
"""

import sys
import subprocess
import argparse


def run_tests(test_type="all", coverage=False, markers=None):
    """运行测试"""
    cmd = ["python", "-m", "pytest"]
    
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "e2e":
        cmd.append("tests/e2e/")
    else:
        cmd.append("tests/")
    
    # 标记过滤
    if markers:
        cmd.extend(["-m", markers])
    
    # 基础选项
    cmd.extend(["-v", "--tb=short"])
    
    # 覆盖率
    if coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run AI-NAS tests")
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["all", "unit", "integration", "e2e"],
        help="Test type to run"
    )
    parser.add_argument(
        "--cov",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--markers",
        default=None,
        help="Run tests with specific markers (e.g., 'not slow')"
    )
    
    args = parser.parse_args()
    
    # 设置测试环境
    import os
    os.environ["AI_NAS_ENV"] = "test"
    os.environ["AI_NAS_DB_PATH"] = ":memory:"
    
    # 运行测试
    exit_code = run_tests(args.type, args.cov, args.markers)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
