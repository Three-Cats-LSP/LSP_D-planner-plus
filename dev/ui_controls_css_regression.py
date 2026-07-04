#!/usr/bin/env python3
"""Seven-lens Cycle 06 UI-CSS-CONTROLS behavioral regression (computed styles + geometry)."""
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
    "SL-C06-SEG-FOCUS-VISIBLE",
    "SL-C06-GAS-NUM-TOUCH-TARGET",
    "SL-C06-CSS-DEAD-SI-INNER",
    "SL-C06-CSS-DEAD-T-COL",
    "SL-C06-CSS-DEAD-BTN-CALC",
    "SL-C06-FIELD-INVALID-STATE",
    "SL-C06-REDUCED-MOTION",
)

STATE_HASH_JS = r"""
() => {
  const parts = [];
  parts.push(document.body.className);
  parts.push(typeof navMode !== 'undefined' ? navMode : '');
  parts.push(document.activeElement?.id || '');
  for (const id of ['cylBot_size', 'cylBot_pres']) {
    const el = document.getElementById(id);
    parts.push(el ? `${el.value}|${el.disabled}|${el.validity?.valid}` : 'missing');
  }
  parts.push(document.querySelectorAll('.si-inner').length);
  parts.push(document.querySelectorAll('.btn-calc').length);
  return parts.join('::');
}
"""

DEAD_JS = r"""
async () => {
  const fetchText = async (href) => {
    try { return await (await fetch(href)).text(); }
    catch (_) { return ''; }
  };
  const controls = await fetchText('lsp-dplanner-controls.css');
  return {
    siInnerCount: document.querySelectorAll('.si-inner').length,
    tColCount: document.querySelectorAll('.t-col').length,
    btnCalcCount: document.querySelectorAll('.btn-calc').length,
    genBtnCount: document.querySelectorAll('.gen-btn').length,
    hasSiInnerRule: /\.si-inner\s*\{/.test(controls),
    hasTColRule: /\.t-col\s*\{/.test(controls),
    hasBtnCalcRule: /\.btn-calc\s*\{/.test(controls) || /\.gen-btn,\s*\.btn-calc/.test(controls),
    deadSiInnerOk: document.querySelectorAll('.si-inner').length === 0 && !/\.si-inner\s*\{/.test(controls),
    deadTColOk: document.querySelectorAll('.t-col').length === 0 && !/\.t-col\s*\{/.test(controls),
    deadBtnCalcOk: !/\.btn-calc\s*\{/.test(controls) && !/\.gen-btn,\s*\.btn-calc/.test(controls)
      && document.querySelectorAll('.gen-btn').length > 0,
  };
}
"""

TOUCH_JS = r"""
(order) => {
  const snap = () => ({
    buh: document.getElementById('navBtnBuh')?.classList.contains('active'),
    planner: document.getElementById('tab-planner')?.classList.contains('active'),
  });
  const prev = snap();
  try {
    setMainNav('buh');
    switchTab('planner', document.getElementById('tab-planner'));
    const sizeEl = document.getElementById('cylBot_size');
    const presEl = document.getElementById('cylBot_pres');
    if (!sizeEl || !presEl) return { order, ok: false, missing: true };
    const sizeBox = sizeEl.getBoundingClientRect();
    const presBox = presEl.getBoundingClientRect();
    const overlap = !(sizeBox.right <= presBox.left || presBox.right <= sizeBox.left
      || sizeBox.bottom <= presBox.top || presBox.bottom <= sizeBox.top);
    return {
      order,
      sizeW: sizeBox.width,
      sizeH: sizeBox.height,
      presW: presBox.width,
      presH: presBox.height,
      overlap,
      ok: sizeBox.width >= 44 && sizeBox.height >= 44 && presBox.width >= 44 && presBox.height >= 44 && !overlap,
    };
  } finally {
    if (prev.buh) setMainNav('buh');
    if (prev.planner) switchTab('planner', document.getElementById('tab-planner'));
    else switchTab('deco', document.getElementById('tab-deco'));
  }
}
"""

REDUCED_JS = r"""
() => {
  const read = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    return { transitionDuration: cs.transitionDuration };
  };
  const seg = read('.seg-btn');
  const thumb = read('.option-pill-thumb');
  const input = read('.field input');
  const zeroed = (row) => row && (row.transitionDuration === '0s' || row.transitionDuration.startsWith('0s'));
  return { seg, thumb, input, ok: zeroed(seg) && zeroed(thumb) && zeroed(input) };
}
"""

