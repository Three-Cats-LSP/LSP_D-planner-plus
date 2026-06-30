#!/usr/bin/env python3
"""Compile Android Java sources and validate Gradle/XML (SUITE-ANDROID)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402

ANDROID = ROOT / "android"
FILE_PATHS = ROOT / "android" / "app" / "src" / "main" / "res" / "xml" / "file_paths.xml"


def android_sdk_root() -> Path | None:
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        val = os.environ.get(key, "").strip()
        if val:
            path = Path(val)
            if path.is_dir():
                return path
    local_props = ANDROID / "local.properties"
    if local_props.is_file():
        for line in local_props.read_text(encoding="utf-8").splitlines():
            if line.startswith("sdk.dir="):
                raw = line.split("=", 1)[1].strip()
                path = Path(raw.replace("\\\\", "/"))
                if path.is_dir():
                    return path
    return None


def ensure_local_properties(sdk: Path) -> None:
    props = ANDROID / "local.properties"
    line = f"sdk.dir={sdk.as_posix()}\n"
    if props.is_file() and line in props.read_text(encoding="utf-8"):
        return
    props.write_text(line, encoding="utf-8")


def main() -> int:
    errors: list[str] = []
    if not FILE_PATHS.is_file():
        errors.append("file_paths.xml missing")
    else:
        xml = FILE_PATHS.read_text(encoding="utf-8")
        if "<external-path" in xml:
            errors.append("file_paths.xml still exposes <external-path>")

    sdk = android_sdk_root()
    if sdk is None:
        if os.environ.get("GITHUB_ACTIONS") == "true" or os.environ.get("LSP_REQUIRE_ANDROID") == "1":
            errors.append("Android SDK not found (set ANDROID_HOME or android/local.properties)")
        else:
            print("Android compile check: SKIP (no SDK configured locally)")
            finish_suite(
                ROOT,
                [case_row("android-compile", True, "skipped locally: no Android SDK")],
                0,
            )
            return 0

    ensure_local_properties(sdk)
    gradlew = ANDROID / ("gradlew.bat" if sys.platform == "win32" else "gradlew")
    if not gradlew.is_file():
        errors.append(f"missing {gradlew}")
    else:
        proc = subprocess.run(
            [str(gradlew), "compileDebugJavaWithJavac", "--no-daemon", "-q"],
            cwd=ANDROID,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            errors.append((proc.stdout or proc.stderr or "gradle compile failed").strip()[:800])

    passed = not errors
    if passed:
        print("Android compile check: PASS")
    else:
        print("Android compile check: FAIL")
        for err in errors:
            print(f"  - {err}")
    finish_suite(
        ROOT,
        [case_row("android-compile", passed, "; ".join(errors))],
        0 if passed else 1,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    main()
