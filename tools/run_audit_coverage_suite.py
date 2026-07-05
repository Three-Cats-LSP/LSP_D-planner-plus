#!/usr/bin/env python3
"""Audit coverage validation plus Audit v2 self-tests (SUITE-COVERAGE)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402


def _self_test_modules(profile: str) -> list[str]:
    modules = [
        "tools.audit.test_system",
        "tools.test_ui_structure_suite",
        "tools.test_seven_lens_protocol",
        "tools.test_seven_lens_protocol_migrations",
    ]
    if profile != "static":
        modules.append("tools.test_seven_lens_browser_trace")
    return modules


def main() -> int:
    profile = (os.environ.get("LSP_AUDIT_PROFILE") or "static").strip() or "static"
    cov = subprocess.run(
        [sys.executable, "tools/audit_coverage.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    reviewed = subprocess.run(
        [sys.executable, "tools/seven_lens_protocol.py", "check-all"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "unittest",
            *_self_test_modules(profile),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if cov.returncode != 0:
        print(cov.stdout, end="")
        print(cov.stderr, end="", file=sys.stderr)
    if tests.returncode != 0:
        print(tests.stdout, end="")
        print(tests.stderr, end="", file=sys.stderr)
    if reviewed.returncode != 0:
        print(reviewed.stdout, end="")
        print(reviewed.stderr, end="", file=sys.stderr)
    passed = cov.returncode == 0 and tests.returncode == 0 and reviewed.returncode == 0
    msg = ""
    if cov.returncode != 0:
        msg = "audit_coverage --check failed"
    elif tests.returncode != 0:
        msg = "audit infrastructure unit tests failed"
    elif reviewed.returncode != 0:
        msg = "reviewed seven-lens cycle records are invalid"
    finish_suite(ROOT, [case_row("AUDIT-COV-01", passed, msg)], 0 if passed else 1)
    return 0 if passed else 1


if __name__ == "__main__":
    main()
