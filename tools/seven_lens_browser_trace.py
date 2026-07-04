#!/usr/bin/env python3
"""Execute declarative seven-lens traces through real browser event paths."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "dev"
if str(DEV) not in sys.path:
    sys.path.insert(0, str(DEV))
TRACE_SCHEMA_VERSION = 2


def validate_trace_spec(spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if spec.get("schema_version") != TRACE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {TRACE_SCHEMA_VERSION}")
    repeat = spec.get("repeat", 2)
    if not isinstance(repeat, int) or not 2 <= repeat <= 5:
        errors.append("repeat must be an integer from 2 to 5")
    traces = spec.get("traces")
    if not isinstance(traces, list) or not traces:
        return errors + ["traces must be a non-empty list"]
    ids: set[str] = set()
    for trace in traces:
        trace_id = trace.get("id", "<unknown>")
        if not isinstance(trace_id, str) or len(trace_id.strip()) < 5:
            errors.append("trace id is missing")
        elif trace_id in ids:
            errors.append(f"duplicate trace id {trace_id}")
        ids.add(trace_id)
        if not isinstance(trace.get("entry_event"), str) or len(trace["entry_event"].strip()) < 5:
            errors.append(f"{trace_id}: entry_event missing")
        consumers = trace.get("consumer_path")
        if not isinstance(consumers, list) or len(consumers) < 2 or not all(isinstance(x, str) and x for x in consumers):
            errors.append(f"{trace_id}: consumer_path needs at least two named stages")
        state = trace.get("state", {})
        selectors = state.get("selectors")
        restore = state.get("restore_order")
        if not isinstance(selectors, list) or not selectors:
            errors.append(f"{trace_id}: state selectors missing")
            selectors = []
        elif not all(isinstance(value, str) and value for value in selectors):
            errors.append(f"{trace_id}: state selectors must be non-empty strings")
            selectors = [value for value in selectors if isinstance(value, str) and value]
        if isinstance(restore, list) and not all(isinstance(value, str) and value for value in restore):
            errors.append(f"{trace_id}: restore_order entries must be non-empty strings")
            restore = [value for value in restore if isinstance(value, str) and value]
        if len(selectors) != len(set(selectors)):
            errors.append(f"{trace_id}: state selectors must be unique")
        if (
            not isinstance(restore, list)
            or len(restore) != len(selectors)
            or len(restore) != len(set(restore))
            or set(restore) != set(selectors)
        ):
            errors.append(f"{trace_id}: restore_order must cover every state selector exactly")
        globals_tracked = set(state.get("globals", []))
        for phase_name in ("setup", "steps"):
            rows = trace.get(phase_name, [])
            if not isinstance(rows, list):
                errors.append(f"{trace_id}: {phase_name} must be a list")
                continue
            for row in rows:
                if not isinstance(row, dict):
                    errors.append(f"{trace_id}: {phase_name} entries must be objects")
                    continue
                if "action" not in row:
                    continue
                action = row.get("action")
                if action not in {"fill", "select", "click", "check", "set_global", "run_script"}:
                    errors.append(f"{trace_id}: unsupported {phase_name} action {action!r}")
                if phase_name == "steps" and action == "run_script":
                    errors.append(f"{trace_id}: tested steps must not use run_script")
                if phase_name == "steps" and row.get("force"):
                    errors.append(f"{trace_id}: tested user actions must not use force")
                if (
                    phase_name == "setup"
                    and row.get("force")
                    and not (isinstance(row.get("setup_only_reason"), str) and row["setup_only_reason"].strip())
                ):
                    errors.append(f"{trace_id}: forced setup action needs setup_only_reason")
                selector = row.get("selector")
                if selector and selector not in selectors and phase_name == "steps":
                    errors.append(f"{trace_id}: tested selector {selector} is absent from state snapshot")
                if action == "set_global":
                    if phase_name != "setup":
                        errors.append(f"{trace_id}: set_global is allowed only during setup")
                    if row.get("name") not in globals_tracked:
                        errors.append(f"{trace_id}: setup global {row.get('name')} is not state-tracked")
        steps = trace.get("steps", [])
        if not any("action" in row for row in steps):
            errors.append(f"{trace_id}: trace has no tested user action")
        captures = [row for row in steps if "capture" in row]
        if len(captures) < 2:
            errors.append(f"{trace_id}: trace needs captures before and after the tested action")
        for row in captures:
            values = row.get("values")
            if not isinstance(values, dict) or not values or not all(isinstance(v, str) and v.strip() for v in values.values()):
                errors.append(f"{trace_id}/{row.get('capture')}: capture expressions missing")
        assertions = trace.get("assertions")
        if not isinstance(assertions, list) or not assertions:
            errors.append(f"{trace_id}: assertions must be non-empty")
            continue
        assertion_ids = [row.get("id") for row in assertions]
        if any(not isinstance(value, str) or not value for value in assertion_ids):
            errors.append(f"{trace_id}: every assertion needs an id")
        if len(assertion_ids) != len(set(assertion_ids)):
            errors.append(f"{trace_id}: assertion ids must be unique")
        for row in assertions:
            if row.get("op") not in {"equal", "not_equal", "close", "finite"}:
                errors.append(f"{trace_id}/{row.get('id')}: invalid assertion operator")
            if not isinstance(row.get("left"), str) or not row["left"].startswith("$."):
                errors.append(f"{trace_id}/{row.get('id')}: left side must reference a capture")
    return errors


def _resolve_path(value: Any, captures: dict[str, Any]) -> Any:
    if not isinstance(value, str) or not value.startswith("$"):
        return value
    current: Any = captures
    try:
        for part in value[1:].lstrip(".").split("."):
            current = current[int(part)] if isinstance(current, list) else current[part]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
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


def _capture_is_finite(value: Any) -> bool:
    if isinstance(value, float):
        return value == value and abs(value) != float("inf")
    if isinstance(value, dict):
        return "traceError" not in value and all(_capture_is_finite(item) for item in value.values())
    if isinstance(value, list):
        return all(_capture_is_finite(item) for item in value)
    return True


def _sanitize_capture(value: Any) -> Any:
    if isinstance(value, float) and (value != value or abs(value) == float("inf")):
        return {"traceError": "non-finite capture"}
    if isinstance(value, dict):
        return {key: _sanitize_capture(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_capture(item) for item in value]
    return value


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=True)


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
    elif kind == "run_script":
        page.evaluate(str(action.get("script", "")))
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
        if tag == "BUTTON":
            style = state.get("style")
            if style:
                locator.evaluate("(el, st) => el.setAttribute('style', st)", style)
            if "active" in (state.get("className") or ""):
                locator.click(force=True)
            continue
        if tag == "DIV" and state.get("style") is not None:
            locator.evaluate("(el, st) => el.setAttribute('style', st)", state.get("style"))
            continue
        if tag == "SELECT":
            locator.select_option(str(state["value"]), force=True)
            if selector == "#unitsSelect":
                page.evaluate(
                    "() => { const u = document.getElementById('unitsSelect')?.value; if (typeof setUnits === 'function' && u) setUnits(u); }"
                )
        elif input_type in {"checkbox", "radio"}:
            locator.set_checked(bool(state["checked"]), force=True)
        elif tag in {"INPUT", "TEXTAREA"} and state["value"] is not None:
            locator.fill(str(state["value"]), force=True)
            if selector in {"#travelGasManualDepth", "#cylBot_size", "#bestMixDepth", "#cnsDepth"}:
                page.evaluate(
                    """([sel, dataset]) => {
                      const id = sel.slice(1);
                      if (id.includes('Depth') && typeof syncDepthInputCanonical === 'function') {
                        syncDepthInputCanonical(id);
                      } else if (id.includes('size') && typeof syncVolumeInputCanonical === 'function') {
                        syncVolumeInputCanonical(id);
                      }
                      const el = document.querySelector(sel);
                      if (el && !Object.keys(dataset || {}).length) {
                        for (const key of Object.keys(el.dataset)) delete el.dataset[key];
                      }
                    }""",
                    [selector, state.get("dataset") or {}],
                )
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
    page.evaluate(
        """() => {
          const raw = localStorage.getItem('lspDiveSettings_v6');
          if (!raw || typeof appSettings === 'undefined') return;
          try { appSettings._syncUiAfterRestore?.(JSON.parse(raw)); } catch (_) {}
        }"""
    )
    page.evaluate(
        """state => {
          localStorage.clear();
          sessionStorage.clear();
          for (const [key, value] of Object.entries(state.localStorage)) localStorage.setItem(key, value);
          for (const [key, value] of Object.entries(state.sessionStorage)) sessionStorage.setItem(key, value);
        }""",
        before,
    )
    for selector in selectors:
        state = before["elements"].get(selector)
        if state is None:
            continue
        if selector in {"#travelGasManualDepth", "#cylBot_size", "#bestMixDepth", "#cnsDepth"}:
            page.evaluate(
                """([sel, value, dataset]) => {
                  const el = document.querySelector(sel);
                  if (!el || value == null) return;
                  el.value = String(value);
                  for (const key of Object.keys(el.dataset)) delete el.dataset[key];
                  for (const [k, v] of Object.entries(dataset || {})) el.dataset[k] = v;
                  const id = sel.slice(1);
                  if (id.includes('Depth') && typeof syncDepthInputCanonical === 'function') {
                    syncDepthInputCanonical(id);
                  } else if (id.includes('size') && typeof syncVolumeInputCanonical === 'function') {
                    syncVolumeInputCanonical(id);
                  }
                  if (!Object.keys(dataset || {}).length) {
                    for (const key of Object.keys(el.dataset)) delete el.dataset[key];
                  }
                }""",
                [selector, state.get("value"), state.get("dataset") or {}],
            )
    page.evaluate(
        """([beforeElements, selectors]) => {
          if (selectors.includes('#cylDg3_size') && !beforeElements['#cylDg3_size']) {
            if (document.querySelector('#cylDg3_size') && typeof removeDecoGasCard === 'function') {
              removeDecoGasCard(3);
            }
          }
          if (selectors.includes('#advancedSettingsToggle')) {
            const body = document.getElementById('advancedSettingsBody');
            const summary = document.getElementById('advancedSettingsSummary');
            if (body && body.style.display !== 'none' && summary) summary.textContent = '';
            else if (typeof _updateAdvancedSummary === 'function') _updateAdvancedSummary();
          }
        }""",
        [before.get("elements", {}), selectors],
    )


def run_trace(
    page, trace: dict[str, Any], console_errors: list[str], page_errors: list[str]
) -> dict[str, Any]:
    state_spec = trace.get("state", {})
    before: dict[str, Any] = {}
    captures: dict[str, Any] = {}
    error = ""
    try:
        for action in trace.get("setup", []):
            _act(page, action)
        before = _state_snapshot(page, state_spec)
        for step in trace.get("steps", []):
            if "action" in step:
                _act(page, step)
            if "capture" in step:
                captures[step["capture"]] = _sanitize_capture(
                    _capture(page, step.get("values", {}))
                )
    except Exception as exc:  # browser errors belong in the artifact
        error = str(exc)
    finally:
        if before:
            try:
                _restore(page, before, state_spec)
            except Exception as exc:
                suffix = f"state restoration failed: {exc}"
                error = f"{error}; {suffix}" if error else suffix
    after = _state_snapshot(page, state_spec) if before else {}
    assertion_rows = []
    for assertion in trace.get("assertions", []):
        passed, detail = evaluate_assertion(assertion, captures)
        assertion_rows.append({"id": assertion.get("id"), "passed": passed, "detail": detail})
    state_restored = before == after
    passed = (
        not error and not console_errors and not page_errors and state_restored
        and _capture_is_finite(captures)
        and bool(assertion_rows) and all(row["passed"] for row in assertion_rows)
    )
    return {
        "id": trace.get("id"),
        "entry_event": trace.get("entry_event"),
        "consumer_path": trace.get("consumer_path", []),
        "captures": captures,
        "assertions": assertion_rows,
        "state_before_sha256": hashlib.sha256(_stable_json(before).encode()).hexdigest(),
        "state_after_sha256": hashlib.sha256(_stable_json(after).encode()).hexdigest(),
        "state_before": before,
        "state_after": after,
        "state_restored": state_restored,
        "console_errors": console_errors,
        "page_errors": page_errors,
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
    spec_errors = validate_trace_spec(spec)
    if spec_errors:
        print("SEVEN-LENS BROWSER TRACE SPEC: INVALID", file=sys.stderr)
        for error in spec_errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    from playwright.sync_api import sync_playwright
    from playwright_boot import boot_app_page
    from test_http import serve_www

    results = []
    repeat = spec.get("repeat", 2)
    with serve_www(ROOT) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            for trace in spec.get("traces", []):
                runs = []
                for _ in range(repeat):
                    context = browser.new_context()
                    page = context.new_page()
                    console_errors: list[str] = []
                    page_errors: list[str] = []
                    page.on("console", lambda msg, out=console_errors: out.append(msg.text) if msg.type == "error" else None)
                    page.on("pageerror", lambda error, out=page_errors: out.append(str(error)))
                    boot_app_page(page, base_url)
                    runs.append(run_trace(page, trace, console_errors, page_errors))
                    context.close()
                first = dict(runs[0])
                repeatable = all(
                    _stable_json(row.get("captures")) == _stable_json(first.get("captures"))
                    and _stable_json(row.get("assertions")) == _stable_json(first.get("assertions"))
                    and row.get("state_restored") == first.get("state_restored")
                    for row in runs[1:]
                )
                first["repeatable"] = repeatable
                first["repeat_count"] = repeat
                first["runs"] = runs
                first["passed"] = repeatable and all(row.get("passed") is True for row in runs)
                results.append(first)
        finally:
            browser.close()
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    artifact = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "runner_version": 2,
        "spec": str(args.spec),
        "spec_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(),
        "commit": git_commit,
        "traces": results,
        "passed": bool(results) and all(r["passed"] for r in results),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(f"SEVEN-LENS BROWSER TRACE: {'PASS' if artifact['passed'] else 'FAIL'}")
    for row in results:
        print(f"  [{'PASS' if row['passed'] else 'FAIL'}] {row['id']}")
    return 0 if artifact["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
