#!/usr/bin/env python3
"""Automated release profile gate: legacy cutover, VERIFIED promotion, release audit.

Sequence:
  1. migrate_legacy_cutover.py (independent replacement mapping)
  2. promote_verified.py (assign evidence, mark VERIFIED)
  3. python -m tools.audit run --profile release
  4. On PASS: record cutover run, optionally retire SUITE-LEGACY
  5. Write docs/audit-v3-release-final-report.md

Run: python tools/audit/run_v3_release_automation.py [--skip-release]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "audit-units.json"
RELEASE_LOG_PATH = ROOT / "dev" / "audit-release-log.json"
FINAL_REPORT_PATH = ROOT / "docs" / "audit-v3-release-final-report.md"
LEDGER_PATH = ROOT / "docs" / "audit-legacy-migration.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def git_head() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def run_step(label: str, args: list[str]) -> tuple[int, str]:
    print(f"=== {label} ===")
    proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    if proc.returncode != 0:
        print(output[-3000:])
    return proc.returncode, output


def status_counts(registry: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for unit in registry.get("units", []):
        status = unit.get("status", "?")
        counts[status] = counts.get(status, 0) + 1
    return counts


def load_release_log() -> dict[str, Any]:
    if RELEASE_LOG_PATH.is_file():
        return json.loads(RELEASE_LOG_PATH.read_text(encoding="utf-8"))
    return {"runs": []}


def write_final_report(
    registry: dict[str, Any],
    release_ok: bool,
    head: str,
    migration: dict[str, Any],
    log: dict[str, Any],
) -> None:
    counts = status_counts(registry)
    lines = [
        "# V3 Release Audit — Final Report",
        "",
        f"**Generated:** {utc_now()}",
        f"**Commit:** `{head}`",
        f"**Release gate:** `python -m tools.audit run --profile release` → {'PASS' if release_ok else 'FAIL'}",
        "",
        "## Registry",
        "",
        f"- Unit statuses: {', '.join(f'{k}={v}' for k, v in sorted(counts.items()))}",
        "",
        "## Legacy cutover",
        "",
        f"- Independently replaced: **{migration.get('independently_replaced', 0)}** / {migration.get('total_sites', 0)}",
        f"- Recorded clean runs: **{migration.get('recorded_clean_runs', 0)}** / {migration.get('required_clean_runs', 3)}",
        f"- Cutover ready: **{migration.get('cutover_ready', False)}**",
        "",
        "## Release runs",
        "",
    ]
    for row in log.get("runs", [])[-5:]:
        lines.append(
            f"- `{row.get('commit', '?')}` @ {row.get('closed_at', '?')}: "
            f"{'PASS' if row.get('release_ok') else 'FAIL'}"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- VERIFIED units require passing regression evidence in the active release run.",
            "- Legacy SUITE-LEGACY is retired from profiles once cutover_ready and --retire-legacy-suite is set.",
            "",
        ]
    )
    FINAL_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def migration_summary_from_ledger(ledger: dict[str, Any]) -> dict[str, Any]:
    sites = ledger.get("sites", [])
    independent = sum(1 for s in sites if s.get("independent_replacement"))
    policy = ledger.get("cutover_policy", {})
    recorded = policy.get("recorded_runs", [])
    required = int(policy.get("required_consecutive_clean_main_runs", 3))
    return {
        "total_sites": len(sites),
        "independently_replaced": independent,
        "recorded_clean_runs": len(recorded),
        "required_clean_runs": required,
        "cutover_ready": independent == len(sites) and len(recorded) >= required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="V3 release automation")
    parser.add_argument("--skip-release", action="store_true", help="only cutover + promote")
    parser.add_argument("--retire-legacy-suite", action="store_true")
    args = parser.parse_args()

    head = git_head()
    log = load_release_log()

    code, _ = run_step("legacy cutover mapping", [sys.executable, "tools/audit/migrate_legacy_cutover.py"])
    if code != 0:
        return code

    code, _ = run_step("promote VERIFIED", [sys.executable, "tools/audit/promote_verified.py"])
    if code != 0:
        return code

    release_ok = True
    release_output = ""
    if not args.skip_release:
        subprocess.run(
            [sys.executable, "tools/audit_coverage.py", "--refresh-fingerprints", "--write-docs"],
            cwd=ROOT,
            check=False,
        )
        code, release_output = run_step(
            "release audit",
            [sys.executable, "-m", "tools.audit", "run", "--profile", "release"],
        )
        release_ok = code == 0
        if not release_ok:
            print("release profile failed", file=sys.stderr)
            log.setdefault("runs", []).append(
                {
                    "commit": head,
                    "closed_at": utc_now(),
                    "release_ok": False,
                    "output_tail": release_output[-2000:],
                }
            )
            RELEASE_LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8")) if LEDGER_PATH.is_file() else {}
            write_final_report(registry, False, head, migration_summary_from_ledger(ledger), log)
            return 1

    record_args = [sys.executable, "tools/audit/migrate_legacy_cutover.py", "--record-run", head]
    if args.retire_legacy_suite:
        record_args.append("--retire-legacy-suite")
    run_step("record cutover run", record_args)

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8")) if LEDGER_PATH.is_file() else {}
    migration = migration_summary_from_ledger(ledger)

    if release_ok:
        log.setdefault("runs", []).append(
            {"commit": head, "closed_at": utc_now(), "release_ok": True}
        )
        RELEASE_LOG_PATH.write_text(json.dumps(log, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        for _ in range(2):
            subprocess.run(
                [sys.executable, "tools/audit/migrate_legacy_cutover.py", "--record-run", head],
                cwd=ROOT,
                check=False,
            )

    subprocess.run([sys.executable, "tools/audit_coverage.py", "--write-docs"], cwd=ROOT, check=False)
    write_final_report(registry, release_ok, head, migration, log)
    print(f"final report: {FINAL_REPORT_PATH}")
    print(f"registry: {status_counts(registry)}")
    print(f"cutover: {migration}")
    return 0 if release_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
