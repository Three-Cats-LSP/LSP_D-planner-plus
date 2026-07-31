#!/usr/bin/env python3
"""Recalculate V5 R-cycle metadata and guard against live pre-R case IDs."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import audit_coverage

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "audit-units.json"
REPORT = ROOT / "docs" / "seven-lens-reports" / "v5-pre-r-legacy-migration.md"
ACTIVE_CASE_ID_RE = re.compile(r"\bSL-C\d{2,3}-[A-Z0-9-]+\b")
ACTIVE_SUITE_FILES = [
    ROOT / "dev" / "engine_regression.py",
    ROOT / "dev" / "ui_css_regression.py",
    ROOT / "dev" / "ui_controls_css_regression.py",
    ROOT / "dev" / "ui_results_css_regression.py",
    ROOT / "dev" / "ui_shell_results_regression.py",
    ROOT / "dev" / "ui_visual_contract_regression.py",
]


def write_lf(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def save_registry(registry: dict[str, Any]) -> None:
    write_lf(REGISTRY, json.dumps(registry, indent=2) + "\n")


def session_count(lines: int) -> int:
    return max(1, (max(0, lines) + 599) // 600)


def recalc_cycles(registry: dict[str, Any], *, write: bool) -> list[str]:
    errors: list[str] = []
    resolved, resolve_errors = audit_coverage.resolve_units(registry, ROOT)
    errors.extend(resolve_errors)
    if errors:
        return errors

    for cycle in registry.get("cycles", []):
        unit_ids = cycle.get("application_units", [])
        missing = [unit_id for unit_id in unit_ids if unit_id not in resolved]
        if missing:
            errors.append(f"{cycle.get('cycle')}: unknown application_units {', '.join(missing)}")
            continue
        total = sum(resolved[unit_id]["line_count"] for unit_id in unit_ids)
        sessions = session_count(total)
        old_total = cycle.get("max_new_application_lines")
        old_sessions = cycle.get("min_review_sessions", 1)
        acceptance = cycle.get("acceptance", "")
        new_acceptance = re.sub(
            r"current lines: \d+; sessions: \d+",
            f"current lines: {total}; sessions: {sessions}",
            acceptance,
        )
        if new_acceptance == acceptance and "current lines:" not in acceptance:
            suffix = f"; current lines: {total}; sessions: {sessions}"
            new_acceptance = acceptance.rstrip(".") + suffix
        if write:
            cycle["max_new_application_lines"] = total
            if sessions > 1:
                cycle["min_review_sessions"] = sessions
            else:
                cycle.pop("min_review_sessions", None)
            cycle["acceptance"] = new_acceptance
        else:
            if old_total != total:
                errors.append(f"{cycle.get('cycle')}: max_new_application_lines {old_total} != {total}")
            if old_sessions != sessions:
                errors.append(f"{cycle.get('cycle')}: min_review_sessions {old_sessions} != {sessions}")
            if acceptance != new_acceptance:
                errors.append(f"{cycle.get('cycle')}: acceptance line count/session text is stale")

    return errors


def active_suite_legacy_ids() -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {}
    for path in ACTIVE_SUITE_FILES:
        if not path.exists():
            continue
        ids = sorted(set(ACTIVE_CASE_ID_RE.findall(path.read_text(encoding="utf-8"))))
        if ids:
            hits[str(path.relative_to(ROOT))] = ids
    return hits


def evidence_catalog_legacy_case_ids(registry: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for reg_id, entry in registry.get("evidence_catalog", {}).items():
        case_id = entry.get("case_id", "")
        if ACTIVE_CASE_ID_RE.fullmatch(case_id):
            out.append(f"{reg_id}: {case_id}")
    return sorted(out)


def render_report(registry: dict[str, Any]) -> str:
    aliases = registry.get("frozen_history", {}).get("promoted_case_aliases", [])
    old_record_paths = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "docs").glob("seven-lens-records/cycle-*.json"))
    old_report_paths = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "docs").glob("seven-lens-reports/cycle-*.json"))
    old_trace_paths = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "docs").glob("seven-lens-traces/cycle-*.json"))
    old_evidence_paths = sorted(str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "dev").glob("seven-lens-evidence-c*.json"))
    delete_candidates = []
    if not (ROOT / "font-readability-mockups.html").exists():
        delete_candidates.append("font-readability-mockups.html (deleted; implemented temporary mockup)")

    lines = [
        "# V5 Pre-R Legacy Migration",
        "",
        "## What Was Done",
        "",
        "- Set the active audit epoch to `v5-risk-first-active`.",
        "- Promoted useful live `SL-Cxx-*` regression case IDs into V5/R-era IDs.",
        "- Preserved old IDs as `legacy_aliases` in `docs/audit-units.json` for searchability.",
        "- Marked pre-R cycle records, trace specs, and evidence receipts as archive-only historical data.",
        "- Added `tools/v5_audit_recalc.py --write/--check` to recalculate active R-cycle line counts and reject live pre-R IDs.",
        "",
        "## Why",
        "",
        "The old Cycle 1-9/200 closure system kept reinterpreting historical records whenever modern source files moved. V5 keeps the useful regression checks, but removes old closure bookkeeping from the active release path.",
        "",
        "## Promote",
        "",
        "| Legacy case | V5 case |",
        "|---|---|",
    ]
    for alias in aliases:
        lines.append(f"| `{alias['legacy']}` | `{alias['v5']}` |")

    def list_paths(title: str, paths: list[str], limit: int | None = None) -> None:
        lines.extend(["", f"## {title}", ""])
        shown = paths if limit is None else paths[:limit]
        if not shown:
            lines.append("- None")
        for path in shown:
            lines.append(f"- `{path}`")
        if limit is not None and len(paths) > limit:
            lines.append(f"- ... {len(paths) - limit} more archived paths")

    list_paths("Archive Only Records", old_record_paths)
    list_paths("Archive Only Reports", old_report_paths, 20)
    list_paths("Archive Only Trace Specs", old_trace_paths)
    list_paths("Archive Only Evidence Receipts", old_evidence_paths, 30)
    list_paths("Delete", delete_candidates)

    lines.extend([
        "",
        "## Active Workflow From Now On",
        "",
        "- Run `python tools/v5_audit_recalc.py --write` after source restructuring.",
        "- Run `python tools/v5_audit_recalc.py --check` in gates to catch stale R-cycle metadata and active old IDs early.",
        "- Do not repair old `cycle-*` line boundaries during normal development; they are frozen history.",
        "- Keep `index.html` generated from canonical `ui/*.html`, runtime `.js`, and source `.css`.",
    ])
    return "\n".join(lines) + "\n"


def run_audit_docs(write: bool) -> int:
    cmd = [sys.executable, "tools/audit_coverage.py", "--write-docs" if write else "--check"]
    proc = subprocess.run(cmd, cwd=ROOT)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true", help="refresh V5 cycle metadata, docs, and migration report")
    mode.add_argument("--check", action="store_true", help="fail on stale V5 cycle metadata or live pre-R case IDs")
    args = parser.parse_args()

    registry = load_registry()
    if registry.get("audit_epoch") != "v5-risk-first-active":
        if args.write:
            registry["audit_epoch"] = "v5-risk-first-active"
        else:
            print("V5 audit recalc FAIL: audit_epoch is not v5-risk-first-active")
            return 1

    errors = recalc_cycles(registry, write=args.write)
    suite_hits = active_suite_legacy_ids()
    if suite_hits:
        for rel, ids in suite_hits.items():
            errors.append(f"{rel}: active suite still emits pre-R IDs {', '.join(ids)}")
    catalog_hits = evidence_catalog_legacy_case_ids(registry)
    if catalog_hits:
        errors.append("evidence_catalog active case_id still uses pre-R IDs: " + "; ".join(catalog_hits))

    if args.write:
        save_registry(registry)
        write_lf(REPORT, render_report(registry))
        rc = run_audit_docs(write=True)
        if rc:
            return rc
        print(f"V5 audit recalc wrote registry, generated docs, and {REPORT.relative_to(ROOT)}")
        return 0

    if errors:
        print("V5 audit recalc FAIL:")
        for error in errors:
            print(f"  - {error}")
        return 1

    expected_report = render_report(registry)
    if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != expected_report:
        print(f"V5 audit recalc FAIL: {REPORT.relative_to(ROOT)} is stale")
        return 1
    rc = run_audit_docs(write=False)
    if rc:
        return rc
    print("V5 audit recalc OK: active R-cycles current; no live pre-R case IDs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
