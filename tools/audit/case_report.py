"""Structured audit case results for leaf evidence suites."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CASE_MARKER = "---LSP-AUDIT-CASES---"
RESULTS_DIR = "dev/audit-suite-results"


def results_path(root: Path, suite_id: str) -> Path:
    return root / RESULTS_DIR / f"{suite_id}.json"


def write_suite_cases(root: Path, suite_id: str, cases: list[dict[str, Any]]) -> None:
    payload = {"suite_id": suite_id, "cases": cases}
    path = results_path(root, suite_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(CASE_MARKER)
    print(json.dumps(payload, ensure_ascii=False))


def load_suite_cases(root: Path, suite_id: str) -> dict[str, Any] | None:
    path = results_path(root, suite_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def validate_suite_cases(
    suite_id: str, declared_case_ids: list[str], payload: dict[str, Any] | None
) -> list[str]:
    if not declared_case_ids:
        return []
    errors: list[str] = []
    if payload is None:
        return [f"{suite_id}: missing structured case results file"]
    if payload.get("suite_id") != suite_id:
        errors.append(f"{suite_id}: results suite_id mismatch")
    rows = payload.get("cases")
    if not isinstance(rows, list):
        return errors + [f"{suite_id}: cases must be a list"]
    seen: list[str] = []
    status_by_id: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            errors.append(f"{suite_id}: invalid case row")
            continue
        case_id = row.get("case_id")
        status = row.get("status")
        if not case_id:
            errors.append(f"{suite_id}: case row missing case_id")
            continue
        seen.append(case_id)
        status_by_id[case_id] = status
        if status not in {"PASS", "FAIL", "SKIP"}:
            errors.append(f"{suite_id}: {case_id} has invalid status {status!r}")
    duplicates = {case for case in seen if seen.count(case) > 1}
    if duplicates:
        errors.append(f"{suite_id}: duplicate case IDs {', '.join(sorted(duplicates))}")
    extra = sorted(set(seen) - set(declared_case_ids))
    if extra:
        errors.append(f"{suite_id}: undeclared case IDs emitted: {', '.join(extra)}")
    for case_id in declared_case_ids:
        if case_id not in status_by_id:
            errors.append(f"{suite_id}: missing declared case {case_id}")
        elif status_by_id[case_id] != "PASS":
            errors.append(f"{suite_id}: case {case_id} status {status_by_id[case_id]!r}")
    return errors


def emit_suite_results(
    root: Path, suite_id: str, cases: list[dict[str, Any]], exit_code: int
) -> None:
    write_suite_cases(root, suite_id, cases)
    sys.exit(exit_code)


def case_pass(case_id: str) -> dict[str, str]:
    return {"case_id": case_id, "status": "PASS"}


def case_fail(case_id: str, message: str = "") -> dict[str, str]:
    row: dict[str, str] = {"case_id": case_id, "status": "FAIL"}
    if message:
        row["message"] = message
    return row
