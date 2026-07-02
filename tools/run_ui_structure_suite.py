#!/usr/bin/env python3
"""Audit V3 UI structure suite (SUITE-UI-STRUCTURE)."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402
from tools.build_pages_site import ROOT_FILES  # noqa: E402
from tools.extract_ui_cores import EXPECTED_SCRIPT_ORDER  # noqa: E402
from tools.extract_ui_css import CSS_UNITS  # noqa: E402
from tools.ui_assets import PAGES_UI_ASSETS  # noqa: E402
from tools.verify_sw_assets import verify_sw_assets  # noqa: E402

INDEX = ROOT / "index.html"
SCRIPT_SRC_RE = re.compile(r'<script\s+src="([^"]+)"\s*></script>')
LINK_CSS_RE = re.compile(r'<link\s+href="([^"]+\.css)"\s+rel="stylesheet"/?>')


def _run(cmd: list[str]) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    output = (proc.stdout + proc.stderr).strip()
    return proc.returncode == 0, output


def _script_order_ok() -> tuple[bool, str]:
    html = INDEX.read_text(encoding="utf-8")
    actual = [src for src in SCRIPT_SRC_RE.findall(html) if not src.startswith("http")]
    cursor = -1
    for src in EXPECTED_SCRIPT_ORDER:
        try:
            cursor = actual.index(src, cursor + 1)
        except ValueError:
            return False, f"missing or out-of-order script {src}"
    return True, "UI core script order matches extract_ui_cores.py"


def _css_order_ok() -> tuple[bool, str]:
    html = INDEX.read_text(encoding="utf-8")
    actual = [href for href in LINK_CSS_RE.findall(html) if href.startswith("lsp-dplanner-")]
    expected = [filename for _, filename, _ in CSS_UNITS]
    cursor = -1
    for href in expected:
        try:
            cursor = actual.index(href, cursor + 1)
        except ValueError:
            return False, f"missing or out-of-order stylesheet {href}"
    return True, "CSS link order matches extract_ui_css.py"


def _pages_assets_ok() -> tuple[bool, str]:
  missing = sorted(path for path in PAGES_UI_ASSETS if path not in ROOT_FILES)
  if missing:
      return False, "build_pages_site ROOT_FILES missing: " + ", ".join(missing)
  return True, "Pages site copies all canonical UI runtime assets"


def main() -> int:
    rows = []

    ok, msg = _run([sys.executable, "tools/extract_ui_cores.py"])
    rows.append(case_row("UI-EXTRACT-CORES", ok, msg))

    ok, msg = _run([sys.executable, "tools/extract_ui_css.py"])
    rows.append(case_row("UI-EXTRACT-CSS", ok, msg))

    ok, msg = _run([sys.executable, "tools/assemble_ui_html.py", "--verify"])
    rows.append(case_row("UI-ASSEMBLE-MARKUP", ok, msg))

    ok, msg = _script_order_ok()
    rows.append(case_row("UI-SCRIPT-ORDER", ok, msg))

    ok, msg = _css_order_ok()
    rows.append(case_row("UI-CSS-LINK-ORDER", ok, msg))

    ok, msg = _pages_assets_ok()
    rows.append(case_row("UI-PAGES-ASSETS", ok, msg))

    sw_failures = verify_sw_assets()
    rows.append(case_row("UI-SW-PRECACHE", not sw_failures, sw_failures[0] if sw_failures else "sw precache ok"))

    passed = all(row.get("status") == "PASS" for row in rows)
    finish_suite(ROOT, rows, 0 if passed else 1)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
