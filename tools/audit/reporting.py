from __future__ import annotations

import json
from pathlib import Path

from .model import AuditReport


def render_console(report: AuditReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [f"LSP Audit v2 - {report.profile} ({report.commit})", "=" * 60]
    if report.migration:
        lines.append(
            "Legacy migration: "
            f"{report.migration['independently_replaced']}/{report.migration['total_sites']} independently replaced; "
            f"cutover ready={report.migration['cutover_ready']}"
        )
    for error in report.configuration_errors:
        lines.append(f"CONFIG ERROR: {error}")
    for check in report.checks:
        lines.append(f"[{check.status}] {check.id}: {check.message}")
    for suite in report.suites:
        lines.append(f"[{suite.status}] {suite.id} ({suite.duration_ms} ms)")
        if suite.status in {"FAIL", "ERROR"}:
            detail = suite.error or suite.stderr or suite.stdout
            if detail:
                lines.append(detail[-2000:].rstrip())
    for finding in report.invalid_findings:
        lines.append(f"[INVALID] finding {finding['id']}: {finding['reason']}")
    lines.extend(
        [
            "-" * 60,
            f"Checks: {summary['checks_passed']} passed, {summary['checks_failed']} failed",
            f"Suites: {summary['suites_passed']} passed, {summary['suites_failed']} failed, "
            f"{summary['suites_skipped']} skipped",
            f"Verdict: {'PASS' if summary['ok'] else 'FAIL'}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_markdown(report: AuditReport) -> str:
    data = report.to_dict()
    summary = data["summary"]
    lines = [
        "# LSP Audit Report",
        "",
        f"- Profile: `{report.profile}`",
        f"- Commit: `{report.commit}`",
        f"- Verdict: **{'PASS' if summary['ok'] else 'FAIL'}**",
        f"- Static checks: {summary['checks_passed']} passed, {summary['checks_failed']} failed",
        f"- Evidence suites: {summary['suites_passed']} passed, {summary['suites_failed']} failed",
        f"- Legacy migration: {report.migration.get('independently_replaced', 0)}/"
        f"{report.migration.get('total_sites', 0)} independently replaced",
        f"- Cutover ready: **{report.migration.get('cutover_ready', False)}**",
        "",
        "## Static Rules",
        "",
        "| ID | Status | Severity | Units | Location | Message |",
        "|---|---|---|---|---|---|",
    ]
    for item in report.checks:
        location = item.path or "-"
        if item.line:
            location += f":{item.line}"
        lines.append(
            f"| {item.id} | {item.status} | {item.severity} | {', '.join(item.unit_ids)} | "
            f"{location} | {item.message.replace('|', '\\|')} |"
        )
    lines.extend(["", "## Evidence", "", "| Suite | Status | Duration | Command |", "|---|---|---:|---|"])
    for suite in report.suites:
        lines.append(f"| {suite.id} | {suite.status} | {suite.duration_ms} ms | `{' '.join(suite.command)}` |")
    lines.extend(["", "## Effective Unit Status", "", "| Unit | Declared | Effective | Reason |", "|---|---|---|---|"])
    for unit_id, status in sorted(report.effective_units.items()):
        lines.append(f"| {unit_id} | {status['declared']} | {status['effective']} | {status['reason']} |")
    if report.invalid_findings:
        lines.extend(["", "## Invalid Findings", ""])
        for finding in report.invalid_findings:
            lines.append(f"- **{finding['id']}**: {finding['reason']}")
    return "\n".join(lines) + "\n"


def write_reports(root: Path, report: AuditReport) -> None:
    dev = root / "dev"
    dev.mkdir(exist_ok=True)
    (dev / "audit-results.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (dev / "audit-report.md").write_text(render_markdown(report), encoding="utf-8")
