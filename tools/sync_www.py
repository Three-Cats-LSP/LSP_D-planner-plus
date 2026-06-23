"""Copy all web assets required for PWA + Capacitor Android into www/."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "www"

# Single files at repo root required for offline app + ZHL engine
ROOT_FILES = [
    "index.html",
    "capacitor-bridge.js",
    "manifest.json",
    "icon-192.png",
    "icon-512.png",
    "sw.js",
    "zhl-engine-bundle.js",
    "zhl-worker-bridge.js",
    "zhl-schedule-worker.js",
]

# Directories copied recursively (vendor fonts, jsPDF, partner icons)
ROOT_DIRS = [
    "vendor",
]


def sync_www() -> None:
    if WWW.exists():
        shutil.rmtree(WWW)
    WWW.mkdir(parents=True)

    for name in ROOT_FILES:
        src = ROOT / name
        if not src.is_file():
            raise SystemExit(f"Missing required web asset: {name}")
        shutil.copy2(src, WWW / name)

    for name in ROOT_DIRS:
        src = ROOT / name
        if not src.is_dir():
            raise SystemExit(f"Missing required web directory: {name}")
        shutil.copytree(src, WWW / name)

    print(f"Synced {len(ROOT_FILES)} files + {len(ROOT_DIRS)} dirs -> {WWW}")


if __name__ == "__main__":
    sync_www()
