#!/usr/bin/env python3
"""Plan and validate manual seven-lens audit-cycle records."""
from __future__ import annotations

import argparse
import fnmatch
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
CURRENT_RECORD_SCHEMA = 5
LEGACY_RECORD_SCHEMA = 4
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


def _normalize_cycle_id(value: Any) -> Any:
    text = str(value).strip()
    if re.fullmatch(r"\d+", text):
        return int(text)
    match = re.fullmatch(r"[Rr](\d+)", text)
    if match:
        return f"R{int(match.group(1)):02d}"
    return text


def make_plan(root: Path, cycle_id: Any) -> dict[str, Any]:
    registry, resolved = _resolved_registry(root)
    if _git("status", "--porcelain", root=root):
        raise RuntimeError("plan requires a clean worktree")
    head = _git("rev-parse", "HEAD", root=root)
    integration_base = _git("rev-parse", "origin/dev", root=root)
    if head != integration_base:
        raise RuntimeError(
            "plan must run before cycle work begins: HEAD must equal origin/dev"
        )
    normalized_cycle_id = _normalize_cycle_id(cycle_id)
    cycle = next((row for row in registry.get("cycles", []) if _normalize_cycle_id(row.get("cycle")) == normalized_cycle_id), None)
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
        "cycle": normalized_cycle_id,
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


def _short_commit(commit: str) -> str:
    value = str(commit or "").strip()
    return value[:7] if len(value) >= 7 else value


def _record_finding_resolution(record_finding: dict[str, Any]) -> str:
    return _short_commit(str(record_finding.get("resolution_commit", "")))


def _load_validated_receipt(root: Path, evidence: dict[str, Any]) -> dict[str, Any] | None:
    receipt_path = evidence.get("receipt_path")
    receipt_hash = evidence.get("receipt_sha256")
    if not _text(receipt_path, 5) or not _text(receipt_hash, 64):
        return None
    receipt_file = root / str(receipt_path)
    if not receipt_file.is_file() or _file_sha256(receipt_file) != receipt_hash:
        return None
    try:
        return json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _prepare_record_for_validation(
    root: Path,
    record: dict[str, Any],
    *,
    check_git: bool = True,
) -> tuple[dict[str, Any], list[str]]:
    from tools.seven_lens_protocol_migrations import (
        LEGACY_RECORD_SCHEMA,
        apply_protocol_migrations,
        requires_explicit_resolution_commit,
    )

    schema = int(record.get("schema_version", 1) or 0)
    if schema > CURRENT_RECORD_SCHEMA:
        return record, [f"unsupported schema_version {schema}"]
    if schema < LEGACY_RECORD_SCHEMA:
        return record, []
    migrated, errors = apply_protocol_migrations(root, record, git_fn=_git)
    if requires_explicit_resolution_commit(record, CURRENT_RECORD_SCHEMA):
        for finding in migrated.get("findings", []):
            if finding.get("status") == "CLOSED" and not _text(finding.get("resolution_commit"), 7):
                errors.append(f"{finding.get('id')}: resolution_commit missing")
    return migrated, errors


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


def _audit_infrastructure_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized in {
        "tools/seven_lens_protocol.py",
        "tools/seven_lens_protocol_migrations.py",
        "tools/test_seven_lens_protocol.py",
        "tools/test_seven_lens_protocol_migrations.py",
    }


def _attestation_only_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return (
        _audit_infrastructure_path(normalized)
        or normalized.startswith("docs/seven-lens-reports/")
        or normalized.startswith("docs/seven-lens-records/")
        or normalized == "docs/seven-lens-manual-ledger.json"
        or normalized == "docs/audit-coverage.md"
        or normalized == "docs/audit-master-plan.md"
        or fnmatch.fnmatch(normalized, "dev/seven-lens-browser-trace-*.json")
        or fnmatch.fnmatch(normalized, "dev/seven-lens-evidence-*.json")
    )


def _closure_only_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if _attestation_only_path(normalized):
        return True
    return normalized == "docs/audit-units.json"


def _forbidden_closure_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if _closure_only_path(normalized):
        return False
    if normalized.startswith("docs/seven-lens-traces/"):
        return True
    if normalized.startswith("lsp-dplanner-") or normalized == "index.html":
        return True
    if normalized.startswith("ui/"):
        return True
    if normalized.startswith("dev/"):
        return True
    if normalized.startswith("tools/audit/"):
        return True
    return False


