#!/usr/bin/env python3
"""Finish schema-v4 evidence for cycle 2a/2b/2c subcycles at current HEAD."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = [
    (ROOT / "docs/seven-lens-records/cycle-02-rec-planner.json", "2a"),
    (ROOT / "docs/seven-lens-records/cycle-200-tec-planner.json", "2b"),
    (ROOT / "docs/seven-lens-records/cycle-201-mode-isolation.json", "2c"),
]


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True, check=False)
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _refresh_trace_hashes(record: dict) -> None:
    for row in record.get("evidence_runs", []):
        trace = row.get("runtime_trace")
        if not trace:
            continue
        for key, path_key in (("spec_sha256", "spec_path"), ("artifact_sha256", "artifact_path")):
            rel = trace.get(path_key)
            if rel:
                trace[key] = _sha256(ROOT / rel)


def _retag_receipts(record: dict, tag: str) -> None:
    for row in record.get("evidence_runs", []):
        eid = row["id"]
        row["receipt_path"] = f"dev/seven-lens-evidence-{tag}-{eid}.json"
        row["receipt_sha256"] = ""


def _stamp(record_paths: list[Path], commit: str) -> None:
    for path in record_paths:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        record["verified_source_commit"] = commit
        for row in record.get("evidence_runs", []):
            row["commit"] = commit
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _run_receipts(record_paths: list[Path], commit: str) -> None:
    for record_path in record_paths:
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        for row in record.get("evidence_runs", []):
            row["commit"] = commit
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
                raise RuntimeError(f"evidence {row['id']} failed for {record_path.name}")
            row["receipt_sha256"] = _sha256(receipt_path)
            if row.get("runtime_trace"):
                _refresh_trace_hashes(record)
        record["verified_source_commit"] = commit
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def _update_ledger(commit: str) -> None:
    ledger_path = ROOT / "docs/seven-lens-manual-ledger.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
    for row in ledger.get("reviews", []):
        if row.get("cycle_id") in {"SL-C02", "SL-C200", "SL-C201"} and row.get("review_status") == "SEVEN_LENS_REVIEWED":
            row["verified_source_commit"] = commit
            row["last_checked_commit"] = commit
    ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    record_paths: list[Path] = []
    for path, tag in RECORDS:
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        _retag_receipts(record, tag)
        _refresh_trace_hashes(record)
        path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        record_paths.append(path)

    commit = _git("rev-parse", "HEAD")
    _stamp(record_paths, commit)
    _run_receipts(record_paths, commit)
    _update_ledger(commit)

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
