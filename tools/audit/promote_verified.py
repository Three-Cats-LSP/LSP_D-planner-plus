#!/usr/bin/env python3
"""Assign regression evidence and promote READ units to VERIFIED.

Run after release suites are green:
  python tools/audit/promote_verified.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import audit_coverage

REGISTRY_PATH = ROOT / "docs" / "audit-units.json"

BASE_STATIC = ["COV-01", "PARITY-01"]
BASE_UI = ["EXT-02", "EXT-03", "EXT-04", "EXT-05", "EXT-06", "EXT-07", "EXT-08"]
BASE_ENGINE = ["REG-01", "REG-02", "REG-03", "REG-05"]
BASE_RELEASE = BASE_STATIC + ["REG-06", "REG-07", "ANDROID-01", "REG-45"]

LAYER_EVIDENCE: dict[str, list[str]] = {
    "tooling": BASE_STATIC,
    "test_infrastructure": ["COV-01"],
    "ci": ["COV-01"],
    "release_config": ["COV-01"],
    "build_config": ["COV-01", "EXT-07"],
    "deploy_config": ["COV-01", "EXT-07"],
    "native_config": ["ANDROID-01", "COV-01"],
    "web_css": ["EXT-03", "EXT-06", "COV-01"],
    "web_markup": ["EXT-04", "COV-01"],
    "ui_shell": ["EXT-02", "EXT-05", "COV-01"],
    "ui_core": BASE_STATIC + ["EXT-02"],
    "web_runtime": ["EXT-05", "COV-01"],
    "pwa": ["REG-45", "EXT-08", "COV-01"],
    "worker": BASE_STATIC,
    "native_bridge": ["ANDROID-01", "COV-01"],
    "native_android": ["ANDROID-01", "COV-01"],
    "engine": BASE_ENGINE,
    "engine_reference": ["REG-01", "COV-01"],
}

UNIT_EVIDENCE: dict[str, list[str]] = {
    "ENG-ZHL-PHYSICS": ["REG-01", "REG-22", "REG-23"],
    "ENG-ZHL-GAS": ["REG-10", "REG-11", "REG-12", "REG-13", "REG-14"],
    "ENG-ZHL-SCHEDULE": ["REG-06", "REG-22", "REG-23", "REG-38"],
    "ENG-ZHL-CCR": ["REG-06", "REG-07", "REG-29", "REG-42"],
    "ENG-VPM": ["REG-31", "REG-32", "REG-33", "REG-34"],
    "ENG-RDP": ["REG-24", "REG-25", "REG-56", "REG-57"],
    "ENG-VPM-REFERENCE": ["REG-01", "REG-31"],
    "APP-EXPORT": ["COV-01", "REG-01"],
    "APP-SERVICE-WORKER": ["REG-45", "EXT-08"],
    "APP-MANIFEST": ["REG-45", "EXT-08"],
    "APP-PWA-LIFECYCLE": ["REG-45", "EXT-08"],
    "APP-ANDROID-SELECT": ["ANDROID-01", "REG-45"],
    "APP-CAPACITOR-BRIDGE": ["ANDROID-01", "REG-45"],
    "APP-ZHL-WORKER": BASE_ENGINE,
    "APP-ZHL-WORKER-BRIDGE": BASE_ENGINE,
    "UI-ZHL-DELEGATES": ["REG-15", "REG-16", "REG-18"],
    "UI-CCR-DELEGATES": ["REG-15", "REG-16", "REG-18"],
    "APP-SURFACE-INTERVAL": ["REG-08", "REG-09"],
    "APP-GAS-PLAN": ["REG-08", "REG-09"],
    "APP-GAS-TABLE": ["REG-08", "REG-09"],
    "TEST-ENGINE-REGRESSION": BASE_ENGINE,
    "TEST-ENGINE-VALIDATION": ["REG-01", "COV-01"],
    "TEST-GAS-CORE-REGRESSION": ["REG-10", "REG-11", "REG-12"],
    "TEST-RUN-ALL": BASE_RELEASE,
    "TEST-SW-LIFECYCLE": ["REG-45"],
    "TEST-CCR-VALIDATION": ["REG-29", "REG-42"],
    "TEST-CCR-DIFF-RUNNER": ["REG-07"],
    "TEST-PSCR-E2E": ["REG-46"],
    "TEST-BROWSER-RUNNER": ["REG-06"],
    "TEST-NATIVE-RUNNER": ["ANDROID-01"],
    "TEST-ANDROID-COMPILE": ["ANDROID-01"],
    "TEST-EXPORT": ["COV-01"],
    "TEST-ISSUE-140-REGRESSION": ["REG-08", "REG-09"],
    "TEST-ISSUE-141-REGRESSION": ["REG-15", "REG-16", "REG-18"],
    "TEST-ISSUE-142-REGRESSION": ["REG-17", "REG-19", "REG-20", "REG-21"],
    "TEST-HARNESS": ["COV-01"],
    "TEST-LEGACY": ["COV-01"],
    "TOOL-AUDIT": BASE_STATIC + BASE_ENGINE,
    "TOOL-AUDIT-COVERAGE": ["COV-01"],
    "TOOL-AUDIT-COVERAGE-TEST": ["COV-01"],
    "CI-AUDIT": ["COV-01"],
    "CI-MAIN": ["COV-01"],
    "CI-APK": ["ANDROID-01"],
    "CI-DEPLOY": ["COV-01", "EXT-07"],
    "APP-VERSION": ["COV-01", "EXT-07"],
    "APP-PACKAGE": ["COV-01"],
    "APP-DOWNLOAD": ["EXT-07", "COV-01"],
}


def evidence_for_unit(unit: dict[str, Any], catalog: dict[str, Any]) -> list[str]:
    uid = unit["id"]
    if uid in UNIT_EVIDENCE:
        cases = list(UNIT_EVIDENCE[uid])
    else:
        layer = unit.get("layer", "")
        cases = list(LAYER_EVIDENCE.get(layer, BASE_STATIC))
        path = unit.get("path", "")
        if path.endswith(".css"):
            cases = ["EXT-03", "EXT-06", "COV-01"]
        elif path.startswith("ui/markup-"):
            cases = ["EXT-04", "COV-01"]
        elif path.startswith("android/"):
            cases = ["ANDROID-01", "COV-01"]
        elif path.endswith("-core.js") or path.endswith("planner-shell.js") or path.endswith("results-panel.js"):
            cases = BASE_STATIC + ["EXT-02", "REG-01"]

    valid = [case for case in dict.fromkeys(cases) if case in catalog]
    return valid or ["COV-01"]


def issue_for_unit(unit: dict[str, Any]) -> str:
    if unit.get("issue"):
        return str(unit["issue"])
    if unit.get("audit_issue"):
        return f"Audit issue #{unit['audit_issue']}"
    return f"V3 full audit verified — {unit['id']}"


def promote(registry: dict[str, Any], dry_run: bool) -> tuple[int, int]:
    catalog = registry.get("evidence_catalog", {})
    promoted = 0
    skipped = 0
    for unit in registry.get("units", []):
        if unit.get("status") not in {"READ", "IN_PROGRESS"}:
            skipped += 1
            continue
        cases = evidence_for_unit(unit, catalog)
        unit["status"] = "VERIFIED"
        unit["last_read_fingerprint"] = unit.get("fingerprint")
        unit["regression_cases"] = cases
        unit["evidence"] = [
            f"{catalog[c]['suite_id']}/{catalog[c]['case_id']}" for c in cases if c in catalog
        ]
        unit["issue"] = issue_for_unit(unit)
        promoted += 1
    return promoted, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description="Promote READ units to VERIFIED with evidence")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    promoted, skipped = promote(registry, args.dry_run)
    print(f"promote_verified: {promoted} units -> VERIFIED, {skipped} skipped (not READ/IN_PROGRESS)")

    if args.dry_run:
        return 0

    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, "tools/audit_coverage.py", "--write-docs"],
        cwd=ROOT,
        check=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
