#!/usr/bin/env python3
"""Validate and report the machine-readable audit coverage registry."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "audit-units.json"
COVERAGE_DOC = ROOT / "docs" / "audit-coverage.md"
MASTER_DOC = ROOT / "docs" / "audit-master-plan.md"
VALID_STATUSES = {"UNREAD", "IN_PROGRESS", "READ", "VERIFIED"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def load_registry(path: Path = REGISTRY) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def git_tracked_files(root: Path = ROOT) -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    return [p.decode("utf-8") for p in proc.stdout.split(b"\0") if p]


def is_source_candidate(path: str, policy: dict[str, Any]) -> bool:
    name = Path(path).name
    if name in policy.get("exact_names", []):
        return True
    return Path(path).suffix.lower() in set(policy.get("extensions", []))


def matches_any(path: str, entries: list[dict[str, Any]]) -> bool:
    return any(fnmatch.fnmatch(path, entry["pattern"]) for entry in entries)


def unit_defaults(unit: dict[str, Any]) -> dict[str, Any]:
    out = {
        "priority": "P2",
        "status": "UNREAD",
        "fingerprint": "",
        "last_read_fingerprint": None,
        "evidence": [],
        "issue": None,
        "regression_cases": [],
    }
    out.update(unit)
    return out


def all_units(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [unit_defaults(unit) for unit in registry.get("units", [])]


def resolve_units(
    registry: dict[str, Any], root: Path = ROOT
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    errors: list[str] = []
    resolved: dict[str, dict[str, Any]] = {}
    by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in all_units(registry):
        by_path[unit["path"]].append(unit)

    for rel_path, units in by_path.items():
        path = root / rel_path
        if not path.is_file():
            errors.append(f"registered source missing: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        if not lines and text == "":
            lines = [""]

        types = {unit.get("boundary", {}).get("type") for unit in units}
        if types == {"whole_file"}:
            if len(units) != 1:
                errors.append(f"{rel_path}: whole_file requires exactly one unit")
                continue
            unit = units[0]
            resolved[unit["id"]] = {
                **unit,
                "start_line": 1,
                "end_line": len(lines),
                "line_count": len(lines),
                "current_fingerprint": sha256_text(text),
            }
            continue

        if types != {"marker"}:
            errors.append(f"{rel_path}: cannot mix boundary types {sorted(str(x) for x in types)}")
            continue

        marker_positions: list[tuple[int, dict[str, Any]]] = []
        for unit in units:
            marker = unit["boundary"].get("marker", "")
            hits = [
                idx for idx, line in enumerate(lines)
                if marker in re.findall(r"AUDIT-UNIT:[A-Z0-9-]+", line)
            ]
            if len(hits) != 1:
                errors.append(
                    f"{rel_path}: marker for {unit['id']} occurs {len(hits)} times"
                )
                continue
            marker_positions.append((hits[0], unit))

        if len(marker_positions) != len(units):
            continue
        marker_positions.sort(key=lambda item: item[0])
        declared_ids = [unit["id"] for unit in units]
        actual_ids = [unit["id"] for _, unit in marker_positions]
        if declared_ids != actual_ids:
            errors.append(f"{rel_path}: marker order differs from registry order")
        if marker_positions[0][0] != 0:
            errors.append(f"{rel_path}: first audit marker must be on line 1")

        for idx, (start, unit) in enumerate(marker_positions):
            end = marker_positions[idx + 1][0] if idx + 1 < len(marker_positions) else len(lines)
            if end <= start:
                errors.append(f"{rel_path}: empty or overlapping unit {unit['id']}")
                continue
            unit_text = "".join(lines[start:end])
            resolved[unit["id"]] = {
                **unit,
                "start_line": start + 1,
                "end_line": end,
                "line_count": end - start,
                "current_fingerprint": sha256_text(unit_text),
            }
    return resolved, errors


def validate_registry(
    registry: dict[str, Any], root: Path = ROOT, tracked: list[str] | None = None
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    if registry.get("schema_version") not in {1, 2}:
        errors.append("schema_version must be 1 or 2")

    units = all_units(registry)
    ids = [unit.get("id", "") for unit in units]
    duplicates = sorted(k for k, v in Counter(ids).items() if not k or v > 1)
    if duplicates:
        errors.append(f"duplicate or empty unit IDs: {', '.join(duplicates)}")

    evidence_catalog = registry.get("evidence_catalog", {})
    suite_ids = {suite.get("id") for suite in registry.get("suite_catalog", [])}
    for case_id, evidence in evidence_catalog.items():
        if registry.get("schema_version", 1) >= 2:
            if evidence.get("suite_id") not in suite_ids:
                errors.append(f"evidence {case_id}: unknown suite_id")
            if not evidence.get("case_id"):
                errors.append(f"evidence {case_id}: case_id missing")
            continue
        evidence_path = root / evidence.get("path", "")
        if not evidence_path.is_file():
            errors.append(f"evidence {case_id}: file missing")
            continue
        needle = evidence.get("needle", "")
        count = evidence_path.read_text(encoding="utf-8").count(needle)
        if not needle or count != 1:
            errors.append(f"evidence {case_id}: needle occurs {count} times")
        if not evidence.get("command"):
            errors.append(f"evidence {case_id}: command missing")

    for unit in units:
        unit_id = unit.get("id", "<missing>")
        for key in ("path", "layer", "boundary"):
            if not unit.get(key):
                errors.append(f"{unit_id}: missing {key}")
        if unit["status"] not in VALID_STATUSES:
            errors.append(f"{unit_id}: invalid status {unit['status']!r}")
        if unit["priority"] not in VALID_PRIORITIES:
            errors.append(f"{unit_id}: invalid priority {unit['priority']!r}")
        unknown_cases = sorted(set(unit["regression_cases"]) - set(evidence_catalog))
        if unknown_cases:
            errors.append(f"{unit_id}: unknown regression cases {', '.join(unknown_cases)}")
        if unit["status"] == "VERIFIED":
            if not unit["evidence"] or not unit["regression_cases"]:
                errors.append(f"{unit_id}: VERIFIED requires evidence and regression_cases")
            if not unit.get("issue"):
                errors.append(f"{unit_id}: VERIFIED requires an issue or review reference")

    resolved, resolve_errors = resolve_units(registry, root)
    errors.extend(resolve_errors)
    for unit_id, unit in resolved.items():
        current = unit["current_fingerprint"]
        if unit.get("fingerprint") != current:
            errors.append(f"{unit_id}: stored fingerprint is stale")
        if unit["status"] in {"READ", "VERIFIED"}:
            if unit.get("last_read_fingerprint") != current:
                errors.append(f"{unit_id}: {unit['status']} unit changed since its last read")
        elif unit.get("last_read_fingerprint"):
            errors.append(f"{unit_id}: {unit['status']} must not retain last_read_fingerprint")

    policy = registry.get("source_policy", {})
    generated = policy.get("generated", [])
    excluded = policy.get("excluded", [])
    registered_paths = {unit["path"] for unit in units}
    if tracked is None:
        tracked = git_tracked_files(root)
    candidates = [path for path in tracked if is_source_candidate(path, policy)]
    unknown = sorted(
        path for path in candidates
        if path not in registered_paths
        and not matches_any(path, generated)
        and not matches_any(path, excluded)
    )
    if unknown:
        errors.append("unregistered source files: " + ", ".join(unknown))
    for entry in generated:
        if not entry.get("generator") or not entry.get("check") or not entry.get("reason"):
            errors.append(f"generated pattern {entry.get('pattern')}: incomplete metadata")
    for entry in excluded:
        if not entry.get("kind") or not entry.get("reason"):
            errors.append(f"excluded pattern {entry.get('pattern')}: incomplete metadata")

    unit_ids = set(ids)
    scheduled: set[str] = set()
    for cycle in registry.get("cycles", []):
        if cycle.get("max_new_application_lines", 0) > 600:
            errors.append(f"Cycle {cycle.get('cycle')}: line budget exceeds 600")
        app_ids = cycle.get("application_units", [])
        for unit_id in app_ids + cycle.get("engine_reverification", []):
            if unit_id not in unit_ids:
                errors.append(f"Cycle {cycle.get('cycle')}: unknown unit {unit_id}")
        repeated = sorted(set(app_ids) & scheduled)
        if repeated:
            errors.append(f"Cycle {cycle.get('cycle')}: repeated units {', '.join(repeated)}")
        scheduled.update(app_ids)
        actual_lines = sum(resolved.get(unit_id, {}).get("line_count", 0) for unit_id in app_ids)
        if actual_lines > cycle.get("max_new_application_lines", 600):
            errors.append(
                f"Cycle {cycle.get('cycle')}: {actual_lines} application lines exceed budget"
            )

    for finding in registry.get("findings", []):
        severity = finding.get("severity")
        if severity not in VALID_SEVERITIES:
            errors.append(f"finding {finding.get('id')}: invalid severity")
        if finding.get("unit_id") not in unit_ids:
            errors.append(f"finding {finding.get('id')}: unknown unit")
        if not finding.get("issue"):
            errors.append(f"finding {finding.get('id')}: issue reference missing")
        if finding.get("status") == "OPEN" and severity in {"CRITICAL", "HIGH"}:
            errors.append(f"release-blocking finding remains open: {finding.get('id')}")

    return errors, resolved


def summary(registry: dict[str, Any], resolved: dict[str, dict[str, Any]]) -> dict[str, Any]:
    statuses = Counter(unit["status"] for unit in resolved.values())
    layers: dict[str, Counter[str]] = defaultdict(Counter)
    for unit in resolved.values():
        layers[unit["layer"]][unit["status"]] += 1
        layers[unit["layer"]]["TOTAL"] += 1
    return {"statuses": statuses, "layers": layers, "total": len(resolved)}


def render_coverage(registry: dict[str, Any], resolved: dict[str, dict[str, Any]]) -> str:
    data = summary(registry, resolved)
    lines = [
        "# Audit Coverage Ledger",
        "",
        "> Generated from `docs/audit-units.json` by `tools/audit_coverage.py`. Do not edit manually.",
        "",
        f"**Baseline:** `{registry['baseline_commit']}`",
        "**States:** `UNREAD`, `IN_PROGRESS`, `READ`, `VERIFIED`",
        "",
        "## Summary",
        "",
        "| Layer | Total | Unread | In progress | Read | Verified |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for layer, counts in sorted(data["layers"].items()):
        lines.append(
            f"| {layer} | {counts['TOTAL']} | {counts['UNREAD']} | "
            f"{counts['IN_PROGRESS']} | {counts['READ']} | {counts['VERIFIED']} |"
        )
    s = data["statuses"]
    lines.extend([
        f"| **Total** | **{data['total']}** | **{s['UNREAD']}** | **{s['IN_PROGRESS']}** | **{s['READ']}** | **{s['VERIFIED']}** |",
        "",
        "## Units",
        "",
        "| Unit | Layer | Source | Lines | Priority | Status | Evidence |",
        "|---|---|---|---:|---|---|---|",
    ])
    for unit in resolved.values():
        evidence = ", ".join(unit["regression_cases"] or unit["evidence"]) or "-"
        source = f"`{unit['path']}:{unit['start_line']}`"
        lines.append(
            f"| {unit['id']} | {unit['layer']} | {source} | {unit['line_count']} | "
            f"{unit['priority']} | {unit['status']} | {evidence} |"
        )
    return "\n".join(lines) + "\n"


def render_master(registry: dict[str, Any], resolved: dict[str, dict[str, Any]]) -> str:
    data = summary(registry, resolved)
    s = data["statuses"]
    lines = [
        "# Audit Master Plan v2.0",
        "",
        "> Generated schedule and totals. Policy and unit metadata live in `docs/audit-units.json`.",
        "",
        f"**Baseline:** `{registry['baseline_commit']}`",
        f"**Units:** {data['total']} total; {s['UNREAD']} unread; {s['IN_PROGRESS']} in progress; {s['READ']} read; {s['VERIFIED']} verified.",
        "**Gate:** `python -m tools.audit check --profile static`",
        "",
        "## Operating Rules",
        "",
        "- Audit P0 before P1, then P2/P3. Unit priority is not finding severity.",
        "- A cycle may read at most 600 new application-source lines plus one bounded engine re-verification unit.",
        "- Record actual findings only; there are no finding quotas or projections.",
        "- `VERIFIED` requires a current fingerprint and evidence that passes in the current audit profile.",
        "- Generated artifacts are validated by their generator and parity command, not manual READ coverage.",
        "- Open CRITICAL or HIGH findings fail the coverage gate and block release.",
        "",
        "## Seven Lenses",
        "",
        "1. Arithmetic and physics",
        "2. Control flow",
        "3. State and mutation",
        "4. API contracts",
        "5. Canonical/generated parity",
        "6. Safety regression",
        "7. Tooling and CI",
        "",
        "## Cycles 5-12",
        "",
        "| Cycle | Application units | New lines | Engine re-verification | Acceptance |",
        "|---:|---|---:|---|---|",
    ]
    for cycle in registry.get("cycles", []):
        app_ids = cycle.get("application_units", [])
        actual = sum(resolved[unit_id]["line_count"] for unit_id in app_ids)
        engines = ", ".join(cycle.get("engine_reverification", [])) or "-"
        lines.append(
            f"| {cycle['cycle']} | {', '.join(app_ids) or '-'} | {actual} | {engines} | {cycle['acceptance']} |"
        )
    lines.extend([
        "",
        "## Definition of Done",
        "",
        "- Every registered unit is READ and at least 85% are VERIFIED.",
        "- No open CRITICAL or HIGH findings remain.",
        "- `python -m tools.audit run --profile release` passes with every required leaf suite.",
        "- No tracked source is unregistered, stale, overlapping, or uncovered.",
        "- Generated bundles and deployment mirrors reproduce cleanly from canonical sources.",
        "",
        "## Session Card",
        "",
        "1. Pull `main`; run `python -m tools.audit check --profile static`.",
        "2. Read each selected unit in full and apply all seven lenses.",
        "3. Record unit ID, exact lines, lens, severity, issue, and regression case ID.",
        "4. Re-read fixed units, run the relevant suite, refresh fingerprints, and regenerate these reports.",
        "5. Close the cycle only when the registry and worktree are clean.",
    ])
    return "\n".join(lines) + "\n"


def refresh_fingerprints(registry: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    resolved, errors = resolve_units(registry, root)
    if errors:
        raise ValueError("; ".join(errors))
    for unit in registry["units"]:
        current = resolved[unit["id"]]["current_fingerprint"]
        changed = unit.get("fingerprint") not in (None, "", current)
        unit["fingerprint"] = current
        if unit.get("status") in {"READ", "VERIFIED"}:
            if changed:
                unit["status"] = "IN_PROGRESS"
                unit["last_read_fingerprint"] = None
                unit["evidence"] = []
                unit["regression_cases"] = []
            elif not unit.get("last_read_fingerprint"):
                unit["last_read_fingerprint"] = current
        else:
            unit["last_read_fingerprint"] = None
    return registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail on registry or generated-doc drift")
    parser.add_argument("--write-docs", action="store_true", help="regenerate Markdown views")
    parser.add_argument("--refresh-fingerprints", action="store_true", help="refresh unit content hashes")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    args = parser.parse_args()

    registry = load_registry(args.registry)
    if args.refresh_fingerprints:
        registry = refresh_fingerprints(registry)
        write_text_lf(args.registry, json.dumps(registry, indent=2) + "\n")

    errors, resolved = validate_registry(registry)
    if not errors:
        expected_coverage = render_coverage(registry, resolved)
        expected_master = render_master(registry, resolved)
        if args.write_docs:
            write_text_lf(COVERAGE_DOC, expected_coverage)
            write_text_lf(MASTER_DOC, expected_master)
        if args.check:
            if COVERAGE_DOC.read_text(encoding="utf-8") != expected_coverage:
                errors.append("docs/audit-coverage.md is not generated from the registry")
            if MASTER_DOC.read_text(encoding="utf-8") != expected_master:
                errors.append("docs/audit-master-plan.md is not generated from the registry")

    if errors:
        print("AUDIT COVERAGE FAILURES:")
        for error in errors:
            print(f"  - {error}")
        return 1

    data = summary(registry, resolved)
    s = data["statuses"]
    print(
        f"Audit coverage OK: {data['total']} units; "
        f"{s['UNREAD']} UNREAD, {s['IN_PROGRESS']} IN_PROGRESS, "
        f"{s['READ']} READ, {s['VERIFIED']} VERIFIED; "
        f"{len(registry.get('evidence_catalog', {}))} stable regression IDs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