def _registry_regression_id(registry: dict[str, Any], regression_id: str) -> str | None:
    for reg_id, row in registry.get("evidence_catalog", {}).items():
        if row.get("case_id") == regression_id:
            return reg_id
    return None


def _finding_closure_issue(cycle: int) -> str:
    return f"Seven-lens Cycle {cycle:02d} controls CSS audit"


def _expected_registry_evidence_cases(
    record_finding: dict[str, Any], registry: dict[str, Any]
) -> list[str]:
    return [
        reg_id
        for regression_id in record_finding.get("regression_ids", [])
        if (reg_id := _registry_regression_id(registry, regression_id))
    ]


def _validate_units_fingerprint_realignments(
    root: Path, before_units: list[dict[str, Any]], after_units: list[dict[str, Any]]
) -> list[str]:
    errors: list[str] = []
    before_map = {row.get("id"): row for row in before_units}
    after_map = {row.get("id"): row for row in after_units}
    if set(before_map) - set(after_map):
        errors.append("registry closure removed unit catalog entries")
        return errors
    if list(before_map) != [uid for uid in after_map if uid in before_map]:
        errors.append("registry closure reordered existing unit catalog entries")
        return errors
    for unit_id, before in before_map.items():
        after = after_map[unit_id]
        if before == after:
            continue
        before_copy = dict(before)
        after_copy = dict(after)
        before_fp = before_copy.pop("fingerprint", None)
        after_fp = after_copy.pop("fingerprint", None)
        if before_copy != after_copy:
            errors.append(f"registry closure changed unit {unit_id} outside fingerprint realignment")
            continue
        path = root / str(after.get("path", ""))
        expected = _file_sha256(path) if path.is_file() else ""
        if after_fp != expected:
            errors.append(f"registry closure unit {unit_id} fingerprint does not match source file")
    return errors


