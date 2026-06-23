#!/usr/bin/env python3
"""Run in-browser regression suites (tests-verify + tests-pscr-otu-cns) over HTTP."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[1]

JS_RUN_SUITE = """
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
            if (w && w.VPMEngine && w.ZHLEngine) {
              w._zhlHeadless = true;
              return setTimeout(() => cb(null, { win: w, version: w.APP_VERSION }), 1500);
            }
          } catch (_) {}
          if (bootErr) return cb(new Error('Boot: ' + bootErr));
          if (Date.now() - start > 180000) return cb(new Error('Timed out waiting for engines'));
          setTimeout(check, 300);
        };
        frame.src = 'index.html?massiveSuite=1&ts=' + Date.now();
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


def run_suite(page, base_url: str, html_name: str) -> dict:
    url = urljoin(base_url, html_name)
    page.goto(url, wait_until="domcontentloaded", timeout=180000)
    return page.evaluate(JS_RUN_SUITE, html_name)


def main() -> int:
    from playwright.sync_api import sync_playwright

    sys.path.insert(0, str(ROOT / "dev"))
    from validate_pscr_e2e import serve_root  # noqa: E402

    suites = [
        "tests-verify.html",
        "tests-pscr-otu-cns.html",
    ]
    results = []

    with serve_root(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(240000)
            for name in suites:
                print(f"Running {name} …")
                results.append(run_suite(page, base_url, name))
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
        total_warn += warn
        status = "FAIL" if fail else ("WARN" if warn else "PASS")
        print(
            f"  {suite.get('page')}: {status} — "
            f"{suite.get('pass', 0)} pass, {warn} warn, {fail} fail"
        )
        if fail:
            for row in suite.get("rows", []):
                if not row.get("pass"):
                    print(f"    ✗ {row.get('name')}: {row.get('detail')}")

    if total_fail:
        print(f"\nBrowser regression: {total_fail} failure(s)")
        return 1
    print(f"\nBrowser regression: all suites passed ({total_warn} warning(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
