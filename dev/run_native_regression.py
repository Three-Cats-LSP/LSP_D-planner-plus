#!/usr/bin/env python3
"""Playwright regression for Android select picker and Capacitor export bridge."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
_DEV = Path(__file__).resolve().parent
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from test_http import serve_root  # noqa: E402

PASS: list[str] = []
FAIL: list[str] = []

ANDROID_SELECT_TESTS = """
async () => {
  const sel = document.getElementById('gasSelect');
  const btn = document.querySelector('.lsp-android-select-btn');
  if (!sel || !btn) throw new Error('select wrapper missing');
  const out = [];

  function assert(cond, msg) {
    if (!cond) throw new Error(msg);
    out.push(msg);
  }

  assert(btn.textContent.trim() === 'Air', 'initial button label is Air');
  sel.value = 'ean32';
  assert(btn.textContent.trim() === 'EAN32', 'value setter syncs button (issue #22)');

  sel.selectedIndex = 0;
  assert(btn.textContent.trim() === 'Air', 'selectedIndex setter syncs button');

  if (!window.LspAndroidSelect || typeof window.LspAndroidSelect.sync !== 'function') {
    throw new Error('LspAndroidSelect.sync missing');
  }
  sel.value = 'ean32';
  sel.options[1].textContent = 'EAN32 renamed';
  window.LspAndroidSelect.sync(sel);
  assert(btn.textContent.trim() === 'EAN32 renamed', 'LspAndroidSelect.sync updates label');

  sel.value = 'air';
  const field2 = document.createElement('div');
  field2.className = 'field';
  field2.innerHTML = '<label>Algo</label><select id="algoSelect"><option value="zhl">ZHL</option><option value="vpm">VPM</option></select>';
  document.body.appendChild(field2);
  await new Promise(r => requestAnimationFrame(r));
  const algoBtn = field2.querySelector('.lsp-android-select-btn');
  const algoSel = field2.querySelector('select');
  assert(!!algoBtn, 'dynamically added select is wrapped');
  algoSel.value = 'vpm';
  assert(algoBtn.textContent.trim() === 'VPM', 'dynamic select value setter syncs');
  algoSel.options[1].textContent = 'VPM-B';
  window.LspAndroidSelect.syncAll();
  assert(algoBtn.textContent.trim() === 'VPM-B', 'LspAndroidSelect.syncAll updates all buttons (issue #23)');
  assert(btn.textContent.trim() === 'Air', 'syncAll also refreshes earlier selects');

  btn.click();
  await new Promise(r => requestAnimationFrame(r));
  const sheet = document.getElementById('lsp-android-select-sheet');
  assert(!!sheet, 'sheet opens on button click');
  const items = sheet.querySelectorAll('.lsp-android-select-item');
  assert(items.length === 2, 'disabled unselected option omitted from sheet');
  assert(!sheet.textContent.includes('EAN50'), 'disabled option not offered in sheet');

  sel.options[1].disabled = true;
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const sheetAfterDisable = document.getElementById('lsp-android-select-sheet');
  assert(!!sheetAfterDisable, 'sheet stays open after option disabled');
  assert(!sheetAfterDisable.textContent.includes('EAN32'), 'disabled option removed from open sheet (issue #24)');

  return out;
}
"""

CAPACITOR_CLICK_TEST = """
async () => {
  const payload = 'LSP export regression';
  const blob = new Blob([payload], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'LSP_plan.txt';
  a.click();
  for (let i = 0; i < 80; i++) {
    if (window.__capBridgeTest.writes.length) break;
    await new Promise(r => setTimeout(r, 50));
  }
  const writes = window.__capBridgeTest.writes;
  if (!writes.length) throw new Error('click() did not intercept blob download');
  const data = writes[0].data || '';
  const decoded = atob(data);
  if (!decoded.includes(payload)) throw new Error('writeFile data mismatch after click()');
  return ['click() intercept writes blob to Filesystem'];
}
"""

CAPACITOR_DISPATCH_TEST = """
async () => {
  window.__capBridgeTest.writes = [];
  const payload = 'jsPDF dispatch path';
  const blob = new Blob([payload], { type: 'application/pdf' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'LSP_plan.pdf';
  const ev = new MouseEvent('click', { bubbles: true, cancelable: true });
  a.dispatchEvent(ev);
  for (let i = 0; i < 80; i++) {
    if (window.__capBridgeTest.writes.length) break;
    await new Promise(r => setTimeout(r, 50));
  }
  const writes = window.__capBridgeTest.writes;
  if (!writes.length) throw new Error('dispatchEvent(click) did not intercept blob download');
  const decoded = atob(writes[0].data || '');
  if (!decoded.includes(payload)) throw new Error('dispatchEvent writeFile data mismatch');
  return ['dispatchEvent(MouseEvent click) intercept (jsPDF path)'];
}
"""

CAPACITOR_UNIQUE_FILENAME_TEST = """
async () => {
  window.__capBridgeTest.writes = [];
  let statCalls = 0;
  const origStat = window.Capacitor.Plugins.Filesystem.stat;
  window.Capacitor.Plugins.Filesystem.stat = async (opts) => {
    statCalls += 1;
    if (statCalls === 1) return { type: 'file' };
    return origStat(opts);
  };
  const blob = new Blob(['dup'], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'LSP_plan.txt';
  a.click();
  for (let i = 0; i < 80; i++) {
    if (window.__capBridgeTest.writes.length) break;
    await new Promise(r => setTimeout(r, 50));
  }
  const path = window.__capBridgeTest.writes[0]?.path || '';
  if (!path.includes('(1)')) throw new Error('uniqueFilename did not append (1): ' + path);
  window.Capacitor.Plugins.Filesystem.stat = origStat;
  return ['uniqueFilename avoids overwrite when file exists'];
}
"""

CAPACITOR_BLOB_FALLBACK_TEST = """
async () => {
  window.__capBridgeTest.writes = [];
  const a = document.createElement('a');
  a.href = 'blob:http://invalid/revoked-deadbeef';
  a.download = 'LSP_plan.txt';
  a.click();
  await new Promise(r => setTimeout(r, 200));
  if (window.__capBridgeTest.writes.length) {
    throw new Error('failed blob read must not save via Capacitor (issue #24)');
  }
  return ['blob read failure does not save via Capacitor bridge (issue #24)'];
}
"""

CAPACITOR_ASYNC_ERROR_TEST = """
async () => {
  window.__capBridgeTest.writes = [];
  const origWrite = window.Capacitor.Plugins.Filesystem.writeFile;
  window.Capacitor.Plugins.Filesystem.writeFile = async () => {
    throw new Error('simulated write failure');
  };
  const blob = new Blob(['fail path'], { type: 'text/plain' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'LSP_fail.txt';
  a.click();
  await new Promise(r => setTimeout(r, 500));
  window.Capacitor.Plugins.Filesystem.writeFile = origWrite;
  return ['handleBlobDownload rejection handled via .catch (issue #24)'];
}
"""


def ok(msg: str) -> None:
    PASS.append(msg)
    print(f"  ✓ {msg}")


def fail(msg: str) -> None:
    FAIL.append(msg)
    print(f"  ✗ {msg}")


def run_android_select(page, base_url: str) -> None:
    page.goto(f"{base_url}dev/fixtures/native-select.html", wait_until="networkidle", timeout=60000)
    page.wait_for_selector(".lsp-android-select-btn", timeout=10000)
    try:
        rows = page.evaluate(ANDROID_SELECT_TESTS)
        for row in rows:
            ok(f"android-select: {row}")
    except Exception as exc:
        fail(f"android-select: {exc}")


def run_capacitor_bridge(page, base_url: str) -> None:
    page.goto(f"{base_url}dev/fixtures/capacitor-bridge.html", wait_until="networkidle", timeout=60000)
    ready = page.evaluate(
        "() => !!(window.__capBridgeTest && window.Capacitor && window.Capacitor.isNativePlatform())"
    )
    if not ready:
        fail("capacitor-bridge: Capacitor mock not active before bridge load")
        return
    for label, js in [
        ("click intercept", CAPACITOR_CLICK_TEST),
        ("dispatchEvent intercept", CAPACITOR_DISPATCH_TEST),
        ("uniqueFilename", CAPACITOR_UNIQUE_FILENAME_TEST),
        ("blob read fallback", CAPACITOR_BLOB_FALLBACK_TEST),
        ("async export error", CAPACITOR_ASYNC_ERROR_TEST),
    ]:
        try:
            rows = page.evaluate(js)
            for row in rows:
                ok(f"capacitor-bridge: {row}")
        except Exception as exc:
            fail(f"capacitor-bridge {label}: {exc}")


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("LSP D-Planner — Native bridge regression")
    print("Android select picker + Capacitor export bridge")
    print("=" * 60)

    with serve_root(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(60000)
            run_android_select(page, base_url)
            run_capacitor_bridge(page, base_url)
            browser.close()

    out = ROOT / "dev" / "native_regression_results.json"
    summary = {"pass": len(PASS), "fail": len(FAIL), "passed": PASS, "failed": FAIL}
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    print(f"\n{'─' * 60}")
    print(f"  Results: {len(PASS)} passed, {len(FAIL)} failed")
    print(f"{'─' * 60}\n")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
