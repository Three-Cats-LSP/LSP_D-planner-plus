#!/usr/bin/env python3
"""Frozen historical migrations for seven-lens protocol records.

Migration algorithms are versioned and tested with golden fixtures so future
protocol upgrades cannot silently invalidate completed cycle evidence.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

MIGRATION_RESOLUTION_COMMIT_V1 = "resolution-commit-v1"
MIGRATION_RECEIPT_EXIT_V1 = "receipt-exit-v1"
MIGRATION_REGISTRY_RECONCILE_V1 = "registry-reconcile-v1"

MIGRATION_ORDER = (
    MIGRATION_RESOLUTION_COMMIT_V1,
    MIGRATION_RECEIPT_EXIT_V1,
    MIGRATION_REGISTRY_RECONCILE_V1,
)

LEGACY_RECORD_SCHEMA = 4


def migration_fingerprint() -> str:
    """Stable fingerprint of all migration algorithms in this module."""
    import hashlib

    source = Path(__file__).read_text(encoding="utf-8")
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _short_commit(commit: str) -> str:
    value = str(commit or "").strip()
    return value[:7] if len(value) >= 7 else value


def _text(value: Any, minimum: int = 1) -> bool:
    return isinstance(value, str) and len(value.strip()) >= minimum


def _expand_commit(root: Path, commit: str, git_fn) -> str:
    value = str(commit or "").strip()
    if not _text(value, 7):
        return value
    if len(value) >= 40:
        return value
    try:
        return git_fn("rev-parse", value, root=root)
    except (RuntimeError, OSError):
        return value


def _load_registry_at(root: Path, commit: str, git_fn) -> dict[str, Any]:
    payload = git_fn("show", f"{commit}:docs/audit-units.json", root=root)
    return json.loads(payload)


def _registry_findings_map(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row.get("id"): row for row in registry.get("findings", []) if row.get("id")}


def _file_sha256(path: Path) -> str:
    import hashlib

    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return hashlib.sha256(data).hexdigest()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load_receipt(root: Path, evidence: dict[str, Any]) -> dict[str, Any] | None:
    receipt_path = evidence.get("receipt_path")
    receipt_hash = evidence.get("receipt_sha256")
    if not _text(receipt_path, 5) or not _text(receipt_hash, 64):
        return None
    receipt_file = root / str(receipt_path)
    if not receipt_file.is_file():
        return None
    if _file_sha256(receipt_file) != receipt_hash:
        return None
    try:
        return json.loads(receipt_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _evidence_map(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row.get("id"): row for row in record.get("evidence_runs", []) if row.get("id")}


def finding_has_proven_resolution(record: dict[str, Any], finding: dict[str, Any]) -> bool:
    if finding.get("status") != "CLOSED":
        return False
    evidence_ids = set(_evidence_map(record))
    linked = finding.get("evidence_ids", [])
    if not linked or any(item not in evidence_ids for item in linked):
        return False
    severity = finding.get("severity")
    if severity in {"CRITICAL", "HIGH", "MEDIUM"}:
        regressions = finding.get("regression_ids", [])
        if not regressions:
            return False
        for label in ("pre_fix_evidence_id", "post_fix_evidence_id", "state_restoration_evidence_id"):
            evidence_id = finding.get(label)
            if evidence_id not in evidence_ids:
                return False
        evidence = _evidence_map(record)
        post = evidence.get(finding.get("post_fix_evidence_id"), {})
        if post.get("kind") != "post_fix" or post.get("exit_code") != 0:
            return False
    return True


def derive_resolution_commit_v1(
    root: Path,
    record: dict[str, Any],
    finding: dict[str, Any],
    *,
    git_fn,
) -> str:
    """Deterministic resolution_commit for legacy closed findings."""
    if not finding_has_proven_resolution(record, finding):
        return ""
    explicit = str(finding.get("resolution_commit", "")).strip()
    if _text(explicit, 7):
        return _expand_commit(root, explicit, git_fn)
    verified = str(record.get("verified_source_commit", "")).strip()
    finding_id = str(finding.get("id", ""))
    if _text(verified, 7):
        try:
            registry = _load_registry_at(root, verified, git_fn)
            reg_row = _registry_findings_map(registry).get(finding_id, {})
            reg_rc = str(reg_row.get("resolution_commit", "")).strip()
            if reg_row.get("status") == "CLOSED" and _text(reg_rc, 7):
                return _expand_commit(root, reg_rc, git_fn)
        except (RuntimeError, json.JSONDecodeError, OSError):
            pass
    evidence = _evidence_map(record)
    post_id = finding.get("post_fix_evidence_id")
    post = evidence.get(post_id, {}) if post_id else {}
    post_commit = str(post.get("commit", "")).strip()
    if _text(post_commit, 7):
        return _expand_commit(root, post_commit, git_fn)
    if _text(verified, 7):
        return verified
    return ""


def apply_resolution_commit_v1(
    root: Path,
    record: dict[str, Any],
    *,
    git_fn,
) -> tuple[dict[str, Any], list[str]]:
    migrated = copy.deepcopy(record)
    errors: list[str] = []
    for finding in migrated.get("findings", []):
        if finding.get("status") != "CLOSED":
            continue
        if _text(str(finding.get("resolution_commit", "")), 7):
            finding["resolution_commit"] = _expand_commit(
                root, str(finding["resolution_commit"]), git_fn
            )
            continue
        derived = derive_resolution_commit_v1(root, migrated, finding, git_fn=git_fn)
        if not derived:
            errors.append(f"{finding.get('id')}: cannot derive resolution_commit from history")
            continue
        finding["resolution_commit"] = derived
    return migrated, errors


def apply_receipt_exit_v1(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    migrated = copy.deepcopy(record)
    for row in migrated.get("evidence_runs", []):
        receipt = _load_receipt(root, row)
        if receipt is None or not isinstance(receipt.get("exit_code"), int):
            continue
        row["exit_code"] = receipt["exit_code"]
        if isinstance(receipt.get("worktree_clean_after"), bool):
            row["worktree_clean"] = receipt["worktree_clean_after"]
    return migrated


def _registry_regression_id(registry: dict[str, Any], regression_id: str) -> str | None:
    for reg_id, row in registry.get("evidence_catalog", {}).items():
        if row.get("case_id") == regression_id:
            return reg_id
    return None


def _expected_registry_evidence_cases(
    record_finding: dict[str, Any], registry: dict[str, Any]
) -> list[str]:
    return [
        reg_id
        for regression_id in record_finding.get("regression_ids", [])
        if (reg_id := _registry_regression_id(registry, regression_id))
    ]


def _finding_closure_issue(cycle: int) -> str:
    return f"Seven-lens Cycle {cycle:02d} audit"


def _planned_registry_finding_row(
    root: Path,
    record: dict[str, Any],
    finding: dict[str, Any],
    registry: dict[str, Any],
    existing: dict[str, Any] | None,
    *,
    git_fn,
) -> dict[str, Any] | None:
    finding_id = finding.get("id")
    if not finding_id or finding.get("status") != "CLOSED":
        return None
    if not finding_has_proven_resolution(record, finding):
        return None
    resolution = derive_resolution_commit_v1(root, record, finding, git_fn=git_fn)
    if not resolution:
        return None
    cycle = int(record.get("cycle", 0) or 0)
    expected_evidence = _expected_registry_evidence_cases(finding, registry)
    if not expected_evidence and finding.get("severity") == "LOW":
        linked = set(finding.get("evidence_ids", []))
        if linked.intersection({"static", "ci"}):
            expected_evidence = ["COV-01"]
    if not expected_evidence:
        return None
    unit_id = str(finding.get("unit_id", ""))
    summary = finding.get("summary") or finding.get("recommendation") or finding.get("fix_summary") or ""
    if existing is None:
        return {
            "id": finding_id,
            "unit_id": unit_id,
            "severity": finding.get("severity"),
            "status": "CLOSED",
            "issue": _finding_closure_issue(cycle),
            "summary": summary if _text(summary, 5) else finding_id,
            "affected_units": [unit_id] if unit_id else [],
            "resolution_commit": _short_commit(resolution),
            "evidence_cases": expected_evidence,
        }
    patched = dict(existing)
    patched["status"] = "CLOSED"
    patched["resolution_commit"] = _short_commit(resolution)
    patched.setdefault("issue", _finding_closure_issue(cycle))
    if not _text(str(patched.get("summary", "")), 5):
        patched["summary"] = summary if _text(summary, 5) else finding_id
    if not patched.get("affected_units"):
        patched["affected_units"] = [unit_id] if unit_id else []
    if not patched.get("evidence_cases"):
        patched["evidence_cases"] = expected_evidence
    patched.setdefault("unit_id", unit_id)
    patched.setdefault("severity", finding.get("severity"))
    return patched


def _registry_finding_migration_equivalent(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    keys = ("id", "unit_id", "severity", "status", "affected_units", "evidence_cases")
    for key in keys:
        if expected.get(key) != actual.get(key):
            return False
    return _short_commit(str(expected.get("resolution_commit", ""))) == _short_commit(
        str(actual.get("resolution_commit", ""))
    )


def registry_reconcile_plan_v1(
    root: Path,
    record: dict[str, Any],
    registry: dict[str, Any],
    *,
    git_fn,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return registry finding rows to add/update; never force-close without proof."""
    updates: list[dict[str, Any]] = []
    errors: list[str] = []
    current = _registry_findings_map(registry)
    for finding in record.get("findings", []):
        finding_id = finding.get("id")
        if not finding_id or finding.get("status") != "CLOSED":
            continue
        planned = _planned_registry_finding_row(
            root, record, finding, registry, current.get(finding_id), git_fn=git_fn
        )
        if planned is None:
            if finding.get("status") == "CLOSED" and finding_has_proven_resolution(record, finding):
                if not derive_resolution_commit_v1(root, record, finding, git_fn=git_fn):
                    errors.append(f"{finding_id}: registry reconcile lacks resolution_commit")
            continue
        existing = current.get(finding_id)
        if existing is not None and existing == planned:
            continue
        if existing is not None and existing.get("status") == "CLOSED":
            if _short_commit(str(existing.get("resolution_commit", ""))) == planned.get(
                "resolution_commit"
            ) and existing.get("evidence_cases") == planned.get("evidence_cases"):
                continue
        updates.append(planned)
    return updates, errors


