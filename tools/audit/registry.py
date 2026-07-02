from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from tools import audit_coverage

from . import SCHEMA_VERSION

VALID_RULE_KINDS = {
    "parser.syntax",
    "js.no_duplicate_top_level_functions",
    "html.unique_ids",
    "html.script_order",
    "html.css_link_order",
    "html.dom_references_resolve",
    "extract.no_reinline",
}
VALID_LAYERS = {
    "web_shell",
    "ui_core",
    "ui_shell",
    "web_css",
    "web_markup",
    "web_runtime",
    "engine",
    "engine_reference",
    "tooling",
    "test",
    "test_infrastructure",
    "native",
    "native_bridge",
    "native_android",
    "native_config",
    "ci",
    "pwa",
    "worker",
    "release_config",
    "deploy_config",
    "build_config",
}
VALID_DISPOSITIONS = {
    "MIGRATED_STATIC",
    "MIGRATED_REGRESSION",
    "DUPLICATE",
    "OBSOLETE",
}
RECURSIVE_TOKENS = {"tools.audit", "run_all_regression.py", "audit.py"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_registry(root: Path) -> dict[str, Any]:
    return load_json(root / "docs" / "audit-units.json")


def _duplicates(values: list[str]) -> set[str]:
    return {value for value in values if values.count(value) > 1}


def legacy_assertion_sites(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    groups: list[tuple[int, str]] = []
    for lineno, line in enumerate(source.splitlines(), 1):
        match = re.match(r"# GROUP(?:\s+(\d+))?\s*[—-]\s*(.+)", line)
        if match:
            groups.append((lineno, match.group(1) or "X"))
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id not in {"ok", "fail"}:
            continue
        group = "BOOT"
        for group_line, group_id in groups:
            if group_line > node.lineno:
                break
            group = group_id
        sites.append(
            {
                "id": f"LEG-G{group}-L{node.lineno:05d}-{node.func.id.upper()}",
                "line": node.lineno,
                "call": node.func.id,
                "group": group,
            }
        )
    return sorted(sites, key=lambda item: (item["line"], item["call"]))


def validate_migration(root: Path) -> list[str]:
    errors: list[str] = []
    ledger_path = root / "docs" / "audit-legacy-migration.json"
    legacy_path = root / "tools" / "audit" / "legacy_v1.py"
    if not ledger_path.is_file():
        return ["legacy migration ledger missing"]
    ledger = load_json(ledger_path)
    current_hash = hashlib.sha256(legacy_path.read_bytes()).hexdigest()
    if ledger.get("legacy_sha256") != current_hash:
        errors.append("legacy migration ledger fingerprint is stale")
    actual = {item["id"] for item in legacy_assertion_sites(legacy_path)}
    entries = ledger.get("sites", [])
    declared = [item.get("id", "") for item in entries]
    if duplicates := _duplicates(declared):
        errors.append(f"duplicate legacy migration IDs: {', '.join(sorted(duplicates))}")
    missing = actual - set(declared)
    extra = set(declared) - actual
    if missing:
        errors.append(f"unmapped legacy assertion sites: {len(missing)}")
    if extra:
        errors.append(f"unknown legacy assertion sites: {len(extra)}")
    for entry in entries:
        disposition = entry.get("disposition")
        if disposition not in VALID_DISPOSITIONS:
            errors.append(f"{entry.get('id')}: invalid migration disposition")
        if not entry.get("rationale"):
            errors.append(f"{entry.get('id')}: migration rationale missing")
        if disposition in {"MIGRATED_STATIC", "MIGRATED_REGRESSION"} and not entry.get("replacement_ids"):
            errors.append(f"{entry.get('id')}: replacement IDs missing")
        if not isinstance(entry.get("independent_replacement"), bool):
            errors.append(f"{entry.get('id')}: independent_replacement must be boolean")
    return errors


def migration_summary(root: Path) -> dict[str, Any]:
    ledger = load_json(root / "docs" / "audit-legacy-migration.json")
    sites = ledger.get("sites", [])
    independent = sum(bool(site.get("independent_replacement")) for site in sites)
    policy = ledger.get("cutover_policy", {})
    required_runs = int(policy.get("required_consecutive_clean_main_runs", 3))
    recorded_runs = policy.get("recorded_runs", [])
    return {
        "total_sites": len(sites),
        "independently_replaced": independent,
        "pending_independent_replacement": len(sites) - independent,
        "required_clean_runs": required_runs,
        "recorded_clean_runs": len(recorded_runs),
        "cutover_ready": independent == len(sites) and len(recorded_runs) >= required_runs,
    }


def validate_registry_v2(root: Path, registry: dict[str, Any]) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors: list[str] = []
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"registry schema_version must be {SCHEMA_VERSION}")
    for unit in registry.get("units", []):
        layer = unit.get("layer", "")
        if layer and layer not in VALID_LAYERS:
            errors.append(f"{unit.get('id')}: unknown layer {layer!r}")
    tracked = audit_coverage.git_tracked_files(root)
    coverage_errors, resolved = audit_coverage.validate_registry(registry, root, tracked)
    errors.extend(coverage_errors)

    unit_ids = {unit.get("id") for unit in registry.get("units", [])}
    rules = registry.get("rule_catalog", [])
    rule_ids = [rule.get("id", "") for rule in rules]
    if duplicates := _duplicates(rule_ids):
        errors.append(f"duplicate rule IDs: {', '.join(sorted(duplicates))}")
    for rule in rules:
        rule_id = rule.get("id", "<unknown>")
        if rule.get("kind") not in VALID_RULE_KINDS:
            errors.append(f"{rule_id}: unknown rule kind")
        owners = rule.get("unit_ids", [])
        if not owners or any(owner not in unit_ids for owner in owners):
            errors.append(f"{rule_id}: invalid owning units")
        if rule.get("severity") not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
            errors.append(f"{rule_id}: invalid severity")
        if not rule.get("rationale") or not rule.get("remediation"):
            errors.append(f"{rule_id}: rationale and remediation are required")

    suites = registry.get("suite_catalog", [])
    suite_ids = [suite.get("id", "") for suite in suites]
    if duplicates := _duplicates(suite_ids):
        errors.append(f"duplicate suite IDs: {', '.join(sorted(duplicates))}")
    for suite in suites:
        suite_id = suite.get("id", "<unknown>")
        command = suite.get("command")
        if not isinstance(command, list) or not command or not all(isinstance(token, str) for token in command):
            errors.append(f"{suite_id}: command must be a non-empty argument array")
            continue
        command_text = " ".join(command)
        if any(token in command_text for token in RECURSIVE_TOKENS):
            errors.append(f"{suite_id}: recursive umbrella command is forbidden")
        if not set(suite.get("profiles", [])) <= {"static", "ci", "release"}:
            errors.append(f"{suite_id}: invalid profile")
        if not isinstance(suite.get("timeout_seconds"), int) or suite["timeout_seconds"] <= 0:
            errors.append(f"{suite_id}: positive timeout_seconds required")

    suite_id_set = set(suite_ids)
    suite_cases = {suite["id"]: set(suite.get("case_ids", [])) for suite in suites if suite.get("id")}
    evidence = registry.get("evidence_catalog", {})
    for evidence_id, spec in evidence.items():
        if spec.get("suite_id") not in suite_id_set:
            errors.append(f"evidence {evidence_id}: unknown suite_id")
        if not spec.get("case_id"):
            errors.append(f"evidence {evidence_id}: case_id missing")
        elif spec.get("case_id") not in suite_cases.get(spec.get("suite_id"), set()):
            errors.append(f"evidence {evidence_id}: case_id is not declared by its suite")

    evidence_ids = set(evidence)
    for finding in registry.get("findings", []):
        if finding.get("status") != "CLOSED":
            continue
        finding_id = finding.get("id", "<unknown>")
        if not finding.get("resolution_commit"):
            errors.append(f"finding {finding_id}: closed finding lacks resolution_commit")
        affected = finding.get("affected_units", [])
        if not affected or any(unit not in unit_ids for unit in affected):
            errors.append(f"finding {finding_id}: closed finding has invalid affected_units")
        cases = finding.get("evidence_cases", [])
        if not cases or any(case not in evidence_ids for case in cases):
            errors.append(f"finding {finding_id}: closed finding has invalid evidence_cases")

    errors.extend(validate_migration(root))
    ledger_path = root / "docs" / "audit-legacy-migration.json"
    if ledger_path.is_file():
        known_replacements = set(rule_ids) | suite_id_set
        for site in load_json(ledger_path).get("sites", []):
            unknown = sorted(set(site.get("replacement_ids", [])) - known_replacements)
            if unknown:
                errors.append(f"{site.get('id')}: unknown migration replacements {', '.join(unknown)}")
    return errors, resolved
