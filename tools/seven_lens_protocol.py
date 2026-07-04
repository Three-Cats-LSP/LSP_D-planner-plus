#!/usr/bin/env python3
"""Plan and validate manual seven-lens audit-cycle records."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
TRACE_STAGES = {"input", "canonical", "consumer", "observable"}
CURRENT_RECORD_SCHEMA = 4
EVIDENCE_RECEIPT_SCHEMA = 1


def _git(*args: str, root: Path = ROOT) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False,
    )
    if proc.returncode:
        raise RuntimeError(proc.stderr.strip() or f"git {' '.join(args)} failed")
    return proc.stdout.strip()


def _git_ok(*args: str, root: Path = ROOT) -> bool:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False,
    ).returncode == 0


def _normalize_file_bytes(data: bytes) -> bytes:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return data
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(_normalize_file_bytes(path.read_bytes())).hexdigest()


def _part_hash(path: Path, start: int, end: int) -> str:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    lines = text.splitlines(keepends=True)
    if start < 1 or end < start or start > len(lines):
        return hashlib.sha256(b"").hexdigest()
    segment = "".join(lines[start - 1 : end])
    normalized = segment.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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
    structural_errors = [
        error for error in errors
        if not error.startswith("release-blocking finding remains open:")
    ]
    if structural_errors:
        raise RuntimeError("registry invalid:\n" + "\n".join(structural_errors))
    return registry, resolved


def make_plan(root: Path, cycle_id: int) -> dict[str, Any]:
    registry, resolved = _resolved_registry(root)
    if _git("status", "--porcelain", root=root):
        raise RuntimeError("plan requires a clean worktree")
    head = _git("rev-parse", "HEAD", root=root)
    integration_base = _git("rev-parse", "origin/dev", root=root)
    if head != integration_base:
        raise RuntimeError(
            "plan must run before cycle work begins: HEAD must equal origin/dev"
        )
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
        "schema_version": CURRENT_RECORD_SCHEMA,
        "cycle": cycle_id,
        "record_path": "",
        "target_branch": "dev",
        "integration_base_commit": integration_base,
        "baseline_commit": head,
        "baseline_registry_fingerprint": hashlib.sha256(
            (root / "docs" / "audit-units.json").read_text(encoding="utf-8").strip().encode("utf-8")
        ).hexdigest(),
        "baseline_findings": [
            {
                "id": row.get("id"),
                "severity": row.get("severity"),
                "status": row.get("status"),
                "summary": row.get("summary", ""),
            }
            for row in registry.get("findings", [])
        ],
        "audit_commit": "",
        "verified_source_commit": "",
        "verification_status": "PENDING",
        "parts": parts,
        "findings": [],
        "evidence_runs": [],
        "changed_paths": [],
        "audit_report": "",
        "notes": "Generated boundaries are review scopes, not permission to skip semantic dependencies.",
    }


def _text(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _validate_evidence_receipt(root: Path, evidence: dict[str, Any]) -> list[str]:
    evidence_id = evidence.get("id", "<unknown>")
    errors: list[str] = []
    argv = evidence.get("command_argv")
    if not isinstance(argv, list) or not argv or not all(_text(item) for item in argv):
        errors.append(f"evidence {evidence_id}: command_argv must be a non-empty string list")
    receipt_path = evidence.get("receipt_path")
    receipt_hash = evidence.get("receipt_sha256")
    if not _text(receipt_path, 5):
        errors.append(f"evidence {evidence_id}: receipt_path missing")
        return errors
    if not _text(receipt_hash, 64):
        errors.append(f"evidence {evidence_id}: receipt_sha256 missing")
    receipt_file = root / receipt_path
    if not receipt_file.is_file():
        errors.append(f"evidence {evidence_id}: receipt is missing: {receipt_path}")
        return errors
    actual_hash = _file_sha256(receipt_file)
    if actual_hash != receipt_hash:
        errors.append(f"evidence {evidence_id}: receipt hash does not match")
        return errors
    try:
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"evidence {evidence_id}: receipt is malformed: {exc}")
        return errors
    expected = {
        "schema_version": EVIDENCE_RECEIPT_SCHEMA,
        "evidence_id": evidence_id,
        "command_argv": argv,
        "commit": evidence.get("commit"),
        "exit_code": evidence.get("exit_code"),
        "case_ids": evidence.get("case_ids", []),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            errors.append(f"evidence {evidence_id}: receipt {field} does not match record")
    for field in ("started_at", "finished_at", "stdout_sha256", "stderr_sha256"):
        if not _text(receipt.get(field), 10):
            errors.append(f"evidence {evidence_id}: receipt {field} missing")
    executor = root / "tools" / "seven_lens_evidence.py"
    expected_executor = _file_sha256(executor) if executor.is_file() else ""
    if receipt.get("executor_sha256") != expected_executor:
        errors.append(f"evidence {evidence_id}: receipt executor fingerprint is stale")
    if receipt.get("worktree_clean_before") is not True:
        errors.append(f"evidence {evidence_id}: receipt started from a dirty worktree")
    if receipt.get("worktree_clean_after") is not True:
        errors.append(f"evidence {evidence_id}: receipt left tracked worktree changes")
    return errors


def _attestation_only_path(path: str) -> bool:
    return (
        path.startswith("docs/seven-lens-reports/")
        or path.startswith("docs/seven-lens-records/")
        or path == "docs/seven-lens-manual-ledger.json"
    )


def _audit_metadata_path(path: str) -> bool:
    return (
        _attestation_only_path(path)
        or path.startswith("docs/seven-lens-traces/")
        or path in {
            "docs/audit-units.json",
            "docs/audit-coverage.md",
            "docs/audit-master-plan.md",
        }
    )


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
            if finding.get("severity") in {"CRITICAL", "HIGH", "MEDIUM"}:
                if not _text(finding.get("observable_contract"), 20):
                    errors.append(f"{fid}: observable_contract missing")
                before_id = finding.get("pre_fix_evidence_id")
                after_id = finding.get("post_fix_evidence_id")
                restore_id = finding.get("state_restoration_evidence_id")
                for label, evidence_id in (
                    ("pre_fix_evidence_id", before_id),
                    ("post_fix_evidence_id", after_id),
                    ("state_restoration_evidence_id", restore_id),
                ):
                    if evidence_id not in evidence_ids:
                        errors.append(f"{fid}: {label} is missing or unknown")
    if phase == "close":
        open_ids = [f.get("id") for f in record.get("findings", []) if f.get("status") != "CLOSED"]
        if open_ids:
            errors.append("open findings block closure: " + ", ".join(open_ids))
    return errors


def _validate_evidence(
    root: Path, record: dict[str, Any], phase: str, check_git: bool
) -> list[str]:
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
        elif check_git and phase in {"verify", "close"} and not _git_ok(
            "cat-file", "-e", f"{row['commit']}^{{commit}}", root=root
        ):
            errors.append(f"evidence {evidence_id}: commit does not exist")
        if not isinstance(row.get("exit_code"), int):
            errors.append(f"evidence {evidence_id}: integer exit_code missing")
        if not isinstance(row.get("worktree_clean"), bool):
            errors.append(f"evidence {evidence_id}: worktree_clean must be boolean")
        if row.get("kind") not in {"baseline_failure", "post_fix", "state_restoration", "gate"}:
            errors.append(f"evidence {evidence_id}: invalid kind")
        if not isinstance(row.get("case_ids"), list):
            errors.append(f"evidence {evidence_id}: case_ids must be a list")
        if row.get("kind") in {"baseline_failure", "post_fix", "state_restoration"}:
            if not row.get("case_ids"):
                errors.append(f"evidence {evidence_id}: behavioral evidence needs case_ids")
            if not isinstance(row.get("observable_assertions"), list) or not row.get("observable_assertions"):
                errors.append(f"evidence {evidence_id}: observable_assertions missing")
            if not isinstance(row.get("state_restored"), bool):
                errors.append(f"evidence {evidence_id}: state_restored must be boolean")
        if row.get("kind") == "state_restoration" and (
            record.get("schema_version", 1) >= 2 or record.get("verification_status") == "PASSED"
        ):
            before = row.get("state_before_sha256")
            after = row.get("state_after_sha256")
            if not (_text(before, 64) and _text(after, 64)):
                errors.append(f"evidence {evidence_id}: state snapshot hashes missing")
            elif before != after:
                errors.append(f"evidence {evidence_id}: before/after state snapshots differ")
        if row.get("kind") == "baseline_failure" and row.get("exit_code") == 0:
            errors.append(f"evidence {evidence_id}: baseline failure must fail before the fix")
        if row.get("kind") in {"post_fix", "state_restoration", "gate"} and row.get("exit_code") != 0:
            errors.append(f"evidence {evidence_id}: passing evidence has nonzero exit_code")
        if (
            phase == "close"
            and record.get("schema_version", 1) >= 3
            and row.get("kind") in {"post_fix", "state_restoration", "gate"}
            and row.get("commit") != record.get("verified_source_commit")
        ):
            errors.append(f"evidence {evidence_id}: must run at verified_source_commit")
        if record.get("schema_version", 1) >= CURRENT_RECORD_SCHEMA and phase in {"verify", "close"}:
            errors.extend(_validate_evidence_receipt(root, row))
    if phase in {"verify", "close"} and record.get("verification_status") == "PASSED":
        passed = {
            row.get("id") for row in record.get("evidence_runs", [])
            if row.get("exit_code") == 0 and row.get("worktree_clean") is True
        }
        if missing := {"static", "ci"} - passed:
            errors.append("required clean evidence missing: " + ", ".join(sorted(missing)))
    return errors


def _validate_trace_artifact(
    root: Path,
    fid: str,
    trace: dict[str, Any],
    require_artifacts: bool,
    *,
    expected_commit: str = "",
    required_case_ids: set[str] | None = None,
    current_schema: bool = False,
) -> list[str]:
    errors: list[str] = []
    artifact_path = trace.get("artifact_path")
    artifact_hash = trace.get("artifact_sha256")
    trace_id = trace.get("trace_id")
    if not _text(trace_id, 5):
        errors.append(f"{fid}: post-fix browser trace lacks trace_id")
    if not _text(artifact_hash, 64):
        errors.append(f"{fid}: post-fix browser trace lacks artifact hash")
    if not _text(artifact_path, 5):
        errors.append(f"{fid}: post-fix browser trace lacks artifact path")
        return errors
    artifact = root / artifact_path
    if not artifact.is_file():
        if require_artifacts:
            errors.append(f"{fid}: browser trace artifact is missing: {artifact_path}")
        return errors
    if _file_sha256(artifact) != artifact_hash:
        errors.append(f"{fid}: browser trace artifact hash does not match")
        return errors
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{fid}: browser trace artifact is malformed: {exc}")
        return errors
    if payload.get("passed") is not True:
        errors.append(f"{fid}: browser trace artifact did not pass")
    if expected_commit and payload.get("commit") != expected_commit:
        errors.append(f"{fid}: browser trace artifact commit does not match evidence commit")
    if current_schema:
        spec_path = trace.get("spec_path")
        spec_hash = trace.get("spec_sha256")
        if not _text(spec_path, 5) or not _text(spec_hash, 64):
            errors.append(f"{fid}: browser trace lacks immutable spec path/hash")
        else:
            spec_file = root / spec_path
            if not spec_file.is_file():
                errors.append(f"{fid}: browser trace spec is missing: {spec_path}")
            elif _file_sha256(spec_file) != spec_hash:
                errors.append(f"{fid}: browser trace spec hash does not match")
            if payload.get("spec_sha256") != spec_hash:
                errors.append(f"{fid}: artifact/spec fingerprint mismatch")
        if payload.get("schema_version") != 3 or payload.get("runner_version", 0) < 2:
            errors.append(f"{fid}: browser trace artifact uses an obsolete schema/runner")
    rows = [row for row in payload.get("traces", []) if row.get("id") == trace_id]
    if len(rows) != 1:
        errors.append(f"{fid}: browser trace artifact must contain trace {trace_id} exactly once")
        return errors
    row = rows[0]
    if required_case_ids and not required_case_ids.issubset(set(row.get("case_ids", []))):
        errors.append(f"{fid}: browser trace does not declare every finding regression case")
    if row.get("passed") is not True or row.get("repeatable") is not True:
        errors.append(f"{fid}: browser trace is not passing and repeatable")
    if row.get("state_restored") is not True:
        errors.append(f"{fid}: browser trace did not restore state")
    if row.get("console_errors") or row.get("page_errors"):
        errors.append(f"{fid}: browser trace emitted console/page errors")
    assertions = row.get("assertions", [])
    if not assertions or any(item.get("passed") is not True for item in assertions):
        errors.append(f"{fid}: browser trace lacks a complete passing assertion set")
    return errors


def _validate_closed_finding_evidence(
    root: Path, record: dict[str, Any], phase: str, require_artifacts: bool = True
) -> list[str]:
    if phase not in {"verify", "close"}:
        return []
    errors: list[str] = []
    evidence = {row.get("id"): row for row in record.get("evidence_runs", [])}
    for finding in record.get("findings", []):
        if finding.get("status") != "CLOSED" or finding.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM"}:
            continue
        fid = finding.get("id", "<unknown>")
        regressions = set(finding.get("regression_ids", []))
        before = evidence.get(finding.get("pre_fix_evidence_id"), {})
        after = evidence.get(finding.get("post_fix_evidence_id"), {})
        restore = evidence.get(finding.get("state_restoration_evidence_id"), {})
        if before.get("kind") != "baseline_failure" or before.get("exit_code") == 0:
            errors.append(f"{fid}: pre-fix evidence does not demonstrate failure")
        if after.get("kind") != "post_fix" or after.get("exit_code") != 0:
            errors.append(f"{fid}: post-fix evidence does not demonstrate success")
        if not regressions.issubset(set(after.get("case_ids", []))):
            errors.append(f"{fid}: post-fix evidence does not emit every regression ID")
        if restore.get("kind") != "state_restoration" or restore.get("state_restored") is not True:
            errors.append(f"{fid}: state restoration evidence is not clean")
        trace = after.get("runtime_trace", {})
        if record.get("schema_version", 1) >= 2:
            if not _text(trace.get("entry_event"), 5):
                errors.append(f"{fid}: post-fix browser trace lacks an entry event")
            consumers = trace.get("consumer_path", [])
            if not isinstance(consumers, list) or not consumers:
                errors.append(f"{fid}: post-fix browser trace lacks consumer path")
            captures = trace.get("captures", [])
            stages = {
                item.get("stage") for item in captures if isinstance(item, dict)
            } if isinstance(captures, list) else set()
            if not TRACE_STAGES.issubset(stages):
                missing = ", ".join(sorted(TRACE_STAGES - stages))
                errors.append(f"{fid}: post-fix browser trace lacks stages: {missing}")
            errors.extend(_validate_trace_artifact(
                root,
                fid,
                trace,
                require_artifacts,
                expected_commit=str(after.get("commit", "")),
                required_case_ids=regressions,
                current_schema=record.get("schema_version", 1) >= CURRENT_RECORD_SCHEMA,
            ))
    return errors


def _validate_finding_continuity(
    registry: dict[str, Any], record: dict[str, Any], phase: str
) -> list[str]:
    if record.get("schema_version", 1) < 2 or phase not in {"audit", "verify", "close"}:
        return []
    errors: list[str] = []
    baseline = {row.get("id"): row for row in record.get("baseline_findings", [])}
    current = {row.get("id"): row for row in registry.get("findings", [])}
    cycle_findings = {row.get("id"): row for row in record.get("findings", [])}
    for finding_id, old in baseline.items():
        if not finding_id:
            errors.append("baseline finding without id")
            continue
        new = current.get(finding_id)
        if new is None:
            errors.append(f"historical finding {finding_id} was deleted")
            continue
        if SEVERITY_RANK.get(new.get("severity"), 0) < SEVERITY_RANK.get(old.get("severity"), 0):
            errors.append(f"historical finding {finding_id} severity was downgraded")
        if old.get("status") != "CLOSED" and new.get("status") == "CLOSED":
            cycle_copy = cycle_findings.get(finding_id, {})
            if cycle_copy.get("status") != "CLOSED" or not cycle_copy.get("evidence_ids"):
                errors.append(
                    f"historical finding {finding_id} closed without this cycle's evidence"
                )
    return errors


def _validate_audit_checkpoint(root: Path, record: dict[str, Any], check_git: bool) -> list[str]:
    if not check_git:
        return []
    errors: list[str] = []
    baseline = str(record.get("baseline_commit", ""))
    audit = str(record.get("audit_commit", ""))
    verified = str(record.get("verified_source_commit", ""))
    if not (_text(baseline, 7) and _text(audit, 7)):
        return errors
    if baseline == audit:
        errors.append("audit_commit must be a report-only commit after baseline")
        return errors
    if not _git_ok("merge-base", "--is-ancestor", baseline, audit, root=root):
        errors.append("audit_commit is not descended from baseline_commit")
        return errors
    if record.get("schema_version", 1) >= 2:
        try:
            base_registry_text = _git(
                "show", f"{baseline}:docs/audit-units.json", root=root
            )
            base_registry = json.loads(base_registry_text)
            actual_hash = hashlib.sha256(base_registry_text.encode("utf-8")).hexdigest()
            if actual_hash != record.get("baseline_registry_fingerprint"):
                errors.append("baseline registry fingerprint does not match git history")
            expected_findings = [
                {
                    "id": row.get("id"),
                    "severity": row.get("severity"),
                    "status": row.get("status"),
                    "summary": row.get("summary", ""),
                }
                for row in base_registry.get("findings", [])
            ]
            if expected_findings != record.get("baseline_findings"):
                errors.append("baseline finding snapshot does not match git history")
        except (RuntimeError, json.JSONDecodeError) as exc:
            errors.append(f"cannot verify baseline registry: {exc}")
        try:
            remote_base = _git("merge-base", audit, "origin/dev", root=root)
            if remote_base != baseline:
                errors.append(
                    "baseline_commit is not the cycle branch point from origin/dev"
                )
        except RuntimeError as exc:
            errors.append(f"cannot verify origin/dev branch point: {exc}")
    if record.get("schema_version", 1) >= 3:
        record_path = str(record.get("record_path", ""))
        if _text(record_path, 5):
            try:
                audit_record = json.loads(_git("show", f"{audit}:{record_path}", root=root))
                audit_findings = {row.get("id"): row for row in audit_record.get("findings", [])}
                current_findings = {row.get("id"): row for row in record.get("findings", [])}
                for finding_id, old in audit_findings.items():
                    new = current_findings.get(finding_id)
                    if new is None:
                        errors.append(f"audit finding {finding_id} was deleted from the cycle record")
                        continue
                    if SEVERITY_RANK.get(new.get("severity"), 0) < SEVERITY_RANK.get(old.get("severity"), 0):
                        errors.append(f"audit finding {finding_id} severity was downgraded")
                    if old.get("status") == "CLOSED":
                        errors.append(f"audit finding {finding_id} was already closed at audit checkpoint")
            except (RuntimeError, json.JSONDecodeError) as exc:
                errors.append(f"cannot verify audit finding snapshot: {exc}")
    changed = _git("diff", "--name-only", f"{baseline}..{audit}", root=root).splitlines()
    if not any(_attestation_only_path(path) for path in changed):
        errors.append("audit checkpoint does not contain a cycle report or record")
    disallowed = [path for path in changed if path and not _audit_metadata_path(path)]
    if disallowed:
        errors.append("audit checkpoint contains source/test fixes: " + ", ".join(disallowed))
    cycle = int(record.get("cycle", 0) or 0)
    prior_records = []
    for path in changed:
        match = re.match(r"docs/seven-lens-records/cycle-(\d+)", path)
        if match and int(match.group(1)) != cycle:
            prior_records.append(path)
    if prior_records:
        errors.append("audit checkpoint edits prior-cycle records: " + ", ".join(prior_records))
    if "docs/seven-lens-manual-ledger.json" in changed:
        errors.append("audit checkpoint must not rewrite the manual ledger")
    if _text(verified, 7) and not _git_ok("merge-base", "--is-ancestor", audit, verified, root=root):
        errors.append("verified_source_commit does not descend from audit_commit")
    return errors


def validate_record(
    root: Path,
    record: dict[str, Any],
    phase: str,
    check_git: bool = True,
    require_artifacts: bool = True,
    enforce_current_schema: bool = True,
) -> list[str]:
    registry, _ = _resolved_registry(root)
    errors = _validate_parts(root, record, phase)
    errors.extend(_validate_findings(record, phase))
    errors.extend(_validate_evidence(root, record, phase, check_git))
    errors.extend(_validate_closed_finding_evidence(root, record, phase, require_artifacts))
    errors.extend(_validate_finding_continuity(registry, record, phase))
    if record.get("schema_version", 1) >= 2:
        if record.get("integration_base_commit") != record.get("baseline_commit"):
            errors.append("integration_base_commit must equal baseline_commit")
        if not _text(record.get("baseline_registry_fingerprint"), 64):
            errors.append("baseline_registry_fingerprint missing")
    if record.get("schema_version", 1) >= 3 and not _text(record.get("record_path"), 5):
        errors.append("record_path missing")
    if phase == "close" and enforce_current_schema and record.get("schema_version") != CURRENT_RECORD_SCHEMA:
        errors.append(
            f"schema_version must be current ({CURRENT_RECORD_SCHEMA}) before closure"
        )
    if record.get("target_branch") != "dev":
        errors.append("target_branch must be dev")
    if phase in {"verify", "close"} and not _text(record.get("audit_commit"), 7):
        errors.append("audit_commit missing")
    if phase in {"verify", "close"}:
        errors.extend(_validate_audit_checkpoint(root, record, check_git))
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


def validate_reviewed_cycles(root: Path, require_artifacts: bool = False) -> list[str]:
    ledger_path = root / "docs" / "seven-lens-manual-ledger.json"
    if not ledger_path.is_file():
        return ["manual seven-lens ledger is missing"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    reviews: dict[int, list[dict[str, Any]]] = {}
    for row in ledger.get("reviews", []):
        match = re.fullmatch(r"SL-C(\d+)", str(row.get("cycle_id", "")))
        if not match:
            return [f"ledger has invalid cycle_id {row.get('cycle_id')!r}"]
        reviews.setdefault(int(match.group(1)), []).append(row)

    record_files: dict[int, list[Path]] = {}
    for path in sorted((root / "docs" / "seven-lens-records").glob("cycle-*.json")):
        match = re.match(r"cycle-(\d+)", path.name)
        if match:
            record_files.setdefault(int(match.group(1)), []).append(path)

    errors: list[str] = []
    for cycle, rows in sorted(reviews.items()):
        reviewed = [row for row in rows if row.get("review_status") == "SEVEN_LENS_REVIEWED"]
        if not reviewed:
            continue
        paths = record_files.get(cycle, [])
        exemptions = [row.get("protocol_record_exemption") for row in reviewed]
        if not paths:
            if not all(_text(value, 20) for value in exemptions):
                errors.append(f"SL-C{cycle:02d}: reviewed ledger has no protocol record or exemption")
            continue
        if len(paths) != 1:
            errors.append(f"SL-C{cycle:02d}: expected one protocol record, found {len(paths)}")
            continue
        record = json.loads(paths[0].read_text(encoding="utf-8"))
        if record.get("schema_version") != CURRENT_RECORD_SCHEMA:
            errors.append(
                f"SL-C{cycle:02d}: reviewed cycle must use current protocol schema {CURRENT_RECORD_SCHEMA}"
            )
        record_errors = validate_record(
            root, record, "close", check_git=False, require_artifacts=require_artifacts
        )
        errors.extend(f"SL-C{cycle:02d}: {error}" for error in record_errors)
        record_units = {part.get("unit_id") for part in record.get("parts", [])}
        for row in reviewed:
            unit_id = row.get("unit_id")
            if unit_id not in record_units:
                errors.append(f"SL-C{cycle:02d}: ledger unit {unit_id} is absent from record")
            if row.get("verification_status") not in {"PASS", "PASSED"}:
                errors.append(f"SL-C{cycle:02d}/{unit_id}: reviewed ledger is not verified")
            if row.get("verified_source_commit") != record.get("verified_source_commit"):
                errors.append(f"SL-C{cycle:02d}/{unit_id}: ledger/record verified commit mismatch")
            if row.get("findings_open"):
                errors.append(f"SL-C{cycle:02d}/{unit_id}: reviewed ledger still has open findings")
        verified = str(record.get("verified_source_commit", ""))
        if verified and not _git_ok("cat-file", "-e", f"{verified}^{{commit}}", root=root):
            errors.append(f"SL-C{cycle:02d}: verified source commit does not exist")
    for cycle, paths in sorted(record_files.items()):
        if cycle not in reviews:
            errors.append(f"SL-C{cycle:02d}: protocol record has no ledger entry")
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
    check_all = sub.add_parser("check-all")
    check_all.add_argument("--require-artifacts", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "plan":
            record = make_plan(ROOT, args.cycle)
            if args.output:
                output = args.output if args.output.is_absolute() else ROOT / args.output
                record["record_path"] = output.relative_to(ROOT).as_posix()
                rendered = json.dumps(record, indent=2) + "\n"
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(rendered, encoding="utf-8")
                print(f"wrote {output.relative_to(ROOT)} with {len(record['parts'])} bounded parts")
            else:
                rendered = json.dumps(record, indent=2) + "\n"
                print(rendered, end="")
            return 0
        if args.command == "check-all":
            errors = validate_reviewed_cycles(ROOT, require_artifacts=args.require_artifacts)
            if errors:
                print("SEVEN-LENS REVIEWED-CYCLE GATE: BLOCKED", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            print("SEVEN-LENS REVIEWED-CYCLE GATE: PASS")
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
