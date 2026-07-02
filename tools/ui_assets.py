"""Canonical UI runtime asset lists shared by audit, Pages build, and SW checks."""
from __future__ import annotations

from tools.extract_ui_cores import EXPECTED_SCRIPT_ORDER, UI_CORE_BLOCKS
from tools.extract_ui_css import CSS_UNITS

UI_CORE_SCRIPTS: tuple[str, ...] = tuple(EXPECTED_SCRIPT_ORDER)
UI_CSS_FILES: tuple[str, ...] = tuple(filename for _, filename, _ in CSS_UNITS)
UI_MARKUP_PARTIALS: tuple[str, ...] = (
    "ui/markup-header.html",
    "ui/markup-planner.html",
    "ui/markup-consumption.html",
    "ui/markup-tools.html",
    "ui/markup-modals.html",
)
UI_SHELL_SCRIPTS: tuple[str, ...] = ("planner-shell.js", "results-panel.js")

RUNTIME_HEAD_SCRIPTS: tuple[str, ...] = (
    "app-version.js",
    "capacitor-bridge.js",
    "zhl-engine-bundle.js",
    "padi-engine.js",
    "vpm-engine-bundle.js",
    "zhl-worker-bridge.js",
)

PAGES_UI_ASSETS: tuple[str, ...] = (
    *UI_CSS_FILES,
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
)

SW_REQUIRED_UI_SCRIPTS: tuple[str, ...] = (
    "settings-core.js",
    "surf-interval-core.js",
    "gas-table-core.js",
    "gas-plan-core.js",
    "export-core.js",
    "contingency-core.js",
    "results-panel.js",
    "results-render-core.js",
    "planner-shell.js",
    "gas-cards-core.js",
    "plot-core.js",
)
