import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_FILE = os.path.join(ROOT_DIR, "tests", "test_requirement_flows.py")

result = subprocess.run(
    [sys.executable, "-m", "unittest", "-v", TEST_FILE],
    cwd=ROOT_DIR,
)

raise SystemExit(result.returncode)
