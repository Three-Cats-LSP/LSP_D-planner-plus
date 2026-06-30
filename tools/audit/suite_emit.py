"""Helpers for leaf audit suites to emit structured case results."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any


def audit_suite_id() -> str | None:
    raw = os.environ.get("LSP_AUDIT_SUITE_ID", "").strip()
    return raw or None


def case_row(case_id: str, passed: bool, message: str = "") -> dict[str, Any]:
    row: dict[str, Any] = {"case_id": case_id, "status": "PASS" if passed else "FAIL"}
    if message:
        row["message"] = message
    return row


def finish_suite(root: Path, cases: list[dict[str, Any]], exit_code: int) -> None:
    suite_id = audit_suite_id()
    if suite_id:
        from .case_report import write_suite_cases

        write_suite_cases(root, suite_id, cases)
    sys.exit(exit_code)


def finish_single(root: Path, case_id: str, passed: bool, message: str = "") -> None:
    finish_suite(root, [case_row(case_id, passed, message)], 0 if passed else 1)
