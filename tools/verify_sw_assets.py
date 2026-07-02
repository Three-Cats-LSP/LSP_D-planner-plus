#!/usr/bin/env python3
"""Verify service worker precache covers index.html runtime assets."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from tools.ui_assets import UI_CORE_SCRIPTS, UI_CSS_FILES  # noqa: E402

INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"

REQUIRED_RUNTIME_ASSETS: tuple[str, ...] = (
    *UI_CSS_FILES,
    *UI_CORE_SCRIPTS,
)
REQUIRED_BLOCK_RE = re.compile(
    r"const\s+REQUIRED_PRECACHE\s*=\s*\[(.*?)\];",
    re.DOTALL,
)
APP_BASE_ENTRY_RE = re.compile(r"APP_BASE\s*\+\s*'([^']+)'")


def index_runtime_assets() -> set[str]:
    return set(REQUIRED_RUNTIME_ASSETS)


def sw_required_assets() -> set[str]:
    source = SW.read_text(encoding="utf-8")
    block = REQUIRED_BLOCK_RE.search(source)
    if not block:
        raise SystemExit("sw.js missing REQUIRED_PRECACHE block")
    return set(APP_BASE_ENTRY_RE.findall(block.group(1)))


def verify_sw_assets() -> list[str]:
    failures: list[str] = []
    required = index_runtime_assets()
    precache = sw_required_assets()
    missing = sorted(path for path in required if path not in precache)
    if missing:
        failures.append("sw.js REQUIRED_PRECACHE missing: " + ", ".join(missing))
    return failures


def main() -> int:
    failures = verify_sw_assets()
    if failures:
        for item in failures:
            print(item, file=sys.stderr)
        return 1
    print("sw precache covers index.html runtime assets")
    return 0


if __name__ == "__main__":
    sys.exit(main())
