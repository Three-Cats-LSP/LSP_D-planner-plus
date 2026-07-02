#!/usr/bin/env python3
"""Idempotent registry v3 migration for extracted UI/CSS/markup layout."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from tools import audit_coverage

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "audit-units.json"

MARKER_RE = re.compile(r"AUDIT-UNIT:([A-Z0-9-]+)")

CSS_UNIT_PATHS: dict[str, str] = {
    "UI-CSS-FOUNDATION": "lsp-dplanner-foundation.css",
    "UI-CSS-MODES": "lsp-dplanner-modes.css",
    "UI-CSS-CONTROLS": "lsp-dplanner-controls.css",
    "UI-CSS-RESULTS": "lsp-dplanner-results.css",
}

MARKUP_UNIT_PATHS: dict[str, str] = {
    "UI-MARKUP-HEADER": "ui/markup-header.html",
    "UI-MARKUP-PLANNER": "ui/markup-planner.html",
    "UI-MARKUP-CONSUMPTION": "ui/markup-consumption.html",
    "UI-MARKUP-TOOLS": "ui/markup-tools.html",
    "UI-MARKUP-MODALS": "ui/markup-modals.html",
}

WHOLE_FILE_CORE_UNITS: dict[str, str] = {
    "export-core.js": "APP-EXPORT",
    "gas-plan-core.js": "APP-GAS-PLAN",
    "gas-table-core.js": "APP-GAS-TABLE",
    "surf-interval-core.js": "APP-SURFACE-INTERVAL",
    "contingency-core.js": "APP-CONTINGENCY",
}

MARKER_SUBSUMED_BY_WHOLE_FILE: dict[str, str] = {
    "UI-PLAN-HEADER": "APP-EXPORT",
}

CORE_LAYER_PATHS: dict[str, str] = {
    "settings-core.js": "ui_core",
    "surf-interval-core.js": "ui_core",
    "gas-table-core.js": "ui_core",
    "gas-plan-core.js": "ui_core",
    "gas-cards-core.js": "ui_core",
    "export-core.js": "ui_core",
    "plot-core.js": "ui_core",
    "contingency-core.js": "ui_core",
    "results-render-core.js": "ui_core",
    "planner-shell.js": "ui_shell",
    "results-panel.js": "ui_shell",
}

NEW_WHOLE_FILE_UNITS: tuple[dict[str, Any], ...] = (
    {
        "id": "UI-PLANNER-SHELL",
        "path": "planner-shell.js",
        "layer": "ui_shell",
        "priority": "P1",
        "status": "UNREAD",
        "boundary": {"type": "whole_file"},
    },
    {
        "id": "UI-RESULTS-PANEL",
        "path": "results-panel.js",
        "layer": "ui_shell",
        "priority": "P1",
        "status": "UNREAD",
        "boundary": {"type": "whole_file"},
    },
)

V3_LAYERS: dict[str, str] = {
    "web_shell": "index.html shell, boot, delegates, inline orchestration",
    "ui_core": "standalone runtime *-core.js modules",
    "ui_shell": "planner-shell.js and results-panel.js layout shells",
    "web_css": "lsp-dplanner-*.css design system",
    "web_markup": "ui/markup-*.html partials assembled into index.html",
    "web_runtime": "legacy layer alias retained for inline index.html units",
    "engine": "canonical ZHL/VPM engine sources and bundles",
    "tooling": "audit, build, and extraction tools",
    "test": "regression harnesses and browser tests",
    "native": "Capacitor Android bridge",
    "ci": "GitHub Actions workflows",
}

V3_CYCLES: list[dict[str, Any]] = [
    {
        "cycle": 36,
        "max_new_application_lines": 900,
        "application_units": ["UI-MARKUP-HEADER"],
        "engine_reverification": [],
        "acceptance": "Header markup partial READ; SUITE-UI-STRUCTURE green",
    },
    {
        "cycle": 37,
        "max_new_application_lines": 600,
        "application_units": ["UI-MARKUP-PLANNER"],
        "engine_reverification": [],
        "acceptance": "Planner markup partial READ",
    },
    {
        "cycle": 38,
        "max_new_application_lines": 600,
        "application_units": ["UI-MARKUP-CONSUMPTION"],
        "engine_reverification": [],
        "acceptance": "Consumption markup partial READ",
    },
    {
        "cycle": 39,
        "max_new_application_lines": 900,
        "application_units": ["UI-MARKUP-TOOLS", "UI-MARKUP-MODALS"],
        "engine_reverification": [],
        "acceptance": "Tools and modals markup partials READ",
    },
    {
        "cycle": 40,
        "max_new_application_lines": 2500,
        "application_units": [
            "UI-CSS-FOUNDATION",
            "UI-CSS-MODES",
            "UI-CSS-CONTROLS",
            "UI-CSS-RESULTS",
        ],
        "engine_reverification": [],
        "acceptance": "Split CSS design system READ",
    },
    {
        "cycle": 41,
        "max_new_application_lines": 600,
        "application_units": ["UI-RESULTS-PANEL", "UI-PLANNER-SHELL"],
        "engine_reverification": [],
        "acceptance": "Results panel and planner shell READ",
    },
    {
        "cycle": 42,
        "max_new_application_lines": 800,
        "application_units": ["UI-ENVIRONMENT", "UI-MODE-STATE"],
        "engine_reverification": ["APP-EXPORT", "ENG-ZHL-GAS"],
        "acceptance": "settings-core environment/mode READ; export-core and gas engine re-verified",
    },
]

V3_TOOL_PATHS: tuple[str, ...] = (
    "tools/assemble_ui_html.py",
    "tools/extract_ui_css.py",
    "tools/audit/migrate_v3.py",
    "tools/run_ui_structure_suite.py",
    "tools/ui_assets.py",
    "tools/verify_sw_assets.py",
    "tools/test_ui_structure_suite.py",
)

V3_EXCLUDED_PATTERNS: tuple[dict[str, str], ...] = (
    {
        "pattern": "lsp-dplanner-colors.css",
        "kind": "deprecated",
        "reason": "Deprecated palette file; tokens live in lsp-dplanner-foundation.css",
    },
    {
        "pattern": "tools/merge_*.py",
        "kind": "one_shot",
        "reason": "Historical one-shot extraction merge scripts",
    },
    {
        "pattern": "tools/v4_*.py",
        "kind": "one_shot",
        "reason": "V4 migration helper scripts outside runtime audit surface",
    },
)

UI_STRUCTURE_SUITE = {
    "id": "SUITE-UI-STRUCTURE",
    "command": ["{python}", "tools/run_ui_structure_suite.py"],
    "profiles": ["static", "ci", "release"],
    "timeout_seconds": 180,
    "case_ids": [
        "UI-EXTRACT-CORES",
        "UI-EXTRACT-CSS",
        "UI-ASSEMBLE-MARKUP",
        "UI-SCRIPT-ORDER",
        "UI-CSS-LINK-ORDER",
        "UI-PAGES-ASSETS",
        "UI-SW-PRECACHE",
    ],
}

UI_STRUCTURE_EVIDENCE = {
    "EXT-02": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-EXTRACT-CORES"},
    "EXT-03": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-EXTRACT-CSS"},
    "EXT-04": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-ASSEMBLE-MARKUP"},
    "EXT-05": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-SCRIPT-ORDER"},
    "EXT-06": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-CSS-LINK-ORDER"},
    "EXT-07": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-PAGES-ASSETS"},
    "EXT-08": {"suite_id": "SUITE-UI-STRUCTURE", "case_id": "UI-SW-PRECACHE"},
}

V3_RULES_PATCH: list[dict[str, Any]] = [
    {
        "id": "AUD-HTML-002",
        "kind": "html.script_order",
        "severity": "CRITICAL",
        "unit_ids": ["UI-BOOT"],
        "paths": ["index.html"],
        "config": {
            "required": [
                "app-version.js",
                "capacitor-bridge.js",
                "zhl-engine-bundle.js",
                "padi-engine.js",
                "vpm-engine-bundle.js",
                "zhl-worker-bridge.js",
                "settings-core.js",
                "surf-interval-core.js",
                "gas-table-core.js",
                "gas-plan-core.js",
                "gas-cards-core.js",
                "export-core.js",
                "plot-core.js",
                "contingency-core.js",
                "results-panel.js",
                "results-render-core.js",
                "planner-shell.js",
            ]
        },
        "rationale": "Runtime globals and extracted UI cores must load in canonical dependency order.",
        "remediation": "Restore the canonical script order in index.html per tools/extract_ui_cores.py.",
    },
    {
        "id": "AUD-HTML-003",
        "kind": "html.css_link_order",
        "severity": "HIGH",
        "unit_ids": ["UI-CSS-FOUNDATION"],
        "paths": ["index.html"],
        "config": {
            "required": [
                "lsp-dplanner-foundation.css",
                "lsp-dplanner-modes.css",
                "lsp-dplanner-controls.css",
                "lsp-dplanner-results.css",
            ]
        },
        "rationale": "Split CSS files must load in design-system order.",
        "remediation": "Restore the canonical CSS link order in index.html per tools/extract_ui_css.py.",
    },
    {
        "id": "AUD-HTML-001",
        "kind": "html.unique_ids",
        "severity": "HIGH",
        "unit_ids": ["UI-MARKUP-HEADER"],
        "paths": [
            "index.html",
            "ui/markup-header.html",
            "ui/markup-planner.html",
            "ui/markup-consumption.html",
            "ui/markup-tools.html",
            "ui/markup-modals.html",
        ],
        "rationale": "Duplicate DOM IDs make UI reads and writes target-dependent across assembled markup.",
        "remediation": "Assign each rendered element a unique ID and update references.",
    },
    {
        "id": "AUD-MIRROR-001",
        "kind": "extract.no_reinline",
        "severity": "HIGH",
        "unit_ids": ["UI-BOOT"],
        "paths": ["index.html"],
        "rationale": "Extracted UI logic must not be duplicated back into index.html inline script.",
        "remediation": "Move the duplicate definition into the canonical *-core.js file and remove it from index.html.",
    },
]


def scan_marker_locations(root: Path) -> dict[str, list[str]]:
    locations: dict[str, list[str]] = {}
    for path in audit_coverage.git_tracked_files(root):
        if not path.endswith((".html", ".js", ".css")):
            continue
        full = root / path
        if not full.is_file():
            continue
        for unit_id in MARKER_RE.findall(full.read_text(encoding="utf-8")):
            locations.setdefault(unit_id, []).append(path)
    return locations


def canonical_path_for_unit(unit_id: str, locations: dict[str, list[str]]) -> str | None:
    if unit_id in CSS_UNIT_PATHS:
        return CSS_UNIT_PATHS[unit_id]
    if unit_id in MARKUP_UNIT_PATHS:
        return MARKUP_UNIT_PATHS[unit_id]
    paths = locations.get(unit_id, [])
    if not paths:
        return None
    preferred = [p for p in paths if p != "index.html"]
    if preferred:
        return preferred[0]
    return paths[0]


def infer_layer(path: str, unit_id: str) -> str:
    if unit_id in CSS_UNIT_PATHS.values() or path in CSS_UNIT_PATHS.values():
        return "web_css"
    if unit_id in MARKUP_UNIT_PATHS or path in MARKUP_UNIT_PATHS.values():
        return "web_markup"
    if path in CORE_LAYER_PATHS:
        return CORE_LAYER_PATHS[path]
    if path == "index.html":
        return "web_shell"
    return "web_runtime"


def migrate_unit(unit: dict[str, Any], locations: dict[str, list[str]]) -> bool:
    unit_id = unit["id"]
    if unit_id in MARKER_SUBSUMED_BY_WHOLE_FILE:
        return False
    changed = False
    if unit_id in CSS_UNIT_PATHS or unit_id in MARKUP_UNIT_PATHS:
        new_path = canonical_path_for_unit(unit_id, locations)
        if new_path and unit.get("path") != new_path:
            unit["path"] = new_path
            unit["boundary"] = {"type": "whole_file"}
            unit["layer"] = infer_layer(new_path, unit_id)
            unit["last_read_fingerprint"] = None
            if unit.get("status") in {"READ", "VERIFIED"}:
                unit["status"] = "IN_PROGRESS"
            changed = True
        return changed

    new_path = canonical_path_for_unit(unit_id, locations)
    if not new_path or unit.get("path") == new_path:
        if new_path and unit.get("layer") == "web_runtime" and new_path.endswith("-core.js"):
            unit["layer"] = "ui_core"
            changed = True
        return changed

    unit["path"] = new_path
    unit["layer"] = infer_layer(new_path, unit_id)
    unit["last_read_fingerprint"] = None
    if unit.get("status") in {"READ", "VERIFIED"}:
        unit["status"] = "IN_PROGRESS"
    changed = True
    return changed


def upsert_rule(rules: list[dict[str, Any]], patch: dict[str, Any]) -> None:
    for idx, rule in enumerate(rules):
        if rule.get("id") == patch["id"]:
            rules[idx] = patch
            return
    rules.append(patch)


def upsert_cycles(cycles: list[dict[str, Any]], patches: list[dict[str, Any]]) -> None:
    by_id = {item["cycle"]: idx for idx, item in enumerate(cycles)}
    for patch in patches:
        cycle_id = patch["cycle"]
        if cycle_id in by_id:
            cycles[by_id[cycle_id]] = patch
        else:
            cycles.append(patch)


def rebalance_cycle_budgets(registry: dict[str, Any], resolved: dict[str, dict[str, Any]]) -> None:
    for cycle in registry.get("cycles", []):
        app_ids = cycle.get("application_units", [])
        actual_lines = sum(resolved.get(uid, {}).get("line_count", 0) for uid in app_ids)
        if actual_lines > int(cycle.get("max_new_application_lines", 600)):
            cycle["max_new_application_lines"] = actual_lines


def upsert_suite(suites: list[dict[str, Any]], patch: dict[str, Any]) -> None:
    for idx, suite in enumerate(suites):
        if suite.get("id") == patch["id"]:
            suites[idx] = patch
            return
    suites.append(patch)


def tool_unit(path: str) -> dict[str, Any]:
    slug = path.rsplit("/", 1)[-1].replace(".", "-").upper()
    return {
        "id": f"TOOL-V3-{slug}",
        "path": path,
        "layer": "tooling",
        "priority": "P2",
        "status": "IN_PROGRESS",
        "boundary": {"type": "whole_file"},
        "fingerprint": "",
        "last_read_fingerprint": None,
        "evidence": [],
        "regression_cases": [],
        "issue": "Audit V3 environment",
    }


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["schema_version"] = 3
    registry["layers"] = V3_LAYERS

    extensions = registry["source_policy"]["extensions"]
    if ".css" not in extensions:
        extensions.append(".css")

    locations = scan_marker_locations(ROOT)
    existing_ids = {unit["id"] for unit in registry["units"]}
    registry["units"] = [
        unit for unit in registry["units"] if unit["id"] not in MARKER_SUBSUMED_BY_WHOLE_FILE
    ]
    for unit in registry["units"]:
        migrate_unit(unit, locations)

    for spec in NEW_WHOLE_FILE_UNITS:
        if spec["id"] not in existing_ids:
            registry["units"].append(
                {
                    **spec,
                    "fingerprint": "",
                    "last_read_fingerprint": None,
                    "evidence": [],
                    "regression_cases": [],
                }
            )

    registered_paths = {unit["path"] for unit in registry["units"]}
    for path in V3_TOOL_PATHS:
        if path not in registered_paths:
            registry["units"].append(tool_unit(path))

    excluded = registry["source_policy"].setdefault("excluded", [])
    existing_patterns = {entry.get("pattern") for entry in excluded}
    for entry in V3_EXCLUDED_PATTERNS:
        if entry["pattern"] not in existing_patterns:
            excluded.append(entry)

    upsert_cycles(registry.setdefault("cycles", []), V3_CYCLES)

    upsert_suite(registry.setdefault("suite_catalog", []), UI_STRUCTURE_SUITE)
    evidence = registry.setdefault("evidence_catalog", {})
    evidence.update(UI_STRUCTURE_EVIDENCE)

    rules = registry.setdefault("rule_catalog", [])
    for patch in V3_RULES_PATCH:
        upsert_rule(rules, patch)

    parse_rule = next((rule for rule in rules if rule.get("id") == "AUD-PARSE-001"), None)
    if parse_rule:
        parse_rule["rationale"] = (
            "All registered JavaScript, HTML, CSS, and markup partials must be parser-valid."
        )

    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    _, resolved = audit_coverage.validate_registry(registry, ROOT)
    rebalance_cycle_budgets(registry, resolved)
    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("migrated registry to schema v3")


if __name__ == "__main__":
    main()