READ_FIELD_STYLES_JS = r"""
node => {
  const cs = getComputedStyle(node);
  return {
    borderColor: cs.borderColor,
    boxShadow: cs.boxShadow,
    outlineStyle: cs.outlineStyle,
    outlineWidth: cs.outlineWidth,
  };
}
"""


def _styles_differ(left: dict | None, right: dict | None) -> bool:
    if not left or not right:
        return False
    return left.get("borderColor") != right.get("borderColor") or left.get("boxShadow") != right.get("boxShadow")


def _css_color(page, value: str) -> str:
    return page.evaluate(
        """value => {
          const probe = document.createElement('span');
          probe.style.color = value;
          document.body.appendChild(probe);
          const color = getComputedStyle(probe).color;
          probe.remove();
          return color;
        }""",
        value,
    )


def _keyboard_seg_focus(page, *, gas_rule: bool) -> dict:
    if gas_rule:
        page.evaluate(
            """() => {
              setMainNav('buh');
              const legacy = document.querySelector('.legacy-panels');
              if (legacy) legacy.style.setProperty('display', 'block', 'important');
              const gp = document.getElementById('gasplan');
              if (gp) gp.style.display = '';
              switchTab('gasplan');
            }"""
        )
        targets = {"gpRuleHalf", "gpRuleThirds"}
        restore = """() => {
          switchTab('deco', document.getElementById('tab-deco'));
          const gp = document.getElementById('gasplan');
          if (gp) gp.style.display = 'none';
          const legacy = document.querySelector('.legacy-panels');
          if (legacy) legacy.style.removeProperty('display');
        }"""
    else:
        page.evaluate(
            """() => {
              setMainNav('rec');
              const btn = document.querySelector("#recResultTabs [data-tab='multi']");
              if (btn) switchResultTab('multi', btn);
            }"""
        )
        targets = {"dc2", "dc3", "dc4"}
        restore = """() => {
          setMainNav('buh');
          switchTab('deco', document.getElementById('tab-deco'));
        }"""
    page.locator("body").click(position={"x": 8, "y": 8})
    found: dict[str, dict] = {}
    for _ in range(200):
        page.keyboard.press("Tab")
        active = page.evaluate(
            """() => {
              const el = document.activeElement;
              if (!el || !el.classList.contains('seg-btn')) return null;
              const cs = getComputedStyle(el);
              return {
                id: el.id,
                active: el.classList.contains('active'),
                outlineWidth: parseFloat(cs.outlineWidth) || 0,
                outlineStyle: cs.outlineStyle,
              };
            }"""
        )
        if active and active.get("id") in targets:
            ow = float(active.get("outlineWidth") or 0)
            os = str(active.get("outlineStyle") or "none")
            active["ok"] = ow >= 1.0 and os == "solid"
            found[active["id"]] = active
    page.evaluate(restore)
    if gas_rule:
        want = ("gpRuleHalf", "gpRuleThirds")
    else:
        want = ("dc2", "dc3")
    rows = [found.get(i) for i in want]
    return {"found": found, "rows": rows, "ok": all(row and row.get("ok") for row in rows), "gas_rule": gas_rule}


