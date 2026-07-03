#!/usr/bin/env python3
"""Execute declarative seven-lens traces through real browser event paths."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "dev"
if str(DEV) not in sys.path:
    sys.path.insert(0, str(DEV))


def _resolve_path(value: Any, captures: dict[str, Any]) -> Any:
    if not isinstance(value, str) or not value.startswith("$"):
        return value
    current: Any = captures
    for part in value[1:].lstrip(".").split("."):
        current = current[int(part)] if isinstance(current, list) else current[part]
    return current


def evaluate_assertion(assertion: dict[str, Any], captures: dict[str, Any]) -> tuple[bool, str]:
    left = _resolve_path(assertion.get("left"), captures)
    right = _resolve_path(assertion.get("right"), captures)
    op = assertion.get("op")
    if op == "equal":
        passed = left == right
    elif op == "not_equal":
        passed = left != right
    elif op == "close":
        tolerance = float(assertion.get("tolerance", 1e-9))
        try:
            passed = abs(float(left) - float(right)) <= tolerance
        except (TypeError, ValueError):
            passed = False
    elif op == "finite":
        try:
            value = float(left)
            passed = value == value and abs(value) != float("inf")
        except (TypeError, ValueError):
            passed = False
    else:
        return False, f"unknown assertion operator {op!r}"
    return passed, f"{left!r} {op} {right!r}"


def _capture(page, values: dict[str, str]) -> dict[str, Any]:
    return page.evaluate(
        """values => Object.fromEntries(Object.entries(values).map(([name, expression]) => {
          try { return [name, (0, eval)(expression)]; }
          catch (error) { return [name, {traceError: String(error)}]; }
        }))""",
        values,
    )


def _state_snapshot(page, spec: dict[str, Any]) -> dict[str, Any]:
    return page.evaluate(
        """spec => {
          const elements = {};
          for (const selector of spec.selectors || []) {
            const el = document.querySelector(selector);
            elements[selector] = el ? {
              value: 'value' in el ? el.value : null,
              checked: 'checked' in el ? el.checked : null,
              text: el.textContent,
              className: el.className,
              style: el.getAttribute('style'),
              dataset: {...el.dataset}
            } : null;
          }
          const globals = {};
          for (const name of spec.globals || []) globals[name] = window[name];
          return {elements, globals, localStorage: {...localStorage}, sessionStorage: {...sessionStorage}};
        }""",
        spec,
    )


def _act(page, action: dict[str, Any]) -> None:
    selector = action.get("selector")
    locator = page.locator(selector) if selector else None
    if locator is not None and locator.count() != 1:
        raise RuntimeError(f"{selector}: expected exactly one element")
    kind = action.get("action")
    force = bool(action.get("force", False))
    if kind == "fill":
        locator.fill(str(action.get("value", "")), force=force)
    elif kind == "select":
        locator.select_option(str(action.get("value", "")), force=force)
    elif kind == "click":
        locator.click(force=force)
    elif kind == "check":
        locator.set_checked(bool(action.get("value")), force=force)
    elif kind == "set_global":
        page.evaluate(
            "([name, value]) => { window[name] = value; }",
            [str(action.get("name")), action.get("value")],
        )
    else:
        raise RuntimeError(f"unsupported browser action {kind!r}")


def _restore(page, before: dict[str, Any], spec: dict[str, Any]) -> None:
    selectors = spec.get("restore_order") or spec.get("selectors", [])
    for selector in selectors:
        state = before["elements"].get(selector)
        if state is None:
            continue
        locator = page.locator(selector)
        tag = locator.evaluate("el => el.tagName")
        input_type = locator.get_attribute("type")
        if tag == "SELECT":
            locator.select_option(str(state["value"]), force=True)
        elif input_type in {"checkbox", "radio"}:
            locator.set_checked(bool(state["checked"]), force=True)
        elif state["value"] is not None:
            locator.fill(str(state["value"]), force=True)
        dataset = state.get("dataset") or {}
        locator.evaluate(
            """(el, ds) => {
              for (const key of Object.keys(el.dataset)) delete el.dataset[key];
              for (const [k, v] of Object.entries(ds)) el.dataset[k] = v;
            }""",
            dataset,
        )
    page.evaluate(
        """state => {
          localStorage.clear();
          sessionStorage.clear();
          for (const [key, value] of Object.entries(state.localStorage)) localStorage.setItem(key, value);
          for (const [key, value] of Object.entries(state.sessionStorage)) sessionStorage.setItem(key, value);
          for (const [key, value] of Object.entries(state.globals)) window[key] = value;
        }""",
        before,
    )


def run_trace(page, trace: dict[str, Any]) -> dict[str, Any]:
    for action in trace.get("setup", []):
        _act(page, action)
    state_spec = trace.get("state", {})
    before = _state_snapshot(page, state_spec)
    captures: dict[str, Any] = {}
    error = ""
    try:
        for step in trace.get("steps", []):
            if "action" in step:
                _act(page, step)
            if "capture" in step:
                captures[step["capture"]] = _capture(page, step.get("values", {}))
    except Exception as exc:  # browser errors belong in the artifact
        error = str(exc)
    finally:
        _restore(page, before, state_spec)
    after = _state_snapshot(page, state_spec)
    assertion_rows = []
    for assertion in trace.get("assertions", []):
        passed, detail = evaluate_assertion(assertion, captures)
        assertion_rows.append({"id": assertion.get("id"), "passed": passed, "detail": detail})
    state_restored = before == after
    passed = not error and state_restored and all(row["passed"] for row in assertion_rows)
    return {
        "id": trace.get("id"),
        "entry_event": trace.get("entry_event"),
        "consumer_path": trace.get("consumer_path", []),
        "captures": captures,
        "assertions": assertion_rows,
        "state_before_sha256": hashlib.sha256(json.dumps(before, sort_keys=True).encode()).hexdigest(),
        "state_after_sha256": hashlib.sha256(json.dumps(after, sort_keys=True).encode()).hexdigest(),
        "state_before": before,
        "state_after": after,
        "state_restored": state_restored,
        "error": error,
        "passed": passed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("dev/seven-lens-browser-trace.json"))
    args = parser.parse_args()
    spec_path = args.spec if args.spec.is_absolute() else ROOT / args.spec
    output = args.output if args.output.is_absolute() else ROOT / args.output
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    from playwright.sync_api import sync_playwright
    from playwright_boot import boot_app_page
    from test_http import serve_www

    results = []
    with serve_www(ROOT) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for trace in spec.get("traces", []):
                context = browser.new_context()
                page = context.new_page()
                boot_app_page(page, base_url)
                results.append(run_trace(page, trace))
                context.close()
        finally:
            browser.close()
    artifact = {"spec": str(args.spec), "traces": results, "passed": all(r["passed"] for r in results)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"SEVEN-LENS BROWSER TRACE: {'PASS' if artifact['passed'] else 'FAIL'}")
    for row in results:
        print(f"  [{'PASS' if row['passed'] else 'FAIL'}] {row['id']}")
    return 0 if artifact["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
