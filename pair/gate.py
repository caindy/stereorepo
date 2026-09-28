# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""The pair loop's gate: its tests, reported in the one shape every gate here prints (A21).

Each test module under `pair/` is one step. A step prints `ok <step> — <scope>`
when every test in it passes, and `x  <step> (<count>)` with one indented line
per failure when any does. The exit code is non-zero when any step failed.
"""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    """Run each test module as a step and print its verdict."""
    sys.path.insert(0, str(HERE))
    failed = False
    for path in sorted(HERE.glob("test_*.py")):
        suite = unittest.defaultTestLoader.loadTestsFromName(path.stem)
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
        problems = result.failures + result.errors
        step = f"{path.stem.removeprefix('test_')} tests"
        if problems:
            failed = True
            print(f"x  {step} ({len(problems)})")
            for case, trace in problems:
                last = trace.strip().splitlines()[-1]
                print(f"     {case.id()}: {last}")
        else:
            print(f"ok {step} — {result.testsRun} tests")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
