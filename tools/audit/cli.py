from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools import audit_coverage

from .model import AuditReport
from .registry import load_registry, migration_summary, validate_registry_v2
from .reporting import render_console, write_reports
from .rules import evaluate_rules
from .runner import run_suites
from .workspace import commit, restore_generated, snapshot_generated, tracked_status, workspace_changed

ROOT = Path(__file__).resolve().parents[2]


def _case_status(suites: list[Any], suite_id: str, case_id: str) -> str | None:
    for suite in suites:
        if suite.id != suite_id:
            continue
        for row in suite.case_results:
            if row.get("case_id") == case_id:
                return row.get("status")
        return None
    return None


def _evidence_ok(registry: dict[str, Any], suites: list[Any], evidence_id: str) -> tuple[bool, str]:
    spec = registry.get("evidence_catalog", {}).get(evidence_id)
    if not spec:
        return False, "unknown evidence"
    suite_id = spec["suite_id"]
    case_id = spec["case_id"]
    status = _case_status(suites, suite_id, case_id)
    if status is None:
        return False, f"case {case_id} not emitted by {suite_id}"
    if status != "PASS":
        return False, f"case {case_id} status {status}"
    return True, "ok"


def effective_statuses(
    registry: dict[str, Any], resolved: dict[str, dict[str, Any]], suites: list[Any]
) -> dict[str, dict[str, str]]:
    suite_status = {suite.id: suite.status for suite in suites}
    evidence = registry.get("evidence_catalog", {})
    output: dict[str, dict[str, str]] = {}
    for unit in registry.get("units", []):
        unit_id = unit["id"]
        declared = unit["status"]
        effective = declared
        reason = "current fingerprint"
        current = resolved.get(unit_id, {}).get("current_fingerprint")
        if unit.get("fingerprint") != current or (
            declared in {"READ", "VERIFIED"} and unit.get("last_read_fingerprint") != current
        ):
            effective, reason = "IN_PROGRESS", "stale fingerprint"
        elif declared == "VERIFIED":
            required_cases = list(unit.get("regression_cases", []))
            bad_cases = []
            missing_cases = []
            for evidence_id in required_cases:
                ok, reason = _evidence_ok(registry, suites, evidence_id)
                if not ok:
                    if "not emitted" in reason:
                        missing_cases.append(evidence_id)
                    else:
                        bad_cases.append(f"{evidence_id} ({reason})")
            if bad_cases:
                effective, reason = "READ", f"failed evidence: {', '.join(bad_cases)}"
            elif missing_cases:
                effective, reason = "READ", f"evidence not executed: {', '.join(missing_cases)}"
            else:
                reason = "fingerprint current and all evidence cases passed"
        output[unit_id] = {"declared": declared, "effective": effective, "reason": reason}
    return output


def invalid_closed_findings(
    registry: dict[str, Any], suites: list[Any], require_all: bool = False
) -> list[dict[str, str]]:
    suite_status = {suite.id: suite.status for suite in suites}
    evidence = registry.get("evidence_catalog", {})
    invalid = []
    for finding in registry.get("findings", []):
        if finding.get("status") != "CLOSED":
            continue
        bad = []
        missing = []
        for evidence_id in finding.get("evidence_cases", []):
            ok, reason = _evidence_ok(registry, suites, evidence_id)
            if not ok:
                if require_all or "not emitted" not in reason:
                    bad.append(f"{evidence_id}: {reason}")
                elif "not emitted" in reason:
                    missing.append(evidence_id)
        if bad:
            invalid.append({"id": finding["id"], "reason": "; ".join(bad)})
            continue
        if require_all and missing:
            invalid.append({
                "id": finding["id"],
                "reason": f"required release evidence was not executed: {', '.join(missing)}",
            })
    return invalid


def execute(command_name: str, profile: str) -> int:
    baseline = tracked_status(ROOT)
    try:
        registry = load_registry(ROOT)
        errors, resolved = validate_registry_v2(ROOT, registry)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Audit configuration error: {exc}", file=sys.stderr)
        return 2
    report = AuditReport(
        schema_version=2, profile=profile, command=command_name,
        commit=commit(ROOT), configuration_errors=errors,
    )
    try:
        report.migration = migration_summary(ROOT)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report.configuration_errors.append(f"migration summary unavailable: {exc}")
    generated_snapshot, generated_original = snapshot_generated(ROOT, registry)
    if not errors:
        checks, parser_errors = evaluate_rules(ROOT, registry)
        report.checks = checks
        report.configuration_errors.extend(parser_errors)
        if not parser_errors:
            report.suites = run_suites(ROOT, registry, profile)
        report.effective_units = effective_statuses(registry, resolved, report.suites)
        report.invalid_findings = invalid_closed_findings(
            registry, report.suites, require_all=profile == "release"
        )
    restore_generated(ROOT, registry, generated_snapshot, generated_original)
    report.workspace_clean, report.workspace_drift = workspace_changed(ROOT, baseline)
    write_reports(ROOT, report)
    print(render_console(report), end="")
    if report.configuration_errors:
        return 2
    return 1 if report.failed else 0


def refresh(unit_id: str) -> int:
    registry = load_registry(ROOT)
    if unit_id != "all" and unit_id not in {unit["id"] for unit in registry.get("units", [])}:
        print(f"Unknown audit unit: {unit_id}", file=sys.stderr)
        return 2
    refreshed = audit_coverage.refresh_fingerprints(registry, ROOT)
    if unit_id != "all":
        old = load_registry(ROOT)
        keep = {unit["id"]: unit for unit in old["units"] if unit["id"] != unit_id}
        refreshed["units"] = [keep.get(unit["id"], unit) for unit in refreshed["units"]]
    registry_path = ROOT / "docs" / "audit-units.json"
    registry_path.write_text(json.dumps(refreshed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Refreshed fingerprints for {unit_id}")
    return 0


def legacy(extra: list[str]) -> int:
    return subprocess.call([sys.executable, str(ROOT / "tools" / "audit" / "legacy_v1.py"), *extra], cwd=ROOT)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LSP registry-driven audit platform")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "run"):
        child = sub.add_parser(name)
        child.add_argument("--profile", choices=("static", "ci", "release"), default="static" if name == "check" else "ci")
    child = sub.add_parser("refresh")
    child.add_argument("--unit", default="all")
    legacy_parser = sub.add_parser("legacy")
    legacy_parser.add_argument("args", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command in {"check", "run"}:
        return execute(args.command, args.profile)
    if args.command == "refresh":
        return refresh(args.unit)
    return legacy(args.args)
