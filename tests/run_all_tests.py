
#!/usr/bin/env python3
"""
Run all automated tests for the Student Attendance Sync Platform.
"""

import subprocess
import sys
import os
from datetime import datetime

# Project root directory
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')
)

def run_all_tests():
    """Run all test files and generate coverage report."""

    print("\n" + "=" * 70)
    print("Student Attendance Sync Platform - Test Suite")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # All six test files
    test_files = [
        'tests/test_attendance_sync.py',
        'tests/test_data_conversion.py',
        'tests/test_notifications.py',
        'tests/test_notifications_db.py',
        'tests/test_sync_logs.py',
        'tests/test_sync_logs_db.py'
    ]

    cmd = [
        sys.executable,
        '-m', 'pytest',
        '-v',
        '--tb=short',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing'
    ] + test_files

    print(f"Running command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    print("\n" + "=" * 70)

    if result.returncode == 0:
        print("All tests passed!")
    else:
        print("Some tests failed. Check the errors above.")

    print("=" * 70)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nCoverage report: htmlcov/index.html")

    return result.returncode


def document_bugs():
    """Remind the user to document discovered bugs."""

    print("\n" + "=" * 70)
    print("Bug Documentation")
    print("=" * 70)
    print("Create BUGS_FOUND.md in your project root if bugs were found.")
    print("Include:")
    print("1. What you were testing")
    print("2. Expected result")
    print("3. Actual result")
    print("4. Steps to reproduce")
    print("5. Whether it is fixed or still needs work")
    print("=" * 70)


if __name__ == '__main__':
    exit_code = run_all_tests()
    document_bugs()
    sys.exit(exit_code)
