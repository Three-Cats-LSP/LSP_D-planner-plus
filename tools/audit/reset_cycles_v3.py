#!/usr/bin/env python3
"""Reset audit cycles to V3 full-audit schedule starting at cycle 1."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from tools import audit_coverage

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "docs" / "audit-units.json"

# Each entry: (cycle_id, application_units, engine_reverification, acceptance)
V3_FULL_AUDIT_CYCLES: tuple[tuple[int, list[str], list[str], str], ...] = (
    (
        1,
        ["UI-MARKUP-HEADER"],
        [],
        "V3 cycle 1: header markup partial READ; SUITE-UI-STRUCTURE must be green",
    ),
    (2, ["UI-MARKUP-PLANNER"], [], "Planner markup partial READ"),
    (3, ["UI-MARKUP-CONSUMPTION"], [], "Consumption markup partial READ"),
    (4, ["UI-MARKUP-TOOLS", "UI-MARKUP-MODALS"], [], "Tools and modals markup partials READ"),
    (5, ["UI-CSS-FOUNDATION", "UI-CSS-MODES"], [], "Foundation and modes CSS READ"),
    (6, ["UI-CSS-CONTROLS"], [], "Controls CSS READ"),
    (7, ["UI-CSS-RESULTS"], [], "Results CSS READ"),
    (8, ["UI-PLANNER-SHELL", "UI-RESULTS-PANEL"], [], "Planner shell and results panel READ"),
    (9, ["UI-ENVIRONMENT", "UI-MODE-STATE"], [], "settings-core environment and mode state READ"),
    (10, ["APP-SURFACE-INTERVAL", "APP-GAS-TABLE"], [], "Surface interval and gas table cores READ"),
    (11, ["UI-GAS-INPUTS", "UI-GAS-CARDS"], ["ENG-ZHL-GAS"], "Gas card UI READ"),
    (12, ["APP-GAS-PLAN"], [], "Gas plan core READ"),
    (13, ["APP-CONTINGENCY"], [], "Contingency core READ"),
    (14, ["APP-EXPORT"], [], "export-core text/PDF READ"),
    (15, ["UI-PLOT-RENDER", "UI-PLOT-WAYPOINTS"], [], "plot-core render and waypoints READ"),
    (16, ["UI-TOOLS-PROFILE", "UI-PLOT-INIT"], [], "Profile tool and plot init READ"),
    (17, ["UI-VPM-RENDER", "UI-ZHL-RESULTS"], [], "results-render-core READ"),
    (
        18,
        ["UI-ZHL-DELEGATES", "UI-CCR-DELEGATES"],
        ["ENG-ZHL-SCHEDULE"],
        "ZHL/CCR delegate thin layer READ",
    ),
    (
        19,
        ["UI-DECO-PHYSICS", "UI-SCHEDULE-INPUTS"],
        ["ENG-ZHL-CCR"],
        "Deco physics and schedule inputs READ",
    ),
    (
        20,
        ["UI-ZHL-RUNNER-SETUP", "UI-ZHL-RUNNER-ENGINE"],
        ["ENG-ZHL-SCHEDULE"],
        "ZHL runner setup and engine invocation READ",
    ),
    (21, ["UI-ZHL-HEADLESS-HELPERS", "UI-ZHL-HEADLESS-ENGINE"], [], "Headless ZHL path READ"),
    (22, ["UI-VPM-RUNNER"], ["ENG-VPM"], "VPM runner READ"),
    (23, ["UI-RUNTIME-BOOTSTRAP", "UI-APP-INIT"], [], "Runtime bootstrap and app init READ"),
    (24, ["UI-ALGORITHM-SETTINGS", "UI-SETTINGS-CONTROLS"], [], "Algorithm and settings controls READ"),
    (25, ["UI-SETTINGS", "UI-UNIT-HELPERS", "UI-UNIT-SWITCHING"], [], "Settings persistence and unit helpers READ"),
    (26, ["UI-TOOLS-TISSUES", "UI-TOOLS-EXPOSURE", "UI-TOOLS-GF"], [], "Tools panels READ"),
    (27, ["UI-PROFILE-PRESETS", "UI-CONFIG-PRESETS"], [], "Profile and config presets READ"),
    (28, ["UI-BOOT"], [], "index.html shell boot region READ"),
    (29, ["APP-SERVICE-WORKER", "UI-PWA-LIFECYCLE", "APP-MANIFEST"], [], "PWA and service worker READ"),
    (30, ["APP-ZHL-WORKER", "APP-ZHL-WORKER-BRIDGE"], [], "ZHL schedule worker and bridge READ"),
    (31, ["APP-CAPACITOR-BRIDGE", "APP-ANDROID-SELECT"], [], "Capacitor and Android select bridge READ"),
    (32, ["ENG-ZHL-PHYSICS", "ENG-ZHL-GAS"], [], "ZHL physics and gas canonical cores READ"),
    (33, ["ENG-ZHL-SCHEDULE"], [], "ZHL schedule canonical core READ"),
    (34, ["ENG-ZHL-CCR"], [], "ZHL CCR canonical core READ"),
    (35, ["ENG-VPM"], [], "VPM canonical core READ"),
    (36, ["ENG-RDP"], [], "PADI RDP engine READ"),
    (37, ["ENG-VPM-REFERENCE"], [], "VPM reference implementation READ"),
    (38, ["APP-DOWNLOAD"], [], "Download page READ"),
    (
        39,
        [],
        ["TEST-ENGINE-REGRESSION", "TEST-ENGINE-VALIDATION", "TEST-GAS-CORE-REGRESSION"],
        "Engine and gas regression harnesses re-verified",
    ),
    (
        40,
        [],
        [
            "TEST-RUN-ALL",
            "TEST-SW-LIFECYCLE",
            "TEST-CCR-VALIDATION",
            "TEST-CCR-DIFF-RUNNER",
            "TEST-PSCR-E2E",
        ],
        "Full regression umbrella and release-tier test paths re-verified",
    ),
    (
        41,
        ["APP-PACKAGE"],
        ["CI-AUDIT", "CI-MAIN", "CI-APK", "CI-DEPLOY"],
        "Package manifest and CI workflows READ",
    ),
)

APPLICATION_RESET_LAYERS = {
    "web_markup",
    "web_css",
    "web_shell",
    "ui_core",
    "ui_shell",
    "web_runtime",
    "pwa",
    "worker",
    "native_bridge",
    "engine",
    "engine_reference",
    "release_config",
}


def current_head(root: Path) -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def build_cycles(resolved: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    cycles: list[dict[str, Any]] = []
    scheduled_app: set[str] = set()
    for cycle_id, app_units, engines, acceptance in V3_FULL_AUDIT_CYCLES:
        repeated = sorted(set(app_units) & scheduled_app)
        if repeated:
            raise ValueError(f"cycle {cycle_id}: repeated application units {repeated}")
        scheduled_app.update(app_units)
        actual_lines = sum(resolved[uid]["line_count"] for uid in app_units)
        cycles.append(
            {
                "cycle": cycle_id,
                "max_new_application_lines": max(actual_lines, 600),
                "application_units": app_units,
                "engine_reverification": engines,
                "acceptance": acceptance,
            }
        )
    return cycles


def reset_application_units(registry: dict[str, Any]) -> int:
    count = 0
    for unit in registry.get("units", []):
        if unit.get("layer") not in APPLICATION_RESET_LAYERS:
            continue
        unit["status"] = "UNREAD"
        unit["last_read_fingerprint"] = None
        unit["evidence"] = []
        unit["regression_cases"] = []
        count += 1
    return count


def register_reset_tool(registry: dict[str, Any]) -> None:
    path = "tools/audit/reset_cycles_v3.py"
    if any(unit.get("path") == path for unit in registry.get("units", [])):
        return
    registry["units"].append(
        {
            "id": "TOOL-V3-RESET-CYCLES-V3-PY",
            "path": path,
            "layer": "tooling",
            "priority": "P2",
            "status": "IN_PROGRESS",
            "boundary": {"type": "whole_file"},
            "fingerprint": "",
            "last_read_fingerprint": None,
            "evidence": [],
            "regression_cases": [],
            "issue": "Audit V3 cycle reset",
        }
    )
    excluded = registry["source_policy"].setdefault("excluded", [])
    patterns = {entry.get("pattern") for entry in excluded}
    if "dev/audit-cycle-log.json" not in patterns:
        excluded.append(
            {
                "pattern": "dev/audit-cycle-log.json",
                "kind": "audit_artifact",
                "reason": "Mutable V3 per-cycle agent workflow log",
            }
        )


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    register_reset_tool(registry)
    registry["schema_version"] = 3
    registry["baseline_commit"] = current_head(ROOT)
    registry["audit_epoch"] = "v3-full-reset"
    registry["cycles"] = []

    reset_count = reset_application_units(registry)
    registry = audit_coverage.refresh_fingerprints(registry, ROOT)
    _, resolved = audit_coverage.validate_registry(registry, ROOT)
    registry["cycles"] = build_cycles(resolved)

    errors, _resolved = audit_coverage.validate_registry(registry, ROOT)
    if errors:
        raise SystemExit("cycle reset validation failed:\n" + "\n".join(errors))

    REGISTRY_PATH.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"reset {len(registry['cycles'])} cycles (1-{registry['cycles'][-1]['cycle']}); "
        f"reset {reset_count} application units to UNREAD; "
        f"baseline {registry['baseline_commit'][:12]}"
    )


if __name__ == "__main__":
    main()
