"""Read app version from app-version.js and verify release alignment."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_VERSION_JS = ROOT / "app-version.js"
INDEX = ROOT / "index.html"
SW = ROOT / "sw.js"
README = ROOT / "README.md"
PACKAGE = ROOT / "package.json"
GRADLE = ROOT / "android" / "app" / "build.gradle"


def read_app_version() -> str:
    text = APP_VERSION_JS.read_text(encoding="utf-8")
    m = re.search(r"(?:const APP_VERSION\s*=\s*|\.APP_VERSION\s*=\s*)'([^']+)'", text)
    if not m:
        raise SystemExit("APP_VERSION not found in app-version.js")
    return m.group(1)


def verify_sw_derives_cache(version: str) -> None:
    sw = SW.read_text(encoding="utf-8")
    if "importScripts('app-version.js')" not in sw:
        raise SystemExit("sw.js must importScripts('app-version.js')")
    if "const CACHE_VERSION = 'lsp-dplanner-plus-v' + APP_VERSION" not in sw:
        raise SystemExit("sw.js must derive CACHE_VERSION from APP_VERSION")
    if f"lsp-dplanner-plus-v{version}" not in f"lsp-dplanner-plus-v{version}":
        pass  # derived at runtime — no static string required


def verify_index_loads_version_js() -> None:
    html = INDEX.read_text(encoding="utf-8")
    if 'src="app-version.js"' not in html and "src='app-version.js'" not in html:
        raise SystemExit("index.html must load app-version.js")
    if re.search(r"const APP_VERSION\s*=\s*'", html):
        raise SystemExit("index.html must not duplicate APP_VERSION — use app-version.js")


def sync_package_json(version: str) -> bool:
    data = json.loads(PACKAGE.read_text(encoding="utf-8"))
    if data.get("version") == version:
        return False
    data["version"] = version
    PACKAGE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return True


def sync_gradle(version: str) -> bool:
    text = GRADLE.read_text(encoding="utf-8")
    parts = version.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        raise SystemExit(f"Invalid semver for versionCode: {version}")
    version_code = int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
    updated = text
    updated, n1 = re.subn(r'versionName\s+"[^"]+"', f'versionName "{version}"', updated, count=1)
    updated, n2 = re.subn(r"versionCode\s+\d+", f"versionCode {version_code}", updated, count=1)
    if n1 != 1 or n2 != 1:
        raise SystemExit("versionName/versionCode not found in build.gradle")
    if updated == text:
        return False
    GRADLE.write_text(updated, encoding="utf-8")
    return True


def sync_readme_badge(version: str) -> bool:
    text = README.read_text(encoding="utf-8")
    updated, n = re.subn(
        r"(> v)([\d.]+)( · MIT)",
        rf"\g<1>{version}\3",
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit("README badge line not found (> vX.Y.Z · MIT)")
    if updated == text:
        return False
    README.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    version = read_app_version()
    verify_sw_derives_cache(version)
    verify_index_loads_version_js()
    changed = []
    if sync_readme_badge(version):
        changed.append("README.md")
    if sync_package_json(version):
        changed.append("package.json")
    if sync_gradle(version):
        changed.append("build.gradle")
    if changed:
        print(f"Synced {', '.join(changed)} to {version}")
    else:
        print(f"Version {version} aligned (app-version.js, README.md, sw.js, package.json, build.gradle)")


if __name__ == "__main__":
    main()
