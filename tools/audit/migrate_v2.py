#!/usr/bin/env python3
"""One-time, idempotent registry-v2 and legacy-ledger migration."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools import audit_coverage
from tools.audit.registry import legacy_assertion_sites

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "audit-units.json"
LEDGER_PATH = ROOT / "docs" / "audit-legacy-migration.json"


SUITES = [
    {"id": "SUITE-BUILD-PAGES", "command": ["{python}", "tools/build_pages_site.py"], "profiles": ["static", "ci", "release"], "timeout_seconds": 120},
    {"id": "SUITE-COVERAGE", "command": ["{python}", "tools/test_audit_coverage.py"], "profiles": ["static", "ci", "release"], "timeout_seconds": 120},
    {"id": "SUITE-PARITY", "command": ["{python}", "tools/check_engine_parity.py"], "profiles": ["static", "ci", "release"], "timeout_seconds": 120},
    {"id": "SUITE-LEGACY", "command": ["{python}", "tools/audit/legacy_v1.py"], "profiles": ["static", "ci", "release"], "timeout_seconds": 180},
    {"id": "SUITE-EXPORT", "command": ["{python}", "export_regression.py"], "profiles": ["ci", "release"], "timeout_seconds": 300},
    {"id": "SUITE-ENGINE-VALIDATION", "command": ["{python}", "engine_validation_regression.py"], "profiles": ["ci", "release"], "timeout_seconds": 300},
    {"id": "SUITE-ENGINE-FULL", "command": ["{python}", "dev/engine_regression.py"], "profiles": ["ci", "release"], "timeout_seconds": 300},
    {"id": "SUITE-CCR-VALIDATION", "command": ["{python}", "dev/ccr_engine_validation_regression.py"], "profiles": ["release"], "timeout_seconds": 300},
    {"id": "SUITE-BROWSER", "command": ["{python}", "dev/run_browser_regression.py"], "profiles": ["release"], "timeout_seconds": 420},
    {"id": "SUITE-PSCR-E2E", "command": ["{python}", "dev/validate_pscr_e2e.py"], "profiles": ["release"], "timeout_seconds": 300, "env": {"SKIP_AUDIT": "1"}},
    {"id": "SUITE-CCR-DIFFERENTIAL", "command": ["{python}", "dev/run_ccr_differential.py"], "profiles": ["release"], "timeout_seconds": 420},
    {"id": "SUITE-NATIVE", "command": ["{python}", "dev/run_native_regression.py"], "profiles": ["release"], "timeout_seconds": 300},
]

SUITE_CASES = {
    "SUITE-BUILD-PAGES": ["pages-site-build"],
    "SUITE-COVERAGE": ["AUDIT-COV-01"],
    "SUITE-PARITY": ["canonical-generated-parity"],
    "SUITE-LEGACY": ["legacy-v1-clean-baseline", "extract-ui-marker-contract"],
    "SUITE-EXPORT": ["export-regression"],
    "SUITE-ENGINE-VALIDATION": ["engine-input-validation"],
    "SUITE-ENGINE-FULL": ["AUDIT-REG-01", "AUDIT-REG-02", "AUDIT-REG-03", "AUDIT-REG-05"],
    "SUITE-CCR-VALIDATION": ["ccr-input-validation"],
    "SUITE-BROWSER": ["gf-pinned-schedules", "browser-regression"],
    "SUITE-PSCR-E2E": ["pscr-e2e"],
    "SUITE-CCR-DIFFERENTIAL": ["ccr-differential-required-goldens"],
    "SUITE-NATIVE": ["native-bridge-regression"],
}
for suite in SUITES:
    suite["case_ids"] = SUITE_CASES[suite["id"]]

EVIDENCE = {
    "REG-01": {"suite_id": "SUITE-ENGINE-FULL", "case_id": "AUDIT-REG-01"},
    "REG-02": {"suite_id": "SUITE-ENGINE-FULL", "case_id": "AUDIT-REG-02"},
    "REG-03": {"suite_id": "SUITE-ENGINE-FULL", "case_id": "AUDIT-REG-03"},
    "REG-05": {"suite_id": "SUITE-ENGINE-FULL", "case_id": "AUDIT-REG-05"},
    "COV-01": {"suite_id": "SUITE-COVERAGE", "case_id": "AUDIT-COV-01"},
    "EXT-01": {"suite_id": "SUITE-LEGACY", "case_id": "extract-ui-marker-contract"},
    "REG-06": {"suite_id": "SUITE-BROWSER", "case_id": "gf-pinned-schedules"},
    "REG-07": {"suite_id": "SUITE-CCR-DIFFERENTIAL", "case_id": "ccr-differential-required-goldens"},
    "LEGACY-BASELINE": {"suite_id": "SUITE-LEGACY", "case_id": "legacy-v1-clean-baseline"},
    "PARITY-01": {"suite_id": "SUITE-PARITY", "case_id": "canonical-generated-parity"},
}

RULES = [
    {
        "id": "AUD-PARSE-001", "kind": "parser.syntax", "severity": "CRITICAL",
        "unit_ids": ["TOOL-AUDIT"],
        "rationale": "All registered JavaScript, HTML, and inline CSS must be parser-valid.",
        "remediation": "Correct the parser diagnostic at the reported source location.",
    },
    {
        "id": "AUD-JS-001", "kind": "js.no_duplicate_top_level_functions", "severity": "HIGH",
        "unit_ids": ["UI-BOOT"], "paths": ["index.html"],
        "rationale": "Duplicate top-level declarations can shadow runtime behavior.",
        "remediation": "Keep one canonical declaration and remove the duplicate.",
    },
    {
        "id": "AUD-HTML-001", "kind": "html.unique_ids", "severity": "HIGH",
        "unit_ids": ["UI-MARKUP-HEADER"], "paths": ["index.html"],
        "rationale": "Duplicate DOM IDs make UI reads and writes target-dependent.",
        "remediation": "Assign each rendered element a unique ID and update references.",
    },
    {
        "id": "AUD-HTML-002", "kind": "html.script_order", "severity": "CRITICAL",
        "unit_ids": ["UI-BOOT"], "paths": ["index.html"],
        "config": {"required": ["app-version.js", "capacitor-bridge.js", "zhl-engine-bundle.js", "vpm-engine-bundle.js", "zhl-worker-bridge.js"]},
        "rationale": "Runtime globals must load before dependent application code.",
        "remediation": "Restore the canonical dependency order in index.html.",
    },
]


def tool_unit(path: str) -> dict:
    return {
        "id": "TOOL-AUDIT-V2-" + path.rsplit("/", 1)[-1].replace(".", "-").upper(),
        "path": path,
        "layer": "tooling",
        "priority": "P0",
        "status": "IN_PROGRESS",
        "boundary": {"type": "whole_file"},
        "fingerprint": "",
        "last_read_fingerprint": None,
        "evidence": [],
        "regression_cases": [],
        "issue": "Ground-up audit architecture",
    }


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    registry["schema_version"] = 2
    extensions = registry["source_policy"]["extensions"]
    if ".mjs" not in extensions:
        extensions.append(".mjs")
    registry["suite_catalog"] = SUITES
    registry["evidence_catalog"] = EVIDENCE
    registry["rule_catalog"] = RULES
    registry["parser_config"] = {
        "wrappers": {
            "vpm-engine-core.js": {"prefix": "(function () {", "suffix": "})();"}
        }
    }

    for finding in registry.get("findings", []):
        finding.setdefault("affected_units", [finding["unit_id"]])
        finding.setdefault("resolution_commit", "legacy-history")
        finding.setdefault("evidence_cases", ["LEGACY-BASELINE"])
    for finding in registry.get("findings", []):
        if finding.get("id") == "REGRESSION-GF-CCR-FIX":
            finding["resolution_commit"] = "a83bbec"
            finding["affected_units"] = ["ENG-ZHL-SCHEDULE", "ENG-ZHL-CCR"]
            finding["evidence_cases"] = ["REG-06", "REG-07"]
            finding["summary"] = "GF pre-anchor and CCR endpoint corrected; verification requires REG-06 and REG-07 in the current release run"

    audit_files = [
        "audit.py",
        "docs/audit-legacy-migration.json",
        *sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "tools" / "audit").glob("*.*")),
    ]
    existing_paths = {unit["path"] for unit in registry["units"]}
    for path in audit_files:
        if path not in existing_paths:
            registry["units"].append(tool_unit(path))

    legacy_path = ROOT / "tools" / "audit" / "legacy_v1.py"
    sites = legacy_assertion_sites(legacy_path)
    existing_ledger = (
        json.loads(LEDGER_PATH.read_text(encoding="utf-8")) if LEDGER_PATH.is_file() else {}
    )
    existing_sites = {site.get("id"): site for site in existing_ledger.get("sites", [])}
    ledger_sites = []
    for site in sites:
        try:
            group_number = int(site["group"])
        except ValueError:
            group_number = 999
        static = group_number <= 15
        default_entry = {
                **site,
                "disposition": "MIGRATED_STATIC" if static else "MIGRATED_REGRESSION",
                "replacement_ids": ["AUD-PARSE-001", "AUD-JS-001"] if static else ["SUITE-LEGACY", "SUITE-ENGINE-FULL", "SUITE-BROWSER"],
                "rationale": "Parser-backed structural coverage" if static else "Preserved by blocking legacy baseline and behavioral release suites during staged migration",
                "independent_replacement": False,
            }
        previous = existing_sites.get(site["id"], {})
        for key in ("disposition", "replacement_ids", "rationale", "independent_replacement"):
            if key in previous:
                default_entry[key] = previous[key]
        ledger_sites.append(default_entry)
    ledger = {
        "schema_version": 1,
        "legacy_path": "tools/audit/legacy_v1.py",
        "legacy_sha256": hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
        "cutover_policy": {
            "required_consecutive_clean_main_runs": 3,
            "recorded_runs": existing_ledger.get("cutover_policy", {}).get("recorded_runs", []),
        },
        "sites": ledger_sites,
    }
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
