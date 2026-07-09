#!/usr/bin/env python3
"""Audit coverage validation plus Audit v2 self-tests (SUITE-COVERAGE)."""
from __future__ import annotations

import subprocess
import sys
import time
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402


UNIT_TEST_MODULES = (
    "tools.audit.test_system",
    "tools.test_ui_structure_suite",
)


def run_step(label: str, command: list[str]) -> subprocess.CompletedProcess[str]:
    print(f"BEGIN {label}", flush=True)
    started = time.perf_counter()
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    print(f"TIMING {label} {elapsed_ms} ms exit {proc.returncode}", flush=True)
    if proc.returncode != 0:
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
    return proc


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SUITE-COVERAGE validation.")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Run deterministic registry/protocol checks only; CI/release profiles use the full default suite.",
    )
    args = parser.parse_args()

    cov = run_step(
        "audit_coverage --check",
        [sys.executable, "tools/audit_coverage.py", "--check"],
    )
    parallel_steps = [
        *[
            (f"unittest {module}", [sys.executable, "-m", "unittest", module])
            for module in UNIT_TEST_MODULES
        ],
    ]
    results_by_label: dict[str, subprocess.CompletedProcess[str]] = {}
    if cov.returncode == 0:
        with ThreadPoolExecutor(max_workers=min(4, len(parallel_steps))) as executor:
            futures = {
                executor.submit(run_step, label, command): label
                for label, command in parallel_steps
            }
            for future in as_completed(futures):
                label = futures[future]
                results_by_label[label] = future.result()
    else:
        results_by_label = {
            label: subprocess.CompletedProcess(command, 1, "", "skipped after coverage failure")
            for label, command in parallel_steps
        }
    test_results = [
        results_by_label[f"unittest {module}"]
        for module in UNIT_TEST_MODULES
    ]
    passed = (
        cov.returncode == 0
        and all(proc.returncode == 0 for proc in test_results)
    )
    msg = ""
    if cov.returncode != 0:
        msg = "audit_coverage --check failed"
    elif any(proc.returncode != 0 for proc in test_results):
        msg = "audit infrastructure unit tests failed"
    finish_suite(ROOT, [case_row("AUDIT-COV-01", passed, msg)], 0 if passed else 1)
    return 0 if passed else 1


if __name__ == "__main__":
    main()
