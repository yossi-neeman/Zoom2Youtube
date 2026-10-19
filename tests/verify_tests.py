#!/usr/bin/env python3
"""
Verify test structure and syntax without running tests
"""

import ast
import sys
from pathlib import Path


def check_python_syntax(filepath):
    """Check if a Python file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        return True, None
    except SyntaxError as e:
        return False, str(e)


def main():
    """Main verification"""
    tests_dir = Path(__file__).parent
    test_files = list(tests_dir.glob('test_*.py'))

    print("=" * 70)
    print("Verifying Test Structure")
    print("=" * 70)
    print()

    all_valid = True
    for test_file in test_files:
        print(f"Checking {test_file.name}...", end=" ")
        valid, error = check_python_syntax(test_file)
        if valid:
            print("✓ Valid syntax")
        else:
            print(f"✗ Syntax error: {error}")
            all_valid = False

    print()
    print("=" * 70)
    if all_valid:
        print("✅ All test files have valid syntax")
        print()
        print("To run tests, install dependencies:")
        print("  pip install -r requirements.txt")
        print("  pip install -r requirements-test.txt")
        print()
        print("Then run:")
        print("  python tests/run_tests.py")
        return 0
    else:
        print("❌ Some test files have syntax errors")
        return 1


if __name__ == '__main__':
    sys.exit(main())
