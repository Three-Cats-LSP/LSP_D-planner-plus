#!/usr/bin/env python3
"""Verify Tier-3 engine sources are embedded in bundles (no mirror drift)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def strip_header(text: str) -> str:
    if text.startswith("/**"):
        end = text.find("*/")
        text = text[end + 2 :].lstrip()
    if text.startswith("'use strict';"):
        text = text[len("'use strict';") :].lstrip()
    elif text.startswith('"use strict";'):
        text = text[len('"use strict";') :].lstrip()
    return text


def normalize_js(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//.*?$", "", text, flags=re.M)
    text = re.sub(r"\s+", "", text)
    return text


def function_names(src: str) -> list[str]:
    return re.findall(r"^function\s+([A-Za-z_$][\w$]*)\s*\(", src, flags=re.M)


def extract_function_body(src: str, name: str) -> str:
    marker = f"function {name}("
    start = src.find(marker)
    if start < 0:
        return ""
    brace = src.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    i = brace
    in_line_comment = False
    in_block_comment = False
    in_single = False
    in_double = False
    in_template = False
    template_expr_depth = 0
    escape = False
    while i < len(src):
        ch = src[i]
        nxt = src[i + 1] if i + 1 < len(src) else ""
        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue
        if in_block_comment:
            if ch == "*" and nxt == "/":
                in_block_comment = False
                i += 2
                continue
            i += 1
            continue
        if in_single:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_single = False
            i += 1
            continue
        if in_double:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_double = False
            i += 1
            continue
        if in_template:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "`" and template_expr_depth == 0:
                in_template = False
            elif ch == "$" and nxt == "{":
                template_expr_depth += 1
                i += 2
                continue
            elif ch == "}" and template_expr_depth > 0:
                template_expr_depth -= 1
            i += 1
            continue
        if ch == "/" and nxt == "/":
            in_line_comment = True
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            i += 2
            continue
        if ch == "'":
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = True
            i += 1
            continue
        if ch == "`":
            in_template = True
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return src[start : i + 1]
        i += 1
    return ""


def api_export_present(bundle: str, name: str) -> bool:
    return bool(re.search(rf"\b{re.escape(name)}\b\s*,", bundle)) or bool(
        re.search(rf"\b{re.escape(name)}\b\s*\n", bundle)
    )


def extract_api_block(bundle: str) -> str:
    marker = "const api = {"
    start = bundle.find(marker)
    if start < 0:
        return ""
    brace = bundle.find("{", start)
    if brace < 0:
        return ""
    depth = 0
    i = brace
    while i < len(bundle):
        if bundle[i] == "{":
            depth += 1
        elif bundle[i] == "}":
            depth -= 1
            if depth == 0:
                return bundle[brace + 1 : i]
        i += 1
    return ""


def main() -> int:
    failures: list[str] = []

    ccr_src = strip_header((ROOT / "zhl-ccr-core.js").read_text(encoding="utf-8"))
    physics_src = strip_header((ROOT / "zhl-physics-core.js").read_text(encoding="utf-8"))
    gas_src = strip_header((ROOT / "zhl-gas-core.js").read_text(encoding="utf-8"))
    schedule_src = strip_header((ROOT / "zhl-schedule-core.js").read_text(encoding="utf-8"))
    vpm_src = strip_header((ROOT / "vpm-engine-core.js").read_text(encoding="utf-8"))

    zhl_bundle = (ROOT / "zhl-engine-bundle.js").read_text(encoding="utf-8")
    vpm_bundle = (ROOT / "vpm-engine-bundle.js").read_text(encoding="utf-8")

    for fn in function_names(ccr_src):
        if f"function {fn}(" not in zhl_bundle:
            failures.append(f"zhl-engine-bundle.js missing CCR function {fn}")

    for fn in function_names(physics_src):
        if f"function {fn}(" not in zhl_bundle:
            failures.append(f"zhl-engine-bundle.js missing physics function {fn}")

    for fn in function_names(gas_src):
        if f"function {fn}(" not in zhl_bundle:
            failures.append(f"zhl-engine-bundle.js missing gas helper {fn}")

    if "function runZhlScheduleCore(" not in zhl_bundle:
        failures.append("zhl-engine-bundle.js missing runZhlScheduleCore")

    for fn in function_names(ccr_src):
        src_body = normalize_js(extract_function_body(ccr_src, fn))
        bundle_body = normalize_js(extract_function_body(zhl_bundle, fn))
        if src_body and bundle_body and src_body != bundle_body:
            failures.append(f"zhl-ccr-core.js function {fn} diverges from bundle")

    for fn in ("getActiveGas", "enforceMinDecoProfile", "ppO2Check", "validateHypoxicDecoGas"):
        if fn not in function_names(gas_src):
            continue
        src_body = normalize_js(extract_function_body(gas_src, fn))
        bundle_body = normalize_js(extract_function_body(zhl_bundle, fn))
        if src_body and bundle_body and src_body != bundle_body:
            failures.append(f"zhl-gas-core.js function {fn} diverges from bundle")

    for fn in ("gfAtDepth", "ndlClearAtDepth", "buhNDL", "ceiling"):
        if fn not in function_names(physics_src):
            continue
        src_body = normalize_js(extract_function_body(physics_src, fn))
        bundle_body = normalize_js(extract_function_body(zhl_bundle, fn))
        if src_body and bundle_body and src_body != bundle_body:
            failures.append(f"zhl-physics-core.js function {fn} diverges from bundle")

    sched_embed = schedule_src.replace(
        "\nif (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;\n",
        "\n",
    ).replace(
        "function runZhlScheduleCore(params) {",
        "function runZhlScheduleCore(params) {\n  applyEnvironment(params.environment || defaultEnvironment());",
        1,
    )
    if normalize_js(sched_embed) not in normalize_js(zhl_bundle):
        failures.append("zhl-schedule-core.js body not embedded in zhl-engine-bundle.js")

    norm_vpm = normalize_js(vpm_src)
    norm_vpm_bundle_body = normalize_js(
        vpm_bundle.split("const VPMEngine = (() => {", 1)[1].rsplit("})();", 1)[0]
        if "const VPMEngine = (() => {" in vpm_bundle
        else vpm_bundle
    )
    if norm_vpm not in norm_vpm_bundle_body:
        failures.append("vpm-engine-core.js body diverges from vpm-engine-bundle.js")

    api_exports = [
        "normalizeCCRSettings",
        "getEffectivePpo2",
        "loadTissuesWithCCR",
        "getActiveGas",
        "enforceMinDecoProfile",
        "ceiling",
        "gfAtDepth",
        "ndlClearAtDepth",
        "buhNDL",
        "n2FracFromCustomO2",
        "n2FracFromPercentages",
        "validateHypoxicDecoGas",
        "ppO2Check",
        "applyEnvironment",
        "defaultEnvironment",
        "setHeHalfTimeMode",
        "OTU_EXPONENT",
    ]
    api_block = extract_api_block(zhl_bundle)
    for name in api_exports:
        if not api_export_present(api_block, name):
            failures.append(f"ZhlEngineBundle API missing export {name}")

    build_zhl = (ROOT / "tools" / "build_zhl_bundle.py").read_text(encoding="utf-8")
    if "index.html" in build_zhl and "read_text" in build_zhl and "getActiveGas" in build_zhl:
        failures.append("build_zhl_bundle.py still scrapes index.html for engine helpers")

    if not (ROOT / "tools" / "build_vpm_bundle.py").is_file():
        failures.append("tools/build_vpm_bundle.py missing (VPM bundle not automated)")

    if failures:
        print("ENGINE PARITY FAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("Engine source/bundle parity OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