def _invalid_field(page, *, viewport: tuple[int, int], browser_version: str) -> dict:
    page.evaluate(
        """() => {
          setMainNav('buh');
          switchTab('planner', document.getElementById('tab-planner'));
        }"""
    )
    el = page.locator("#cylBot_size")
    if el.count() == 0:
        return {
            "ok": False,
            "missing": True,
            "viewport": list(viewport),
            "browserVersion": browser_version,
        }

    snap = el.evaluate(
        """node => ({
          value: node.value,
          disabled: node.disabled,
          min: node.min,
          max: node.max,
          step: node.step,
          valid: node.validity.valid,
          validationMessage: node.validationMessage,
        })"""
    )
    selector_matches = page.evaluate(
        """() => ({
          fieldInputCount: document.querySelectorAll('.field input').length,
          targetPresent: !!document.getElementById('cylBot_size'),
          targetInField: !!document.querySelector('.field input#cylBot_size'),
        })"""
    )
    before_styles = el.evaluate(READ_FIELD_STYLES_JS)
    pristine_valid = bool(snap.get("valid"))

    try:
        el.click()
        el.select_text()
        el.fill("0")
        el.evaluate("node => node.dispatchEvent(new Event('input', { bubbles: true }))")
        page.locator("#cylBot_pres").click()

        after_valid = el.evaluate("node => node.validity.valid")
        after_invalid = not after_valid
        invalid_styles = el.evaluate(READ_FIELD_STYLES_JS)

        el.click()
        focused = el.evaluate("node => document.activeElement === node")
        focus_styles = el.evaluate(READ_FIELD_STYLES_JS)

        el.evaluate("node => { node.disabled = true; }")
        disabled = el.evaluate("node => node.disabled")
        disabled_styles = el.evaluate(READ_FIELD_STYLES_JS)
    finally:
        page.evaluate(
            """(snap) => {
              const node = document.getElementById('cylBot_size');
              if (!node) return;
              node.disabled = false;
              node.value = snap.value;
              if (typeof syncVolumeInputCanonical === 'function') {
                syncVolumeInputCanonical('cylBot_size');
              }
              node.dispatchEvent(new Event('input', { bubbles: true }));
              node.dispatchEvent(new Event('change', { bubbles: true }));
              node.blur();
            }""",
            snap,
        )
        page.locator("body").click(position={"x": 8, "y": 8})
        page.evaluate("() => { switchTab('deco', document.getElementById('tab-deco')); }")

    invalid_visual = _styles_differ(before_styles, invalid_styles)
    expected_invalid_border = _css_color(page, "var(--red)")
    invalid_border_is_red = invalid_styles.get("borderColor") == expected_invalid_border
    invalid_shadow_visible = invalid_styles.get("boxShadow") not in {"none", ""}
    focus_differs = _styles_differ(invalid_styles, focus_styles)
    disabled_differs = _styles_differ(invalid_styles, disabled_styles)
    ok = (
        pristine_valid
        and after_invalid
        and invalid_visual
        and invalid_border_is_red
        and invalid_shadow_visible
        and focus_differs
        and disabled_differs
        and focused
        and disabled
    )
    return {
        "ok": ok,
        "viewport": list(viewport),
        "browserVersion": browser_version,
        "pristineValid": pristine_valid,
        "pristineInvalid": not pristine_valid,
        "afterValid": after_valid,
        "afterInvalid": after_invalid,
        "selectorMatches": selector_matches,
        "values": {
            "snapshotValue": snap.get("value"),
            "editedValue": "0",
            "min": snap.get("min"),
            "max": snap.get("max"),
            "step": snap.get("step"),
        },
        "validity": {
            "pristineValid": pristine_valid,
            "afterValid": after_valid,
            "validationMessage": snap.get("validationMessage"),
        },
        "borderColors": {
            "before": before_styles.get("borderColor"),
            "invalid": invalid_styles.get("borderColor"),
            "expectedInvalid": expected_invalid_border,
            "focus": focus_styles.get("borderColor"),
            "disabled": disabled_styles.get("borderColor"),
        },
        "boxShadows": {
            "before": before_styles.get("boxShadow"),
            "invalid": invalid_styles.get("boxShadow"),
            "focus": focus_styles.get("boxShadow"),
            "disabled": disabled_styles.get("boxShadow"),
        },
        "focusState": {
            "focused": focused,
            "outlineStyle": focus_styles.get("outlineStyle"),
            "outlineWidth": focus_styles.get("outlineWidth"),
        },
        "disabledState": {
            "disabled": disabled,
        },
        "checks": {
            "invalidVisual": invalid_visual,
            "invalidBorderIsRed": invalid_border_is_red,
            "invalidShadowVisible": invalid_shadow_visible,
            "focusDiffers": focus_differs,
            "disabledDiffers": disabled_differs,
        },
    }


