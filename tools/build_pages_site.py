"""Assemble a minimal GitHub Pages site (web app + browser tests only).

Excludes Knowledge Base PDFs, reverse-engineering binaries, APK, Android
sources, and other repo-only assets so deploy artifacts stay small.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "_pages"

ROOT_FILES = [
    ".nojekyll",
    "index.html",
    "download.html",
    "app-version.js",
    "capacitor-bridge.js",
    "manifest.json",
    "icon-192.png",
    "icon-512.png",
    "sw.js",
    "zhl-engine-bundle.js",
    "vpm-engine-bundle.js",
    "zhl-worker-bridge.js",
    "zhl-schedule-worker.js",
    "tests.html",
    "tests-extended.html",
    "tests-massive.html",
    "tests-massive-main.html",
    "tests-pscr-otu-cns.html",
    "tests-ccr-differential.html",
    "tests-verify.html",
]

ROOT_DIRS = [
    "vendor",
]

# Copied without Python build scripts (browser tests only).
CCR_DIFF = "tests/ccr-differential"
CCR_SKIP_SUFFIXES = {".py", ".pyc"}


def _copy_tree_filtered(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)

    for item in src.rglob("*"):
        rel = item.relative_to(src)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if item.suffix in CCR_SKIP_SUFFIXES:
            continue
        target = dst / rel
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)


def build_pages_site() -> Path:
    from update_sw_version import main as verify_app_version

    verify_app_version()
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    for name in ROOT_FILES:
        src = ROOT / name
        if not src.is_file():
            raise SystemExit(f"Missing required Pages asset: {name}")
        shutil.copy2(src, OUT / name)

    for name in ROOT_DIRS:
        src = ROOT / name
        if not src.is_dir():
            raise SystemExit(f"Missing required Pages directory: {name}")
        shutil.copytree(src, OUT / name)

    ccr_src = ROOT / CCR_DIFF
    if not ccr_src.is_dir():
        raise SystemExit(f"Missing required Pages directory: {CCR_DIFF}")
    _copy_tree_filtered(ccr_src, OUT / CCR_DIFF)

    file_count = sum(1 for p in OUT.rglob("*") if p.is_file())
    total_bytes = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"Built Pages site: {file_count} files, {total_bytes / 1024 / 1024:.2f} MB -> {OUT}")
    return OUT


if __name__ == "__main__":
    build_pages_site()
