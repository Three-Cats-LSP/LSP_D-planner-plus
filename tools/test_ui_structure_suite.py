#!/usr/bin/env python3
"""Tests for SUITE-UI-STRUCTURE leaf checks."""
from __future__ import annotations

import unittest

from tools.run_ui_structure_suite import _css_order_ok, _pages_assets_ok, _script_order_ok
from tools.verify_sw_assets import verify_sw_assets


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


if __name__ == "__main__":
    unittest.main()
