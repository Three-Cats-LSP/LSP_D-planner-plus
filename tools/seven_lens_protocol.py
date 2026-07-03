#!/usr/bin/env python3
"""Plan and validate manual seven-lens audit-cycle records."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
LENSES = tuple(f"L{i}" for i in range(1, 8))
FINDING_FIELDS = (
    "id", "severity", "unit_id", "location", "root_cause", "failure_path",
    "impact", "evidence", "recommendation", "status",
)
MAX_SESSION_LINES = 600


def _git(*args: str, root: Path = ROOT) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _part_hash(path: Path, start: int, end: int) -> str:
    lines = path.read_bytes().splitlines(keepends=True)
    return hashlib.sha256(b"".join(lines[start - 1:end])).hexdigest()


def _split_boundary(start: int, end: int, size: int = 500) -> list[tuple[int, int]]:
    parts = []
    cursor = start
    while cursor <= end:
        part_end = min(end, cursor + size - 1)
        parts.append((cursor, part_end))
        cursor = part_end + 1
    return parts


def _resolved_registry(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    from tools.audit.registry import load_registry, validate_registry_v2

    registry = load_registry(root)
    errors, resolved = validate_registry_v2(root, registry)
    if errors:
        raise RuntimeError("registry invalid:\n" + "\n".join(errors))
    return registry, resolved


def make_plan(root: Path, cycle_id: int) -> dict[str, Any]:
    registry, resolved = _resolved_registry(root)
    cycle = next((row for row in registry.get("cycles", []) if row.get("cycle") == cycle_id), None)
    if not cycle:
        raise ValueError(f"cycle {cycle_id} is not registered")
    parts = []
    for unit_id in cycle.get("application_units", []):
        unit = resolved[unit_id]
        for index, (start, end) in enumerate(
            _split_boundary(unit["start_line"], unit["end_line"]), 1
        ):
            path = root / unit["path"]
            parts.append({
                "id": f"{unit_id}-P{index:02d}",
                "unit_id": unit_id,
                "path": unit["path"],
                "start_line": start,
                "end_line": end,
                "line_count": end - start + 1,
                "content_fingerprint": _part_hash(path, start, end),
                "review_session": "",
                "verification_session": "",
                "lens_results": {
                    lens: {"trace": "", "boundary_cases": [], "evidence": "", "result": ""}
                    for lens in LENSES
                },
            })
    return {
        "schema_version": 1,
        "cycle": cycle_id,
        "target_branch": "dev",
        "baseline_commit": _git("rev-parse", "HEAD", root=root),
        "audit_commit": "",
        "verified_source_commit": "",
        "verification_status": "PENDING",
        "parts": parts,
        "findings": [],
        "evidence_runs": [],
        "changed_paths": [],
        "notes": "Generated boundaries are review scopes, not permission to skip semantic dependencies.",
    }


def _text(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _attestation_only_path(path: str) -> bool:
    return path.startswith("docs/seven-lens-reports/") or path == "docs/seven-lens-manual-ledger.json"


def _validate_parts(root: Path, record: dict[str, Any], phase: str) -> list[str]:
    errors: list[str] = []
    _, resolved = _resolved_registry(root)
    grouped: dict[str, list[dict[str, Any]]] = {}
    session_lines: dict[tuple[str, str], int] = {}
    for part in record.get("parts", []):
        pid = part.get("id", "<unknown>")
        unit_id = part.get("unit_id")
        if unit_id not in resolved:
            errors.append(f"{pid}: unknown unit {unit_id}")
            continue
        unit = resolved[unit_id]
        grouped.setdefault(unit_id, []).append(part)
        start, end = part.get("start_line"), part.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int) or start > end:
            errors.append(f"{pid}: invalid line boundary")
            continue
        count = end - start + 1
        if part.get("line_count") != count:
            errors.append(f"{pid}: line_count does not match boundary")
        if count > MAX_SESSION_LINES:
            errors.append(f"{pid}: {count} lines exceeds {MAX_SESSION_LINES}")
        path = root / str(part.get("path", ""))
        if not path.is_file() or part.get("path") != unit["path"]:
            errors.append(f"{pid}: canonical path mismatch")
        elif part.get("content_fingerprint") != _part_hash(path, start, end):
            errors.append(f"{pid}: content fingerprint is stale")
        review_session = str(part.get("review_session", "")).strip()
        if not review_session:
            errors.append(f"{pid}: review_session missing")
        else:
            session_lines[("review", review_session)] = session_lines.get(("review", review_session), 0) + count
        lenses = part.get("lens_results", {})
        for lens in LENSES:
            result = lenses.get(lens, {})
            if not _text(result.get("trace"), 20):
                errors.append(f"{pid}/{lens}: concrete trace missing")
            if not isinstance(result.get("boundary_cases"), list) or not result["boundary_cases"]:
                errors.append(f"{pid}/{lens}: boundary_cases missing")
            if not _text(result.get("evidence"), 10):
                errors.append(f"{pid}/{lens}: evidence missing")
            if result.get("result") not in {"NO_FINDING", "FINDING"}:
                errors.append(f"{pid}/{lens}: result must be NO_FINDING or FINDING")
        if phase in {"verify", "close"}:
            verify_session = str(part.get("verification_session", "")).strip()
            if not verify_session:
                errors.append(f"{pid}: verification_session missing")
            elif verify_session == review_session:
                errors.append(f"{pid}: verifier must use a different session")
            else:
                key = ("verify", verify_session)
                session_lines[key] = session_lines.get(key, 0) + count
    for (role, session), count in session_lines.items():
        if count > MAX_SESSION_LINES:
            errors.append(f"{role} session {session!r}: {count} lines exceeds {MAX_SESSION_LINES}")
    for unit_id, parts in grouped.items():
        unit = resolved[unit_id]
        ordered = sorted(parts, key=lambda row: row["start_line"])
        expected = unit["start_line"]
        for part in ordered:
            if part["start_line"] != expected:
                errors.append(f"{unit_id}: gap or overlap before line {part['start_line']}")
            expected = part["end_line"] + 1
        if expected != unit["end_line"] + 1:
            errors.append(f"{unit_id}: coverage ends at {expected - 1}, expected {unit['end_line']}")
    return errors


def _validate_findings(record: dict[str, Any], phase: str) -> list[str]:
    errors: list[str] = []
    evidence_ids = {row.get("id") for row in record.get("evidence_runs", [])}
    ids: set[str] = set()
    for finding in record.get("findings", []):
        fid = finding.get("id", "<unknown>")
        if fid in ids:
            errors.append(f"duplicate finding ID {fid}")
        ids.add(fid)
        for field in FINDING_FIELDS:
            if not _text(finding.get(field), 2):
                errors.append(f"{fid}: {field} missing")
        if finding.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{fid}: invalid severity")
        if finding.get("status") not in {"OPEN", "BLOCKED", "CLOSED"}:
            errors.append(f"{fid}: invalid status")
        if phase in {"verify", "close"} and finding.get("status") == "CLOSED":
            regressions = finding.get("regression_ids", [])
            linked = finding.get("evidence_ids", [])
            if finding.get("severity") in {"CRITICAL", "HIGH", "MEDIUM"} and not regressions:
                errors.append(f"{fid}: closed finding lacks behavioral regression IDs")
            if not linked or any(item not in evidence_ids for item in linked):
                errors.append(f"{fid}: closed finding lacks valid evidence IDs")
    if phase == "close":
        open_ids = [f.get("id") for f in record.get("findings", []) if f.get("status") != "CLOSED"]
        if open_ids:
            errors.append("open findings block closure: " + ", ".join(open_ids))
    return errors


def _validate_evidence(record: dict[str, Any], phase: str) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for row in record.get("evidence_runs", []):
        evidence_id = row.get("id", "<unknown>")
        if evidence_id in seen:
            errors.append(f"duplicate evidence ID {evidence_id}")
        seen.add(evidence_id)
        if not _text(row.get("command"), 5):
            errors.append(f"evidence {evidence_id}: command missing")
        if not _text(row.get("commit"), 7):
            errors.append(f"evidence {evidence_id}: commit missing")
        if not isinstance(row.get("exit_code"), int):
            errors.append(f"evidence {evidence_id}: integer exit_code missing")
        if not isinstance(row.get("worktree_clean"), bool):
            errors.append(f"evidence {evidence_id}: worktree_clean must be boolean")
    if phase in {"verify", "close"} and record.get("verification_status") == "PASSED":
        passed = {
            row.get("id") for row in record.get("evidence_runs", [])
            if row.get("exit_code") == 0 and row.get("worktree_clean") is True
        }
        if missing := {"static", "ci"} - passed:
            errors.append("required clean evidence missing: " + ", ".join(sorted(missing)))
    return errors


def validate_record(root: Path, record: dict[str, Any], phase: str, check_git: bool = True) -> list[str]:
    errors = _validate_parts(root, record, phase)
    errors.extend(_validate_findings(record, phase))
    errors.extend(_validate_evidence(record, phase))
    if record.get("target_branch") != "dev":
        errors.append("target_branch must be dev")
    if phase in {"verify", "close"} and not _text(record.get("audit_commit"), 7):
        errors.append("audit_commit missing")
    if phase in {"verify", "close"} and record.get("verification_status") not in {"PASSED", "BLOCKED"}:
        errors.append("verification_status must be PASSED or BLOCKED")
    if phase in {"verify", "close"} and record.get("verification_status") == "PASSED" and not _text(record.get("verified_source_commit"), 7):
        errors.append("verified_source_commit missing")
    if phase == "close":
        if record.get("verification_status") != "PASSED":
            errors.append("verification_status must be PASSED")
        if not _text(record.get("verified_source_commit"), 7):
            errors.append("verified_source_commit missing")
        if check_git and _git("status", "--porcelain", root=root):
            errors.append("tracked or untracked worktree is not clean")
        if check_git and _text(record.get("verified_source_commit"), 7):
            protected = {part["path"] for part in record.get("parts", [])} | set(record.get("changed_paths", []))
            if _text(record.get("audit_commit"), 7):
                fix_diff = _git(
                    "diff", "--name-only", f"{record['audit_commit']}..{record['verified_source_commit']}",
                    root=root,
                )
                protected.update(
                    path for path in fix_diff.splitlines()
                    if path.strip() and not _attestation_only_path(path)
                )
            paths = sorted(protected)
            if paths:
                changed = _git("diff", "--name-only", f"{record['verified_source_commit']}..HEAD", "--", *paths, root=root)
                if changed:
                    errors.append("reviewed source/test changed after verification: " + changed.replace("\n", ", "))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--cycle", type=int, required=True)
    plan.add_argument("--output", type=Path)
    check = sub.add_parser("check")
    check.add_argument("--phase", choices=("audit", "verify", "close"), required=True)
    check.add_argument("--record", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "plan":
            record = make_plan(ROOT, args.cycle)
            rendered = json.dumps(record, indent=2) + "\n"
            if args.output:
                output = args.output if args.output.is_absolute() else ROOT / args.output
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered, encoding="utf-8")
                print(f"wrote {output.relative_to(ROOT)} with {len(record['parts'])} bounded parts")
            else:
                print(rendered, end="")
            return 0
        record_path = args.record if args.record.is_absolute() else ROOT / args.record
        record = json.loads(record_path.read_text(encoding="utf-8"))
        errors = validate_record(ROOT, record, args.phase)
        if errors:
            print("SEVEN-LENS PROTOCOL: BLOCKED", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
            return 1
        print(f"SEVEN-LENS PROTOCOL: {args.phase.upper()} PASS")
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"SEVEN-LENS PROTOCOL ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
