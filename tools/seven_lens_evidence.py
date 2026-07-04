#!/usr/bin/env python3
"""Execute one declared seven-lens evidence command and write an immutable receipt."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECEIPT_SCHEMA = 1


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )


def _tracked_clean(root: Path) -> bool:
    result = _git(root, "status", "--porcelain", "--untracked-files=all")
    if result.returncode != 0:
        return False
    unexpected = []
    for line in result.stdout.splitlines():
        path = line[3:].replace("\\", "/") if len(line) > 3 else line
        if line.startswith("?? ") and fnmatch.fnmatch(path, "dev/seven-lens-evidence-*.json"):
            continue
        if line[:2] in {" M", "M ", "MM"} and any(
            fnmatch.fnmatch(path, pat)
            for pat in (
                "docs/seven-lens-records/*.json",
                "docs/seven-lens-manual-ledger.json",
                "dev/seven-lens-browser-trace-*.json",
            )
        ):
            continue
        unexpected.append(line)
    return not unexpected


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--execution-root",
        type=Path,
        help="Prepared clean worktree used to execute baseline evidence.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    record_path = args.record if args.record.is_absolute() else ROOT / args.record
    receipt_path = args.receipt if args.receipt.is_absolute() else ROOT / args.receipt
    execution_root = (args.execution_root or ROOT).resolve()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    record = json.loads(record_path.read_text(encoding="utf-8-sig"))
    rows = [row for row in record.get("evidence_runs", []) if row.get("id") == args.evidence]
    if len(rows) != 1:
        print(f"expected one evidence row {args.evidence!r}", file=sys.stderr)
        return 2
    evidence = rows[0]
    declared = evidence.get("command_argv")
    if command != declared:
        print("command does not exactly match record command_argv", file=sys.stderr)
        return 2
    if not command:
        print("empty evidence command", file=sys.stderr)
        return 2
    head = _git(execution_root, "rev-parse", "HEAD")
    if head.returncode != 0:
        print(head.stderr, file=sys.stderr)
        return 2
    commit = head.stdout.strip()
    if evidence.get("commit") != commit:
        print("record evidence commit does not match HEAD", file=sys.stderr)
        return 2
    clean_before = _tracked_clean(execution_root)
    if not clean_before:
        print("evidence command requires a clean tracked worktree", file=sys.stderr)
        return 2

    started = _utc_now()
    result = subprocess.run(command, cwd=execution_root, capture_output=True, check=False)
    finished = _utc_now()
    clean_after = _tracked_clean(execution_root)
    receipt = {
        "schema_version": RECEIPT_SCHEMA,
        "evidence_id": args.evidence,
        "command_argv": command,
        "commit": commit,
        "exit_code": result.returncode,
        "case_ids": evidence.get("case_ids", []),
        "worktree_clean_before": clean_before,
        "worktree_clean_after": clean_after,
        "started_at": started,
        "finished_at": finished,
        "stdout_sha256": _sha256(result.stdout),
        "stderr_sha256": _sha256(result.stderr),
        "executor_sha256": _sha256(Path(__file__).read_bytes()),
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    try:
        display_path = receipt_path.relative_to(ROOT)
    except ValueError:
        display_path = receipt_path
    print(f"receipt: {display_path}")
    print(f"sha256: {_sha256(receipt_path.read_bytes())}")
    if result.stdout:
        sys.stdout.buffer.write(result.stdout)
    if result.stderr:
        sys.stderr.buffer.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
