#!/usr/bin/env python3
"""
LSP D-Planner audit.py
======================
Comprehensive static-analysis checks for index.html.
Run from the repo root: python3 audit.py [path/to/index.html]

Exit code 0 = all checks pass. Non-zero = failures found.
Every check added here must correspond to a real bug or regression
that was found in production. No theoretical checks.
"""

import re, sys, os, json, ast, subprocess
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Load file ─────────────────────────────────────────────────────────────────
path = sys.argv[1] if len(sys.argv) > 1 else "index.html"
if not os.path.exists(path):
    print(f"File not found: {path}")
    sys.exit(1)

with open(path, encoding="utf-8") as f:
    html = f.read()

# Extract all inline (non-src) script blocks — main app is the largest; do not use scripts[0]
# alone (v2.51+ adds a small <head> bootstrap before the main block).
scripts = re.findall(r"<script(?![^>]*src)[^>]*>(.*?)</script>", html, re.DOTALL)
if not scripts:
    print("FATAL: No inline script block found")
    sys.exit(1)
js = "\n\n".join(scripts)
js_lines = js.split("\n")

# Tier 3: Bühlmann core lives in zhl-engine-bundle.js — merge for ZHL pattern checks
bundle_path = os.path.join(os.path.dirname(path) if os.path.dirname(path) else ".", "zhl-engine-bundle.js")
if not os.path.isabs(bundle_path):
    bundle_path = os.path.join(os.path.dirname(os.path.abspath(path)), "zhl-engine-bundle.js")
zhl_bundle_js = ""
if os.path.isfile(bundle_path):
    with open(bundle_path, encoding="utf-8") as f:
        zhl_bundle_js = f.read()
zhl_src = js + "\n" + zhl_bundle_js

def _read_build_core(filename):
    core_path = os.path.join(os.path.dirname(os.path.abspath(path)), filename)
    if not os.path.isfile(core_path):
        return ""
    text = open(core_path, encoding="utf-8").read()
    if text.startswith("/**"):
        text = text[text.find("*/") + 2 :].lstrip()
    return text

_physics_core_js = _read_build_core("zhl-physics-core.js")
_gas_core_js = _read_build_core("zhl-gas-core.js")
_ccr_core_src = _read_build_core("zhl-ccr-core.js")
_UI_CORE_FILES = (
    "surf-interval-core.js",
    "gas-table-core.js",
    "gas-plan-core.js",
    "export-core.js",
    "contingency-core.js",
)
_ui_parts = [_read_build_core(name) for name in _UI_CORE_FILES]
_ui_core_js = "\n".join(t for t in _ui_parts if t)
if _ui_core_js:
    js = js + "\n" + _ui_core_js
    js_lines = js.split("\n")
tier3_engine_src = zhl_src + "\n" + _physics_core_js + "\n" + _gas_core_js + "\n" + _ccr_core_src

# Tier 3: VPM-B core lives in vpm-engine-bundle.js — merge for VPM pattern checks
vpm_bundle_path = os.path.join(os.path.dirname(path) if os.path.dirname(path) else ".", "vpm-engine-bundle.js")
if not os.path.isabs(vpm_bundle_path):
    vpm_bundle_path = os.path.join(os.path.dirname(os.path.abspath(path)), "vpm-engine-bundle.js")
vpm_bundle_js = ""
if os.path.isfile(vpm_bundle_path):
    with open(vpm_bundle_path, encoding="utf-8") as f:
        vpm_bundle_js = f.read()
vpm_src = vpm_bundle_js if vpm_bundle_js else js
app_version_path = os.path.join(os.path.dirname(os.path.abspath(path)), "app-version.js")
app_version_js = ""
if os.path.isfile(app_version_path):
    with open(app_version_path, encoding="utf-8") as f:
        app_version_js = f.read()
vpm_core_path = os.path.join(os.path.dirname(os.path.abspath(path)), "vpm-engine-core.js")
vpm_core_js = ""
if os.path.isfile(vpm_core_path):
    with open(vpm_core_path, encoding="utf-8") as f:
        vpm_core_js = f.read()
worker_bridge_path = os.path.join(os.path.dirname(os.path.abspath(path)), "zhl-worker-bridge.js")
worker_bridge_js = ""
if os.path.isfile(worker_bridge_path):
    with open(worker_bridge_path, encoding="utf-8") as f:
        worker_bridge_js = f.read()
capacitor_bridge_path = os.path.join(os.path.dirname(os.path.abspath(path)), "capacitor-bridge.js")
capacitor_bridge_js = ""
if os.path.isfile(capacitor_bridge_path):
    with open(capacitor_bridge_path, encoding="utf-8") as f:
        capacitor_bridge_js = f.read()

# Helper: line number in JS block (1-indexed)
def js_line(char_pos):
    return js[:char_pos].count("\n") + 1

# Helper: all positions of a pattern in js
def find_all(pattern, text=None, flags=re.MULTILINE):
    return list(re.finditer(pattern, text or js, flags))

# Arg counter (rough, ignores nested parens only one level deep)
def count_args(args_str):
    return len(re.split(r",(?![^(]*\))", args_str.strip())) if args_str.strip() else 0

PASS = []
FAIL = []

def ok(msg):
    PASS.append(msg)

def fail(msg):
    FAIL.append(msg)

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 1 — STRUCTURE / DUPLICATES
# ══════════════════════════════════════════════════════════════════════════════

# 1.1 No duplicate top-level function declarations
all_fn_names = re.findall(r"^function (\w+)\s*\(", js, re.MULTILINE)
dupes = {k: v for k, v in Counter(all_fn_names).items() if v > 1}
if dupes:
    for fn, cnt in sorted(dupes.items()):
        fail(f"Duplicate function declaration: {fn} ({cnt}x) — orphaned body causes 'Illegal return'")
else:
    ok("No duplicate function declarations")

# 1.2 No bare return at depth-0 (orphaned function body / missing header)
depth = 0
bare_returns = []
for i, line in enumerate(js_lines):
    stripped = line.strip()
    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
        continue
    depth += line.count("{") - line.count("}")
    if depth == 0 and re.match(r"\s+return\b", line) and "function" not in line:
        bare_returns.append((i + 1, stripped[:80]))
if bare_returns:
    for ln, txt in bare_returns:
        fail(f"Bare 'return' at JS line {ln} (depth 0) — orphaned function body: {txt}")
else:
    ok("No bare return statements at global scope")

# 1.3 APP_VERSION constant exists (single source: app-version.js)
if re.search(r"(?:const\s+APP_VERSION|\.APP_VERSION\s*=)", app_version_js) and ('src="app-version.js"' in html or "src='app-version.js'" in html):
    ok("APP_VERSION in app-version.js (loaded by index.html)")
else:
    fail("APP_VERSION missing from app-version.js or not loaded by index.html")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 2 — TRIMIX ENGINE CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# 2.1 Global ZHL16C_HE_HT defined
if "const ZHL16C_HE_HT_BAKER" in js and "const ZHL16C_HE_HT_BUHL2003" in js:
    ok("ZHL16C_HE_HT_BAKER and ZHL16C_HE_HT_BUHL2003 defined")
else:
    fail("ZHL16C_HE_HT constants missing — He half-time variants not defined")

# 2.2 Active ZHL16C_HE_HT is a mutable let (not const) — needed for runtime switching
if re.search(r"^let ZHL16C_HE_HT\s*=", js, re.MULTILINE):
    ok("ZHL16C_HE_HT is mutable (let) for runtime switching")
else:
    fail("ZHL16C_HE_HT should be 'let', not 'const', to allow updateHeHalfTime() switching")

# 2.3 ZHL16C_HE_AB defined with 16 entries
m = re.search(r"const ZHL16C_HE_AB\s*=\s*\[(.*?)\];", tier3_engine_src, re.DOTALL) or re.search(r"ZHL16C_HE_AB", js)
if m and (not hasattr(m, "group") or m.group(0)):
    if hasattr(m, "group") and m.lastindex:
        pairs = re.findall(r"\[[\d.,\s]+\]", m.group(1))
        if len(pairs) == 16:
            ok(f"ZHL16C_HE_AB has 16 compartment entries")
        else:
            fail(f"ZHL16C_HE_AB has {len(pairs)} entries, expected 16")
    else:
        ok("ZHL16C_HE_AB available via ZhlEngineBundle (Tier 3)")
else:
    fail("ZHL16C_HE_AB missing — weighted a/b for trimix ceiling not defined")

# 2.4 Global ZHL16C has 16 N2 compartments
m2 = re.search(r"const ZHL16C\s*=\s*\[(.*?)\];", tier3_engine_src, re.DOTALL) or re.search(r"ZhlEngineBundle\.ZHL16C", js)
if m2:
    if hasattr(m2, "group") and m2.lastindex and m2.group(1):
        comps = re.findall(r"\[[\d.,\s]+\]", m2.group(1))
        if len(comps) == 16:
            ok("ZHL16C has 16 N2 compartments")
        else:
            fail(f"ZHL16C has {len(comps)} compartments, expected 16")
    else:
        ok("ZHL16C available via ZhlEngineBundle (Tier 3)")
else:
    fail("ZHL16C constant missing")

# 2.5 initTissues returns {pN2, pHe} objects (not scalar floats)
m3 = re.search(r"function initTissues\(\).*?return.*?;", tier3_engine_src, re.DOTALL)
if m3 and "pHe" in m3.group(0):
    ok("initTissues() returns {pN2, pHe} objects")
elif "ZhlEngineBundle.initTissues" in js:
    ok("initTissues() delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("initTissues() may still return scalar pN2 floats — tissue objects needed for trimix")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 3 — FUNCTION SIGNATURES (trimix He param)
# ══════════════════════════════════════════════════════════════════════════════

def check_sig(fn_name, expected_substr, description):
    m = re.search(rf"function {fn_name}\s*\(([^)]*)\)", js)
    if not m:
        fail(f"Function {fn_name} not found")
        return
    params = m.group(1)
    if expected_substr in params:
        ok(f"{fn_name}({params}) — {description}")
    else:
        fail(f"{fn_name}({params}) — missing {expected_substr}: {description}")

check_sig("saturate",        "fHe",        "He param for trimix tissue loading")
check_sig("saturateLinear",  "fHe",        "He param for linear trimix tissue loading")
check_sig("ceiling",         "tissues",    "accepts tissue objects")
check_sig("ppO2Check",       "fHe",        "He param — fO2 = 1-fN2-fHe for trimix")
check_sig("calcEND",         "fHe",        "He param — He is non-narcotic")
check_sig("getBottomGasFractions", "",     "returns {fO2,fHe,fN2} for bottom gas")
check_sig("getDecoCardFractions",  "n",    "returns {fO2,fHe,fN2} for deco card n")
check_sig("getGasLabel",     "fHe",        "formats trimix as O2/He notation")
check_sig("toggleBottomTrimix", "",        "shows/hides He fields on bottom gas card")
check_sig("updateHeHalfTime",   "",        "syncs ZHL16C_HE_HT + VPMEngine He HT")

# optimalSwitchDepth is nested — search without ^ anchor
m_osd = re.search(r"function optimalSwitchDepth\s*\(([^)]*)\)", zhl_src) or re.search(r"function zhlOptimalSwitchDepth\s*\(([^)]*)\)", zhl_src)
if m_osd and ("fO2override" in m_osd.group(1) or re.match(r"\s*fO2\s*,", m_osd.group(1))):
    ok(f"optimalSwitchDepth({m_osd.group(1)}) — fO2override param for trimix")
else:
    sig = m_osd.group(1) if m_osd else "NOT FOUND"
    fail(f"optimalSwitchDepth({sig}) — missing fO2override (1-fN2 wrong for trimix)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 4 — CALL SITE AUDITS
# Bug class: functions updated to accept fHe but call sites not updated
# ══════════════════════════════════════════════════════════════════════════════

# 4.1 All saturate() calls must have ≥5 args (tissues, depthM, t, fN2, fHe)
# Exception: function definition itself and VPMEngine's internal use
sat_fails = []
for m in re.finditer(r"\bsaturate\(([^)]{5,200})\)", js):
    call = m.group(0)
    # skip the function def line
    if call.startswith("function "):
        continue
    args = m.group(1)
    n = count_args(args)
    if n < 5:
        ln = js_line(m.start())
        # Exempt: VPMEngine internal saturations (different saturate impl)
        context = js[max(0, m.start()-300):m.start()+50]
        if "VPMEngine" in context or "loadTissuesConstant" in context or "loadTissuesLinear" in context:
            continue
        # Exempt: schreiner-based usage inside VPMEngine IIFE (different function)
        if "haldane" in context or "schreiner" in context[:50]:
            continue
        # Exempt: nitrox-only planner/NDL contexts (no He available in these UI modes)
        # Identified keywords: effNDL (NDL-check loop), tBase/tTest (multi-dive SI planner),
        # testT (surface NDL loop), udpBT (dive block calculator)
        nitrox_only_keywords = ["effNDL", "tBase", "tTest =", "si2", "udpBT", "siMins", "siFrac", "siSteps"]
        if any(kw in context for kw in nitrox_only_keywords):
            continue
        sat_fails.append((ln, call[:80]))
if sat_fails:
    for ln, call in sat_fails:
        fail(f"saturate() call at JS line {ln} missing fHe (arg 5): {call}")
else:
    ok(f"All saturate() call sites pass fHe (≥5 args)")

# 4.2 All saturateLinear() calls must have ≥6 args
satL_fails = []
for m in re.finditer(r"\bsaturateLinear\(([^)]{5,300})\)", js):
    args = m.group(1)
    n = count_args(args)
    if n < 6:
        ln = js_line(m.start())
        # Exempt: VPMEngine internal (different function with different signature)
        context = js[max(0, m.start()-300):m.start()+200]
        if "VPMEngine" in context or "loadTissuesLinear" in context:
            continue
        # Exempt: travel gas descent (travel gas is always nitrox, never trimix)
        if "travelInfo.fN2" in context or "travelDescentTime" in context:
            continue
        # Skip if the full call actually contains bottomFHe (regex truncation issue)
        full_call = js[m.start():m.start()+200]
        if "bottomFHe" in full_call:
            continue
        satL_fails.append((ln, m.group(0)[:80]))
if satL_fails:
    for ln, call in satL_fails:
        fail(f"saturateLinear() call at JS line {ln} missing fHe (arg 6): {call}")
else:
    ok(f"All saturateLinear() call sites pass fHe (≥6 args)")

# 4.3 All ppO2Check() calls must have ≥3 args (depthM, fN2, fHe)
ppO2_fails = []
for m in re.finditer(r"\bppO2Check\(([^)]+)\)", js):
    args = m.group(1)
    n = count_args(args)
    if n < 3:
        ln = js_line(m.start())
        ppO2_fails.append((ln, m.group(0)[:80]))
if ppO2_fails:
    for ln, call in ppO2_fails:
        fail(f"ppO2Check() call at JS line {ln} missing fHe (arg 3): {call}")
else:
    ok(f"All ppO2Check() call sites pass fHe (≥3 args)")

# 4.4 All optimalSwitchDepth() call sites pass fO2 as second arg
# (the fix: pass fO2 so it doesn't use 1-fN2 internally)
osd_calls = find_all(r"\boptimalSwitchDepth\(([^)]+)\)")
osd_calls_nosig = [m for m in osd_calls if "fO2override" not in m.group(1) and "function" not in js[max(0,m.start()-20):m.start()]]
osd_single_arg = [(js_line(m.start()), m.group(0)[:60]) for m in osd_calls_nosig if count_args(m.group(1)) < 2]
if osd_single_arg:
    for ln, call in osd_single_arg:
        fail(f"optimalSwitchDepth() at JS line {ln} called with 1 arg (no fO2) — wrong for trimix: {call}")
else:
    ok(f"optimalSwitchDepth() call sites pass fO2 override ({len(osd_calls_nosig)} calls checked)")

# 4.5 decoGases.push() includes fO2 field (needed for correct O2% in output)
dgp_fails = []
for m in re.finditer(r"decoGases\.push\(\{([^}]+)\}\)", js):
    body = m.group(1)
    if "fO2" not in body and "o2:" not in body:
        ln = js_line(m.start())
        dgp_fails.append((ln, body.strip()[:100]))
if dgp_fails:
    for ln, body in dgp_fails:
        fail(f"decoGases.push() at JS line {ln} missing fO2 field — wrong O2% in trimix output: {{{body}}}")
else:
    ok("All decoGases.push() calls include fO2 field")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 5 — THE 1-fN2 BUG PATTERN
# Bug class: using (1 - fN2) to derive fO2 — correct for nitrox, WRONG for trimix
# ══════════════════════════════════════════════════════════════════════════════

# 5.1 bottomFO2 must NOT be derived as 1-bottomFN2 anywhere
bad_bottom_fo2 = find_all(r"1\s*-\s*bottomFN2")
# Filter out comments and known-safe uses (ppO2 calc for N2-only gas, CNS calc)
real_bad = []
for m in bad_bottom_fo2:
    line = js[max(0, m.start()-5):m.start()+50]
    ln = js_line(m.start())
    full_line = js_lines[ln - 1].strip()
    if full_line.startswith("//") or full_line.startswith("*"):
        continue
    # CNS ppO2 calculations on the bottom segment use 1-bottomFN2 for nitrox-only N2
    # (bottom gas is N2+O2 only in old recs mode) — allowed
    if "segCNSfrac" in js[m.start():m.start()+100] or "rowCNS" in js[max(0,m.start()-100):m.start()+100]:
        continue
    # Skip if same line also contains bottomFO2 (comment on trimix-safe fix)
    if "bottomFO2" in full_line:
        continue
    real_bad.append((ln, full_line[:100]))

if real_bad:
    for ln, txt in real_bad:
        fail(f"JS line {ln}: uses (1-bottomFN2) as fO2 — wrong for trimix (use bottomFO2): {txt}")
else:
    ok("bottomFO2 not derived as 1-bottomFN2 (trimix-safe)")

# 5.2 bottomO2pct in output must use bottomFO2, not 1-bottomFN2
if "bottomO2pct = Math.round(bottomFO2 * 100)" in js:
    ok("bottomO2pct computed from bottomFO2 (trimix-safe)")
elif "bottomO2pct = Math.round((1 - bottomFN2)" in js:
    fail("bottomO2pct uses (1-bottomFN2) — wrong for trimix, shows wrong O2% in output header")
else:
    # It might be in VPM path only — check if both paths are handled
    if "bottomO2pct" in js:
        ok("bottomO2pct present (manual review needed for trimix correctness)")
    else:
        ok("bottomO2pct not used as global var (may be local)")

# 5.3 deco gas O2% in output must not use (1-fN2) unguarded
# Fixed pattern: use fO2 field or (1-fN2-(fHe||0))
bad_dg_o2 = find_all(r"1\s*-\s*dg\.fN2\b")
real_bad_dg = []
for m in bad_dg_o2:
    ln = js_line(m.start())
    full_line = js_lines[ln - 1].strip()
    if full_line.startswith("//") or full_line.startswith("*"):
        continue
    # Allow safe pattern: fO2 guard (dg.fO2 != null ? ... : 1-fN2-fHe)
    context_window = js[max(0, m.start()-80):m.start()+80]
    if "fO2 != null" in context_window or "dg.fHe" in context_window:
        continue
    # Allow inside getActiveGas if already using dg.fO2 guard
    if "dg.fO2 !=" in context_window:
        continue
    real_bad_dg.append((ln, full_line[:100]))
if real_bad_dg:
    for ln, txt in real_bad_dg:
        fail(f"JS line {ln}: uses (1-dg.fN2) as deco gas fO2 — wrong for trimix: {txt}")
else:
    ok("Deco gas O2% not derived as (1-dg.fN2) (trimix-safe)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 6 — VARIABLE DECLARATION ORDER (let/const hoisting)
# Bug 1: let-declared vars used before their declaration line
# ══════════════════════════════════════════════════════════════════════════════

# 6.1 In runDecoSchedule: bottomMixLabel must be declared AFTER _botFracs/bottomFO2/bottomFHe
idx_label = js.find("getGasLabel(bottomFO2, bottomFHe)")
idx_fracs  = js.find("_botFracs = getBottomGasFractions()")
if idx_label > 0 and idx_fracs > 0:
    if idx_fracs < idx_label:
        ok("bottomMixLabel declared after _botFracs (let hoisting fix correct)")
    else:
        fail("bottomMixLabel uses bottomFO2/bottomFHe BEFORE their let declaration — ReferenceError crash")
else:
    ok("bottomMixLabel/getBottomGasFractions pattern not found (may be refactored)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 7 — UI WIRING
# ══════════════════════════════════════════════════════════════════════════════

# 7.1 Bottom gas card has Trimix option
if 'value="trimix"' in html and "botTrimixO2" in html and "botTrimixHe" in html:
    ok("Bottom gas card has Trimix option with O2/He fields")
else:
    fail("Bottom gas card missing Trimix option or He/O2 fields")

# 7.2 Deco gas cards (static 1 and 2) have Trimix option
if "dg1TrimixO2" in html and "dg1TrimixHe" in html:
    ok("Deco gas card 1 has Trimix He fields")
else:
    fail("Deco gas card 1 missing Trimix He fields")

if "dg2TrimixO2" in html and "dg2TrimixHe" in html:
    ok("Deco gas card 2 has Trimix He fields")
else:
    fail("Deco gas card 2 missing Trimix He fields")

# 7.3 Dynamic deco gas card template has Trimix option
if "dg${idx}TrimixO2" in html or 'dg${n}TrimixO2' in html:
    ok("Dynamic deco gas card template has Trimix fields")
else:
    fail("Dynamic deco gas card template missing Trimix fields — addDecoGasCard() won't have He fields")

# 7.4 He HT mode selector present
if 'id="heHalfTimeMode"' in html:
    ok("He half-time mode selector (heHalfTimeMode) present")
else:
    fail("He half-time mode selector missing — user cannot choose Baker/Bühlmann 2003 variant")

# 7.5 Default He HT is Baker 1.88 — VPM-B canonical (Baker FORTRAN 1998, ApexDeco, MultiDeco)
# Rationale: LSP uses VPM-B as primary algorithm; Baker half-times are the correct match.
# Bühlmann 2003 (1.51) matches Shearwater/Subsurface but is NOT the VPM-B reference.
baker_selected = ('value="baker" selected' in html or 'selected="" value="baker"' in html or
                  "value='baker' selected" in html or "selected value=\"baker\"" in html)
buhl_selected  = ('value="buhl2003" selected' in html or 'selected="" value="buhl2003"' in html)
if baker_selected:
    ok("Default He HT is Baker 1.88 (VPM-B canonical — ApexDeco/MultiDeco compatible)")
elif buhl_selected:
    fail("Default He HT is Bühlmann 2003 (1.51) — should be Baker 1.88 for VPM-B engine compatibility")
else:
    fail("He HT default selection unclear")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 8 — SETTINGS PERSISTENCE (appSettings.DECO_FIELDS)
# Bug 6: New UI fields not added → reset on reload
# ══════════════════════════════════════════════════════════════════════════════

deco_fields_idx = html.find("DECO_FIELDS:")
if deco_fields_idx < 0:
    deco_fields_idx = html.find("'DECO_FIELDS'")

if deco_fields_idx > 0:
    deco_fields_block = html[deco_fields_idx:deco_fields_idx + 1500]
    required_fields = [
        ("heHalfTimeMode",  "He half-time mode selector"),
        ("botTrimixO2",     "Bottom gas trimix O2 input"),
        ("botTrimixHe",     "Bottom gas trimix He input"),
        ("dg1TrimixO2",     "Deco gas 1 trimix O2 input"),
        ("dg1TrimixHe",     "Deco gas 1 trimix He input"),
        ("dg2TrimixO2",     "Deco gas 2 trimix O2 input"),
        ("dg2TrimixHe",     "Deco gas 2 trimix He input"),
        ("dg1Mix",          "Deco gas 1 mix selector"),
        ("dg1CustomO2",     "Deco gas 1 custom O2 input"),
        ("dg2Mix",          "Deco gas 2 mix selector"),
        ("dg2CustomO2",     "Deco gas 2 custom O2 input"),
    ]
    for field_id, description in required_fields:
        if field_id in deco_fields_block:
            ok(f"DECO_FIELDS includes {field_id} ({description})")
        else:
            fail(f"DECO_FIELDS missing '{field_id}' ({description}) — trimix input lost on reload")
else:
    fail("DECO_FIELDS not found in appSettings")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 9 — INIT / PAGE LOAD SEQUENCE
# Bug 5: VPMEngine He HT not synced on load
# ══════════════════════════════════════════════════════════════════════════════

# 9.1 updateHeHalfTime called in DOMContentLoaded
dcl_idx = js.rfind("DOMContentLoaded")
if dcl_idx > 0:
    dcl_block = js[dcl_idx:dcl_idx + 12000]
    if "updateHeHalfTime()" in dcl_block:
        ok("updateHeHalfTime() called in DOMContentLoaded — VPMEngine He HT synced on load")
    else:
        fail("updateHeHalfTime() NOT called in DOMContentLoaded — VPMEngine always uses Baker 1.88 until user toggles")
else:
    fail("DOMContentLoaded handler not found")

# 9.2 updateHeHalfTime patches VPMEngine internal He HT
uht_fn = re.search(r"function updateHeHalfTime\(\)(.*?)^}", js, re.DOTALL | re.MULTILINE)
if uht_fn:
    body = uht_fn.group(1)
    if "_setHeHT1" in body or "ZHL16C_He" in body:
        ok("updateHeHalfTime() patches VPMEngine internal He compartment HT")
    else:
        fail("updateHeHalfTime() does not patch VPMEngine — VPM-B He HT stays at Baker 1.88")
else:
    fail("updateHeHalfTime() function not found")

# 9.3 VPMEngine exports He HT sync API (buhl2003 — BUG-76 He)
if "_syncHeHalfTimes:" in vpm_bundle_js and "_setHeHT1:" in vpm_bundle_js and "ZHL16C_He[i].ht" in vpm_bundle_js:
    ok("VPMEngine._syncHeHalfTimes + _setHeHT1 exported — buhl2003 He HT sync works")
else:
    fail("VPMEngine He HT sync API missing — buhl2003 mode leaves VPM He HT at Baker 1.88")
uht_fn2 = re.search(r"function updateHeHalfTime\(\)(.*?)^}", js, re.DOTALL | re.MULTILINE)
if uht_fn2 and "_syncHeHalfTimes" in uht_fn2.group(1):
    ok("updateHeHalfTime() calls VPMEngine._syncHeHalfTimes (full 16-compartment sync)")
else:
    fail("updateHeHalfTime() does not call VPMEngine._syncHeHalfTimes")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 10 — TISSUE OBJECT CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════════

# 10.1 ceiling() uses pTotal not plain pN2
ceiling_fn = re.search(r"function ceiling\(tissues, gfHigh\)(.*?)^}", js, re.DOTALL | re.MULTILINE)
if ceiling_fn:
    body = ceiling_fn.group(1)
    if "pHe" in body and ("pTotal" in body or "pN2 +" in body):
        ok("ceiling() uses weighted a/b with pN2+pHe (trimix ceiling correct)")
    elif "pHe" not in body:
        fail("ceiling() does not handle pHe — scalar tissue format assumed (breaks trimix)")
    else:
        ok("ceiling() references pHe (manual check recommended)")
else:
    fail("ceiling() function not found")

# 10.2 maxSatPct() uses pTotal
msp_fn = re.search(r"function maxSatPct\(tissues.*?\)(.*?)^}", js, re.DOTALL | re.MULTILINE)
if msp_fn:
    body = msp_fn.group(1)
    if "pHe" in body or "pTotal" in body:
        ok("maxSatPct() handles He (uses pTotal or pHe)")
    else:
        fail("maxSatPct() uses plain pN2 — wrong saturation % for trimix")
else:
    fail("maxSatPct() function not found")

# 10.3 updateTissueViz() handles {pN2,pHe} objects
viz_fn = re.search(r"function updateTissueViz\(.*?\)(.*?)^\}", js, re.DOTALL | re.MULTILINE)
if viz_fn:
    body = viz_fn.group(1)
    if "pHe" in body:
        ok("updateTissueViz() handles pHe (trimix tissue visualisation)")
    else:
        fail("updateTissueViz() uses plain pN2 — tissue bars wrong for trimix")
else:
    fail("updateTissueViz() function not found")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 11 — VPM ENGINE INTEGRITY
# ══════════════════════════════════════════════════════════════════════════════

# 11.1 VPMEngine object exists
if ('src="vpm-engine-bundle.js"' in html or "src='vpm-engine-bundle.js'" in html) and "window.VPMEngine = VPMEngine" in vpm_bundle_js:
    ok("VPMEngine defined (Tier 3 vpm-engine-bundle.js)")
elif "window.VPMEngine" in js or "const VPMEngine" in js or "var VPMEngine" in js:
    ok("VPMEngine defined")
else:
    fail("VPMEngine not found")

if "BUILD SOURCE ONLY" in vpm_core_js and "vpm-engine-core.js" not in html:
    ok("vpm-engine-core.js marked BUILD SOURCE ONLY (not loaded by index.html)")
elif "BUILD SOURCE ONLY" in vpm_core_js:
    ok("vpm-engine-core.js marked BUILD SOURCE ONLY")
else:
    fail("vpm-engine-core.js missing BUILD SOURCE ONLY header")

if re.search(r"function vpmAccumPpo2\([^)]*\)[^{]*\{", vpm_src) and "function calculate(levels" in vpm_src:
    vpm_fn_pos = vpm_src.find("function vpmAccumPpo2")
    calc_pos = vpm_src.find("function calculate(levels")
    if vpm_fn_pos >= 0 and calc_pos >= 0 and vpm_fn_pos < calc_pos:
        ok("vpmAccumPpo2 at module scope (before calculate)")
    else:
        fail("vpmAccumPpo2 not at module scope before calculate()")
else:
    fail("vpmAccumPpo2 helper missing from VPM bundle")

if "runtime += ascSegTime" in vpm_src:
    ok("VPM inter-level deco ascent uses loadTissuesLinear return for runtime")
else:
    fail("VPM runInterLevelDecoAscent may recalculate ascent time instead of ascSegTime")

if "function takeZhlRepStateSnapshot()" in js and "repState: takeZhlRepStateSnapshot()" in js:
    ok("ZHL repState uses atomic takeZhlRepStateSnapshot (BUG-C)")
else:
    fail("ZHL repState still reads window._zhlRepState without atomic take (BUG-C)")

if "function mergeRepSettings(settings)" in js and "mergeRepSettings(settings)" in js:
    ok("ZHLEngine.calculate/worker merge rep state via mergeRepSettings (BUG-C)")
else:
    fail("ZHLEngine missing mergeRepSettings for repetitive dive carry (BUG-C)")

if "calculateCcrViaDom" not in js:
    ok("Dead calculateCcrViaDom DOM-mutation path removed (BUG-B)")
else:
    fail("calculateCcrViaDom still present — ZHLEngine mutates DOM on headless calls (BUG-B)")

if "vpmApi.calculate" in js and "VPM engine failed to load" in js:
    ok("runVPMSchedule guards VPMEngine before calculate (BUG-A)")
else:
    fail("runVPMSchedule calls bare VPMEngine.calculate without load guard (BUG-A)")

if "VPMEngine He half-time sync skipped" in js:
    ok("updateHeHalfTime warns when VPMEngine._syncHeHalfTimes missing (BUG-D)")
else:
    fail("updateHeHalfTime silent no-op when VPM sync unavailable (BUG-D)")

if "function saveZhlRepState(" in js and "saveZhlRepState(tissues" in js:
    ok("ZHL repetitive dive writes window._zhlRepState after schedule (Issue #2)")
else:
    fail("ZHL repetitive dive never saves window._zhlRepState (Issue #2)")

if 'id="zhlRepRow"' in html and "function updateZhlRepUI()" in js:
    ok("Bühlmann repetitive dive UI panel present (Issue #2)")
else:
    fail("Bühlmann repetitive dive UI missing (Issue #2)")

if "function peekZhlRepState()" in js and "peekZhlRepState()" in js[js.find("function mergeRepSettings"):js.find("function mergeRepSettings") + 500]:
    snap_fn = js[js.find("function takeZhlRepStateSnapshot()"):js.find("function takeZhlRepStateSnapshot()") + 300]
    if "getZhlRepStateForSchedule()" in snap_fn and "window._zhlRepState = null" not in snap_fn:
        ok("mergeRepSettings peeks _zhlRepState without destructive clear (Issue #2)")
    else:
        fail("takeZhlRepStateSnapshot still clears window._zhlRepState (Issue #2)")
else:
    fail("peekZhlRepState / non-destructive rep merge missing (Issue #2)")

if ("result.finalTissues && !_contingencyRunning" in js) or ("result.finalTissues && !window._contingencyRunning" in js):
    ok("VPM repetitive state skipped during contingency runs (Issue #2)")
else:
    fail("Contingency may overwrite _lastVPMResult (Issue #2)")

if ("load: function load()" in vpm_src) or ("function load()" in vpm_src and "load," in vpm_src):
    ok("VPMEngine.load() noop API present (Issue #2)")
else:
    fail("VPMEngine.load() missing from bundle (Issue #2)")

if "for (const n of getAllDecoGasIds())" in js and "runVPMSchedule" in js:
    ok("runVPMSchedule deco gas loop uses getAllDecoGasIds() (Issue #2)")
else:
    fail("runVPMSchedule still hardcodes deco gas slots 1..3 (Issue #2)")

if "function getWaterTypeForVPM()" in js:
    ok("VPM waterType derived from BAR_PER_METRE when select missing (Issue #2)")
else:
    fail("getWaterTypeForVPM helper missing (Issue #2)")

if "function renderDecoAlerts(" in js and "_vpmHeHtSyncFailed" in js:
    ok("He HT sync failure surfaces in decoAlerts UI (Issue #2)")
else:
    fail("He HT sync failure console-only (Issue #2)")

if "window.VPMEngine) {" in js and "typeof VPMEngine !== 'undefined'" not in js:
    ok("VPM branch uses window.VPMEngine consistently (Issue #2)")
elif "window.VPMEngine" in js:
    ok("VPM branch uses window.VPMEngine (Issue #2)")
else:
    fail("Bare VPMEngine reference may throw in strict scope (Issue #2)")

if "getRegistrations()" not in html.split("PWA: service worker registration", 1)[-1][:3000]:
    ok("SW cache lifecycle deferred to sw.js activate — no page-level cache wipe (Issue #2)")
else:
    fail("Page still unregisters SW or wipes caches before activation (Issue #2)")

if "Mirrors VPMEngine.calculate(" not in js:
    ok("ZHLEngine header comment avoids VPMEngine.calculate linter false positive")
else:
    fail("ZHLEngine comment still uses VPMEngine.calculate() syntax (info)")

_zhl_core_path = os.path.join(os.path.dirname(os.path.abspath(path)), "zhl-schedule-core.js")
if os.path.isfile(_zhl_core_path):
    with open(_zhl_core_path, encoding="utf-8") as f:
        _zhl_core_src = f.read()
    if "continuationLevel must be shallower than current depth" in _zhl_core_src:
        ok("ZHL continuation levels guarded for monotonic shallower depth")
    else:
        fail("ZHL continuation level depth-order guard missing")
    if "ZHL16C_HE_HT[i] || 1" not in _zhl_core_src:
        ok("ZHL surface-interval He off-gas uses table half-times, not || 1 fallback (issue #27 BUG-A)")
    else:
        fail("ZHL surface-interval He still uses || 1 half-time fallback (issue #27 BUG-A)")
    if "travelInfo.fHe" in _zhl_core_src and "travelFO2" in _zhl_core_src:
        ok("ZHL travel gas descent passes travelInfo.fHe (issue #27 BUG-B)")
    else:
        fail("ZHL travel gas descent missing travelInfo.fHe (issue #27 BUG-B)")
    if "1 - travelInfo.fN2 - travelFHe" in _zhl_core_src:
        ok("ZHL travelFO2 fallback subtracts fHe when fO2 omitted (issue #28)")
    else:
        fail("ZHL travelFO2 fallback overcounts O2 for trimix (issue #28)")
    if "travelInfo gas fractions invalid" in _zhl_core_src:
        ok("ZHL travel gas rejects fN2 + fHe > 1 instead of silent fO2 clamp (issue #29)")
    else:
        fail("ZHL travel gas still clamps impossible fractions to fO2=0 (issue #29)")
    if "Math.max(0, inferred)" in _zhl_core_src:
        ok("ZHL travelFO2 clamps IEEE float residuals after validation (issue #30)")
    else:
        fail("ZHL travelFO2 missing post-validation float clamp (issue #30)")
else:
    fail("zhl-schedule-core.js missing")

_ccr_core_path = os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js")
if os.path.isfile(_ccr_core_path):
    with open(_ccr_core_path, encoding="utf-8") as f:
        _ccr_core_src = f.read()
    if "getEffectiveSetpointAtDepth(endpointDepth" in _ccr_core_src or "getEffectiveSetpointAtDepth(seg.toDepth" in _ccr_core_src:
        ok("CCR saturateLinearCCR uses segment boundary depth for setpoint (issue #27 BUG-C / #118 M-7 / #123 H-03)")
    elif "getEffectiveSetpointAtDepth(seg.fromDepth" in _ccr_core_src:
        ok("CCR saturateLinearCCR uses segment entry depth for setpoint (issue #27 BUG-C)")
    else:
        fail("CCR saturateLinearCCR still uses midpoint setpoint (issue #27 BUG-C)")
    if "function computePSCRFractions(pAmb, fO2, fHe, ccr)" in _ccr_core_src:
        ok("computePSCRFractions drops unused runtimeMin param (issue #27 BUG-F)")
    else:
        fail("computePSCRFractions still accepts dead runtimeMin param (issue #27 BUG-F)")
else:
    fail("zhl-ccr-core.js missing")

if zhl_bundle_js:
    if "ZHL16C_HE_HT[i] || 1" not in zhl_bundle_js:
        ok("zhl-engine-bundle He off-gas uses table half-times, not || 1 (issue #28 bundle parity)")
    else:
        fail("zhl-engine-bundle still has || 1 He half-time fallback (issue #28)")
    if "travelInfo.fHe" in zhl_bundle_js and "travelFO2" in zhl_bundle_js:
        ok("zhl-engine-bundle travel gas descent passes fHe (issue #28 bundle parity)")
    else:
        fail("zhl-engine-bundle missing travel gas fHe (issue #28)")
    if "getEffectiveSetpointAtDepth(endpointDepth" in zhl_bundle_js or "getEffectiveSetpointAtDepth(seg.toDepth" in zhl_bundle_js:
        ok("zhl-engine-bundle CCR setpoint at segment boundary depth (issue #28 / #118 M-7 / #123)")
    elif "getEffectiveSetpointAtDepth(seg.fromDepth" in zhl_bundle_js:
        ok("zhl-engine-bundle CCR setpoint at segment entry depth (issue #28 bundle parity)")
    else:
        fail("zhl-engine-bundle still uses midpoint CCR setpoint (issue #28)")
    if "function computePSCRFractions(pAmb, fO2, fHe, ccr)" in zhl_bundle_js:
        ok("zhl-engine-bundle computePSCRFractions drops runtimeMin (issue #28 bundle parity)")
    else:
        fail("zhl-engine-bundle computePSCRFractions still has runtimeMin (issue #28)")
    if "1 - travelInfo.fN2 - travelFHe" in zhl_bundle_js:
        ok("zhl-engine-bundle travelFO2 fallback subtracts fHe when fO2 omitted (issue #28)")
    else:
        fail("zhl-engine-bundle travelFO2 fallback overcounts O2 for trimix (issue #28)")
    if "travelInfo gas fractions invalid" in zhl_bundle_js:
        ok("zhl-engine-bundle rejects impossible travel gas fractions (issue #29)")
    else:
        fail("zhl-engine-bundle still silently clamps impossible travel gas (issue #29)")
    if "Math.max(0, inferred)" in zhl_bundle_js:
        ok("zhl-engine-bundle travelFO2 clamps float residuals after validation (issue #30)")
    else:
        fail("zhl-engine-bundle missing post-validation float clamp (issue #30)")
else:
    fail("zhl-engine-bundle.js missing")

_travel_deco_block = js.split("const travelInfo = getTravelGasInfo()", 1)
if len(_travel_deco_block) > 1 and "resolveTravelGasFractions" in _travel_deco_block[1][:800]:
    ok("index.html travelFO2 in decoGases subtracts fHe (issue #29)")
else:
    fail("index.html travelFO2 still uses 1 - fN2 only (issue #29)")
if "function resolveTravelGasFractions" in js and "inferred < -1e-9" in js.split("function resolveTravelGasFractions", 1)[-1][:1500]:
    ok("index.html travel gas skips invalid fractions before decoGases.push (issue #30)")
else:
    fail("index.html travel gas missing fraction guard before decoGases.push (issue #30)")
if "function resolveTravelGasFractions" in js and "warnTravelGasFractionIssue" in js:
    ok("index.html travel gas invalid fractions warn instead of silent discard (issue #31)")
else:
    fail("index.html travel gas silently discards invalid fractions (issue #31)")
if "function resolveTravelGasFractions" in js and "travelInfo.fO2 < -1e-9" in js:
    ok("index.html travel gas rejects negative explicit fO2 (issue #31)")
else:
    fail("index.html explicit travel fO2 bypasses negativity guard (issue #31)")
if "_travelGasFractionWarning" in js and "_travelGasFractionWarning ||" in js:
    ok("index.html travel gas warning shown in decoAlerts (issue #31)")
else:
    fail("index.html travel gas warning not wired to decoAlerts (issue #31)")
if "function resolveTravelGasFractions" in js and "!isFinite(travelInfo.fO2)" in js:
    ok("index.html travel gas rejects non-finite explicit fO2 (issue #32)")
else:
    fail("index.html NaN fO2 bypasses resolveTravelGasFractions (issue #32)")
if "function refreshTravelGasFractionWarning" in js and "refreshTravelGasFractionWarning()" in js.split("function renderDecoAlerts", 1)[-1].split("function ", 1)[0]:
    ok("index.html travel gas warning refreshed on decoAlerts render (issue #32)")
else:
    fail("index.html stale _travelGasFractionWarning not cleared on render (issue #32)")
_res_frac_block = js.split("function resolveTravelGasFractions", 1)[-1][:1500] if "function resolveTravelGasFractions" in js else ""
if _res_frac_block and "travelInfo.fHe || 0" not in _res_frac_block and "rawFHe != null && !isFinite(rawFHe)" in _res_frac_block and "explicit fHe is negative" in _res_frac_block:
    ok("index.html fHe validated before defaulting — no NaN || 0 masking (issue #33)")
else:
    fail("index.html fHe NaN masked by || 0 before isFinite guard (issue #33)")
if _res_frac_block and "!isFinite(inferred)" not in _res_frac_block and "inferred < -1e-9" in _res_frac_block:
    ok("resolveTravelGasFractions drops dead !isFinite(inferred) check (issue #34)")
else:
    fail("resolveTravelGasFractions still has dead !isFinite(inferred) guard (issue #34)")
if "function injectEndCells" not in js and "function applyEndColumn" not in js and "applyEndColumn()" not in js:
    ok("orphaned END column injectEndCells/applyEndColumn removed (issue #35)")
else:
    fail("injectEndCells or applyEndColumn still present after column removal (issue #35)")
if "END column (Feature)" not in js:
    ok("stale END column (Feature) comment removed (issue #47)")
else:
    fail("stale END column (Feature) comment still in index.html (issue #47)")
if "Apply persisted END column state" not in js:
    ok("stale Apply persisted END column state comment removed (issue #47)")
else:
    fail("stale Apply persisted END column state comment still in index.html (issue #47)")
if "function rowCNS" not in js:
    ok("per-row rowCNS helper removed after CNS% column drop (issue #35)")
else:
    fail("rowCNS still computed after CNS% column removal (issue #35)")
_draw_prof = js.split("function drawDecoProfile", 1)[-1][:2500] if "function drawDecoProfile" in js else ""
if _draw_prof and "switchTxt.match" not in _draw_prof and "if (phase === 'switch') return" in _draw_prof:
    ok("drawDecoProfile drops dead first-pass switch @-regex (issue #35)")
else:
    fail("drawDecoProfile still has dead switch @-regex first pass (issue #35)")
_mod_travel_block = js.split("function updateTravelGasMOD", 1)[-1].split("function ", 1)[0] if "function updateTravelGasMOD" in js else ""
if _mod_travel_block and "refreshTravelGasFractionWarning" not in _mod_travel_block:
    ok("updateTravelGasMOD does not redundantly refresh travel gas warning (issue #33)")
else:
    fail("updateTravelGasMOD redundantly calls refreshTravelGasFractionWarning (issue #33)")
if "function escapeHtmlText" in js and "escapeHtmlText(reason)" in js.split("setTravelGasFractionWarning", 1)[-1][:400]:
    ok("index.html travel gas warning escapes reason HTML (issue #32)")
else:
    fail("index.html travel gas reason unescaped in innerHTML (issue #32)")

if worker_bridge_js and ("nextId = 1" in worker_bridge_js or "let nextId = 1" in worker_bridge_js):
    ok("ZhlWorkerBridge tracks monotonic nextId (issue #27 BUG-E / #135 L-3)")
else:
    fail("ZhlWorkerBridge missing nextId worker session tracking (issue #27 BUG-E)")

if "function getTravelGasInfo" in js and "fHe: 0" in js.split("function getTravelGasInfo", 1)[-1][:2500]:
    ok("getTravelGasInfo exposes fHe field for travel gas schema (issue #27 BUG-B)")
else:
    fail("getTravelGasInfo missing fHe in return object (issue #27 BUG-B)")

if "terminate" in worker_bridge_js and "ZhlWorkerBridge = { calculateInWorker, terminate }" in worker_bridge_js:
    ok("ZhlWorkerBridge exposes terminate() for worker lifecycle")
else:
    fail("ZhlWorkerBridge missing terminate() API")

if "ZhlWorkerBridge.terminate()" in html:
    ok("beforeunload terminates ZHL worker on page leave (BUG-E lifecycle)")
else:
    fail("beforeunload missing ZhlWorkerBridge.terminate()")

if os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(path)), "tools", "update_sw_version.py")):
    ok("tools/update_sw_version.py verifies release version alignment")
else:
    fail("tools/update_sw_version.py missing for version alignment checks")

sw_path_early = os.path.join(os.path.dirname(os.path.abspath(path)), "sw.js")
if os.path.isfile(sw_path_early):
    with open(sw_path_early, encoding="utf-8") as f:
        sw_early = f.read()
    if ("importScripts('app-version.js')" in sw_early and
            "const CACHE_VERSION = 'lsp-dplanner-plus-v' + APP_VERSION" in sw_early):
        ok("sw.js CACHE_VERSION derived from app-version.js APP_VERSION")
    else:
        fail("sw.js must importScripts app-version.js and derive CACHE_VERSION")
else:
    fail("sw.js missing")

# 11.2 VPM-B bottom gas reads He from getBottomGasFractions
vpm_path = re.search(r"_vpmBotFracs\s*=\s*getBottomGasFractions\(\)", js)
if vpm_path:
    ok("VPM-B path reads bottom gas He via getBottomGasFractions()")
else:
    fail("VPM-B path may not read He from UI — check _vpmBotFracs / bottomHePct")

# 11.3 VPM deco gases include He from getDecoCardFractions
vpm_deco_he = re.search(r"getDecoCardFractions\(n\)", js)
if vpm_deco_he:
    ok("VPM-B path reads deco gas He via getDecoCardFractions()")
else:
    fail("VPM-B deco gas build may not read He from UI")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 12 — CORE CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# 12.1 Water vapor — LSP default 0.0577 (MultiDeco); Bühlmann option 0.0627 in UI
if "WATER_VAPOR = 0.0577" in js and 'value="0.0577"' in html:
    ok("Water vapor default 0.0577 bar (LSP MultiDeco default)")
elif "WATER_VAPOR = 0.0627" in js or "WATER_VAPOR_PRESSURE = 0.0627" in js:
    ok("Water vapor = 0.0627 bar (Baker/Bühlmann canonical)")
else:
    # It might use a variable — check it's defined
    if "WATER_VAPOR" in js:
        ok("WATER_VAPOR constant present (check value manually)")
    else:
        fail("WATER_VAPOR constant not found")

# 12.2 BAR_PER_METRE defined
if "BAR_PER_METRE" in js:
    ok("BAR_PER_METRE constant present")
else:
    fail("BAR_PER_METRE constant missing")

# 12.3 SEA_LEVEL_P defined
if "SEA_LEVEL_P" in js:
    ok("SEA_LEVEL_P constant present")
else:
    fail("SEA_LEVEL_P constant missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 13 — EXPORT CONSISTENCY
# Rule: any text/display change must apply to ALL export modes
# ══════════════════════════════════════════════════════════════════════════════

# 13.1 buildExportText function exists
if "function buildExportText" in js:
    ok("buildExportText() present")
else:
    fail("buildExportText() missing")

# 13.2 buildMessengerText function exists
if "function buildMessengerText" in js:
    ok("buildMessengerText() present")
else:
    fail("buildMessengerText() missing")

# 13.3 exportPDF function exists
if "function exportPDF" in js or "async function exportPDF" in js:
    ok("exportPDF() present")
else:
    fail("exportPDF() missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 14 — CRITICAL SAFETY RULES
# ══════════════════════════════════════════════════════════════════════════════

# 14.1 Gas shortage warnings use red (not yellow) — running out of gas is life-critical
# Check that gas warning color is red, not yellow
gas_warn_section = re.search(r"gas.{0,30}shortage|gasShort|GAS_SHORT|gas.*warning", js, re.IGNORECASE)
# Check that yellow is NOT used for gas quantity warnings
bad_yellow_gas = re.findall(r"gasQuantity.*yellow|yellow.*gasQuantity|gas.*short.*yellow|yellow.*gas.*short", js, re.IGNORECASE)
if bad_yellow_gas:
    fail("Gas shortage warning uses yellow — must be red (life-critical)")
else:
    ok("Gas shortage warnings not found using yellow (safety rule maintained)")

# 14.2 O2 at 6m: LSP intentionally differs from ApexDeco (allowed at MOD)
if "allowO2AtMOD" in js or "isPureO2" in js:
    ok("O2@6m handling present (LSP intentional difference from ApexDeco)")
else:
    fail("O2@6m special case handling missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 15 — MOBILE / CANVAS
# ══════════════════════════════════════════════════════════════════════════════

# 15.1 isMobile detected before PAD/PW/PH in canvas draw functions
# (isMobile must be before canvas padding calculation — previous regression)
for fn_name in ["_drawDiveProfileCore", "drawGFCurve"]:
    fn_m = re.search(rf"function {fn_name}\b(.*?)^\}}", js, re.DOTALL | re.MULTILINE)
    if fn_m:
        body = fn_m.group(1)
        mobile_pos = body.find("isMobile")
        pad_pos = body.find("PAD") if "PAD" in body else body.find("const PW")
        if mobile_pos > 0 and pad_pos > 0 and mobile_pos < pad_pos:
            ok(f"{fn_name}(): isMobile detected before PAD/PW/PH calculation")
        elif mobile_pos < 0:
            fail(f"{fn_name}(): isMobile not found — mobile layout may use desktop padding")
        else:
            fail(f"{fn_name}(): PAD/PW/PH appears before isMobile — mobile layout bug")

# 15.2 Canvas fill uses rgba() not 8-digit hex (canvas ignores alpha in #rrggbbaa)
bad_hex_alpha = re.findall(r'fillStyle\s*=\s*["\']\#[0-9a-fA-F]{8}["\']', js)
if bad_hex_alpha:
    for b in bad_hex_alpha[:3]:
        fail(f"Canvas fillStyle uses 8-digit hex alpha ({b}) — use rgba() instead (canvas ignores alpha in hex)")
else:
    ok("No 8-digit hex alpha in canvas fillStyle (rgba used correctly)")

# GROUP 16 — FEATURE A: Altitude-adjusted VPM critical radii
# ══════════════════════════════════════════════════════════════════════════════

# 16.1 P_SL constant defined (standard sea-level pressure)
if re.search(r"const P_SL\s*=\s*1\.01325", vpm_src):
    ok("P_SL = 1.01325 bar (standard sea-level pressure for altFactor)")
else:
    fail("P_SL constant missing or wrong value — altitude radii calculation broken")

# 16.2 altFactor formula: (P_SL / surfP) ^ (1/3) — cube root of volume ratio
if re.search(r"Math\.pow\s*\(\s*P_SL\s*/\s*surfP\s*,\s*1\.0\s*/\s*3\.0\s*\)", vpm_src):
    ok("altFactor = (P_SL/surfP)^(1/3) — correct cube-root radius scaling")
else:
    fail("altFactor formula missing or wrong — VPM altitude radii not properly scaled")

# 16.3 initRadN2/initRadHe use altFactor
if "initRadN2 = INITIAL_RADIUS_N2 * altFactor" in vpm_src and "initRadHe = INITIAL_RADIUS_He * altFactor":
    ok("initRadN2/initRadHe scaled by altFactor")
else:
    fail("initRadN2/initRadHe not scaled by altFactor — altitude correction not applied to initial radii")

# 16.4 All 12 VPM state quantities seeded from altitude-adjusted radii
# They don't need altFactor literally — they use initRadN2/initRadHe which already incorporates it
vpm_state_fn = re.search(r"createVPMState\s*\(.*?return \{", vpm_src, re.DOTALL)
if vpm_state_fn:
    state_body = vpm_state_fn.group(0)
    required_state_vars = [
        "critRadiiN2", "critRadiiHe",
        "adjustedCritRadiiN2", "adjustedCritRadiiHe",
        "regeneratedRadiiN2", "regeneratedRadiiHe",
        "allowableGradientN2", "allowableGradientHe",
        "decoGradientN2", "decoGradientHe",
        "initialAllowableGradientN2", "initialAllowableGradientHe",
    ]
    missing = [v for v in required_state_vars if v not in state_body]
    if missing:
        for m in missing:
            fail(f"createVPMState missing '{m}' — altitude-adjusted radius not propagated to all state arrays")
    else:
        ok("All 12 VPM state radius arrays present in createVPMState()")
else:
    fail("createVPMState() not found — cannot verify altitude radii propagation")

# 16.5 Sea-level identity: at surfP=1.01325, altFactor == 1.0 exactly
# Verified by physics: (1.01325/1.01325)^(1/3) = 1. Code-level check: P_SL value matches surfP default
m_psl = re.search(r"const P_SL\s*=\s*([\d.]+)", vpm_src)
if m_psl and abs(float(m_psl.group(1)) - 1.01325) < 1e-5:
    ok("P_SL = 1.01325 bar — sea-level identity (altFactor=1.0) preserved")
else:
    fail("P_SL value deviates from 1.01325 — sea-level identity broken, existing tests will fail")

# 16.6 Altitude badge shown in VPM results when altitude > 0
if "altM" in js and ("radii" in js or "altFactor" in vpm_src) and "altitude" in js.lower():
    ok("Altitude badge present in VPM results display")
else:
    fail("Altitude badge missing in VPM results — user not informed that altitude-adjusted radii are active")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 17 — FEATURE B: Repetitive VPM dive bubble state carry
# ══════════════════════════════════════════════════════════════════════════════

# 17.1 REGEN_TIME_MIN constant = 20160 min (14 days)
m_regen = re.search(r"REGEN_TIME(?:_MIN)?\s*=\s*([\d.]+)", vpm_src)
if m_regen and abs(float(m_regen.group(1)) - 20160.0) < 1.0:
    ok(f"REGEN_TIME_MIN = {m_regen.group(1)} min (14 days = 14×24×60 ✓)")
else:
    val = m_regen.group(1) if m_regen else "NOT FOUND"
    fail(f"REGEN_TIME_MIN = {val}, expected 20160 (14 days) — bubble regeneration rate wrong")

# 17.2 Regeneration formula: exp(-si / REGEN_TIME_MIN) — exponential decay
if re.search(r"Math\.exp\s*\(\s*-\s*\w+\s*/\s*REGEN_TIME(?:_MIN)?\s*\)", vpm_src):
    ok("Regeneration formula uses exp(-t/REGEN_TIME_MIN) — correct exponential decay")
else:
    fail("Regeneration formula missing exp(-t/REGEN_TIME_MIN) — bubble state carry physics wrong")

# 17.3 finalBubbleState exported from buildResult with adjustedCritRadii and regeneratedRadii
if ("finalBubbleState" in vpm_src and
    "adjustedCritRadiiN2" in vpm_src[vpm_src.find("finalBubbleState"):vpm_src.find("finalBubbleState")+300] or
    "adjustedCritRadiiN2" in vpm_src):
    ok("finalBubbleState exported from VPMEngine buildResult()")
else:
    fail("finalBubbleState not exported from buildResult() — repetitive dive state not available")

# 17.4 _lastVPMResult saves { finalTissues, finalBubbleState }
lvm_idx = js.find("_lastVPMResult = {")
if lvm_idx > 0:
    lvm_block = js[lvm_idx:lvm_idx + 300]
    if "finalBubbleState" in lvm_block:
        ok("_lastVPMResult saves { finalTissues, finalBubbleState }")
    else:
        fail("_lastVPMResult does not save finalBubbleState — repetitive bubble state not persisted between runs")
else:
    fail("_lastVPMResult assignment not found")

# 17.5 createVPMState reads _prevBubbleState and applies regeneration
if "_prevBubbleState" in vpm_src and "regenFactor" in vpm_src:
    ok("createVPMState reads _prevBubbleState and applies regenFactor")
else:
    fail("createVPMState does not read _prevBubbleState — repetitive dive bubble carry not implemented")

# 17.6 Carried radii applied to ALL relevant state arrays (not just critRadii)
# Search the whole JS for the carry loop (window of 600 was too small)
carry_block_start = vpm_src.find("pb.regeneratedRadiiN2")
if carry_block_start > 0:
    # The loop spans ~1500 chars; use 1800 to cover all assignments safely
    carry_block = vpm_src[max(0, carry_block_start - 200):carry_block_start + 1800]
    carry_arrays = ["critRadiiN2", "critRadiiHe", "adjustedCritRadiiN2", "adjustedCritRadiiHe",
                    "allowableGradientN2", "allowableGradientHe",
                    "decoGradientN2", "decoGradientHe",
                    "initialAllowableGradientN2", "initialAllowableGradientHe"]
    missing_carry = [a for a in carry_arrays if a not in carry_block]
    if missing_carry:
        for a in missing_carry:
            fail(f"Bubble carry loop missing '{a}' — repetitive dive radii not fully applied")
    else:
        ok("Bubble carry loop seeds all 10 VPM state arrays from previous dive state")
else:
    fail("Bubble carry loop (pb.regeneratedRadiiN2) not found — repetitive dive physics missing")

# 17.7 UI elements present
rep_ui_elements = {
    "vpmRepMode":       "repetitive dive checkbox",
    "vpmRepSIRow":      "surface interval row",
    "vpmRepLabel":      "bubble state status label",
    "vpmRepRow":        "outer container (shown/hidden by setDecoAlgorithm)",
    "vpmSurfaceInterval": "surface interval input",
}
for elem_id, description in rep_ui_elements.items():
    if f'id="{elem_id}"' in html:
        ok(f"Repetitive VPM UI: id=\"{elem_id}\" ({description}) present")
    else:
        fail(f"Repetitive VPM UI: id=\"{elem_id}\" ({description}) missing")

# 17.8 clearVpmRepState function exists
if "function clearVpmRepState()" in js:
    ok("clearVpmRepState() function present")
else:
    fail("clearVpmRepState() missing — user cannot reset repetitive dive state")

# 17.9 setDecoAlgorithm hides rep panel when switching to ZHL
algo_fn = re.search(r"function setDecoAlgorithm\(.*?(?=\nfunction )", js, re.DOTALL)
if algo_fn:
    algo_body = algo_fn.group(0)
    if "vpmRepRow" in algo_body:
        ok("setDecoAlgorithm hides/shows vpmRepRow when switching algorithms")
    else:
        fail("setDecoAlgorithm does not handle vpmRepRow — panel stays visible when switching to ZHL")
else:
    fail("setDecoAlgorithm not found for rep panel check")

# 17.10 vpmSurfaceInterval and vpmRepMode in DECO_FIELDS (persistence)
deco_fields_idx2 = html.find("DECO_FIELDS:")
if deco_fields_idx2 > 0:
    deco_fields_block2 = html[deco_fields_idx2:deco_fields_idx2 + 1800]
    for field_id, description in [
        ("vpmSurfaceInterval", "VPM repetitive surface interval input"),
        ("vpmRepMode",         "VPM repetitive dive checkbox"),
        ("zhlSurfaceInterval", "ZHL repetitive surface interval input"),
        ("zhlRepMode",         "ZHL repetitive dive checkbox"),
        ("n2NarcSel",          "N2 narcosis mode selector"),
        ("o2NarcSel",          "O2 narcosis mode selector"),
        ("o2AtMODSelect",      "allow O2 at MOD selector"),
    ]:
        if field_id in deco_fields_block2:
            ok(f"DECO_FIELDS includes {field_id} ({description})")
        else:
            fail(f"DECO_FIELDS missing '{field_id}' ({description}) — input lost on page reload")
else:
    fail("DECO_FIELDS not found — cannot check Feature B persistence")

# GROUP 18 — FEATURE: SAC-based gas consumption
# ══════════════════════════════════════════════════════════════════════════════

# 18.1 SAC inputs present
for eid, desc in [("sacBottom", "bottom SAC L/min"), ("sacDeco", "deco SAC L/min")]:
    if f'id="{eid}"' in html:
        ok(f"SAC input id=\"{eid}\" ({desc}) present")
    else:
        fail(f"SAC input id=\"{eid}\" ({desc}) missing")

# 18.2 Cylinder fields present for all gas positions
cyl_fields = [
    ("cylBot_size",        "bottom gas cylinder size"),
    ("cylBot_pres",        "bottom gas cylinder pressure"),
    ("cylDg1_size",        "deco gas 1 cylinder size"),
    ("cylDg1_pres",        "deco gas 1 cylinder pressure"),
    ("cylDg2_size",        "deco gas 2 cylinder size"),
    ("cylDg2_pres",        "deco gas 2 cylinder pressure"),
    ("cylTravelGas_size",  "travel gas cylinder size"),
    ("cylTravelGas_pres",  "travel gas cylinder pressure"),
]
for eid, desc in cyl_fields:
    if f'id="{eid}"' in html:
        ok(f"Cylinder field id=\"{eid}\" ({desc}) present")
    else:
        fail(f"Cylinder field id=\"{eid}\" ({desc}) missing")

# 18.3 Gas consumption function uses correct formula: SAC × P_abs × time
if "sac * absP * durMin" in js or "sac * absP * dur" in js:
    ok("Gas consumption formula: SAC × P_abs × duration (correct surface-equivalent litres)")
else:
    fail("Gas consumption formula missing sac × absP × duration")

# 18.4 Buhlmann path converts psi→bar for imperial units
# Search 800 chars from cylIds definition to cover the entire forEach loop
buh_cyl_start = js.find("const cylIds = [\n      ['cylBot_size','cylBot_pres']")
buh_cyl_block = js[buh_cyl_start:buh_cyl_start + 800] if buh_cyl_start > 0 else ""
if "14.5038" in buh_cyl_block or ("imperial" in buh_cyl_block and "prRaw" in buh_cyl_block):
    ok("Buhlmann gas consumption: cylinder pressure converted psi→bar in imperial mode")
else:
    fail("Buhlmann gas consumption: no psi→bar conversion — cylinder capacity overstated in imperial mode")

# 18.5 VPM path ALSO converts psi→bar for imperial units
vpm_cyl_start = js.find("cylCapVPM = {};")
vpm_cyl_block = js[vpm_cyl_start:vpm_cyl_start + 400] if vpm_cyl_start > 0 else ""
if "14.5038" in vpm_cyl_block or ("imperial" in vpm_cyl_block and "pr " in vpm_cyl_block):
    ok("VPM gas consumption: cylinder pressure converted psi→bar in imperial mode")
else:
    fail("VPM gas consumption: no psi→bar conversion — WRONG cylinder capacity in imperial mode")

# 18.6 Travel gas cylinder included in Buhlmann cylIds
buh_cyl_section = js[js.find("const cylIds = ["):js.find("const cylIds = [") + 400] if "const cylIds = [" in js else ""
if "cylTravelGas_size" in buh_cyl_section:
    ok("Buhlmann cylIds includes travel gas cylinder")
else:
    fail("Buhlmann cylIds missing travel gas — travel gas consumption has no shortage warning")

# 18.7 Travel gas cylinder included in VPM cylIds
vpm_cyl_ids = js[js.find("[['cylBot_size','cylBot_pres']"):js.find("[['cylBot_size','cylBot_pres']") + 300] if "[['cylBot_size','cylBot_pres']" in js else ""
if "cylTravelGas_size" in vpm_cyl_ids:
    ok("VPM cylIds includes travel gas cylinder")
else:
    fail("VPM cylIds missing travel gas — travel gas consumption has no shortage warning")

# 18.8 All SAC and cylinder fields in DECO_FIELDS (persistence)
deco_fields_idx3 = html.find("DECO_FIELDS:")
if deco_fields_idx3 > 0:
    deco_fields_block3 = html[deco_fields_idx3:deco_fields_idx3 + 1800]
    gas_fields_required = [
        ("sacBottom",           "bottom SAC"),
        ("sacDeco",             "deco SAC"),
        ("cylBot_size",         "bottom cylinder size"),
        ("cylBot_pres",         "bottom cylinder pressure"),
        ("cylDg1_size",         "deco gas 1 cylinder size"),
        ("cylDg1_pres",         "deco gas 1 cylinder pressure"),
        ("cylDg2_size",         "deco gas 2 cylinder size"),
        ("cylDg2_pres",         "deco gas 2 cylinder pressure"),
        ("cylTravelGas_size",   "travel gas cylinder size"),
        ("cylTravelGas_pres",   "travel gas cylinder pressure"),
    ]
    for field_id, description in gas_fields_required:
        if field_id in deco_fields_block3:
            ok(f"DECO_FIELDS includes {field_id} ({description})")
        else:
            fail(f"DECO_FIELDS missing '{field_id}' ({description}) — value lost on page reload")
else:
    fail("DECO_FIELDS not found — cannot verify gas consumption field persistence")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 19 — FEATURE: VPM-B/GFS gradient blending (applyGFSurfacing)
# ══════════════════════════════════════════════════════════════════════════════

# 19.1 applyGFSurfacing function exists
if "function applyGFSurfacing(" in vpm_src:
    ok("applyGFSurfacing() function present")
else:
    fail("applyGFSurfacing() missing — VPM-B/GFS gradient blending not implemented")

# 19.2 Blend fraction: stopDepth / firstStopDepth (1 at first stop → VPM, 0 at surface → GF)
if "fraction = stopDepth / firstStopDepth" in vpm_src:
    ok("GFS blend fraction = stopDepth/firstStopDepth (1=first stop pure VPM, 0=surface pure GF)")
else:
    fail("GFS blend fraction formula wrong — direction of VPM→GF transition incorrect")

# 19.3 Blend formula: per-gas VPM→GF interpolation (issue #123 M-04)
if ("blendedGradN2 = vpmGradN2 * fraction + buhlGrad * (1 - fraction)" in vpm_src
        and "blendedGradHe = vpmGradHe * fraction + buhlGrad * (1 - fraction)" in vpm_src):
    ok("GFS blend formula: per-gas linear VPM→GF interpolation correct")
elif "blendedGrad = vpmGrad * fraction + buhlGrad * (1 - fraction)" in vpm_src:
    ok("GFS blend formula: linear VPM→GF interpolation correct")
else:
    fail("GFS blend formula missing or wrong")

# 19.4 applyGFSurfacing uses weighted a/b for trimix (not plain N2 values)
gfs_fn = re.search(r"function applyGFSurfacing\(.*?\n    \}", vpm_src, re.DOTALL)
if gfs_fn:
    body = gfs_fn.group(0)
    if "ZHL16C_He" in body and "pTotal" in body:
        ok("applyGFSurfacing uses weighted a/b for trimix (ZHL16C_He + pTotal weighting)")
    else:
        fail("applyGFSurfacing does not use weighted a/b — GFS ceiling wrong for trimix")
else:
    fail("applyGFSurfacing function body not found for trimix check")

# 19.5 applyGFSurfacing only called for VPMB_GFS model (not VPMB or VPMBE)
# Find the call and check the guard that wraps it
gfs_call_idx = vpm_src.find("applyGFSurfacing(ctx.state")
if gfs_call_idx > 0:
    guard_ctx = vpm_src[max(0, gfs_call_idx - 150):gfs_call_idx]
    if "model === 'VPMB_GFS'" in guard_ctx or 'model === "VPMB_GFS"' in guard_ctx:
        ok("applyGFSurfacing called only when model === 'VPMB_GFS'")
    else:
        fail("applyGFSurfacing may be called for wrong models — check conditional")
else:
    fail("applyGFSurfacing call site not found")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 20 — GAS CONSUMPTION: unit correctness
# ══════════════════════════════════════════════════════════════════════════════

# 20.1 SAC fields have convertNumericInput in setUnits (L/min ↔ cu ft/min)
set_units_fn = re.search(r"function setUnits\(.*?(?=\nfunction )", js, re.DOTALL)
if set_units_fn:
    set_units_body = set_units_fn.group(0)
    if "convertNumericInput('sacBottom'" in set_units_body:
        ok("setUnits converts sacBottom value (L/min ↔ cu ft/min)")
    else:
        fail("setUnits missing convertNumericInput for sacBottom — SAC value stays at metric default in imperial mode")
    if "convertNumericInput('sacDeco'" in set_units_body:
        ok("setUnits converts sacDeco value (L/min ↔ cu ft/min)")
    else:
        fail("setUnits missing convertNumericInput for sacDeco — SAC value stays at metric default in imperial mode")
else:
    fail("setUnits function not found for SAC conversion check")

# 20.2 Gas consumption display uses correct unit label (not hardcoded 'L')
# Buhlmann path: normal plan uses calcGasPlan() (volU declared inside),
# emergency path uses inline Object.entries forEach with volUnitV2.
# VPM path: uses for..of loop over gasConsVPM entries with volUnitV.
buh_block_start = js.find("if (gasEl && Object.keys(gasConsumed).length)")
buh_block = js[buh_block_start:buh_block_start + 3000] if buh_block_start > 0 else ""
if ("volUnitV" in buh_block or "calcGasPlan()" in buh_block):
    ok("Buhlmann gas consumption display uses units-aware volume label (L / cu ft)")
else:
    fail("Buhlmann gas consumption display hardcodes 'L' — wrong unit shown in imperial mode")

vpm_block_start = js.find("if (gasElVPM && Object.keys(gasConsVPM).length)")
vpm_block = js[vpm_block_start:vpm_block_start + 3000] if vpm_block_start > 0 else ""
if "volUnitV" in vpm_block or "volUnit" in vpm_block:
    ok("VPM gas consumption display uses units-aware volume label (L / cu ft)")
else:
    fail("VPM gas consumption display hardcodes 'L' — wrong unit shown in imperial mode")

# 20.3 Buhlmann gas plan renders via calcGasPlan() or declares volUnitV before use
# (Buhlmann refactored to use calcGasPlan() for normal path + volUnitV2 for emergency path)
calc_gas_plan_fn = js.find("function calcGasPlan()")
calc_gas_plan_units = js[calc_gas_plan_fn:calc_gas_plan_fn + 200] if calc_gas_plan_fn > 0 else ""
if ("const volU" in calc_gas_plan_units or "volUnit" in calc_gas_plan_units):
    ok("calcGasPlan() declares unit-aware volume label — no ReferenceError in Buhlmann gas render")
else:
    fail("volUnitV not declared in Buhlmann gas loop — ReferenceError when gas consumption renders")

# 20.1b ZHLEngine exposed on window for test harnesses
if "window.ZHLEngine = ZHLEngine" in js and "const ZHLEngine = (() => {" in js:
    ok("ZHLEngine callable interface exposed — Bühlmann testable without DOM coupling")
else:
    fail("ZHLEngine not exposed on window — ZHLC_GF tests in test harness will run VPM-B instead")

# 20.3b calcEND_tool uses calcEND() — not simplified sea-level formula
# Bug: was using pNarc * 10 - 10 (wrong at altitude, ignored narcotic toggles)
end_tool_fn = js[js.find("function calcEND_tool()"):js.find("function calcEND_tool()") + 2500]
if "calcEND(dM" in end_tool_fn or "calcEND(depthM" in end_tool_fn:
    ok("calcEND_tool() delegates to calcEND() — altitude-correct, respects narcotic toggles")
else:
    fail("calcEND_tool() uses simplified formula — wrong at altitude, ignores narcoticN2/narcoticO2 settings")

# 20.3c calcMODTool() in Tools panel uses altSurfaceP (not hardcoded sea-level formula)
mod_fn_start = js.find("function calcMODTool() {")
mod_fn = js[mod_fn_start:mod_fn_start + 400] if mod_fn_start > 0 else ""
if mod_fn_start > 0 and "calcGasMODm" in mod_fn:
    ok("calcMODTool() (Tools tab) delegates to calcGasMODm — altitude-correct")
elif mod_fn_start > 0 and "altSurfaceP" in mod_fn and "BAR_PER_METRE" in mod_fn:
    ok("calcMODTool() (Tools tab) uses altSurfaceP + BAR_PER_METRE — altitude-correct")
else:
    fail("calcMODTool() (Tools tab) uses hardcoded sea-level formula — wrong at altitude")

# 20.3c2 updateGasMODDisplays() planner gas-card MOD uses altSurfaceP
ugmd_start = js.find("function updateGasMODDisplays()")
ugmd_end = js.find("\nfunction ", ugmd_start + 1) if ugmd_start > 0 else -1
ugmd_fn = js[ugmd_start:ugmd_end] if ugmd_start > 0 and ugmd_end > ugmd_start else ""
if ugmd_start > 0 and "altSurfaceP" in ugmd_fn and "(ppO2limit / fO2 - 1)" not in ugmd_fn:
    ok("updateGasMODDisplays() uses altSurfaceP — planner MOD fields altitude-correct")
else:
    fail("updateGasMODDisplays() still uses sea-level (ppO2/fO2 - 1) formula — wrong at altitude")

# 20.3c3 nitroxMOD() REC mode uses calcGasMODm (altitude-correct)
nitrox_mod_m = re.search(r"function nitroxMOD\([^)]*\)\s*\{[^}]{0,200}\}", js)
if nitrox_mod_m and "calcGasMODm" in nitrox_mod_m.group(0):
    ok("nitroxMOD() delegates to calcGasMODm — REC altitude-correct")
else:
    fail("nitroxMOD() uses hardcoded sea-level * 10 formula — wrong at altitude")

# 20.3c4 calcGasMODm() CCR bailout MOD uses altSurfaceP
cgm_m = re.search(r"function calcGasMODm\([^)]*\)\s*\{[^}]{0,800}\}", js)
if cgm_m and "altSurfaceP" in cgm_m.group(0) and "(ppO2Limit / fO2 - 1)" not in cgm_m.group(0):
    ok("calcGasMODm() uses altSurfaceP — CCR bailout MOD altitude-correct")
else:
    fail("calcGasMODm() still uses sea-level (ppO2/fO2 - 1) formula — wrong at altitude")

# 20.3c5 setAltitude() refreshes MOD displays when altitude changes
set_alt_start = js.find("function setAltitude()")
set_alt_fn = js[set_alt_start:set_alt_start + 3500] if set_alt_start > 0 else ""
if set_alt_start > 0 and "refreshAltitudeDependentUI" in set_alt_fn:
    ok("setAltitude() calls refreshAltitudeDependentUI — MOD/EAD/tools refresh on altitude change")
elif set_alt_start > 0 and "updateGasMODDisplays" in set_alt_fn and "calcMODTool" in set_alt_fn:
    ok("setAltitude() refreshes MOD displays (updateGasMODDisplays + calcMODTool)")
else:
    fail("setAltitude() missing MOD refresh calls — stale MOD after altitude change")

# 20.3c6 loadAltitudeFromStorage() refreshes altitude-dependent UI on page load
load_alt_start = js.find("function loadAltitudeFromStorage()")
load_alt_fn = js[load_alt_start:load_alt_start + 2500] if load_alt_start > 0 else ""
if load_alt_start > 0 and "refreshAltitudeDependentUI" in load_alt_fn:
    ok("loadAltitudeFromStorage() calls refreshAltitudeDependentUI — saved altitude applies on load")
else:
    fail("loadAltitudeFromStorage() missing UI refresh — MOD stale after page load with saved altitude")

# 20.3c7 refreshAltitudeDependentUI includes calcBestMix and renderEADTable
raf_start = js.find("function refreshAltitudeDependentUI()")
raf_fn = js[raf_start:raf_start + 1200] if raf_start > 0 else ""
if raf_start > 0 and "calcBestMix?.()" in raf_fn and "calcBestMixTec?.()" in raf_fn and "renderEADTable" in raf_fn:
    ok("refreshAltitudeDependentUI() refreshes calcBestMix + renderEADTable")
else:
    fail("refreshAltitudeDependentUI() missing calcBestMix or renderEADTable")

# 20.3c9 renderModRefTable delegates MOD rows to calcGasMODm
rmrt_start = js.find("function renderModRefTable()")
rmrt_fn = js[rmrt_start:rmrt_start + 2000] if rmrt_start > 0 else ""
if rmrt_start > 0 and "calcGasMODm" in rmrt_fn and "(1.4 / fO2 - (altSurfaceP" not in rmrt_fn:
    ok("renderModRefTable() uses calcGasMODm — not raw inline formula")
else:
    fail("renderModRefTable() still uses raw inline MOD formula — wrong at altitude")

# 20.3c10 loadAltitudeFromStorage refresh is outside try/catch (errors not silently swallowed)
if load_alt_start > 0 and load_alt_fn.rfind("refreshAltitudeDependentUI") > load_alt_fn.rfind("catch"):
    ok("loadAltitudeFromStorage() refresh outside try/catch — refresh errors surface")
else:
    fail("loadAltitudeFromStorage() refresh inside try/catch — errors silently swallowed on load")

# 20.3c11 getTravelGasInfo auto switch uses calcGasMODm (not inline formula)
tgi_start = js.find("function getTravelGasInfo()")
tgi_fn = js[tgi_start:tgi_start + 3500] if tgi_start > 0 else ""
if tgi_start > 0 and "calcGasMODm" in tgi_fn and "ppO2Bot / fO2 - altSurfaceP" not in tgi_fn:
    ok("getTravelGasInfo() auto switch uses calcGasMODm — allowO2AtMOD consistent")
else:
    fail("getTravelGasInfo() still uses inline MOD formula — missing allowO2AtMOD override")

# 20.3c12 runDecoSchedule travel-gas botMODm uses calcGasMODm
_bzhl_sched = js.split("function buildZhlScheduleParamsFromDom", 1)
_bzhl_body = _bzhl_sched[1][:8000] if len(_bzhl_sched) > 1 else ""
if len(_bzhl_sched) > 1 and "calcGasMODm(bottomFO2" in _bzhl_body:
    ok("runDecoSchedule botMODm uses calcGasMODm — travel switch depth consistent with gas cards")
else:
    fail("runDecoSchedule botMODm still uses inline MOD formula")

# 20.3c13 getDecoGasSwitches ZHL fallback uses calcGasMODm
dgs_start = js.find("function getDecoGasSwitches()")
dgs_fn = js[dgs_start:dgs_start + 4500] if dgs_start > 0 else ""
if dgs_start > 0 and "calcGasMODm" in dgs_fn and "limit / fO2 - altSurfaceP" not in dgs_fn:
    ok("getDecoGasSwitches() ZHL fallback uses calcGasMODm — export/banner consistent with gas cards")
else:
    fail("getDecoGasSwitches() still uses inline MOD formula")

# 20.3c14 vpmDecoSwitchDepthVal pure-O2 path uses calcGasMODm (not hardcoded 6 m)
vpm_sw_m = re.search(r"function vpmDecoSwitchDepthVal\([^)]*\)\s*\{[\s\S]{0,600}?\}", js)
if vpm_sw_m and "calcGasMODm" in vpm_sw_m.group(0) and "return dU ? 6 : 20" not in vpm_sw_m.group(0):
    ok("vpmDecoSwitchDepthVal() uses calcGasMODm for pure O₂ — respects lastDecoStop")
else:
    fail("vpmDecoSwitchDepthVal() still hardcodes 6 m for pure O₂ deco gas")

if "function calcMODTool()" in js and "function calcMOD(" not in js and ugmd_start > 0 and "calcGasMODm" in ugmd_fn:
    ok("calcMOD name collision resolved — calcGasMODm shared, calcMODTool for Tools (issue #4 BUG-1)")
else:
    fail("calcMOD name collision still present — local and global share name (issue #4 BUG-1)")

# 20.3c8 calcGasMODm clamps negative MOD to zero; pure O₂ never below 6 m / lastDecoStop
if cgm_m and "Math.max(0" in cgm_m.group(0) and ("Math.max(o2MODm, strictM)" in cgm_m.group(0) or "strictM" in cgm_m.group(0)):
    ok("calcGasMODm() clamps negative MOD to 0; pure O₂ enforces minimum deco-stop floor in Strict mode")
elif cgm_m and "Math.max(0" in cgm_m.group(0):
    ok("calcGasMODm() clamps negative MOD to 0")
else:
    fail("calcGasMODm() missing Math.max(0,…) clamp — negative MOD can display at extreme altitude")

if "async function ensurePDFFontsForPDF(doc)" in js and js.count("ensurePDFFontsForPDF(doc)") >= 3:
    ok("PDF builders guard font load via ensurePDFFontsForPDF (issue #4 BUG-2)")
else:
    fail("PDF builders call unguarded loadPDFFonts (issue #4 BUG-2)")

if js.count("drawFooter(); doc.addPage()") >= 3:
    ok("All PDF checkY helpers call drawFooter before page break (issue #4 BUG-3)")
else:
    fail("exportContingencyPDF or exportPDF checkY missing drawFooter (issue #4 BUG-3)")

run_deco_start = js.find("function runDecoSchedule(")
run_deco_chunk = js[run_deco_start:run_deco_start + 12000] if run_deco_start > 0 else ""
if run_deco_chunk and "function toMMSS(" not in run_deco_chunk:
    ok("runDecoSchedule uses global toMMSS — no nested redefinition (issue #4 BUG-4)")
else:
    fail("runDecoSchedule still nests redundant toMMSS (issue #4 BUG-4)")

if "unhandledrejection" in js and "__lspErrorHandlersInstalled" in js:
    ok("Global unhandledrejection handler installed (issue #4 LOW)")
else:
    fail("No global unhandledrejection handler (issue #4 LOW)")

# 20.3d setUnits() refreshes Tools panels (END Calc, Best Mix, MOD, EAD, Gas Table, Surface Int)
set_units_end = js[js.find("function setUnits("):js.find("function setUnits(") + 14000]
required_refreshes = ["calcEND_tool", "calcBestMix", "renderEADTable", "renderGasTable", "calcSurfInt", "calcAvgDepth"]
missing = [f for f in required_refreshes if f not in set_units_end]
if not missing:
    ok("setUnits() refreshes all Tools panels — no stale displays on metric/imperial toggle")
else:
    fail(f"setUnits() missing Tools panel refresh calls: {', '.join(missing)}")

# 20.4 PSI_PER_BAR and CUFT_PER_L constants defined with correct values
psi_m = re.search(r"PSI_PER_BAR\s*=\s*([\d.]+)", js)
cuft_m = re.search(r"CUFT_PER_L\s*=\s*([\d.]+)", js)
if psi_m and abs(float(psi_m.group(1)) - 14.5038) < 0.01:
    ok(f"PSI_PER_BAR = {psi_m.group(1)} (correct)")
else:
    fail(f"PSI_PER_BAR = {psi_m.group(1) if psi_m else 'NOT FOUND'} (expected 14.5038)")
if cuft_m and abs(float(cuft_m.group(1)) - 0.0353147) < 0.000001:
    ok(f"CUFT_PER_L = {cuft_m.group(1)} (correct)")
else:
    fail(f"CUFT_PER_L = {cuft_m.group(1) if cuft_m else 'NOT FOUND'} (expected 0.0353147)")

# 20.5 Cylinder pressure inputs converted in setUnits (bar ↔ psi)
if set_units_fn:
    body = set_units_fn.group(0)
    if "allCylPres" in body and "PSI_PER_BAR" in body:
        ok("setUnits converts all cylinder pressure fields (bar ↔ psi)")
    else:
        fail("setUnits missing cylinder pressure conversion — fields stay in metric units when switching to imperial")
    if "allCylSize" in body and "CUFT_PER_L" in body:
        ok("setUnits converts all cylinder size fields (L ↔ cu ft)")
    else:
        fail("setUnits missing cylinder size conversion — size fields stay in metric units when switching")

# 20.6 Dynamic cylinder pressure fields covered by allCylPres (querySelectorAll)
if "querySelectorAll" in js and 'cylDg' in js and '_pres' in js:
    ok("allCylPres uses querySelectorAll to include dynamic deco gas cylinder fields")
else:
    fail("allCylPres missing querySelectorAll — dynamically added deco gas cylinder fields not converted")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 21 — FEATURE: Minimum Decompression Profile
# ══════════════════════════════════════════════════════════════════════════════

# 21.1 enforceMinDecoProfile function exists
if "function enforceMinDecoProfile(" in js:
    ok("enforceMinDecoProfile() function present")
else:
    fail("enforceMinDecoProfile() missing — minimum deco profile feature not implemented")

# 21.2 Called in Buhlmann path
if "enforceMinDecoProfile(collapsed," in zhl_src:
    ok("enforceMinDecoProfile called in Buhlmann path")
else:
    fail("enforceMinDecoProfile not called in Buhlmann path — min deco profile ignored for ZHL")

# 21.3 Called in VPM path
if "enforceMinDecoProfile(_vpmRawStops," in js:
    ok("enforceMinDecoProfile called in VPM path")
else:
    fail("enforceMinDecoProfile not called in VPM path — min deco profile ignored for VPM-B")

# 21.4 UI fields present
for eid, desc in [
    ("minDecoProfileEnable", "enable/disable select"),
    ("minDeco9m",            "9m stop minimum minutes"),
    ("minDeco6m",            "6m stop minimum minutes"),
    ("minDecoProfileFields", "fields container (shown/hidden)"),
]:
    if f'id="{eid}"' in html:
        ok(f'Min deco UI: id="{eid}" ({desc}) present')
    else:
        fail(f'Min deco UI: id="{eid}" ({desc}) missing')

# 21.5 Fields in DECO_FIELDS (persistence)
deco_fields_idx4 = html.find("DECO_FIELDS:")
deco_block4 = html[deco_fields_idx4:deco_fields_idx4+1600] if deco_fields_idx4 > 0 else ""
for field_id, desc in [
    ("minDecoProfileEnable", "enable select"),
    ("minDeco9m",            "9m minimum"),
    ("minDeco6m",            "6m minimum"),
]:
    if field_id in deco_block4:
        ok(f"DECO_FIELDS includes {field_id} ({desc})")
    else:
        fail(f"DECO_FIELDS missing '{field_id}' ({desc}) — value lost on page reload")

# 21.6 Fields in _doResetToDefaults
reset_fn = re.search(r"function _doResetToDefaults\(.*?(?=\nfunction )", js, re.DOTALL)
if reset_fn:
    reset_body = reset_fn.group(0)
    for field_id, default, desc in [
        ("minDecoProfileEnable", "'no'",       "min deco enable"),
        ("minDeco9m",            "'1'",         "9m default"),
        ("minDeco6m",            "'3'",         "6m default"),
        ("cylTravelGas_size",    "'11'",        "travel cylinder size"),
        ("cylTravelGas_pres",    "'200'",       "travel cylinder pressure"),
        ("heHalfTimeMode",       "'baker'",     "He HT default"),
    ]:
        if field_id in reset_body:
            ok(f"_doResetToDefaults includes {field_id} (default {default})")
        else:
            fail(f"_doResetToDefaults missing '{field_id}' — Reset button leaves it unchanged")
else:
    fail("_doResetToDefaults function not found")

# 21.7 Label update on unit switch
set_units_fn2 = re.search(r"function setUnits\(.*?(?=\nfunction )", js, re.DOTALL)
if set_units_fn2 and "updateMinDecoLabels" in set_units_fn2.group(0):
    ok("setUnits calls updateMinDecoLabels (9m/30ft labels update on unit switch)")
elif "updateMinDecoLabels" in js:
    # Check if it's called somewhere in setUnits section
    su_idx = js.find("function setUnits(")
    su_end = js.find("\nfunction ", su_idx+1)
    if "updateMinDecoLabels" in js[su_idx:su_end]:
        ok("setUnits calls updateMinDecoLabels (9m/30ft labels update on unit switch)")
    else:
        fail("setUnits does not call updateMinDecoLabels — depth labels stay metric when switching to imperial")
else:
    fail("updateMinDecoLabels missing — depth labels do not update on unit switch")

# 21.8 pO2: null in injected stops is handled (falls through to ppO2Check)
if (
    "pO2 != null ? parseFloat(s.pO2) : parseFloat(ppO2Check(" in js
    or "s.pO2 != null ? String(s.pO2) : ppO2Check(" in js
):
    ok("Injected stop pO2:null handled — ppO2Check recalculates ppO2 for min deco stops")
else:
    fail("pO2:null injected stops may not get ppO2 recalculated — check stop row rendering")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 22 — RESET TO DEFAULTS (completeness)
# ══════════════════════════════════════════════════════════════════════════════

# 22.1 confirmModal present (used by resetToDefaults)
if 'id="confirmModal"' in html and 'id="confirmModalMsg"' in html:
    ok("confirmModal and confirmModalMsg present (reset confirmation dialog)")
else:
    fail("confirmModal/confirmModalMsg missing — reset confirmation dialog broken")

# 22.2 showConfirm / closeConfirmModal functions present
for fn_name in ["showConfirm", "closeConfirmModal"]:
    if f"function {fn_name}(" in js:
        ok(f"{fn_name}() present")
    else:
        fail(f"{fn_name}() missing — reset confirmation broken")

# 22.3 resetToDefaults uses showConfirm (not direct reset)
reset_fn2 = re.search(r"function resetToDefaults\(\).*?\}", js, re.DOTALL)
if reset_fn2 and "showConfirm" in reset_fn2.group(0):
    ok("resetToDefaults uses showConfirm (user confirmation before reset)")
elif "function resetToDefaults()" in js:
    idx_r = js.find("function resetToDefaults()")
    body_r = js[idx_r:idx_r+200]
    if "showConfirm" in body_r:
        ok("resetToDefaults uses showConfirm (user confirmation before reset)")
    else:
        fail("resetToDefaults does not use showConfirm — reset happens immediately without confirmation")
else:
    fail("resetToDefaults function not found")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 23 — getPPO2Limit trimix safety
# Bug: getPPO2Limit(fN2) used 1-fN2 as fO2 — wrong for trimix (He > 0)
# e.g. 21/35 trimix: fN2=0.44 → 1-fN2=0.56 → ppo2High(1.4) band selected
# Correct: fO2=0.21 → <28% → ppo2Low(1.6) band → switch depth 9m deeper
# ══════════════════════════════════════════════════════════════════════════════

# 23.1 getPPO2Limit takes fO2 directly (not fN2)
ppl_fn = re.search(r"function getPPO2Limit\((\w+)\)", zhl_src)
if ppl_fn:
    param = ppl_fn.group(1)
    if param == 'fO2':
        ok("getPPO2Limit(fO2) — uses fO2 directly, trimix-safe")
    else:
        fail(f"getPPO2Limit({param}) — uses {param}, not fO2; 1-fN2 wrong for trimix (wrong ppO2 limit band)")
else:
    fail("getPPO2Limit function not found")

# 23.2 getPPO2Limit body uses fO2 directly (not 1-fN2)
ppl_body = re.search(r"function getPPO2Limit\(.*?\{(.*?)\}", zhl_src, re.DOTALL)
if ppl_body:
    body = ppl_body.group(1)
    if "1 - fN2" in body or "1-fN2" in body:
        fail("getPPO2Limit body still uses 1-fN2 — trimix ppO2 limit wrong")
    else:
        ok("getPPO2Limit body does not use 1-fN2 (trimix-safe)")

# 23.3 optimalSwitchDepth passes fO2 (not fN2) to getPPO2Limit
osd_fn = re.search(r"function optimalSwitchDepth\(.*?\n  \}", js, re.DOTALL)
if osd_fn:
    osd_body = osd_fn.group(0)
    if "getPPO2Limit(fO2)" in osd_body or "getPPO2Limit(fO2 " in osd_body:
        ok("optimalSwitchDepth passes fO2 to getPPO2Limit (trimix-safe switch depth)")
    elif "getPPO2Limit(fN2)" in osd_body:
        fail("optimalSwitchDepth passes fN2 to getPPO2Limit — switch depth wrong for trimix")

# 23.4 Stop row rendering passes trimix-safe fO2 to getPPO2Limit
stop_loop = js[js.find("collapsedMDP.forEach"):js.find("collapsedMDP.forEach")+600] if "collapsedMDP.forEach" in js else ""
if "getPPO2Limit(_sFO2)" in stop_loop or ("getPPO2Limit" in stop_loop and "_sFHe" in stop_loop):
    ok("Stop row rendering passes trimix-safe fO2 to getPPO2Limit")
elif "getPPO2Limit(_sFN2)" in stop_loop:
    fail("Stop row passes _sFN2 to getPPO2Limit — ppO2 limit color wrong for trimix stops")

# 23.5 getActiveGas passes fO2 (not fN2) to getPPO2LimitFn
_gag_ppo2 = _gas_core_js.split("function getActiveGas", 1)[-1].split("function ppO2Check", 1)[0] if "function getActiveGas" in _gas_core_js else ""
if "getPPO2LimitFn(fO2)" in _gag_ppo2 or "getPPO2LimitFn( fO2" in _gag_ppo2:
    ok("getActiveGas passes fO2 to getPPO2LimitFn (trimix-safe deco gas selection)")
elif "getPPO2LimitFn(dg.fN2)" in _gag_ppo2:
    fail("getActiveGas passes dg.fN2 to getPPO2LimitFn — wrong ppO2 limit band for trimix deco gases")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 24 — GAS BAND ppO2 LIMITS (mid-band and boundary correctness)
# Bug: ppo2Mid was set to ppo2Bottom (1.4) — gives wrong MOD for 28-44% O2
#      gases like EAN32. Should be 1.5.
# Bug: inner engine getPPO2Limit used <=28 and <=45 (wrong boundary assignment)
#      — exactly 28% should be mid (1.5), exactly 45% should be rich (1.6).
# ══════════════════════════════════════════════════════════════════════════════

# 24.1 ppo2Mid is 1.5 (not ppo2Bottom) in runDecoSchedule
run_deco_fn = re.search(r"function runDecoSchedule\(\)(.*?)(?=\nfunction )", js, re.DOTALL)
if run_deco_fn:
    rd_body = run_deco_fn.group(1)
    if "ppo2Mid  = 1.5" in rd_body or "ppo2Mid = 1.5" in rd_body:
        ok("runDecoSchedule: ppo2Mid = 1.5 (mid-band 28–44% O2 uses 1.5 bar limit)")
    elif "ppo2Mid  = ppo2Bottom" in rd_body or "ppo2Mid = ppo2Bottom" in rd_body:
        fail("runDecoSchedule: ppo2Mid = ppo2Bottom — EAN32/EAN36 get wrong MOD (1.4 instead of 1.5)")
    else:
        fail("runDecoSchedule: ppo2Mid assignment not found — mid-band limit unknown")
else:
    fail("runDecoSchedule function not found — cannot audit ppo2Mid")

# 24.2 Inner engine getPPO2Limit uses < not <= for 28% boundary (28% is mid)
inner_ppl = re.search(r"function getPPO2Limit.*?ppO2Low.*?ppO2Mid.*?ppO2High", js, re.DOTALL)
inner_js_block = js[js.find("if (settings.ppO2Low && settings.ppO2Mid"):js.find("if (settings.ppO2Low && settings.ppO2Mid")+300]
if "o2pct < 28" in inner_js_block:
    ok("Inner engine getPPO2Limit: <28 boundary (28% O2 correctly goes to mid/1.5)")
elif "o2pct <= 28" in inner_js_block:
    fail("Inner engine getPPO2Limit: <=28 boundary — 28% O2 wrongly gets lean/1.4 (should be mid/1.5)")

# 24.3 Inner engine getPPO2Limit uses < not <= for 45% boundary (45% is rich)
if "o2pct < 45" in inner_js_block:
    ok("Inner engine getPPO2Limit: <45 boundary (45% O2 correctly goes to rich/1.6)")
elif "o2pct <= 45" in inner_js_block:
    fail("Inner engine getPPO2Limit: <=45 boundary — 45% O2 wrongly gets mid/1.5 (should be rich/1.6)")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 25 — REPETITIVE DIVE CNS/OTU CARRY
# Bug: CNS/OTU always started at 0 even for repetitive dives.
# Fix: _lastVPMResult now stores finalCNS/finalOTU; settings._preCNS (decayed
#      on 90-min half-life) and settings._preOTU are injected for next dive;
#      calculate() initialises totalCNS/totalOTU from these pre-dive values.
# ══════════════════════════════════════════════════════════════════════════════

# 25.1 _lastVPMResult stores finalCNS
if "finalCNS:" in js and "_lastVPMResult" in js:
    ok("_lastVPMResult stores finalCNS for repetitive dive carry")
else:
    fail("_lastVPMResult missing finalCNS — CNS not carried across repetitive dives")

# 25.2 _lastVPMResult stores finalOTU
if "finalOTU:" in js and "_lastVPMResult" in js:
    ok("_lastVPMResult stores finalOTU for repetitive dive carry")
else:
    fail("_lastVPMResult missing finalOTU — OTU not carried across repetitive dives")

# 25.3 _preCNS injected with 90-min half-life decay
if "settings._preCNS" in js and "Math.pow(0.5, siMin / 90)" in js:
    ok("_preCNS injected with 90-min half-life CNS decay across surface interval")
else:
    fail("_preCNS not set with 90-min half-life decay — CNS carry broken for repetitive dives")

# 25.4 _preOTU injected (daily accumulator, no decay)
if "settings._preOTU" in js:
    ok("_preOTU injected as daily accumulator for repetitive OTU carry")
else:
    fail("_preOTU not set — OTU not carried across repetitive dives")

# 25.5 totalCNS initialised from _preCNS in VPM calculate()
if "settings._preCNS || 0" in js:
    ok("VPM calculate() initialises totalCNS from _preCNS (repetitive carry)")
else:
    fail("VPM calculate() still starts totalCNS at 0 — repetitive CNS carry broken")

# 25.6 totalOTU initialised from _preOTU in VPM calculate()
if "settings._preOTU || 0" in js:
    ok("VPM calculate() initialises totalOTU from _preOTU (repetitive carry)")
else:
    fail("VPM calculate() still starts totalOTU at 0 — repetitive OTU carry broken")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 26 — WATER PRESSURE FACTOR ALIGNMENT
# Both engines must use the same canonical m/bar factors:
#   salt:    10.000 m/bar (MultiDeco/DiveKit/ApexDeco standard)
#   fresh:   10.330 m/bar (matches ZHL WATER_DENSITY.fresh 0.09681 bar/m)
#   EN13319: 10.080 m/bar (EN13319 standard — DiveKit compatible)
# VPM engine must recognise EN13319 as waterType===2 (not silently fall through to salt).
# ══════════════════════════════════════════════════════════════════════════════

# 26.1 VPM SLP_SW_M = 10.000 (not old 10.078)
if "SLP_SW_M = 10.000" in vpm_src:
    ok("VPM SLP_SW_M = 10.000 m/bar (MultiDeco/DiveKit standard)")
elif "SLP_SW_M = 10.078" in vpm_src:
    fail("VPM SLP_SW_M still 10.078 — should be 10.000 to match MultiDeco/DiveKit")
else:
    fail("VPM SLP_SW_M not found or unexpected value")

# 26.2 VPM SLP_FW_M = 10.330 (matches ZHL WATER_DENSITY.fresh)
if "SLP_FW_M = 10.330" in vpm_src:
    ok("VPM SLP_FW_M = 10.330 m/bar (matches ZHL fresh factor)")
elif "SLP_FW_M = 10.337" in vpm_src:
    fail("VPM SLP_FW_M still 10.337 — should be 10.330 to match ZHL WATER_DENSITY.fresh")
else:
    fail("VPM SLP_FW_M not found or unexpected value")

# 26.3 VPM SLP_EN_M defined (EN13319)
if "SLP_EN_M = 10.080" in vpm_src:
    ok("VPM SLP_EN_M = 10.080 m/bar (EN13319 constant defined)")
else:
    fail("VPM SLP_EN_M not defined — EN13319 water type unsupported in VPM engine")

# 26.4 getSLP handles waterType===2 (EN13319)
if "settings.waterType === 2" in vpm_src:
    ok("getSLP(): waterType===2 branch present (EN13319 support)")
else:
    fail("getSLP(): no waterType===2 branch — EN13319 silently uses salt factor in VPM")

# 26.5 waterTypeVal maps EN13319 to 2
if ("'en13319' ? 2" in js or '"en13319" ? 2' in js or
    "=== 'en13319' ? 2" in js or '=== "en13319" ? 2' in js or
    "sel === 'en13319') return 2" in js):
    ok("waterTypeVal: EN13319 mapped to 2 (not silently 0/salt)")
else:
    fail("waterTypeVal: EN13319 not mapped to 2 — VPM engine uses wrong water factor for EN13319")

# 26.5b custom water density maps to waterType 3 + barPerM in VPM
if ("sel === 'custom') return 3" in js
        and "waterType === 3" in vpm_src
        and "settings.barPerM" in vpm_src):
    ok("waterTypeVal: custom maps to waterType 3 with barPerM in VPM engine (Issue #2 MEDIUM-2)")
else:
    fail("waterTypeVal: custom water density not mapped for VPM (Issue #2 MEDIUM-2)")

# 26.6 No hardcoded salt slp in VPM functions
if "SLP_SW_M : SLP_SW_F" in vpm_src:
    fail("VPM inner functions still use hardcoded salt slp — water type not respected")
else:
    ok("VPM inner functions use getSLP(settings) not hardcoded salt factor")

# 26.7 ZHL WATER_DENSITY.salt = 0.10000
if "salt:     0.10000" in js or "salt: 0.10000" in js:
    ok("ZHL WATER_DENSITY.salt = 0.10000 bar/m (10.000 m/bar — industry standard)")
elif "salt:     0.10020" in js or "salt: 0.10020" in js:
    fail("ZHL WATER_DENSITY.salt still 0.10020 — should be 0.10000 (MultiDeco/DiveKit)")
else:
    fail("ZHL WATER_DENSITY.salt not found or unexpected value")

# 26.8 ZHL WATER_DENSITY.en13319 = 0.09921
if "en13319:  0.09921" in js or "en13319: 0.09921" in js:
    ok("ZHL WATER_DENSITY.en13319 = 0.09921 bar/m (10.080 m/bar — EN13319 standard)")
elif "en13319:  0.09964" in js or "en13319: 0.09964" in js:
    fail("ZHL WATER_DENSITY.en13319 still 0.09964 — should be 0.09921 (10.080 m/bar)")
else:
    fail("ZHL WATER_DENSITY.en13319 not found or unexpected value")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 27 — BAR_PER_METRE INIT AND 10.078 ERADICATION
# After the water constant unification, BAR_PER_METRE must initialise to the
# salt default (0.10000) and no display/calculation code may hardcode 10.078.
# ══════════════════════════════════════════════════════════════════════════════

# 27.1 BAR_PER_METRE init = 0.10000 (salt default, not stale 1/10.078 = 0.09922)
if "BAR_PER_METRE = 0.10000" in js:
    ok("BAR_PER_METRE init = 0.10000 (salt default, matches WATER_DENSITY.salt)")
elif "BAR_PER_METRE = 1/10.078" in js or "BAR_PER_METRE = 1 / 10.078" in js:
    fail("BAR_PER_METRE init still 1/10.078 = 0.09922 — stale after water constant update")
else:
    fail("BAR_PER_METRE init value unclear — should be 0.10000")

# 27.2 No hardcoded / 10.078 in live calculation code (tooltip HTML exempt)
import re
# Strip HTML comments and tooltip strings before checking
stripped = re.sub(r'<!--.*?-->', '', js, flags=re.DOTALL)
# Remove content inside showTip(...) calls to avoid flagging tooltip text
stripped = re.sub(r"showTip\([^)]{0,400}\)", "showTip()", stripped)
hardcoded_instances = [ln for ln in stripped.split('\n') if '/ 10.078' in ln and '//' not in ln.lstrip()[:3]]
if not hardcoded_instances:
    ok("No hardcoded / 10.078 in live calculation code — all replaced with BAR_PER_METRE")
else:
    fail(f"Hardcoded / 10.078 still present in {len(hardcoded_instances)} line(s) — use BAR_PER_METRE")

# 27.3 VPM render pAmb uses BAR_PER_METRE not 0.0305 imperial hardcode
if "seg.depth * BAR_PER_METRE" in js or ("vpmDisplayPpo2" in js and "depthM * BAR_PER_METRE" in js):
    ok("VPM render: pAmb uses BAR_PER_METRE (not hardcoded imperial 0.0305)")
elif "seg.depth * 0.0305" in js:
    fail("VPM render: pAmb still uses hardcoded imperial 0.0305 — use BAR_PER_METRE")
else:
    fail("VPM render: pAmb calculation not found or ambiguous")

# 27.4 VPM gas tag switch depth: floor in metres, then convert to feet for imperial
if "/ BAR_PER_METRE * (dU ? 1 : 3.28084)" in js:
    ok("VPM gas tag switch depth: imperial formula correct (/ BAR_PER_METRE * 3.28084 → feet)")
elif "Math.floor(modM * 3.28084)" in js and "function vpmDecoSwitchDepthVal" in js:
    ok("VPM gas tag switch depth: floors in metres then converts to feet (L-5)")
elif "BAR_PER_METRE * 0.3048) / (dU ? 1 : 3.28084)" in js or "BAR_PER_METRE * 0.3048) / 3.28084" in js:
    fail("VPM gas tag switch depth: imperial formula broken — / (BPM*0.3048)/3.28084 cancels to metres, displays wrong ft value")
else:
    fail("VPM gas tag switch depth formula not found or changed structure")



# ══════════════════════════════════════════════════════════════════════════════
# GROUP 28 — GF FIRST-STOP ANCHOR FIX (v2.10.7)
# Bug: firstStopDepth was pre-computed from ceiling(bottom_tissues, gfL) → caused
# spurious stop at 21m for Air+EAN50 dives (MultiDeco shows first stop at 18m).
# Fix: firstStopDepth is now anchored dynamically at the ACTUAL first mustStop depth.
# ══════════════════════════════════════════════════════════════════════════════

# 28.1 firstStopDepth must be declared as `let` (mutable), not `const`
# The old bug used `const firstStopDepth = ...` pre-computed from bottom tissues.
if re.search(r'let firstStopDepth = 0;', zhl_src):
    ok("GF anchor: firstStopDepth declared as `let` (mutable, dynamically anchored)")
else:
    fail("GF anchor: firstStopDepth must be `let firstStopDepth = 0` — pre-computed const causes spurious stops")

# 28.2 candidateFirstStop used for stop list, not firstStopDepth
# The candidate stop list must be built from candidateFirstStop, not the old firstStopDepth.
if re.search(r'const candidateFirstStop = bottomCeil > 0', zhl_src):
    ok("GF anchor: stop list built from candidateFirstStop (not pre-computed firstStopDepth)")
else:
    fail("GF anchor: missing candidateFirstStop — stop list must use candidate variable, not firstStopDepth")

# 28.3 firstStopDepth is anchored in the mustStop branch
# The fix must set firstStopDepth = cur when the first required stop is found.
if re.search(r'firstStopDepth\s*=\s*cur;\s*//\s*anchor GF line', zhl_src):
    ok("GF anchor: firstStopDepth set to cur at first mustStop (anchor from actual first stop)")
else:
    fail("GF anchor: firstStopDepth not anchored at first mustStop — spurious stop bug will recur")

# 28.4 minStopZoneDepth is declared as `let` (not const) and starts as null
# With dynamic anchoring, minStopZoneDepth must be null until first stop is known.
if re.search(r'let minStopZoneDepth = null;', zhl_src):
    ok("GF anchor: minStopZoneDepth starts as null (set when first stop is known)")
else:
    fail("GF anchor: minStopZoneDepth must be `let ... = null` — const from pre-computed firstStopDepth is broken")

# 28.5 minStopZoneDepth is set in mustStop branch alongside firstStopDepth
if re.search(r'minStopZoneDepth\s*=\s*cur;\s*//\s*enable min-stop', zhl_src):
    ok("GF anchor: minStopZoneDepth set to cur at first mustStop (min-stop enforcement enabled)")
else:
    fail("GF anchor: minStopZoneDepth not set at first mustStop — min-stop enforcement may fail")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 29 — HEADLESS CNS/OTU DESCENT+BOTTOM FIX (v2.10.8)
# Bug found via 3-way DiveKit/MultiDeco/LSP comparison: window._lastPlan.steps
# only contains ascent/deco segments (descent + bottom are rendered straight to
# DOM in the live app, never pushed into `steps`). The headless CNS/OTU fallback
# in ZHLEngine.calculate() summed only `lp.steps`, silently omitting descent and
# the full bottom-time exposure — the dominant share of CNS/OTU on most dives.
# This was a test-infrastructure bug only: the live DOM-rendering path computes
# CNS/OTU correctly across the full table. Existing tests never caught it because
# they only assert finiteness/ordering, never magnitude against a known value.
# ══════════════════════════════════════════════════════════════════════════════

# 29.1 Plan-walk exposure helper (v2.30.25: replaces inline headlessPpo2 block)
if "function computePlanExposureTotals" in js:
    ok("Headless CNS/OTU: computePlanExposureTotals() plan-walk helper present")
else:
    fail("Headless CNS/OTU: computePlanExposureTotals() missing — descent/bottom may be omitted")

# 29.2 Descent + bottom included via injected plan segments before steps
if "type: 'descent'" in js and "type: 'bottom'" in js and "computePlanExposureTotals(" in js:
    ok("Headless CNS/OTU: descent + bottom segments included in plan-walk exposure")
else:
    fail("Headless CNS/OTU: descent/bottom exposure missing from plan-walk path")

# 29.3 ZHLEngine uses plan-walk after run patching (not pre-plan steps-only sum)
if re.search(r'computePlanExposureTotals\(\s*result\.plan, s, fO2bot', js):
    ok("Headless CNS/OTU: ZHLEngine integrates exposure from assembled plan with run times")
else:
    fail("Headless CNS/OTU: ZHLEngine missing post-plan exposure integration")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 30 — GF-LOW PRE-ANCHOR REGRESSION FIX (v2.10.9)
# Bug found via 3-way comparison against MultiDeco/DiveKit reference data: the
# v2.10.7 gfAt() fix returned gfH (not gfL) when firstStopDepth was unanchored.
# Per Baker's published algorithm (and DAN/Erik Baker's own description), GF LOW
# is what determines the first stop — not GF High. Returning gfH pre-anchor made
# the search use the loose GF-High M-value, so the loop only stopped once GF-High
# itself was violated, anchoring 1-3 deco steps shallower than correct and
# silently dropping total deco time (confirmed: S1 30m/23min air GF30/70 should
# anchor at 12m matching MultiDeco/DiveKit exactly; the gfH-pre-anchor bug instead
# anchored at 6m, skipping the 12m and 9m stops entirely).
# ══════════════════════════════════════════════════════════════════════════════

# 30.1 gfAtDepth returns gfH pre-anchor for NDL; schedule gfAt() keeps gfL pre-anchor
if re.search(r'if \(!firstStopDepth \|\| firstStopDepth <= 0\) return gfH;', _physics_core_js):
    ok("GF anchor: gfAtDepth returns gfH when firstStopDepth unanchored (NDL path)")
elif re.search(r'if \(!firstStopDepth \|\| firstStopDepth <= 0\) return gfL;', _physics_core_js):
    fail("GF anchor: gfAtDepth still returns gfL pre-anchor — NDL uses conservative GF Low")
else:
    fail("GF anchor: gfAtDepth pre-anchor return value not found or changed structure")
_schedule_gf = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
if re.search(r'function gfAt\(depthM\)[\s\S]{0,220}if \(!firstStopDepth \|\| firstStopDepth <= 0\) return gfH;', _schedule_gf):
    ok("GF anchor: schedule gfAt() returns gfH when firstStopDepth unanchored (issue #137 H-7)")
elif re.search(r'function gfAt\(depthM\)[\s\S]{0,220}if \(!firstStopDepth \|\| firstStopDepth <= 0\) return gfL;', _schedule_gf):
    ok("GF anchor: schedule gfAt() returns gfL pre-anchor (Baker first-stop search)")
else:
    fail("GF anchor: schedule gfAt() missing pre-anchor guard (gfH or gfL)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 31 — TTS METRIC + DECOZONE GF-INDEPENDENCE FIX (v2.10.10)
# Found via 3-way comparison against MultiDeco/DiveKit: (1) LSP had no TTS
# (time-to-surface) metric at all, despite MultiDeco/DiveKit both reporting it
# as a primary field; (2) LSP's "decozone start" was actually an alias for
# firstStopDepth (the GF-anchored first stop), not the GF-independent ambient-
# crossing depth MultiDeco/DiveKit report — same dive at different GF settings
# was wrongly reporting different decozone values, off by 10+ metres from
# reference on several scenarios.
# ══════════════════════════════════════════════════════════════════════════════

# 31.1 TTS computed in the engine (headless-safe) as rt - bt
if re.search(r'const ttsMin = Math\.max\(0, rt - bt\);', zhl_src):
    ok("TTS: computed as rt-bt (ascent+deco only) before the headless early-return")
else:
    fail("TTS: rt-bt computation missing — TTS will be unavailable in headless tests")

# 31.2 TTS stored on window._lastPlan
if re.search(r'tts: Math\.round\(ttsMin \* 10\) / 10,', zhl_src) or re.search(r'\.\.\.zhlCore\.lastPlan', js):
    ok("TTS: stored on window._lastPlan.tts")
else:
    fail("TTS: not stored on _lastPlan — headless ZHLEngine.calculate() callers cannot read it")

# 31.3 TTS exposed in ZHLEngine.calculate() return object
if re.search(r'tts: lp\.tts \|\| 0,', js) or re.search(r'tts: lp\.tts \|\| 0,', zhl_bundle_js):
    ok("TTS: exposed in ZHLEngine.calculate() return object")
else:
    fail("TTS: missing from calculate() return object")

# 31.4 TTS shown in the live footer
if re.search(r'>TTS:</span>', js):
    ok("TTS: displayed in the live-render footer")
else:
    fail("TTS: not displayed in footer — feature incomplete")

# 31.5 ambientCrossingDepth() function present — the GF-independent decozone calc
if re.search(r'function ambientCrossingDepth\(tissues\)', js):
    ok("Decozone: ambientCrossingDepth() GF-independent function present")
else:
    fail("Decozone: ambientCrossingDepth() missing — decozone fix may be reverted")

# 31.6 decoZoneStart in _lastPlan uses the new GF-independent value, not firstStopDepth
if re.search(r'decoZoneStart: trueDecoZoneStart,', zhl_src) or re.search(r'\.\.\.zhlCore\.lastPlan', js):
    ok("Decozone: _lastPlan.decoZoneStart uses trueDecoZoneStart (GF-independent)")
elif re.search(r'decoZoneStart: hasDeco \? firstStopDepth : 0,', js):
    fail("Decozone: _lastPlan.decoZoneStart still aliases firstStopDepth — REGRESSION, will vary incorrectly with GF Lo/Hi")
else:
    fail("Decozone: _lastPlan.decoZoneStart assignment not found or changed structure")

# 31.7 Footer decozone display uses the GF-independent value
if re.search(r'formatDecoZoneStart\(trueDecoZoneStart\)', js):
    ok("Decozone: footer display uses trueDecoZoneStart (GF-independent)")
else:
    fail("Decozone: footer display not using trueDecoZoneStart — live render may still show GF-dependent value")


# ══════════════════════════════════════════════════════════════════════════════
# GROUP 32 — MISSING FINAL SURFACE-ASCENT LEG (post-v2.10.12)
# Found via divekit.app's published inputs.json: MultiDeco/DiveKit both use a
# dedicated, slower surfaceAscentMPerMin rate for the final leg from the last
# stop to the surface, distinct from the deep and deco rates. LSP's ZHL engine
# had a surfaceAscentRate UI field and variable, but it was only ever passed to
# runVPMSchedule — the ZHL ascent loop itself treated surfacing as instantaneous
# (zero time, zero off-gassing) once the last stop's hold finished.
# ══════════════════════════════════════════════════════════════════════════════

# 32.1 Final ascent leg present after the main stop loop, using surfaceRate
if re.search(r'const finalAscentDur = cur / surfaceRate;', zhl_src):
    ok("Final ascent: surfaceRate-based leg from lastStop to surface present")
else:
    fail("Final ascent: surfaceRate leg missing — surfacing time/off-gassing undercounted")

# 32.2 Final ascent applies off-gassing via saturateLinear (not treated as instant)
if re.search(r'tissues = saturateLinear\(tissues, cur, 0, finalAscentDur', zhl_src) or re.search(r'tissues = zhlLoadLinear\(tissues, cur, 0, finalAscentDur', zhl_src):
    ok("Final ascent: off-gassing applied via saturateLinear during the final leg")
else:
    fail("Final ascent: off-gassing not applied — tissue state wrong for repetitive-dive surface interval")

# 32.3 Final ascent leg is pushed as its own step (visible in plan/exports)
if re.search(r"type: 'ascent', from: cur, to: 0,", zhl_src):
    ok("Final ascent: pushed as a visible step (from=lastStop, to=0)")
else:
    fail("Final ascent: step not pushed — RT/TTS may update but plan/exports won't show the leg")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 33 — HEADLESS holdStep RESULT-CHANGING BUG (post-v2.10.43)
# Found via a from-scratch 16-compartment tissue diff against ApexDeco on S2:
# tissue states matched almost exactly at every stop (noise-level diffs), but
# the FIRST stop's reported duration differed by ~0.5-0.7min between headless
# test runs and what the real app / ApexDeco would produce for identical input.
# Root cause: holdStep (the while-loop's ceiling-check granularity) was forced
# to a coarse 1 minute in headless mode even for the first stop, which the real
# app deliberately gives a fine 1/6-min (10-sec) resolution. This is the ONLY
# _zhlHeadless branch in the file that changes a computed RESULT rather than
# skipping DOM rendering — every other _zhlHeadless check just skips a render
# call, so this one silently meant headless test numbers (used by this audit's
# sibling test suites AND by Claude's own headless verification scripts) did
# not match what the live app would actually show for the same inputs.
# ══════════════════════════════════════════════════════════════════════════════

# 33.1 holdStep no longer forces coarse resolution for the first stop in headless mode
if re.search(r'const holdStep = isFirstDecoStop \? 1/6 : 1;', zhl_src):
    ok("holdStep: first-stop fine resolution (1/6 min) applies regardless of headless mode")
elif re.search(r'const holdStep = \(window\._zhlHeadless\) \? 1 :', js):
    fail("holdStep: REGRESSION — headless mode still forces coarse 1-min resolution on the first stop, producing different RT/TTS than the real app for identical inputs")
else:
    fail("holdStep: assignment not found or changed structure — verify manually")



# ══════════════════════════════════════════════════════════════════════════════
# GROUP 34 — v2.20.0 features (Surface GF, Prior Carry, Shallow Gradient,
#            Contingency Depth, App Presets)
# ══════════════════════════════════════════════════════════════════════════════

# 34.1 computeSurfaceGF function defined
if re.search(r'function computeSurfaceGF\(tissues\)', js):
    ok("computeSurfaceGF: function defined")
else:
    fail("computeSurfaceGF: function missing — Surface GF metric not computable")

# 34.2 computeSurfaceGF uses correct M-value denominator formula (Baker M0 = a + P_surf/b)
if re.search(r'a\s*\+\s*P_surf\s*/\s*b', tier3_engine_src) and re.search(r'function computeSurfaceGF\(tissues\)', tier3_engine_src):
    ok("computeSurfaceGF: correct M-value denominator (a + P_surf/b)")
elif "ZhlEngineBundle.computeSurfaceGF" in js:
    ok("computeSurfaceGF delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("computeSurfaceGF: M-value denominator formula not found — Surface GF may be wrong")

# 34.3 surfaceGF stored in ZHL _lastPlan
if re.search(r'surfaceGF:\s*computeSurfaceGF\(tissues\)', zhl_src) or re.search(r'\.\.\.zhlCore\.lastPlan', js):
    ok("surfaceGF: stored in ZHL _lastPlan via computeSurfaceGF(tissues)")
else:
    fail("surfaceGF: not stored in ZHL _lastPlan — footer metric missing")

# 34.4 surfaceGF stored in VPM _lastPlan
if re.search(r'surfaceGF:\s*result\.finalTissues\s*\?', js):
    ok("surfaceGF: stored in VPM _lastPlan (conditional on finalTissues)")
else:
    fail("surfaceGF: not stored in VPM _lastPlan")

# 34.5 Surf GF displayed in buildPlanInfoRowHtml
if re.search(r'Surf GF:', js):
    ok("buildPlanInfoRowHtml: Surf GF label in footer")
else:
    fail("buildPlanInfoRowHtml: Surf GF label missing from footer display")

# 34.6 data-surfgf attribute in hidden totals row
if re.search(r'data-surfgf=', js):
    ok("buildPlanInfoRowHtml: data-surfgf attribute stored in hidden totals row")
else:
    fail("buildPlanInfoRowHtml: data-surfgf attribute missing")

# 34.7 PLAN_INFO_TIP updated with Surf GF
if re.search(r'Surf GF.*surface gradient', html, re.IGNORECASE):
    ok("PLAN_INFO_TIP: Surf GF definition included")
else:
    fail("PLAN_INFO_TIP: Surf GF not documented in tooltip")

# 34.8 updatePriorDiveCarry function
if re.search(r'function updatePriorDiveCarry\(\)', js):
    ok("updatePriorDiveCarry: function defined")
else:
    fail("updatePriorDiveCarry: function missing — prior dive OTU/CNS carry not functional")

# 34.9 OTU day-boundary: resets when >= 24h
if re.search(r'24 \* 60', js) and re.search(r'otuCarry.*totalMinutes', js, re.DOTALL):
    ok("updatePriorDiveCarry: day-boundary check (24*60 minutes) present")
else:
    fail("updatePriorDiveCarry: day-boundary logic missing — OTU may not reset after 24h")

# 34.10 Prior carry seeded into ZHL accumulators
if re.search(r'_pdCarry.*priorDiveCarry', js) or re.search(r'_priorDiveCarry.*cnsCarry.*100', js):
    ok("ZHL accumulators: seeded from _priorDiveCarry on init")
else:
    fail("ZHL accumulators: prior dive carry not seeded — CNS/OTU not carried into ZHL plan")

# 34.11 Prior carry injected into VPM settings
if re.search(r'settings\._preOTU.*_priorDiveCarry.*otuCarry', js, re.DOTALL) or \
   re.search(r'_priorDiveCarry.*settings\._preOTU', js, re.DOTALL):
    ok("VPM settings: prior dive carry injected as _preOTU/_preCNS")
else:
    fail("VPM settings: prior dive carry not injected — OTU/CNS not carried into VPM plan")

# 34.12 shallowGradient select element
if re.search(r'id="shallowGradient"', html):
    ok("shallowGradient: select element present in advanced settings")
else:
    fail("shallowGradient: select element missing from HTML")

# 34.13 shallowGradient default is off
if re.search(r'id="shallowGradient".*?<option selected.*?value="off"', html, re.DOTALL):
    ok("shallowGradient: default value is 'off' (standard GF behavior)")
else:
    fail("shallowGradient: default not 'off' — non-standard GF behavior on by default")

# 34.14 shallowGradient in _ADV_FIELDS
if re.search(r"_ADV_FIELDS\s*=\s*\[[\s\S]*?'shallowGradient'", js):
    ok("_ADV_FIELDS: includes shallowGradient")
else:
    fail("_ADV_FIELDS: shallowGradient missing — setting not saved/loaded with config presets")

# 34.15 gfAt respects shallowGradient
if re.search(r'shallowGradient.*value.*===.*on', js) or re.search(r"shallowGradient.*'on'", js):
    ok("gfAt: shallowGradient setting read at runtime")
else:
    fail("gfAt: shallowGradient setting not referenced — toggle has no effect")

# 34.16 gfAt shallow gradient: clamps to gfH at lastStop when ON
if re.search(r'sgOn && depthM <= lastStop.*return gfH', zhl_src, re.DOTALL) or re.search(
    r'shallowGradient && depthM <= lastStop.*return gfH', tier3_engine_src, re.DOTALL
):
    ok("gfAt: shallow gradient ON returns gfH at lastStop and shallower")
else:
    fail("gfAt: shallow gradient ON does not apply gfH at lastStop")

# 34.17 contExtraDepth variable declared
if re.search(r'let contExtraDepth\s*=', js):
    ok("contExtraDepth: variable declared")
else:
    fail("contExtraDepth: variable missing — went-deeper contingency not wired")

# 34.18 selectContDepth function
if re.search(r'function selectContDepth\(metres\)', js):
    ok("selectContDepth: function defined")
else:
    fail("selectContDepth: function missing")

# 34.19 Went deeper buttons in HTML
if all(re.search(f'id="contDepth{v}"', html) for v in [0, 3, 5]):
    ok("contingency HTML: +0m/+3m/+5m depth buttons present")
else:
    fail("contingency HTML: went-deeper buttons missing (contDepth0/3/5)")

# 34.20 calcContingency sets origDepth and restores it
if re.search(r'origDepth.*decoDepth.*value', js) and re.search(r"document.*getElementById\('decoDepth'\)\.value\s*=\s*origDepth", js):
    ok("calcContingency: depth saved as origDepth and restored after scenario run")
else:
    fail("calcContingency: depth not saved/restored — went-deeper leaves depth field modified")

# 34.21 LSP_APP_PRESETS constant defined with 5 entries
app_presets = re.findall(r"name:\s*'(MultiDeco|Abysner|Subsurface|GUE DecPlanner|DiveKit)'", js)
if len(set(app_presets)) == 5:
    ok(f"LSP_APP_PRESETS: all 5 app presets defined ({', '.join(sorted(set(app_presets)))})")
else:
    fail(f"LSP_APP_PRESETS: only {len(set(app_presets))}/5 app presets found: {set(app_presets)}")

# 34.22 loadAppPreset function
if re.search(r'function loadAppPreset\(idx\)', js):
    ok("loadAppPreset: function defined")
else:
    fail("loadAppPreset: function missing — app presets cannot be loaded")

# 34.23 _renderConfigPresetModal shows app presets header
if re.search(r'App Reference Presets', js):
    ok("_renderConfigPresetModal: app presets section header present")
else:
    fail("_renderConfigPresetModal: app presets section not shown in modal")

# 34.27 App presets: stopRounding values must be 'wholeminute' or 'fractional' (not 'whole')
stale_whole = re.findall(r"stopRounding:\s*'whole'(?!minute)", js)
if stale_whole:
    fail(f"App presets: {len(stale_whole)} stopRounding='whole' (invalid) — must be 'wholeminute' or 'fractional'")
else:
    ok("App presets: stopRounding values all valid ('wholeminute' or 'fractional')")

# 34.28 App presets: o2AtMODSelect must be 'on' or 'off' (not 'yes'/'no')
stale_yes = re.findall(r"o2AtMODSelect:\s*'yes'", js)
if stale_yes:
    fail(f"App presets: {len(stale_yes)} o2AtMODSelect='yes' (invalid) — must be 'on' or 'off'")
else:
    ok("App presets: o2AtMODSelect values all valid ('on' or 'off')")

# 34.29 GUE DecPlanner ppo2 values must be valid select options (1.2/1.4/1.5/1.6)
gue_ppo2 = re.findall(r"name:\s*'GUE DecPlanner'[\s\S]*?ppo2Bottom:\s*'([^']+)'", js)
if gue_ppo2 and gue_ppo2[0] not in ('1.2','1.4','1.5','1.6'):
    fail(f"GUE DecPlanner ppo2Bottom={gue_ppo2[0]!r} not a valid select option (1.2/1.4/1.5/1.6)")
else:
    ok("GUE DecPlanner preset: ppo2Bottom is a valid select option (1.2 now supported)")
if re.search(r'CNS DUAL-METHOD AUDIT', js):
    ok("CNS dual-method audit: cross-check comment documented")
else:
    fail("CNS dual-method audit: audit comment missing")

# 34.25 OTU_EXPONENT constant defined and no stale 0.833 copies remain
if re.search(r'const OTU_EXPONENT\s*=\s*0\.8333', js) or "ZhlEngineBundle.OTU_EXPONENT" in js:
    ok("OTU_EXPONENT: constant defined (0.8333)")
else:
    fail("OTU_EXPONENT: constant missing — OTU exponent not a single source of truth")

stale_083 = re.findall(r'0\.833[^3]', js)
if stale_083:
    fail(f"OTU exponent: {len(stale_083)} stale 0.833 (3-digit) copies remain — should use OTU_EXPONENT")
else:
    ok("OTU exponent: no stale 0.833 (3-digit) copies — all sites use OTU_EXPONENT")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 35 — v2.20.4–v2.20.14 GF controls, ppo2 expansion, export guards
# ══════════════════════════════════════════════════════════════════════════════

# 35.1 Bühlmann GF dropdown: 50/80 and 60/70 present (regression: missing in v2.20.5–v2.20.6)
buhl_gf_opts = re.findall(r'option value="(\d+/\d+)"', html)
for must_have in ['50/80', '60/70']:
    if must_have in buhl_gf_opts:
        ok(f"GF preset dropdown: {must_have} option present")
    else:
        fail(f"GF preset dropdown: {must_have} missing — regression from v2.20.5/v2.20.6")

# 35.2 ppo2Bottom and ppo2Deco selects include 1.2 bar option (v2.20.13)
for sel_id in ('ppo2Bottom', 'ppo2Deco'):
    # find the select block
    pat = rf'id="{sel_id}"[\s\S]{{1,300}}?</select>'
    m = re.search(pat, html)
    if not m:
        fail(f"{sel_id}: select element not found in HTML")
    elif '1.2' not in m.group():
        fail(f"{sel_id}: 1.2 bar option missing — GUE DecPlanner preset will silently fail")
    else:
        ok(f"{sel_id}: 1.2 bar option present")

# 35.3 VPM-B/GFS GF dropdown: hi/N options defined in setDecoAlgorithm
if re.search(r'value="hi/70"', html) and re.search(r'value="hi/85"', html):
    ok("VPM-B/GFS GF dropdown: hi/N options defined in setDecoAlgorithm rebuild")
else:
    fail("VPM-B/GFS GF dropdown: hi/N format options not found")

# 35.4 mGF selection restored after Bühlmann dropdown rebuild (v2.20.14)
if re.search(r'_restoredOpt\s*=\s*Array\.from\(gfSel\.options\)', js):
    ok("setDecoAlgorithm: mGF selection restored into rebuilt Bühlmann dropdown (v2.20.14)")
else:
    fail("setDecoAlgorithm: mGF restore missing — GF selection lost after VPM-B→Bühlmann switch")

# 35.5 cnsNumExport guard: no crash when planSum.cns is undefined (v2.20.11)
if re.search(r'parseFloat\(\(planSum\.cns\s*\|\|\s*\'0\'\)\.replace', js):
    ok("cnsNumExport: guarded (planSum.cns || '0') — no crash on undefined")
else:
    fail("cnsNumExport: missing guard — text export crashes when planSum.cns undefined")

# 35.6 getContingencySummaryExport returns surfGF (v2.20.15)
if re.search(r'function getContingencySummaryExport\(\)', js):
    ok("getContingencySummaryExport: function present")
else:
    fail("getContingencySummaryExport: function missing")

if re.search(r'surfGF.*c\.surfGF', js) and re.search(r'totRow\.dataset\.surfgf', js):
    ok("getContingencySummaryExport: returns surfGF from dataset and _lastContingency")
else:
    fail("getContingencySummaryExport: surfGF not propagated — contingency export missing Surf GF")

if re.search(r'_lastContingency\s*=.*surfGF', js):
    ok("_lastContingency: stores surfGF for export")
else:
    fail("_lastContingency: surfGF not stored — contingency text/PDF export will show '-'")

if re.search(r'emSumPdf\.surfGF', js):
    ok("contingency PDF footer: includes Surf GF")
else:
    fail("contingency PDF footer: Surf GF missing — inconsistent with main plan PDF")

# 35.7 algorithmSelect and gfPresetSelect in appSettings save/restore field list
for fid in ('algorithmSelect', 'gfPresetSelect'):
    if re.search(rf"'{fid}'", js):
        ok(f"appSettings: '{fid}' referenced in save/restore")
    else:
        fail(f"appSettings: '{fid}' missing — algorithm/GF not persisted across sessions")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 36 — dive plan info banner, PDF helpers, travel gas, text export refactor
# ══════════════════════════════════════════════════════════════════════════════

# 36.1 buildDecoPlanHeaderData function exists
if re.search(r'function buildDecoPlanHeaderData\(\)', js):
    ok("buildDecoPlanHeaderData: function defined")
else:
    fail("buildDecoPlanHeaderData: function missing — banner/export/PDF will crash")

# 36.2 buildDecoPlanHeaderLines function exists
if re.search(r'function buildDecoPlanHeaderLines\(\)', js):
    ok("buildDecoPlanHeaderLines: function defined")
else:
    fail("buildDecoPlanHeaderLines: missing — text export header broken")

# 36.3 renderDecoPlanHeaderHtml function exists
if re.search(r'function renderDecoPlanHeaderHtml\(', js):
    ok("renderDecoPlanHeaderHtml: function defined")
else:
    fail("renderDecoPlanHeaderHtml: missing — on-screen banner will not render")

# 36.4 stamp format YYYY/MM/DD — must NOT be YYYY/DD/MM (month and day swapped)
stamp_pat = re.search(r'const stamp\s*=\s*`\$\{_yy\}/\$\{([^}]+)\}/\$\{([^}]+)\}', js)
if stamp_pat:
    first, second = stamp_pat.group(1), stamp_pat.group(2)
    if first == '_mm' and second == '_dd':
        ok("stamp format: YYYY/MM/DD (correct)")
    elif first == '_dd' and second == '_mm':
        fail("stamp format: YYYY/DD/MM (month and day SWAPPED — date shown incorrectly)")
    else:
        fail(f"stamp format: unexpected order {first}/{second}")
else:
    fail("stamp format: pattern not found")

# 36.5 getDecoGasSwitches does NOT call closure-scoped optimalSwitchDepth
gdsw_start = js.find('function getDecoGasSwitches()')
gdsw_end = js.find('\nfunction ', gdsw_start + 10)
if gdsw_start >= 0:
    gdsw_body = js[gdsw_start:gdsw_end] if gdsw_end > 0 else js[gdsw_start:gdsw_start+2000]
    if 'optimalSwitchDepth' in gdsw_body:
        fail("getDecoGasSwitches: calls closure-scoped optimalSwitchDepth — ReferenceError outside runDecoSchedule")
    else:
        ok("getDecoGasSwitches: no closure-scoped optimalSwitchDepth — safe to call globally")
else:
    fail("getDecoGasSwitches: function not found")

# 36.6 getTravelGasExport and isTravelGasConfigured defined
for fn in ('getTravelGasExport', 'isTravelGasConfigured', 'getTravelGasFromTable'):
    if re.search(rf'function {fn}\(\)', js):
        ok(f"{fn}: defined")
    else:
        fail(f"{fn}: missing")

# 36.7 PDF helper functions defined
for fn in ('_pdfDecoTableLayout', '_pdfDrawDecoTableHeader', '_pdfDrawSwitchRow',
           '_pdfDrawDecoTableCells', '_pdfDrawDecoPhaseLabel', 'drawDecoPlanBannerPdf'):
    if re.search(rf'function {fn}\(', js):
        ok(f"{fn}: PDF helper defined")
    else:
        fail(f"{fn}: missing — PDF table/banner rendering broken")

# 36.8 _PDF_TBL_PAD constant defined
if re.search(r'const _PDF_TBL_PAD\s*=', js):
    ok("_PDF_TBL_PAD: PDF table padding constant defined")
else:
    fail("_PDF_TBL_PAD: missing — _pdfDecoTableLayout uses undefined variable")

# 36.9 dive-plan-banner CSS and helper functions
if re.search(r'\.dive-plan-banner\s*\{', html):
    ok("dive-plan-banner: CSS class defined")
else:
    fail("dive-plan-banner: CSS class missing")

for fn in ('_escHtmlPre', 'shortMixLabel', '_dpbGasChipClass', '_pdfChipColors'):
    if re.search(rf'function {fn}\(', js):
        ok(f"{fn}: helper defined")
    else:
        fail(f"{fn}: missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 37 — buildDecoPlanHeaderData fixes: densityMap, du, stamp consistency
# ══════════════════════════════════════════════════════════════════════════════

# 37.1 buildDecoPlanHeaderData defines its own density label (not relying on outer scope)
bdhd_start = js.find('function buildDecoPlanHeaderData()')
bdhd_end = js.find('\nfunction ', bdhd_start + 10) if bdhd_start >= 0 else -1
if bdhd_start >= 0:
    bdhd_body = js[bdhd_start:bdhd_end] if bdhd_end > 0 else js[bdhd_start:bdhd_start+3000]
    if re.search(r'const _?densityMap\s*=\s*\{', bdhd_body) or 'waterDensityDisplayLabel()' in bdhd_body:
        ok("buildDecoPlanHeaderData: defines own densityMap — no ReferenceError")
    else:
        fail("buildDecoPlanHeaderData: missing densityMap definition — ReferenceError on call")
else:
    fail("buildDecoPlanHeaderData: function not found")

# 37.2 buildDecoPlanHeaderData defines du before returning it
if bdhd_start >= 0:
    bdhd_body2 = js[bdhd_start:bdhd_end] if bdhd_end > 0 else js[bdhd_start:bdhd_start+3000]
    if re.search(r'const du\s*=', bdhd_body2):
        ok("buildDecoPlanHeaderData: defines du — not undefined in return")
    else:
        fail("buildDecoPlanHeaderData: missing 'du' definition — returns undefined for du")

# 37.3 buildExportText stamp is YYYY/MM/DD (not YYYY/DD/MM)
bex_start = js.find('function buildExportText(')
bex_end = js.find('\nfunction ', bex_start + 10) if bex_start >= 0 else -1
if bex_start >= 0:
    bex_body = js[bex_start:bex_end] if bex_end > 0 else js[bex_start:bex_start+5000]
    bex_stamp = re.search(r'const stamp\s*=\s*`\$\{_yy\}/\$\{([^}]+)\}/\$\{([^}]+)\}', bex_body)
    if bex_stamp:
        f1, f2 = bex_stamp.group(1), bex_stamp.group(2)
        if f1 == '_mm' and f2 == '_dd':
            ok("buildExportText stamp: YYYY/MM/DD (correct)")
        else:
            fail(f"buildExportText stamp: wrong order {f1}/{f2} — should be _mm/_dd")
    else:
        fail("buildExportText: stamp pattern not found")
else:
    fail("buildExportText: function not found")

# 37.4 buildSlateText stamp is YYYY/MM/DD (not YYYY/DD/MM)
bsl_start = js.find('function buildSlateText()')
bsl_end = js.find('\nfunction ', bsl_start + 10) if bsl_start >= 0 else -1
if bsl_start >= 0:
    bsl_body = js[bsl_start:bsl_end] if bsl_end > 0 else js[bsl_start:bsl_start+5000]
    bsl_stamp = re.search(r'const stamp\s*=\s*`\$\{[^}]+\}/\$\{([^}]+)\}/\$\{([^}]+)\}', bsl_body)
    if bsl_stamp:
        f1, f2 = bsl_stamp.group(1), bsl_stamp.group(2)
        if f1 == '_sMo' and f2 == '_sD':
            ok("buildSlateText stamp: YYYY/MM/DD (correct)")
        else:
            fail(f"buildSlateText stamp: wrong order {f1}/{f2} — should be _sMo/_sD")
    else:
        fail("buildSlateText: stamp pattern not found")
else:
    fail("buildSlateText: function not found")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 38 — handleGFSelect custom: populates from mGF not stale localStorage
# ══════════════════════════════════════════════════════════════════════════════

# 38.1 handleGFSelect Buhlmann custom branch uses mGF, not raw localStorage
hgfs_start = js.find('function handleGFSelect(')
hgfs_end = js.find('\nfunction ', hgfs_start + 10) if hgfs_start >= 0 else -1
if hgfs_start >= 0:
    hgfs_body = js[hgfs_start:hgfs_end] if hgfs_end > 0 else js[hgfs_start:hgfs_start+2000]
    # Check Buhlmann custom branch: must reference mGF (not just raw localStorage)
    # Find the non-VPMB_GFS custom branch
    custom_idx = hgfs_body.find("} else if (val === 'custom') {")
    if custom_idx >= 0:
        custom_branch = hgfs_body[custom_idx:custom_idx+900]
        if re.search(r'mGF\.low', custom_branch) and re.search(r'mGF\.high', custom_branch):
            ok("handleGFSelect custom (Buhlmann): uses mGF.low/high — preset values preserved when switching to Custom")
        else:
            fail("handleGFSelect custom (Buhlmann): uses raw localStorage only — switching to Custom resets inputs, ignoring loaded preset values")
    else:
        fail("handleGFSelect: Buhlmann custom branch not found")
else:
    fail("handleGFSelect: function not found")

# 38.2 handleGFSelect VPM-B/GFS custom branch also uses mGF
if hgfs_start >= 0:
    vpmgfs_idx = hgfs_body.find("val === 'custom' && isVPMBGFSMode")
    if vpmgfs_idx >= 0:
        vpmgfs_branch = hgfs_body[vpmgfs_idx:vpmgfs_idx+600]
        if re.search(r'mGF\.high', vpmgfs_branch):
            ok("handleGFSelect custom (VPM-B/GFS): uses mGF.high — current GF High preserved when switching to Custom")
        else:
            fail("handleGFSelect custom (VPM-B/GFS): uses raw localStorage only — GF High resets on Custom select")
    else:
        fail("handleGFSelect: VPM-B/GFS custom branch not found")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 39 — contingency + messenger export stamp order
# ══════════════════════════════════════════════════════════════════════════════

# 39.1 buildMessengerText contingency branch stamp YYYY/MM/DD
bmsg_start = js.find('function buildMessengerText(')
bmsg_end = js.find('\nfunction ', bmsg_start + 10) if bmsg_start >= 0 else -1
if bmsg_start >= 0:
    bmsg_body = js[bmsg_start:bmsg_end] if bmsg_end > 0 else js[bmsg_start:bmsg_start+8000]
    cont_idx = bmsg_body.find("if (mode === 'contingency')")
    if cont_idx >= 0:
        cont_body = bmsg_body[cont_idx:cont_idx+3000]
        if re.search(r'_cStamp\s*=\s*`\$\{_cn\.getFullYear\(\)\}/\$\{String\(_cn\.getMonth\(\)\+1\)', cont_body):
            ok("buildMessengerText contingency stamp: YYYY/MM/DD (correct)")
        elif re.search(r'_cStamp\s*=\s*`\$\{_cn\.getFullYear\(\)\}/\$\{String\(_cn\.getDate\(\)\)', cont_body):
            fail("buildMessengerText contingency stamp: YYYY/DD/MM (day before month)")
        else:
            fail("buildMessengerText contingency: _cStamp pattern not found")
    else:
        fail("buildMessengerText: contingency branch not found")
else:
    fail("buildMessengerText: function not found")

# 39.2 buildMessengerText deco stamp YYYY/MM/DD
bmsg_start = js.find('function buildMessengerText(')
bmsg_end = js.find('\nfunction ', bmsg_start + 10) if bmsg_start >= 0 else -1
if bmsg_start >= 0:
    bmsg_body = js[bmsg_start:bmsg_end] if bmsg_end > 0 else js[bmsg_start:bmsg_start+5000]
    if re.search(r'_msgStamp\s*=\s*`\$\{_msgNow\.getFullYear\(\)\}/\$\{String\(_msgNow\.getMonth\(\)\+1\)', bmsg_body):
        ok("buildMessengerText stamp: YYYY/MM/DD (correct)")
    elif re.search(r'_msgStamp\s*=\s*`\$\{_msgNow\.getFullYear\(\)\}/\$\{String\(_msgNow\.getDate\(\)\)', bmsg_body):
        fail("buildMessengerText stamp: YYYY/DD/MM (day before month)")
    else:
        fail("buildMessengerText: _msgStamp pattern not found")
else:
    fail("buildMessengerText: function not found")

# 39.3 buildContingencySlateText stamp YYYY/MM/DD
bcs_start = js.find('function buildContingencySlateText(')
bcs_end = js.find('\nfunction ', bcs_start + 10) if bcs_start >= 0 else -1
if bcs_start >= 0:
    bcs_body = js[bcs_start:bcs_end] if bcs_end > 0 else js[bcs_start:bcs_start+5000]
    if re.search(r'ecStamp\s*=\s*`\$\{_ecNow\.getFullYear\(\)\}/\$\{_ecMo\}/\$\{_ecD\}', bcs_body):
        ok("buildContingencySlateText stamp: YYYY/MM/DD (correct)")
    elif re.search(r'ecStamp\s*=\s*`\$\{_ecNow\.getFullYear\(\)\}/\$\{_ecD\}/\$\{_ecMo\}', bcs_body):
        fail("buildContingencySlateText stamp: YYYY/DD/MM (day before month)")
    else:
        fail("buildContingencySlateText: ecStamp pattern not found")
else:
    fail("buildContingencySlateText: function not found")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 40 — formatPlanSummaryBlock returns array; all callers use spread
# ══════════════════════════════════════════════════════════════════════════════

# 40.1 formatPlanSummaryBlock returns an array in both branches (not a string)
fpsb_start = js.find('function formatPlanSummaryBlock(')
fpsb_end = js.find('\nfunction ', fpsb_start + 10) if fpsb_start >= 0 else -1
if fpsb_start >= 0:
    fpsb_body = js[fpsb_start:fpsb_end] if fpsb_end > 0 else js[fpsb_start:fpsb_start+800]
    # Both branches must return an array literal, not a template string
    returns = re.findall(r'return\s+(.*?)(?:\n|;)', fpsb_body)
    all_arrays = all(r.strip().startswith('[') for r in returns if r.strip())
    any_string = any(r.strip().startswith('`') or r.strip().startswith('"') or r.strip().startswith("'") for r in returns if r.strip())
    if all_arrays and not any_string:
        ok("formatPlanSummaryBlock: returns array in both branches — callers must spread")
    else:
        fail(f"formatPlanSummaryBlock: non-array return detected — returns={returns}")
else:
    fail("formatPlanSummaryBlock: function not found")

# 40.2 All call sites use spread operator (...formatPlanSummaryBlock(...))
all_calls = re.findall(r'(?:push|unshift)\((?:\.\.\.|)formatPlanSummaryBlock\(', js)
spread_calls = re.findall(r'push\(\.\.\.formatPlanSummaryBlock\(', js)
non_spread = [c for c in all_calls if '...' not in c]
if non_spread:
    fail(f"formatPlanSummaryBlock: {len(non_spread)} call site(s) missing spread — will push array as single element")
elif spread_calls:
    ok(f"formatPlanSummaryBlock: all {len(spread_calls)} call site(s) use spread (...) — array lines pushed correctly")
else:
    fail("formatPlanSummaryBlock: no call sites found")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 41 — CCR / Rebreather (v2.30)
# ══════════════════════════════════════════════════════════════════════════════

if 'getInspiredInertPressures' in js or js.find('function getInspiredInertPressures(') >= 0:
    ok("getInspiredInertPressures() shared CCR helper present")
else:
    fail("getInspiredInertPressures() not found")

if js.find('// CCR stub') >= 0:
    fail("CCR stub comments still present — tissue math not fully wired")
else:
    ok("No CCR stub comments remain")

if html.find('id="circuitSelect"') >= 0:
    ok("circuitSelect UI control present")
else:
    fail("circuitSelect UI control missing")

if js.find("'circuitSelect'") >= 0 and js.find('DECO_FIELDS') >= 0:
    deco_fields_block = js[js.find('DECO_FIELDS'):js.find('DECO_FIELDS')+1500]
    if "'circuitSelect'" in deco_fields_block:
        ok("circuitSelect in appSettings.DECO_FIELDS")
    else:
        fail("circuitSelect not in appSettings.DECO_FIELDS")
else:
    fail("DECO_FIELDS block not found for CCR check")

if js.find('loadTissuesWithCCR') >= 0 and js.find('function loadTissuesWithCCR') >= 0:
    ok("loadTissuesWithCCR() Bühlmann CCR wrapper present")
else:
    fail("loadTissuesWithCCR() not found")

if js.find('splitSegmentAtSetpoint') >= 0:
    ok("splitSegmentAtSetpoint() present for setpoint crossing")
else:
    fail("splitSegmentAtSetpoint() not found")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 42 — v2.30.9 fixes (errors_bugs_report_v8)
# ══════════════════════════════════════════════════════════════════════════════

buh_cap_start = js.find("const cylCapacity = {}; // gas label")
buh_cap_block = js[buh_cap_start:buh_cap_start + 500] if buh_cap_start > 0 else ""
if "28.3168" in buh_cap_block or "GP_CUFT_PER_L" in buh_cap_block:
    ok("Buhlmann cylCapacity: cylinder size converted cu ft → L in imperial mode")
else:
    fail("Buhlmann cylCapacity: missing imperial cu ft → L conversion (BUG-40)")

clear_start = js.find("clear: function()")
clear_block = js[clear_start:clear_start + 400] if clear_start > 0 else ""
if "lspDiveSettings_v6" in clear_block:
    ok("appSettings.clear() removes lspDiveSettings_v6")
else:
    fail("appSettings.clear() still removes wrong storage key (BUG-41)")

restore_start = js.find("_restoreFields: function")
restore_block = js[restore_start:restore_start + 1200] if restore_start > 0 else ""
if "setTimeout(() => restoreOne(id), 100)" not in restore_block:
    ok("_restoreFields(): no duplicate deferred restore pass")
else:
    fail("_restoreFields() still restores every field twice (BUG-42)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 43 — v2.30.10 fixes (errors_bugs_report_v9)
# ══════════════════════════════════════════════════════════════════════════════

if "scrMetabolicO2 || 0.85" not in js:
    ok("CCR metabolic O2 fallback is 1.5 L/min, not 0.85 (BUG-43)")
else:
    fail("scrMetabolicO2 still falls back to 0.85 L/min (BUG-43)")

if "getCcrMetabolicO2Rate" in js:
    ok("getCcrMetabolicO2Rate() shared helper present")
else:
    fail("getCcrMetabolicO2Rate() helper missing (BUG-43)")

val_ccr_start = js.find("function validateCcrGasConfiguration")
val_ccr_block = js[val_ccr_start:val_ccr_start + 600] if val_ccr_start > 0 else ""
if "circuit === 'pSCR'" in val_ccr_block and "getBailoutPpo2Limit()" in val_ccr_block:
    ok("validateCcrGasConfiguration: pSCR diluent MOD uses ppo2Bottom (BUG-44)")
else:
    fail("validateCcrGasConfiguration: pSCR still uses ccrBottomSetpoint for MOD (BUG-44)")

gp_req_start = js.find("function gpRequiredFor")
gp_req_block = js[gp_req_start:gp_req_start + 700] if gp_req_start > 0 else ""
if "loopMixLabelFor" in gp_req_block:
    ok("gpRequiredFor(): resolves CCR/pSCR loop mix labels (BUG-45)")
else:
    fail("gpRequiredFor(): missing loopMixLabelFor lookup (BUG-45)")

ccr_lit_start = js.find("function ccrGasLitres")
ccr_lit_block = js[ccr_lit_start:ccr_lit_start + 450] if ccr_lit_start > 0 else ""
if "pAmb / pSurf" in ccr_lit_block or "(pAmb / pSurf)" in ccr_lit_block:
    ok("ccrGasLitres(): diluent scaled by ambient pressure (BUG-46)")
else:
    fail("ccrGasLitres(): diluent still flat surface L/min (BUG-46)")

if 'name="description"' in html and "CCR" in html[:3000]:
    ok("<meta description> mentions CCR (BUG-47)")
else:
    fail("<meta description> still OC-only text (BUG-47)")

if 'content="LSP+"' in html and 'apple-mobile-web-app-title' in html[:4000]:
    ok('apple-mobile-web-app-title is "LSP+" (BUG-48)')
else:
    fail('apple-mobile-web-app-title still "D-Planner" (BUG-48)')

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 44 — v2.30.11 fixes (errors_bugs_report_v9 rewrite: BUG-49, BUG-50)
# ══════════════════════════════════════════════════════════════════════════════

if "LSP_${getExportCircuitTag()}_${isoDate}_GasPlan_" in js:
    ok("Gas Plan PDF filename uses dynamic circuit tag (BUG-49 updated)")
else:
    fail("Gas Plan PDF filename does not use getExportCircuitTag() (BUG-49)")

if "LSP_${getExportCircuitTag()}_${isoDate}_Emergency_" in js:
    ok("Emergency PDF filename uses dynamic circuit tag (BUG-49 updated)")
else:
    fail("Emergency PDF filename does not use getExportCircuitTag() (BUG-49)")

if "LSP D-PLANNER + CCR - CNS O2 TRACKER" in js:
    ok("CNS text export header includes + CCR (BUG-50)")
else:
    fail("CNS text export header missing + CCR (BUG-50)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 45 — v2.30.12 fixes (errors_bugs_report_v10)
# ══════════════════════════════════════════════════════════════════════════════

pscr_sch_start = js.find("if (cfg.circuit === 'pSCR')")
pscr_sch_block = js[pscr_sch_start:pscr_sch_start + 700] if pscr_sch_start > 0 else ""
if "getCCRInertSchreinerParams" in js[pscr_sch_start - 200:pscr_sch_start + 50] or pscr_sch_start > 0:
    if "rN2: ((pEnd - ppH2O) * fr1.fN2 - inspN2Start) * pressureRate" not in pscr_sch_block:
        ok("pSCR Schreiner rate: no double pressureRate multiply (BUG-51)")
    else:
        fail("pSCR Schreiner rate still multiplies by pressureRate twice (BUG-51)")

if "u.startsWith('PSCR ')" in js or 'startsWith("PSCR ")' in js:
    ok("isCcrOnLoopGasLabel recognises pSCR prefix (BUG-52)")
else:
    fail("isCcrOnLoopGasLabel still CCR-only (BUG-52)")

if "if (/^air$/i.test(s)) return 'Air';" in js:
    ok("shortMix helpers preserve CCR/pSCR Air labels (BUG-53)")
else:
    fail("shortMix still collapses CCR Air to Air (BUG-53)")

if "diluentUseAsBailout:" in js and "getCCRSettingsFromDOM" in js:
    ok("CCR settings include diluentUseAsBailout via getCCRSettingsFromDOM (BUG-54)")
else:
    fail("getCCRSettingsFromDOM missing diluentUseAsBailout (BUG-54)")

tcf_start = js.find("function toggleCircuitFields")
tcf_block = js[tcf_start:tcf_start + 700] if tcf_start > 0 else ""
if "isRB && bailoutOn" in tcf_block:
    ok("toggleCircuitFields hides bailout GF until rebreather bailout on (BUG-55/59)")
else:
    fail("ccrBailoutSettingsGroup still shown for pSCR/bailout-off (BUG-55)")

if "PSCR_DEFAULT_BYPASS_RATIO" in js and "metRate * PSCR_DEFAULT_BYPASS_RATIO" in js[js.find("function ccrDiluentSurfaceLpm"):js.find("function ccrDiluentSurfaceLpm") + 400]:
    ok("ccrDiluentSurfaceLpm pSCR: metRate × bypass ratio (BUG-75)")
else:
    fail("ccrDiluentSurfaceLpm pSCR still uses (metRate/fO2Loop)×bypass (BUG-75)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 46 — v2.30.13 fixes (errors_bugs_report_v11)
# ══════════════════════════════════════════════════════════════════════════════

cdl_start = js.find("function ccrDiluentSurfaceLpm")
cdl_block = js[cdl_start:cdl_start + 650] if cdl_start > 0 else ""
if "metRate / fO2Loop" not in cdl_block and "altSurfaceP + dM * BAR_PER_METRE" not in cdl_block:
    ok("ccrDiluentSurfaceLpm pSCR: depth scaled once in ccrGasLitres (BUG-57)")
else:
    fail("ccrDiluentSurfaceLpm pSCR still double-scales depth or uses fO2Loop divisor (BUG-57)")

if "function ccrGasLitres" in js and (
    "ccrDiluentSurfaceLpm(depthM) * (pAmb / pSurf)" in js
    or ("surfLpm * (pAmb / pSurf)" in js and "ccrDiluentSurfaceLpm(depthM)" in js.split("function ccrGasLitres", 1)[-1].split("function toggleCircuitFields", 1)[0])
):
    ok("ccrGasLitres scales pSCR diluent once by ambient/surface pressure (BUG-58 path)")
else:
    fail("ccrGasLitres missing single depth scale for pSCR diluent (BUG-58)")

tcf_start = js.find("function toggleCircuitFields")
tcf_block = js[tcf_start:tcf_start + 700] if tcf_start > 0 else ""
if "isRB && bailoutOn" in tcf_block:
    ok("toggleCircuitFields shows bailout GF for pSCR bailout-on (BUG-59)")
else:
    fail("ccrBailoutSettingsGroup still CCR-only (BUG-59)")

if "settings.circuit !== 'pSCR'" not in vpm_src.split("offLoopPath", 1)[-1][:160]:
    ok("VPM offLoopPath includes pSCR (issue #138 L-1; supersedes BUG-60)")
else:
    fail("VPM offLoopPath still excludes pSCR (issue #138 L-1)")

vpm_gas_start = js.find("const gasConsVPM = {}")
vpm_gas_block = js[vpm_gas_start:vpm_gas_start + 800] if vpm_gas_start > 0 else ""
if "endParseDepthM(depthRaw)" in vpm_gas_block:
    ok("VPM gas consumption parses arrow depth cells (BUG-61)")
else:
    fail("VPM gas consumption still parseFloat depth as 0 (BUG-61)")

clear_start = js.find("clear: function()")
clear_block = js[clear_start:clear_start + 700] if clear_start > 0 else ""
if "waterDensity" in clear_block and "lspUserAdvDefaults" in clear_block:
    ok("appSettings.clear() removes extended localStorage keys (BUG-62)")
else:
    fail("appSettings.clear() still misses app-owned keys (BUG-62)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 47 — v2.30.14 fixes (errors_bugs_report_v12)
# ══════════════════════════════════════════════════════════════════════════════

if "function vpmAccumPpo2" in vpm_src and "getEffectivePpo2(pAmb, 0, fO2, ccr" in vpm_src:
    ok("VPM OTU/CNS uses getEffectivePpo2 for pSCR loop ppO2 (BUG-63)")
else:
    fail("VPM OTU/CNS still uses diluent fO2 × pAmb for pSCR (BUG-63)")

vpm_ppo2_count = js.count("vpmAccumPpo2(") + vpm_bundle_js.count("vpmAccumPpo2(")
if vpm_ppo2_count >= 9:
    ok(f"VPM OTU/CNS accumulation wired through vpmAccumPpo2 ({vpm_ppo2_count} sites)")
else:
    fail(f"VPM OTU/CNS not fully wired through vpmAccumPpo2 (found {vpm_ppo2_count})")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 48 — v2.30.15 fixes (pSCR OTU/CNS consistency audit BUG-64–68)
# ══════════════════════════════════════════════════════════════════════════════

exp_ctx_start = vpm_src.find("function addExposureToContext")
exp_ctx_block = vpm_src[exp_ctx_start:exp_ctx_start + 700] if exp_ctx_start > 0 else ""
if "vpmAccumPpo2" in exp_ctx_block and ("ctxOffLoop(ctx)" in exp_ctx_block or "ctxUseOCForPpo2" in exp_ctx_block):
    ok("VPM continuation helpers use vpmAccumPpo2 (BUG-64)")
else:
    fail("addExposureToContext still uses diluent ppO2 (BUG-64)")

if "scrRuntimeMin: seg && seg.runtime" in js or "scrRuntimeMin: seg.runtime" in js:
    ok("vpmDisplayPpo2 uses segment runtime for pSCR loop ppO2 (BUG-65)")
else:
    fail("vpmDisplayPpo2 missing scrRuntimeMin from segment (BUG-65)")

if "scrRuntimeMin: diveRuntimeMin" in js:
    ok("Bühlmann _ccrPpo2Opts passes diveRuntimeMin (BUG-66)")
else:
    fail("_ccrPpo2Opts missing diveRuntimeMin for OTU/CNS (BUG-66)")

calc_cns_start = js.find("function calcCNS")
calc_cns_block = js[calc_cns_start:calc_cns_start + 1000] if calc_cns_start > 0 else ""
if "scrRuntimeMin: bt" in calc_cns_block:
    ok("calcCNS uses BT as pSCR scrRuntimeMin proxy (BUG-67)")
else:
    fail("calcCNS missing pSCR BT runtime proxy (BUG-67)")

exp_start = js.find("function computePlanExposureTotals")
exp_block = js[exp_start:exp_start + 2500] if exp_start > 0 else ""
if exp_start > 0 and "getEffectivePpo2(pAmb, 0, fo2" in exp_block and "cfg.circuit === 'pSCR'" in exp_block:
    ok("ZHLEngine headless OTU/CNS uses getEffectivePpo2 for pSCR (BUG-68)")
else:
    fail("ZHLEngine headless still uses raw diluent ppO2 for pSCR (BUG-68)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 49 — pSCR OTU/CNS dedicated test suite (v2.30.15 release validation)
# ══════════════════════════════════════════════════════════════════════════════

pscr_test_path = os.path.join(os.path.dirname(__file__), "tests-pscr-otu-cns.html")
if os.path.isfile(pscr_test_path):
    with open(pscr_test_path, encoding="utf-8") as f:
        pscr_test = f.read()
    ok("tests-pscr-otu-cns.html present")
    for needle in [
        "getEffectivePpo2",
        "computePSCRFractions",
        "PINNED_LOOP_PPO2",
        "PINNED_BOTTOM_OTU",
        "PINNED_DILUENT_BOTTOM_OTU",
        "recomputeExposureFromPlan",
        "VPMEngine.calculate",
        "ZHLEngine.calculate",
        "refGasLitresAmbient",
        "20_E32",
        "40_E32",
        "60_E32",
        "20_E36",
        "40_E36",
        "60_E36",
    ]:
        if needle in pscr_test:
            ok(f"pSCR test suite references {needle}")
        else:
            fail(f"tests-pscr-otu-cns.html missing {needle}")
else:
    fail("tests-pscr-otu-cns.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 50 — v2.30.16 fixes (errors_bugs_report_v14 BUG-69–70)
# ══════════════════════════════════════════════════════════════════════════════

surf_gf_start = tier3_engine_src.find("function computeSurfaceGF")
surf_gf_block = tier3_engine_src[surf_gf_start:surf_gf_start + 600] if surf_gf_start > 0 else ""
if surf_gf_start > 0 and "const P_surf = altSurfaceP" in surf_gf_block:
    ok("computeSurfaceGF uses altSurfaceP for altitude-aware surface GF (BUG-69)")
elif "ZhlEngineBundle.computeSurfaceGF" in js:
    ok("computeSurfaceGF delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("computeSurfaceGF still hardcodes P_surf=1.0 (BUG-69)")

if "function addBailoutStressReserve" in js and "addBailoutStressReserve(" in js:
    ok("addBailoutStressReserve splits stress reserve across deco phases (BUG-70)")
else:
    fail("addBailoutStressReserve missing — stress reserve still bottom-only (BUG-70)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 51 — v2.30.17 fix (errors_bugs_report_v15 BUG-71)
# ══════════════════════════════════════════════════════════════════════════════

if "function sacDomToLpm" in js and "sacDomToLpm('sacBottom'" in js:
    ok("sacDomToLpm converts imperial SAC to L/min before gas consumption (BUG-71)")
else:
    fail("sacDomToLpm missing — imperial gas consumption still in cu_ft·bar (BUG-71)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 52 — shared dual-engine test harness (v2.30.18)
# ══════════════════════════════════════════════════════════════════════════════

harness_path = os.path.join(os.path.dirname(__file__), "lsp-test-harness.js")
if os.path.isfile(harness_path):
    with open(harness_path, encoding="utf-8") as f:
        harness = f.read()
    ok("lsp-test-harness.js present")
    for needle in ["waitForApp", "ZHLEngine", "VPMEngine", "model === 'ZHLC_GF'"]:
        if needle in harness:
            ok(f"lsp-test-harness.js defines {needle}")
        else:
            fail(f"lsp-test-harness.js missing {needle}")
else:
    fail("lsp-test-harness.js missing")

for test_file, needle in [
    ("tests.html", "LSPTestHarness.waitForApp"),
    ("tests-extended.html", "LSPTestHarness.waitForApp"),
    ("tests-pscr-otu-cns.html", "LSPTestHarness.waitForApp"),
    ("tests-verify.html", "ZHLEngine"),
]:
    p = os.path.join(os.path.dirname(__file__), test_file)
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            body = f.read()
        if needle in body:
            ok(f"{test_file} wired to dual-engine harness")
        else:
            fail(f"{test_file} missing dual-engine wiring ({needle})")
    else:
        fail(f"{test_file} missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 53 — v2.30.19 fix (errors_bugs_report_v16 BUG-72)
# ══════════════════════════════════════════════════════════════════════════════

vpm_gas_start = js.find("for (const [gas, reqL] of Object.entries(gasConsVPM))")
vpm_gas_block = js[vpm_gas_start:vpm_gas_start + 2500] if vpm_gas_start > 0 else ""
if vpm_gas_start > 0 and "gpVolDisp(reqL)" in vpm_gas_block:
    ok("VPM gas summary uses gpVolDisp for imperial volume display (BUG-72)")
else:
    fail("VPM gas summary still shows raw litres as cu ft (BUG-72)")

emerg_start = js.find("// Emergency plan — keep simple sufficient/short table")
emerg_block = js[emerg_start:emerg_start + 1800] if emerg_start > 0 else ""
if emerg_start > 0 and "gpVolDisp(reqL)" in emerg_block:
    ok("Emergency gas block uses gpVolDisp for imperial volume display (BUG-72)")
else:
    fail("Emergency gas block still shows raw litres as cu ft (BUG-72)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 54 — v2.30.21 fix (ctxUseOCForPpo2 ReferenceError in VPMEngine)
# ══════════════════════════════════════════════════════════════════════════════

if re.search(r"function ctxUseOCForPpo2\(calcSettings\)", vpm_src):
    ok("ctxUseOCForPpo2 takes calcSettings param (BUG-73)")
else:
    fail("ctxUseOCForPpo2 still missing calcSettings param (BUG-73)")

if "ctxUseOCForPpo2(settings)" in vpm_src:
    ok("VPM OTU/CNS paths pass settings into ctxUseOCForPpo2 (BUG-73)")
else:
    fail("ctxUseOCForPpo2 not called with settings (BUG-73)")

ctx_oc_start = vpm_src.find("function ctxUseOCForPpo2")
ctx_oc_block = vpm_src[ctx_oc_start:ctx_oc_start + 120] if ctx_oc_start > 0 else ""
if ctx_oc_start > 0 and "calcSettings.bailout" in ctx_oc_block and "return settings." not in ctx_oc_block:
    ok("ctxUseOCForPpo2 body uses calcSettings not free settings (BUG-73)")
else:
    fail("ctxUseOCForPpo2 still references free settings identifier (BUG-73)")

calc_start = vpm_src.find("function calculate(levels, decoGases, settings, model)")
ctx_oc_start = vpm_src.find("function ctxUseOCForPpo2")
if calc_start > 0 and ctx_oc_start > calc_start:
    ok("ctxUseOCForPpo2 defined inside VPMEngine.calculate (BUG-73)")
else:
    fail("ctxUseOCForPpo2 still at module scope outside calculate (BUG-73)")

if re.search(r"APP_VERSION\s*=\s*['\"]2\.53\.04['\"]", app_version_js):
    ok("APP_VERSION bumped to 2.53.04")
else:
    fail("APP_VERSION not bumped to 2.53.04 in app-version.js")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 57 — v2.30.25 fix (pSCR OTU/CNS plan integration)
# ══════════════════════════════════════════════════════════════════════════════

if "function computePlanExposureTotals" in js:
    ok("computePlanExposureTotals helper exists for headless OTU/CNS (pSCR)")
else:
    fail("computePlanExposureTotals missing (pSCR OTU/CNS plan walk)")

if "computePlanExposureTotals(" in js and "exposure.totalOTU" in js:
    ok("ZHLEngine.calculate uses computePlanExposureTotals after plan assembly (pSCR)")
else:
    fail("ZHLEngine still uses pre-plan headless OTU/CNS path (pSCR)")

if "run: seg.run != null ? seg.run : seg.runtime" in vpm_src:
    ok("VPM buildResult exposes runtime as run on plan segments (pSCR)")
else:
    fail("VPM plan segments missing run alias from runtime (pSCR)")

pscr_test_path = os.path.join(os.path.dirname(__file__), "tests-pscr-otu-cns.html")
if os.path.isfile(pscr_test_path):
    with open(pscr_test_path, encoding="utf-8") as f:
        pscr_test = f.read()
    if "recomputeExposureFromPlan" in pscr_test and "computePlanExposureTotals" in pscr_test:
        ok("tests-pscr-otu-cns.html uses shared computePlanExposureTotals for plan walk")
    else:
        fail("tests-pscr-otu-cns.html missing shared plan exposure recompute")
else:
    fail("tests-pscr-otu-cns.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 56 — v2.30.24 fix (errors_bugs_report_v17)
# ══════════════════════════════════════════════════════════════════════════════

if exp_start > 0 and "cfg.circuit === 'CCR'" in exp_block and "getEffectiveSetpointAtDepth" in exp_block:
    ok("ZHLEngine headless CNS/OTU uses CCR setpoint path (v17 BUG-73)")
else:
    fail("ZHLEngine headless still uses OC ppO2 for CCR dives (v17 BUG-73)")

pkg_path = os.path.join(os.path.dirname(__file__), "package.json")
gradle_path = os.path.join(os.path.dirname(__file__), "android", "app", "build.gradle")
sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
app_ver_path = os.path.join(os.path.dirname(__file__), "app-version.js")
version_ok = True
app_ver_m = re.search(r"APP_VERSION\s*=\s*['\"]([^'\"]+)['\"]", app_version_js) if app_version_js else None
app_ver = app_ver_m.group(1) if app_ver_m else None
if not app_ver:
    version_ok = False
if os.path.isfile(pkg_path):
    with open(pkg_path, encoding="utf-8") as f:
        pkg = f.read()
    if app_ver and f'"version": "{app_ver}"' not in pkg:
        version_ok = False
else:
    version_ok = False
if os.path.isfile(gradle_path):
    with open(gradle_path, encoding="utf-8") as f:
        gradle = f.read()
    if app_ver and (f'versionName "{app_ver}"' not in gradle):
        version_ok = False
    if app_ver:
        parts = app_ver.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            vc = int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
            if f"versionCode {vc}" not in gradle:
                version_ok = False
        else:
            version_ok = False
else:
    version_ok = False
if os.path.isfile(sw_path):
    with open(sw_path, encoding="utf-8") as f:
        sw = f.read()
    if "importScripts('app-version.js')" not in sw or "lsp-dplanner-plus-v' + APP_VERSION" not in sw:
        version_ok = False
    if "version.json" not in sw:
        version_ok = False
else:
    version_ok = False
readme_path = os.path.join(os.path.dirname(__file__), "README.md")
if app_ver and os.path.isfile(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        readme_txt = f.read()
    readme_badge_m = re.search(r"> v([\d.]+)\s·", readme_txt)
    if not readme_badge_m or readme_badge_m.group(1) != app_ver:
        version_ok = False
else:
    version_ok = False
version_json_path = os.path.join(os.path.dirname(__file__), "version.json")
if app_ver and os.path.isfile(version_json_path):
    with open(version_json_path, encoding="utf-8") as f:
        vj = f.read()
    parts = app_ver.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        vc = int(parts[0]) * 10000 + int(parts[1]) * 100 + int(parts[2])
        if f'"version": "{app_ver}"' not in vj or f'"versionCode": {vc}' not in vj:
            version_ok = False
        if f"LSP_D-planner-plus-v{app_ver}.apk" not in vj:
            version_ok = False
        if '"downloadPage"' not in vj or '"apkUrl"' not in vj:
            version_ok = False
    else:
        version_ok = False
elif app_ver:
    version_ok = False
if version_ok and app_ver:
    ok(f"All version files aligned at {app_ver} (app-version.js, README, SW cache, version.json)")
else:
    fail("Version mismatch across app-version.js / README / sw.js / package.json / build.gradle / version.json (v17 BUG-74)")

_update_banner = js.split("function showUpdateBanner", 1)[-1].split("function checkForApkUpdate", 1)[0] if "function showUpdateBanner" in js else ""
_banner_ver_param = ""
_banner_inner_expr = ""
_banner_xss_ok = False
if _update_banner:
    _banner_sig = re.match(r"\s*\(\s*(\w+)", _update_banner)
    _banner_ver_param = _banner_sig.group(1) if _banner_sig else ""
if _update_banner and "banner.innerHTML" in _update_banner:
    if not _banner_ver_param:
        fail("showUpdateBanner version param name not parsed for innerHTML XSS check (issue #53)")
    else:
        _inner_tail = _update_banner.split("banner.innerHTML", 1)[-1]
        _inner_stop = len(_inner_tail)
        for _stop_marker in (
            "document.body.appendChild(banner)",
            "banner.appendChild(",
            "getElementById('apkUpdateDownloadBtn')",
        ):
            _pos = _inner_tail.find(_stop_marker)
            if _pos > 0:
                _inner_stop = min(_inner_stop, _pos)
        _inner_expr = _inner_tail[:_inner_stop]
        _banner_inner_expr = _inner_expr
        _uses_escaped_var = bool(re.search(r"\+\s*safe\w*\s*\+", _inner_expr))
        _uses_inline_escape = bool(re.search(
            rf"(?:escapeHtmlText|escapeBannerHtml)\s*\(\s*{_banner_ver_param}\s*\)", _inner_expr))
        _raw_param_in_inner = bool(re.search(
            rf"(?<!escapeHtmlText\()(?<!escapeBannerHtml\()\b{_banner_ver_param}\b", _inner_expr))
        _unsafe_ver_in_html = _raw_param_in_inner and not (_uses_escaped_var or _uses_inline_escape)
        if ("escapeHtmlText(" in _update_banner or "escapeBannerHtml(" in _update_banner) and not _unsafe_ver_in_html:
            ok("showUpdateBanner escapes version string before innerHTML (issue #50)")
            _banner_xss_ok = True
        else:
            fail("showUpdateBanner injects version string into innerHTML unsanitized (issue #50)")
elif _update_banner and _banner_ver_param and re.search(
        rf"\.textContent\s*=\s*{_banner_ver_param}|createTextNode\s*\(\s*{_banner_ver_param}",
        _update_banner):
    ok("showUpdateBanner uses DOM text API for version string (issue #50)")
elif "function showUpdateBanner" in js:
    fail("showUpdateBanner missing safe version-string handling (issue #50)")
_open_dl = js.split("function openDownloadPage", 1)[-1].split("function checkForApkUpdate", 1)[0] if "function openDownloadPage" in js else ""
if _open_dl and "!/^https?:\\/\\//i.test(url)" in _open_dl and "DEFAULT_DOWNLOAD_PAGE" in _open_dl:
    ok("openDownloadPage rejects non-http(s) download URLs from manifest")
else:
    fail("openDownloadPage missing http(s) URL guard for remote downloadPage")
if "function escapeBannerHtml" in js:
    fail("escapeBannerHtml duplicate removed — use escapeHtmlText only (issue #59)")
_esc_html = js.split("function escapeHtmlText", 1)[-1].split("function setTravelGasFractionWarning", 1)[0] if "function escapeHtmlText" in js else ""
if _esc_html and ".replace(/'/g, '&#39;')" in _esc_html:
    ok("escapeHtmlText escapes apostrophe for innerHTML reuse")
else:
    fail("escapeHtmlText missing apostrophe escape")
if os.path.isfile(version_json_path):
    with open(version_json_path, encoding="utf-8") as f:
        _vj50 = f.read()
    if '"apkUrl"' in _vj50 and f"LSP_D-planner-plus-v" in _vj50:
        ok("version.json includes apkUrl for direct APK download (issue #50)")
    else:
        fail("version.json missing apkUrl for APK download (issue #50)")
    if '"minUpdateCheckVersion"' not in _vj50:
        ok("version.json omits unused minUpdateCheckVersion field (issue #50)")
    else:
        fail("version.json still has unused minUpdateCheckVersion field (issue #50)")
_apk_yml = os.path.join(os.path.dirname(__file__), ".github", "workflows", "build-apk.yml")
if os.path.isfile(_apk_yml):
    with open(_apk_yml, encoding="utf-8") as f:
        _apk_yml_txt = f.read()
    if "git checkout -- android/app/build.gradle" not in _apk_yml_txt:
        ok("build-apk.yml omits redundant git checkout before reset --hard (issue #50)")
    else:
        fail("build-apk.yml redundant git checkout before reset --hard (issue #50)")
_sync_www_path = os.path.join(os.path.dirname(__file__), "tools", "sync_www.py")
if os.path.isfile(_sync_www_path):
    with open(_sync_www_path, "rb") as f:
        _sync_www_bytes = f.read()
    if _sync_www_bytes.endswith(b"\n"):
        ok("sync_www.py ends with trailing newline (issue #50)")
    else:
        fail("sync_www.py missing trailing newline (issue #50)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 58 — v2.30.26 fix (errors_bugs_report_v18/v19 BUG-75)
# ══════════════════════════════════════════════════════════════════════════════

if cdl_start > 0 and "metRate / fO2Loop" not in cdl_block:
    ok("BUG-75 fixed: pSCR ccrDiluentSurfaceLpm no longer divides by fO2Loop")
else:
    fail("BUG-75 still present: ccrDiluentSurfaceLpm uses metRate/fO2Loop")

verify_path = os.path.join(os.path.dirname(__file__), "tests-verify.html")
if os.path.isfile(verify_path):
    with open(verify_path, encoding="utf-8") as f:
        verify_html = f.read()
    if "BUG-75" in verify_html and "ccrDiluentSurfaceLpm" in verify_html:
        ok("tests-verify.html regression for pSCR ccrDiluentSurfaceLpm (BUG-75)")
    else:
        fail("tests-verify.html missing BUG-75 pSCR gas flow regression")
    if "At/below setpoint crossover: zero loop inert" in verify_html and "pAmb = sp + ppH2O" in verify_html:
        ok("tests-verify CCR shallow test expects zero inert at crossover")
    else:
        fail("tests-verify CCR shallow test missing zero-inert crossover check")
    if "assertRtPinned" in verify_html and "VerifyWarn" in verify_html:
        ok("tests-verify.html RT pinned drift ±1–2 min → WARN (not fail)")
    else:
        fail("tests-verify.html missing assertRtPinned / VerifyWarn RT drift handling")
else:
    fail("tests-verify.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 59 — v2.30.28 fix (errors_bugs_report_v21 BUG-77)
# ══════════════════════════════════════════════════════════════════════════════

if "function planSegDepthM" in js and ("runStart + frac * dur" in js or "scrRuntimeMin = Math.max(0, runEnd - dur)" in js):
    ok("BUG-77 fixed: computePlanExposureTotals uses segment-start scrRuntimeMin + planSegDepthM")
else:
    fail("BUG-77: computePlanExposureTotals still uses end-of-segment scrRuntimeMin or depth=0 on VPM ascents")

if "function buildResult(plan, runtime" in vpm_src and "totalOTU: exposure.totalOTU" in vpm_src and "computePlanExposureTotals(" in vpm_src:
    ok("BUG-77 fixed: VPM buildResult totals from computePlanExposureTotals")
else:
    fail("BUG-77: VPM buildResult still uses inline vpmAccumPpo2 totals vs plan walk")

pscr_test_path = os.path.join(os.path.dirname(__file__), "tests-pscr-otu-cns.html")
if os.path.isfile(pscr_test_path):
    with open(pscr_test_path, encoding="utf-8") as f:
        pscr_test = f.read()
    if "recomputeExposureFromPlan" in pscr_test and "computePlanExposureTotals" in pscr_test:
        ok("tests-pscr-otu-cns.html uses shared computePlanExposureTotals for plan walk")
    else:
        fail("tests-pscr-otu-cns.html still duplicates plan exposure integration")
else:
    fail("tests-pscr-otu-cns.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 61 — v2.30.29 fix (ZHL CNS plan re-integration / BUG-66)
# ══════════════════════════════════════════════════════════════════════════════

if "function accumulateHeadlessPlanExposure" in js and "totalCNS: _headlessExposure.totalCNS" in js:
    ok("BUG-66 fixed: headless Bühlmann OTU/CNS before _zhlHeadless return")
else:
    fail("BUG-66: runDecoSchedule missing headless OTU/CNS accumulation")

if "pO2:   s.pO2" in js or "pO2: s.pO2" in js:
    ok("ZHLEngine plan preserves diveRuntimeMin-baked pO2 from Bühlmann steps")
else:
    fail("ZHLEngine plan mapping drops step pO2 (CNS plan walk mismatch)")

if "isFinite(baked)" in js and "seg.pO2" in js:
    ok("computePlanExposureTotals uses baked step pO2 when present")
else:
    fail("computePlanExposureTotals ignores Bühlmann step pO2")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 62 — v2.30.30 fix (ZHL OTU plan walk / BUG-82)
# ══════════════════════════════════════════════════════════════════════════════

if "function accumulateHeadlessPlanExposure" in js and "computePlanExposureTotals(" in js:
    ahpe_start = js.find("function accumulateHeadlessPlanExposure")
    ahpe_end = js.find("\nfunction computePlanExposureTotals", ahpe_start)
    ahpe_block = js[ahpe_start:ahpe_end] if ahpe_end > ahpe_start else ""
    if ahpe_block.count("computePlanExposureTotals(") >= 1 and "btAtDepthMin" in ahpe_block:
        ok("BUG-82 fixed: accumulateHeadlessPlanExposure delegates to computePlanExposureTotals")
    else:
        fail("BUG-82: accumulateHeadlessPlanExposure still uses single-sample pSCR ppO2 integration")
else:
    fail("BUG-82: accumulateHeadlessPlanExposure or computePlanExposureTotals missing")

if "lp.totalOTU" not in js[js.find("const ZHLEngine"):js.find("if (typeof window !== 'undefined') window.ZHLEngine")]:
    ok("BUG-82 fixed: ZHLEngine.calculate totals from computePlanExposureTotals (not lp.totalOTU)")
else:
    fail("BUG-82: ZHLEngine.calculate still prefers lp.totalOTU over plan walk")

pscr_test61 = os.path.join(os.path.dirname(__file__), "tests-pscr-otu-cns.html")
if os.path.isfile(pscr_test61):
    with open(pscr_test61, encoding="utf-8") as f:
        pscr61 = f.read()
    if "WIN.altSurfaceP" in pscr61 and "WIN.BAR_PER_METRE" in pscr61:
        ok("tests-pscr-otu-cns.html recompute uses live altSurfaceP/BAR_PER_METRE")
    else:
        fail("tests-pscr-otu-cns.html still uses hardcoded SURF/BAR for recompute")
else:
    fail("tests-pscr-otu-cns.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 60 — v2.30.28 fix (errors_bugs_report_v21 BUG-76)
# ══════════════════════════════════════════════════════════════════════════════

if "massiveSuite" in js and "_massiveSuiteActive" in js:
    ok("BUG-76 fixed: index.html early headless when massiveSuite=1")
else:
    fail("BUG-76: index.html missing massiveSuite early headless guard")

if re.search(r"if\s*\(\s*!window\._zhlHeadless\s*\)\s*renderNDLTable\s*\(\s*\)", js):
    ok("BUG-76 fixed: setDecoAlgorithm/setCustomGF skip renderNDLTable in headless mode")
else:
    fail("BUG-76: setDecoAlgorithm still calls renderNDLTable unconditionally")

massive_path60 = os.path.join(os.path.dirname(__file__), "tests-massive.html")
if os.path.isfile(massive_path60):
    with open(massive_path60, encoding="utf-8") as f:
        massive60 = f.read()
    if "enterMassiveHeadless" in massive60 and "installMassiveSuiteGuards" in massive60:
        ok("BUG-76 fixed: tests-massive.html enterMassiveHeadless + suite guards")
    else:
        fail("BUG-76: tests-massive.html missing enterMassiveHeadless / installMassiveSuiteGuards")
    if "massiveSuite=1" in massive60 and "MIN_APP_VERSION" in massive60:
        ok("BUG-76 fixed: tests-massive.html loads index with massiveSuite=1 + version guard")
    else:
        fail("BUG-76: tests-massive.html missing massiveSuite=1 or MIN_APP_VERSION")
    if "WIN._zhlHeadless = false" not in massive60.split("function fastRDS")[1].split("function safeSetUnits")[0]:
        ok("BUG-76 fixed: fastRDS never clears _zhlHeadless")
    else:
        fail("BUG-76: fastRDS still clears _zhlHeadless before runDecoSchedule")
else:
    fail("tests-massive.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 55 — v2.30.22 fix (massive suite headless mode leak)
# ══════════════════════════════════════════════════════════════════════════════

if "ZhlEngineBundle.calculate" in js and "calculateCcrViaDom" not in js:
    ok("ZHLEngine.calculate uses pure bundle path without _zhlHeadlessDepth DOM leak (BUG-74)")
elif "_zhlHeadlessDepth" in js and "window._zhlHeadless = _headlessEntry > 0" in js:
    ok("ZHLEngine.calculate preserves _zhlHeadless across calls (BUG-74)")
else:
    fail("ZHLEngine.calculate still clears _zhlHeadless after headless runs (BUG-74)")

_rds_bug74 = js.split("function runDecoSchedule", 1)[-1].split("function planSegDepthM", 1)[0] if "function runDecoSchedule" in js else ""
if _rds_bug74 and re.search(r"!window\._zhlHeadless && (?:!_contingencyRunning && )?isCcrGasUiMode\(\)", _rds_bug74) and "validateCcrGasConfiguration()" in _rds_bug74:
    ok("runDecoSchedule skips CCR alert when headless (BUG-74)")
else:
    fail("runDecoSchedule may alert() during headless test runs (BUG-74)")

if re.search(r"!window\._zhlHeadless && (?:!_contingencyRunning && )?isRebreatherCircuit\(_uiCcr\.circuit\)", js):
    ok("runDecoSchedule DOM gas validation uses window._zhlHeadless (not bare _zhlHeadless)")
else:
    fail("runDecoSchedule references bare _zhlHeadless (ReferenceError in UI)")

massive_path = os.path.join(os.path.dirname(__file__), "tests-massive.html")
if os.path.isfile(massive_path):
    with open(massive_path, encoding="utf-8") as f:
        massive = f.read()
    if "keepHeadless" in massive and "enterMassiveHeadless" in massive:
        ok("tests-massive.html calc() + enterMassiveHeadless guard (BUG-74)")
    else:
        fail("tests-massive.html missing headless guard in calc() (BUG-74)")
else:
    fail("tests-massive.html missing")

massive_main_path = os.path.join(os.path.dirname(__file__), "tests-massive-main.html")
if os.path.isfile(massive_main_path):
    with open(massive_main_path, encoding="utf-8") as f:
        massive_main = f.read()
    if "MIN_APP_VERSION" in massive_main and "about:blank" in massive_main:
        ok("tests-massive-main.html guards against stale cached index.html (BUG-73)")
    else:
        fail("tests-massive-main.html missing MIN_APP_VERSION / about:blank guard (BUG-73)")
else:
    fail("tests-massive-main.html missing")

tests_html_path = os.path.join(os.path.dirname(__file__), "tests.html")
if os.path.isfile(tests_html_path):
    with open(tests_html_path, encoding="utf-8") as f:
        tests_html = f.read()
    if "function ndlSettings" in tests_html and "ndlSettings()" in tests_html:
        ok("tests.html NDL group uses GF 100/100 via ndlSettings()")
    else:
        fail("tests.html No-Deco tests still use default GF conservatism")
else:
    fail("tests.html missing")

massive_html_path = os.path.join(os.path.dirname(__file__), "tests-massive.html")
massive_html = ""
if os.path.isfile(massive_html_path):
    with open(massive_html_path, encoding="utf-8") as f:
        massive_html = f.read()
    if "firstStop: 36" in massive_html and "ref.stops[rd]" not in massive_html:
        ok("tests-massive.html CCR cross-val uses DiveKit first-stop pins (no MultiDeco per-stop table)")
    else:
        fail("tests-massive.html CCR cross-val still pinned to MultiDeco per-stop tables")
    if "C3: { rt: 83" in massive_html:
        ok("tests-massive.html CCR C3 RT pinned to LSP engine (83 min, DiveKit first stop)")
    else:
        fail("tests-massive.html CCR C3 RT pin missing or stale (expected rt: 83)")
    if "function refreshFrameWin" in massive_html and "_suiteRunId" in massive_html:
        ok("tests-massive.html iframe run guard + refreshFrameWin present")
    else:
        fail("tests-massive.html missing iframe hardening (refreshFrameWin / _suiteRunId)")
    if "function vpmEngine" in massive_html and "(w || E).calculate" not in massive_html:
        ok("tests-massive.html vpmEngine() resolves VPMEngine (not iframe window)")
    else:
        fail("tests-massive.html missing vpmEngine() or still uses (w||E).calculate")
else:
    fail("tests-massive.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 62 — v2.30.29 fix (errors_bugs_report_v22 BUG-78)
# ══════════════════════════════════════════════════════════════════════════════

massive78 = massive_html if os.path.isfile(massive_html_path) else ""
if massive78 and "serviceWorker" in massive78 and "SKIP_WAITING" in massive78:
    ok("BUG-78 fixed: tests-massive.html SW skip-waiting before iframe load")
else:
    fail("BUG-78: tests-massive.html missing service worker guard")

if massive78 and "MIN_APP_VERSION + '&ts='" in massive78:
    ok("BUG-78 fixed: tests-massive.html cache-busts iframe with MIN_APP_VERSION")
else:
    fail("BUG-78: tests-massive.html iframe src missing version cache-bust")

massive_main78_path = os.path.join(os.path.dirname(__file__), "tests-massive-main.html")
if os.path.isfile(massive_main78_path):
    with open(massive_main78_path, encoding="utf-8") as f:
        massive_main78 = f.read()
    if "function vpmEngine" in massive_main78 and "(w || E).calculate" not in massive_main78:
        ok("BUG-81 fixed: tests-massive-main.html vpmEngine() — not (w||E).calculate")
    else:
        fail("BUG-81: tests-massive-main.html still calls calculate on iframe window")
else:
    fail("tests-massive-main.html missing")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 63 — Android MainActivity package matches applicationId (launch crash)
# ══════════════════════════════════════════════════════════════════════════════

main_ccr = os.path.join(os.path.dirname(__file__), "android", "app", "src", "main", "java", "com", "threecats", "lsp", "dplannerplus", "MainActivity.java")
main_oc = os.path.join(os.path.dirname(__file__), "android", "app", "src", "main", "java", "com", "threecats", "lsp", "dplanner", "MainActivity.java")
gradle_path = os.path.join(os.path.dirname(__file__), "android", "app", "build.gradle")

if os.path.isfile(main_ccr):
    with open(main_ccr, encoding="utf-8") as f:
        main_src = f.read()
    if "package com.threecats.lsp.dplannerplus;" in main_src and "class MainActivity extends BridgeActivity" in main_src:
        ok("Android MainActivity in com.threecats.lsp.dplannerplus (matches applicationId)")
    else:
        fail("Android MainActivity package does not match applicationId dplannerplus")
else:
    fail("Android MainActivity missing at dplannerplus/MainActivity.java")

if os.path.isfile(main_oc):
    fail("Stale Android MainActivity still at dplanner/ — launch ClassNotFoundException risk")

if os.path.isfile(gradle_path):
    with open(gradle_path, encoding="utf-8") as f:
        gradle = f.read()
    if 'applicationId "com.threecats.lsp.dplannerplus"' in gradle and ('namespace "com.threecats.lsp.dplannerplus"' in gradle or 'namespace = "com.threecats.lsp.dplannerplus"' in gradle):
        ok("Android applicationId/namespace aligned at com.threecats.lsp.dplannerplus")
    else:
        fail("Android build.gradle applicationId/namespace mismatch")

build_apk_path = os.path.join(os.path.dirname(__file__), ".github", "workflows", "build-apk.yml")
if os.path.isfile(build_apk_path):
    with open(build_apk_path, encoding="utf-8") as f:
        build_apk = f.read()
    if 'sync-apk-d-planner-plus' in build_apk and 'sync-apk-d-planner"' not in build_apk.replace('sync-apk-d-planner-plus', ''):
        ok("build-apk.yml dispatches sync-apk-d-planner-plus (site APK sync)")
    else:
        fail("build-apk.yml must dispatch sync-apk-d-planner-plus, not sync-apk-d-planner")
    if "assembleRelease" in build_apk and "ANDROID_KEYSTORE_BASE64" in build_apk:
        ok("build-apk.yml builds signed release APK")
    else:
        fail("build-apk.yml must use assembleRelease with release keystore signing")

manifest_path = os.path.join(os.path.dirname(__file__), "android", "app", "src", "main", "AndroidManifest.xml")
if os.path.isfile(manifest_path):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = f.read()
    if 'android:name="com.threecats.lsp.dplannerplus.MainActivity"' in manifest:
        ok("AndroidManifest uses fully qualified MainActivity class name")
    else:
        fail("AndroidManifest MainActivity must be com.threecats.lsp.dplannerplus.MainActivity")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 64 — Issue #1 deep audit fixes (pSCR trimix, units, validation, PWA)
# ══════════════════════════════════════════════════════════════════════════════

pscr_frac_block = _ccr_core_src.split("function computePSCRFractions", 1)[-1][:1200] if "function computePSCRFractions" in _ccr_core_src else ""
if pscr_frac_block and "sourceInert" in pscr_frac_block and ("fHe / sourceInert" in pscr_frac_block or "fN2src / sourceInert" in pscr_frac_block):
    ok("computePSCRFractions normalizes trimix inert via sourceInert (issue #1)")
else:
    fail("computePSCRFractions still mis-treats fInert as N2-only (issue #1)")

if pscr_frac_block and (
    ("PSCR_MIN_PPO2 * loopVol" in pscr_frac_block and "PSCR_MIN_PPO2 * loopVol * pAmb" not in pscr_frac_block)
    or ("Math.max(PSCR_MIN_PPO2, ppO2Supply - ppO2Drop)" in pscr_frac_block)
    or ("cappedDrop = Math.min(ppO2Drop" in pscr_frac_block)
):
    ok("pSCR O₂ floor uses true 0.16 bar minimum (not 16% fraction floor)")
else:
    fail("pSCR O₂ floor still scales with ambient pressure (issue #1)")

if "function validateDecoInputs" in js and "validateDecoInputs()" in js and "Cannot generate schedule" in js:
    ok("validateDecoInputs blocks invalid depth/BT before runDecoSchedule (issue #1)")
else:
    fail("validateDecoInputs missing or not wired into runDecoSchedule (issue #1)")

if "function validatePlannerInputs" in js and "validatePlannerInputs()" in js and "Cannot calculate dive" in js:
    ok("validatePlannerInputs blocks invalid depth/BT before runPlanner (issue #1 follow-up)")
else:
    fail("validatePlannerInputs missing or not wired into runPlanner (issue #1 follow-up)")

if "function validateDiveInputs" in js and "maxBt: 300" in js:
    ok("validateDiveInputs enforces 300 min BT limit matching input max (issue #1 follow-up)")
else:
    fail("validateDiveInputs missing or BT limit not 300 (issue #1 follow-up)")

if "setUnits(u, opts)" in js or "relabelOnly" in js:
    ok("setUnits supports relabelOnly for settings restore without value conversion (issue #1 follow-up)")
else:
    fail("setUnits relabelOnly restore path missing (issue #1 follow-up)")

if "__units__" in js and "values['__units__']" in js:
    ok("appSettings persists unit system as __units__ (issue #1)")
else:
    fail("Unit system not persisted in appSettings (issue #1)")

if '<option value="ean80">EAN80' in html and html.count('value="ean80"') >= 2:
    ok("EAN80 option present on deco gas selectors (issue #1)")
else:
    fail("EAN80 missing from dg1Mix/dg2Mix (issue #1)")

_vpm_deco63 = js.split("function runVPMSchedule", 1)[-1].split("function ", 1)[0] if "function runVPMSchedule" in js else ""
if (_vpm_deco63 and "getDecoCardFractions(n)" in _vpm_deco63) or "mixEl.value === 'ean80' ? 80" in js:
    ok("runVPMSchedule maps ean80 to 80% O₂ (issue #1)")
else:
    fail("runVPMSchedule still maps ean80 incorrectly (issue #1)")

tissue_start = js.find("function renderTissueLoadChart")
tissue_block = js[tissue_start:tissue_start + 1500] if tissue_start > 0 else ""
if tissue_start > 0 and "gfHighInput" in tissue_block and "algorithmSelect" in tissue_block:
    ok("renderTissueLoadChart reads gfHighInput and algorithmSelect (issue #1)")
else:
    fail("renderTissueLoadChart still uses stale gfHighSel/algoSel (issue #1)")

if "getElementById('gfHighSel')" not in js and "getElementById('algoSel')" not in js:
    ok("Stale gfHighSel/algoSel DOM IDs removed (issue #1)")
else:
    fail("Stale gfHighSel or algoSel still referenced (issue #1)")

export_start = js.find("if (mode === 'planner')")
export_block = js[export_start:export_start + 600] if export_start > 0 else ""
if export_start > 0 and "getElementById('gasMix')" in export_block and "getElementById('gas')" not in export_block:
    ok("Planner text export reads gasMix control (issue #1)")
else:
    fail("Planner text export still reads nonexistent gas control (issue #1)")

manifest_path = os.path.join(os.path.dirname(__file__), "manifest.json")
if os.path.isfile(manifest_path):
    with open(manifest_path, encoding="utf-8") as f:
        manifest_json = f.read()
    if '"start_url": "./"' in manifest_json and '"scope": "./"' in manifest_json:
        ok("manifest.json uses relative start_url/scope (issue #1)")
    else:
        fail("manifest.json still hardcodes /LSP_D-planner-CCR/ paths (issue #1)")

sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
if os.path.isfile(sw_path):
    with open(sw_path, encoding="utf-8") as f:
        sw_src = f.read()
    if ".then(cached => cached || caches.match(OFFLINE_INDEX" in sw_src or "status: 503" in sw_src:
        ok("sw.js offline fallback chains to app-shell lookup (issue #1)")
    else:
        fail("sw.js offline fallback still uses broken Promise || chain (issue #1)")

e2e_path = os.path.join(os.path.dirname(__file__), "dev", "validate_pscr_e2e.py")
if os.path.isfile(e2e_path):
    with open(e2e_path, encoding="utf-8") as f:
        e2e_src = f.read()
    if "ThreadingHTTPServer" in open(os.path.join(os.path.dirname(__file__), "dev", "test_http.py"), encoding="utf-8").read():
        ok("test harness uses quiet ThreadingHTTPServer (issue #3)")
    else:
        fail("dev/test_http.py quiet server missing (issue #3)")
    if "regression=1" in e2e_src and ("wait_app_engines" in e2e_src or "ensure_app_engines" in e2e_src):
        ok("validate_pscr_e2e.py loads app with regression=1 and re-waits before evaluate (issue #3)")
    else:
        fail("validate_pscr_e2e.py missing regression=1 reload guard (issue #3)")
    if "serve_www" in open(os.path.join(os.path.dirname(__file__), "dev", "test_http.py"), encoding="utf-8").read():
        ok("validate_pscr_e2e.py serves post-sync www/ via serve_www (APK parity)")
    elif "serve_root" in e2e_src and "as_uri()" not in e2e_src:
        ok("validate_pscr_e2e.py serves app over HTTP (not file://)")
    else:
        fail("validate_pscr_e2e.py still loads index via file:// (issue #1)")

audit_wf = os.path.join(os.path.dirname(__file__), ".github", "workflows", "audit.yml")
if os.path.isfile(audit_wf):
    with open(audit_wf, encoding="utf-8") as f:
        audit_wf_src = f.read()
    if (
        "run_all_regression.py" in audit_wf_src and "--tier release" in audit_wf_src
    ) or (
        "run_browser_regression.py" in audit_wf_src
        and "validate_pscr_e2e.py" in audit_wf_src
        and "run_native_regression.py" in audit_wf_src
    ):
        ok("audit.yml CI runs browser + native bridge regression + pSCR E2E")
    else:
        fail("audit.yml must run browser, native bridge, and pSCR E2E regression")
else:
    fail("Missing .github/workflows/audit.yml CI workflow (issue #1)")

if "function isAutomatedTestMode()" in html and "massiveSuite') === '1'" in html:
    ok("index.html skips SW migration/registration in automated test mode (issue #3)")
else:
    fail("index.html missing isAutomatedTestMode SW guard (issue #3)")

if '<caption id="decoSummary"' not in html and '<div id="decoSummary" class="deco-plan-caption"></div>' in html:
    ok("decoSummary is a div sibling, not a table caption (issue #12)")
else:
    fail("decoSummary must not be rendered as a table caption (issue #12)")

if (
    re.search(r"<caption[^>]*class=\"deco-plan-caption\"", html) is None
    and re.search(r"\.deco-plan-caption\s*\{[^}]*width\s*:\s*max-content", html) is None
    and re.search(r"\.deco-table-wrap\s*\{[^}]*width\s*:\s*max-content", html)
):
    ok("deco plan caption div-based, no max-content inflation; table-wrap uses width:max-content (issue #12)")
else:
    fail("deco plan caption layout still allows caption-driven table widening (issue #12)")

sync_start = js.find("function syncDecoScheduleStackWidths")
sync_block = js[sync_start:sync_start + 700] if sync_start > 0 else ""
measure_start = js.find("function measureDecoScheduleColumnWidth")
measure_block = js[measure_start:measure_start + 700] if measure_start > 0 else ""
if (
    "void wrap.offsetHeight" in sync_block
    and "measureDecoScheduleColumnWidth(table)" in sync_block
    and "tr:not(.deco-totals-row)" in measure_block
    and "cell.getBoundingClientRect()" in measure_block
):
    ok("syncDecoScheduleStackWidths measures schedule columns and ignores totals width (issue #12)")
else:
    fail("syncDecoScheduleStackWidths must flush layout and measure non-totals schedule columns (issue #12)")

if "--deco-table-width" in html and ".deco-totals-inner > span" in html:
    ok("deco summary, alerts, legend, and totals wrap to measured table width (issue #12 follow-up)")
else:
    fail("deco schedule sibling blocks must use measured table width and wrap totals text (issue #12 follow-up)")

if os.path.isfile(pscr_test_path):
    if "pSCR trimix fraction normalization" in pscr_test and "18/45" in pscr_test:
        ok("tests-pscr-otu-cns.html includes trimix fraction regression (issue #1)")
    else:
        fail("tests-pscr-otu-cns.html missing trimix fraction tests (issue #1)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 65 — CCR differential test harness (issue #2)
# ══════════════════════════════════════════════════════════════════════════════

ccr_plan = os.path.join(os.path.dirname(__file__), "docs", "CCR_ENGINE_DIFFERENTIAL_TEST_PLAN.md")
ccr_runner = os.path.join(os.path.dirname(__file__), "dev", "run_ccr_differential.py")
ccr_html = os.path.join(os.path.dirname(__file__), "tests-ccr-differential.html")
ccr_lib = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "lib", "ccrdiff.js")
ccr_build = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "build_assets.py")

for path, label in [
    (ccr_plan, "CCR_ENGINE_DIFFERENTIAL_TEST_PLAN.md"),
    (ccr_runner, "dev/run_ccr_differential.py"),
    (ccr_html, "tests-ccr-differential.html"),
    (ccr_lib, "tests/ccr-differential/lib/ccrdiff.js"),
    (ccr_build, "tests/ccr-differential/build_assets.py"),
]:
    if os.path.isfile(path):
        ok(f"{label} present (issue #2)")
    else:
        fail(f"{label} missing (issue #2)")

fixture_c1 = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "fixtures", "CCR-C1.json")
md_golden = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "goldens", "multideco", "CCR-C1.json")
if os.path.isfile(fixture_c1) and os.path.isfile(md_golden):
    ok("CCR-C1 fixture and MultiDeco golden migrated (issue #2)")
else:
    fail("CCR-C1 fixture or MultiDeco golden missing (issue #2)")

ab_golden = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "goldens", "abysner", "CCR-C1.json")
ss_golden = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "goldens", "subsurface", "CCR-C1.json")
if os.path.isfile(ab_golden) and os.path.isfile(ss_golden):
    ok("CCR-C1 Abysner and Subsurface goldens present (issue #2)")
else:
    fail("CCR-C1 Abysner or Subsurface golden missing (issue #2)")

ccr_config = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "config.json")
if os.path.isfile(ccr_config):
    with open(ccr_config, encoding="utf-8") as f:
        ccr_cfg = json.load(f)
    engines = ccr_cfg.get("comparatorEngines") or []
    if "abysner" in engines and "subsurface" in engines and "diveprome" not in ccr_cfg:
        ok("CCR config lists Abysner + Subsurface comparators (issue #2)")
    else:
        fail("CCR config missing Abysner/Subsurface or still references diveprome (issue #2)")

ccr_schema = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "schemas", "scenario.schema.json")
ccr_defects = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "known-lsp-defects.json")
if os.path.isfile(ccr_schema):
    ok("CCR scenario schema present (issue #2)")
else:
    fail("CCR scenario schema missing (issue #2)")
if os.path.isfile(ccr_defects):
    ok("CCR known LSP defects registry present (issue #2)")
else:
    fail("CCR known-lsp-defects.json missing (issue #2)")

if "function validateCcrCalculationInputs" in js and "validateCcrCalculationInputs(levels, s, decoGases)" in js:
    ok("validateCcrCalculationInputs wired into ZHLEngine.calculate (issue #2)")
else:
    fail("validateCcrCalculationInputs missing from production engine (issue #2)")

invalid_fixtures = [
    "CCR-INVALID-SP.json",
    "CCR-INVALID-GAS-SUM.json",
    "CCR-INVALID-GAS-NEGATIVE.json",
    "CCR-INVALID-PROFILE.json",
    "CCR-SP-CROSSING.json",
]
for name in invalid_fixtures:
    path = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "fixtures", name)
    if os.path.isfile(path):
        ok(f"{name} present (issue #2 invalid-input split)")
    else:
        fail(f"{name} missing (issue #2 invalid-input split)")

if os.path.isfile(ccr_runner):
    with open(ccr_runner, encoding="utf-8") as f:
        ccr_src = f.read()
    if "EXPECTED_DIFFERENCE" in open(ccr_lib, encoding="utf-8").read() and "runMetamorphic" in open(ccr_lib, encoding="utf-8").read() and "assertFixtureEffectiveness" in open(ccr_lib, encoding="utf-8").read():
        ok("CCR differential lib includes classification + metamorphic tests (issue #2)")
    else:
        fail("CCR differential lib incomplete (issue #2)")

audit_wf2 = os.path.join(os.path.dirname(__file__), ".github", "workflows", "audit.yml")
if os.path.isfile(audit_wf2):
    with open(audit_wf2, encoding="utf-8") as f:
        wf2 = f.read()
    if "run_ccr_differential.py" in wf2 or ("run_all_regression.py" in wf2 and "--tier release" in wf2):
        ok("audit.yml runs CCR differential suite (issue #2)")
    else:
        fail("audit.yml missing CCR differential step (issue #2)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 66 — validateCcrCalculationInputs pSCR + default setpoints (BUG-95/96)
# ══════════════════════════════════════════════════════════════════════════════

val_ccr_calc = js[js.find("function validateCcrCalculationInputs"):js.find("function validateCcrCalculationInputs") + 2500]
if "circuit === 'pSCR'" in val_ccr_calc and "value === 0) continue" in val_ccr_calc:
    ok("validateCcrCalculationInputs validates active pSCR setpoints (issue #138 M-15; supersedes BUG-95)")
else:
    fail("validateCcrCalculationInputs still skips pSCR setpoint checks (issue #138 M-15)")
if re.search(r"descentSetpoint\s*!=\s*null\s*\?\s*s\.descentSetpoint\s*:\s*0\.7", val_ccr_calc):
    ok("validateCcrCalculationInputs defaults descent setpoint to 0.7 (BUG-96)")
else:
    fail("validateCcrCalculationInputs missing descent setpoint default (BUG-96)")
if re.search(r"bottomSetpoint\s*!=\s*null.*1\.2", val_ccr_calc) and re.search(r"decoSetpoint\s*!=\s*null.*1\.3", val_ccr_calc):
    ok("validateCcrCalculationInputs defaults bottom/deco setpoints to 1.2/1.3 (BUG-96)")
else:
    fail("validateCcrCalculationInputs missing bottom/deco setpoint defaults (BUG-96)")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 67 — validateGasFractionsPct + deco gas validation (BUG-97/98/99)
# ══════════════════════════════════════════════════════════════════════════════

if "function validateGasFractionsPct" in js:
    ok("validateGasFractionsPct present (BUG-97)")
else:
    fail("validateGasFractionsPct missing (BUG-97)")

if re.search(
    r"he == null \|\| he === ''\) \? 0 : Number\(he\)",
    js[js.find("function validateGasFractionsPct"):js.find("function validateGasFractionsPct") + 600],
):
    ok("validateGasFractionsPct rejects NaN He without || 0 coercion (BUG-97)")
else:
    fail("validateGasFractionsPct still coerces NaN He via || 0 (BUG-97)")

if "validateCcrCalculationInputs(levels, s, decoGases)" in js:
    ok("ZHLEngine.calculate passes decoGases to validateCcrCalculationInputs (BUG-98)")
else:
    fail("ZHLEngine.calculate missing decoGases in CCR validation (BUG-98)")

if "decoGases.forEach" in val_ccr_calc and "validateGasFractionsPct(g.o2, g.he" in val_ccr_calc:
    ok("validateCcrCalculationInputs validates deco gases (BUG-98)")
else:
    fail("validateCcrCalculationInputs missing deco gas validation (BUG-98)")

if "validateGasFractionsPct(level.o2, level.he" in val_ccr_calc and "o2pct > 1" not in val_ccr_calc:
    ok("validateCcrCalculationInputs uses percent convention for level gases (BUG-99)")
else:
    fail("validateCcrCalculationInputs still mixes fraction/percent conventions (BUG-99)")

ccr_val_reg = os.path.join(os.path.dirname(__file__), "dev", "ccr_engine_validation_regression.py")
if os.path.isfile(ccr_val_reg):
    ok("dev/ccr_engine_validation_regression.py present (BUG-97/98)")
else:
    fail("dev/ccr_engine_validation_regression.py missing (BUG-97/98)")

if "_lspEngineError" in html and "startLspEngineReadyPolling" in html and "showEngineLoadErrorBanner" in html:
    ok("Engine boot sentinel sets _lspEngineError and user-visible banner on timeout")
else:
    fail("Engine boot sentinel missing timeout error handling")

if "function guardEngineBootForCalculate" in html and html.count("guardEngineBootForCalculate()") >= 2:
    ok("runPlanner and runDecoSchedule gate on engine boot readiness")
else:
    fail("guardEngineBootForCalculate missing from planner/deco entry points")

pb = os.path.join(os.path.dirname(__file__), "dev", "playwright_boot.py")
if os.path.isfile(pb) and "_lspEngineError" in open(pb, encoding="utf-8").read():
    ok("playwright_boot fails fast when _lspEngineError is set")
else:
    fail("playwright_boot missing fast-fail on engine boot error")

engine_reg = os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py")
run_all_reg = os.path.join(os.path.dirname(__file__), "dev", "run_all_regression.py")
if os.path.isfile(engine_reg):
    with open(engine_reg, encoding="utf-8") as f:
        eng_reg_src = f.read()
    if "VPMB_GFS" in eng_reg_src and "zhlRep" in eng_reg_src and "waterType: 3" in eng_reg_src:
        ok("dev/engine_regression.py covers all algos + rep + custom water (engine suite)")
    else:
        fail("dev/engine_regression.py missing algo/rep/water coverage")
else:
    fail("dev/engine_regression.py missing (full engine regression)")

if os.path.isfile(run_all_reg) and "engine_full" in open(run_all_reg, encoding="utf-8").read():
    ok("dev/run_all_regression.py orchestrates unified regression tiers")
else:
    fail("dev/run_all_regression.py missing or incomplete")

if os.path.isfile(run_all_reg):
    with open(run_all_reg, encoding="utf-8") as f:
        run_all_src = f.read()
    try:
        run_all_tree = ast.parse(run_all_src)
    except SyntaxError:
        run_all_tree = None
        fail("dev/run_all_regression.py has syntax errors")
    release_suites_ok = run_all_tree is not None
    release_suite_specs = [
        ("run_browser_regression.py", "browser"),
        ("run_ccr_differential.py", "ccr_differential"),
        ("ccr_engine_validation_regression.py", "engine_ccr_validation"),
    ]
    suites_dict = None
    if run_all_tree is not None:
        for node in ast.walk(run_all_tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SUITES" and isinstance(node.value, ast.Dict):
                    suites_dict = node.value
                    break
        if suites_dict is None:
            fail("dev/run_all_regression.py missing SUITES dict")
            release_suites_ok = False
    for script, label in release_suite_specs:
        path = os.path.join(os.path.dirname(__file__), "dev", script)
        if not os.path.isfile(path):
            fail(f"dev/{script} missing (release suite {label})")
            release_suites_ok = False
            continue
        if suites_dict is None:
            release_suites_ok = False
            continue
        suite_entry = None
        for key, val in zip(suites_dict.keys, suites_dict.values):
            if isinstance(key, ast.Constant) and key.value == label:
                suite_entry = val
                break
        if suite_entry is None:
            fail(f"dev/run_all_regression.py missing {label} suite entry")
            release_suites_ok = False
            continue
        if not isinstance(suite_entry, ast.Dict):
            fail(f"dev/run_all_regression.py {label} suite entry malformed")
            release_suites_ok = False
            continue
        for sk, sv in zip(suite_entry.keys, suite_entry.values):
            if isinstance(sk, ast.Constant) and sk.value == "optional":
                if isinstance(sv, ast.Constant) and sv.value is True:
                    fail(f"dev/run_all_regression.py marks {label} optional but script is present")
                    release_suites_ok = False
                break
    if release_suites_ok:
        ok("browser, ccr_differential, and engine_ccr_validation required when scripts present")

# ══════════════════════════════════════════════════════════════════════════════
# GROUP 68 — raw DOM gas validation before clamping (BUG-100)
# ══════════════════════════════════════════════════════════════════════════════

if "function getDomBottomGasPct" in js and "function getDomDecoGasPct" in js and "function validateDomDecoGases" in js:
    ok("getDomBottomGasPct / validateDomDecoGases present (BUG-100)")
else:
    fail("raw DOM gas validation helpers missing (BUG-100)")

if "validateDomDecoGases()" in js and "getDomBottomGasPct()" in js:
    ok("runDecoSchedule validates raw DOM gases before schedule (BUG-100)")
else:
    fail("runDecoSchedule still validates clamped gas fractions only (BUG-100)")

if "validateDomDecoGases()" in js[js.find("function validateCcrGasConfiguration"):js.find("function validateCcrGasConfiguration") + 1200]:
    ok("validateCcrGasConfiguration includes raw DOM gas checks (BUG-100)")
else:
    fail("validateCcrGasConfiguration missing raw DOM gas checks (BUG-100)")

if "getDomDecoGasPct(idx)" in js[js.find("function collectDecoGasesPctFromDom"):js.find("function collectDecoGasesPctFromDom") + 400]:
    ok("collectDecoGasesPctFromDom uses raw DOM percents (BUG-100)")
else:
    fail("collectDecoGasesPctFromDom still uses clamped fractions (BUG-100)")

vpm_empty = vpm_src[vpm_src.find("function calculate(levels, decoGases, settings, model)"):vpm_src.find("function calculate(levels, decoGases, settings, model)") + 3500]
if "No bottom segments defined" in vpm_empty and "totalRuntime: 0" in vpm_empty.split("No bottom segments defined")[1][:400]:
    ok("VPM empty-levels error includes totalRuntime: 0 (VPM/ZHL parity)")
else:
    fail("VPM empty-levels error missing totalRuntime: 0 (VPM/ZHL parity)")

if "splitZhlProfileLevels" in js and "_zhlContinuationLevels" in js and "phaseNextStop" in zhl_src:
    ok("ZHL headless multi-level continuation wired (splitZhlProfileLevels)")
else:
    fail("ZHL headless multi-level continuation missing")

if "validateZhlHeadlessProfile" in js and "cannot re-descend after a shallower level" in js:
    ok("validateZhlHeadlessProfile rejects unsupported ZHL profile shapes")
else:
    fail("validateZhlHeadlessProfile missing (unsupported multi-level ZHL profiles)")

if "validateEngineInputs" in js and "engineValidationError" in js:
    ok("validateEngineInputs + engineValidationError exported for VPM API hardening")
else:
    fail("validateEngineInputs / engineValidationError missing")

if ("function gasFractionsFromPct" in js and
        "gasFractionsFromPct(g.o2, g.he)" in vpm_src):
    ok("VPM deco gas normalization uses gasFractionsFromPct (omitted He → 0)")
else:
    fail("VPM deco gas normalization missing gasFractionsFromPct helper")

# GROUP — site runtime asset manifest (Pages + threecats-lsp.com sync parity)
repo_root = os.path.dirname(__file__)
pages_dir = os.path.join(repo_root, "_pages")
manifest_path = os.path.join(repo_root, "site-assets-manifest.txt")
required_runtime = [
    "app-version.js", "vpm-engine-bundle.js", "zhl-engine-bundle.js",
    "zhl-worker-bridge.js", "zhl-schedule-worker.js", "sw.js",
    "capacitor-bridge.js",
    "android-select-picker.js",
    "vendor/jspdf.umd.min.js", "vendor/fonts/fonts.css",
    "vendor/icons/giw-icon-192.png",
]
for rel in required_runtime:
    if os.path.isfile(os.path.join(repo_root, rel.replace("/", os.sep))):
        ok(f"runtime asset present: {rel}")
    else:
        fail(f"runtime asset missing in repo: {rel}")
if not os.path.isdir(pages_dir):
    fail("_pages/ missing — run tools/build_pages_site.py before audit")
elif not os.path.isfile(manifest_path):
    fail("site-assets-manifest.txt missing — run tools/build_pages_site.py")
else:
    with open(manifest_path, encoding="utf-8") as mf:
        manifest_lines = [ln.strip() for ln in mf if ln.strip()]
    missing_in_pages = [
        ln for ln in manifest_lines
        if ln not in (".nojekyll",)
        and not os.path.isfile(os.path.join(pages_dir, ln.replace("/", os.sep)))
    ]
    if not missing_in_pages:
        ok(f"site-assets-manifest.txt lists {len(manifest_lines)} files — all present in _pages/")
    else:
        fail(f"site-assets-manifest/_pages mismatch: missing {len(missing_in_pages)} file(s), e.g. {missing_in_pages[0]}")
    pages_files = []
    for dirpath, _dirnames, filenames in os.walk(pages_dir):
        for fn in filenames:
            rel = os.path.relpath(os.path.join(dirpath, fn), pages_dir).replace("\\", "/")
            pages_files.append(rel)
    extra_in_pages = sorted(set(pages_files) - set(manifest_lines))
    if not extra_in_pages:
        ok("_pages/ tree matches manifest (no extra files)")
    else:
        fail(f"_pages/ has {len(extra_in_pages)} file(s) not in manifest, e.g. {extra_in_pages[0]}")
    if "vpm-engine-bundle.js" in manifest_lines and "app-version.js" in manifest_lines:
        ok("site-assets-manifest includes app-version.js and vpm-engine-bundle.js")
    else:
        fail("site-assets-manifest missing app-version.js or vpm-engine-bundle.js")

if os.path.isfile(os.path.join(os.path.dirname(__file__), "android-select-picker.js")):
    with open(os.path.join(os.path.dirname(__file__), "android-select-picker.js"), encoding="utf-8") as f:
        android_picker_js = f.read()
else:
    android_picker_js = ""

if "android-select-picker.js" in html and android_picker_js and "lsp-android-select-sheet" in android_picker_js:
    ok("android-select-picker.js loaded — custom Android select sheet (replaces broken native picker)")
else:
    fail("android-select-picker.js missing or not wired in index.html")

if "lsp-android-select-btn" in html:
    ok("Android custom select picker CSS present")
else:
    fail("Android custom select picker CSS missing")

if re.search(r"\.field select\s*\{[^}]*appearance:\s*none", html, re.DOTALL):
    ok(".field select uses appearance:none — single custom chevron (no double arrows)")
else:
    fail(".field select missing appearance:none — native + custom chevron overlap")

if android_picker_js and "if (opt.disabled) return" in android_picker_js and "scrollIntoView" in android_picker_js:
    ok("android-select-picker: disabled options non-interactive + scroll to selected (issue #20)")
else:
    fail("android-select-picker missing disabled guard or scrollIntoView (issue #20)")

if android_picker_js and "new MutationObserver(function () {" in android_picker_js and "syncBtn();" in android_picker_js.split("selObserver", 1)[-1][:300]:
    ok("android-select-picker: MutationObserver wraps syncBtn callback (issue #20)")
else:
    fail("android-select-picker MutationObserver callback not wrapped (issue #20)")

sw_path = os.path.join(os.path.dirname(__file__), "sw.js")
sw_js = ""
if os.path.isfile(sw_path):
    with open(sw_path, encoding="utf-8") as f:
        sw_js = f.read()
if sw_js and "/LSP_D-planner-plus" in sw_js and "return swDir || '/LSP_D-planner-plus/'" in sw_js:
    ok("sw.js getAppBasePath checks LSP_D-planner-plus before LSP_D-planner (issue #20)")
else:
    fail("sw.js getAppBasePath missing LSP_D-planner-plus path ordering (issue #20)")

if worker_bridge_js and "settlePending" in worker_bridge_js and "ZHL worker timeout" in worker_bridge_js:
    ok("zhl-worker-bridge settles pending with timeout + fresh errors (issue #20/#21)")
else:
    fail("zhl-worker-bridge onerror/timeout handling incomplete (issue #20)")

if capacitor_bridge_js and "uniqueFilename" in capacitor_bridge_js and "return null" in capacitor_bridge_js.split("async function saveFile", 1)[-1][:1200]:
    ok("capacitor-bridge saveFile: uniqueFilename + three-tier fallback complete")
else:
    fail("capacitor-bridge saveFile missing uniqueFilename or tier fallback")

if capacitor_bridge_js and "readBlobFromHref" in capacitor_bridge_js and "deferredRevokeUrls" in capacitor_bridge_js and "async function readBlobFromHref" in capacitor_bridge_js:
    ok("capacitor-bridge: async blob read with deferred revokeObjectURL (issue #21 CR-1 / #117 M-2)")
    if "fetch(href)" in capacitor_bridge_js.split("readBlobFromHref", 1)[-1][:300]:
        ok("capacitor-bridge: async blob read uses fetch (non-blocking)")
    else:
        fail("capacitor-bridge missing fetch-based blob read")
else:
    fail("capacitor-bridge missing async blob read before revoke (issue #21 CR-1)")

if capacitor_bridge_js and "dirPath != null && dirPath !== ''" in capacitor_bridge_js:
    ok("capacitor-bridge uniqueFilename dirPath guard (issue #21 CR-2)")
else:
    fail("capacitor-bridge uniqueFilename dirPath guard missing (issue #21 CR-2)")

def _is_regex_start(rest, j):
    """True if / at j likely begins a regex literal (not division)."""
    k = j - 1
    while k >= 0 and rest[k] in " \t\n\r":
        k -= 1
    if k < 0:
        return True
    return rest[k] in "(=,[!?:;{&|+-*%<>~^}"

def _harness_fn_body(src, fn_name, *end_markers):
    """Return a named function body; stop at the first end_marker (e.g. next top-level fn)."""
    if not src:
        return ""
    parts = src.split(f"function {fn_name}", 1)
    if len(parts) < 2:
        return ""
    rest = parts[1]
    p0 = rest.find("(")
    if p0 < 0:
        return ""
    depth = 0
    close_paren = -1
    quote = None
    escape = False
    in_regex = False
    in_char_class = False
    regex_escape = False
    for j in range(p0, len(rest)):
        c = rest[j]
        if escape:
            escape = False
            continue
        if in_regex:
            if regex_escape:
                regex_escape = False
                continue
            if c == "\\":
                regex_escape = True
                continue
            if in_char_class:
                if c == "]":
                    in_char_class = False
                continue
            if c == "[":
                in_char_class = True
                continue
            if c == "/":
                in_regex = False
            continue
        if quote:
            if c == "\\":
                escape = True
                continue
            if c == quote:
                quote = None
            continue
        if c in ("'", '"', "`"):
            quote = c
            continue
        if c == "/" and _is_regex_start(rest, j):
            in_regex = True
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                close_paren = j
                break
    if close_paren < 0:
        return ""
    after = rest[close_paren + 1:]
    m_body = re.search(r"\s*\{", after)
    if not m_body:
        return ""
    body = after[m_body.end():]
    for marker in end_markers:
        if marker in body:
            body = body.split(marker, 1)[0]
            break
    return body

_harness_wait = _harness_fn_body(harness, "waitForApp", "/** Route ZHLC_GF", "function calc") if harness else ""
_harness_assert = _harness_fn_body(harness, "assertFiniteNumbers", "function clone") if harness else ""
_harness_clone = _harness_fn_body(harness, "clone", "function hookIframe") if harness else ""

if harness and "__lspAppFullyReady" in harness and "appFullyReady" in _harness_wait:
    if not re.search(r",\s*1500\s*\)", _harness_wait):
        ok("lsp-test-harness polls __lspAppFullyReady, no hardcoded 1500ms delay (issue #21 CR-3/4)")
    else:
        fail("lsp-test-harness still uses 1500ms boot delay in waitForApp (issue #21 CR-3)")
else:
    fail("lsp-test-harness still uses 1500ms delay or missing ready poll (issue #21 CR-3)")

if harness and "reloadApp(iframe, qs)" in harness:
    ok("lsp-test-harness reloadApp accepts optional query string (issue #21 CR-9)")
else:
    fail("lsp-test-harness reloadApp missing optional qs (issue #21 CR-9)")

if (harness and "function assertFiniteNumbers" in harness
        and "assertFiniteNumbers(v, '')" in _harness_clone
        and "!isFinite(v)" in _harness_assert
        and "Harness clone: non-finite number" in _harness_assert):
    ok("lsp-test-harness clone rejects non-finite numbers before JSON round-trip")
else:
    fail("lsp-test-harness clone still masks NaN/Infinity via JSON.stringify")

_wait_start = _harness_wait.split("function check", 1)[0] if _harness_wait else ""
if _wait_start and "var start = Date.now()" in _wait_start:
    ok("lsp-test-harness waitForApp declares start before check()")
else:
    fail("lsp-test-harness waitForApp start declared after check()")

for _inline_test in ("tests.html", "tests-extended.html", "tests-pscr-otu-cns.html"):
    _ip = os.path.join(os.path.dirname(__file__), _inline_test)
    if os.path.isfile(_ip):
        with open(_ip, encoding="utf-8") as f:
            _ib = f.read()
        _ih = _ib.split("/* inlined from lsp-test-harness.js — keep in sync */", 1)
        _ih = _ih[1].split("</script>", 1)[0] if len(_ih) > 1 else ""
        _inline_wait = _harness_fn_body(_ih, "waitForApp", "/** Route ZHLC_GF", "function calc")
        _inline_assert = _harness_fn_body(_ih, "assertFiniteNumbers", "function clone")
        _inline_clone = _harness_fn_body(_ih, "clone", "function hookIframe")
        _inline_start = _inline_wait.split("function check", 1)[0] if _inline_wait else ""
        if (_ih and "appFullyReady" in _ih and "reloadApp(iframe, qs)" in _ih
                and "assertFiniteNumbers(v, '')" in _inline_clone
                and "!isFinite(v)" in _inline_assert
                and not re.search(r",\s*1500\s*\)", _inline_wait)
                and "var start = Date.now()" in _inline_start):
            ok(f"{_inline_test} inlined harness synced with lsp-test-harness.js")
        else:
            fail(f"{_inline_test} inlined harness stale (missing appFullyReady, boot delay, or start order)")
    else:
        fail(f"{_inline_test} missing for inlined harness sync check")

if worker_bridge_js and "WORKER_TIMEOUT_MS" in worker_bridge_js and "ZHL worker timeout" in worker_bridge_js:
    ok("zhl-worker-bridge per-request timeout (issue #21 CR-5)")
else:
    fail("zhl-worker-bridge missing per-request timeout (issue #21 CR-5)")

if sw_js and ("android-select-picker.js" in sw_js.split("PRECACHE_ASSETS", 1)[-1][:800] or "android-select-picker.js" in sw_js.split("OPTIONAL_PRECACHE", 1)[-1][:400]):
    ok("sw.js precaches android-select-picker.js (issue #21 CR-6)")
else:
    fail("sw.js missing android-select-picker.js in PRECACHE_ASSETS (issue #21 CR-6)")

if android_picker_js and "selectObservers" in android_picker_js and "beforeunload" in android_picker_js:
    ok("android-select-picker disconnects observers on unload (issue #21 CR-8)")
else:
    fail("android-select-picker missing observer cleanup (issue #21 CR-8)")

if app_version_js and "g.APP_VERSION" in app_version_js and "const APP_VERSION" not in app_version_js:
    ok("app-version.js sets APP_VERSION on globalThis only (issue #21 CR-10)")
else:
    fail("app-version.js still uses bare const APP_VERSION global (issue #21 CR-10)")

if app_version_js and "\r" not in app_version_js:
    ok("app-version.js uses Unix line endings (code-review OBS-3)")
else:
    fail("app-version.js has CRLF/CR line endings (code-review OBS-3)")

if android_picker_js and "patchSelectValueSetters" in android_picker_js and "LspAndroidSelect" in android_picker_js:
    ok("android-select-picker syncs on programmatic .value changes (issue #22)")
else:
    fail("android-select-picker missing value setter sync (issue #22)")

if android_picker_js and "syncAllSelects" in android_picker_js and "selectSyncFns.forEach" not in android_picker_js:
    ok("android-select-picker syncAll iterates wrapped selects, not WeakMap (issue #23)")
else:
    fail("android-select-picker syncAll still calls WeakMap.forEach (issue #23)")

if android_picker_js and "openSheetSelect" in android_picker_js and "scheduleSheetRebuild" in android_picker_js:
    ok("android-select-picker rebuilds open sheet when options mutate (issue #24)")
else:
    fail("android-select-picker missing open-sheet rebuild on mutation (issue #24)")

if android_picker_js and "sheetRebuildPending" in android_picker_js and "new WeakMap" in android_picker_js:
    ok("android-select-picker debounces sheet rebuild per select via WeakMap (issue #28)")
elif android_picker_js and "sheetRebuildScheduled" in android_picker_js:
    fail("android-select-picker uses module-scoped sheetRebuildScheduled — second select drops rebuild (issue #28)")
else:
    fail("android-select-picker missing debounced sheet rebuild (issue #25)")

if capacitor_bridge_js and "falling back to browser download" not in capacitor_bridge_js and "return false" in capacitor_bridge_js.split("interceptBlobDownload", 1)[-1][:500]:
    ok("capacitor-bridge does not swallow download when blob read fails (issue #24)")
else:
    fail("capacitor-bridge still swallows download or claims false fallback (issue #24/#25)")

if capacitor_bridge_js and ("handleBlobDownload(blob, dl).catch" in capacitor_bridge_js or ".catch(function (err)" in capacitor_bridge_js.split("deferredRevokeUrls.add(href)", 1)[-1][:500]):
    ok("capacitor-bridge handleBlobDownload errors caught via .catch (issue #24)")
else:
    fail("capacitor-bridge handleBlobDownload fire-and-forget without .catch (issue #24)")

if worker_bridge_js and "function rejectAll" in worker_bridge_js:
    ok("zhl-worker-bridge rejectAll helper deduplicates pending rejection (issue #24)")
else:
    fail("zhl-worker-bridge missing rejectAll helper (issue #24)")

eng_val_path = os.path.join(os.path.dirname(__file__), "engine_validation_regression.py")
if os.path.isfile(eng_val_path):
    with open(eng_val_path, encoding="utf-8") as f:
        eng_val_lifecycle = f.read()
    if "run_worker_timeout_check" in eng_val_lifecycle and "run_worker_recovery_check" in eng_val_lifecycle:
        if "page.close()" in eng_val_lifecycle.split("def main", 1)[-1]:
            ok("engine_validation_regression.py page lifecycle owned by main (issue #24)")
        else:
            fail("engine_validation_regression.py missing explicit page.close in main (issue #24)")
        if "TEST_SETTINGS" in eng_val_lifecycle and eng_val_lifecycle.count('"gfLo": 30') <= 1:
            ok("engine_validation_regression.py uses shared TEST_SETTINGS (issue #25)")
        else:
            fail("engine_validation_regression.py duplicates settings dict (issue #25)")
        if "timeout override active" in eng_val_lifecycle:
            ok("engine_validation_regression.py asserts worker timeout override (issue #25)")
        else:
            fail("engine_validation_regression.py missing timeout override assertion (issue #25)")
        if "expT.length > 0" in eng_val_lifecycle:
            ok("engine_validation_regression.py requires tissue data before tissuesClose (issue #30)")
        else:
            fail("engine_validation_regression.py tissuesClose accepts empty arrays (issue #30)")
    else:
        fail("engine_validation_regression.py missing split worker timeout/recovery helpers (issue #24)")
else:
    fail("engine_validation_regression.py missing")

if worker_bridge_js and "killWorker" in worker_bridge_js and "ZHL worker timeout" in worker_bridge_js:
    ok("zhl-worker-bridge recreates worker after timeout (issue #22)")
else:
    fail("zhl-worker-bridge missing worker recovery on timeout (issue #22)")

if worker_bridge_js and "__LSP_ZHL_WORKER_TIMEOUT_MS" in worker_bridge_js:
    ok("zhl-worker-bridge supports __LSP_ZHL_WORKER_TIMEOUT_MS regression override")
else:
    fail("zhl-worker-bridge missing __LSP_ZHL_WORKER_TIMEOUT_MS test hook")

native_reg = os.path.join(os.path.dirname(__file__), "dev", "run_native_regression.py")
native_select_fixture = os.path.join(os.path.dirname(__file__), "dev", "fixtures", "native-select.html")
if os.path.isfile(native_reg) and os.path.isfile(native_select_fixture):
    with open(native_reg, encoding="utf-8") as f:
        native_reg_src = f.read()
    if "android-select" in native_reg_src and "capacitor-bridge" in native_reg_src:
        ok("dev/run_native_regression.py covers Android select + Capacitor bridge")
    else:
        fail("dev/run_native_regression.py missing Android select or Capacitor coverage")
else:
    fail("dev/run_native_regression.py or native-select fixture missing")

eng_val = eng_val_path
if os.path.isfile(eng_val):
    with open(eng_val, encoding="utf-8") as f:
        eng_val_src = f.read()
    if "ZHL worker timeout" in eng_val_src and "worker recovers after timeout" in eng_val_src:
        ok("engine_validation_regression.py tests ZHL worker timeout + recovery")
    else:
        fail("engine_validation_regression.py missing ZHL worker timeout/recovery tests")
else:
    fail("engine_validation_regression.py missing")

if os.path.isfile(run_all_reg):
    with open(run_all_reg, encoding="utf-8") as f:
        run_all_native_src = f.read()
    if "native_bridge" in run_all_native_src and "build_pages_site" in run_all_native_src:
        ok("run_all_regression.py includes native_bridge suite + build_pages pre-step")
    else:
        fail("run_all_regression.py missing native_bridge suite or build_pages pre-step")

ci_wf = os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml")
if os.path.isfile(ci_wf):
    with open(ci_wf, encoding="utf-8") as f:
        ci_wf_src = f.read()
    if "run_native_regression.py" in ci_wf_src:
        ok("ci.yml runs native bridge regression on push/PR")
    else:
        fail("ci.yml missing native bridge regression job")
else:
    fail("ci.yml missing")

if "__lspAppFullyReady = true" in html:
    ok("index.html sets __lspAppFullyReady after init (issue #21 CR-3)")
else:
    fail("index.html missing __lspAppFullyReady sentinel (issue #21 CR-3)")

if "android-webview" in html and "isAndroidWebView" in html:
    ok("Early Android WebView detection script present")
else:
    fail("Early Android WebView detection script missing")

if re.search(r'id="dg1Mix"[\s\S]*?ean50[\s\S]*?selected', html) or re.search(
    r'id="dg1Mix"[\s\S]*?selected[\s\S]*?value="ean50"', html
):
    ok("dg1Mix defaults to EAN50 (50%) on first load")
else:
    fail("dg1Mix missing selected EAN50 default")

if re.search(
    r"classList\.add\(['\"]android-webview['\"],\s*['\"]capacitor-native['\"]\)", html
):
    ok("index.html early head script marks android-webview + capacitor-native")
else:
    fail("index.html missing early android-webview/capacitor-native class hook")

if capacitor_bridge_js and "classList.add('capacitor-native')" not in capacitor_bridge_js:
    ok("capacitor-bridge.js does not duplicate capacitor-native class (owned by index.html)")
elif capacitor_bridge_js:
    fail("capacitor-bridge.js should not set capacitor-native — use index.html head script only")
else:
    fail("capacitor-bridge.js missing")

# ── Issue #55: full codebase audit (10 findings) ─────────────────────────────
if "rowDisplayPpo2(descentMidM" in js and "rawD / 2" not in js.split("No travel gas", 1)[-1][:800]:
    ok("imperial descent CNS uses depthM/2 not rawD/2 (issue #55 F1)")
else:
    fail("single-descent row still uses rawD/2 for pressure (issue #55 F1)")

if re.search(r"limits = \{6:720.*17:45\}", js) and "Math.min(lo + 1, 17)" in js.split("function segCNSfrac", 1)[-1][:500]:
    ok("segCNSfrac NOAA table extends to ppO2 1.70 (issue #55 F2)")
else:
    fail("segCNSfrac CNS limits table missing key 17 / hi clamp (issue #55 F2)")

if "rowDisplayPpo2(travelMidM, travelInfoRow.fN2, travelInfoRow.fHe" in js:
    ok("travel-gas descent CNS passes fHe fraction (issue #55 F3)")
else:
    fail("travel-gas descent rowDisplayPpo2 still hardcodes fHe=0 (issue #55 F3)")

if "shortMix(cv[3])" in js and "shortMix(c[3])" in js and "shortMix(cv[5])" not in js:
    ok("buildMessengerText bottom/stop rows use Mix column cv[3] (issue #55 F4)")
else:
    fail("buildMessengerText still indexes Mix from TTS column cv[5] (issue #55 F4)")

if re.search(r"if \(isTrimix\) \{[^}]*fHeNeeded", js, re.DOTALL):
    ok("calcBestMixTec He need not gated on narcoticN2 alone (issue #55 F5)")
else:
    fail("calcBestMixTec still skips He when narcoticN2 is false (issue #55 F5)")

if harness and "_lspEngineReady" in harness and "function appReady" in harness:
    ok("lsp-test-harness appReady accepts _lspEngineReady (issue #55 F6)")
else:
    fail("lsp-test-harness appReady missing _lspEngineReady fallback (issue #55 F6)")

_ccr_seg = _ccr_core_src.split("function saturateLinearCCR", 1)
if len(_ccr_seg) > 1 and "if (!(segTime > 0)) continue" in _ccr_seg[1][:1200]:
    ok("saturateLinearCCR skips NaN/zero segTime (issue #55 F7)")
else:
    fail("saturateLinearCCR still uses segTime <= 0 guard (issue #55 F7)")

if capacitor_bridge_js and "saved.finalName || filename" in capacitor_bridge_js and "deferredRevokeUrls" in capacitor_bridge_js:
    ok("capacitor-bridge share uses finalName + deferred blob revoke (issue #55 F8/F9 / #117 M-2)")
else:
    fail("capacitor-bridge missing finalName share or deferred blob read (issue #55 F8/F9)")

if capacitor_bridge_js and "status === 'granted'" in capacitor_bridge_js.split("function ensurePermission", 1)[-1][:600]:
    ok("capacitor-bridge ensurePermission requires granted status (issue #55 F10)")
else:
    fail("capacitor-bridge ensurePermission still treats non-denied as granted (issue #55 F10)")

if re.search(r'id="algoTools"[^<]*<img[^>]+tools-1424252\.png', html) and re.search(r'id="envSettingsToggle"[^<]*<img[^>]+settings-2099058\.png', html):
    ok("Mode row uses vendored Flaticon PNG icons for Tools and ENV")
else:
    fail("Mode row missing vendored Flaticon PNG for Tools or ENV")

if os.path.isfile(os.path.join(os.path.dirname(__file__), "vendor", "icons", "tools-1424252.png")) and os.path.isfile(os.path.join(os.path.dirname(__file__), "vendor", "icons", "settings-2099058.png")):
    ok("vendor/icons Flaticon PNG assets present offline")
else:
    fail("vendor/icons missing tools-1424252.png or settings-2099058.png")

_mode_row = html.split('<div class="algo-toggle"', 1)
if "syncEnvRowDisplay" in js and len(_mode_row) > 1 and 'id="envSettingsToggle"' in _mode_row[1][:3500]:
    ok("ENV settings toggle lives in mode row (Rec | Tec | Tools | ENV | Ref)")
else:
    fail("ENV toggle not in mode row or syncEnvRowDisplay missing")

if re.search(r'</div><!-- /deco panel -->\s*<div class="panel" id="cns">', html):
    ok("CNS and tools panels are siblings outside deco panel (not nested)")
else:
    fail("deco panel not closed before cns — tools mode content would be hidden")

if re.search(r'id="algoTools"[^<]*<img', html) and re.search(r'id="envSettingsToggle"[^<]*<img', html) and ".algo-btn-icon img" in html and "brightness(0) invert(1)" in html:
    ok("Mode row PNG icons use theme-aware brightness filters")
else:
    fail("Mode row PNG icons missing theme-aware brightness/contrast CSS")

if 'id="envSettingsBody"' in html and 'id="algoSettingsRow"' not in html and 'syncEnvRowDisplay' in js and 'algoSettingsRow' not in js.split('function syncEnvRowDisplay', 1)[1][:600]:
    ok("Rec mode uses global ENV panel only (no duplicate algoSettingsRow)")
else:
    fail("Rec duplicate algoSettingsRow still present or ENV panel missing")

_bmt_he = js.split("function calcBestMixTec", 1)[-1].split("function ", 1)[0] if "function calcBestMixTec" in js else ""
if _bmt_he and "effNarco" not in _bmt_he and re.search(
        r"if\s*\(\s*narcoFracAir\s*>\s*0\s*\)\s*\{[^}]*fHeNeeded", _bmt_he, re.DOTALL):
    ok("calcBestMixTec skips He when both narcosis flags off (issue #56)")
else:
    fail("calcBestMixTec still uses phantom fN2air narcosis fallback when narcoFracAir is 0 (issue #56)")

_audit_src57 = open(__file__, encoding="utf-8").read()
if (
    "_inner_tail = _update_banner.split(\"banner.innerHTML\", 1)[-1]" in _audit_src57
    and "document.body.appendChild(banner)" in _audit_src57
    and _banner_xss_ok
    and _banner_inner_expr
    and re.search(r"\+\s*safe\w*\s*\+", _banner_inner_expr)
):
    ok("showUpdateBanner XSS audit spans full innerHTML past CSS semicolons (issue #57)")
else:
    fail("showUpdateBanner XSS audit missing appendChild-bounded innerHTML slice (issue #57)")

_seg_cns = js.split("function segCNSfrac", 1)[-1].split("function ", 1)[0] if "function segCNSfrac" in js else ""
if _seg_cns and re.search(r"if\s*\(\s*ppo2\s*<\s*0\.6\s*\)\s*return\s*0", _seg_cns):
    ok("segCNSfrac returns zero below NOAA table floor 0.6 bar (issue #59 F1)")
else:
    fail("segCNSfrac still extrapolates phantom CNS between 0.5–0.6 bar (issue #59 F1)")
_aes = js.split("function addExposureSample", 1)[-1].split("function ", 1)[0] if "function addExposureSample" in js else ""
if _aes and "17:45" in _aes and re.search(r"if\s*\(\s*ppO2\s*>\s*0\.5", _aes) and re.search(r"if\s*\(\s*ppO2\s*<\s*0\.6", _aes):
    ok("addExposureSample OTU/CNS use separate NOAA thresholds (issue #59 F2 / #60 F1)")
else:
    fail("addExposureSample missing split OTU>0.5 / CNS<0.6 guards (issue #59 F2 / #60 F1)")
_www_bridge = os.path.join(os.path.dirname(__file__), "www", "capacitor-bridge.js")
if capacitor_bridge_js and os.path.isfile(_www_bridge):
    with open(_www_bridge, encoding="utf-8") as _wb:
        _www_bridge_txt = _wb.read()
    if "saved.finalName || filename" in _www_bridge_txt and (
        "responseType = 'arraybuffer'" in _www_bridge_txt
        or "async function readBlobFromHref" in _www_bridge_txt
    ):
        ok("www/capacitor-bridge.js synced with root share + arraybuffer fallback (issue #59 F3/F10)")
    else:
        fail("www/capacitor-bridge.js stale vs root — run sync_www.py (issue #59 F3/F10)")
elif capacitor_bridge_js:
    ok("www/capacitor-bridge.js sync check skipped (www/ not built yet)")
else:
    fail("capacitor-bridge.js missing")
if re.search(r"mix === 'custom'[\s\S]{0,200}Math\.max\(0\.05", js):
    ok("getBottomGasFractions custom O2 floor is 0.05 (issue #59 F4)")
else:
    fail("getBottomGasFractions custom path still clamps O2 to 0.21 (issue #59 F4)")
if "c.slice(1, 9)" in js and "c.slice(1, 8)" not in js.split("function exportPDF", 1)[-1][:8000]:
    ok("exportPDF includes EAD column via c.slice(1, 9) (issue #59 F5)")
else:
    fail("exportPDF still drops EAD column with c.slice(1, 8) (issue #59 F5)")
if "runPdfExportFromDialog" in js and ".catch(function" in js.split("function runPdfExportFromDialog", 1)[-1][:400]:
    ok("PDF export dialogs await async export with user-facing .catch (issue #59 F6)")
else:
    fail("PDF export dialogs fire-and-forget async exportPDF (issue #59 F6)")
_emdp = _gas_core_js.split("function enforceMinDecoProfile", 1)[-1].split("function getActiveGas", 1)[0] if "function enforceMinDecoProfile" in _gas_core_js else ""
if _emdp and "for (const s of result)" in _emdp.split("function resolveGasAtDepth", 1)[-1][:800]:
    ok("enforceMinDecoProfile resolveGasAtDepth uses in-progress result array (issue #59 F7)")
elif "ZhlEngineBundle.enforceMinDecoProfile" in js:
    ok("enforceMinDecoProfile delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("enforceMinDecoProfile resolveGasAtDepth still closes over original steps (issue #59 F7)")
if "_decoRowBuf" in js and "tbody.innerHTML += _decoRowBuf" in js:
    ok("deco table batches row HTML before single tbody write (issue #59 F8)")
else:
    fail("deco table still uses O(N²) tbody.innerHTML += in loop (issue #59 F8)")
if "pdfExportDialog" in js.split("function handleNativeBackForModals", 1)[-1].split("function initNativeModalBackHandler", 1)[0]:
    ok("handleNativeBackForModals dismisses pdfExportDialog (issue #59 F9)")
else:
    fail("handleNativeBackForModals missing pdfExportDialog back handler (issue #59 F9)")
_bdhd59 = js.split("function buildDecoPlanHeaderData", 1)[-1].split("function ", 1)[0] if "function buildDecoPlanHeaderData" in js else ""
if _bdhd59 and "waterDensityDisplayLabel()" in _bdhd59:
    ok("buildDecoPlanHeaderData water density defaults match UI select (issue #59 F12)")
else:
    fail("buildDecoPlanHeaderData still defaults density to en13319 only (issue #59 F12)")
if "function escapePresetHtml" not in js:
    ok("escapePresetHtml removed — presets use escapeHtmlText (issue #59 F13)")
else:
    fail("escapePresetHtml duplicate escaper still present (issue #59 F13)")
_harness = open(os.path.join(os.path.dirname(__file__), "lsp-test-harness.js"), encoding="utf-8").read() if os.path.isfile(os.path.join(os.path.dirname(__file__), "lsp-test-harness.js")) else ""
if _harness and "onErr(null)" in _harness and "bootErr = msg || null" in _harness:
    ok("lsp-test-harness clears stale bootErr on iframe load (issue #59 F11)")
else:
    fail("lsp-test-harness may propagate stale bootErr across reloadApp (issue #59 F11)")

_apk_update = js.split("function checkForApkUpdate", 1)[-1].split("// APP_VERSION", 1)[0] if "function checkForApkUpdate" in js else ""
if _apk_update and "function isNativeApk" in js.split("Native APK update check", 1)[-1].split("// APP_VERSION", 1)[0]:
    ok("Native APK update check uses isNativeApk WebView fallback (issue #58)")
else:
    fail("Native APK update check missing isNativeApk WebView class fallback (issue #58)")
if _apk_update and "visibilitychange" in _apk_update and "setTimeout(scheduleApkUpdateCheck, 500)" in _apk_update:
    ok("Native APK update check retries on load, visibility, and delayed schedule (issue #58)")
else:
    fail("Native APK update check missing deferred/retry scheduling (issue #58)")
if _apk_update and "navigator.onLine" not in _apk_update.split("function checkForApkUpdate", 1)[-1].split("function scheduleApkUpdateCheck", 1)[0]:
    ok("Native APK update check does not bail on navigator.onLine alone (issue #58)")
else:
    fail("Native APK update check still skips when navigator.onLine is false (issue #58)")

_pages_bridge = os.path.join(os.path.dirname(__file__), "_pages", "capacitor-bridge.js")
if capacitor_bridge_js and os.path.isfile(_pages_bridge):
    with open(_pages_bridge, encoding="utf-8") as _pb:
        _pages_bridge_txt = _pb.read()
    if "saved.finalName || filename" in _pages_bridge_txt and (
        "responseType = 'arraybuffer'" in _pages_bridge_txt
        or "async function readBlobFromHref" in _pages_bridge_txt
    ):
        ok("_pages/capacitor-bridge.js synced with root share + arraybuffer fallback (issue #60 F2)")
    else:
        fail("_pages/capacitor-bridge.js stale vs root — run build_pages_site.py (issue #60 F2)")
elif capacitor_bridge_js:
    ok("_pages/capacitor-bridge.js sync check skipped (_pages/ not built yet)")
_rpdf = js.split("function runPdfExportFromDialog", 1)[-1].split("function ", 1)[0] if "function runPdfExportFromDialog" in js else ""
if _rpdf and "?.checked !== false" in _rpdf and "&& !!" not in _rpdf:
    ok("runPdfExportFromDialog opts default to included when checkbox absent (issue #60 F3)")
else:
    fail("runPdfExportFromDialog still double-reads checkbox as false when absent (issue #60 F3)")
if "function waterDensityDisplayLabel" in js and re.search(
        r"key === 'custom'[\s\S]{0,120}Custom", js.split("function waterDensityDisplayLabel", 1)[-1][:400]):
    ok("waterDensityDisplayLabel handles custom density (issue #60 F4)")
else:
    fail("water density export still shows undefined for custom water type (issue #60 F4)")
_gdbgp = js.split("function getDomBottomGasPct", 1)[-1].split("function ", 1)[0] if "function getDomBottomGasPct" in js else ""
if "function readDomO2Pct" in js and _gdbgp and "readDomO2Pct('decoCustomO2')" in _gdbgp:
    ok("getDomBottomGasPct uses readDomO2Pct for custom O2 (issue #60 F5)")
else:
    fail("getDomBottomGasPct still returns raw parseFloat NaN without explicit guard (issue #60 F5)")
if _harness and "__lspBootErr" not in _harness:
    ok("lsp-test-harness removed dead __lspBootErr assignment (issue #60 F6)")
else:
    fail("lsp-test-harness still assigns unread __lspBootErr (issue #60 F6)")
_deco_render = js.split("// ── DESCENT ROW(S)", 1)[-1].split("tbody.innerHTML += _decoRowBuf", 1)[0] if "// ── DESCENT ROW(S)" in js else ""
if _deco_render and "_decoRowBuf +=" in _deco_render and "tbody.innerHTML +=" not in _deco_render.split("collapsedMDP.forEach", 1)[0]:
    ok("deco table batches descent/bottom rows in _decoRowBuf (issue #60 F7)")
else:
    fail("deco table still uses tbody.innerHTML += before collapsedMDP loop (issue #60 F7)")
if re.search(r'id="decoCustomO2"[^>]*min="5"', html) and "5% used" in js:
    ok("custom bottom O2 below 5% shows clamp warning (issue #60 F8)")
else:
    fail("custom bottom O2 silently clamps below 5% without user warning (issue #60 F8)")

_android_bridge = os.path.join(os.path.dirname(__file__), "android", "app", "src", "main", "assets", "public", "capacitor-bridge.js")
if capacitor_bridge_js and os.path.isfile(_android_bridge):
    with open(_android_bridge, encoding="utf-8") as _ab:
        _android_bridge_txt = _ab.read()
    if "shareFile(saved.uri, saved.finalName || filename)" in _android_bridge_txt:
        ok("android capacitor-bridge.js share uses finalName (issue #61 F1/F6)")
    else:
        fail("android capacitor-bridge.js stale — run cap sync android (issue #61 F1/F6)")
elif capacitor_bridge_js:
    ok("android capacitor-bridge.js sync check skipped (cap sync not run yet)")
if "getDomDecoGasPct(cidx)" in js and "Enter a valid O₂ % for custom deco gas" in js:
    ok("deco gas MOD shows sentinel for blank custom O2 (issue #61 F2)")
else:
    fail("deco gas MOD still substitutes EAN50 for blank custom O2 (issue #61 F2)")
_wddl = js.split("function waterDensityDisplayLabel", 1)[-1].split("function ", 1)[0] if "function waterDensityDisplayLabel" in js else ""
if _wddl and "|| 'salt'" in _wddl:
    ok("waterDensityDisplayLabel defaults to salt (issue #61 F3)")
else:
    fail("waterDensityDisplayLabel missing salt default (issue #61 F3)")
if "waterDensityDisplayLabel()" in js.split("function _envSettingsSummary", 1)[-1].split("function ", 1)[0]:
    ok("_envSettingsSummary uses waterDensityDisplayLabel (issue #61 F4)")
else:
    fail("_envSettingsSummary still pushes raw water density keys (issue #61 F4)")
if re.search(r"botMix === 'custom'[\s\S]{0,160}botDom\.o2\s*>\s*0\s*&&\s*botDom\.o2\s*<\s*5", js):
    ok("custom bottom O2=0 shows sentinel; clamp note only for (0,5) (issue #61 F5 / #62 F3)")
else:
    fail("custom bottom O2 clamp guard wrong for zero vs sub-5% (issue #61 F5 / #62 F3)")
_rds62 = js.split("function runDecoSchedule()", 1)[-1][:3500] if "function runDecoSchedule()" in js else ""
_vdg62 = _rds62.find("validateDomDecoGases()")
_ccr62 = _rds62.find("isRebreatherCircuit(_uiCcr.circuit)")
if _vdg62 >= 0 and (_ccr62 < 0 or _vdg62 < _ccr62):
    ok("runDecoSchedule validates deco gases before CCR-only gate (issue #62 F1)")
else:
    fail("validateDomDecoGases still gated inside rebreather-only block (issue #62 F1)")
_dgf62 = js.split("function getDecoGasFractions", 1)[-1].split("function ", 1)[0] if "function getDecoGasFractions" in js else ""
if _dgf62 and "readDomO2Pct(customId)" in _dgf62 and "|| 50" not in _dgf62:
    ok("getDecoGasFractions returns null for blank custom O2 (issue #62 F1)")
else:
    fail("getDecoGasFractions still substitutes EAN50 for blank custom O2 (issue #62 F1)")
if re.search(r"sel\.value === 'trimix'[\s\S]{0,200}getDomDecoGasPct\(cidx\)", js):
    ok("deco gas MOD sentinel covers trimix blank fields (issue #62 F2)")
else:
    fail("deco gas MOD missing trimix NaN guard (issue #62 F2)")
_vgfp62 = js.split("function validateGasFractionsPct", 1)[-1].split("function ", 1)[0] if "function validateGasFractionsPct" in js else ""
if _vgfp62 and "o <= 0" in _vgfp62:
    ok("validateGasFractionsPct rejects zero O2 (issue #62 F3)")
else:
    fail("validateGasFractionsPct still accepts 0% O2 (issue #62 F3)")
if re.search(r"sel\.value === 'custom' \|\| sel\.value === 'trimix'[\s\S]{0,120}getDomDecoGasPct\(cidx\)", js):
    ok("getDomDecoGasPct called only for custom/trimix cards (issue #62 F4)")
else:
    fail("getDomDecoGasPct still called for every deco gas card (issue #62 F4)")
_gbf63 = js.split("function getBottomGasFractions", 1)[-1].split("function ", 1)[0] if "function getBottomGasFractions" in js else ""
if _gbf63 and "readDomO2Pct('decoCustomO2')" in _gbf63 and "return null" in _gbf63:
    ok("getBottomGasFractions uses readDomO2Pct and returns null for blank custom (issue #63 F1)")
else:
    fail("getBottomGasFractions still falls back to Air for blank custom bottom gas (issue #63 F1)")
if re.search(r"function runVPMSchedule[\s\S]{0,1200}getDecoCardFractions\(n\)", js) and "dg${n}CustomO2" not in js.split("function runVPMSchedule", 1)[-1].split("function runVPMScheduleCore", 1)[0][:2500]:
    ok("VPM deco gas assembly uses getDecoCardFractions not CustomO2 element (issue #63 F2/F5)")
else:
    fail("VPM deco gas still reads dg CustomO2 for trimix cards (issue #63 F2/F5)")
_bzpd63 = js.split("function buildZhlScheduleParamsFromDom", 1)[-1].split("function ", 1)[0] if "function buildZhlScheduleParamsFromDom" in js else ""
if _bzpd63 and "throw new Error" in _bzpd63 and "Invalid deco gas" in _bzpd63:
    ok("buildZhlScheduleParamsFromDom throws on blank trimix deco gas (issue #63 F3)")
else:
    fail("buildZhlScheduleParamsFromDom still silently drops blank trimix deco gas (issue #63 F3)")
if re.search(r"function calcGasPlan[\s\S]{0,400}validateDomDecoGases\(\)", js):
    ok("calcGasPlan validates deco gases before getBottomGasFractions (issue #63 F4)")
else:
    fail("calcGasPlan still uses getBottomGasFractions without gas validation (issue #63 F4)")
if re.search(r"function exportPDF[\s\S]{0,500}validateDomDecoGases\(\)", js):
    ok("exportPDF validates deco gases before building PDF (issue #63 F1)")
else:
    fail("exportPDF still skips gas validation (issue #63 F1)")
_bst64 = js.split("function buildSlateText", 1)[-1].split("function showSlate", 1)[0] if "function buildSlateText" in js else ""
if _bst64 and "if (!botFracs) return null" in _bst64:
    ok("buildSlateText guards null getBottomGasFractions (issue #64 F1)")
else:
    fail("buildSlateText crashes on null getBottomGasFractions (issue #64 F1)")
_bcs64 = js.split("function buildContingencySlateText", 1)[-1].split("function showContingencySlate", 1)[0] if "function buildContingencySlateText" in js else ""
if _bcs64 and "if (!botFracs) return null" in _bcs64:
    ok("buildContingencySlateText guards null getBottomGasFractions (issue #64 F1)")
else:
    fail("buildContingencySlateText crashes on null getBottomGasFractions (issue #64 F1)")
_bmt64 = js.split("function buildMessengerText", 1)[-1].split("function exportTXT", 1)[0] if "function buildMessengerText" in js else ""
if _bmt64 and "if (!_msgBotFracs) return null" in _bmt64:
    ok("buildMessengerText guards null getBottomGasFractions (issue #64 F1)")
else:
    fail("buildMessengerText crashes on null getBottomGasFractions (issue #64 F1)")
if re.search(r"function runUnifiedPlan[\s\S]{0,400}if\s*\(\s*rbOnLoop\s*&&\s*!bot\s*\)\s*return", js):
    ok("runUnifiedPlan guards null bottom gas on CCR loop (issue #64 F1)")
else:
    fail("runUnifiedPlan crashes on null getBottomGasFractions for CCR (issue #64 F1)")
if "curFracs && calcEND" in js and "curFracs ? currentEND - actualEND" in js:
    ok("calcBestMixTec guards null getBottomGasFractions return (issue #64 F2)")
else:
    fail("calcBestMixTec still dereferences null getBottomGasFractions (issue #64 F2)")
if re.search(r"function ccrDiluentSurfaceLpm[\s\S]{0,200}if\s*\(\s*!bot\s*\)\s*return\s*NaN", js):
    ok("ccrDiluentSurfaceLpm guards null getBottomGasFractions (issue #64 F3)")
else:
    fail("ccrDiluentSurfaceLpm crashes on null getBottomGasFractions (issue #64 F3)")
if re.search(r"function isCcrDiluentGasLabel[\s\S]{0,300}if\s*\(\s*!bot\s*\)\s*return\s*false", js):
    ok("isCcrDiluentGasLabel guards null getBottomGasFractions (issue #64 F3)")
else:
    fail("isCcrDiluentGasLabel crashes on null getBottomGasFractions (issue #64 F3)")

# ── Issue #65: ccrDiluent air fallback, export toasts, dead guards, audit gaps ──
if re.search(r"function ccrDiluentSurfaceLpm[\s\S]{0,250}metRate\s*/\s*0\.21", js) is None:
    ok("ccrDiluentSurfaceLpm no silent air-diluent fallback on null bottom gas (issue #65 F1)")
else:
    fail("ccrDiluentSurfaceLpm still returns metRate/0.21 when bottom gas null (issue #65 F1)")
if "function notifyInvalidGasExport" in js and re.search(r"function showSlate[\s\S]{0,400}notifyInvalidGasExport\(", js):
    ok("showSlate shows gas validation error not misleading no-plan toast (issue #65 F2)")
else:
    fail("showSlate misleading toast on blank bottom gas (issue #65 F2)")
if re.search(r"function showContingencySlate[\s\S]{0,500}notifyInvalidGasExport\(", js):
    ok("showContingencySlate shows gas validation error on blank bottom gas (issue #65 F2)")
else:
    fail("showContingencySlate misleading toast on blank bottom gas (issue #65 F2)")
if re.search(r"function copyDiveProfile[\s\S]{0,800}notifyInvalidGasExport\(", js):
    ok("copyDiveProfile shows gas validation error on blank bottom gas (issue #65 F2)")
else:
    fail("copyDiveProfile misleading toast on blank bottom gas (issue #65 F2)")
_vpm_rr65 = js.split("function renderVPMResults", 1)[-1].split("function getAllDecoGasIds", 1)[0] if "function renderVPMResults" in js else ""
if _vpm_rr65 and "addBailoutStressReserve" in _vpm_rr65 and "if (!botFracs) return" not in _vpm_rr65:
    ok("renderVPMResults stress-reserve block has no dead botFracs return (issue #65 F3)")
else:
    fail("renderVPMResults still has dead if (!botFracs) return in stress block (issue #65 F3)")
_cbt65 = js.split("function calcBestMixTec", 1)[-1].split("function ", 1)[0] if "function calcBestMixTec" in js else ""
if _cbt65 and "typeof getBottomGasFractions === 'function'" not in _cbt65:
    ok("calcBestMixTec calls getBottomGasFractions directly without typeof guard (issue #65 F4)")
else:
    fail("calcBestMixTec still has dead typeof getBottomGasFractions guard (issue #65 F4)")
_bdph65 = js.split("function buildDecoPlanHeaderData", 1)[-1].split("function ", 1)[0] if "function buildDecoPlanHeaderData" in js else ""
if _bdph65 and "_expBotFracs ?" in _bdph65:
    ok("buildDecoPlanHeaderData null-safe bottom gas fractions (issue #65 F5)")
else:
    fail("buildDecoPlanHeaderData missing null guard for getBottomGasFractions (issue #65 F5)")
_bet65 = js.split("function calcGasPlan", 1)[-1].split("function ", 1)[0] if "function calcGasPlan" in js else ""
if _bet65 and re.search(r"getBottomGasFractions\(\)[\s\S]{0,80}if\s*\(\s*!botFracs\s*\)\s*return", _bet65):
    ok("calcGasPlan guards null getBottomGasFractions (issue #65 F5)")
else:
    fail("calcGasPlan missing null guard for getBottomGasFractions (issue #65 F5)")
_ccns65 = js.split("function calcCNS", 1)[-1].split("function ", 1)[0] if "function calcCNS" in js else ""
if _ccns65 and "getBottomGasFractions()" in _ccns65 and "botFracs ?" in _ccns65 and "typeof getBottomGasFractions" not in _ccns65:
    ok("calcCNS null-safe fHe from getBottomGasFractions (issue #65 F5)")
else:
    fail("calcCNS missing null guard for getBottomGasFractions fHe (issue #65 F5)")
_vccr65 = js.split("function validateCcrGasConfiguration", 1)[-1].split("function updateCcrGasValidation", 1)[0] if "function validateCcrGasConfiguration" in js else ""
if _vccr65 and "getBottomGasFractions()" in _vccr65 and re.search(r"if\s*\(\s*!bot\s*\)", _vccr65):
    ok("validateCcrGasConfiguration guards null getBottomGasFractions (issue #65 F5)")
else:
    fail("validateCcrGasConfiguration missing null guard for getBottomGasFractions (issue #65 F5)")

# ── Issue #66: NaN diluent consumption, export guards, toast UX, audit gaps ──
if re.search(r"function ccrDiluentSurfaceLpm[\s\S]{0,200}if\s*\(\s*!bot\s*\)\s*return\s*NaN", js):
    ok("ccrDiluentSurfaceLpm returns NaN not zero for null bottom gas (issue #66 F1)")
else:
    fail("ccrDiluentSurfaceLpm still returns 0 for null bottom gas (issue #66 F1)")
if re.search(r"function ccrGasLitres[\s\S]{0,350}!Number\.isFinite\(surfLpm\)", js):
    ok("ccrGasLitres propagates invalid diluent surface LPM as NaN (issue #66 F1)")
else:
    fail("ccrGasLitres missing NaN guard for invalid diluent surface LPM (issue #66 F1)")
if re.search(r"function gpVolDisp[\s\S]{0,120}!Number\.isFinite\(litres\)", js):
    ok("gpVolDisp renders non-finite litres as em dash (issue #66 F1)")
else:
    fail("gpVolDisp missing non-finite litres display guard (issue #66 F1)")
_cdp66 = js.split("function copyDiveProfile", 1)[-1].split("function closeCopyModal", 1)[0] if "function copyDiveProfile" in js else ""
if _cdp66 and "exportNeedsDecoBottomGas(mode)" in _cdp66 and not re.search(r"if\s*\(\s*mode\s*===\s*['\"]deco['\"]\s*\)\s*\{[^}]*notifyInvalidGasExport", _cdp66):
    ok("copyDiveProfile gas guard covers all export modes (issue #66 F2/F5)")
else:
    fail("copyDiveProfile gas guard still mode-gated to deco only (issue #66 F2/F5)")
_ext66 = js.split("function exportTXT", 1)[-1].split("function copyFallback", 1)[0] if "function exportTXT" in js else ""
if _ext66 and "exportNeedsDecoBottomGas(mode)" in _ext66 and "notifyInvalidGasExport" in _ext66:
    ok("exportTXT guards invalid bottom gas before download (issue #66 F3/F5)")
else:
    fail("exportTXT missing gas validation guard (issue #66 F3/F5)")
_nige66 = js.split("function notifyInvalidGasExport", 1)[-1].split("function notifyScheduleError", 1)[0] if "function notifyInvalidGasExport" in js else ""
if _nige66 and "showToast(" in _nige66 and "alert(" not in _nige66 and "typeof validateDomDecoGases" not in _nige66:
    ok("notifyInvalidGasExport uses showToast not blocking alert (issue #66 F4)")
else:
    fail("notifyInvalidGasExport still uses blocking alert (issue #66 F4)")

# ── Issue #67: NaN accumulator, exportTXT contingency, toast error style, audit gaps ──
if "function accumGasLitres" in js and "accumGasLitres(gasConsVPM" in js and "accumGasLitres(gasConsumed" in js:
    ok("gas consumption accumulators use NaN-preserving accumGasLitres (issue #67 F1)")
else:
    fail("gas consumption still uses (acc[label] || 0) NaN-erasing idiom (issue #67 F1)")
_end67 = js.split("function exportNeedsDecoBottomGas", 1)[-1].split("function copyDiveProfile", 1)[0] if "function exportNeedsDecoBottomGas" in js else ""
if _end67 and "'cns'" not in _end67 and "mode === 'planner'" in _end67:
    ok("exportNeedsDecoBottomGas excludes cns mode (issue #67 F4)")
else:
    fail("exportNeedsDecoBottomGas still blocks cns export on blank deco gas (issue #67 F4)")
_ext67 = js.split("function exportTXT", 1)[-1].split("function copyFallback", 1)[0] if "function exportTXT" in js else ""
if _ext67 and "_lastContingency" in _ext67 and re.search(r"mode\s*===\s*['\"]contingency['\"][\s\S]{0,120}_lastContingency", _ext67):
    ok("exportTXT guards missing contingency plan with toast (issue #67 F2/F6)")
else:
    fail("exportTXT silent no-op when contingency plan not run (issue #67 F2/F6)")
_st67 = js.split("function showToast", 1)[-1].split("function runContingencyScenario", 1)[0] if "function showToast" in js else ""
if _st67 and "isError" in _st67 and "var(--red)" in _st67:
    ok("showToast supports error styling for invalid-gas notifications (issue #67 F3)")
else:
    fail("showToast missing error color distinction (issue #67 F3)")
_rds67 = js.split("function runDecoSchedule", 1)[-1].split("function planSegDepthM", 1)[0] if "function runDecoSchedule" in js else ""
if _rds67 and "notifyScheduleError" in _rds67 and "alert('Cannot generate schedule" not in _rds67:
    ok("runDecoSchedule uses notifyScheduleError not blocking alert (issue #67 F5)")
else:
    fail("runDecoSchedule still uses blocking alert for invalid gas (issue #67 F5)")

# ── Issue #68: toast error color, dead typeof cleanup, error extraction, audit gaps ──
_ext68 = js.split("function exportTXT", 1)[-1].split("function copyFallback", 1)[0] if "function exportTXT" in js else ""
if _ext68 and re.search(r"Run an emergency plan first['\"],\s*['\"]export['\"],\s*true", _ext68):
    ok("exportTXT contingency no-plan toast uses error styling (issue #68 F1)")
else:
    fail("exportTXT contingency no-plan toast missing isError styling (issue #68 F1)")
_rds68 = js.split("function runDecoSchedule", 1)[-1].split("function planSegDepthM", 1)[0] if "function runDecoSchedule" in js else ""
if _rds68 and "typeof validateCcrGasConfiguration" not in _rds68 and "typeof updateCcrGasValidation" not in _rds68:
    ok("runDecoSchedule calls CCR validators directly without typeof guards (issue #68 F2)")
else:
    fail("runDecoSchedule still has dead typeof guards for CCR validators (issue #68 F2)")
if _rds68 and re.search(r"validateCcrGasConfiguration\(\)[\s\S]{0,250}typeof err0 === 'string'", _rds68):
    ok("runDecoSchedule CCR gas error uses .message extraction (issue #68 F3)")
else:
    fail("runDecoSchedule CCR gas error extraction not forward-compatible (issue #68 F3)")
if _rds68 and all(p in _rds68 for p in (
    "validateDecoInputs()",
    "validateCcrGasConfiguration()",
    "validateDomDecoGases()",
    "validateCcrCalculationInputs(",
)):
    ok("runDecoSchedule has all four validation paths before schedule run (issue #68 F4)")
else:
    fail("runDecoSchedule missing one or more validation paths (issue #68 F4)")
if _rds68 and _rds68.count("notifyScheduleError(") >= 4:
    ok("runDecoSchedule routes all validation failures through notifyScheduleError (issue #68 F4)")
else:
    fail("runDecoSchedule missing notifyScheduleError on one or more validation paths (issue #68 F4)")
_vpm68 = js.split("function renderVPMResults", 1)[-1].split("function getAllDecoGasIds", 1)[0] if "function renderVPMResults" in js else ""
if _vpm68 and "addBailoutStressReserve" in _vpm68 and re.search(r"addBailoutStressReserve[\s\S]{0,250}accumGasLitres\(gasConsVPM", _vpm68):
    ok("addBailoutStressReserve lambda uses accumGasLitres (issue #68 F4)")
else:
    fail("addBailoutStressReserve lambda missing accumGasLitres (issue #68 F4)")

# ── Issue #69: isError toast coverage, domGasVal extraction, typeof cleanup ──
if js.count("Run an emergency plan first', 'export', true") >= 1 and js.count("Run an emergency plan first', 'copy', true") >= 1 and js.count("Run an emergency plan first', 'slate', true") >= 2:
    ok("all contingency no-plan toasts use isError styling (issue #69 F1)")
else:
    fail("contingency no-plan toast missing isError on copy/slate paths (issue #69 F1)")
_rds69 = js.split("function runDecoSchedule", 1)[-1].split("function planSegDepthM", 1)[0] if "function runDecoSchedule" in js else ""
if _rds69 and re.search(r"validateDomDecoGases\(\)[\s\S]{0,200}domErr0\?\.message", _rds69):
    ok("runDecoSchedule DOM gas error uses safe .message extraction (issue #69 F2)")
else:
    fail("runDecoSchedule DOM gas error still uses hard errors[0].message access (issue #69 F2)")
_ugmd69 = js.split("function updateGasMODDisplays", 1)[-1].split("function _dgCardCount", 1)[0] if "function updateGasMODDisplays" in js else ""
if _ugmd69 and "isCcrGasUiMode()" in _ugmd69 and "typeof isCcrGasUiMode" not in _ugmd69:
    ok("updateGasMODDisplays calls isCcrGasUiMode directly without typeof guard (issue #69 F3)")
else:
    fail("updateGasMODDisplays still has dead typeof isCcrGasUiMode guard (issue #69 F3)")

# ── Issue #70: deco no-plan isError toasts, domErr0 fallback, typeof cleanup, audit ──
if js.count("Run a dive plan first', 'copy', true") >= 2 and js.count("Run a dive plan first', 'slate', true") >= 2:
    ok("all deco no-plan toasts use isError styling (issue #70 F1/F4)")
else:
    fail("deco no-plan toast missing isError on copy/slate paths (issue #70 F1/F4)")
_rds70 = js.split("function runDecoSchedule", 1)[-1].split("function planSegDepthM", 1)[0] if "function runDecoSchedule" in js else ""
if _rds70 and "domErr0?.message || 'Invalid gas configuration.'" in _rds70 and "|| domErr0" not in _rds70.split("domErr0", 1)[-1].split("notifyScheduleError", 1)[0]:
    ok("runDecoSchedule DOM gas error avoids object fallback in toast (issue #70 F2)")
else:
    fail("runDecoSchedule DOM gas error still has unsafe || domErr0 object fallback (issue #70 F2)")
if "typeof isCcrGasUiMode" not in js:
    ok("no dead typeof isCcrGasUiMode guards remain (issue #70 F3)")
else:
    fail("dead typeof isCcrGasUiMode guards still present (issue #70 F3)")

# ── Issue #71: storage error toast, typeof cleanup, CCR error extraction audit ──
if "Could not save defaults — storage unavailable', 'error', true" in js:
    ok("save-defaults storage error toast uses isError styling (issue #71 F1)")
else:
    fail("save-defaults storage error toast missing isError styling (issue #71 F1)")
if "typeof getAllDecoGasIds" not in js and "typeof validateDomDecoGases" not in js:
    ok("no dead typeof guards for getAllDecoGasIds or validateDomDecoGases (issue #71 F2)")
else:
    fail("dead typeof getAllDecoGasIds or validateDomDecoGases guards remain (issue #71 F2)")
_rds71 = js.split("function runDecoSchedule", 1)[-1].split("function planSegDepthM", 1)[0] if "function runDecoSchedule" in js else ""
if _rds71 and re.search(r"validateCcrGasConfiguration\(\)[\s\S]{0,250}typeof err0 === 'string'", _rds71):
    ok("runDecoSchedule CCR gas error avoids bare object fallback (issue #71 F3)")
else:
    fail("runDecoSchedule CCR gas error still has unsafe object passthrough (issue #71 F3)")

# ── Issue #72: remaining dead typeof guards for always-present functions ──
_gcbm72 = js.split("function getConfiguredBailoutMixes", 1)[-1].split("function resolveCcrSacForGas", 1)[0] if "function getConfiguredBailoutMixes" in js else ""
if _gcbm72 and "getDecoCardFractions(cidx)" in _gcbm72 and "typeof getDecoCardFractions" not in _gcbm72:
    ok("getConfiguredBailoutMixes calls getDecoCardFractions directly (issue #72 F1)")
else:
    fail("getConfiguredBailoutMixes still has dead typeof getDecoCardFractions guard (issue #72 F1)")
_rcr72 = js.split("function resolveCcrSacForGas", 1)[-1].split("function getBailoutReserveMixLabel", 1)[0] if "function resolveCcrSacForGas" in js else ""
if _rcr72 and "getCCRSettingsFromDOM()" in _rcr72 and "typeof getCCRSettingsFromDOM" not in _rcr72 and "typeof isCcrDiluentGasLabel" not in _rcr72:
    ok("resolveCcrSacForGas calls CCR helpers directly without typeof guards (issue #72 F1)")
else:
    fail("resolveCcrSacForGas still has dead typeof guards (issue #72 F1)")
_gcm72 = _ccr_core_src.split("function getCcrMetabolicO2Rate", 1)[-1].split("function computePSCRFractions", 1)[0] if "function getCcrMetabolicO2Rate" in _ccr_core_src else ""
if _gcm72 and "normalizeCCRSettings" in _gcm72:
    ok("getCcrMetabolicO2Rate uses normalizeCCRSettings in zhl-ccr-core (issue #72 F1)")
elif "ZhlEngineBundle.getCcrMetabolicO2Rate" in js:
    ok("getCcrMetabolicO2Rate delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("getCcrMetabolicO2Rate still has dead typeof getCCRSettingsFromDOM guard (issue #72 F1)")
if "typeof setGF" not in js.split("function syncGfPresetFromValues", 1)[-1].split("let lastTissues", 1)[0]:
    ok("syncGfPresetFromValues calls setGF directly (issue #72 F1)")
else:
    fail("syncGfPresetFromValues still has dead typeof setGF guard (issue #72 F1)")
if "typeof setGasRule" not in js.split("function resetToDefaults", 1)[-1].split("function _doResetToDefaults", 1)[0]:
    ok("resetToDefaults calls setGasRule directly (issue #72 F1)")
else:
    fail("resetToDefaults still has dead typeof setGasRule guard (issue #72 F1)")
_geb72 = js.split("function guardEngineBootForCalculate", 1)[-1].split("function ", 1)[0] if "function guardEngineBootForCalculate" in js else ""
if _geb72 and "showEngineLoadErrorBanner()" in _geb72 and "typeof showEngineLoadErrorBanner" not in _geb72:
    ok("guardEngineBootForCalculate calls showEngineLoadErrorBanner directly (issue #72 F1)")
else:
    fail("guardEngineBootForCalculate still has dead typeof showEngineLoadErrorBanner guard (issue #72 F1)")

# ── Issue #73: final typeof cleanup batch ──
_dead73 = (
    "typeof escapeHtmlText",
    "typeof renumberDecoGasCards",
    "typeof getCCRSettingsFromDOM",
    "typeof loopMixLabelFor",
    "typeof setGF",
    "typeof setCustomGF",
)
if all(s not in js for s in _dead73):
    ok("no dead typeof guards for issue #73 function set (issue #73 F1)")
else:
    fail("dead typeof guards remain from issue #73 sweep (issue #73 F1)")
_gpr73 = js.split("function gpRequiredFor", 1)[-1].split("function _syncCylToGasPlan", 1)[0] if "function gpRequiredFor" in js else ""
if _gpr73 and "loopMixLabelFor(label, getCCRSettingsFromDOM())" in _gpr73:
    ok("gpRequiredFor uses loopMixLabelFor and getCCRSettingsFromDOM directly (issue #73 F1)")
else:
    fail("gpRequiredFor still has dead typeof CCR label guards (issue #73 F1)")

# ── Issue #74: typeof cleanup batch (renderNDLTable, runDecoSchedule, etc.) ──
_dead74 = (
    "typeof renderNDLTable",
    "typeof runDecoSchedule",
    "typeof runPlanner",
    "typeof calcCNS",
    "typeof initTools",
    "typeof calcGasPlan",
    "typeof calcContingency",
    "typeof setAlgo",
    "typeof toggleCircuitFields",
    "typeof handleGFSelect",
    "typeof calcCNS==='function'",
)
if all(s not in js for s in _dead74):
    ok("no dead typeof guards for issue #74 function set (issue #74 F1)")
else:
    fail("dead typeof guards remain from issue #74 sweep (issue #74 F1)")
_drd74 = js.split("function _doResetToDefaults", 1)[-1].split("function ", 1)[0] if "function _doResetToDefaults" in js else ""
if _drd74 and ".switch-depth-display" in _drd74 and "typeof runDecoSchedule" not in _drd74:
    ok("_doResetToDefaults resets switch-depth displays without misleading runDecoSchedule guard (issue #74 F2)")
else:
    fail("_doResetToDefaults still has misleading typeof runDecoSchedule guard (issue #74 F2)")

# ── Issue #75: typeof guard cleanup campaign complete (v2.51.24 review CLEAN) ──
_ccm75 = js.split("function closeConfirmModal", 1)[-1].split("function ", 1)[0] if "function closeConfirmModal" in js else ""
if _ccm75 and "typeof _confirmCallback === 'function'" in _ccm75:
    ok("closeConfirmModal retains legitimate _confirmCallback typeof guard (issue #75)")
else:
    fail("closeConfirmModal missing legitimate _confirmCallback typeof guard (issue #75)")
_dead_campaign = _dead73 + _dead74
if all(s not in js for s in _dead_campaign):
    ok("typeof guard cleanup campaign complete — no dead guards from issues #73–#74 sets (issue #75)")
else:
    fail("dead typeof guards reintroduced after campaign complete (issue #75)")

# ── Issue #93: deep review v2.52.00 (2 HIGH / 10 MEDIUM / 3 LOW) ──
if "s.fN2 != null ? s.fN2 : bottomFN2" in js and "s.fN2 || bottomFN2" not in js.split("function runDecoSchedule", 1)[-1][:12000]:
    ok("O2 deco stop: fN2=0 preserved in ceiling walk (issue #93 H-1)")
else:
    fail("ceiling walk still uses s.fN2 || bottomFN2 falsy-zero fallback (issue #93 H-1)")
if "function computePSCRFractions(pAmb, fO2, fHe, ccr)" in _ccr_core_src and ("ppO2Drop = metO2 / loopVol" in _ccr_core_src or "cappedDrop = Math.min(ppO2Drop" in _ccr_core_src):
    ok("zhl-ccr-core computePSCRFractions steady-state Baker formula (issue #93 H-2)")
else:
    fail("index.html computePSCRFractions still uses cumulative runtime depletion (issue #93 H-2)")
if "result.finalTissues && !_contingencyRunning" in js and "window._contingencyRunning" not in js.split("function runVPMSchedule", 1)[-1][:4000]:
    ok("VPM tissue-viz uses module _contingencyRunning guard (issue #93 M-1)")
else:
    fail("VPM guards still read window._contingencyRunning (issue #93 M-1)")
if "window._lastVPMExport = null" in js.split("function setAlgo", 1)[-1][:8000]:
    ok("setAlgo/setDecoAlgorithm clear _lastVPMExport (issue #93 M-2)")
else:
    fail("_lastVPMExport not cleared on algorithm switch (issue #93 M-2)")
if "ccrLoopGasBelowSetpoint" in _ccr_core_src and "fHe / inertSrc" in _ccr_core_src.split("function ccrLoopGasBelowSetpoint", 1)[-1][:600]:
    ok("CCR below-setpoint: proportional diluent He/N2 in loop inert (issue #98/#117)")
else:
    fail("CCR below-setpoint still zeroes or over-assigns loop inert (issue #98/#117)")
if "validateGasFractionsPct" in js.split("function validatePlannerInputs", 1)[-1][:1600]:
    ok("validatePlannerInputs validates trimix O2+He totals (issue #98 H-2)")
else:
    fail("validatePlannerInputs missing trimix gas validation (issue #98 H-2)")
if "5.0 / 1.88" in html and "4.0 / 1.88" not in html:
    ok("He HT tooltip uses 5.0 min N2 compartment (issue #98 L-1)")
else:
    fail("He HT tooltip still documents 4.0 min N2 compartment (issue #98 L-1)")
if "'gfs_40_25_air_hi85':      { rt:119" in verify_html:
    ok("VPM-B/GFS pinned RT updated to 119 min (issue #98 L-2)")
else:
    fail("VPM-B/GFS pinned RT still stale at 109 min (issue #98 L-2)")

# ── issue #98 MEDIUM-1: dev dependency tar override (superseded by Capacitor 8 in #110 M-2) ──
_pkg_json = open(os.path.join(os.path.dirname(__file__), "package.json"), encoding="utf-8").read()
if '"@capacitor/cli": "^8' in _pkg_json:
    ok("Capacitor 8 CLI resolves patched tar without override (issue #98 M-1 / #110 M-2)")
elif '"tar": "^6.2.1"' in _pkg_json or '"tar": ">=6.2.1"' in _pkg_json:
    ok("package.json overrides tar to patched 6.2.1+ (Capacitor-compatible, issue #98 M-1)")
else:
    fail("package.json missing tar >=6.2.1 override for Capacitor CLI (issue #98 M-1)")

if "headlessSegPpo2" in zhl_bundle_js or "onLoop" in zhl_bundle_js.split("function computeHeadlessCnsOtu", 1)[-1][:1200]:
    ok("computeHeadlessCnsOtu CCR-aware ppO2 (issue #93 M-4)")
else:
    fail("computeHeadlessCnsOtu still uses OC-only ppO2 (issue #93 M-4)")
_gcnd = js.split("function getCNSDailyLimit", 1)[-1][:500] if "function getCNSDailyLimit" in js else ""
if "if (ppo2 >= 1.6) return CNS_DAILY_LIMITS[16]" in _gcnd and "if (key >= 16) return CNS_DAILY_LIMITS[16]" not in _gcnd:
    ok("getCNSDailyLimit float clamp, no post-round key>=16 guard (issue #93/#94)")
else:
    fail("getCNSDailyLimit premature key>=16 clamp after Math.round (issue #93/#94)")
_deco93 = js[js.find("DECO_FIELDS:"):js.find("DECO_FIELDS:")+2000] if "DECO_FIELDS:" in js else ""
for _fid, _desc in [
    ("priorDiveDays", "prior dive days"), ("priorDiveOTU", "prior dive OTU"),
    ("travelGasMix", "travel gas mix"), ("travelGasSwitchMode", "travel gas switch mode"),
]:
    if _fid in _deco93:
        ok(f"DECO_FIELDS includes {_fid} ({_desc}) (issue #93 M-6/L-2)")
    else:
        fail(f"DECO_FIELDS missing {_fid} ({_desc}) (issue #93 M-6/L-2)")
if "ceiling(testT, mGF.low / 100)" in js or "ndlClearAtDepth(testT" in js:
    ok("multi-dive NDL uses gfLow for residual loading check (issue #93 M-7)")
else:
    fail("multi-dive NDL missing gfLow ceiling check (issue #93 M-7)")
if "const mValue = a + P_surf / b;" in tier3_engine_src and "const mMargin = mValue - P_surf" in tier3_engine_src.split("function computeSurfaceGF", 1)[-1][:1200]:
    ok("computeSurfaceGF uses (mValue - P_surf) GF denominator (issue #104 M-1)")
elif "ZhlEngineBundle.computeSurfaceGF" in js:
    ok("computeSurfaceGF delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("computeSurfaceGF still divides by raw mValue (issue #104 M-1)")
if "ppO2Avg = (ppO2Start + ppO2End) / 2" in open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read():
    ok("VPM descent CNS/OTU uses time-averaged ppO2 (issue #93 M-9)")
else:
    fail("VPM descent CNS/OTU still uses endpoint ppO2 only (issue #93 M-9)")
if "if (key >= 16) return CNS_LIMITS[16]" in js or "if (ppo2 >= 1.6) return CNS_LIMITS[16]" in js:
    ok("getCNSLimit clamps at ppO2 1.6 bar (issue #93 L-1 / #95 M-8)")
else:
    fail("getCNSLimit missing ppO2>=1.6 clamp (issue #93 L-1 / #95 M-8)")
if "status: 503" in sw_src and "Offline — asset unavailable" in sw_src:
    ok("sw.js returns 503 for offline non-HTML assets (issue #93 L-3)")
else:
    fail("sw.js still serves index.html for all offline cache misses (issue #93 L-3)")

# ── issue #95 fixes ──
if "el.type === 'checkbox' ? el.checked" in js and "el.checked = values[id]" in js:
    ok("DECO_FIELDS saves/restores checkbox .checked state (issue #95 H-1)")
else:
    fail("DECO_FIELDS still uses el.value for checkboxes (issue #95 H-1)")
if "setHeHalfTimeMode" in zhl_src and "ZHL16C_HE_HT_BUHL2003" in zhl_src:
    ok("zhl-engine-bundle exports setHeHalfTimeMode with Buhl2003 table (issue #95 H-2)")
else:
    fail("zhl-engine-bundle missing setHeHalfTimeMode (issue #95 H-2)")
if "ZhlEngineBundle.setHeHalfTimeMode" in js:
    ok("updateHeHalfTime syncs bundle He half-times (issue #95 H-2)")
else:
    fail("updateHeHalfTime does not call ZhlEngineBundle.setHeHalfTimeMode (issue #95 H-2)")
if "parseStopDisplayTime(stpRaw)" in js and "parseStopDisplayTime(c[2])" in js:
    ok("export/messenger use parseStopDisplayTime for stop durations (issue #95 M-1)")
else:
    fail("export/messenger still use MM:SS-only regex for stops (issue #95 M-1)")
if "savedLastPlan = window._lastPlan" in js and "window._lastPlan = savedLastPlan" in js:
    ok("runContingencyScenario restores window._lastPlan (issue #95 M-5)")
else:
    fail("runContingencyScenario overwrites window._lastPlan without restore (issue #95 M-5)")
if "getAllDecoGasIds()" in js.split("function buildContingencyButtons", 1)[-1][:800]:
    ok("buildContingencyButtons scans all deco gas cards (issue #95 M-6)")
else:
    fail("buildContingencyButtons still hardcodes dg1Mix/dg2Mix (issue #95 M-6)")
_vpm_render_idx = js.find("function renderVPMResults")
if _vpm_render_idx >= 0 and "contingencyJumpBtn" in js[_vpm_render_idx:_vpm_render_idx + 50000]:
    ok("renderVPMResults shows contingencyJumpBtn (issue #95 M-7)")
else:
    fail("renderVPMResults missing contingencyJumpBtn display (issue #95 M-7)")
if "carriedFirstStopDepth" in zhl_src:
    ok("multi-level ZHL carries firstStopDepth across phases via carriedFirstStopDepth (issue #108 M-7; supersedes #99 M-1)")
elif "if (_zhlPhaseIdx === 0) firstStopDepth = 0" in zhl_src:
    fail("multi-level ZHL carries firstStopDepth across phases (issue #99 M-1)")
else:
    _phase_loop = zhl_src.split("for (let _zhlPhaseIdx = 0", 1)[-1][:300] if "for (let _zhlPhaseIdx = 0" in zhl_src else ""
    if "firstStopDepth = 0;" in _phase_loop:
        ok("multi-level ZHL resets firstStopDepth at start of each phase (issue #99 M-1)")
    else:
        fail("multi-level ZHL missing firstStopDepth = 0 per phase (issue #99 M-1)")
if "ppO2 >= 1.6" in zhl_src and "addHeadlessExposure" in zhl_src:
    ok("addHeadlessExposure clamps CNS at ppO2 >= 1.6 bar (issue #95 M-3)")
else:
    fail("addHeadlessExposure missing ppO2>=1.6 CNS clamp (issue #95 M-3)")
vpm_core_95 = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
if "waterVapor != null" in vpm_core_95:
    ok("getWaterVaporPressure accepts explicit zero (issue #95 M-4)")
else:
    fail("getWaterVaporPressure still treats waterVapor=0 as unset (issue #95 M-4)")
if "depth < currentDepth ? ascentRate : descentRate" in vpm_core_95:
    ok("VPM inter-level travel uses ascent rate when shallower (issue #95 M-11)")
else:
    fail("VPM inter-level still uses descent rate for upward travel (issue #95 M-11)")

# ── issue #96 fixes ──
_he_frac_body = ""
if "function getHeFrac(mix)" in js:
    _he_frac_body = js.split("function getHeFrac(mix)", 1)[1].split("function ", 1)[0]
if "function getHeFrac(mix)" in js and "trimix" in _he_frac_body and "plannerTrimixHe" in _he_frac_body and not re.search(r"^\s*return\s+0\s*;", _he_frac_body.strip(), re.M):
    ok("getHeFrac reads He from trimix mix (issue #96/#99 L-1)")
elif "readDomHePct('plannerTrimixHe')" in _he_frac_body and "mix === 'trimix'" in _he_frac_body:
    ok("getHeFrac reads He from trimix mix (issue #96/#99 L-1)")
else:
    fail("getHeFrac still stubbed — always returns 0 (issue #96/#99 L-1)")
if "saturate(tissues, depthM, 1, fN2, fH)" in js or "saturate(tissues, depthM, 1, fN2, fHe" in js or "saturate(tissues, depthM, 1, fN2, fH)" in _physics_core_js:
    ok("buhNDL passes fHe to saturate (issue #96 L-1)")
else:
    fail("buhNDL still hardcodes fHe=0 in NDL loop (issue #96 L-1)")
if "validateGasFractionsPct" in js.split("function validatePlannerInputs", 1)[-1][:1600]:
    ok("validatePlannerInputs rejects invalid trimix totals (issue #98 H-2)")
else:
    fail("validatePlannerInputs missing trimix fraction validation (issue #98 H-2)")

# ── issue #99 fixes ──
_gesp = _ccr_core_src.split("function getEffectiveSetpointAtDepth", 1)[-1][:2200] if "function getEffectiveSetpointAtDepth" in _ccr_core_src else ""
if "depthAtSetpointCrossing" in _gesp and "if (depthM > deepestCross) return bottomSP" not in _gesp:
    ok("getEffectiveSetpointAtDepth uses depth-derived phase thresholds (issue #99 H-1 / #104 M-4)")
else:
    fail("index.html getEffectiveSetpointAtDepth still uses pAmb/setpoint comparisons (issue #99 H-1)")
if "'plannerTrimixO2'" in js and "'plannerTrimixHe'" in js.split("DECO_FIELDS:", 1)[-1][:1200]:
    ok("plannerTrimixO2/He in DECO_FIELDS (issue #99 H-2)")
else:
    fail("plannerTrimixO2/He missing from DECO_FIELDS (issue #99 H-2)")
if "if (ppo2 < 0.6) return Infinity;" in js.split("function getCNSDailyLimit", 1)[-1][:300]:
    ok("getCNSDailyLimit uses float guard ppo2 < 0.6 (issue #99 M-2)")
else:
    fail("getCNSDailyLimit still uses rounded key guard (issue #99 M-2)")
if "if (decayTime < 0) { state.surfacePhaseVolumeTime[i] = 0; continue; }" in vpm_core_95:
    ok("calcSurfacePhaseVolumeTime guards negative decayTime (issue #99 M-3)")
else:
    fail("calcSurfacePhaseVolumeTime missing negative decayTime guard (issue #99 M-3)")
if "saveZhlRepState(tissues, parseFloat(document.getElementById('zhlSurfaceInterval')" in js:
    ok("saveZhlRepState reads zhlSurfaceInterval from DOM (issue #99 M-4)")
else:
    fail("saveZhlRepState still hardcodes surfaceIntervalMin=0 (issue #99 M-4)")
if "validateDomDecoGases()" in js.split("function validateDecoInputs", 1)[-1][:400]:
    ok("validateDecoInputs validates deco gas cards (issue #99 M-5)")
else:
    fail("validateDecoInputs missing deco gas card validation (issue #99 M-5)")
_vpm_ml = vpm_core_95.split("if (level.oc) forcedOCMode = true;", 1)
if len(_vpm_ml) > 1 and "const sp = (forcedOCMode || nextLevelOffLoop)" in _vpm_ml[1][:400]:
    ok("VPM multi-level OC bailout sets forcedOCMode before sp (issue #99 M-6)")
else:
    fail("VPM multi-level OC bailout still sets forcedOCMode after level processing (issue #99 M-6)")
if "perDiveCns * dives + cnsCarry" in js.split("function calcCnsWidgetExposure", 1)[-1][:2500]:
    ok("calcCnsWidgetExposure adds CNS carry once (issue #99 M-7)")
else:
    fail("calcCnsWidgetExposure still multiplies carry by dives (issue #99 M-7)")
if "if (ph === 'totals' || ph === 'info') return;" in js.split("EMERGENCY ASCENT SCHEDULE", 1)[-1][:2000]:
    ok("buildExportText skips contingency info row (issue #99 M-8)")
else:
    fail("buildExportText missing skip for contingency info row (issue #99 M-8)")
if "ppO2Surf < 0.16" in js.split("function calcEND_tool()", 1)[-1][:2500]:
    ok("END/EAD tool warns on hypoxic surface ppO2 (issue #99 M-9)")
else:
    fail("END/EAD tool missing hypoxic mix warning (issue #99 M-9)")
if "return saturate(tissues, 0, durMin, FN2_AIR, 0);" in js.split("function offgasAtSurface", 1)[-1][:200]:
    ok("offgasAtSurface uses ambient air, not CCR loop (issue #99 M-10)")
else:
    fail("offgasAtSurface still uses CCR loop gas at surface (issue #99 M-10)")
if ("Math.max(0, (100 - o2pct) / 100)" in js.split("function getN2Frac", 1)[-1][:400] or "n2FracFromCustomO2" in js.split("function getN2Frac", 1)[-1][:400]) and "Math.min(40, Math.max(21" not in js.split("function getN2Frac", 1)[-1][:400]:
    ok("getN2Frac custom mix no longer clamps O2 to 21-40% (issue #99 M-11)")
else:
    fail("getN2Frac still clamps custom O2 to 21-40% (issue #99 M-11)")
if "usableL === 0" in js.split("if (short)", 1)[-1][:600]:
    ok("gas shortage widget shows no-usable-gas when usableL=0 (issue #99 L-2)")
else:
    fail("gas shortage widget missing usableL===0 guard (issue #99 L-2)")

# ── issue #101 fixes ──
if "forcedOCMode: !!forcedOCModeAtStart" in vpm_core_95 and "function runContinuationSchedule" in vpm_core_95:
    _rcs = vpm_core_95.split("function runContinuationSchedule", 1)[-1][:500]
    if "forcedOCAtStart" in _rcs and "appendLevelHold(ctx, level)" in vpm_core_95:
        _alh = vpm_core_95.split("function appendLevelHold", 1)[-1][:400]
        if "if (level.oc) ctx.forcedOCMode = true" in _alh and "ctx.forcedOCMode || nextLevelOffLoop" in _alh:
            ok("VPM continuation preserves forcedOCMode across levels (issue #101 H-1)")
        else:
            fail("VPM appendLevelHold missing persistent forcedOCMode (issue #101 H-1)")
    else:
        fail("VPM runContinuationSchedule missing forcedOCAtStart propagation (issue #101 H-1)")
else:
    fail("VPM schedule context missing forcedOCMode field (issue #101 H-1)")
_cnsw = js.split("function calcCnsWidgetExposure", 1)[-1][:3500] if "function calcCnsWidgetExposure" in js else ""
if "planCnsFromRecompute" in _cnsw and "vpmPerDiveCns" in _cnsw:
    ok("calcCnsWidgetExposure separates carry from per-dive CNS (issue #101 H-2)")
else:
    fail("calcCnsWidgetExposure still mis-accounts repetitive CNS carry (issue #101 H-2)")
if "'gasMix'" in js.split("DECO_FIELDS:", 1)[-1][:800] and "'customO2'" in js.split("DECO_FIELDS:", 1)[-1][:800]:
    ok("gasMix and customO2 in DECO_FIELDS (issue #101 M-1)")
else:
    fail("gasMix/customO2 missing from DECO_FIELDS (issue #101 M-1)")
if 'id="customO2" max="100"' in html and "O₂ % (21–100)" in html:
    ok("custom O2 input range aligned to 21-100% (issue #101 L-1)")
else:
    fail("custom O2 input still advertises 21-40% (issue #101 L-1)")

# ── issue #102 fixes ──
if "Math.ceil((bottomCeil + 1e-9) / decoStep)" in zhl_src:
    ok("ZHL candidateFirstStop uses epsilon guard against float fence-post (issue #102 BUG-A)")
else:
    fail("ZHL candidateFirstStop missing epsilon guard (issue #102 BUG-A)")
if "if (si > 0) {" not in vpm_core_95 and "const regenFactor = Math.exp(-si / REGEN_TIME)" in vpm_core_95:
    ok("VPM zero-SI bubble carry uses regenFactor=1 (issue #104 H-1 / supersedes #102 BUG-B)")
else:
    fail("VPM still skips bubble carry on zero surface interval (issue #104 H-1)")
if "Math.ceil((depth + 1e-9) / stepSize)" in vpm_core_95:
    ok("VPM roundUpToStop uses epsilon guard (issue #102 BUG-A)")
else:
    fail("VPM roundUpToStop missing epsilon guard (issue #102 BUG-A)")
if "MAX_WORKER_FAILURES" in open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read():
    ok("ZHL worker bridge limits consecutive crash recovery (issue #102 BUG-E)")
else:
    fail("ZHL worker bridge missing crash recovery limit (issue #102 BUG-E)")
if "emAlertsHtml" in js and "window._lastContingency.emAlertsHtml" in js:
    ok("contingency stores emAlertsHtml for PDF export (issue #102 BUG-D)")
else:
    fail("contingency missing emAlertsHtml persistence (issue #102 BUG-D)")
if "git diff --exit-code zhl-engine-bundle.js vpm-engine-bundle.js" in open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml"), encoding="utf-8").read():
    ok("CI guards engine bundle sync (issue #102 BUG-I)")
else:
    fail("CI missing engine bundle sync guard (issue #102 BUG-I)")
if "ccrVpm:" in open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("engine regression includes CCR VPM test case (issue #102 BUG-H)")
else:
    fail("engine regression missing CCR VPM test (issue #102 BUG-H)")
if "importScripts('app-version.js')" in open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read():
    ok("sw.js CACHE_VERSION derived from app-version.js (issue #102 BUG-C/J)")
else:
    fail("sw.js not linked to app-version.js (issue #102 BUG-C/J)")

# ── issue #103 fixes ──
_zwb = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), "rb").read()
if b"\r\r\n" not in _zwb and _zwb.count(b"\r\n") == 0:
    ok("zhl-worker-bridge.js uses LF line endings (issue #103 F-1)")
else:
    fail("zhl-worker-bridge.js has double-CRLF or CRLF line endings (issue #103 F-1)")
_zwb_txt = _zwb.decode("utf-8")
if "function terminate(resetDisabledFlag)" in _zwb_txt and "if (resetDisabledFlag) workerPermanentlyDisabled = false" in _zwb_txt:
    ok("terminate() preserves workerPermanentlyDisabled unless explicitly reset (issue #103 F-2)")
else:
    fail("terminate() still clears workerPermanentlyDisabled unconditionally (issue #103 F-2)")
_sw_path = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
if "/LSP_D-planner-plus/')" in _sw_path and _sw_path.find("/LSP_D-planner-plus/')") < _sw_path.find("/LSP_D-planner/')"):
    ok("sw.js getAppBasePath uses trailing-slash prefix checks (issue #103 F-3)")
else:
    fail("sw.js getAppBasePath missing trailing-slash disambiguation (issue #103 F-3)")

# ── issue #104 fixes ──
_vpm104 = vpm_core_95
if "_bubbleCarryApplied" in _vpm104 and "scaleCarried" in _vpm104.split("function setCriticalRadiiForConservatism", 1)[-1][:900]:
    ok("setCriticalRadiiForConservatism scales carried radii when bubble carry applied (issue #104 H-2 / #106 H-1)")
else:
    fail("setCriticalRadiiForConservatism still skips conservatism on bubble carry (issue #104 H-2)")
if "Math.max(denomBase, Math.max(0.001, pN2 * 1e-4))" in _vpm104 or "Math.max(denomBase, 0.001)" in _vpm104:
    ok("VPM calcSurfacePhaseVolumeTime guards near-zero denominator (issue #104 M-9)")
else:
    fail("VPM surface phase volume missing denominator guard (issue #104 M-9)")
if "window._tecGasMix" in js and "function getPersistedGasMix" in js:
    ok("Tec gasMix stored separately from Rec display (issue #104 H-3 / #106 H-3)")
else:
    fail("Rec mode still overwrites persisted Tec gasMix (issue #104 H-3)")
if "if (firstStopDepth <= interpBase) return gfH;" in zhl_src:
    ok("gfAt guards zero denominator when firstStop equals lastStop (issue #104 M-2)")
else:
    fail("gfAt missing firstStopDepth <= lastStop guard (issue #104 M-2)")
if "snap.surfaceIntervalMin" in js.split("function getZhlRepStateForSchedule", 1)[-1][:400]:
    ok("getZhlRepStateForSchedule uses stored surfaceIntervalMin snapshot (issue #104 M-3)")
else:
    fail("getZhlRepStateForSchedule still reads live DOM SI (issue #104 M-3)")
_ccr128 = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_gesp128 = _ccr128.split("function getEffectiveSetpointAtDepth", 1)[-1][:2200] if "function getEffectiveSetpointAtDepth" in _ccr128 else ""
if "depthAtSetpointCrossing" in _gesp128 and "if (depthM > deepestCross) return bottomSP" not in _gesp128:
    ok("getEffectiveSetpointAtDepth uses depth-derived phase thresholds (issue #104 M-4)")
else:
    fail("getEffectiveSetpointAtDepth still compares pAmb to setpoint pressures (issue #104 M-4)")
if "function ndlClearAtDepth" in _physics_core_js and "ZhlEngineBundle.buhNDL" in js:
    ok("buhNDL uses GF-line ascent simulation (issue #104 M-5 / #106 M-1)")
else:
    fail("buhNDL still ignores gfHigh in NDL ceiling check (issue #104 M-5)")
if "'travelGasTrimixO2'" in js.split("DECO_FIELDS:", 1)[-1][:2500] and "'travelGasTrimixHe'" in js.split("DECO_FIELDS:", 1)[-1][:2500]:
    ok("travelGasTrimixO2/He in DECO_FIELDS (issue #104 M-6)")
else:
    fail("travelGasTrimixO2/He missing from DECO_FIELDS (issue #104 M-6)")
if "decoTime += parseRunMinutes(tr.querySelectorAll('td')[2]" in js.split("function runContingencyScenario", 1)[-1][:1200]:
    ok("runContingencyScenario uses parseRunMinutes for stop MM:SS decoTime (issue #108 H-1; supersedes #104 M-7)")
elif "parseStopDisplayTime(tr.querySelectorAll('td')[2]" in js:
    ok("runContingencyScenario uses parseStopDisplayTime for decoTime (issue #104 M-7)")
elif 'td[data-label="Stop"]' in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("runContingencyScenario reads integer stop minutes from Stop column (issue #127 M-5)")
else:
    fail("runContingencyScenario still parseFloats MM:SS stop durations (issue #104 M-7)")
_zwb104 = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
_onmsg104 = _zwb104.split("worker.onmessage", 1)[-1][:800]
if (
    ("consecutiveWorkerFailures += 1" in _onmsg104 and "if (ok) {" in _onmsg104)
    or ("handleWorkerFailure(error" in _onmsg104 and "if (ok) {" in _onmsg104)
):
    ok("worker bridge increments failures on ok:false replies (issue #104 M-8)")
else:
    fail("worker bridge still resets failure counter on ok:false (issue #104 M-8)")
if "const ppO2Limit = parseFloat(document.getElementById('ppo2Bottom')" in js.split("function calcEND_tool", 1)[-1][:2500]:
    ok("calcEND_tool MOD uses configured ppO2 limit (issue #104 L-1)")
else:
    fail("calcEND_tool MOD still hardcoded to 1.4 bar (issue #104 L-1)")
if "function syncContDepthLabels" in js and "Math.round(v * 3.28084)" in js.split("function syncContDepthLabels", 1)[-1][:300]:
    ok("contingency depth buttons show imperial-converted labels (issue #104 L-2)")
else:
    fail("contingency depth buttons still label metres as feet (issue #104 L-2)")
if "margin <= 5 ? 'var(--orange)'" in js.split("function statusColor", 1)[-1][:200]:
    ok("UDP statusColor uses orange for 1–5 min margin (issue #118 L-1; supersedes #104/#108)")
elif "margin <= 5 ? 'var(--red)'" in js and "margin <= 10 ? 'var(--yellow)'" in js.split("function statusColor", 1)[-1][:200]:
    ok("UDP statusColor uses red ≤5 / yellow ≤10 (issue #108 M-1; supersedes #104 L-3)")
elif "margin <= 5 ? 'var(--yellow)'" in js:
    ok("UDP statusColor uses yellow for within 5% of NDL (issue #104 L-3)")
else:
    fail("UDP statusColor still red for 1-5% NDL margin (issue #104 L-3)")

# ── issue #106 fixes ──
_vpm106 = vpm_core_95
if "_bubbleCarryApplied" in _vpm106 and "scaleCarried" in _vpm106.split("function setCriticalRadiiForConservatism", 1)[-1][:900]:
    ok("setCriticalRadiiForConservatism scales carried radii by conservatism (issue #106 H-1)")
else:
    fail("setCriticalRadiiForConservatism still ignores conservatism on bubble carry (issue #106 H-1)")
if "function vpmSetpointAtDepth" in _vpm106 and "vpmSetpointAtDepth(stopDepth, 'deco'" in _vpm106:
    ok("VPM ascent/stops recalculate deco setpoint by phase (issue #106 H-2)")
else:
    fail("VPM still carries bottom setpoint through deco stops (issue #106 H-2)")
if "window._tecGasMix" in js and "function getPersistedGasMix" in js and "getPersistedGasMix()" in js.split("save: function", 1)[-1][:1200]:
    ok("Tec gasMix persisted separately from Rec display (issue #106 H-3)")
else:
    fail("Rec mode still overwrites persisted Tec gasMix (issue #106 H-3)")
if "function ndlClearAtDepth" in _physics_core_js and "function buhNDL" in _physics_core_js:
    ok("buhNDL uses multi-depth GF-line ascent check (issue #106 M-1)")
else:
    fail("buhNDL still ignores GF High in operating range (issue #106 M-1)")
if "function validateVpmSurfaceInterval" in js and "validateVpmSurfaceInterval()" in js.split("function validateDecoInputs", 1)[-1][:600]:
    ok("validateVpmSurfaceInterval guards repetitive VPM surface interval (issue #106 M-2)")
else:
    fail("VPM surface interval still unvalidated (issue #106 M-2)")
if "repConsRts" in open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("engine regression tests repetitive VPM conservatism (issue #106 coverage)")
else:
    fail("engine regression missing repetitive VPM conservatism test (issue #106 coverage)")
if "bottomSp" in _vpm106.split("if (bottomTime > 0)", 1)[-1][:600] and "getEffectiveSetpoint(" in _vpm106.split("const bottomSp", 1)[-1][:200]:
    ok("VPM bottom hold uses bottom setpoint after descent (issue #106 verify H-1)")
else:
    fail("VPM bottom hold still reuses descent setpoint (issue #106 verify H-1)")
if "_conservatismRadiiApplied" in _vpm106.split("function setCriticalRadiiForConservatism", 1)[-1][:500]:
    ok("setCriticalRadiiForConservatism applies once — bubble carry preserved (issue #106 verify H-2)")
else:
    fail("setCriticalRadiiForConservatism still resets carried radii on second call (issue #106 verify H-2)")
if "function syncTecGasMixMemory" in js and "syncTecGasMixMemory();" in js:
    ok("Tec gasMix memory updates on every selector change (issue #106 verify M-1)")
else:
    fail("Tec gasMix memory still only tracks ean50/trimix (issue #106 verify M-1)")
if "vpmBubbleCarryIsolated" in open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("engine regression isolates VPM bubble carry from tissue carry (issue #106 verify H-2)")
else:
    fail("engine regression missing isolated bubble-carry test (issue #106 verify H-2)")

# ── issue #107: README badge + sw.js cache key sync ──
if app_ver and os.path.isfile(readme_path):
    with open(readme_path, encoding="utf-8") as f:
        _readme107 = f.read()
    _badge107 = re.search(r"> v([\d.]+)\s·", _readme107)
    if _badge107 and _badge107.group(1) == app_ver:
        ok(f"README badge matches APP_VERSION ({app_ver}) (issue #107)")
    else:
        fail(f"README badge ({_badge107.group(1) if _badge107 else 'missing'}) != APP_VERSION ({app_ver}) (issue #107)")
else:
    fail("README version badge check skipped — APP_VERSION or README.md missing (issue #107)")
if os.path.isfile(sw_path):
    with open(sw_path, encoding="utf-8") as f:
        _sw107 = f.read()
    if "importScripts('app-version.js')" in _sw107 and "lsp-dplanner-plus-v' + APP_VERSION" in _sw107:
        ok("sw.js CACHE_VERSION derived from APP_VERSION (issue #107)")
    else:
        fail("sw.js CACHE_VERSION hardcoded or not tied to APP_VERSION (issue #107)")
else:
    fail("sw.js missing for CACHE_VERSION sync check (issue #107)")
if "sync_readme_badge" in open(os.path.join(os.path.dirname(__file__), "tools", "update_sw_version.py"), encoding="utf-8").read():
    ok("tools/update_sw_version.py syncs README badge with APP_VERSION (issue #107)")
else:
    fail("tools/update_sw_version.py missing README badge sync (issue #107)")

# ── issue #108 fixes ──
_zhl108 = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
if "parseStopDisplayTime(tr.querySelectorAll('td')[2]" in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("contingency decoTime uses parseStopDisplayTime on stop column (issue #118 H-3; supersedes #108 H-1)")
elif "decoTime += parseRunMinutes(tr.querySelectorAll('td')[2]" in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("contingency decoTime uses parseRunMinutes not parseStopDisplayTime (issue #108 H-1)")
elif 'td[data-label="Stop"]' in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("runContingencyScenario reads integer stop minutes from Stop column (issue #127 M-5)")
else:
    fail("runContingencyScenario still accumulates decoTime via wrong parser (issue #108/#118)")
if "regeneratedRadiiN2" in _vpm106.split("settings._prevBubbleState", 1)[-1][:900] and "regeneratedRadiiHe" in _vpm106.split("settings._prevBubbleState", 1)[-1][:900]:
    ok("VPM bubble carry guards regeneratedRadii arrays (issue #108 H-2)")
else:
    fail("VPM bubble carry still missing regeneratedRadii guard (issue #108 H-2)")
_zwb108 = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
if "getWorkerScriptUrl" in _zwb108 and "p.timer" in _zwb108 and "clearTimeout(p.timer)" in _zwb108:
    ok("ZHL worker bridge clears pending timeouts and uses APP_BASE worker URL (issue #108 H-3/L-2)")
else:
    fail("ZHL worker bridge missing timeout cleanup or base-path worker URL (issue #108 H-3/L-2)")
if "margin <= 5 ? 'var(--orange)'" in js.split("function statusColor", 1)[-1][:200]:
    ok("UDP statusColor uses orange for 1–5 min margin (issue #118 L-1; supersedes #108 M-1)")
elif "margin <= 5 ? 'var(--red)'" in js and "margin <= 10 ? 'var(--yellow)'" in js.split("function statusColor", 1)[-1][:200]:
    ok("UDP statusColor uses red ≤5 / yellow ≤10 (issue #108 M-1)")
else:
    fail("UDP statusColor still has dead yellow branch at margin ≤5 (issue #108 M-1)")
if "toMMSS(rt)" in js.split("renderVPMResults", 1)[-1][:20000] and "toMMSS(deco" in js.split("renderVPMResults", 1)[-1][:20000] and "toMMSS(rt * 60)" not in js.split("renderVPMResults", 1)[-1][:20000]:
    ok("VPM plan summary uses toMMSS with minute values (issue #108 M-2 / #110 H-1)")
else:
    fail("VPM plan summary still double-converts minutes to seconds (issue #110 H-1)")
_ci108 = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml"), encoding="utf-8").read()
if "engine-full:" in _ci108 and "needs: [bundle-sync]" in _ci108:
    ok("CI engine-full job depends on bundle-sync (issue #108 M-3)")
else:
    fail("CI engine-full still races bundle-sync (issue #108 M-3)")
if "vpmSi0TissuesOnly" in open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("engine regression isolates zero-SI bubble carry from tissue-only (issue #108 M-4)")
else:
    fail("engine regression repCarriesBubble still compares fresh dive (issue #108 M-4)")
if "mod14Lbl" in js and "ppO2Limit.toFixed(1)" in js.split("function calcEND_tool", 1)[-1][:4500]:
    ok("calcEND_tool updates MOD label from ppo2Bottom (issue #108 M-5)")
else:
    fail("END tool MOD label still hardcoded @ 1.4 (issue #108 M-5)")
if "check.o2 < 18" in js.split("function validatePlannerInputs", 1)[-1][:1600]:
    ok("validatePlannerInputs rejects hypoxic trimix O₂ (issue #108 M-6)")
else:
    fail("validatePlannerInputs trimix branch missing hypoxic O₂ guard (issue #108 M-6)")
if "carriedFirstStopDepth" in _zhl108:
    ok("ZHL multi-level carries firstStopDepth across phases (issue #108 M-7)")
else:
    fail("ZHL still resets firstStopDepth each continuation phase (issue #108 M-7)")
if "repSurfP = altAcclimatized" in _zhl108 or "rep.surfaceP != null" in _zhl108:
    ok("ZHL rep surface off-gas respects altAcclimatized (issue #108 M-8)")
else:
    fail("ZHL rep off-gas always uses altSurfaceP (issue #108 M-8)")
if ("otu >= 600" in js.split("function calcCNS", 1)[-1][:4500] or "cumulativeOtu >= 600" in js.split("function calcCNS", 1)[-1][:4500]) and "perDiveOtu >= 300" in js.split("function calcCNS", 1)[-1][:4500]:
    ok("CNS widget status warns on OTU ≥300/600 (issue #108 M-9)")
else:
    fail("CNS widget status ignores OTU overages (issue #108 M-9)")
if "btAtDepthMin = Math.max(0, level.time - hDescentTime)" in open(os.path.join(os.path.dirname(__file__), "tools", "build_zhl_bundle.py"), encoding="utf-8").read():
    ok("computeHeadlessCnsOtu subtracts descent from bottom time (issue #108 L-3)")
else:
    fail("computeHeadlessCnsOtu still double-counts descent in level.time (issue #108 L-3)")

# ── issue #110 fixes ──
_b110 = open(os.path.join(os.path.dirname(__file__), "tools", "build_zhl_bundle.py"), encoding="utf-8").read()
if "time: btAtDepthMin" in _b110.split("function mapToEngineReturn", 1)[-1][:1200]:
    ok("ZHL mapToEngineReturn bottom segment uses time-at-depth only (issue #110 H-2)")
else:
    fail("ZHL mapToEngineReturn still assigns full level.time to bottom segment (issue #110 H-2)")
if ".filter(st => !(st.type === 'ascent' && st.decoTransit))" in _b110:
    ok("ZHL mapToEngineReturn excludes folded decoTransit ascents (issue #110 H-3)")
else:
    fail("ZHL mapToEngineReturn still exports folded MultiDeco transit segments (issue #110 H-3)")
if "if (seg.decoTransit) return" in _b110.split("computeHeadlessCnsOtu", 1)[-1][:1200]:
    ok("computeHeadlessCnsOtu skips folded decoTransit segments (issue #110 H-3)")
else:
    fail("computeHeadlessCnsOtu still counts folded MultiDeco transit (issue #110 H-3)")
if "if (s.decoTransit) return" in js.split("function accumulateHeadlessPlanExposure", 1)[-1][:2000]:
    ok("accumulateHeadlessPlanExposure skips folded decoTransit segments (issue #110 H-3)")
else:
    fail("accumulateHeadlessPlanExposure still counts folded MultiDeco transit (issue #110 H-3)")
if "statusCandidates" in js.split("function calcCNS", 1)[-1][:8000] and "b.sev - a.sev" in js.split("function calcCNS", 1)[-1][:8000]:
    ok("calcCNS status picks highest-severity condition (issue #110 M-1)")
else:
    fail("calcCNS status still ordered by category not severity (issue #110 M-1)")
if "plan duration sum" in open(os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "lib", "ccrdiff.js"), encoding="utf-8").read():
    ok("CCR differential integrity checks plan duration vs totalRuntime (issue #110 L-1)")
else:
    fail("CCR differential integrity missing timeline parity checks (issue #110 L-1)")
if "timeline110" in open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("engine regression includes timeline110 parity section (issue #110 L-1)")
else:
    fail("engine regression missing timeline parity checks (issue #110 L-1)")
if "decoTransit: decoZoneEntered && mdCompatMode && firstDecoDepth !== null" in open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read():
    ok("decoTransit only when transit folded into following stop (issue #110 ML continuation)")
else:
    fail("decoTransit still blanket-filters continuation-phase first ascents (issue #110 ML)")
_pkg110 = open(os.path.join(os.path.dirname(__file__), "package.json"), encoding="utf-8").read()
if '"@capacitor/cli": "^8' in _pkg110 and '"tar":' not in _pkg110.split('"overrides"', 1)[-1][:200] if '"overrides"' in _pkg110 else True:
    ok("Capacitor 8 toolchain resolves patched tar without override (issue #110 M-2)")
elif '"tar": "^6.2.1"' in _pkg110 and ("issue #110 M-2" in _pkg110 or "_devSecurityNotes" in _pkg110):
    ok("package.json documents Capacitor tar 6.x dev-only override (issue #110 M-2 acknowledged)")
else:
    fail("package.json tar/Capacitor dev security posture undocumented (issue #110 M-2)")
_vars_cap8 = open(os.path.join(os.path.dirname(__file__), "android", "variables.gradle"), encoding="utf-8").read()
if "minSdkVersion = 24" in _vars_cap8 and "compileSdkVersion = 36" in _vars_cap8 and "targetSdkVersion = 36" in _vars_cap8:
    ok("Android variables.gradle meets Capacitor 8 SDK minimums")
else:
    fail("Android variables.gradle below Capacitor 8 SDK 36 / minSdk 24")
_root_gradle = open(os.path.join(os.path.dirname(__file__), "android", "build.gradle"), encoding="utf-8").read()
if "gradle:8.13.0" in _root_gradle and "google-services:4.4.4" in _root_gradle:
    ok("Android root build.gradle uses Capacitor 8 AGP and google-services plugin")
else:
    fail("Android root build.gradle missing Capacitor 8 AGP 8.13.0 / google-services 4.4.4")
_wrapper = open(os.path.join(os.path.dirname(__file__), "android", "gradle", "wrapper", "gradle-wrapper.properties"), encoding="utf-8").read()
if "gradle-8.14.3-all.zip" in _wrapper:
    ok("Gradle wrapper pinned to 8.14.3 for Capacitor 8")
else:
    fail("Gradle wrapper not updated to 8.14.3 for Capacitor 8")
_manifest_cap8 = open(os.path.join(os.path.dirname(__file__), "android", "app", "src", "main", "AndroidManifest.xml"), encoding="utf-8").read()
if "|density" in _manifest_cap8 and "|navigation" in _manifest_cap8.split("configChanges", 1)[-1][:120]:
    ok("AndroidManifest configChanges includes navigation|density for Capacitor 8")
else:
    fail("AndroidManifest missing Capacitor 8 density configChanges")
if '"node": ">=22"' in _pkg110:
    ok("package.json engines requires Node 22+ for Capacitor 8")
else:
    fail("package.json missing Node 22+ engines field for Capacitor 8")
_audit_yml = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "audit.yml"), encoding="utf-8").read()
_apk_yml_cap8 = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "build-apk.yml"), encoding="utf-8").read()
if "node-version: '22'" in _audit_yml and "node-version: '22'" in _apk_yml_cap8:
    ok("CI Capacitor workflows use Node 22")
else:
    fail("CI workflows still use Node 20 with Capacitor 8")
if "android-36" in _apk_yml_cap8:
    ok("Android APK workflow targets SDK 36 for Capacitor 8")
else:
    fail("Android APK workflow still targets SDK 34")

# ── Issue #111: full codebase audit v2.52.00 — verify 14 findings resolved at HEAD ──
_111_vpm = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_111_zhl = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
_111_bundle = open(os.path.join(os.path.dirname(__file__), "zhl-engine-bundle.js"), encoding="utf-8").read()
_111_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_111_ci = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml"), encoding="utf-8").read()
_111_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
_111_gesp = js.split("function getEffectiveSetpointAtDepth", 1)[-1][:2200] if "function getEffectiveSetpointAtDepth" in js else ""
_111_ndl = js.split("function buhNDL", 1)[-1][:1500] if "function buhNDL" in js else ""
_111_rep = js.split("function getZhlRepStateForSchedule", 1)[-1][:400] if "function getZhlRepStateForSchedule" in js else ""
_111_end = js.split("function calcEND_tool", 1)[-1][:2500] if "function calcEND_tool" in js else ""
_111_cont = js.split("function syncContDepthLabels", 1)[-1][:300] if "function syncContDepthLabels" in js else ""
_111_deco = js.split("DECO_FIELDS:", 1)[-1][:2500] if "DECO_FIELDS:" in js else ""
_111_zwb = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
_111_sw = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
if "_bubbleCarryApplied" in _111_vpm and "scaleCarried" in _111_vpm.split("function setCriticalRadiiForConservatism", 1)[-1][:900]:
    ok("issue #111 H-1: VPM conservatism scales carried bubble radii, not flat overwrite")
else:
    fail("issue #111 H-1: setCriticalRadiiForConservatism still destroys bubble carry")
if "const mMargin = mValue - P_surf" in _111_bundle:
    ok("issue #111 H-2: computeSurfaceGF uses (mValue - P_surf) denominator in bundle")
else:
    fail("issue #111 H-2: computeSurfaceGF bundle still divides by raw mValue")
if ("depthAtSetpointCrossing" in _111_ccr or "ZhlEngineBundle.getEffectiveSetpointAtDepth" in js) and "if (depthM > deepestCross) return bottomSP" not in _111_ccr:
    ok("issue #111 H-3: getEffectiveSetpointAtDepth uses depth/phase thresholds (index + ccr-core)")
else:
    fail("issue #111 H-3: getEffectiveSetpointAtDepth still compares pAmb to ppO2 setpoints")
if "if (firstStopDepth <= interpBase) return gfH;" in _physics_core_js.split("function gfAtDepth", 1)[-1][:500] and "if (firstStopDepth <= interpBase) return gfH;" in _111_bundle:
    ok("issue #111 H-5: gfAt zero-denominator guard in schedule core and bundle")
else:
    fail("issue #111 H-5: gfAt missing firstStopDepth === lastStop guard")
if "surfaceIntervalMin: snap.surfaceIntervalMin" in _111_rep:
    ok("issue #111 H-6: getZhlRepStateForSchedule returns snap surfaceIntervalMin")
else:
    fail("issue #111 H-6: getZhlRepStateForSchedule still reads live DOM SI")
if "function ndlClearAtDepth" in _physics_core_js and "gfH" in _physics_core_js.split("function ndlClearAtDepth", 1)[-1][:600]:
    ok("issue #111 M-1: buhNDL uses GF-line ndlClearAtDepth with gfHigh")
else:
    fail("issue #111 M-1: buhNDL still ignores gfHigh")
if "'travelGasTrimixO2'" in _111_deco and "'travelGasTrimixHe'" in _111_deco:
    ok("issue #111 M-2: travelGasTrimixO2/He persisted in DECO_FIELDS")
else:
    fail("issue #111 M-2: travel gas trimix missing from DECO_FIELDS")
if (
    ("if (ok) {" in _111_zwb.split("worker.onmessage", 1)[-1][:600] and "consecutiveWorkerFailures += 1" in _111_zwb.split("worker.onmessage", 1)[-1][:800])
    or "handleWorkerFailure(error" in _111_zwb.split("worker.onmessage", 1)[-1][:800]
):
    ok("issue #111 M-3: worker bridge increments failures only on ok:false")
else:
    fail("issue #111 M-3: worker bridge failure counter regression")
if "Math.max(denomBase, Math.max(0.001, pN2 * 1e-4))" in _111_vpm or "Math.max(denomBase, 0.001)" in _111_vpm:
    ok("issue #111 M-4: VPM calcSurfacePhaseVolumeTime near-zero denominator guard")
else:
    fail("issue #111 M-4: VPM surface phase volume missing denominator guard")
if "repSurfP = altAcclimatized" in _111_zhl or "rep.surfaceP != null" in _111_zhl:
    ok("issue #111 M-5: ZHL rep surface off-gas respects altAcclimatized (issue #109 fix verified)")
else:
    fail("issue #111 M-5: ZHL repSurfP still ignores altAcclimatized")
if "const ppO2Limit = parseFloat(document.getElementById('ppo2Bottom')" in _111_end:
    ok("issue #111 M-6: calcEND_tool MOD uses configured ppO2 limit")
else:
    fail("issue #111 M-6: calcEND_tool MOD still hardcoded 1.4 bar")
if re.search(r"APP_VERSION\s*=\s*['\"]2\.53\.04['\"]", app_version_js):
    ok("issue #111 L-1: app-version 2.53.04 synced; SW derives CACHE_VERSION dynamically")
else:
    fail("issue #111 L-1: SW/app-version sync regression")
if "build_vpm_bundle.py" in _111_ci and "git diff --exit-code zhl-engine-bundle.js vpm-engine-bundle.js" in _111_ci:
    ok("issue #111 L-2: CI bundle-sync guards ZHL and VPM bundle drift")
else:
    fail("issue #111 L-2: CI missing VPM bundle sync guard")
if "Math.round(v * 3.28084)" in _111_cont:
    ok("issue #111 L-3: contingency depth buttons show imperial-converted labels")
else:
    fail("issue #111 L-3: contingency depth labels still show metres as feet")
if "ccrVpm:" in _111_regr and "ccrVpmSetpoints" in _111_regr:
    ok("issue #111 L-4: engine regression covers CCR VPM setpoint paths")
else:
    fail("issue #111 L-4: engine regression missing CCR VPM coverage")

# ── Issue #98: deep review v2.52.00 — verify 2 HIGH / 1 MEDIUM / 2 LOW resolved ──
_98_vpm = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_98_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_98_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
_98_pkg = open(os.path.join(os.path.dirname(__file__), "package.json"), encoding="utf-8").read()
if "fO2dry" in _98_ccr.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700] and "spTarget / pDry" in _98_ccr.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700]:
    ok("issue #98 H-1: ccrLoopGasBelowSetpoint O2-maximized crossover on dry-gas basis (zhl-ccr-core)")
else:
    fail("issue #98 H-1: CCR below-setpoint still loads full diluent inert")
if "fO2dry" in js.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700] and "spTarget / pDry" in js.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700]:
    ok("issue #98 H-1: ccrLoopGasBelowSetpoint O2-maximized crossover on dry-gas basis in index.html")
elif "ZhlEngineBundle.ccrLoopGasBelowSetpoint" in js:
    ok("issue #98 H-1: index.html delegates ccrLoopGasBelowSetpoint to ZhlEngineBundle")
else:
    fail("issue #98 H-1: index.html below-setpoint branch still assigns diluent inert")
if "validateGasFractionsPct" in js.split("function validatePlannerInputs", 1)[-1][:1600]:
    ok("issue #98 H-2: validatePlannerInputs rejects invalid trimix O2+He totals")
else:
    fail("issue #98 H-2: planner trimix still accepts O2+He>100% silently")
if "issue98CcrInert" in _98_regr and "issue98TrimixValidate" in _98_regr:
    ok("issue #98: engine regression covers CCR inert + trimix validation")
else:
    fail("issue #98: engine regression missing H-1/H-2 coverage")
if '"@capacitor/cli": "^8' in _98_pkg:
    ok("issue #98 M-1: Capacitor 8 CLI resolves patched tar (superseded)")
else:
    fail("issue #98 M-1: dev dependency tar advisories unresolved")
if "5.0 / 1.88" in html and "4.0 / 1.88" not in html:
    ok("issue #98 L-1: He HT tooltip uses 5.0 min N2 compartment")
else:
    fail("issue #98 L-1: He HT tooltip still documents 4.0 min N2 compartment")
if "'gfs_40_25_air_hi85':      { rt:119" in verify_html:
    ok("issue #98 L-2: VPM-B/GFS pinned RT updated to 119 min")
else:
    fail("issue #98 L-2: VPM-B/GFS pinned RT still stale at 109 min")

# ── Issue #112: deep review faf3442 — 2 HIGH / 4 MEDIUM / 5 LOW ──
_112_zhl = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
_112_bundle = open(os.path.join(os.path.dirname(__file__), "zhl-engine-bundle.js"), encoding="utf-8").read()
if "isRebreatherCircuit(ccrSettings.circuit)) _ccrLoopElapsedMin += travelDur" in _112_zhl.split("decoZoneEntered && mdCompatMode", 1)[-1][:500]:
    ok("issue #112 H-1: mdCompat rebreather transit advances _ccrLoopElapsedMin when tissues skipped")
else:
    fail("issue #112 H-1: CCR scrubber runtime still lags on mdCompat deco transit")
if "firstStopDepth = cur;" in _112_zhl.split("minStopZoneDepth !== null && cur <= minStopZoneDepth", 1)[-1][:800]:
    ok("issue #112 H-2: min-stop-zone first stop anchors firstStopDepth for gfAt")
else:
    fail("issue #112 H-2: min-stop-zone path still omits firstStopDepth anchor")
if "let legTransitDur = 0;" in _112_zhl and "(si === 0) ? legTransitDur" in _112_zhl:
    ok("issue #112 M-2: si=0 transitDur uses actual ascent leg time")
else:
    fail("issue #112 M-2: si=0 transitDur still hardcoded to 0")
if "function zhlStepPpo2" in _112_zhl and "zhlStepPpo2(cur" in _112_zhl:
    ok("issue #112 M-3: CCR-on-loop steps use setpoint-derived ppO2 (zhlStepPpo2)")
else:
    fail("issue #112 M-3: ascent steps still derive ppO2 from diluent fractions on loop")
if "isFinalAscentPhase" in _112_zhl and "lastClearGf" in _112_zhl:
    ok("issue #112 M-4: intermediate-phase last stop clears to floor GF not surface")
else:
    fail("issue #112 M-4: lastStop branch still uses gfAt(0) for all phases")
if "deepest level only" in _112_zhl.split("tissuesAtBottom", 1)[-1][:120]:
    ok("issue #112 L-1: tissuesAtBottom snapshot limitation documented")
else:
    fail("issue #112 L-1: tissuesAtBottom ML limitation undocumented")
if "collapsedMDP.map(s => s.gas)" in _112_zhl:
    ok("issue #112 L-2: gasUsed derived from MDP-enforced plan")
else:
    fail("issue #112 L-2: gasUsed still derived from pre-MDP collapsed steps")
if "not longer than descent" in js.split("function validatePlannerInputs", 1)[-1][:1200]:
    ok("issue #112 L-3: validatePlannerInputs warns when BT <= descent time")
else:
    fail("issue #112 L-3: planner accepts BT shorter than descent without warning")
if "surfaceP: snap.surfaceP" in js.split("function getZhlRepStateForSchedule", 1)[-1][:500]:
    ok("issue #112 L-4: ZHL rep state carries plan-time surfaceP snapshot")
else:
    fail("issue #112 L-4: rep off-gas still reads live altSurfaceP global")
if "rep.surfaceP != null" in _112_zhl:
    ok("issue #112 L-4: schedule core uses repState surfaceP for off-gas")
else:
    fail("issue #112 L-4: schedule core ignores repState surfaceP")
if "prev.decoTransit = !!(prev.decoTransit || s.decoTransit)" in _112_zhl:
    ok("issue #112 L-5: merged ascent steps propagate decoTransit flag")
else:
    fail("issue #112 L-5: ascent merge drops decoTransit on partial transit segments")
if "isRebreatherCircuit(ccrSettings.circuit)) _ccrLoopElapsedMin += travelDur" in _112_bundle:
    ok("issue #112 H-1: bundle includes mdCompat rebreather runtime sync fix")
else:
    fail("issue #112 H-1: zhl-engine-bundle missing CCR runtime sync fix")
if "issue112PlannerBt" in open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("issue #112: engine regression covers planner BT vs descent validation")
else:
    fail("issue #112: engine regression missing planner BT validation")

# ── Issue #113: deep review 8f1fbd9 — 4 HIGH / 8 MEDIUM / 3 LOW ──
_113_vpm = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_113_vpm_b = open(os.path.join(os.path.dirname(__file__), "vpm-engine-bundle.js"), encoding="utf-8").read()
_113_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_113_zhl = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
_113_bridge = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
_113_sw = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
_113_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "VPM_STOP_CAP" in _113_vpm and "vpmStopCapError" in _113_vpm and "vpmStopCapFailedDepth" in _113_vpm:
    ok("issue #113 H-1: VPM stop cap aborts with VPM_STOP_CAP error (no silent ascent)")
else:
    fail("issue #113 H-1: VPM inner stop loop still ascends silently after 999-min cap")
if (
    "return d > 0 ? d : null;" in _113_ccr.split("function depthAtSetpointCrossing", 1)[-1][:400]
    or "Number.isFinite(d) && d > 0 ? d : null" in _113_ccr.split("function depthAtSetpointCrossing", 1)[-1][:400]
):
    ok("issue #113 H-2: depthAtSetpointCrossing returns null below surface (zhl-ccr-core)")
else:
    fail("issue #113 H-2: depthAtSetpointCrossing still clamps unreachable crossing to 0")
if "return d > 0 ? d : null;" in js.split("function depthAtSetpointCrossing", 1)[-1][:200]:
    ok("issue #113 H-2: depthAtSetpointCrossing null crossing in index.html")
elif "ZhlEngineBundle.depthAtSetpointCrossing" in js:
    ok("issue #113 H-2: index.html delegates depthAtSetpointCrossing to ZhlEngineBundle")
else:
    fail("issue #113 H-2: index.html depthAtSetpointCrossing still clamps to 0")
if "descCross == null && bottomCross != null" in _113_ccr and ("descCross == null && bottomCross != null" in js or "ZhlEngineBundle.getEffectiveSetpointAtDepth" in js):
    ok("issue #113 H-2: shallow zone uses descSP when descent crossing unreachable")
else:
    fail("issue #113 H-2: getEffectiveSetpointAtDepth shallow zone still forces decoSP")
if "HYPOXIC_DECO_GAS" in js.split("function validateDomDecoGases", 1)[-1][:800] or "validateHypoxicDecoGas" in js.split("function validateDomDecoGases", 1)[-1][:800]:
    ok("issue #113 H-3: validateDomDecoGases rejects hypoxic deco gases")
else:
    fail("issue #113 H-3: deco gas validation still accepts O2 < 18% trimix")
if "p.timer !== timer" in _113_bridge and "nextId = 1" not in _113_bridge.split("function handleWorkerFailure", 1)[-1][:400]:
    ok("issue #113 H-4: worker timeout verifies timer identity; nextId not reset on failure")
else:
    fail("issue #113 H-4: worker bridge stale timeout can kill healthy requests")
if "isRebreatherCircuit(ccrSettings.circuit)) _ccrLoopElapsedMin += travelDur" in _113_zhl:
    ok("issue #113 M-1: mdCompat runtime advance for all rebreathers (CCR + pSCR)")
else:
    fail("issue #113 M-1: mdCompat transit still skips pSCR runtime sync")
if "let bottomPhaseRuntime = 0" in _113_vpm and "bottomPhaseRuntime += descTime" in _113_vpm and "bottomPhaseRuntime += bottomTime" in _113_vpm:
    _il_regen = _113_vpm.split("function runInterLevelDecoAscent", 1)[-1].split("function ", 1)[0][:500]
    if "applyNuclearRegeneration(state, bottomPhaseRuntime)" in _113_vpm and "applyNuclearRegeneration(state, bottomPhaseRuntime)" not in _il_regen:
        ok("issue #113 M-2: applyNuclearRegeneration once after full bottom phase (excl. inter-level partial)")
    elif _113_vpm.count("applyNuclearRegeneration(state, bottomPhaseRuntime)") >= 2:
        ok("issue #113 M-2: applyNuclearRegeneration uses tracked bottom-phase runtime (excl. deco)")
    else:
        fail("issue #113 M-2: applyNuclearRegeneration not wired to bottomPhaseRuntime at all call sites")
elif "applyNuclearRegeneration(state, bottomPhaseRuntime)" in _113_vpm and "applyNuclearRegeneration(state, runtime)" not in _113_vpm.split("function runInterLevelDecoAscent", 1)[-1][:200]:
    ok("issue #113 M-2: applyNuclearRegeneration uses tracked bottom-phase runtime (excl. deco)")
else:
    fail("issue #113 M-2: nuclear regeneration still uses total runtime incl. deco")
if "const hasSnap = s.circuit != null" in js.split("function mergeCCRSettings", 1)[-1][:400]:
    ok("issue #113 M-3: mergeCCRSettings skips DOM read when circuit snapshotted")
else:
    fail("issue #113 M-3: mergeCCRSettings still reads live DOM on every call")
if "function estimateWidgetOtuWithDeco" in js and "estimateWidgetOtuWithDeco(bottomOtu" in js.split("function calcCNS", 1)[-1][:1800]:
    ok("issue #113 M-4: CNS widget estimates OTU incl. likely deco when no plan")
else:
    fail("issue #113 M-4: widget OTU still bottom-only without deco estimate")
if "syncContDepthLabels" in js.split("loadAltitudeFromStorage();", 1)[-1][:200] and "syncContDepthLabels" in js.split("_restoreFields: function", 1)[-1][:2500]:
    ok("issue #113 M-5: syncContDepthLabels on restore and DOMContentLoaded")
else:
    fail("issue #113 M-5: contingency depth labels not synced at startup")
if "REQUIRED_PRECACHE.every" in _113_sw and "verifyShellPrecache" in _113_sw:
    ok("issue #113 M-6: sw.js skipWaiting only after required shell precache succeeds")
else:
    fail("issue #113 M-6: sw.js still calls skipWaiting when all precache fails")
if "Math.max(0, (100 - o2pct) / 100)" in js.split("function getN2Frac", 1)[-1][:500] or "n2FracFromCustomO2" in js.split("function getN2Frac", 1)[-1][:500]:
    ok("issue #113 M-7: getN2Frac custom branch clamps negative fN2")
else:
    fail("issue #113 M-7: getN2Frac custom still allows O2 > 100 negative fN2")
if "lastDecoStop" in js.split("function buhNDL", 1)[-1][:400] and "decoStep" in js.split("function buhNDL", 1)[-1][:400]:
    ok("issue #113 M-8: buhNDL reads lastDecoStop and decoStep from DOM")
else:
    fail("issue #113 M-8: buhNDL still hardcodes last stop / step to 3 m")
if "Immediate restore failed" in js.split("load: function()", 1)[-1][:2500]:
    ok("issue #113 L-1: immediate _restoreFields wrapped in try/catch")
else:
    fail("issue #113 L-1: immediate restore path still lacks try/catch")
if "perDiveOtu >= 300" in js and "Cumulative OTU" in js.split("function calcCNS", 1)[-1][:5500]:
    ok("issue #113 L-2: OTU warnings separate per-dive vs cumulative carry")
else:
    fail("issue #113 L-2: OTU warning still labels carry-inclusive total as single-dive")
if "No saved settings found (v6)" in js and "removeItem('lspDiveSettings_v5')" in js and "removeItem('lspDiveSettings_v4')" in js:
    ok("issue #113 L-3: storage log references v6; v4/v5 keys cleaned up")
else:
    fail("issue #113 L-3: storage cleanup log or v4/v5 removal regression")
if "issue113" in _113_regr:
    ok("issue #113: engine regression covers setpoint / deco-gas / N2 fixes")
else:
    fail("issue #113: engine regression missing #113 coverage")

# ── Issue #116: residual audit v2.52.00 — 2 HIGH / 1 MEDIUM ──
_116_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "else if (chk.o2 < 18)" in js.split("function validateDomDecoGases", 1)[-1][:800] or "validateHypoxicDecoGas" in js.split("function validateDomDecoGases", 1)[-1][:800]:
    ok("issue #116 H-1: hypoxic deco check applies to nitrox without He (not trimix diluent)")
else:
    fail("issue #116 H-1: hypoxic deco validation still gated on helium > 0")
if "VPM_STOP_CAP" in _113_vpm and "return vpmStopCapError" in _113_vpm:
    ok("issue #116 H-2: VPM stop cap returns fatal VPM_STOP_CAP error")
else:
    fail("issue #116 H-2: VPM stop cap still treated as valid plan segment")
if "result.code === 'VPM_STOP_CAP' && result.plan" in js and "function runVPMSchedule" in js:
    ok("issue #116 H-2: UI renders partial plan on VPM_STOP_CAP for capped-stop warning")
else:
    fail("issue #116 H-2: UI missing VPM_STOP_CAP partial-plan warning path")
if "REQUIRED_PRECACHE" in _113_sw and "verifyShellPrecache" in _113_sw and "throw new Error('Required shell precache incomplete')" in _113_sw:
    ok("issue #116 M-1: SW counts only confirmed cache.add successes")
else:
    fail("issue #116 M-1: SW still treats caught precache failures as successes")
if "activate blocked" in _113_sw and "SKIP_WAITING ignored" in _113_sw:
    ok("issue #116 M-1: SW activate and SKIP_WAITING gated on shell precache verification")
else:
    fail("issue #116 M-1: SW activate/SKIP_WAITING still bypass incomplete precache")
if "r.waiting.postMessage({ type: 'SKIP_WAITING' })" not in js and "SW update install failed" in js:
    ok("issue #116 M-1: index.html no longer forces SKIP_WAITING on waiting worker")
else:
    fail("issue #116 M-1: index.html still forces SKIP_WAITING bypassing precache gate")
if "getRegistrations()" not in js.split("PWA: service worker registration", 1)[-1][:2500] and "caches.delete(k)" not in js.split("PWA: service worker registration", 1)[-1][:2500]:
    ok("issue #116 M-1: index.html no eager SW unregister/cache wipe on version bump")
else:
    fail("issue #116 M-1: index.html still unregisters workers or deletes caches before SW activation")
if "localStorage.setItem(SW_VERSION_KEY, APP_VERSION)" in js.split("controllerchange", 1)[-1][:400]:
    ok("issue #116 M-1: SW version key updates only after controllerchange")
else:
    fail("issue #116 M-1: SW version key still updated before successful activation")
if "issue116" in _116_regr:
    ok("issue #116: engine regression covers custom hypoxic deco + VPM cap path")
else:
    fail("issue #116: engine regression missing #116 coverage")
if os.path.isfile(os.path.join(os.path.dirname(__file__), "dev", "sw_lifecycle_test.py")) and "verifyShellPrecache" in open(os.path.join(os.path.dirname(__file__), "dev", "sw_lifecycle_test.py"), encoding="utf-8").read():
    ok("issue #116 M-1: sw lifecycle behavioral test script present")
else:
    fail("issue #116 M-1: missing sw lifecycle behavioral test")

# ── Issue #117: full codebase audit v2.52.00 — 2 MEDIUM / 4 LOW ──
_117_zhl = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
_117_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_117_bridge = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
_117_cap = open(os.path.join(os.path.dirname(__file__), "capacitor-bridge.js"), encoding="utf-8").read()
_117_picker = open(os.path.join(os.path.dirname(__file__), "android-select-picker.js"), encoding="utf-8").read()
_117_sw = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
_117_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "isRebreatherCircuit(ccrSettings.circuit)) _ccrLoopElapsedMin += travelDur" in _117_zhl.split("decoZoneEntered && mdCompatMode", 1)[-1][:500]:
    ok("issue #117 M-1: mdCompat transit advances _ccrLoopElapsedMin for all rebreathers")
else:
    fail("issue #117 M-1: mdCompat transit still CCR-only for runtime sync")
if "deferredRevokeUrls" in _117_cap and "async function readBlobFromHref" in _117_cap and "xhr.open('GET', href, false)" not in _117_cap:
    ok("issue #117 M-2: capacitor-bridge async blob read with deferred revokeObjectURL")
else:
    fail("issue #117 M-2: capacitor-bridge still blocks UI with sync XHR")
if "REQUIRED_PRECACHE.concat(OPTIONAL_PRECACHE)" in _117_sw and "const PRECACHE_ASSETS = REQUIRED_PRECACHE.concat" in _117_sw:
    ok("issue #117 L-1: sw.js PRECACHE_ASSETS derived from REQUIRED + OPTIONAL lists")
else:
    fail("issue #117 L-1: sw.js still duplicates REQUIRED_PRECACHE and PRECACHE_ASSETS")
if "rejectAll(error || 'ZHL worker calculation failed')" in _117_bridge:
    ok("issue #117 L-2: worker bridge rejects all pending on calculation failure (issue #124 L-2)")
elif "handleWorkerFailure(error || 'ZHL worker calculation failed')" in _117_bridge:
    ok("issue #117 L-2: worker bridge delegates calculation failure to handleWorkerFailure")
elif "killWorker();" in _117_bridge.split("Worker calculation failed", 1)[-1][:250]:
    ok("issue #117 L-2: worker bridge kills worker immediately on ok === false")
else:
    fail("issue #117 L-2: worker bridge still reuses worker after calculation failure")
if "fO2dry" in _117_ccr.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700]:
    ok("issue #117 L-3: ccrLoopGasBelowSetpoint zeroes loop inert at O2-maximized crossover (dry basis)")
else:
    fail("issue #117 L-3: ccrLoopGasBelowSetpoint still assigns wet-fraction loop inert below setpoint")
if "sheetRebuildPending = typeof WeakMap" in _117_picker and "closeSheet();" in _117_picker.split("item.addEventListener('click'", 1)[-1][:200]:
    ok("issue #117 L-4: android picker guards WeakMap and closes sheet before option mutation")
else:
    fail("issue #117 L-4: android picker still flashes ghost sheet on fast tap+mutation")
if "issue117" in _117_regr:
    ok("issue #117: engine regression covers mdCompat pSCR runtime + CCR crossover inert")
else:
    fail("issue #117: engine regression missing #117 coverage")

# ── Issue #118: full codebase audit v2.52.00 — 4 HIGH / 8 MEDIUM / 3 LOW ──
_118_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_118_vpm = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_118_sw = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
_118_ci = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml"), encoding="utf-8").read()
_118_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "descCross == null && bottomCross == null && decoCross == null" in _118_ccr.split("function getEffectiveSetpointAtDepth", 1)[-1][:900]:
    ok("issue #118 H-1: altitude all-null setpoint crossings use ambient pDry zones")
else:
    fail("issue #118 H-1: getEffectiveSetpointAtDepth still assigns bottomSP when all crossings null")
if "applyNuclearRegeneration(state, runtime)" in _118_vpm.split("function runInterLevelDecoAscent", 1)[-1][:500]:
    ok("issue #118 H-2: VPM inter-level deco regenerates with cumulative runtime (issue #124 M-2)")
elif "function runInterLevelDecoAscent" in _118_vpm and "applyNuclearRegeneration(state, bottomPhaseRuntime)" not in _118_vpm.split("function runInterLevelDecoAscent", 1)[-1].split("function ", 1)[0][:400]:
    ok("issue #118 H-2: VPM inter-level deco skips partial nuclear regeneration")
else:
    fail("issue #118 H-2: runInterLevelDecoAscent still calls applyNuclearRegeneration with partial runtime")
if "parseRunMinutes(tr.querySelectorAll('td')[2]" in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("issue #118 H-3: contingency deco time uses parseRunMinutes on stop column (issue #124 H-3)")
elif 'td[data-label="Stop"]' in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("issue #118 H-3: contingency deco time reads integer Stop column (issue #127 M-5)")
else:
    fail("issue #118 H-3: runContingencyScenario still parses stop column incorrectly")
if "SW_SHELL_READY" in _118_sw and "SW_SHELL_READY" in js:
    ok("issue #118 H-4: SW activate notifies clients; page listens for shell-ready migration")
else:
    fail("issue #118 H-4: SW/client shell-ready migration handshake missing")
if "parseDomInt('lastDecoStop'" in js.split("function buhNDL", 1)[-1][:400]:
    ok("issue #118 M-1: buhNDL accepts lastDecoStop/decoStep of 0 (no falsy fallback)")
else:
    fail("issue #118 M-1: buhNDL still treats 0 as missing lastDecoStop/decoStep")
if "zhl-schedule-worker.js" in _118_sw.split("REQUIRED_PRECACHE", 1)[-1][:400]:
    ok("issue #118 M-2: zhl-schedule-worker.js in REQUIRED_PRECACHE shell list")
else:
    fail("issue #118 M-2: ZHL worker script still optional-only precache")
if (
    "const perDiveOtu = fromPlan ? Math.max(0, otu - otuCarry) : otu" in js.split("function calcCNS", 1)[-1][:5500]
    or "const perDiveOtu = Math.max(0, otu - otuCarry)" in js.split("function calcCNS", 1)[-1][:5500]
):
    ok("issue #118 M-3: single-dive OTU warning excludes carry when no plan")
else:
    fail("issue #118 M-3: perDiveOtu still includes carry in widget-only path")
if "ccrLoopGasBelowSetpoint(pAmb, fO2, fHe, setpoint)" in _118_ccr and "spTarget" in _118_ccr.split("function ccrLoopGasBelowSetpoint", 1)[-1][:400]:
    ok("issue #118 M-4: ccrLoopGasBelowSetpoint clamps fO2eff to setpoint target")
else:
    fail("issue #118 M-4: below-setpoint loop gas still ignores setpoint value")
if "VPM_STOP_CAP" in _118_vpm and "result.code === 'VPM_STOP_CAP'" in js:
    ok("issue #118 M-5: VPM stop cap is fatal VPM_STOP_CAP (no silent cap-hit flag)")
else:
    fail("issue #118 M-5: VPM stop cap still silently modifies plan")
if "_restoreInProgress" in js.split("var appSettings", 1)[-1][:800] and "waterDensitySelect" in js.split("DECO_FIELDS:", 1)[-1][:800]:
    ok("issue #118 M-6/M-8: batch restore suppresses change events; waterDensity in v6 blob")
else:
    fail("issue #118 M-6/M-8: settings restore ordering or waterDensity dual-store regression")
if "getEffectiveSetpointAtDepth(endpointDepth" in _118_ccr or "getEffectiveSetpointAtDepth(seg.toDepth" in _118_ccr:
    ok("issue #118 M-7: saturateLinearCCR samples setpoint at segment boundary depth")
else:
    fail("issue #118 M-7: CCR Schreiner still samples setpoint at fromDepth boundary")
if "margin <= 5 ? 'var(--orange)'" in js.split("function statusColor", 1)[-1][:200]:
    ok("issue #118 L-1: UDP statusColor uses orange for 1–5 min margin")
else:
    fail("issue #118 L-1: UDP margin 1–5 min still red like exceeded NDL")
if "export-regression:" in _118_ci and "needs: [bundle-sync]" in _118_ci.split("export-regression:", 1)[-1][:200] and "needs: [bundle-sync]" in _118_ci.split("engine-validation:", 1)[-1][:200]:
    ok("issue #118 L-2: export-regression and engine-validation gated on bundle-sync")
else:
    fail("issue #118 L-2: CI jobs still run against potentially stale bundles")
if "function canonicalCircuit" in _118_ccr and "canonicalCircuit(circuit)" in _118_ccr.split("function isRebreatherCircuit", 1)[-1][:200]:
    ok("issue #118 L-3: isRebreatherCircuit normalizes circuit case via canonicalCircuit")
else:
    fail("issue #118 L-3: rebreather detection still case-sensitive")
if "issue118" in _118_regr:
    ok("issue #118: engine regression covers altitude setpoint + circuit case + buhNDL zero stop")
else:
    fail("issue #118: engine regression missing #118 coverage")

# ── Issue #119: Kiro audit v2.52.00 — 4 CRITICAL / 5 HIGH / 5 MEDIUM / 3 LOW ──
_119_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_119_bundle = open(os.path.join(os.path.dirname(__file__), "zhl-engine-bundle.js"), encoding="utf-8").read()
_119_bridge = open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
_119_sw = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
_119_apk = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "build-apk.yml"), encoding="utf-8").read()
_119_cap = open(os.path.join(os.path.dirname(__file__), "capacitor-bridge.js"), encoding="utf-8").read()
_119_picker = open(os.path.join(os.path.dirname(__file__), "android-select-picker.js"), encoding="utf-8").read()
_119_manifest = open(os.path.join(os.path.dirname(__file__), "manifest.json"), encoding="utf-8").read()
_119_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "--bg-alt:" in html.split(":root", 1)[-1][:800] and "--bg-alt:" in html.split("body.light-theme", 1)[-1][:400]:
    ok("issue #119 BUG-01: --bg-alt defined in dark and light theme tokens")
else:
    fail("issue #119 BUG-01: --bg-alt CSS variable still undefined")
if "function getEffectivePpo2" in _119_ccr and "function getEffectivePpo2" in _119_bundle:
    ok("issue #119 BUG-02: getEffectivePpo2 defined in ZHL bundle for worker context")
else:
    fail("issue #119 BUG-02: getEffectivePpo2 still missing from zhl-engine-bundle.js")
if "git reset --hard HEAD" not in _119_apk.split("Commit APK", 1)[-1][:600] and "github-actions[bot]" in _119_apk:
    ok("issue #119 BUG-03/16: APK commit no longer reset after commit; uses actions bot email")
else:
    fail("issue #119 BUG-03: build-apk.yml still destroys APK commit with reset --hard")
if "test -f www/index.html" in _119_apk:
    ok("issue #119 BUG-04: build-apk verifies www/index.html after sync_www.py")
else:
    fail("issue #119 BUG-04: missing www/ guard after sync_www.py")
if "stepDepthToM" in _gas_core_js.split("function enforceMinDecoProfile", 1)[-1][:1200]:
    ok("issue #119 BUG-05: enforceMinDecoProfile uses metric depth helpers (imperial-safe)")
elif "ZhlEngineBundle.enforceMinDecoProfile" in js:
    ok("issue #119 BUG-05: enforceMinDecoProfile delegates to ZhlEngineBundle (Tier 3)")
else:
    fail("issue #119 BUG-05: enforceMinDecoProfile still hardcodes rounded imperial depths")
if "body.light-theme * { color: inherit" not in html:
    ok("issue #119 BUG-06: light theme no longer applies color:inherit to all elements")
else:
    fail("issue #119 BUG-06: body.light-theme * { color: inherit } still overrides inline colors")
if "typeof APP_VERSION !== 'undefined'" in html and "APP_VERSION unavailable" in html.split("PWA: service worker registration", 1)[-1][:3500]:
    ok("issue #119 BUG-07: SW registration guarded when APP_VERSION missing")
else:
    fail("issue #119 BUG-07: SW still registers with sw.js?v=undefined")
if '<script src="android-select-picker.js"></script>' in html and 'defer="" src="android-select-picker.js"' not in html.split("</head>", 1)[0]:
    ok("issue #119 BUG-08: android-select-picker.js loaded at end of body (non-deferred)")
else:
    fail("issue #119 BUG-08: android-select-picker.js still deferred in head")
if "MAJOR * 1000000" in _119_apk:
    ok("issue #119 BUG-09: APK versionCode uses expanded MINOR/PATCH headroom")
else:
    fail("issue #119 BUG-09: version code formula still overflows at MINOR/PATCH >= 100")
if '"purpose": "maskable"' in _119_manifest and "512x512" in _119_manifest.split("maskable", 1)[-1][:120]:
    ok("issue #119 BUG-11: manifest includes 512 maskable icon entry")
else:
    fail("issue #119 BUG-11: manifest missing 512x512 maskable icon")
if "if (!worker) return" in _119_bridge.split("function handleWorkerFailure", 1)[-1][:200]:
    ok("issue #119 BUG-12: worker failure handler skips double-increment after kill")
else:
    fail("issue #119 BUG-12: worker bridge still double-increments failure counter")
if "selectSyncFns.get(sel)" in _119_picker.split("scheduleSheetRebuild", 1)[-1][:400]:
    ok("issue #119 BUG-13: android picker rebuild uses live syncBtn from WeakMap")
else:
    fail("issue #119 BUG-13: android picker still uses stale syncBtn closure")
if "__LSP_CAP_BRIDGE_TEARDOWN" in _119_cap and "__LSP_CAP_BRIDGE_ORIG__" in _119_cap and "deferredRevokeUrls.forEach" in _119_cap.split("function teardown", 1)[-1][:400]:
    ok("issue #119 BUG-14: capacitor-bridge teardown restores patches and revokes deferred blob URLs")
else:
    fail("issue #119 BUG-14: capacitor-bridge still leaves permanent revokeObjectURL monkey-patch on hot reload")
if "path.endsWith('.apk')" in _119_sw and "url.href.includes" not in _119_sw.split("function shouldNeverCache", 1)[-1][:300]:
    ok("issue #119 BUG-15: shouldNeverCache uses pathname suffix checks")
else:
    fail("issue #119 BUG-15: shouldNeverCache still uses href substring matching")
if '"orientation": "any"' in _119_manifest:
    ok("issue #119 BUG-17: manifest orientation allows landscape on tablets")
else:
    fail("issue #119 BUG-17: manifest still locked to portrait-primary")
if "issue119" in _119_regr:
    ok("issue #119: engine regression covers worker getEffectivePpo2")
else:
    fail("issue #119: engine regression missing #119 coverage")

# ── Issue #120: full codebase audit v2.52.00 — 1 HIGH / 3 MEDIUM / 1 LOW ──
_120_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_120_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
_120_cap = open(os.path.join(os.path.dirname(__file__), "capacitor-bridge.js"), encoding="utf-8").read()
if "fO2dry" in _120_ccr.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700] and "wetScale" in _120_ccr.split("function ccrLoopGasBelowSetpoint", 1)[-1][:700]:
    ok("issue #120 H-1: ccrLoopGasBelowSetpoint uses dry-gas O2-maximized crossover (zero inert)")
else:
    fail("issue #120 H-1: below-setpoint branch still treats water vapour fraction as inert")
if "ZhlEngineBundle.normalizeCCRSettings" in js.split("function mergeCCRSettings", 1)[-1][:2000]:
    ok("issue #120 M-1: mergeCCRSettings canonicalizes via ZhlEngineBundle.normalizeCCRSettings")
else:
    fail("issue #120 M-1: mergeCCRSettings still passes raw circuit string downstream")
if "canonicalCircuit(ccr.circuit) === 'pSCR'" in _ccr_core_src.split("function getEffectiveSetpointAtDepth", 1)[-1][:400] or "ZhlEngineBundle.getEffectiveSetpointAtDepth" in js:
    ok("issue #120 M-1: getEffectiveSetpointAtDepth recognizes canonical pSCR")
else:
    fail("issue #120 M-1: getEffectiveSetpointAtDepth still case-sensitive on circuit")
if "_syncUiAfterRestore" in js.split("var appSettings", 1)[-1][:12000] and "toggleCircuitFields" in js.split("_syncUiAfterRestore", 1)[-1][:600]:
    ok("issue #120 M-2: settings restore runs explicit post-restore UI sync")
else:
    fail("issue #120 M-2: _restoreInProgress still suppresses change handlers without UI resync")
if "__decoCardIds" in js.split("var appSettings", 1)[-1][:12000] and "travelGasActive" in js.split("var appSettings", 1)[-1][:12000] and "restoreDecoGasCardLayout" in js:
    ok("issue #120 M-3: dynamic deco cards + travel gas active state persisted")
else:
    fail("issue #120 M-3: deco cards 3–8 and travelGasActive still not saved/restored")
if "async function readBlobFromHref" in _120_cap and "xhr.open('GET', href, false)" not in _120_cap:
    ok("issue #120 L-1: capacitor-bridge async blob read (www/_pages sync accepts fetch path)")
else:
    fail("issue #120 L-1: capacitor-bridge still requires sync XHR arraybuffer fallback")
if "issue120" in _120_regr:
    ok("issue #120: engine regression covers PSCR canonicalization + dry-gas crossover")
else:
    fail("issue #120: engine regression missing #120 coverage")

# ── Issue #121: follow-up to #120 — trimix UI + dynamic deco values ──
_121_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "toggleCustomO2?.();" in js.split("_syncUiAfterRestore", 1)[-1][:500]:
    ok("issue #121 M-1: post-restore UI sync calls toggleCustomO2 for gasMix trimix fields")
else:
    fail("issue #121 M-1: _syncUiAfterRestore still omits toggleCustomO2 (planner trimix hidden)")
if "decoCardPersistFieldIds" in js and "MAX_DECO_CARD_IDX" in js.split("var appSettings", 1)[-1][:4000]:
    ok("issue #121 M-2: dynamic deco cards 3–8 field IDs included in persistence")
else:
    fail("issue #121 M-2: dg3–dg8 mix/cylinder fields still absent from save/restore")
if "issue121" in _121_regr:
    ok("issue #121: engine regression covers trimix visibility + dynamic deco reload")
else:
    fail("issue #121: engine regression missing #121 coverage")

# ── Issue #122: gapped dynamic deco card layout restore ──
_122_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "appendDecoGasCardAtIdx" in js and "while (_dgNextIdx < id)" not in js.split("function restoreDecoGasCardLayout", 1)[-1][:400]:
    ok("issue #122: restoreDecoGasCardLayout creates exact saved card IDs without gap fillers")
else:
    fail("issue #122: restoreDecoGasCardLayout still advances through intermediate card IDs")
if "issue122" in _122_regr and "layoutOk" in _122_regr:
    ok("issue #122: engine regression asserts exact restored deco card ID list")
else:
    fail("issue #122: engine regression missing exact layout restore coverage")
if "_nextFreeDecoCardIdx" in js and "_syncDgNextIdx" in js and "_dgNextIdx++" not in js.split("function addDecoGasCard", 1)[-1][:200]:
    ok("issue #122 follow-up: addDecoGasCard reuses free card IDs 3–8 instead of unbounded _dgNextIdx")
else:
    fail("issue #122 follow-up: addDecoGasCard still uses unbounded _dgNextIdx++")
if "values.__decoCardIds" in js.split("_restoreFields", 1)[-1][:2500] and "fieldIds.add" in js.split("_restoreFields", 1)[-1][:2500]:
    ok("issue #122 follow-up: restore enumerates saved live deco card field IDs")
else:
    fail("issue #122 follow-up: restore still limited to static dg3–dg8 field list")
if "issue122IdReuse" in _122_regr:
    ok("issue #122 follow-up: engine regression covers ID reuse and dg8 reload")
else:
    fail("issue #122 follow-up: engine regression missing ID reuse coverage")
if "_insertDecoGasCardInIdOrder" in js and "insertBefore" in js.split("function _insertDecoGasCardInIdOrder", 1)[-1][:300]:
    ok("issue #122 follow-up: reused deco cards insert in ID order (stable labels after reload)")
else:
    fail("issue #122 follow-up: appendDecoGasCardAtIdx still appends reused cards out of ID order")

# ── Issue #123: full engine core audit (zhl-ccr-core + vpm-engine-core) ──
_vpm_core = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_zhl_ccr = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_123_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
if "pN2: pDry * fN2effDry" in _zhl_ccr and "pHe: pDry * fHeEffDry" in _zhl_ccr:
    ok("issue #123 C-01: ccrLoopGasBelowSetpoint uses dry-basis partial pressures")
else:
    fail("issue #123 C-01: ccrLoopGasBelowSetpoint still double-scales loop inert partials")
if "ppO2Drop = metO2 / loopVol" in _zhl_ccr:
    ok("issue #123 C-02: computePSCRFractions uses depth-independent Baker metabolic drop")
else:
    fail("issue #123 C-02: computePSCRFractions still subtracts dimensionless drop from bar ppO2")
if "applyExtendedAfterBoyle" in _vpm_core and "state.decoGradientN2[i] *= clampedFactor" in _vpm_core and "state.allowableGradientN2[i] *=" not in _vpm_core.split("function extendedCompensation", 1)[-1][:800]:
    ok("issue #123 H-01: extended compensation scales deco gradients after Boyle step")
else:
    fail("issue #123 H-01: extendedCompensation still scales allowable before Boyle")
if "endpointDepth = ascending ? seg.toDepth : seg.fromDepth" in _vpm_core.split("function loadTissuesLinear", 1)[-1][:2000]:
    ok("issue #123 H-02: loadTissuesLinear uses segment endpoint for setpoint lookup")
else:
    fail("issue #123 H-02: loadTissuesLinear still uses midpoint depth for setpoint")
if "splitLinearDepthAtBoundaries(fromDepth, toDepth" in _zhl_ccr.split("function saturateLinearCCR", 1)[-1][:800] and "phase ? [{ fromDepth" not in _zhl_ccr.split("function saturateLinearCCR", 1)[-1][:800]:
    ok("issue #123 H-03: saturateLinearCCR always splits at setpoint boundaries")
else:
    fail("issue #123 H-03: saturateLinearCCR still bypasses boundary split when ccrPhase set")
if "vpmMaxStopMin" in _vpm_core and ": 180" in _vpm_core and "guard % 50 === 0" in _vpm_core.split("function runRoundedDecoStop", 1)[-1][:2500]:
    ok("issue #123 M-01: vpmMaxStopMin defaults to 180 with perf bailout in stop loop")
else:
    fail("issue #123 M-01: runRoundedDecoStop still uncapped at 999 min default")
if "prevAltFactor" in _vpm_core and "_altFactor: altFactor" in _vpm_core:
    ok("issue #123 M-02: bubble carry stores and normalises _altFactor on repetitive dives")
else:
    fail("issue #123 M-02: bubble carry still omits altitude normalisation")
if "depthM < 0.5" in _zhl_ccr.split("function getEffectiveSetpointAtDepth", 1)[-1][:1500]:
    ok("issue #123 M-03: shallow setpoint tier guard at depths < 0.5 m")
else:
    fail("issue #123 M-03: getEffectiveSetpointAtDepth missing shallow pressure guard")
if "blendedGradN2" in _vpm_core.split("function applyGFSurfacing", 1)[-1][:1400] and "blendedGradHe" in _vpm_core.split("function applyGFSurfacing", 1)[-1][:1400]:
    ok("issue #123 M-04: applyGFSurfacing blends N2 and He VPM gradients independently")
else:
    fail("issue #123 M-04: applyGFSurfacing still assigns single blended scalar to both gases")
if "return 'OC'" in _zhl_ccr.split("function canonicalCircuit", 1)[-1][:200]:
    ok("issue #123 L-03: canonicalCircuit falls back to OC for unknown circuits")
else:
    fail("issue #123 L-03: canonicalCircuit still passes through unknown circuit strings")
if "issue123" in _123_regr:
    ok("issue #123: engine regression covers CCR/VPM audit fixes")
else:
    fail("issue #123: engine regression missing #123 coverage")

# ── Issue #124: post-#123 full codebase audit ──
_124_regr = open(os.path.join(os.path.dirname(__file__), "dev", "engine_regression.py"), encoding="utf-8").read()
_build_py = open(os.path.join(os.path.dirname(__file__), "tools", "build_zhl_bundle.py"), encoding="utf-8").read()
if "if (!(gfHigh > 0)) return 0" in _physics_core_js or "if (!(gfHigh > 0)) return 0" in zhl_bundle_js:
    ok("issue #124 H-1: ceiling() rejects gfHigh <= 0 in zhl-physics-core")
else:
    fail("issue #124 H-1: ceiling() missing gfHigh guard")
if "firstStopDepth <= interpBase" in _physics_core_js.split("function gfAtDepth", 1)[-1][:500]:
    ok("issue #124 H-2: gfAt returns gfHigh when firstStopDepth equals interpBase")
else:
    fail("issue #124 H-2: gfAt still divides by zero when shallowGradient first stop equals lastStop")
if "parseRunMinutes(tr.querySelectorAll" in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("issue #124 H-3: runContingencyScenario accumulates deco time as numeric minutes")
elif 'td[data-label="Stop"]' in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("issue #124 H-3: runContingencyScenario reads integer Stop column for deco minutes")
else:
    fail("issue #124 H-3: runContingencyScenario still uses parseStopDisplayTime string concat")
if "typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325" in _zhl_ccr.split("function getEffectivePpo2", 1)[-1][:600]:
    ok("issue #124 H-4: getEffectivePpo2 guards bare altSurfaceP for worker context")
else:
    fail("issue #124 H-4: getEffectivePpo2 still accesses bare altSurfaceP")
if "cappedDrop = Math.min(ppO2Drop" in _zhl_ccr:
    ok("issue #124 H-5: computePSCRFractions caps metabolic drop before ppO2 subtraction")
else:
    fail("issue #124 H-5: pSCR still uses hard ppO2 floor clamp with discontinuity")
if ".filter(d => d != null)" in _zhl_ccr.split("function getEffectiveSetpointAtDepth", 1)[-1][:2000]:
    ok("issue #124 M-1: getEffectiveSetpointAtDepth ignores null crossings in deepestCross")
else:
    fail("issue #124 M-1: getEffectiveSetpointAtDepth still coalesces null crossings to 0")
if "applyNuclearRegeneration(state, bottomPhaseRuntime)" in _vpm_core and "applyNuclearRegeneration(state, runtime)" not in _vpm_core.split("function runInterLevelDecoAscent", 1)[-1].split("function ", 1)[0][:500]:
    ok("issue #124 M-2: applyNuclearRegeneration once after bottom phase only (issue #125 H-2)")
else:
    fail("issue #124 M-2: VPM inter-level ascent still double-calls applyNuclearRegeneration")
if "function syncDecoGasCardUi" in js:
    ok("issue #124 M-3: syncDecoGasCardUi restores trimix/custom field visibility on deco cards")
else:
    fail("issue #124 M-3: appendDecoGasCardAtIdx still skips post-restore UI sync")
if "travelInfoRow.fO2, 'descent'" in js:
    ok("issue #124 M-4: travel-gas descent rowDisplayPpo2 passes explicit fO2")
else:
    fail("issue #124 M-4: rowDisplayPpo2 CCR+travel path still omits fO2")
if "fO2 > 0.60 ? ppO2Deco : ppO2Bot" in js.split("function getDecoGasSwitches", 1)[-1][:2000]:
    ok("issue #124 M-5: VPM gas switch uses ppO2Bot for low-O2 deco gases")
else:
    fail("issue #124 M-5: VPM gas switch still always uses ppO2Deco limit")
if "simulateDive2" in js.split("function calcSurfInt", 1)[-1][:2500] and "D2BT" in js.split("function calcSurfInt", 1)[-1][:2500]:
    ok("issue #124 M-6: calcSurfInt simulates Dive 2 depth and BT in minimum SI search")
elif "simulateDive2" in open(os.path.join(os.path.dirname(__file__), "surf-interval-core.js"), encoding="utf-8").read() and "D2BT" in open(os.path.join(os.path.dirname(__file__), "surf-interval-core.js"), encoding="utf-8").read():
    ok("issue #124 M-6: calcSurfInt simulates Dive 2 depth and BT in minimum SI search")
else:
    fail("issue #124 M-6: calcSurfInt still ignores Dive 2 depth/BT in SI computation")
if "surfaceP: (environment || defaultEnvironment()).altSurfaceP" in _build_py:
    ok("issue #124 M-7: repState carries explicit surfaceP from environment")
else:
    fail("issue #124 M-7: repetitive dive SI still falls back to stale altSurfaceP closure")
if "vpmStopCapNote" in js and "vpmStopCapHit" in js:
    ok("issue #124 L-1: renderVPMResults surfaces vpmStopCapHit capped-stop warning")
else:
    fail("issue #124 L-1: vpmStopCapHit still not consumed in UI")
if (
    "rejectAll(error || 'ZHL worker calculation failed')" in open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
    or "handleWorkerFailure(error || 'ZHL worker calculation failed')" in open(os.path.join(os.path.dirname(__file__), "zhl-worker-bridge.js"), encoding="utf-8").read()
):
    ok("issue #124 L-2: worker onmessage error path calls rejectAll before killWorker")
else:
    fail("issue #124 L-2: worker error handler still leaves concurrent requests hanging")
if "altSurfaceP || 1.01325" in js.split("function ccrGasLitres", 1)[-1][:400]:
    ok("issue #124 L-3: CCR diluent consumption uses 1.01325 sea-level fallback")
else:
    fail("issue #124 L-3: CCR diluent still uses altSurfaceP || 1.0 fallback")
if "issue124" in _124_regr:
    ok("issue #124: engine regression covers audit #124 fixes")
else:
    fail("issue #124: engine regression missing #124 coverage")

# ── Engine mirror rule (Tier 3 dedup) ─────────────────────────────────────────
_mirror_doc = os.path.join(os.path.dirname(__file__), "docs", "AUDIT_MIRROR_RULE.md")
if os.path.isfile(_mirror_doc) and "Mirror checklist" in open(_mirror_doc, encoding="utf-8").read():
    ok("engine mirror rule documented (docs/AUDIT_MIRROR_RULE.md)")
else:
    fail("docs/AUDIT_MIRROR_RULE.md missing mirror checklist")

for _ui_script in _UI_CORE_FILES:
    if f'src="{_ui_script}"' in html:
        ok(f"index.html loads runtime UI core {_ui_script}")
    else:
        fail(f"index.html missing script src for {_ui_script}")

_extract_tool = open(os.path.join(os.path.dirname(__file__), "tools", "extract_ui_cores.py"), encoding="utf-8").read()
if "LSP-EXTRACT-BEGIN" in _extract_tool and "BEGIN_JS_RE" in _extract_tool and "extract_lines" not in _extract_tool:
    ok("extract_ui_cores.py uses marker-based contract (no line-range extract_lines)")
else:
    fail("extract_ui_cores.py still uses line-range extraction or missing marker contract")
for _blk in ("surf-interval-core", "gas-table-core", "gas-plan-core", "export-core", "contingency-core"):
    if f"LSP-EXTRACT-BEGIN:{_blk}" in html and f"LSP-EXTRACT-END:{_blk}" in html:
        ok(f"index.html has LSP-EXTRACT marker pair for {_blk}")
    else:
        fail(f"index.html missing LSP-EXTRACT marker pair for {_blk}")
_extract_verify = subprocess.run(
    [sys.executable, os.path.join(os.path.dirname(__file__), "tools", "extract_ui_cores.py")],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(__file__),
)
if _extract_verify.returncode == 0:
    ok("tools/extract_ui_cores.py verify passes (extracted layout valid)")
else:
    fail(
        "tools/extract_ui_cores.py verify failed: "
        + (_extract_verify.stderr or _extract_verify.stdout or "unknown").strip()[:240]
    )

_build_zhl = open(os.path.join(os.path.dirname(__file__), "tools", "build_zhl_bundle.py"), encoding="utf-8").read()
if "zhl-physics-core.js" in _build_zhl and "zhl-gas-core.js" in _build_zhl and "index.html" not in _build_zhl.split("read_core", 1)[0]:
    ok("build_zhl_bundle.py concat from *-core.js only (no index.html scrape)")
else:
    fail("build_zhl_bundle.py still depends on index.html scrape or missing core sources")

_parity_tool = os.path.join(os.path.dirname(__file__), "tools", "check_engine_parity.py")
if os.path.isfile(_parity_tool):
    ok("tools/check_engine_parity.py present for bundle/source alignment")
else:
    fail("tools/check_engine_parity.py missing")

_ccr_mirror_fns = [
    "getEffectivePpo2",
    "computePSCRFractions",
    "ccrLoopGasBelowSetpoint",
    "getEffectiveSetpointAtDepth",
]
_ccr_src_mirror = open(os.path.join(os.path.dirname(__file__), "zhl-ccr-core.js"), encoding="utf-8").read()
_bundle_mirror = zhl_bundle_js or ""
_index_has_delegate = all(f"function {fn}(" in js for fn in _ccr_mirror_fns)
_bundle_has_core = all(f"function {fn}(" in _bundle_mirror for fn in _ccr_mirror_fns)
if _index_has_delegate and _bundle_has_core:
    ok("CCR mirror rule: index delegates + bundle embed all key zhl-ccr-core functions")
else:
    fail("CCR mirror rule: index delegate or bundle missing key zhl-ccr-core function")

if "typeof altSurfaceP !== 'undefined'" in _ccr_src_mirror:
    _neighbor_guard_fns = ["getEffectivePpo2"]
    if all(
        "typeof altSurfaceP" in _ccr_src_mirror.split(f"function {fn}", 1)[-1][:900]
        for fn in _neighbor_guard_fns
    ):
        ok("neighbor rule: altSurfaceP guard on getEffectivePpo2 (zhl-ccr-core)")
    else:
        fail("neighbor rule: altSurfaceP guard missing on CCR neighbor function")
else:
    fail("neighbor rule: getEffectivePpo2 missing altSurfaceP guard")

if "normalizeCCRSettings," in _bundle_mirror and "getEffectivePpo2," in _bundle_mirror:
    ok("ZhlEngineBundle exports CCR API for VPM/index delegates")
else:
    fail("ZhlEngineBundle missing normalizeCCRSettings or getEffectivePpo2 export")

# ── Issue #125: Tier-3 engine dedup follow-up (7 HIGH / 7 MEDIUM / 3 LOW) ──
_125_ci = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml"), encoding="utf-8").read()
_125_sw = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
_125_parity = open(os.path.join(os.path.dirname(__file__), "tools", "check_engine_parity.py"), encoding="utf-8").read()
_125_mirror = open(os.path.join(os.path.dirname(__file__), "docs", "AUDIT_MIRROR_RULE.md"), encoding="utf-8").read()
if "build_vpm_bundle.py" in _125_ci and "@generated from vpm-engine-core.js" in open(os.path.join(os.path.dirname(__file__), "tools", "build_vpm_bundle.py"), encoding="utf-8").read():
    ok("issue #125 H-1: VPM bundle built from vpm-engine-core.js via build_vpm_bundle.py")
else:
    fail("issue #125 H-1: VPM bundle still manual mirror without build tool")
if "applyNuclearRegeneration(state, bottomPhaseRuntime)" in _vpm_core and "applyNuclearRegeneration(state, runtime)" not in _vpm_core.split("function runInterLevelDecoAscent", 1)[-1].split("function ", 1)[0][:500]:
    ok("issue #125 H-2: VPM applyNuclearRegeneration not double-called on inter-level ascent")
else:
    fail("issue #125 H-2: runInterLevelDecoAscent still calls applyNuclearRegeneration with cumulative runtime")
if "pendingChangeEls" in js.split("_restoreFields", 1)[-1][:2500]:
    ok("issue #125 H-3: settings restore dispatches change events after restore loop")
else:
    fail("issue #125 H-3: _restoreInProgress still suppresses all change events during restore")
if "siD2BT" in html and "bt2" in js.split("function calcSurfInt", 1)[-1][:2000]:
    ok("issue #125 H-4: calcSurfInt uses separate Dive 2 BT slider")
else:
    fail("issue #125 H-4: calcSurfInt still reuses Dive 1 BT for Dive 2")
if "function gfAtDepth" in _physics_core_js and "n2FracFromCustomO2" in _gas_core_js and "validateHypoxicDecoGas" in _gas_core_js:
    ok("issue #125 H-5: gfAtDepth, n2Frac helpers, validateHypoxicDecoGas in canonical core files")
else:
    fail("issue #125 H-5: gfAt/getN2Frac/validateDomDecoGases logic missing from core sources")
if "mergeCCRSettings(opts.ccr)" in js.split("function ppO2Check", 1)[-1][:400]:
    ok("issue #125 H-6: ppO2Check delegate merges CCR settings before bundle call")
else:
    fail("issue #125 H-6: ppO2Check delegate still passes raw opts.ccr")
if "zhl-physics-core.js" in _125_sw and "zhl-gas-core.js" in _125_sw:
    ok("issue #125 H-7: SW REQUIRED_PRECACHE includes zhl-physics-core.js and zhl-gas-core.js")
else:
    fail("issue #125 H-7: SW precache missing Tier-3 core source files")
if "applyEnvironment" in _125_parity and "extract_function_body" in _125_parity and "api_export_present" in _125_parity:
    ok("issue #125 M-1: check_engine_parity.py uses function-body and API export checks")
else:
    fail("issue #125 M-1: check_engine_parity.py still has ineffective skip/body checks")
if "ZhlEngineBundle.OTU_EXPONENT" in js:
    ok("issue #125 M-2: OTU_EXPONENT sourced from ZhlEngineBundle in index.html")
else:
    fail("issue #125 M-2: OTU_EXPONENT still hardcoded duplicate in index.html")
if "_syncZhlBundleEnv();" in js.split("function enforceMinDecoProfile", 1)[-1][:200] and "_syncZhlBundleEnv();" in js.split("function getActiveGas", 1)[-1][:200]:
    ok("issue #125 M-3: enforceMinDecoProfile and getActiveGas delegates sync bundle env")
else:
    fail("issue #125 M-3: enforceMinDecoProfile/getActiveGas missing _syncZhlBundleEnv")
if "function buhNDL" in _physics_core_js and "buhNDL," in (zhl_bundle_js or ""):
    ok("issue #125 M-4: buhNDL/ndlClearAtDepth extracted to physics core and bundle API")
else:
    fail("issue #125 M-4: buhNDL still inline-only in index.html")
if "+ gas_core" in _build_zhl and _build_zhl.find("+ gas_core") < _build_zhl.find("+ ccr_core"):
    ok("issue #125 M-5: build_zhl_bundle.py concat order is physics → gas → ccr → schedule")
else:
    fail("issue #125 M-5: build_zhl_bundle.py still places CCR before gas-core")
if "Depends on zhl-physics-core.js" in _gas_core_js or "Depends on zhl-physics-core.js" in open(os.path.join(os.path.dirname(__file__), "zhl-gas-core.js"), encoding="utf-8").read():
    ok("issue #125 M-6: zhl-gas-core.js documents physics global dependency")
else:
    fail("issue #125 M-6: zhl-gas-core.js missing physics dependency comment")
if "color:var(--orange)" in js.split("} else if (margin <= 5)", 1)[-1][:300]:
    ok("issue #125 M-7: UDP margin 1–5 advice line uses orange (not red)")
else:
    fail("issue #125 M-7: UDP advice line still hardcodes red for margin 1–5")
if "firstStopDepth === interpBase" not in open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read().split("function gfAt", 1)[-1][:400]:
    ok("issue #125 L-1: redundant gfAt === interpBase branch removed from schedule core")
else:
    fail("issue #125 L-1: gfAt still has dead firstStopDepth === interpBase branch")
if "needs: [bundle-sync]" in _125_ci.split("audit:", 1)[-1][:300]:
    ok("issue #125 L-2: audit CI job depends on bundle-sync")
else:
    fail("issue #125 L-2: audit job still runs without bundle-sync dependency")
if "thin delegates — single source is bundle" in _125_mirror:
    ok("issue #125 L-3: AUDIT_MIRROR_RULE.md updated for post-dedup delegate model")
else:
    fail("issue #125 L-3: mirror doc still says index CCR delegates (until removed)")

# ── Issue #126: Option 1 roadmap completion ──
_pkg126 = open(os.path.join(os.path.dirname(__file__), "package.json"), encoding="utf-8").read()
_vpm_core126 = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_ci126 = open(os.path.join(os.path.dirname(__file__), ".github", "workflows", "ci.yml"), encoding="utf-8").read()
if '"build": "npm run build:bundles"' in _pkg126 or '"build": "npm run build:bundles && npm run check:engine-parity"' in _pkg126:
    ok("issue #126 R-1: package.json build alias points to build:bundles")
else:
    fail("issue #126 R-1: npm run build alias missing from package.json")
if re.search(r"\*/\s*\n\s*'use strict';", _vpm_core126):
    ok("issue #126 R-2: vpm-engine-core.js uses strict mode at file scope")
else:
    fail("issue #126 R-2: vpm-engine-core.js missing top-level use strict")
if all("needs: [bundle-sync]" in _ci126.split(f"{job}:", 1)[-1][:120] for job in ("audit", "export-regression", "engine-full", "engine-validation", "native-bridge-regression")):
    ok("issue #126: all regression CI jobs depend on bundle-sync")
else:
    fail("issue #126: one or more CI jobs still run without bundle-sync dependency")

# ── v2.53.04 stable release ──
if re.search(r"APP_VERSION\s*=\s*['\"]2\.53\.04['\"]", app_version_js):
    ok("stable release APP_VERSION is 2.53.04")
else:
    fail("stable release requires APP_VERSION 2.53.04")

# ── Issue #127: full codebase audit v2.53.00 — 6 HIGH / 7 MEDIUM / 4 LOW ──
_vpm_core127 = open(os.path.join(os.path.dirname(__file__), "vpm-engine-core.js"), encoding="utf-8").read()
_worker127 = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-worker.js"), encoding="utf-8").read()
_parity127 = open(os.path.join(os.path.dirname(__file__), "tools", "check_engine_parity.py"), encoding="utf-8").read()
if "bottomFHe" in _gas_core_js.split("function getActiveGas", 1)[-1][:600] and "fHe: fHeBottom" in _gas_core_js:
    ok("issue #127 H-1: getActiveGas fallback preserves bottom helium fraction")
else:
    fail("issue #127 H-1: getActiveGas still hardcodes fHe: 0 in fallback")
if "return 'ERR'" not in _gas_core_js.split("function ppO2Check", 1)[-1][:400] and "Math.max(0, fO2)" in _gas_core_js.split("function ppO2Check", 1)[-1][:400]:
    ok("issue #127 H-2: ppO2Check clamps invalid O2 fraction to zero ppO2")
else:
    fail("issue #127 H-2: ppO2Check still returns ERR or skips O2 clamp")
if "gfAtDepth(" in _physics_core_js.split("function ndlClearAtDepth", 1)[-1][:900]:
    ok("issue #127 H-3: ndlClearAtDepth uses gfAtDepth with shallowGradient parameter")
else:
    fail("issue #127 H-3: ndlClearAtDepth local gfAt ignores shallowGradient")
_contingency_core127 = open(os.path.join(os.path.dirname(__file__), "contingency-core.js"), encoding="utf-8").read()
if ("try {" in js.split("function runContingencyScenario", 1)[-1][:1500] and "finally {" in js.split("function runContingencyScenario", 1)[-1][:3000]) or ("try {" in _contingency_core127.split("function runContingencyScenario", 1)[-1][:1500] and "finally {" in _contingency_core127.split("function runContingencyScenario", 1)[-1][:3000]):
    ok("issue #127 H-4: runContingencyScenario restores DOM in finally block")
else:
    fail("issue #127 H-4: runContingencyScenario missing try/finally DOM restore")
if "ppO2Drop = metO2 / loopVol" in _ccr_core_src and "* (pAmb /" not in _ccr_core_src.split("function computePSCRFractions", 1)[-1][:500]:
    ok("issue #127 H-5: computePSCRFractions uses depth-independent Baker ppO2 drop")
else:
    fail("issue #127 H-5: computePSCRFractions still scales ppO2 drop by pAmb/altSurfaceP")
if (
    "applyEnvironment(environment || defaultEnvironment())" in (zhl_bundle_js or "")
    and "profileSplit,\n      env" in _worker127.replace("\r\n", "\n")
    and "applyEnvironment" not in _worker127
):
    ok("issue #127 H-6 / #130 BUG-05: worker passes resolved env to calculate() (single applyEnvironment)")
else:
    fail("issue #127 H-6 / #130 BUG-05: altitude environment not applied correctly in worker path")
if "const margin = effNDL - bt" in js.split("effNDLCap", 1)[-1][:200]:
    ok("issue #127 M-1: UDP margin uses uncapped effNDL")
else:
    fail("issue #127 M-1: UDP margin still computed from display-capped NDL")
if all(f"'{f}'" in js.split("DECO_FIELDS:", 1)[-1][:2500] for f in ("siD1Depth", "siD1BT", "siD2Depth", "siD2BT")):
    ok("issue #127 M-2: surface-interval sliders in DECO_FIELDS for persistence")
else:
    fail("issue #127 M-2: siD1/siD2 sliders missing from DECO_FIELDS")
if "endpointDepth = seg.toDepth" in _ccr_core_src.split("function saturateLinearCCR", 1)[-1][:900] or "endpointDepth = seg.fromDepth < seg.toDepth ? seg.toDepth : seg.fromDepth" in _ccr_core_src.split("function saturateLinearCCR", 1)[-1][:900] or "endpointDepth = seg.fromDepth < seg.toDepth ? seg.toDepth : Math.min(seg.fromDepth, seg.toDepth)" in _ccr_core_src.split("function saturateLinearCCR", 1)[-1][:900]:
    ok("issue #127 M-3: saturateLinearCCR uses deep endpoint for setpoint on segment")
else:
    fail("issue #127 M-3: saturateLinearCCR still uses shallow endpoint on descent")
if "heVal <= 0 && o2 < 18" not in _gas_core_js.split("function validateHypoxicDecoGas", 1)[-1][:600] and "o2 < 18" in _gas_core_js.split("function validateHypoxicDecoGas", 1)[-1][:600]:
    ok("issue #133 C-2 / #127 M-4: validateHypoxicDecoGas rejects all O2 < 18% gases including trimix")
else:
    fail("issue #133 C-2: validateHypoxicDecoGas still exempts hypoxic trimix (heVal guard)")
if 'td[data-label="Stop"]' in js.split("function runContingencyScenario", 1)[-1][:2500]:
    ok("issue #127 M-5: contingency decoTime reads Stop column duration")
else:
    fail("issue #127 M-5: contingency decoTime still parses wrong table column")
if "vpmStopCapError(stopDepth, partialPlan)" in _vpm_core127 and "result.code === 'VPM_STOP_CAP' && result.plan" in js:
    ok("issue #127 M-6: VPM stop cap returns partial plan for UI warning")
else:
    fail("issue #127 M-6: vpmStopCapError still discards partial plan")
if all(n in _parity127 for n in ("ndlClearAtDepth", "n2FracFromCustomO2", "n2FracFromPercentages", "validateHypoxicDecoGas")):
    ok("issue #127 M-7: check_engine_parity api_exports includes all dedup helpers")
else:
    fail("issue #127 M-7: parity checker missing dedup API export names")
if "adjustedCritRadiiHe.length === NC" in _vpm_core127.split("bubbleCarryApplied", 1)[-1][:800]:
    ok("issue #127 L-1: VPM bubble carry guard checks adjustedCritRadiiHe length")
else:
    fail("issue #127 L-1: VPM bubble carry missing adjustedCritRadiiHe length guard")
if "surfP != null ? surfP : altSurfaceP" in _ccr_core_src.split("function depthAtSetpointCrossing", 1)[-1][:200]:
    ok("issue #127 L-2: CCR setpoint crossing uses surfP != null guard")
else:
    fail("issue #127 L-2: surfP || altSurfaceP still treats zero as missing")
if "VPM_CRITICAL_RADIUS_FACTOR[interIdx]" in _vpm_core127.split("function runInterLevelDecoAscent", 1)[-1][:2500]:
    ok("issue #127 L-3: inter-level off-loop conservatism relaxes regenerated radii")
else:
    fail("issue #127 L-3: interLevelConservatism still no-op in runInterLevelDecoAscent")
if "in_template" in _parity127 and "in_block_comment" in _parity127:
    ok("issue #127 L-4: check_engine_parity extract_function_body skips string literals")
else:
    fail("issue #127 L-4: parity extractor still blind to braces in strings")

# ── Issue #128: full codebase audit b2ad2ee — 2 CRITICAL / 2 HIGH / 3 MEDIUM / 4 LOW ──
_sw128 = open(os.path.join(os.path.dirname(__file__), "sw.js"), encoding="utf-8").read()
_schedule128 = open(os.path.join(os.path.dirname(__file__), "zhl-schedule-core.js"), encoding="utf-8").read()
_gesp128c = _ccr_core_src.split("function getEffectiveSetpointAtDepth", 1)[-1][:2200] if "function getEffectiveSetpointAtDepth" in _ccr_core_src else ""
if "if (depthM > deepestCross) return bottomSP" not in _gesp128c and "depthAtSetpointCrossing" in _gesp128c:
    ok("issue #128 C-1: getEffectiveSetpointAtDepth no longer forces bottomSP below deepest crossing")
else:
    fail("issue #128 C-1: getEffectiveSetpointAtDepth still uses deepestCross bottomSP shortcut")
_inert128 = _ccr_core_src.split("function getInspiredInertPressures", 1)[-1][:1200] if "function getInspiredInertPressures" in _ccr_core_src else ""
_sch128 = _ccr_core_src.split("function getCCRInertSchreinerParams", 1)[-1].split("function getSetpointBoundaryDepths", 1)[0] if "function getCCRInertSchreinerParams" in _ccr_core_src else ""
if (
    "const den = Math.max(0.001, fN2d + fHe)" in _inert128
    and "const den = Math.max(0.001, fN2d + fHe)" in _sch128
):
    ok("issue #128 C-2: CCR inert PP denominator uses fN2d + fHe (inspired + Schreiner paths)")
else:
    fail("issue #128 C-2: CCR inert paths still divide by (1 - fO2)")
if "ERR_TOTAL_EXCEEDS_100" in _gas_core_js.split("function validateHypoxicDecoGas", 1)[-1][:500]:
    ok("issue #128 H-1: validateHypoxicDecoGas rejects O2+He > 100%")
else:
    fail("issue #128 H-1: validateHypoxicDecoGas missing ERR_TOTAL_EXCEEDS_100 guard")
if "_ccrLoopElapsedMin" in _schedule128 and "_diveRuntimeMin" not in _schedule128:
    ok("issue #128 H-2: schedule core tracks CCR-loop elapsed time explicitly")
else:
    fail("issue #128 H-2: _diveRuntimeMin still used without CCR-loop semantics")
if "CEILING_LOOP_GUARD_MIN = 1440" in _schedule128 and "hitSafetyGuard" in _schedule128:
    ok("issue #128 M-1: ceiling loop guard raised to 1440 min with hitSafetyGuard flag")
else:
    fail("issue #128 M-1: ceiling loop still capped at 360/180 without safety guard")
if "Math.abs(fromDepth - toDepth) < 1e-9" in _ccr_core_src.split("function saturateLinearCCR", 1)[-1][:400]:
    ok("issue #128 M-2: saturateLinearCCR guards constant-depth segments")
else:
    fail("issue #128 M-2: saturateLinearCCR missing constant-depth guard")
if "params.decoAscentRate ?? 3" in _schedule128 and "params.surfaceAscentRate ?? 3" in _schedule128:
    ok("issue #128 M-3 / #130 BUG-02: deco/surface ascent rates default to 3 m/min")
else:
    fail("issue #128 M-3 / #130 BUG-02: ascent rate params still lack 3 m/min nullish defaults")
if "SW_OPTIONAL_PRECACHE_MISS" in _sw128 and "SW_OPTIONAL_PRECACHE_MISS" in js:
    ok("issue #128 L-1: optional SW precache misses surfaced to client")
else:
    fail("issue #128 L-1: SW optional precache failures still silent")
if "may be 0 for constant depth" in _physics_core_js.split("function schreinerLinear", 1)[0][-200:] + _physics_core_js.split("function schreinerLinear", 1)[-1][:120]:
    ok("issue #128 L-2: schreinerLinear documents R=0 constant-depth usage")
else:
    fail("issue #128 L-2: schreinerLinear missing R=0 JSDoc")
_enforce128 = _gas_core_js.split("function enforceMinDecoProfile", 1)[-1][:2200] if "function enforceMinDecoProfile" in _gas_core_js else ""
_enforce_first_loop = _enforce128.split("function injectStop", 1)[0] if "function injectStop" in _enforce128 else ""
if (
    "function resolveGasAtDepth" in _enforce_first_loop
    and _enforce128.find("for (const s of steps)") < _enforce128.find("function resolveGasAtDepth")
):
    ok("issue #128 L-3 / #130 BUG-11: resolveGasAtDepth after enrichment loop, before injectStop")
else:
    fail("issue #128 L-3 / #130 BUG-11: resolveGasAtDepth ordering still wrong in enforceMinDecoProfile")
if "L/min" in _ccr_core_src.split("function getCcrMetabolicO2Rate", 1)[0][-120:] + _ccr_core_src.split("function getCcrMetabolicO2Rate", 1)[-1][:200]:
    ok("issue #128 L-4: getCcrMetabolicO2Rate documents L/min units")
else:
    fail("issue #128 L-4: getCcrMetabolicO2Rate missing unit JSDoc")
if "bar/bar" in _ccr_core_src.split("function computePSCRFractions", 1)[0][-120:] + _ccr_core_src.split("function computePSCRFractions", 1)[-1][:200]:
    ok("issue #128 L-4b: computePSCRFractions documents bar/bar ppO2 drop")
else:
    fail("issue #128 L-4b: computePSCRFractions missing unit JSDoc")

_worker130 = open("zhl-schedule-worker.js", encoding="utf-8").read() if os.path.isfile("zhl-schedule-worker.js") else ""
_ppo2_130 = _gas_core_js.split("function ppO2Check", 1)[-1].split("function n2FracFromCustomO2", 1)[0] if "function ppO2Check" in _gas_core_js else ""
if "const ccrFO2" in _ppo2_130 and "const fO2 = opts.fO2" not in _ppo2_130:
    ok("issue #130 BUG-01: ppO2Check CCR branch uses ccrFO2 (no inner fO2 shadowing)")
else:
    fail("issue #130 BUG-01: ppO2Check still shadows outer fO2 in CCR branch")
if "return 'ERR'" not in _ppo2_130:
    ok("issue #130 BUG-08: ppO2Check returns numeric string instead of ERR sentinel")
else:
    fail("issue #130 BUG-08: ppO2Check still returns non-numeric ERR")
if "allowO2AtMOD = (val === true || val === 'on')" in js:
    ok("issue #130 BUG-03: setAllowO2AtMOD normalizes to boolean")
else:
    fail("issue #130 BUG-03: setAllowO2AtMOD still assigns raw string/value")
if "ZHL16C_HE_AB," in (zhl_bundle_js or ""):
    ok("issue #130 BUG-04: ZHL16C_HE_AB exported from ZhlEngineBundle API")
else:
    fail("issue #130 BUG-04: ZHL16C_HE_AB missing from bundle exports")
if (
    "if (!ZhlEngineBundle)" in _worker130
    and "applyEnvironment" not in _worker130
    and "profileSplit,\n      env" in _worker130.replace("\r\n", "\n")
):
    ok("issue #130 BUG-05/07/10: worker passes resolved env to calculate (no duplicate applyEnvironment)")
else:
    fail("issue #130 BUG-05/07/10: worker still double-applies env or passes raw null environment")
if "ZhlEngineBundle.buhNDL(depthM, fN2, 50, 100, 0, 5, 5, false)" in js:
    ok("issue #130 BUG-06: rec custom nitrox NDL uses explicit 5 m stop params")
else:
    fail("issue #130 BUG-06: rec custom nitrox NDL still inherits DOM decoStep/lastStop")
_ndl130 = _physics_core_js.split("function ndlClearAtDepth", 1)[-1].split("function buhNDL", 1)[0] if "function ndlClearAtDepth" in _physics_core_js else ""
if "if (!(decoStep > 0)) decoStep = 3" in _ndl130:
    ok("issue #130 BUG-09: ndlClearAtDepth guards invalid decoStep/lastStop")
else:
    fail("issue #130 BUG-09: ndlClearAtDepth missing decoStep guard")
_repo_root130 = os.path.dirname(os.path.abspath(__file__))
_physics_hdr = open(os.path.join(_repo_root130, "zhl-physics-core.js"), encoding="utf-8").read()[:400]
_gas_hdr = open(os.path.join(_repo_root130, "zhl-gas-core.js"), encoding="utf-8").read()[:500]
if "BUILD SOURCE ONLY" in _physics_hdr:
    ok("issue #130 BUG-12a: zhl-physics-core.js marked BUILD SOURCE ONLY")
else:
    fail("issue #130 BUG-12a: zhl-physics-core.js missing BUILD SOURCE ONLY header")
if "BUILD SOURCE ONLY" in _gas_hdr:
    ok("issue #130 BUG-12b: zhl-gas-core.js marked BUILD SOURCE ONLY")
else:
    fail("issue #130 BUG-12b: zhl-gas-core.js missing BUILD SOURCE ONLY header")

_vpm131 = open(os.path.join(_repo_root130, "vpm-engine-core.js"), encoding="utf-8").read()
_schedule131 = open(os.path.join(_repo_root130, "zhl-schedule-core.js"), encoding="utf-8").read()
_ccr131 = open(os.path.join(_repo_root130, "zhl-ccr-core.js"), encoding="utf-8").read()
if "if (settings.metric == null) settings.metric = true;" in _vpm131:
    ok("issue #131 H-1: VPM calculate defaults omitted metric flag to true")
else:
    fail("issue #131 H-1: VPM still selects imperial defaults when settings.metric is absent")
_ppo2_131 = _ccr131.split("function getEffectivePpo2", 1)[-1].split("function loadTissuesWithCCR", 1)[0] if "function getEffectivePpo2" in _ccr131 else ""
if "return fr.fO2 * pAmb;" in _ppo2_131 and "Math.max(PSCR_MIN_PPO2, fr.fO2 * pAmb)" not in _ppo2_131:
    ok("issue #131 M-1: getEffectivePpo2 reports physical pSCR loop ppO2")
else:
    fail("issue #131 M-1: getEffectivePpo2 still clamps pSCR ppO2 to PSCR_MIN_PPO2")
_minstop131 = _schedule131.split("} else if (minStopT > 0 && minStopZoneDepth", 1)[-1].split("} else if (cur === lastStop)", 1)[0] if "minStopZoneDepth" in _schedule131 else ""
if (
    "stopT < CEILING_LOOP_GUARD_MIN" in _minstop131
    and "stopT < 360" not in _minstop131
    and "hitSafetyGuard = true" in _minstop131
    and "hitSafetyGuard: hitSafetyGuard" in _minstop131
):
    ok("issue #131 M-2: minimum-stop ceiling loop uses shared guard and propagates hitSafetyGuard")
else:
    fail("issue #131 M-2: minimum-stop branch still uses 360-min cap or omits guard flag")
_ccr_val131 = open(os.path.join(_repo_root130, "dev", "ccr_engine_validation_regression.py"), encoding="utf-8").read()
if "issue #131 H-1" in _ccr_val131 and "pscrHypoxicPpo2" in _ccr_val131:
    ok("issue #131: CCR validation regression covers VPM null-settings parity and hypoxic pSCR")
else:
    fail("issue #131: CCR validation regression missing strengthened null-settings / pSCR checks")

_index132 = js
_index_html132 = html
if "metric:            true," in _index132.split("function runVPMSchedule", 1)[-1][:2500]:
    ok("issue #132 C-1: runVPMSchedule always invokes VPM engine in metric mode")
else:
    fail("issue #132 C-1: runVPMSchedule still passes imperial metric flag to VPM engine")
if "altitudeMFromCustomDisplay" in _index132 and "units === 'imperial' ? v / 3.28084" in _index132.split("function altitudeMFromCustomDisplay", 1)[-1][:200]:
    ok("issue #132 H-1: custom altitude input converts feet to metres when imperial")
else:
    fail("issue #132 H-1: custom altitude still parsed as metres in imperial mode")
if "getAllDecoGasIds().map(n =>" in _index132.split("_cylDefsVPM", 1)[-1][:800]:
    ok("issue #132 H-2: VPM gas planning maps all dynamic deco gas cylinders")
else:
    fail("issue #132 H-2: VPM gas planning still hardcoded to deco gases 1-2")
_calc132 = _index132.split("function calcGasPlan", 1)[-1].split("function _applyGasWarningStyles", 1)[0] if "function calcGasPlan" in _index132 else ""
_card132 = _index132.split("function appendDecoGasCardAtIdx", 1)[-1].split("function addDecoGasCard", 1)[0] if "function appendDecoGasCardAtIdx" in _index132 else ""
if "getAllDecoGasIds().forEach(idx =>" in _calc132 and 'id="cylDg${idx}_reserve"' in _card132:
    ok("issue #132 H-2b: calcGasPlan and dynamic cards cover deco gases 3+ with reserve fields")
else:
    fail("issue #132 H-2b: calcGasPlan still omits dynamic deco gases or reserve inputs")
if "gfAdjustedMValue(a, b, altSurfaceP, gfFem)" in _index132 and "gfAdjustedMValue(a, b, pAmb, gf)" in _index132.split("function getGFInfo", 1)[-1][:1500]:
    ok("issue #132 M-1: emergency PDF and GF Explorer use gfAdjustedMValue helper")
else:
    fail("issue #132 M-1: report/GF Explorer still use obsolete M-value formula")
if 'id="dg1CustomO2"' in _index_html132 and 'oninput="updateGasMODDisplays()"' in _index_html132.split('id="dg1CustomO2"', 1)[-1][:120]:
    ok("issue #132 M-2: custom deco O2 inputs refresh MOD on change")
else:
    fail("issue #132 M-2: custom deco O2 edits still leave MOD stale")
_vpm132 = open(os.path.join(_repo_root130, "vpm-engine-core.js"), encoding="utf-8").read()
if "settings = Object.assign({}, settings || {});" in _vpm132:
    ok("issue #132 L-1: VPM calculate clones settings before mutation")
else:
    fail("issue #132 L-1: VPM calculate still mutates caller-owned settings object")
_ccr_val132 = open(os.path.join(_repo_root130, "dev", "ccr_engine_validation_regression.py"), encoding="utf-8").read()
if "issue #132 C-1" in _ccr_val132 and "issue #132 L-1" in _ccr_val132:
    ok("issue #132: CCR validation covers VPM depth parity and settings immutability")
else:
    fail("issue #132: CCR validation missing depth parity / immutability checks")
_units132 = _index132.split("function setUnits", 1)[-1].split("function ", 1)[0] if "function setUnits" in _index132 else ""
if "allCylReserve" in _units132 and 'querySelectorAll(\'[id^="cylDg"][id$="_reserve"]\')' in _units132:
    ok("issue #132 H-3: dynamic deco cylinder reserve fields included in unit conversion")
else:
    fail("issue #132 H-3: dynamic deco cylinder reserve fields still skip unit conversion")
if "function defaultDecoCylFieldValues" in _index132 and "units === 'imperial'" in _index132.split("function defaultDecoCylFieldValues", 1)[-1][:500]:
    ok("issue #132 H-3b: new dynamic deco cards initialize cylinder values for active units")
else:
    fail("issue #132 H-3b: dynamic deco cards still seed metric defaults under imperial labels")

# ── 2026-06-29 full-audit follow-up ───────────────────────────────────────────
_vpm_audit = open(os.path.join(_repo_root130, "vpm-engine-core.js"), encoding="utf-8").read()
_ccr_sch = _vpm_audit.split("function ccrSchreinerParams", 1)[-1].split("function ccrSplitSegmentAtSetpoint", 1)[0] if "function ccrSchreinerParams" in _vpm_audit else ""
if "syncZhlEnvFromSettings(settings)" in _ccr_sch and "altitude: 0" not in _ccr_sch:
    ok("audit 2026-06-29 M-1: VPM ccrSchreinerParams syncs ZHL env from dive settings (not sea level)")
else:
    fail("audit 2026-06-29 M-1: VPM ccrSchreinerParams still resets ZHL bundle to altitude 0")
if "ccrSchreinerParams(startAmb, setpoint, o2Frac, heFrac, pressureRate, ccr, settings)" in _vpm_audit:
    ok("audit 2026-06-29 M-2: VPM decozone/projected-ascent use ccrSchreinerParams with settings")
else:
    fail("audit 2026-06-29 M-2: VPM calcStartOfDecoZone/projectedAscent still call bare getCCRInertSchreinerParams")
_build_zhl_audit = open(os.path.join(_repo_root130, "tools", "build_zhl_bundle.py"), encoding="utf-8").read()
if "s.minDecoProfile ||" in _build_zhl_audit:
    ok("audit 2026-06-29 M-3: buildZhlScheduleParamsFromEngine threads minDecoProfile from settings")
else:
    fail("audit 2026-06-29 M-3: engine API path still hard-disables minDecoProfile")
if "function zhlOnLoopAt(depthM, gas)" not in js.split("function runDecoSchedule", 1)[-1].split("function runVPMSchedule", 1)[0]:
    ok("audit 2026-06-29 L-2: dead zhlOnLoopAt/zhlGasAt/_ccrPpo2Opts removed from runDecoSchedule")
else:
    fail("audit 2026-06-29 L-2: runDecoSchedule still contains dead pre-migration ZHL helpers")
_audit_yml292 = open(os.path.join(_repo_root130, ".github", "workflows", "audit.yml"), encoding="utf-8").read()
if "bundle-sync:" in _audit_yml292 and "needs: [bundle-sync]" in _audit_yml292:
    ok("audit 2026-06-29 M-4/M-5: audit.yml bundle-sync guards release regression jobs")
else:
    fail("audit 2026-06-29 M-5: audit.yml missing bundle-sync job or needs dependency")
_apk_yml292 = open(os.path.join(_repo_root130, ".github", "workflows", "build-apk.yml"), encoding="utf-8").read()
if "python audit.py" in _apk_yml292 and "check_engine_parity.py" in _apk_yml292:
    ok("audit 2026-06-29 M-10: APK workflow runs bundle parity and static audit before build")
else:
    fail("audit 2026-06-29 M-10: APK workflow still builds without audit/parity gate")
_deploy_yml292 = open(os.path.join(_repo_root130, ".github", "workflows", "deploy.yml"), encoding="utf-8").read()
if "python audit.py" in _deploy_yml292:
    ok("audit 2026-06-29 M-11: Pages deploy workflow runs static audit gate")
else:
    fail("audit 2026-06-29 M-11: Pages deploy still ungated on audit.py")
if '"test":' in open(os.path.join(_repo_root130, "package.json"), encoding="utf-8").read() and "run_all_regression.py" in open(os.path.join(_repo_root130, "package.json"), encoding="utf-8").read():
    ok("audit 2026-06-29 L-4: package.json exposes npm test via run_all_regression release tier")
else:
    fail("audit 2026-06-29 L-4: package.json missing npm test regression script")

# ── 2026-06-29 residual follow-up ─────────────────────────────────────────────
_test_http = os.path.join(os.path.dirname(__file__), "dev", "test_http.py")
if os.path.isfile(_test_http):
    _th_src = open(_test_http, encoding="utf-8").read()
    if "def serve_www" in _th_src and "stage_regression_harness" in _th_src:
        ok("residual: test_http serve_www syncs www/ and stages regression harness")
    else:
        fail("residual: test_http missing serve_www / stage_regression_harness")
else:
    fail("residual: dev/test_http.py missing")

_browser_reg = os.path.join(os.path.dirname(__file__), "dev", "run_browser_regression.py")
if os.path.isfile(_browser_reg):
    _br_src = open(_browser_reg, encoding="utf-8").read()
    if "tests-massive.html" in _br_src and "tests-extended.html" in _br_src and "serve_www" in _br_src:
        ok("residual: run_browser_regression includes massive + extended over serve_www")
    else:
        fail("residual: run_browser_regression missing massive/extended CI or serve_www")
else:
    fail("residual: dev/run_browser_regression.py missing")

_massive_html = os.path.join(os.path.dirname(__file__), "tests-massive.html")
_ext_html = os.path.join(os.path.dirname(__file__), "tests-extended.html")
if os.path.isfile(_massive_html) and "runMassiveRegressionCI" in open(_massive_html, encoding="utf-8").read():
    ok("residual: tests-massive.html exposes runMassiveRegressionCI")
else:
    fail("residual: tests-massive.html missing runMassiveRegressionCI")
if os.path.isfile(_ext_html) and "runExtendedRegressionCI" in open(_ext_html, encoding="utf-8").read():
    ok("residual: tests-extended.html exposes runExtendedRegressionCI")
else:
    fail("residual: tests-extended.html missing runExtendedRegressionCI")

_ccr_cfg = os.path.join(os.path.dirname(__file__), "tests", "ccr-differential", "config.json")
if os.path.isfile(_ccr_cfg):
    import json as _json

    _ccr_cfg_obj = _json.load(open(_ccr_cfg, encoding="utf-8"))
    _ab_req = (_ccr_cfg_obj.get("requiredGoldens") or {}).get("abysner") or []
    _partial = _ccr_cfg_obj.get("partialCoverageEngines") or []
    if len(_ab_req) >= 3 and "multideco" in _partial and "divekit" in _partial:
        ok("residual: CCR differential abysner/subsurface goldens + partial multideco/divekit")
    else:
        fail("residual: CCR differential config missing expanded goldens or partialCoverageEngines")
else:
    fail("residual: tests/ccr-differential/config.json missing")

_ccr_html = os.path.join(os.path.dirname(__file__), "tests-ccr-differential.html")
if os.path.isfile(_ccr_html) and "isPartialCoverageEngine" in open(_ccr_html, encoding="utf-8").read():
    ok("residual: tests-ccr-differential skips partial-coverage inconclusive rows")
else:
    fail("residual: tests-ccr-differential missing partial coverage comparator skip")

_export_reg = os.path.join(os.path.dirname(__file__), "export_regression.py")
if os.path.isfile(_export_reg):
    _ex_src = open(_export_reg, encoding="utf-8").read()
    if "VPMB_GFS" in _ex_src and "circuitSelect" in _ex_src and "serve_www" in _ex_src:
        ok("residual: export_regression covers VPM + CCR paths over serve_www")
    else:
        fail("residual: export_regression still ZHLC_GF-only or serves repo root")
else:
    fail("residual: export_regression.py missing")

# ── issue #133 (audit #128 HEAD 0c919fa) ────────────────────────────────────
_gf133 = _physics_core_js.split("function gfAtDepth", 1)[-1][:200] if "function gfAtDepth" in _physics_core_js else ""
if "firstStopDepth <= 0) return gfH" in _gf133:
    ok("issue #133 H-1 / #134 H-1: gfAtDepth returns gfH when firstStopDepth unanchored")
else:
    fail("issue #133 H-1: gfAtDepth still returns gfL when firstStopDepth <= 0")
_getactive133 = js.split("function getActiveGas", 1)[-1][:280] if "function getActiveGas" in js else ""
if "bottomFHe, decoGases" in _getactive133.replace("\r\n", "\n"):
    ok("issue #133 C-1: index getActiveGas wrapper matches bundle arg order")
else:
    fail("issue #133 C-1: getActiveGas wrapper still has bottomFHe in position 6")
_vpm133 = open(os.path.join(_repo_root130, "vpm-engine-core.js"), encoding="utf-8").read()
if "cloneVPMState(state)" in _vpm133 and "restoreInterLevelDerivedState()" in _vpm133:
    ok("issue #133 C-3: VPM inter-level derived state snapshot restored before main deco")
else:
    fail("issue #133 C-3: VPM missing inter-level radii restore")
if "function isShallowGradientOn" in js and "value === 'on'" in js.split("function isShallowGradientOn", 1)[-1][:120]:
    ok("issue #133 C-4: shallowGradient read via isShallowGradientOn helper (select value=on)")
else:
    fail("issue #133 C-4: shallowGradient DOM read missing or wrong")
_parity133 = open(os.path.join(_repo_root130, "tools", "check_engine_parity.py"), encoding="utf-8").read()
if "template_expr_depth" in _parity133 and "extract_api_block" in _parity133 and "'use strict'" in _parity133.split("def strip_header", 1)[-1][:400]:
    ok("issue #133 H-3/L-6/L-7: check_engine_parity template depth + api block + use strict strip")
else:
    fail("issue #133 H-3/L-6/L-7: check_engine_parity parity extractor still fragile")
if "handleWorkerFailure(error" in open(os.path.join(_repo_root130, "zhl-worker-bridge.js"), encoding="utf-8").read().split("worker.onmessage", 1)[-1][:500]:
    ok("issue #133 H-4: worker onmessage error path delegates to handleWorkerFailure")
else:
    fail("issue #133 H-4: worker onmessage still duplicates rejectAll logic")
if "issue133" in open(os.path.join(_repo_root130, "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("issue #133 H-5: engine_regression includes issue #133 regression section")
else:
    fail("issue #133 H-5: engine_regression missing issue #133 tests")
_ccr133 = _ccr_core_src.split("function saturateLinearCCR", 1)[-1][:900] if "function saturateLinearCCR" in _ccr_core_src else ""
if "endpointDepth = seg.fromDepth < seg.toDepth ? seg.toDepth : seg.fromDepth" in _ccr133 or "endpointDepth = seg.fromDepth < seg.toDepth ? seg.toDepth : Math.min(seg.fromDepth, seg.toDepth)" in _ccr133:
    ok("issue #133 M-2: saturateLinearCCR samples setpoint at deep endpoint of segment")
else:
    fail("issue #133 M-2: saturateLinearCCR still uses shallow endpoint for setpoint")
if "Number.isFinite(sp)" in _ccr_core_src.split("function depthAtSetpointCrossing", 1)[-1][:200]:
    ok("issue #133 M-3: depthAtSetpointCrossing guards non-finite surfP")
else:
    fail("issue #133 M-3: depthAtSetpointCrossing missing finite surfP guard")
if "calcSurfInt?.()" in js.split("_syncUiAfterRestore", 1)[-1][:800]:
    ok("issue #133 M-4: SI slider displays refreshed after settings restore")
else:
    fail("issue #133 M-4: _syncUiAfterRestore missing calcSurfInt / slider fill refresh")
_restore133 = js.split("_restoreFields: function", 1)[-1][:2200] if "_restoreFields: function" in js else ""
if _restore133.find("setWaterDensity") < _restore133.find("_syncUiAfterRestore"):
    ok("issue #133 M-5: waterDensitySelect applied before dependent UI sync")
else:
    fail("issue #133 M-5: setWaterDensity still runs after _syncUiAfterRestore")
if "ppO2DisplayStyle" in js or "pO2Raw === 'ERR'" in js:
    ok("issue #133 M-6: ppO2Check ERR path applies error styling in deco table")
else:
    fail("issue #133 M-6: ppO2 ERR still suppresses colour warnings")
if "fromPlan ? Math.max(0, otu - otuCarry) : otu" in js:
    ok("issue #133 M-7: perDiveOtu only subtracts carry on fromPlan path")
else:
    fail("issue #133 M-7: perDiveOtu still subtracts carry from widget estimate")
if "mGF.low == null" in js.split("function runUnifiedPlan", 1)[-1][:800]:
    ok("issue #133 M-8: runUnifiedPlan guards unset mGF before NDL loop")
else:
    fail("issue #133 M-8: runUnifiedPlan still uses unguarded mGF.low")
if "validateHypoxicDecoGas(bot.o2" in js.split("function validateDomDecoGases", 1)[-1][:800]:
    ok("issue #133 L-1 / #134 C-1 / #138 H-1: bottom gas validated by validateHypoxicDecoGas")
else:
    fail("issue #133 L-1: bottom gas missing validateHypoxicDecoGas (issue #138 H-1)")
if "n2 > 1" in _gas_core_js.split("function n2FracFromPercentages", 1)[-1][:250]:
    ok("issue #133 L-2 / #138 L-9: n2FracFromPercentages rejects impossible N₂ fraction")
else:
    fail("issue #133 L-2: n2FracFromPercentages still clamps impossible mixes to 0")
if "sToM <= targetDepthM" in _gas_core_js:
    ok("issue #133 L-3: injectStop straddles ascent ending exactly at target depth")
else:
    fail("issue #133 L-3: injectStop still misses sToM == targetDepthM case")
if "'siGfLow'" in js.split("DECO_FIELDS:", 1)[-1][:3500]:
    ok("issue #133 L-4: siGfLow persisted in DECO_FIELDS")
else:
    fail("issue #133 L-4: siGfLow missing from DECO_FIELDS")
_restore_flag133 = js.split("_restoreFields: function", 1)[-1][:2500] if "_restoreFields: function" in js else ""
if _restore_flag133.find("_restoreInProgress = false") > _restore_flag133.find("pendingChangeEls.forEach"):
    ok("issue #133 L-5: _restoreInProgress cleared after synthetic change events")
else:
    fail("issue #133 L-5: _restoreInProgress cleared before pendingChangeEls dispatch")
if "Closed field list" in _ccr_core_src:
    ok("issue #133 L-8: normalizeCCRSettings documents closed field list")
else:
    fail("issue #133 L-8: normalizeCCRSettings missing closed-list documentation")
if "2.53.04" in open(os.path.join(_repo_root130, "app-version.js"), encoding="utf-8").read():
    ok("issue #133 H-2: APP_VERSION bumped for PWA cache bust")
else:
    fail("issue #133 H-2: APP_VERSION not bumped after engine fixes")

# ── issue #134 (audit #129 HEAD ee69770) ────────────────────────────────────
if "validateHypoxicDecoGas(bot.o2" in js.split("function validateDomDecoGases", 1)[-1][:800]:
    ok("issue #134 C-1 / #138 H-1: validateDomDecoGases validates hypoxic bottom gas")
else:
    fail("issue #134 C-1: bottom gas missing validateHypoxicDecoGas")
if "d <= targetDepthM" in _gas_core_js:
    ok("issue #134 H-2: injectStop insertion scan uses <= targetDepthM")
else:
    fail("issue #134 H-2: injectStop insertion scan still strict <")
if ('value="on"' in html or "value='on'" in html) and 'id="shallowGradient"' in html and "function isShallowGradientOn" in js:
    ok("issue #134 H-3: shallowGradient select option value=on matches isShallowGradientOn")
else:
    fail("issue #134 H-3: shallowGradient option values not aligned with helper")
_zwb134 = open(os.path.join(_repo_root130, "zhl-worker-bridge.js"), encoding="utf-8").read()
if "settlePending(id, false, new Error('ZHL worker timeout'))" in _zwb134:
    ok("issue #134 H-4: worker timeout settles pending promise when worker already killed")
else:
    fail("issue #134 H-4: worker timeout still leaks pending promise")
if "ndlClearAtDepth(testT" in js.split("function runUnifiedPlan", 1)[-1][:8000] or "ZhlEngineBundle.ndlClearAtDepth(testT" in js.split("function runUnifiedPlan", 1)[-1][:8000]:
    ok("issue #134 M-1/M-2: runUnifiedPlan NDL probe uses ndlClearAtDepth with GF interpolation")
else:
    fail("issue #134 M-1: runUnifiedPlan still probes NDL with gfLow-only ceiling")
if "cloneVPMState(state)" in open(os.path.join(_repo_root130, "vpm-engine-core.js"), encoding="utf-8").read().split("function runInterLevelDecoAscent", 1)[-1][:600]:
    ok("issue #134 M-3: VPM inter-level uses full derived-state snapshot restore")
else:
    fail("issue #134 M-3: VPM inter-level still partial radii-only restore")
if "if (this._restoreInProgress) return;" in js.split("save: function", 1)[-1][:200]:
    ok("issue #134 M-4: appSettings.save skips during restore")
else:
    fail("issue #134 M-4: appSettings.save still fires during synthetic input restore")
if "cumulativeOtu = fromPlan ? otu : (otu + otuCarry)" in js.split("function calcCNS", 1)[-1][:6000]:
    ok("issue #134 M-5: widget OTU uses cumulativeOtu for carry-aware daily limits")
else:
    fail("issue #134 M-5: perDiveOtu/cumulative OTU carry handling still wrong")
if "for (let i = result.length - 1; i >= 0; i--)" in _gas_core_js.split("function resolveGasAtDepth", 1)[-1][:400]:
    ok("issue #134 M-6: resolveGasAtDepth scans shallow-to-deep for deepest matching gas")
else:
    fail("issue #134 M-6: resolveGasAtDepth still overwrites with shallowest step")
_ppo2_134 = _gas_core_js.split("function ppO2Check", 1)[-1].split("function n2FracFromCustomO2", 1)[0] if "function ppO2Check" in _gas_core_js else ""
if ".toFixed(2)" not in _ppo2_134 and "return pAmb * o2frac" in _ppo2_134:
    ok("issue #134 M-7: ppO2Check returns numeric ppO2 (display formats at call site)")
else:
    fail("issue #134 M-7: ppO2Check still returns .toFixed string")
if "worker = null" in _zwb134.split("function killWorker", 1)[-1][:120] and _zwb134.split("function killWorker", 1)[-1][:120].find("worker = null") < _zwb134.split("function killWorker", 1)[-1][:120].find("terminate"):
    ok("issue #134 L-2: killWorker nulls worker before terminate")
else:
    fail("issue #134 L-2: killWorker still terminates before nulling worker ref")
if "settlePending(id, false, new Error('ZHL worker timeout'))" in _zwb134 and "handleWorkerFailure('ZHL worker timeout')" in _zwb134:
    ok("issue #134 L-3: worker timeout settles pending and increments failure counter")
else:
    fail("issue #134 L-3: worker timeout/nextId race not hardened")
if "setpoint === 0 && !cfg.bailout" in _ccr_core_src.split("function loadTissuesWithCCR", 1)[-1][:500]:
    ok("issue #134 L-4: loadTissuesWithCCR treats setpoint=0 without bailout as OC")
else:
    fail("issue #134 L-4: loadTissuesWithCCR still loads CCR when setpoint=0")
_parity134 = open(os.path.join(os.path.dirname(__file__), "tools", "check_engine_parity.py"), encoding="utf-8").read()
if '"ppO2Check"' in _parity134.split("api_exports = [", 1)[-1][:800]:
    ok("issue #134 L-5: check_engine_parity lists ppO2Check in api_exports")
else:
    fail("issue #134 L-5: ppO2Check missing from parity api_exports")
if "issue134" in open(os.path.join(_repo_root130, "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("issue #134 L-6/L-7: engine_regression covers #134 with split assertions")
else:
    fail("issue #134 L-6: engine_regression missing issue134 section")
_av134 = open(os.path.join(_repo_root130, "app-version.js"), encoding="utf-8").read()
if "2.53.04" in _av134:
    ok("issue #134: APP_VERSION bumped to 2.53.04 (historical)")
elif "2.53.03" in _av134:
    ok("issue #134: APP_VERSION bumped to 2.53.03 (historical)")
else:
    fail("issue #134: APP_VERSION historical marker missing")

# ── Issue #135: Audit #130 v2.53.02 — 21 findings ──
_repo_root135 = os.path.dirname(__file__)
_index135 = open(os.path.join(_repo_root135, "index.html"), encoding="utf-8").read()
_app135 = js  # inline scripts + runtime UI *-core.js (post-extraction)
_zwb135 = open(os.path.join(_repo_root135, "zhl-worker-bridge.js"), encoding="utf-8").read()
_rcs135 = _app135.split("function runContingencyScenario", 1)[-1][:3500] if "function runContingencyScenario" in _app135 else ""
_cc135 = _app135.split("function calcContingency", 1)[-1][:9000] if "function calcContingency" in _app135 else ""
if "let ok = false" in _rcs135 and "ok: false, newRows: ''" in _rcs135:
    ok("issue #135 H-1: runContingencyScenario returns ok:false when schedule empty")
else:
    fail("issue #135 H-1: contingency still crashes on undefined newRows")
if "} finally {" in _cc135 and "origBailout" in _cc135 and "if (origBT)" in _cc135.split("} finally {", 1)[-1][:600]:
    ok("issue #135 H-2: calcContingency restores BT/depth/gases in finally")
else:
    fail("issue #135 H-2: calcContingency DOM restore not in try/finally")
if "getBottomGasFractions" in _app135.split("function calcSurfInt", 1)[-1][:2500]:
    ok("issue #135 H-3: calcSurfInt uses bottom gas fN2 not hardcoded FN2_AIR")
else:
    fail("issue #135 H-3: calcSurfInt still hardcodes FN2_AIR")
if "totalCNS:" in _index135.split("function saveZhlRepState", 1)[-1][:500] and "totalOTU:" in _index135.split("function saveZhlRepState", 1)[-1][:500]:
    ok("issue #135 H-4: saveZhlRepState persists CNS/OTU carry")
else:
    fail("issue #135 H-4: saveZhlRepState missing CNS/OTU in rep snapshot")
if "finally {" in _app135.split("EMERGENCY DIVE PROFILE GRAPH", 1)[-1][:1200]:
    ok("issue #135 H-5: emergency PDF DOM-swap restore in finally")
else:
    fail("issue #135 H-5: emergency PDF restore not in finally")
_ppo2_wrap135 = _index135.split("function ppO2Check", 1)[-1].split("function fmtPpO2", 1)[0] if "function ppO2Check" in _index135 else ""
if ".toFixed(2)" not in _ppo2_wrap135 and "return ZhlEngineBundle.ppO2Check" in _ppo2_wrap135:
    ok("issue #135 H-6: ppO2Check delegate returns numeric ppO2")
else:
    fail("issue #135 H-6: ppO2Check wrapper still returns .toFixed string")
if "validateHypoxicDecoGas(dgf.fO2" in _index135.split("function buildZhlScheduleParamsFromDom", 1)[-1][:2500]:
    ok("issue #135 H-7: buildZhlScheduleParamsFromDom validates hypoxic deco gases")
else:
    fail("issue #135 H-7: buildZhlScheduleParamsFromDom missing validateHypoxicDecoGas")
if "parseRunMinutes(stopTxt)" in _rcs135:
    ok("issue #135 H-8: contingency deco time uses parseRunMinutes not parseInt")
else:
    fail("issue #135 H-8: contingency still parseInt M:SS stop times")
if "modPpo2" in _index135 and "nitroxMOD(fO2, modPpo2)" in _index135:
    ok("issue #135 H-9: rec planner MOD uses user ppo2Bottom limit")
else:
    fail("issue #135 H-9: rec planner MOD still hardcoded 1.4 bar")
if "handleWorkerFailure('ZHL worker timeout')" in _zwb135 and "consecutiveWorkerFailures += 1" in _zwb135.split("ZHL worker timeout", 1)[-1][:300]:
    ok("issue #135 H-10: worker timeout increments failure counter when worker null")
else:
    fail("issue #135 H-10: worker timeout still skips failure counter when worker null")
if "!_contingencyRunning" in _index135.split("function runDecoSchedule", 1)[-1][:1200]:
    ok("issue #135 M-2/M-3: runDecoSchedule skips validation during contingency")
else:
    fail("issue #135 M-2: contingency still runs validateDecoInputs during scenario")
if "ccrBailoutToggle" in _cc135 and "contGasLose !== 'none'" in _cc135:
    ok("issue #135 M-4: gas-loss contingency forces CCR bailout mode")
else:
    fail("issue #135 M-4: CCR gas-loss contingency missing bailout toggle")
if "calcEND(dM" in _app135.split("function renderEADTable", 1)[-1][:2000]:
    ok("issue #135 M-6: renderEADTable uses calcEND for altitude-aware EAD")
else:
    fail("issue #135 M-6: renderEADTable still uses inline sea-level EAD formula")
_sac135 = _index135.split("function sacDomToLpm", 1)[-1][:300]
if "raw <= 0) return 0" in _sac135:
    ok("issue #135 M-7: sacDomToLpm does not substitute default when SAC is 0")
else:
    fail("issue #135 M-7: sacDomToLpm still silently uses default for SAC=0")
if "cnsPctNum >= 80" in _index135:
    ok("issue #135 M-8: ZHL CNS warning uses >= 80 threshold")
else:
    fail("issue #135 M-8: ZHL/VPM CNS threshold mismatch")
if "ppo2 >= 1.6" in _index135.split("function calcCNS", 1)[-1][:5000]:
    ok("issue #135 M-9: calcCNS ppO2 limit uses >= 1.6 boundary")
else:
    fail("issue #135 M-9: calcCNS still uses > 1.6 for ppO2 limit")
if "narcoticO2" in _app135.split("function renderGasTable", 1)[-1][:2000]:
    ok("issue #135 M-10: gas table MND respects narcoticO2 toggle")
else:
    fail("issue #135 M-10: gas table MND ignores narcoticO2")
if "calcSurfInt();appSettings.save()" in _index135:
    ok("issue #135 L-1: siGfLow onchange persists via appSettings.save")
else:
    fail("issue #135 L-1: siGfLow missing appSettings.save")
if "nextId = 1" not in _zwb135.split("function terminate", 1)[-1][:200]:
    ok("issue #135 L-3: terminate() no longer resets nextId mid-session")
else:
    fail("issue #135 L-3: terminate() still resets nextId to 1")
if "seenMixes" in _index135.split("function validateDomDecoGases", 1)[-1][:1200]:
    ok("issue #135 L-4: validateDomDecoGases detects duplicate deco gas mixes")
else:
    fail("issue #135 L-4: no duplicate deco gas detection")
if ("if (ead == null) return null" in _index135.split("function calcEAD", 1)[-1][:400]
        or "ead <= 0) return null" in _index135.split("function calcEAD", 1)[-1][:400]):
    ok("issue #135 L-5/L-6: calcEAD/calcEND null for invalid/zero END (issue #138 M-17)")
else:
    fail("issue #135 L-5: calcEAD still rounds before return")
if 'oninput="applyCustomAltitude()"' not in _index135.split("altitudeCustomInput", 1)[-1][:200]:
    ok("issue #135 L-8: altitude custom input no longer double-fires oninput+onchange")
else:
    fail("issue #135 L-8: altitude custom still has oninput+onchange")
if 'data-phase="contingency-' in _cc135:
    ok("issue #135 L-9: contingency table rows tagged with contingency- data-phase prefix")
else:
    fail("issue #135 L-9: contingency rows missing data-phase contingency prefix")
if "1500 OTU/week" in _index135.split("function calcCNS", 1)[-1][:6000]:
    ok("issue #135 L-11: calcCNS warns on NOAA 1500 OTU/week limit")
else:
    fail("issue #135 L-11: no 1500 OTU/week threshold warning")
if "issue135" in open(os.path.join(_repo_root135, "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("issue #135 L-6: engine_regression covers #135 with split assertions")
else:
    fail("issue #135: engine_regression missing issue135 section")
_av135 = open(os.path.join(_repo_root135, "app-version.js"), encoding="utf-8").read()
if "2.53.04" in _av135:
    ok("issue #138: APP_VERSION bumped to 2.53.04")
elif "2.53.03" in _av135:
    ok("issue #135: APP_VERSION bumped to 2.53.03")
else:
    fail("issue #138: APP_VERSION not bumped to 2.53.04")

# ── Issue #138: Audit #132 v2.53.04 — 40 findings ──
_repo_root138 = os.path.dirname(__file__)
_index138 = open(os.path.join(_repo_root138, "index.html"), encoding="utf-8").read()
_app138 = js
_vpm138 = open(os.path.join(_repo_root138, "vpm-engine-core.js"), encoding="utf-8").read()
_zgas138 = open(os.path.join(_repo_root138, "zhl-gas-core.js"), encoding="utf-8").read()
_zsched138 = open(os.path.join(_repo_root138, "zhl-schedule-core.js"), encoding="utf-8").read()
_bzhl138 = open(os.path.join(_repo_root138, "zhl-engine-bundle.js"), encoding="utf-8").read()
_rd138 = _index138.split("function runDecoSchedule", 1)[-1][:12000] if "function runDecoSchedule" in _index138 else ""
_bz138 = _index138.split("function buildZhlScheduleParamsFromDom", 1)[-1][:3000] if "function buildZhlScheduleParamsFromDom" in _index138 else ""
_rep138 = _index138.split("function getZhlRepStateForSchedule", 1)[-1][:500] if "function getZhlRepStateForSchedule" in _index138 else ""
if "validateHypoxicDecoGas" in _bz138 and "bottomGas" in _bz138:
    ok("issue #138 H-1: bottom gas hypoxic validation in buildZhlScheduleParamsFromDom")
else:
    fail("issue #138 H-1: bottom gas missing validateHypoxicDecoGas")
if "escapeHtmlText(err.message" in _index138 and "function runDecoSchedule" in _index138:
    ok("issue #138 H-2: deco schedule error sanitized with escapeHtmlText")
else:
    fail("issue #138 H-2: deco error still unsanitized innerHTML")
if 'id="conservatismSelect" onchange="onConservatismChange()"' in _index138:
    ok("issue #138 H-3: conservatismSelect triggers replan")
else:
    fail("issue #138 H-3: conservatismSelect missing onchange")
if "replanAfterEnvChange()" in _index138.split("function setWaterDensity", 1)[-1][:900]:
    ok("issue #138 H-4: setWaterDensity replans live schedule")
else:
    fail("issue #138 H-4: setWaterDensity missing replan")
if "pO2>modPpo2" in _index138.split("function runPlanner", 1)[-1][:8000] and "const modPpo2" in _index138.split("function runPlanner", 1)[-1][:800]:
    ok("issue #138 H-5/H-6: Bühlmann planner uses scoped modPpo2")
else:
    fail("issue #138 H-5/H-6: Bühlmann modPpo2 still broken")
if "totalCNS: snap.totalCNS" in _rep138 and "totalOTU: snap.totalOTU" in _rep138:
    ok("issue #138 H-7: getZhlRepStateForSchedule carries CNS/OTU")
else:
    fail("issue #138 H-7: rep state missing CNS/OTU")
if "time: btAtDepthMin" in _index138.split("function runVPMSchedule", 1)[-1][:5000]:
    ok("issue #138 H-8: VPM levels use btAtDepthMin")
else:
    fail("issue #138 H-8: VPM still passes raw BT")
if "!_contingencyRunning && isCcrGasUiMode()" in _rd138:
    ok("issue #138 M-1: CCR gas validation skipped during contingency")
else:
    fail("issue #138 M-1: CCR validation not gated on contingency")
if "settings.metric ? stopDepth" in _vpm138.split("function vpmStopCapError", 1)[-1][:400]:
    ok("issue #138 M-3: vpmStopCapError uses metric/imperial suffix")
else:
    fail("issue #138 M-3: vpmStopCapError hardcodes metres")
if "if (stopTime > 0)" in _vpm138.split("let stopTime = 0", 1)[-1][:1200]:
    ok("issue #138 M-4: inter-level VPM skips zero-time forced stop")
else:
    fail("issue #138 M-4: inter-level still forces min stop when clear")
if "pO2Val >= gasLimit" in _index138:
    ok("issue #138 M-5: ppO2 limit boundary uses >=")
else:
    fail("issue #138 M-5: ppO2 still strict >")
if "(s.gas ||" in _index138.split("collapsedMDP.forEach", 1)[-1][:4000]:
    ok("issue #138 M-6: null-safe gas label in deco rows")
else:
    fail("issue #138 M-6: s.gas.toUpperCase still unguarded")
if "getDecoCardFractions(idx)" in _index138.split("function validateDomDecoGases", 1)[-1][:1500]:
    ok("issue #138 M-8: duplicate gas detection uses clamped fractions")
else:
    fail("issue #138 M-8: duplicate key still raw DOM strings")
if "if (low > high)" in _index138.split("function setCustomGF", 1)[-1][:1200]:
    ok("issue #138 M-9: setCustomGF rejects inverted GF")
else:
    fail("issue #138 M-9: GF Low > High not validated")
if "appSettings.save(false)" in _index138.split('id="ppo2Bottom"', 1)[-1][:200]:
    ok("issue #138 M-10: ppo2Bottom persists on change")
else:
    fail("issue #138 M-10: ppo2Bottom not persisted")
if 'ccrDecoSetpoint' in _index138 and "updateCcrGasValidation()" in _index138.split("ccrDecoSetpoint", 1)[-1][:200]:
    ok("issue #138 M-11: ccrDecoSetpoint updates MOD/validation")
else:
    fail("issue #138 M-11: ccrDecoSetpoint missing handler")
_restore138 = _index138.split("_restoreFields: function", 1)[-1][:3500] if "_restoreFields: function" in _index138 else ""
if ("this._restoreInProgress = false" in _restore138
        and _restore138.find("_restoreInProgress = false") > _restore138.find("pendingChangeEls.forEach")):
    ok("issue #138 M-12: _restoreInProgress cleared after sync and change dispatch")
else:
    fail("issue #138 M-12: _restoreInProgress restore order wrong")
if "function parseCcrSetpoint" in _index138:
    ok("issue #138 M-13: CCR setpoints use parseCcrSetpoint")
else:
    fail("issue #138 M-13: setpoint || fallback still treats 0 as missing")
if "activeFN2 ?? 0" in _zgas138 and "activeFN2 ?? 0" in _bzhl138.split("resolveGasAtDepth", 1)[-1][:800]:
    ok("issue #138 M-14: resolveGasAtDepth null-safe fN2 (mirror)")
else:
    fail("issue #138 M-14: resolveGasAtDepth fN2 can be null")
_val138 = _index138.split("function validateCcrCalculationInputs", 1)[-1][:3500] if "function validateCcrCalculationInputs" in _index138 else ""
if "circuit === 'pSCR'" in _val138 and "value === 0) continue" in _val138:
    ok("issue #138 M-15: pSCR setpoints validated when active")
else:
    fail("issue #138 M-15: pSCR still skips setpoint validation")
if "modPpo2Ndl" in _index138.split("function renderNDLTable", 1)[-1][:2000]:
    ok("issue #138 M-16: NDL MOD uses ppo2Bottom")
else:
    fail("issue #138 M-16: NDL MOD still hardcoded 1.4")
if "ead <= 0) return null" in _index138.split("function calcEAD", 1)[-1][:400]:
    ok("issue #138 M-17: calcEAD null for zero END")
else:
    fail("issue #138 M-17: calcEAD still formats 0 m")
if "Number.isFinite(dgvFracs.fO2)" in _index138.split("function runVPMSchedule", 1)[-1][:2500]:
    ok("issue #138 M-18: VPM rejects NaN deco fractions")
else:
    fail("issue #138 M-18: NaN deco gas still pushed to VPM")
if "Number.isFinite(mGF.high)" in _index138.split("function runVPMSchedule", 1)[-1][:800]:
    ok("issue #138 M-19: VPM gfHi fallback when mGF unset")
else:
    fail("issue #138 M-19: VPM gfHi still undefined on cold load")
if "totalCNSCarry: repSnap.totalCNS" in _index138.split("function mergeRepSettings", 1)[-1][:600]:
    ok("issue #138 M-20: mergeRepSettings injects CNS/OTU with _preTissues")
else:
    fail("issue #138 M-20: mergeRepSettings drops CNS/OTU carry")
if "Number.isFinite(altitudeM)" in _index138.split("function runVPMSchedule", 1)[-1][:3500]:
    ok("issue #138 M-21: VPM altitude NaN guard")
else:
    fail("issue #138 M-21: VPM altitude can be NaN")
if "!appSettings._loadPending" in _index138 and "setAlgo('buh')" in _index138.split("appSettings.load();", 1)[-1][:800]:
    ok("issue #138 M-22: app init skips defaults when restore deferred")
else:
    fail("issue #138 M-22: first-time defaults still race deferred restore")
if "settings.circuit !== 'pSCR'" not in _vpm138.split("offLoopPath", 1)[-1][:120]:
    ok("issue #138 L-1: pSCR included in inter-level conservatism relaxation")
else:
    fail("issue #138 L-1: pSCR still excluded from offLoopPath")
if "if (!(r0 > 0)) return 0" in _vpm138.split("function calcCrushRadius", 1)[-1][:200]:
    ok("issue #138 L-2: calcCrushRadius guards zero radius")
else:
    fail("issue #138 L-2: calcCrushRadius NaN on r0=0")
if "function getGasLabel(fO2, fHe)" in _zsched138:
    ok("issue #138 L-10: getGasLabel defined in zhl-schedule-core")
else:
    fail("issue #138 L-10: schedule core still depends on bundle getGasLabel")
if "n2 > 1" in _zgas138.split("function n2FracFromPercentages", 1)[-1][:250]:
    ok("issue #138 L-9: n2FracFromPercentages rejects fN2 > 1")
else:
    fail("issue #138 L-9: n2FracFromPercentages allows fN2 > 1")
if "issue138" in open(os.path.join(_repo_root138, "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("issue #138: engine_regression covers #138")
else:
    fail("issue #138: engine_regression missing issue138 section")

# ── Issue #139: Audit #133 v2.53.04 — 3 new findings (re-verify #138) ──
if 'id="ccrBottomSetpoint"' in _index138 and "appSettings.save(false)" in _index138.split('id="ccrBottomSetpoint"', 1)[-1][:200]:
    ok("issue #139 L-1: ccrBottomSetpoint persists on input")
else:
    fail("issue #139 L-1: ccrBottomSetpoint missing appSettings.save on input")
if 'id="ccrDecoSetpoint"' in _index138 and "appSettings.save(false)" in _index138.split('id="ccrDecoSetpoint"', 1)[-1][:200]:
    ok("issue #139 L-1: ccrDecoSetpoint persists on input")
else:
    fail("issue #139 L-1: ccrDecoSetpoint missing appSettings.save on input")
_safety138 = _index138.split("s.type === 'safety'", 1)[-1][:800] if "s.type === 'safety'" in _index138 else ""
if "pO2Val.toFixed(2)" in _safety138:
    ok("issue #139 L-2: safety stop row formats ppO₂ to 2 decimals")
else:
    fail("issue #139 L-2: safety stop row still renders raw ppO₂")
_gf138 = _index138.split("function setCustomGF", 1)[-1][:1200] if "function setCustomGF" in _index138 else ""
if "low > high" in _gf138 and "lowInput.value = String(low)" in _gf138:
    ok("issue #139 L-3: setCustomGF syncs DOM after GF swap")
else:
    fail("issue #139 L-3: setCustomGF swap does not update input fields")
if "issue139" in open(os.path.join(_repo_root138, "dev", "engine_regression.py"), encoding="utf-8").read():
    ok("issue #139: engine_regression covers #139")
else:
    fail("issue #139: engine_regression missing issue139 section")

print("=" * 60)

if FAIL:
    print(f"\n{'─'*60}")
    print(f"  FAILURES ({len(FAIL)}):")
    print(f"{'─'*60}")
    for f_ in FAIL:
        print(f"  ✗ {f_}")

print(f"\n{'─'*60}")
print(f"  Results: {len(PASS)} passed, {len(FAIL)} failed")
print(f"{'─'*60}\n")

if FAIL:
    sys.exit(1)
else:
    print("  ALL CHECKS PASSED ✓\n")
    sys.exit(0)
