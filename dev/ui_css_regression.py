#!/usr/bin/env python3
"""Seven-lens Cycle 05 UI-CSS behavioral regression (computed styles + keyboard focus)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
_DEV = ROOT / "dev"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from playwright_boot import boot_app_page  # noqa: E402
from test_http import serve_www  # noqa: E402
from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402

CASE_IDS = (
    "SL-C05-GF-ROW-MODE-ISOLATION",
    "SL-C05-EXPORT-FOCUS-VISIBLE",
    "SL-C05-CSS-DEAD-BRAND-ICON",
    "SL-C05-CSS-DEAD-GF-BTN",
    "SL-C05-CSS-DEAD-ALGO-SWITCHER",
    "SL-C05-CSS-DEAD-THEME-TOGGLE",
)

GF_JS = r"""
(mode) => {
  const read = () => {
    const btn = document.querySelector('#gfPresetBtns .gf-preset-btn');
    const row = document.getElementById('gfPresetsRowV3');
    const btnOp = btn ? parseFloat(getComputedStyle(btn).opacity) : null;
    const rowOp = row ? parseFloat(getComputedStyle(row).opacity) : null;
    return {
      btnOp,
      rowOp,
      rec: document.body.classList.contains('rec-mode'),
      tools: document.body.classList.contains('algo-tools'),
      hasBtn: !!btn,
    };
  };
  const snapNav = () => ({
    recActive: document.getElementById('navBtnRec')?.classList.contains('active'),
    buhActive: document.getElementById('navBtnBuh')?.classList.contains('active'),
    toolsActive: document.getElementById('navBtnTools')?.classList.contains('active'),
    navMode: typeof navMode !== 'undefined' ? navMode : null,
    plannerAlgo: typeof plannerAlgo !== 'undefined' ? plannerAlgo : null,
  });
  const prev = snapNav();
  try {
    _buildGfPresetBtns?.();
    if (mode === 'tools-rec-buh') {
      setMainNav('tools');
      const tools = read();
      setMainNav('rec');
      const rec = read();
      setMainNav('buh');
      const tec = read();
      return {
        order: mode,
        tecBtnOp: tec.btnOp,
        recBtnOp: rec.btnOp,
        toolsBtnOp: tools.btnOp,
        ok: tec.hasBtn
          && tec.btnOp >= 0.95
          && rec.btnOp <= 0.55
          && tools.btnOp <= 0.55
          && rec.rec
          && tools.tools
          && !tec.rec
          && !tec.tools,
      };
    }
    setMainNav('buh');
    const tec = read();
    setMainNav('rec');
    const rec = read();
    setMainNav('tools');
    const tools = read();
    return {
      order: mode,
      tecBtnOp: tec.btnOp,
      recBtnOp: rec.btnOp,
      toolsBtnOp: tools.btnOp,
      ok: tec.hasBtn
        && tec.btnOp >= 0.95
        && rec.btnOp <= 0.55
        && tools.btnOp <= 0.55
        && rec.rec
        && tools.tools
        && !tec.rec
        && !tec.tools,
    };
  } finally {
    if (prev.toolsActive) setMainNav('tools');
    else if (prev.recActive) setMainNav('rec');
    else setMainNav('buh');
    _buildGfPresetBtns?.();
  }
}
"""

DEAD_JS = r"""
async () => {
  const fetchText = async (href) => {
    try { return await (await fetch(href)).text(); }
    catch (_) { return ''; }
  };
  const foundation = await fetchText('lsp-dplanner-foundation.css');
  const modes = await fetchText('lsp-dplanner-modes.css');
  const logo = document.querySelector('.brand-logo');
  const logoWidth = logo ? parseFloat(getComputedStyle(logo).width) : 0;
  return {
    brandIconCount: document.querySelectorAll('.brand-icon').length,
    brandLogoCount: document.querySelectorAll('.brand-logo').length,
    gfBtnUnderCustom: document.querySelectorAll('#gfCustomRow .gf-btn').length,
    algoSwitcherCount: document.querySelectorAll('.algo-switcher').length,
    themeToggleCount: document.querySelectorAll('.theme-toggle').length,
    themePillCount: document.querySelectorAll('#themeToggle.theme-pill-toggle').length,
    logoWidth,
    hasBrandIconRule: /\.brand-icon\s*\{/.test(foundation),
    hasGfBtnRule: /#gfCustomRow\s+\.gf-btn/.test(foundation),
    hasAlgoSwitcherRule: /\.algo-switcher\s*\{/.test(foundation) || /\.algo-switcher\s*>/.test(modes),
    hasThemeToggleRule: /\.theme-toggle\s*\{/.test(modes),
    deadBrandOk: document.querySelectorAll('.brand-icon').length === 0
      && document.querySelectorAll('.brand-logo').length > 0
      && logoWidth > 0
      && !/\.brand-icon\s*\{/.test(foundation),
    deadGfBtnOk: document.querySelectorAll('#gfCustomRow .gf-btn').length === 0
      && !/#gfCustomRow\s+\.gf-btn/.test(foundation),
    deadAlgoSwitcherOk: document.querySelectorAll('.algo-switcher').length === 0
      && !/\.algo-switcher\s*\{/.test(foundation)
      && !/body\.algo-tools\s+\.algo-switcher/.test(modes),
    deadThemeToggleOk: document.querySelectorAll('.theme-toggle').length === 0
      && document.querySelectorAll('#themeToggle.theme-pill-toggle').length === 1
      && !/\.theme-toggle\s*\{/.test(modes),
  };
}
"""


def _focus_outline(page) -> dict:
    page.evaluate("() => { setMainNav('buh'); }")
    page.locator("body").click(position={"x": 8, "y": 8})
    handle = page.evaluate_handle(
        """() => {
          const nodes = Array.from(document.querySelectorAll('.btn-export'));
          return nodes.find(el => {
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none';
          }) || null;
        }"""
    )
    if handle.evaluate("el => el === null"):
        return {"tag": None, "cls": "", "outlineWidth": 0, "outlineStyle": "none", "matchesExport": False}
    handle.as_element().scroll_into_view_if_needed()
    for _ in range(80):
        page.keyboard.press("Tab")
        active = page.evaluate(
            """() => {
              const el = document.activeElement;
              if (!el) return { tag: null, cls: '', outlineWidth: 0, outlineStyle: 'none' };
              const cs = getComputedStyle(el);
              return {
                tag: el.tagName,
                cls: el.className || '',
                outlineWidth: parseFloat(cs.outlineWidth) || 0,
                outlineStyle: cs.outlineStyle,
                matchesExport: el.classList.contains('btn-export'),
              };
            }"""
        )
        if active.get("matchesExport"):
            return active
    return {"tag": None, "cls": "", "outlineWidth": 0, "outlineStyle": "none", "matchesExport": False}


def run_cases(page, viewport: tuple[int, int]) -> dict[str, bool]:
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    gf_a = page.evaluate(GF_JS, "buh-rec-tools")
    gf_b = page.evaluate(GF_JS, "tools-rec-buh")
    gf_ok = bool(gf_a.get("ok")) and bool(gf_b.get("ok"))

    focus = _focus_outline(page)
    focus_ok = bool(focus.get("matchesExport")) and float(focus.get("outlineWidth") or 0) >= 1.0
    focus_style = str(focus.get("outlineStyle") or "none")
    if focus_style == "none":
        focus_ok = False

    dead = page.evaluate(DEAD_JS)
    return {
        "SL-C05-GF-ROW-MODE-ISOLATION": gf_ok,
        "SL-C05-EXPORT-FOCUS-VISIBLE": focus_ok,
        "SL-C05-CSS-DEAD-BRAND-ICON": bool(dead.get("deadBrandOk")),
        "SL-C05-CSS-DEAD-GF-BTN": bool(dead.get("deadGfBtnOk")),
        "SL-C05-CSS-DEAD-ALGO-SWITCHER": bool(dead.get("deadAlgoSwitcherOk")),
        "SL-C05-CSS-DEAD-THEME-TOGGLE": bool(dead.get("deadThemeToggleOk")),
        "_detail": {"gf_a": gf_a, "gf_b": gf_b, "focus": focus, "dead": dead, "viewport": viewport},
    }


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Cycle 05 — UI-CSS computed-style regression")
    print("=" * 60)

    results: dict[str, bool] = {case_id: True for case_id in CASE_IDS}
    detail: dict = {}

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(120000)
            page.goto(f"{base_url}/index.html", wait_until="load")
            boot_app_page(page, base_url)

            for viewport in ((1280, 800), (375, 667)):
                page.goto(f"{base_url}/index.html", wait_until="load")
                boot_app_page(page, base_url)
                run = run_cases(page, viewport)
                detail[str(viewport)] = run.pop("_detail")
                for case_id in CASE_IDS:
                    results[case_id] = results[case_id] and bool(run.get(case_id))

            browser.close()

    rows = []
    for case_id in CASE_IDS:
        ok = results[case_id]
        print(f"  {'✓' if ok else '✗'} [{case_id}] {detail}")
        rows.append(case_row(case_id, ok))

    code = 0 if all(results.values()) else 1
    finish_suite(ROOT, rows, code)
    out = ROOT / "dev" / "ui_css_regression_results.json"
    out.write_text(json.dumps({"results": results, "detail": detail}, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