def run_cases(
    page,
    viewport: tuple[int, int],
    *,
    mobile_touch: bool = False,
    seg_focus: bool = False,
    browser_version: str = "",
) -> dict:
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    page.evaluate(
        """() => {
          setMainNav('buh');
          switchTab('deco', document.getElementById('tab-deco'));
          const gp = document.getElementById('gasplan');
          if (gp) gp.style.display = 'none';
          const legacy = document.querySelector('.legacy-panels');
          if (legacy) legacy.style.removeProperty('display');
        }"""
    )
    page.locator("body").click(position={"x": 8, "y": 8})
    before_hash = page.evaluate(STATE_HASH_JS)
    active_before = page.evaluate("() => document.activeElement?.id || ''")
    seg_orders: list = []
    seg_ok = True
    touch_orders: list = []
    touch_ok = True
    dead = {}
    invalid = {}
    reduced = {}
    try:
        if seg_focus:
            for gas_rule in (False, True):
                run = _keyboard_seg_focus(page, gas_rule=gas_rule)
                seg_orders.append(run)
                seg_ok = seg_ok and bool(run.get("ok"))

        if mobile_touch:
            for label, vp in (("portrait", viewport), ("landscape", (667, 375))):
                page.set_viewport_size({"width": vp[0], "height": vp[1]})
                row = page.evaluate(TOUCH_JS, label)
                touch_orders.append(row)
                touch_ok = touch_ok and bool(row.get("ok"))
            page.set_viewport_size({"width": viewport[0], "height": viewport[1]})

        dead = page.evaluate(DEAD_JS)
        invalid = _invalid_field(page, viewport=viewport, browser_version=browser_version)
        page.emulate_media(reduced_motion="reduce")
        reduced = page.evaluate(REDUCED_JS)
        page.emulate_media(reduced_motion="no-preference")
    finally:
        page.evaluate(
            """(activeId) => {
              setMainNav('buh');
              switchTab('deco', document.getElementById('tab-deco'));
              const gp = document.getElementById('gasplan');
              if (gp) gp.style.display = 'none';
              const legacy = document.querySelector('.legacy-panels');
              if (legacy) legacy.style.removeProperty('display');
              const el = document.getElementById('cylBot_size');
              if (el) { el.disabled = false; el.blur(); }
              const target = activeId ? document.getElementById(activeId) : null;
              if (target && typeof target.focus === 'function') target.focus();
              else document.body.focus();
            }""",
            active_before,
        )
        page.locator("body").click(position={"x": 8, "y": 8})
        after_hash = page.evaluate(STATE_HASH_JS)
        state_restored = before_hash == after_hash

    out = {
        "_detail": {
            "viewport": viewport,
            "browserVersion": browser_version,
            "seg_orders": seg_orders,
            "touch_orders": touch_orders,
            "dead": dead,
            "invalid": invalid,
            "reduced": reduced,
            "state_restored": state_restored,
            "before_hash": before_hash,
            "after_hash": after_hash,
        },
    }
    if seg_focus:
        out["SL-C06-SEG-FOCUS-VISIBLE"] = seg_ok
    if mobile_touch:
        out["SL-C06-GAS-NUM-TOUCH-TARGET"] = touch_ok
    out["SL-C06-CSS-DEAD-SI-INNER"] = bool(dead.get("deadSiInnerOk"))
    out["SL-C06-CSS-DEAD-T-COL"] = bool(dead.get("deadTColOk"))
    out["SL-C06-CSS-DEAD-BTN-CALC"] = bool(dead.get("deadBtnCalcOk"))
    out["SL-C06-FIELD-INVALID-STATE"] = bool(invalid.get("ok"))
    out["SL-C06-REDUCED-MOTION"] = bool(reduced.get("ok"))
    if not state_restored:
        for case_id in CASE_IDS:
            if case_id in out:
                out[case_id] = False
    return out


def _run_viewport(browser, base_url: str, viewport: tuple[int, int], *, mobile_touch: bool, seg_focus: bool) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120000)
    try:
        page.goto(f"{base_url}/index.html", wait_until="load")
        boot_app_page(page, base_url)
        return run_cases(
            page,
            viewport,
            mobile_touch=mobile_touch,
            seg_focus=seg_focus,
            browser_version=browser.version,
        )
    finally:
        context.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    print("=" * 60)
    print("Cycle 06 — UI-CSS-CONTROLS computed-style regression")
    print("=" * 60)

    results: dict[str, bool] = {case_id: True for case_id in CASE_IDS}
    detail: dict = {}

    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            mobile = _run_viewport(browser, base_url, (375, 667), mobile_touch=True, seg_focus=False)
            detail["375x667"] = mobile.pop("_detail")
            for case_id, ok in mobile.items():
                results[case_id] = results[case_id] and bool(ok)

            desktop = _run_viewport(browser, base_url, (1280, 800), mobile_touch=False, seg_focus=True)
            detail["1280x800"] = desktop.pop("_detail")
            for case_id, ok in desktop.items():
                results[case_id] = results[case_id] and bool(ok)

            browser.close()

    rows = [case_row(case_id, results[case_id]) for case_id in CASE_IDS]
    for case_id in CASE_IDS:
        print(f"  {'✓' if results[case_id] else '✗'} [{case_id}]")
        if case_id == "SL-C06-FIELD-INVALID-STATE" and not results[case_id]:
            diagnostics = {
                viewport: detail.get(viewport, {}).get("invalid")
                for viewport in detail
            }
            print("SL-C06-FIELD-INVALID-STATE diagnostic:")
            print(json.dumps(diagnostics, indent=2))
    code = 0 if all(results.values()) else 1
    finish_suite(ROOT, rows, code)
    out = ROOT / "dev" / "ui_controls_css_regression_results.json"
    out.write_text(json.dumps({"results": results, "detail": detail}, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
