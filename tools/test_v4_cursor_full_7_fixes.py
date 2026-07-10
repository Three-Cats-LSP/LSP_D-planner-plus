"""Static regressions for confirmed cursor_full_7.md fixer findings."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestV4CursorFull7Fixes(unittest.TestCase):
    def test_viewport_meta_precedes_native_lockdown_script(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        head = html.split("</head>", 1)[0]
        vp_match = re.search(r'<meta[^>]*name=["\']viewport["\'][^>]*>', head, re.I)
        self.assertIsNotNone(vp_match, "viewport meta must exist in <head>")
        lockdown = head.find("user-scalable=no")
        self.assertGreater(lockdown, -1, "native lockdown must set user-scalable=no")
        self.assertLess(
            vp_match.start(),
            lockdown,
            "viewport meta must appear before the lockdown script mutates it",
        )
        self.assertIn("maximum-scale=1.0", head)
        self.assertIn('name="mobile-web-app-capable"', head)
        self.assertIn('name="apple-mobile-web-app-capable"', head)

    def test_pdf_export_totals_use_rt_label(self) -> None:
        src = (ROOT / "export-core.js").read_text(encoding="utf-8")
        self.assertNotRegex(src, r"`Run:\s*\$\{")
        self.assertNotRegex(src, r"`Run:\s*\$\{c\.")
        self.assertGreaterEqual(src.count("`RT:"), 2)
        self.assertIn("TTS:", src)

    def test_ios_a2hs_dismissal_persists(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("lspIosA2hsDismissed", html)
        self.assertRegex(html, r"localStorage\.setItem\(\\'lspIosA2hsDismissed\\',\\'1\\'\)")
        self.assertIn("localStorage.getItem(IOS_A2HS_DISMISS_KEY)", html)
        self.assertNotIn("document.addEventListener('deviceready'", html)

    def test_android_select_accessible_name_source(self) -> None:
        src = (ROOT / "android-select-picker.js").read_text(encoding="utf-8")
        self.assertIn("btn.setAttribute('aria-label', titleForSelect(sel))", src)
        self.assertIn("item.setAttribute('aria-selected', 'true')", src)
        self.assertIn("item.setAttribute('aria-selected', 'false')", src)


if __name__ == "__main__":
    unittest.main()