def _validate_registry_closure_mutations(
    root: Path, record: dict[str, Any], verified_commit: str
) -> list[str]:
    errors: list[str] = []
    cycle = int(record.get("cycle", 0) or 0)
    if cycle < 1:
        errors.append("registry closure validation requires cycle number")
        return errors
    try:
        before = json.loads(_git("show", f"{verified_commit}:docs/audit-units.json", root=root))
    except (RuntimeError, json.JSONDecodeError) as exc:
        errors.append(f"cannot load verified registry: {exc}")
        return errors
    after_path = root / "docs/audit-units.json"
    if not after_path.is_file():
        errors.append("docs/audit-units.json missing at closure HEAD")
        return errors
    after = json.loads(after_path.read_text(encoding="utf-8"))
    record_findings = {
        row.get("id"): row
        for row in record.get("findings", [])
        if _text(row.get("id"), 5)
    }
    expected_closed = {
        finding_id: row
        for finding_id, row in record_findings.items()
        if row.get("status") == "CLOSED"
    }
    immutable_top_level = [
        key for key in before if key not in {"findings", "units"}
    ]
    for key in immutable_top_level:
        if key not in after:
            errors.append(f"registry closure removed top-level section {key}")
        elif before[key] != after[key]:
            errors.append(f"registry closure changed forbidden section {key}")
    for key in after:
        if key in {"findings", "units"}:
            continue
        if key not in before:
            errors.append(f"registry closure added top-level section {key}")
    errors.extend(
        _validate_units_fingerprint_realignments(
            root, before.get("units", []), after.get("units", [])
        )
    )
    before_findings = {row.get("id"): row for row in before.get("findings", [])}
    after_findings = {row.get("id"): row for row in after.get("findings", [])}
    for finding_id, old in before_findings.items():
        if finding_id not in after_findings:
            errors.append(f"registry closure deleted finding {finding_id}")
    for finding_id, new in after_findings.items():
        old = before_findings.get(finding_id)
        if finding_id not in expected_closed:
            if old != new:
                from tools.seven_lens_protocol_migrations import migration_allows_registry_finding_change

                if not migration_allows_registry_finding_change(
                    root, finding_id, old, new, git_fn=_git
                ):
                    errors.append(f"registry closure modified unrelated finding {finding_id}")
            continue
        record_finding = expected_closed[finding_id]
        expected_rc = _record_finding_resolution(record_finding)
        if not expected_rc:
            errors.append(f"registry closure finding {finding_id} lacks record resolution_commit")
            continue
        expected_evidence = _expected_registry_evidence_cases(record_finding, after)
        unit_id = str(record_finding.get("unit_id", ""))
        if old is not None and old == new:
            if new.get("status") != "CLOSED":
                errors.append(f"registry closure finding {finding_id} must remain CLOSED")
            elif _short_commit(str(new.get("resolution_commit", ""))) != expected_rc:
                errors.append(f"registry closure finding {finding_id} resolution_commit mismatch")
            continue
        if old is not None and old.get("status") == "CLOSED" and new.get("status") == "CLOSED":
            diff_keys = {
                key for key in set(old) | set(new) if old.get(key) != new.get(key)
            }
            if diff_keys <= {"resolution_commit"}:
                if _short_commit(str(new.get("resolution_commit", ""))) != expected_rc:
                    errors.append(f"registry closure finding {finding_id} resolution_commit mismatch")
                continue
        if old is None:
            if new.get("status") != "CLOSED":
                errors.append(f"registry closure finding {finding_id} must be CLOSED")
            if _short_commit(str(new.get("resolution_commit", ""))) != expected_rc:
                errors.append(f"registry closure finding {finding_id} resolution_commit mismatch")
            if new.get("unit_id") != unit_id:
                errors.append(f"registry closure finding {finding_id} unit_id mismatch")
            if new.get("severity") != record_finding.get("severity"):
                errors.append(f"registry closure finding {finding_id} severity mismatch")
            if new.get("issue") != _finding_closure_issue(cycle):
                errors.append(f"registry closure finding {finding_id} issue mismatch")
            if new.get("affected_units") != ([unit_id] if unit_id else []):
                errors.append(f"registry closure finding {finding_id} affected_units mismatch")
            if new.get("evidence_cases") != expected_evidence:
                errors.append(f"registry closure finding {finding_id} evidence_cases mismatch")
            if not _text(new.get("summary"), 5):
                errors.append(f"registry closure finding {finding_id} summary missing")
            continue
        allowed_old_status = {"OPEN", "BLOCKED"}
        if old.get("status") not in allowed_old_status:
            errors.append(f"registry closure finding {finding_id} did not start OPEN/BLOCKED")
        mutable = {"status", "resolution_commit"}
        for key, value in old.items():
            if key in mutable:
                continue
            if new.get(key) != value:
                errors.append(f"registry closure finding {finding_id} changed immutable field {key}")
        if new.get("status") != "CLOSED":
            errors.append(f"registry closure finding {finding_id} must end CLOSED")
        if _short_commit(str(new.get("resolution_commit", ""))) != expected_rc:
            errors.append(f"registry closure finding {finding_id} resolution_commit mismatch")
        if new.get("evidence_cases") != expected_evidence:
            errors.append(f"registry closure finding {finding_id} evidence_cases mismatch")
    for finding_id in expected_closed:
        if finding_id not in after_findings:
            errors.append(f"registry closure missing expected finding {finding_id}")
    return errors


def _validate_generated_coverage_doc(root: Path) -> list[str]:
    try:
        from tools import audit_coverage

        registry = audit_coverage.load_registry(root / "docs/audit-units.json")
        _, resolved = audit_coverage.validate_registry(registry, root)
        expected = audit_coverage.render_coverage(registry, resolved)
    except Exception as exc:
        return [f"cannot validate generated coverage doc: {exc}"]
    actual = (root / "docs/audit-coverage.md").read_text(encoding="utf-8")
    if actual != expected:
        return ["docs/audit-coverage.md is not generated from the registry"]
    return []


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


