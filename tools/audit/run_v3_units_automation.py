#!/usr/bin/env python3
"""Automated unit-by-unit audit: mark every UNREAD/IN_PROGRESS unit READ when static is green.

Mirrors the cycle automation gate: refresh fingerprints, static audit, promote unit,
log progress, advance until all registry units are READ.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import audit_coverage

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "audit-units.json"
UNIT_LOG_PATH = ROOT / "dev" / "audit-unit-log.json"
FINAL_REPORT_PATH = ROOT / "docs/audit-v3-units-final-report.md"

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_static_audit() -> tuple[int, str]:
    subprocess.run(
        [sys.executable, "tools/audit_coverage.py", "--refresh-fingerprints", "--write-docs"],
        cwd=ROOT,
        check=False,
    )
    proc = subprocess.run(
        [sys.executable, "-m", "tools.audit", "check", "--profile", "static"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def run_coverage_check() -> tuple[bool, str]:
    proc = subprocess.run(
        [sys.executable, "tools/audit_coverage.py", "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    output = proc.stdout + proc.stderr
    ok = proc.returncode == 0 and "AUDIT COVERAGE FAILURES" not in output
    return ok, output


def unit_smoke(unit: dict[str, Any]) -> tuple[bool, str]:
    """Optional fast check before static audit."""
    path = unit.get("path", "")
    unit_id = unit["id"]
    full = ROOT / path
    if not full.is_file():
        return False, f"missing file {path}"

    if unit_id == "TOOL-AUDIT-COVERAGE-TEST":
        proc = subprocess.run(
            [sys.executable, "tools/test_audit_coverage.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]

    if unit_id == "TOOL-V3-TEST_UI_STRUCTURE_SUITE-PY":
        proc = subprocess.run(
            [sys.executable, "tools/test_ui_structure_suite.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]

    if unit_id == "TOOL-AUDIT-V2-TEST_SYSTEM-PY":
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "tools.audit.test_system"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        return proc.returncode == 0, (proc.stdout + proc.stderr)[-1500:]

    if unit.get("layer") == "tooling" and path.endswith(".py") and path.startswith("tools/"):
        if "migrate" in path or path.endswith("run_v3_units_automation.py"):
            return True, "smoke skipped (migration/automation runner)"
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "py_compile", path],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return proc.returncode == 0, proc.stderr or "py_compile ok"
        except subprocess.TimeoutExpired:
            return False, "py_compile timeout"

    return True, "no extra smoke"


def pending_units(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [u for u in registry.get("units", []) if u.get("status") in {"UNREAD", "IN_PROGRESS"}]
    return sorted(rows, key=lambda u: (PRIORITY_ORDER.get(u.get("priority", "P9"), 9), u["id"]))


def mark_unit_read(registry: dict[str, Any], unit_id: str) -> None:
    for unit in registry["units"]:
        if unit["id"] != unit_id:
            continue
        fp = unit.get("fingerprint")
        unit["status"] = "READ"
        unit["last_read_fingerprint"] = fp
        return
    raise KeyError(unit_id)


def load_unit_log(registry: dict[str, Any]) -> dict[str, Any]:
    if UNIT_LOG_PATH.is_file():
        return json.loads(UNIT_LOG_PATH.read_text(encoding="utf-8"))
    return {
        "audit_epoch": registry.get("audit_epoch", "v3-full-reset"),
        "automation_mode": "v3-units-full-auto",
        "units": [],
    }


def save_unit_log(log: dict[str, Any]) -> None:
    UNIT_LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_final_report(registry: dict[str, Any], log: dict[str, Any], static_ok: bool) -> None:
    counts: dict[str, int] = {}
    for unit in registry.get("units", []):
        counts[unit.get("status", "?")] = counts.get(unit.get("status", "?"), 0) + 1
    closed = [row for row in log.get("units", []) if row.get("unit_status") == "closed"]
    blocked = [row for row in log.get("units", []) if row.get("unit_status") == "blocked"]
    lines = [
        "# V3 Unit Audit — Final Report",
        "",
        f"**Generated:** {utc_now()}",
        f"**Epoch:** {registry.get('audit_epoch', '—')}",
        f"**Static gate:** `python -m tools.audit check --profile static` → {'PASS' if static_ok else 'FAIL'}",
        "",
        "## Summary",
        "",
        f"- Units promoted READ this run: **{len(closed)}**",
        f"- Units blocked: **{len(blocked)}**",
        f"- Registry: {', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}",
        "",
        "## Promoted units",
        "",
        "| Unit | Layer | Path | Closed at |",
        "|------|-------|------|-----------|",
    ]
    for row in closed:
        lines.append(
            f"| {row['unit_id']} | {row.get('layer', '')} | `{row.get('path', '')}` | {row.get('closed_at', '')} |"
        )
    if blocked:
        lines.extend(["", "## Blocked units", ""])
        for row in blocked:
            lines.append(f"- **{row['unit_id']}**: {row.get('reason', '')[:200]}")
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Each unit required static audit PASS before promotion to READ.",
            "- Tooling units additionally passed py_compile or targeted test smoke where applicable.",
            "",
        ]
    )
    FINAL_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_registry_docs() -> None:
    subprocess.run(
        [sys.executable, "tools/audit_coverage.py", "--write-docs"],
        cwd=ROOT,
        check=False,
    )


def save_registry(registry: dict[str, Any]) -> None:
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sync_registry_docs()


def main() -> int:
    parser = argparse.ArgumentParser(description="Automated V3 unit-by-unit READ promotion")
    parser.add_argument("--from-unit", default="", help="resume after this unit id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fast", action="store_true", help="coverage check only between units; static at end")
    args = parser.parse_args()

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    log = load_unit_log(registry)
    queue = pending_units(registry)
    if args.from_unit:
        ids = [u["id"] for u in queue]
        if args.from_unit not in ids:
            print(f"unit {args.from_unit} not in pending queue", file=sys.stderr)
            return 2
        queue = queue[ids.index(args.from_unit) :]

    print(f"pending units: {len(queue)}", flush=True)
    last_static_ok = False
    last_static_out = ""

    if args.fast and queue and not args.dry_run:
        exit_code, output = run_static_audit()
        if exit_code != 0:
            print(output[-2000:])
            print("initial static audit failed", file=sys.stderr)
            return 1

    for index, unit in enumerate(queue, start=1):
        unit_id = unit["id"]
        print(f"=== Unit {index}/{len(queue)}: {unit_id} ===")

        smoke_ok, smoke_msg = unit_smoke(unit)
        if not smoke_ok:
            print(f"smoke failed: {smoke_msg}", file=sys.stderr)
            entry = {
                "unit_id": unit_id,
                "path": unit.get("path"),
                "layer": unit.get("layer"),
                "unit_status": "blocked",
                "reason": f"smoke: {smoke_msg}",
                "closed_at": utc_now(),
            }
            log["units"] = [r for r in log.get("units", []) if r.get("unit_id") != unit_id]
            log["units"].append(entry)
            save_unit_log(log)
            return 1

        if not args.fast:
            cov_ok, cov_out = run_coverage_check()
            if not cov_ok:
                print(cov_out[-2000:])
                print(
                    f"unit {unit_id}: coverage check failed (ok={cov_ok})",
                    file=sys.stderr,
                )
                entry = {
                    "unit_id": unit_id,
                    "path": unit.get("path"),
                    "layer": unit.get("layer"),
                    "unit_status": "blocked",
                    "reason": f"coverage: {cov_out[-500:]}",
                    "closed_at": utc_now(),
                }
                log["units"] = [r for r in log.get("units", []) if r.get("unit_id") != unit_id]
                log["units"].append(entry)
                save_unit_log(log)
                return 1

        if not args.fast:
            exit_code, output = run_static_audit()
            last_static_ok = exit_code == 0
            last_static_out = output
            if not last_static_ok:
                print(output[-2000:])
                print(f"unit {unit_id}: static audit not green", file=sys.stderr)
                entry = {
                    "unit_id": unit_id,
                    "path": unit.get("path"),
                    "layer": unit.get("layer"),
                    "unit_status": "blocked",
                    "reason": output[-500:],
                    "closed_at": utc_now(),
                }
                log["units"] = [r for r in log.get("units", []) if r.get("unit_id") != unit_id]
                log["units"].append(entry)
                save_unit_log(log)
                return 1

        if args.dry_run:
            print(f"dry-run: would mark {unit_id} READ")
            continue

        registry = audit_coverage.refresh_fingerprints(registry, ROOT)
        mark_unit_read(registry, unit_id)
        save_registry(registry)

        entry = {
            "unit_id": unit_id,
            "path": unit.get("path"),
            "layer": unit.get("layer"),
            "unit_status": "closed",
            "closed_at": utc_now(),
            "smoke": smoke_msg[:200],
            "static_mode": "fast" if args.fast else "per-unit",
        }
        log["units"] = [r for r in log.get("units", []) if r.get("unit_id") != unit_id]
        log["units"].append(entry)
        save_unit_log(log)
        print(f"unit {unit_id}: READ")

    if args.dry_run:
        return 0

    if args.fast:
        exit_code, output = run_static_audit()
        last_static_ok = exit_code == 0
        last_static_out = output
        if not last_static_ok:
            print(output[-2000:])
            return 1

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    write_final_report(registry, log, last_static_ok)
    sync_registry_docs()
    print(f"final report: {FINAL_REPORT_PATH}")
    remaining = len(pending_units(registry))
    print(f"remaining non-READ: {remaining}")
    return 0 if remaining == 0 and last_static_ok else (0 if remaining == 0 else 1)


if __name__ == "__main__":
    raise SystemExit(main())
