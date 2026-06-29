#!/usr/bin/env python3
"""Run in-browser regression suites over HTTP (post-sync www/ app shell)."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urljoin

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]

JS_RUN_SECTIONS = """
(pageName) => new Promise((resolve, reject) => {
  const iframe = document.getElementById('app-frame');
  if (!iframe) return reject(new Error('app-frame missing on ' + pageName));
  if (typeof SECTIONS === 'undefined') return reject(new Error('SECTIONS missing on ' + pageName));
  const wait = (typeof LSPTestHarness !== 'undefined' && LSPTestHarness.waitForApp)
    ? LSPTestHarness.waitForApp.bind(LSPTestHarness)
    : (frame, _t, cb) => {
        let bootErr = null;
        frame.addEventListener('load', () => {
          try {
            const w = frame.contentWindow;
            w.addEventListener('error', e => { bootErr = (e && e.message) || 'Script error'; });
          } catch (_) {}
        });
        const start = Date.now();
        const check = () => {
          try {
            const w = frame.contentWindow;
            if (w && w.VPMEngine && w.ZHLEngine && w.__lspAppFullyReady === true) {
              w._zhlHeadless = true;
              return cb(null, { win: w, version: w.APP_VERSION });
            }
            if (w && w.VPMEngine && w.ZHLEngine) {
              w._zhlHeadless = true;
            }
          } catch (_) {}
          if (bootErr) return cb(new Error('Boot: ' + bootErr));
          if (Date.now() - start > 180000) return cb(new Error('Timed out waiting for engines'));
          setTimeout(check, 300);
        };
        frame.src = 'index.html?regression=1&massiveSuite=1&ts=' + Date.now();
        setTimeout(check, 300);
      };
  wait(iframe, 180000, (err, ctx) => {
    if (err) return reject(err);
    WIN = ctx.win;
    const rows = [];
    for (const sec of SECTIONS) {
      for (const [name, fn] of sec.tests) {
        try {
          const detail = fn();
          rows.push({ section: sec.title, name, pass: true, warn: false, detail: detail || 'ok' });
        } catch (e) {
          if (e && e.isVerifyWarn) {
            rows.push({ section: sec.title, name, pass: true, warn: true, detail: e.message || String(e) });
          } else {
            rows.push({ section: sec.title, name, pass: false, warn: false, detail: e.message || String(e) });
          }
        }
      }
    }
    resolve({
      page: pageName,
      version: ctx.version || ctx.win?.APP_VERSION,
      pass: rows.filter(r => r.pass && !r.warn).length,
      warn: rows.filter(r => r.warn).length,
      fail: rows.filter(r => !r.pass).length,
      rows,
    });
  });
})
"""

JS_RUN_MASSIVE = """
() => {
  if (!window.runMassiveRegressionCI) throw new Error('runMassiveRegressionCI missing');
  return window.runMassiveRegressionCI({ skipTier1: true });
}
"""

JS_RUN_EXTENDED = """
() => {
  if (!window.runExtendedRegressionCI) throw new Error('runExtendedRegressionCI missing');
  return window.runExtendedRegressionCI();
}
"""

SUITE_SPECS = [
    ("tests-verify.html", JS_RUN_SECTIONS, 240000, True),
    ("tests-pscr-otu-cns.html", JS_RUN_SECTIONS, 240000, True),
    ("tests-extended.html?ci=1", JS_RUN_EXTENDED, 300000, False),
    ("tests-massive.html?ci=1", JS_RUN_MASSIVE, 900000, False),
]


def run_suite(page, base_url: str, html_name: str, eval_js: str) -> dict:
    url = urljoin(base_url, html_name)
    page.goto(url, wait_until="domcontentloaded", timeout=180000)
    if eval_js is JS_RUN_SECTIONS:
        return page.evaluate(eval_js, html_name.split("?")[0])
    return page.evaluate(eval_js)


def main() -> int:
    from playwright.sync_api import sync_playwright

    sys.path.insert(0, str(ROOT / "dev"))
    from test_http import serve_www  # noqa: E402

    results = []

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            for name, eval_js, timeout_ms, strict_warn in SUITE_SPECS:
                page.set_default_timeout(timeout_ms)
                print(f"Running {name} …")
                result = run_suite(page, base_url, name, eval_js)
                result["strictWarn"] = strict_warn
                results.append(result)
            browser.close()

    out = ROOT / "dev" / "browser_regression_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Wrote {out}")

    total_fail = 0
    total_warn = 0
    for suite in results:
        fail = suite.get("fail", 0)
        warn = suite.get("warn", 0)
        total_fail += fail
        if suite.get("strictWarn", True):
            total_warn += warn
        status = "FAIL" if fail else ("WARN" if warn else "PASS")
        print(
            f"  {suite.get('page')}: {status} — "
            f"{suite.get('pass', 0)} pass, {warn} warn, {fail} fail"
        )
        if fail:
            for row in suite.get("rows", []):
                if not row.get("pass"):
                    print(f"    FAIL {row.get('name')}: {row.get('detail')}")

    if total_fail:
        print(f"\nBrowser regression: {total_fail} failure(s)")
        return 1
    if total_warn:
        print(f"\nBrowser regression: {total_warn} warning(s) treated as failures")
        return 1
    print("\nBrowser regression: all suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