def _validate_unreferenced_receipts(root: Path, record: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    referenced = {
        str(row.get("receipt_path", "")).replace("\\", "/")
        for row in record.get("evidence_runs", [])
        if _text(row.get("receipt_path"), 5)
    }
    cycle = int(record.get("cycle", 0) or 0)
    if cycle < 1:
        return errors
    for path in sorted(root.glob(f"dev/seven-lens-evidence-c{cycle:02d}-*.json")):
        rel = path.relative_to(root).as_posix()
        if rel not in referenced:
            errors.append(f"unreferenced attestation receipt: {rel}")
    return errors


def _validate_closure_only_diff(
    root: Path,
    record: dict[str, Any],
    verified_commit: str,
    closure_commit: str,
    check_git: bool,
) -> list[str]:
    if not check_git or not _text(verified_commit, 7) or not _text(closure_commit, 7):
        return []
    if verified_commit == closure_commit:
        return []
    errors: list[str] = []
    if not _git_ok("merge-base", "--is-ancestor", verified_commit, closure_commit, root=root):
        errors.append("closure_evidence_commit does not descend from verified_source_commit")
        return errors
    try:
        changed = [
            path for path in _git(
                "diff", "--name-only", f"{verified_commit}..{closure_commit}", root=root
            ).splitlines()
            if path.strip()
        ]
    except RuntimeError as exc:
        errors.append(f"cannot inspect closure diff: {exc}")
        return errors
    forbidden = [path for path in changed if _forbidden_closure_path(path)]
    if forbidden:
        errors.append(
            "closure-only diff contains forbidden paths: " + ", ".join(sorted(forbidden))
        )
    if "docs/audit-units.json" in changed:
        errors.extend(_validate_registry_closure_mutations(root, record, verified_commit))
    return errors


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
        receipt = _load_validated_receipt(root, row) if record.get("schema_version", 1) >= LEGACY_RECORD_SCHEMA else None
        effective_exit = row.get("exit_code")
        if receipt is not None and isinstance(receipt.get("exit_code"), int):
            if effective_exit != receipt.get("exit_code"):
                errors.append(f"evidence {evidence_id}: record exit_code does not match receipt")
            effective_exit = receipt.get("exit_code")
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
        if row.get("kind") == "baseline_failure" and effective_exit == 0:
            errors.append(f"evidence {evidence_id}: baseline failure must fail before the fix")
        if row.get("kind") in {"post_fix", "state_restoration", "gate"} and effective_exit != 0:
            errors.append(f"evidence {evidence_id}: passing evidence has nonzero exit_code")
        verified = str(record.get("verified_source_commit", ""))
        closure = str(record.get("closure_evidence_commit", "") or verified)
        if (
            phase == "close"
            and record.get("schema_version", 1) >= 3
            and _text(verified, 7)
        ):
            kind = row.get("kind")
            commit = str(row.get("commit", ""))
            if kind in {"post_fix", "state_restoration"} and commit != verified:
                errors.append(f"evidence {evidence_id}: must run at verified_source_commit")
            elif kind == "gate" and evidence_id in {"static", "ci"} and commit != closure:
                errors.append(f"evidence {evidence_id}: must run at closure_evidence_commit")
        if record.get("schema_version", 1) >= LEGACY_RECORD_SCHEMA and phase in {"verify", "close"}:
            errors.extend(_validate_evidence_receipt(root, row))
    gate_ids = {"static", "ci"}
    gate_rows = [
        row for row in record.get("evidence_runs", [])
        if row.get("id") in gate_ids
    ]
    verified = str(record.get("verified_source_commit", ""))
    if (
        phase == "close"
        and record.get("schema_version", 1) >= 3
        and _text(verified, 7)
        and any(str(row.get("commit", "")) != verified for row in gate_rows)
        and not _text(str(record.get("closure_evidence_commit", "")), 7)
    ):
        errors.append("closure_evidence_commit required when static/ci run after verified_source_commit")
    if record.get("schema_version", 1) >= LEGACY_RECORD_SCHEMA and phase in {"verify", "close"}:
        errors.extend(_validate_unreferenced_receipts(root, record))
    if phase in {"verify", "close"} and record.get("verification_status") == "PASSED":
        passed = set()
        for row in record.get("evidence_runs", []):
            receipt = _load_validated_receipt(root, row)
            exit_code = receipt.get("exit_code") if receipt is not None else row.get("exit_code")
            clean = receipt.get("worktree_clean_after") if receipt is not None else row.get("worktree_clean")
            if exit_code == 0 and clean is True:
                passed.add(row.get("id"))
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


def _finding_proven_closed_in_reviewed_record(root: Path, finding_id: str) -> bool:
    match = re.match(r"SL-C(\d+)-", str(finding_id))
    if not match:
        return False
    cycle = int(match.group(1))
    for path in (root / "docs" / "seven-lens-records").glob(f"cycle-{cycle:02d}-*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("verification_status") != "PASSED":
            continue
        for row in record.get("findings", []):
            if row.get("id") == finding_id and row.get("status") == "CLOSED":
                from tools.seven_lens_protocol_migrations import finding_has_proven_resolution

                return finding_has_proven_resolution(record, row)
    return False


def _validate_finding_continuity(
    root: Path, registry: dict[str, Any], record: dict[str, Any], phase: str
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
                if not _finding_proven_closed_in_reviewed_record(root, finding_id):
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
    migrated, migration_errors = _prepare_record_for_validation(root, record, check_git=check_git)
    errors = list(migration_errors)
    registry, _ = _resolved_registry(root)
    errors.extend(_validate_parts(root, migrated, phase))
    errors.extend(_validate_findings(migrated, phase))
    errors.extend(_validate_evidence(root, migrated, phase, check_git))
    errors.extend(_validate_closed_finding_evidence(root, migrated, phase, require_artifacts))
    errors.extend(_validate_finding_continuity(root, registry, migrated, phase))
    if migrated.get("schema_version", 1) >= 2:
        if migrated.get("integration_base_commit") != migrated.get("baseline_commit"):
            errors.append("integration_base_commit must equal baseline_commit")
        if not _text(migrated.get("baseline_registry_fingerprint"), 64):
            errors.append("baseline_registry_fingerprint missing")
    if migrated.get("schema_version", 1) >= 3 and not _text(migrated.get("record_path"), 5):
        errors.append("record_path missing")
    if phase == "close" and enforce_current_schema and migrated.get("schema_version") != CURRENT_RECORD_SCHEMA:
        if migrated.get("schema_version") != LEGACY_RECORD_SCHEMA:
            errors.append(
                f"schema_version must be current ({CURRENT_RECORD_SCHEMA}) before closure"
            )
    if migrated.get("target_branch") != "dev":
        errors.append("target_branch must be dev")
    if phase in {"verify", "close"} and not _text(migrated.get("audit_commit"), 7):
        errors.append("audit_commit missing")
    if phase in {"verify", "close"}:
        errors.extend(_validate_audit_checkpoint(root, migrated, check_git))
    if phase in {"verify", "close"} and migrated.get("verification_status") not in {"PASSED", "BLOCKED"}:
        errors.append("verification_status must be PASSED or BLOCKED")
    if phase in {"verify", "close"} and migrated.get("verification_status") == "PASSED" and not _text(migrated.get("verified_source_commit"), 7):
        errors.append("verified_source_commit missing")
    if phase == "close":
        if migrated.get("verification_status") != "PASSED":
            errors.append("verification_status must be PASSED")
        if not _text(migrated.get("verified_source_commit"), 7):
            errors.append("verified_source_commit missing")
        if check_git and _git("status", "--porcelain", root=root):
            errors.append("tracked or untracked worktree is not clean")
        if check_git and _text(migrated.get("verified_source_commit"), 7):
            verified = str(migrated["verified_source_commit"])
            closure = str(migrated.get("closure_evidence_commit", "") or verified)
            errors.extend(
                _validate_closure_only_diff(root, migrated, verified, closure, check_git)
            )
            protected = {part["path"] for part in migrated.get("parts", [])} | set(migrated.get("changed_paths", []))
            protected.discard("docs/audit-units.json")
            if _text(migrated.get("audit_commit"), 7):
                fix_diff = _git(
                    "diff", "--name-only", f"{migrated['audit_commit']}..{verified}",
                    root=root,
                )
                protected.update(
                    path for path in fix_diff.splitlines()
                    if path.strip()
                    and path != "docs/audit-units.json"
                    and not _attestation_only_path(path)
                )
            paths = sorted(
                path for path in protected if path.strip() and not _attestation_only_path(path)
            )
            if paths:
                changed = _git(
                    "diff", "--name-only", f"{verified}..HEAD", "--", *paths, root=root
                )
                changed_list = [path for path in changed.splitlines() if path.strip()]
                if changed_list:
                    errors.append(
                        "reviewed source/test changed after verification: " + ", ".join(changed_list)
                    )
            if _text(closure, 7):
                try:
                    head = _git("rev-parse", "HEAD", root=root)
                    if closure != head:
                        post_closure = [
                            path for path in _git(
                                "diff", "--name-only", f"{closure}..HEAD", root=root
                            ).splitlines()
                            if path.strip() and not _attestation_only_path(path)
                        ]
                        if post_closure:
                            errors.append(
                                "post-closure diff contains non-attestation paths: "
                                + ", ".join(post_closure)
                            )
                except RuntimeError:
                    pass
            coverage_path = root / "docs/audit-coverage.md"
            if coverage_path.is_file() and check_git:
                try:
                    if _git(
                        "diff", "--name-only", f"{verified}..HEAD",
                        "--", "docs/audit-coverage.md", root=root,
                    ).strip():
                        errors.extend(_validate_generated_coverage_doc(root))
                except RuntimeError:
                    pass
    if migrated.get("cycle") == 8:
        mirror = root / "docs/seven-lens-records/cycle-08-shell-results.json"
        report = root / "docs/seven-lens-reports/cycle-08-record.json"
        if mirror.is_file() and report.is_file() and mirror.read_bytes() != report.read_bytes():
            errors.append(
                "cycle 8 record mirror diverged: "
                "docs/seven-lens-records/cycle-08-shell-results.json "
                "!= docs/seven-lens-reports/cycle-08-record.json"
            )
    return errors


def validate_reviewed_cycles(root: Path, require_artifacts: bool = False) -> list[str]:
    if _v5_active_epoch(root):
        return []
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
        schema = record.get("schema_version")
        if schema not in {LEGACY_RECORD_SCHEMA, CURRENT_RECORD_SCHEMA}:
            errors.append(
                f"SL-C{cycle:02d}: reviewed cycle must use schema {LEGACY_RECORD_SCHEMA} or {CURRENT_RECORD_SCHEMA}"
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


def _v5_active_epoch(root: Path) -> bool:
    registry_path = root / "docs" / "audit-units.json"
    if not registry_path.is_file():
        return False
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return registry.get("audit_epoch") == "v5-risk-first-active"


def _reviewed_cycle_ids(root: Path) -> tuple[set[int], list[str]]:
    ledger_path = root / "docs" / "seven-lens-manual-ledger.json"
    if not ledger_path.is_file():
        return set(), ["manual seven-lens ledger is missing"]
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    cycles: set[int] = set()
    errors: list[str] = []
    for row in ledger.get("reviews", []):
        if row.get("review_status") != "SEVEN_LENS_REVIEWED":
            continue
        match = re.fullmatch(r"SL-C(\d+)", str(row.get("cycle_id", "")))
        if not match:
            errors.append(f"ledger has invalid cycle_id {row.get('cycle_id')!r}")
            continue
        cycles.add(int(match.group(1)))
    return cycles, errors


def _cycle_record_candidates(root: Path, cycle: int) -> list[Path]:
    candidates = [
        *sorted((root / "docs" / "seven-lens-records").glob(f"cycle-{cycle:02d}-*.json")),
        *sorted((root / "docs" / "seven-lens-reports").glob(f"cycle-{cycle:02d}-*record*.json")),
    ]
    unique: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def _sync_record_part_boundaries(
    root: Path, record: dict[str, Any], resolved: dict[str, dict[str, Any]]
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    changed = False
    grouped: dict[str, list[dict[str, Any]]] = {}
    for part in record.get("parts", []):
        unit_id = str(part.get("unit_id", ""))
        if unit_id:
            grouped.setdefault(unit_id, []).append(part)
    for unit_id, parts in grouped.items():
        unit = resolved.get(unit_id)
        if not unit:
            errors.append(f"{unit_id}: unknown unit")
            continue
        current_ranges = _split_boundary(unit["start_line"], unit["end_line"])
        ordered = sorted(parts, key=lambda row: (row.get("start_line", 0), row.get("id", "")))
        if len(current_ranges) != len(ordered):
            errors.append(
                f"{unit_id}: current split has {len(current_ranges)} parts; "
                f"record has {len(ordered)} parts; re-review required"
            )
            continue
        for index, (part, (start, end)) in enumerate(zip(ordered, current_ranges), 1):
            path = root / unit["path"]
            expected = {
                "id": f"{unit_id}-P{index:02d}",
                "unit_id": unit_id,
                "path": unit["path"],
                "start_line": start,
                "end_line": end,
                "line_count": end - start + 1,
                "content_fingerprint": _part_hash(path, start, end),
            }
            for key, value in expected.items():
                if part.get(key) != value:
                    part[key] = value
                    changed = True
    return changed, errors


def sync_reviewed_boundaries(root: Path, write: bool = False) -> tuple[list[str], list[str]]:
    if _v5_active_epoch(root):
        return [], []
    cycles, errors = _reviewed_cycle_ids(root)
    if errors:
        return [], errors
    _, resolved = _resolved_registry(root)
    changed_paths: list[str] = []
    for cycle in sorted(cycles):
        for path in _cycle_record_candidates(root, cycle):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                errors.append(f"{path.relative_to(root)}: invalid JSON: {exc}")
                continue
            changed, record_errors = _sync_record_part_boundaries(root, record, resolved)
            errors.extend(f"{path.relative_to(root)}: {error}" for error in record_errors)
            if changed:
                changed_paths.append(path.relative_to(root).as_posix())
                if write:
                    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed_paths, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--cycle", required=True)
    plan.add_argument("--output", type=Path)
    check = sub.add_parser("check")
    check.add_argument("--phase", choices=("audit", "verify", "close"), required=True)
    check.add_argument("--record", type=Path, required=True)
    check_all = sub.add_parser("check-all")
    check_all.add_argument("--require-artifacts", action="store_true")
    sync_reviewed = sub.add_parser(
        "sync-reviewed-boundaries",
        help="Refresh reviewed cycle record part boundaries/fingerprints after line-only drift",
    )
    sync_reviewed.add_argument("--write", action="store_true", help="Persist boundary/fingerprint updates")
    migrate = sub.add_parser("migrate", help="Apply frozen historical migrations to a cycle record")
    migrate.add_argument("--record", type=Path, required=True)
    migrate.add_argument("--write", action="store_true", help="Persist migrated record JSON")
    migrate.add_argument(
        "--reconcile-registry",
        action="store_true",
        help="Update docs/audit-units.json only when record evidence proves closure",
    )
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
                print(
                    "Hint: if these are line-boundary or fingerprint drift after source edits, "
                    "run `python tools/seven_lens_protocol.py sync-reviewed-boundaries --write`.",
                    file=sys.stderr,
                )
                return 1
            print("SEVEN-LENS REVIEWED-CYCLE GATE: PASS")
            return 0
        if args.command == "sync-reviewed-boundaries":
            changed, errors = sync_reviewed_boundaries(ROOT, write=args.write)
            if errors:
                print("SEVEN-LENS BOUNDARY SYNC: BLOCKED", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            if changed:
                action = "updated" if args.write else "would update"
                print(f"SEVEN-LENS BOUNDARY SYNC: {action} {len(changed)} record(s)")
                for path in changed:
                    print(f"- {path}")
            else:
                print("SEVEN-LENS BOUNDARY SYNC: no changes")
            return 0
        if args.command == "migrate":
            from tools.seven_lens_protocol_migrations import (
                apply_protocol_migrations,
                apply_registry_reconcile_v1,
            )

            record_path = args.record if args.record.is_absolute() else ROOT / args.record
            record = json.loads(record_path.read_text(encoding="utf-8"))
            migrated, errors = apply_protocol_migrations(ROOT, record, git_fn=_git)
            if args.reconcile_registry:
                registry_path = ROOT / "docs/audit-units.json"
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
                registry, reg_errors = apply_registry_reconcile_v1(
                    ROOT, migrated, registry, git_fn=_git
                )
                errors.extend(reg_errors)
                if args.write and not reg_errors:
                    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
                    print(f"reconciled registry from {record_path.relative_to(ROOT)}")
            if errors:
                print("SEVEN-LENS MIGRATION: BLOCKED", file=sys.stderr)
                for error in errors:
                    print(f"- {error}", file=sys.stderr)
                return 1
            if args.write:
                record_path.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")
                print(f"migrated {record_path.relative_to(ROOT)}")
            else:
                print(json.dumps(migrated, indent=2))
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
