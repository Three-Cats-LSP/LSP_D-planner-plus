"""Copy all web assets required for PWA + Capacitor Android into www/."""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "www"

VERSION_JSON_URL_BASE = "https://threecats-lsp.com/d-planner-plus"
MIN_UPDATE_CHECK_VERSION = "2.50.00"

# Single files at repo root required for offline app + ZHL engine
ROOT_FILES = [
    "index.html",
    "app-version.js",
    "capacitor-bridge.js",
    "android-select-picker.js",
    "manifest.json",
    "icon-192.png",
    "icon-512.png",
    "sw.js",
    "zhl-engine-bundle.js",
    "vpm-engine-bundle.js",
    "zhl-worker-bridge.js",
    "zhl-schedule-worker.js",
]

# Directories copied recursively (vendor fonts, jsPDF, partner icons)
ROOT_DIRS = [
    "vendor",
]


def parse_app_version(app_version_js: str) -> str:
    match = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_version_js)
    if not match:
        raise SystemExit("Could not parse APP_VERSION from app-version.js")
    return match.group(1)


def version_to_code(version: str) -> int:
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise SystemExit(f"Invalid APP_VERSION format: {version}")
    major, minor, patch = (int(p) for p in parts)
    return major * 10000 + minor * 100 + patch


def write_version_json(version: str) -> None:
    apk_file = f"LSP_D-planner-plus-v{version}.apk"
    payload = {
        "version": version,
        "versionCode": version_to_code(version),
        "minUpdateCheckVersion": MIN_UPDATE_CHECK_VERSION,
        "apkUrl": f"{VERSION_JSON_URL_BASE}/{apk_file}",
        "downloadPage": f"{VERSION_JSON_URL_BASE}/download.html",
    }
    text = json.dumps(payload, indent=2) + "\n"
    (ROOT / "version.json").write_text(text, encoding="utf-8", newline="\n")


def sync_www() -> None:
    from update_sw_version import main as verify_app_version
    verify_app_version()

    app_version_path = ROOT / "app-version.js"
    app_version = parse_app_version(app_version_path.read_text(encoding="utf-8"))
    write_version_json(app_version)

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

    shutil.copy2(ROOT / "version.json", WWW / "version.json")

    print(f"Synced {len(ROOT_FILES)} files + {len(ROOT_DIRS)} dirs -> {WWW}")
    print(f"Wrote version.json for {app_version}")


if __name__ == "__main__":
    sync_www()