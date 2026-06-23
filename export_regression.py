#!/usr/bin/env python3
"""
Export regression suite — PrT + depth unit conversions across export formats.
Runs headless via Playwright against a local index.html server.

Usage: python export_regression.py
Exit 0 = all pass, 1 = failures.
"""

import math
import re
import sys
import threading
import http.server
import socketserver
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent

PASS = []
FAIL = []


def ok(msg):
    PASS.append(msg)
    print(f"  ✓ {msg}")


def fail(msg):
    FAIL.append(msg)
    print(f"  ✗ {msg}")


def assert_near(actual, expected, tol, label):
    if actual is None or not math.isfinite(actual):
        fail(f"{label}: invalid value {actual!r} (expected ~{expected})")
        return False
    if abs(actual - expected) <= tol:
        ok(f"{label}: {actual:.1f} ≈ {expected:.1f}")
        return True
    fail(f"{label}: {actual:.1f} (expected ~{expected:.1f}, tol ±{tol})")
    return False


def prt_expected(depth_m, bt_min, bar_per_m=0.1):
    return depth_m * bar_per_m * math.sqrt(bt_min)


def extract_prt(text):
    m = re.search(r"PrT[:\s]+([\d.]+)", text, re.I)
    return float(m.group(1)) if m else None


def extract_prts(text):
    return [float(x) for x in re.findall(r"PrT[:\s]+([\d.]+)", text, re.I)]


def stamp_ok(text, label):
    if re.search(r"\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}", text):
        ok(f"{label}: stamp YYYY/MM/DD HH:MM")
        return True
    bad = re.search(r"\d{4}/(\d{2})/(\d{2})", text)
    if bad and int(bad.group(1)) > 12:
        fail(f"{label}: stamp looks YYYY/DD/MM ({bad.group(0)})")
    else:
        fail(f"{label}: no valid YYYY/MM/DD stamp found")
    return False


def line_has(pattern, text, label):
    if re.search(pattern, text, re.I | re.M):
        ok(label)
        return True
    fail(f"{label} — pattern not found: {pattern}")
    return False


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass


def start_server():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

        def log_message(self, fmt, *args):
            pass

    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, port


