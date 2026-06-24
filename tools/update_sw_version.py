"""Sync sw.js CACHE_VERSION from index.html APP_VERSION."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"


def app_version() -> str:
    text = INDEX.read_text(encoding="utf-8")
    m = re.search(r"const APP_VERSION\s*=\s*'([^']+)'", text)
    if not m:
        raise SystemExit("APP_VERSION not found in index.html")
    return m.group(1)


def sync_sw_cache_version(sw_path: Path | None = None) -> str:
    path = sw_path or SW
    version = app_version()
    cache_name = f"lsp-dplanner-plus-v{version}"
    text = path.read_text(encoding="utf-8")
    updated, n = re.subn(
        r"const CACHE_VERSION\s*=\s*'[^']+';",
        f"const CACHE_VERSION = '{cache_name}';",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit(f"CACHE_VERSION line not found in {path}")
    if updated != text:
        path.write_text(updated, encoding="utf-8")
        print(f"Updated {path.name} CACHE_VERSION -> {cache_name}")
    else:
        print(f"{path.name} CACHE_VERSION already {cache_name}")
    return cache_name


if __name__ == "__main__":
    sync_sw_cache_version(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
