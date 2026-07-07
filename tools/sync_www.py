"""Copy all web assets required for PWA + Capacitor Android into www/."""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

ROOT = Path(__file__).resolve().parents[1]
WWW = ROOT / "www"

VERSION_JSON_URL_BASE = "https://threecats-lsp.com/d-planner-plus"
GITHUB_RELEASE_APK = (
    "https://github.com/Three-Cats-LSP/LSP_D-planner-plus/releases/latest/download/LSP_D-planner-plus.apk"
)

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
    "lsp-dplanner-foundation.css",
    "lsp-dplanner-modes.css",
    "lsp-dplanner-controls.css",
    "lsp-dplanner-results.css",
    "zhl-engine-bundle.js",
    "padi-engine.js",
    "vpm-engine-bundle.js",
    "zhl-worker-bridge.js",
    "zhl-schedule-worker.js",
    "planner-inputs-core.js",
    "rec-planner.js",
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
]

# Directories copied recursively (vendor fonts, jsPDF, partner icons)
ROOT_DIRS = [
    "vendor",
]

RMTREE_RETRIES = 6
RMTREE_RETRY_DELAY_SECONDS = 0.5


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
    payload = {
        "version": version,
        "versionCode": version_to_code(version),
        "apkUrl": GITHUB_RELEASE_APK,
        "apkFileName": f"LSP_D-planner-plus-v{version}.apk",
        "downloadPage": f"{VERSION_JSON_URL_BASE}/download.html",
    }
    text = json.dumps(payload, indent=2) + "\n"
    (ROOT / "version.json").write_text(text, encoding="utf-8", newline="\n")


def remove_tree_with_retries(path: Path) -> None:
    """Bound transient Windows file locks from recently closed Playwright servers."""
    last_error: OSError | None = None
    for attempt in range(RMTREE_RETRIES):
        try:
            shutil.rmtree(path)
            return
        except OSError as exc:
            last_error = exc
            if attempt == RMTREE_RETRIES - 1:
                break
            time.sleep(RMTREE_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"Could not remove {path} after {RMTREE_RETRIES} attempts: {last_error}") from last_error


def sync_www() -> None:
    from update_sw_version import main as verify_app_version
    verify_app_version()

    app_version_path = ROOT / "app-version.js"
    app_version = parse_app_version(app_version_path.read_text(encoding="utf-8"))
    write_version_json(app_version)

    if WWW.exists():
        remove_tree_with_retries(WWW)
    WWW.mkdir(parents=True)

    for name in ROOT_FILES:
        src = ROOT / name
        if not src.is_file():
            raise SystemExit(f"Missing required web asset: {name}")
        dest = WWW / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    for name in ROOT_DIRS:
        src = ROOT / name
        if not src.is_dir():
            raise SystemExit(f"Missing required web directory: {name}")
        shutil.copytree(src, WWW / name, dirs_exist_ok=True)

    shutil.copy2(ROOT / "version.json", WWW / "version.json")

    print(f"Synced {len(ROOT_FILES)} files + {len(ROOT_DIRS)} dirs -> {WWW}")
    print(f"Wrote version.json for {app_version}")


if __name__ == "__main__":
    sync_www()