def apply_registry_reconcile_v1(
    root: Path,
    record: dict[str, Any],
    registry: dict[str, Any],
    *,
    git_fn,
) -> tuple[dict[str, Any], list[str]]:
    updates, errors = registry_reconcile_plan_v1(root, record, registry, git_fn=git_fn)
    if not updates:
        return registry, errors
    merged = copy.deepcopy(registry)
    by_id = {row.get("id"): row for row in merged.get("findings", [])}
    for row in updates:
        finding_id = row.get("id")
        if finding_id in by_id:
            index = next(
                idx for idx, item in enumerate(merged["findings"]) if item.get("id") == finding_id
            )
            merged["findings"][index] = row
        else:
            merged["findings"].append(row)
    return merged, errors


def apply_protocol_migrations(
    root: Path,
    record: dict[str, Any],
    *,
    git_fn,
    persist: bool = False,
) -> tuple[dict[str, Any], list[str]]:
    migrated = copy.deepcopy(record)
    errors: list[str] = []
    applied = list(migrated.get("protocol_migrations", []))

    if MIGRATION_RESOLUTION_COMMIT_V1 not in applied:
        migrated, mig_errors = apply_resolution_commit_v1(root, migrated, git_fn=git_fn)
        errors.extend(mig_errors)
        if not mig_errors:
            applied.append(MIGRATION_RESOLUTION_COMMIT_V1)

    if MIGRATION_RECEIPT_EXIT_V1 not in applied:
        migrated = apply_receipt_exit_v1(root, migrated)
        applied.append(MIGRATION_RECEIPT_EXIT_V1)

    migrated["protocol_migrations"] = applied
    if persist:
        return migrated, errors
    return migrated, errors


