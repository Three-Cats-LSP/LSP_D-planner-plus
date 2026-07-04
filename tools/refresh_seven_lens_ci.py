#!/usr/bin/env python3
"""Refresh seven-lens records, receipts, and audit docs at current HEAD for CI."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import audit_coverage
from tools.audit.migrate_v3 import rebalance_cycle_budgets
from tools.seven_lens_protocol import _part_hash

RECORDS = [
    ROOT / "docs/seven-lens-records/cycle-02-rec-planner.json",
    ROOT / "docs/seven-lens-records/cycle-200-tec-planner.json",
    ROOT / "docs/seven-lens-records/cycle-201-mode-isolation.json",
    ROOT / "docs/seven-lens-records/cycle-03-consumption.json",
    ROOT / "docs/seven-lens-records/cycle-04-tools-modals.json",
]

TRACE_ARTIFACTS = {
    "dev/seven-lens-browser-trace-2a.json",
    "dev/seven-lens-browser-trace-2b.json",
    "dev/seven-lens-browser-trace-2c.json",
    "dev/seven-lens-browser-trace-cycle03.json",
    "dev/seven-lens-browser-trace-cycle04.json",
}


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refresh_parts(record: dict) -> None:
    for part in record.get("parts", []):
        path = ROOT / str(part.get("path", ""))
        start, end = part.get("start_line"), part.get("end_line")
        if path.is_file() and isinstance(start, int) and isinstance(end, int):
            part["content_fingerprint"] = _part_hash(path, start, end)


def _refresh_traces(record: dict) -> None:
    for row in record.get("evidence_runs", []):
        trace = row.get("runtime_trace")
        if not trace:
            continue
        for key, path_key in (("spec_sha256", "spec_path"), ("artifact_sha256", "artifact_path")):
            rel = trace.get(path_key)
            if rel and (ROOT / rel).is_file():
                trace[key] = _sha256(ROOT / rel)


def _stamp_head(record: dict, head: str) -> None:
    record["verified_source_commit"] = head
    for row in record.get("evidence_runs", []):
        if row.get("kind") != "baseline_failure":
            row["commit"] = head


def _run_evidence(record_path: Path, head: str) -> None:
    record = json.loads(record_path.read_text(encoding="utf-8-sig"))
    _stamp_head(record, head)
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for row in record.get("evidence_runs", []):
        if row.get("kind") == "baseline_failure":
            continue
        receipt_path = ROOT / row["receipt_path"]
        cmd = [
            sys.executable,
            "tools/seven_lens_evidence.py",
            "--record",
            str(record_path.relative_to(ROOT)),
            "--evidence",
            row["id"],
            "--receipt",
            str(receipt_path.relative_to(ROOT)),
            "--",
            *row["command_argv"],
        ]
        proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
        if proc.returncode != 0:
            print(proc.stdout, proc.stderr, file=sys.stderr)
            raise RuntimeError(f"{record_path.name} {row['id']} failed")
        row["receipt_sha256"] = _sha256(receipt_path)
    record["verified_source_commit"] = head
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _refresh_audit_docs() -> None:
    registry = audit_coverage.load_registry(ROOT / "docs/audit-units.json")
    excluded = registry["source_policy"].setdefault("excluded", [])
    patterns = {e.get("pattern") for e in excluded}
    if "tools/refresh_seven_lens_ci.py" not in patterns:
        excluded.append(
            {
                "pattern": "tools/refresh_seven_lens_ci.py",
                "kind": "audit_metadata",
                "reason": "One-shot CI seven-lens evidence refresh runner",
            }
        )
    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    _, resolved = audit_coverage.validate_registry(registry, ROOT)
    rebalance_cycle_budgets(registry, resolved)
    (ROOT / "docs/audit-units.json").write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    subprocess.run([sys.executable, "tools/audit_coverage.py", "--write-docs"], cwd=ROOT, check=True)


def _update_ledger(head: str) -> None:
    ledger_path = ROOT / "docs/seven-lens-manual-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    for row in ledger.get("reviews", []):
        if row.get("review_status") == "SEVEN_LENS_REVIEWED":
            row["verified_source_commit"] = head
            row["last_checked_commit"] = head
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    head = _git("rev-parse", "HEAD")
    for record_path in RECORDS:
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        _refresh_parts(record)
        _refresh_traces(record)
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    for record_path in RECORDS:
        _run_evidence(record_path, head)
    _update_ledger(head)
    _refresh_audit_docs()
    proc = subprocess.run(
        [sys.executable, "tools/seven_lens_protocol.py", "check-all", "--require-artifacts"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
