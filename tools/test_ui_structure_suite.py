#!/usr/bin/env python3
"""Tests for SUITE-UI-STRUCTURE leaf checks."""
from __future__ import annotations

from pathlib import Path
import re
import unittest

from tools.run_ui_structure_suite import _css_order_ok, _pages_assets_ok, _script_order_ok
from tools.verify_sw_assets import verify_sw_assets

REPO_ROOT = Path(__file__).resolve().parents[1]
IMPORTANT_SCAN_GLOBS = ("*.css", "*.js")
IMPORTANT_IGNORED_PARTS = {
    "_pages",
    "www",
    "node_modules",
    "Offline Zip",
    "GUE DecPlanner Binary",
}


def _iter_source_files() -> list[Path]:
    files: list[Path] = []
    for pattern in IMPORTANT_SCAN_GLOBS:
        for path in REPO_ROOT.rglob(pattern):
            rel = path.relative_to(REPO_ROOT)
            if rel.as_posix().startswith("android/app/src/main/assets/"):
                continue
            rel_parts = set(rel.parts)
            if rel_parts & IMPORTANT_IGNORED_PARTS:
                continue
            if path.name.endswith(".min.js"):
                continue
            files.append(path)
    return sorted(files)


def _important_is_allowed(rel: str, line: str, context: str) -> bool:
    if line.lstrip().startswith(("/*", "*", "//")):
        return True
    if re.search(r"@media\s+print", context):
        return True
    if re.search(r"prefers-reduced-motion", context):
        return True
    if "lsp-android-select-native" in context:
        return True
    if rel == "lsp-dplanner-mobile-shell.css" and re.search(
        r"(mobile-tab-|app-bottom-nav|mainNavBar|headerBanner|mobile-tools-list|mobile-tool-detail|mainVersionLabel|app-footer-promo)",
        context,
    ):
        return True
    if rel == "lsp-dplanner-results.css" and re.search(
        r"(desktop-only|mobile-only|mainTabsNav|legacy-panels|algo-bar|has-results|contingencyProfileLegend|gfCurveInlineCard|contingencyJumpBtn|decoAlertsNarcotic|app-shell-footer-links|algoRow|algorithmSelect|gfPresetSelect|gfCustomRow|hidden-v3)",
        context,
    ):
        return True
    if rel in {"lsp-dplanner-modes.css", "lsp-dplanner-foundation.css"} and re.search(
        r"(algo-tools|rec-mode|buh-only|\.panel|gfCustomRow|gfPresetsRowV3|gfPresetBtns)",
        context,
    ):
        return True
    return False


class UiStructureSuiteTests(unittest.TestCase):
    def test_script_order_matches_extract_contract(self) -> None:
        ok, _msg = _script_order_ok()
        self.assertTrue(ok)

    def test_css_link_order_matches_extract_contract(self) -> None:
        ok, _msg = _css_order_ok()
        self.assertTrue(ok)

    def test_pages_asset_list_is_complete(self) -> None:
        ok, _msg = _pages_assets_ok()
        self.assertTrue(ok)

    def test_sw_precache_covers_runtime_ui_assets(self) -> None:
        self.assertEqual([], verify_sw_assets())

    def test_unapproved_important_overrides_are_blocked(self) -> None:
        offenders: list[str] = []
        for path in _iter_source_files():
            rel = path.relative_to(REPO_ROOT).as_posix()
            text = path.read_text(encoding="utf-8")
            lines = text.splitlines()
            for idx, line in enumerate(lines):
                if "!important" not in line:
                    continue
                context = "\n".join(lines[max(0, idx - 40) : min(len(lines), idx + 41)])
                if not _important_is_allowed(rel, line, context):
                    offenders.append(f"{rel}:{idx + 1}: {line.strip()}")
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