def migration_allows_registry_finding_change(
    root: Path,
    finding_id: str,
    before: dict[str, Any] | None,
    after: dict[str, Any],
    *,
    git_fn,
) -> bool:
    match = __import__("re").match(r"SL-C(\d+)-", str(finding_id))
    if not match:
        return False
    cycle = int(match.group(1))
    record_path = root / "docs" / "seven-lens-records"
    candidates = sorted(record_path.glob(f"cycle-{cycle:02d}-*.json"))
    if not candidates:
        return False
    record = json.loads(candidates[0].read_text(encoding="utf-8"))
    if MIGRATION_RESOLUTION_COMMIT_V1 not in record.get("protocol_migrations", []):
        migrated, errors = apply_protocol_migrations(root, record, git_fn=git_fn)
        if errors:
            return False
        record = migrated
    finding = next((row for row in record.get("findings", []) if row.get("id") == finding_id), None)
    if finding is None:
        return before == after
    registry = json.loads((root / "docs/audit-units.json").read_text(encoding="utf-8"))
    updates, _ = registry_reconcile_plan_v1(root, record, registry, git_fn=git_fn)
    allowed = {row.get("id"): row for row in updates}
    if finding_id in allowed and _registry_finding_migration_equivalent(allowed[finding_id], after):
        return True
    expected = _planned_registry_finding_row(
        root, record, finding, registry, before, git_fn=git_fn
    )
    if expected and _registry_finding_migration_equivalent(expected, after):
        return True
    return before == after


def requires_explicit_resolution_commit(record: dict[str, Any], current_schema: int) -> bool:
    return int(record.get("schema_version", 1) or 0) >= current_schema