def run_tests(page, port):
    page.goto(f"http://127.0.0.1:{port}/index.html?regression=1", wait_until="domcontentloaded")
    page.wait_for_function(
        "window.VPMEngine && typeof window.VPMEngine.calculate === 'function' "
        "&& window.ZHLEngine && typeof window.ZHLEngine.calculate === 'function'",
        timeout=60000,
    )
    page.wait_for_timeout(2000)

    # ── A: Pure helper functions (metric + imperial) ─────────────────────
    print("\n── A: PrT helpers (domDepthToM / calcPrTBarMin) ──")

    for units, depth_dom, depth_m, bt in [
        ("metric", "40", 40, 30),
        ("imperial", "131", 40, 30),  # ~40 m in ft
    ]:
        exp = prt_expected(depth_m, bt)
        res = page.evaluate(
            """([units, depth, bt]) => {
                if (typeof setUnits === 'function') setUnits(units);
                document.getElementById('decoDepth').value = depth;
                document.getElementById('decoBT').value = String(bt);
                const dM = domDepthToM('decoDepth');
                const prt = calcPrTBarMin(dM, bt);
                return { dM, prt, units: window.units };
            }""",
            [units, depth_dom, bt],
        )
        assert_near(res["dM"], depth_m, 1.5, f"domDepthToM ({units}, DOM={depth_dom})")
        assert_near(res["prt"], exp, 0.5, f"calcPrTBarMin ({units})")

    # Wrong-path detector: raw ft × BAR without conversion would be ~3.28× too high
    wrong = page.evaluate(
        """() => {
            window.units = 'imperial';
            document.getElementById('decoDepth').value = '131';
            document.getElementById('decoBT').value = '30';
            const raw = parseFloat(document.getElementById('decoDepth').value);
            return raw * (window.BAR_PER_METRE || 0.1) * Math.sqrt(30);
        }"""
    )
    correct = prt_expected(40, 30)
    if wrong > correct * 2.5:
        ok(f"Imperial raw-ft bug path would give {wrong:.1f} (>{correct:.1f}×2.5) — conversion required")
    else:
        fail(f"Imperial raw-ft path unexpectedly small ({wrong:.1f}) — test setup issue")

    # ── B: buildDecoPlanHeaderData imperial display ────────────────────
    print("\n── B: Export header depth/rate unit display ──")

    hdr = page.evaluate(
        """() => {
            window.units = 'imperial';
            if (typeof setUnits === 'function') setUnits('imperial');
            document.getElementById('decoDepth').value = '131';
            document.getElementById('decoBT').value = '30';
            document.getElementById('descentRate').value = '20';
            document.getElementById('ascentRate').value = '10';
            document.getElementById('lastDecoStop').value = '3';
            document.getElementById('decoStep').value = '3';
            const d = buildDecoPlanHeaderData();
            return {
                du: d.du,
                depth: d.depth,
                descentRate: d.descentRate,
                lastStop: d.lastStop,
                altLabel: d.altLabel,
                lines: buildDecoPlanHeaderLines().join('\\n'),
            };
        }"""
    )
    if hdr["du"] == "ft":
        ok("buildDecoPlanHeaderData: du=ft in imperial")
    else:
        fail(f"buildDecoPlanHeaderData: du={hdr['du']!r} (expected ft)")

    dr = float(hdr["descentRate"])
    if 60 <= dr <= 70:
        ok(f"buildDecoPlanHeaderData: descentRate {dr} ft/min (metric 20 converted)")
    else:
        fail(f"buildDecoPlanHeaderData: descentRate {dr} (expected ~66 ft/min, not raw 20)")

    ls = float(hdr["lastStop"])
    if 8 <= ls <= 12:
        ok(f"buildDecoPlanHeaderData: lastStop {ls} ft (metric 3 converted)")
    else:
        fail(f"buildDecoPlanHeaderData: lastStop {ls} (expected ~10 ft)")

    if "ft" in hdr["altLabel"] or "Sea level" in hdr["altLabel"]:
        ok(f"buildDecoPlanHeaderData: altLabel uses ft ({hdr['altLabel']})")
    else:
        fail(f"buildDecoPlanHeaderData: altLabel missing ft ({hdr['altLabel']})")

    line_has(r"Descent\s+:\s+\d+ft/min", hdr["lines"], "buildDecoPlanHeaderLines: imperial rate suffix")

    # ── C: Standard deco plan + exports (metric) ─────────────────────────
    print("\n── C: Standard deco exports (metric, 40 m / 30 min, trimix + deco gases) ──")

    plan = page.evaluate(
        """async () => {
            if (typeof setUnits === 'function') setUnits('metric');
            window._zhlHeadless = false;
            window._lastContingency = null;
            document.getElementById('algorithmSelect').value = 'ZHLC_GF';
            document.getElementById('decoDepth').value = '40';
            document.getElementById('decoBT').value = '30';
            document.getElementById('decoGas').value = 'air';
            document.getElementById('dg1Mix').value = 'ean50';
            document.getElementById('dg2Mix').value = 'o2';
            runDecoSchedule();
            await new Promise(r => setTimeout(r, 800));
            const txt = buildExportText('deco');
            const msg = buildMessengerText('deco');
            const slate = typeof buildSlateText === 'function' ? buildSlateText() : '';
            const sum = getPlanSummaryExport();
            return { txt, msg, slate, sumPrt: sum.prt, hasTable: !!document.querySelector('#decoTableBody tr[data-phase="totals"]') };
        }"""
    )

    exp_prt = prt_expected(40, 30)
    if plan["hasTable"]:
        ok("Metric plan: totals row rendered")
    else:
        fail("Metric plan: no totals row after runDecoSchedule")

    try:
        sum_prt = float(plan["sumPrt"])
        assert_near(sum_prt, exp_prt, 1.0, "Metric planSum export PrT")
    except (TypeError, ValueError):
        fail(f"Metric planSum PrT: {plan['sumPrt']!r}")

    prt_vals = []
    for src, text in [("exportText", plan["txt"]), ("messenger", plan["msg"])]:
        if not text:
            fail(f"Metric {src}: empty output")
            continue
        p = extract_prt(text)
        if p is not None:
            prt_vals.append(p)
        else:
            fail(f"Metric {src}: PrT not found")
        stamp_ok(text, f"Metric {src}")

    for p in prt_vals:
        assert_near(p, exp_prt, 1.0, "Metric export PrT consistency")

    if plan["txt"] and "CNS / OTU / PrT" in plan["txt"] or re.search(r"CNS.*OTU.*PrT", plan["txt"]):
        ok("Metric exportText: 3-line summary block (CNS/OTU/PrT line)")
    elif plan["txt"]:
        # formatPlanSummaryBlock compact/non-compact
        prts = extract_prts(plan["txt"])
        if len(prts) >= 1:
            ok(f"Metric exportText: contains PrT ({len(prts)} occurrence(s))")
        else:
            fail("Metric exportText: summary block missing PrT")

    # ── D: Standard deco exports (imperial) ──────────────────────────────
    print("\n── D: Standard deco exports (imperial, ~131 ft / 30 min) ──")

    imp = page.evaluate(
        """async () => {
            window.units = 'imperial';
            if (typeof setUnits === 'function') setUnits('imperial');
            window._zhlHeadless = true;
            window._lastContingency = null;
            document.getElementById('decoDepth').value = '131';
            document.getElementById('decoBT').value = '30';
            document.getElementById('decoGas').value = 'air';
            runDecoSchedule();
            await new Promise(r => setTimeout(r, 500));
            const txt = buildExportText('deco');
            const msg = buildMessengerText('deco');
            const hdrLines = buildDecoPlanHeaderLines().join('\\n');
            const sum = getPlanSummaryExport();
            return { txt, msg, hdrLines, sumPrt: sum.prt };
        }"""
    )

    for src, text in [("exportText", imp["txt"]), ("messenger", imp["msg"])]:
        if not text:
            fail(f"Imperial {src}: empty")
            continue
        p = extract_prt(text)
        assert_near(p, exp_prt, 1.5, f"Imperial {src} PrT")
        if p and p > exp_prt * 2:
            fail(f"Imperial {src}: PrT {p} looks like unconverted ft depth bug")

    line_has(r"131ft|131 ft", imp["hdrLines"] + imp["txt"], "Imperial export: depth shown in ft")
    line_has(r"\d+ft/min", imp["hdrLines"], "Imperial export header: ft/min rates")

    # ── E: Contingency scenarios ─────────────────────────────────────────
    print("\n── E: Contingency PrT + exports ──")

    scenarios = [
        ("standard", {"contGasLose": "none", "contExtraBT": 0, "contExtraDepth": 0}, 40, 30),
        ("extra_bt_5", {"contGasLose": "none", "contExtraBT": 5, "contExtraDepth": 0}, 40, 30),
        ("lost_dg1", {"contGasLose": "1", "contExtraBT": 0, "contExtraDepth": 0}, 40, 30),
        ("extra_depth_3m", {"contGasLose": "none", "contExtraBT": 0, "contExtraDepth": 3}, 40, 30),
    ]

    for name, flags, depth_m, bt_min in scenarios:
        cont = page.evaluate(
            """async (args) => {
                const [flags, depthM, btMin] = args;
                if (typeof setUnits === 'function') setUnits('metric');
                window._zhlHeadless = false;
                window._massiveSuiteActive = false;
                document.getElementById('decoDepth').value = String(Math.round(depthM));
                document.getElementById('decoBT').value = String(btMin);
                document.getElementById('decoGas').value = 'air';
                document.getElementById('dg1Mix').value = 'ean50';
                document.getElementById('dg2Mix').value = 'o2';
                runDecoSchedule();
                await new Promise(r => setTimeout(r, 600));
                if (typeof selectContGas === 'function') selectContGas(flags.contGasLose);
                if (typeof selectContBT === 'function') selectContBT(flags.contExtraBT);
                if (typeof selectContDepth === 'function') selectContDepth(flags.contExtraDepth);
                calcContingency();
                await new Promise(r => setTimeout(r, 600));
                const c = window._lastContingency;
                const emTxt = buildExportText('contingency');
                const emMsg = buildMessengerText('contingency');
                const emSum = getContingencySummaryExport();
                const slate = typeof buildContingencySlateText === 'function' ? buildContingencySlateText() : '';
                return {
                    totalPrT: c && c.totalPrT,
                    emSumPrt: emSum.prt,
                    emTxt, emMsg, slate,
                    hasCont: !!c,
                    label: c && c.label,
                };
            }""",
            [flags, depth_m, bt_min],
        )

        exp = prt_expected(
            depth_m + flags.get("contExtraDepth", 0),
            bt_min + flags.get("contExtraBT", 0),
        )
        if not cont["hasCont"]:
            fail(f"Contingency [{name}]: _lastContingency not set")
            continue

        try:
            c_prt = float(cont["totalPrT"])
        except (TypeError, ValueError):
            c_prt = None
        assert_near(c_prt, exp, 1.5, f"Contingency [{name}] calcContingency totalPrT")

        for src, text in [
            ("summary", cont["emSumPrt"]),
            ("exportText", cont["emTxt"]),
            ("messenger", cont["emMsg"]),
            ("slate", cont["slate"]),
        ]:
            if src == "summary":
                try:
                    s_prt = float(cont["emSumPrt"])
                    assert_near(s_prt, exp, 1.5, f"Contingency [{name}] getContingencySummaryExport")
                except (TypeError, ValueError):
                    fail(f"Contingency [{name}] summary PrT: {cont['emSumPrt']!r}")
            elif text:
                p = extract_prt(text)
                assert_near(p, exp, 1.5, f"Contingency [{name}] {src} PrT")
                stamp_ok(text, f"Contingency [{name}] {src} stamp")
            elif src in ("exportText", "messenger"):
                fail(f"Contingency [{name}] {src}: empty")

    # ── F: Imperial contingency ──────────────────────────────────────────
    print("\n── F: Imperial contingency PrT ──")

    imp_cont = page.evaluate(
        """async () => {
            if (typeof setUnits === 'function') setUnits('imperial');
            window._massiveSuiteActive = false;
            document.getElementById('decoDepth').value = '131';
            document.getElementById('decoBT').value = '30';
            runDecoSchedule();
            await new Promise(r => setTimeout(r, 600));
            if (typeof selectContGas === 'function') selectContGas('none');
            if (typeof selectContBT === 'function') selectContBT(5);
            if (typeof selectContDepth === 'function') selectContDepth(0);
            calcContingency();
            await new Promise(r => setTimeout(r, 600));
            const c = window._lastContingency;
            const msg = buildMessengerText('contingency');
            const txt = buildExportText('contingency');
            return { totalPrT: c && c.totalPrT, msg, txt, label: c && c.label };
        }"""
    )
    exp_imp = prt_expected(40, 35)  # 131 ft ≈ 40 m, +5 min BT
    try:
        assert_near(float(imp_cont["totalPrT"]), exp_imp, 0.5, "Imperial contingency totalPrT")
    except (TypeError, ValueError):
        fail(f"Imperial contingency totalPrT: {imp_cont['totalPrT']!r}")
    for src, text in [("messenger", imp_cont["msg"]), ("exportText", imp_cont["txt"])]:
        if text:
            assert_near(extract_prt(text), exp_imp, 0.5, f"Imperial contingency {src} PrT")
    if imp_cont.get("label") and "+5" in imp_cont["label"]:
        ok("Imperial contingency: scenario label includes +5 min BT")
    else:
        fail(f"Imperial contingency: label missing +5 min BT ({imp_cont.get('label')!r})")

    # ── G: Trimix bottom gas export header ───────────────────────────────
    print("\n── G: Trimix gas settings in export header ──")

    tmx = page.evaluate(
        """async () => {
            window.units = 'metric';
            if (typeof setUnits === 'function') setUnits('metric');
            window._zhlHeadless = true;
            document.getElementById('decoGas').value = 'trimix';
            document.getElementById('botTrimixO2').value = '18';
            document.getElementById('botTrimixHe').value = '45';
            document.getElementById('decoDepth').value = '50';
            document.getElementById('decoBT').value = '25';
            runDecoSchedule();
            await new Promise(r => setTimeout(r, 400));
            const lines = buildDecoPlanHeaderLines().join('\\n');
            const txt = buildExportText('deco');
            return { lines, txt };
        }"""
    )
    if tmx["lines"] and re.search(r"18.*45|TMX|Trimix|18/45", tmx["lines"], re.I):
        ok("Trimix: bottom gas in header lines")
    else:
        fail("Trimix: bottom gas detail missing from header")
    if tmx["txt"] and "PrT" in tmx["txt"]:
        ok("Trimix: export text includes PrT")
    else:
        fail("Trimix: export text missing PrT")


def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("FATAL: playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    print("=" * 60)
    print("LSP D-Planner — Export Regression Suite")
    print("PrT · depth units · contingency · messenger · text export")
    print("=" * 60)

    httpd, port = start_server()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            run_tests(page, port)
        finally:
            browser.close()
            httpd.shutdown()

    print("\n" + "─" * 60)
    print(f"Results: {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("\nFailures:")
        for f in FAIL:
            print(f"  ✗ {f}")
        print("─" * 60)
        sys.exit(1)
    print("─" * 60)
    print("All export regression checks passed.")
    sys.exit(0)


if __name__ == "__main__":
    main()
