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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(DEV) not in sys.path:
    sys.path.insert(0, str(DEV))
TRACE_SCHEMA_VERSION = 3


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
        if not isinstance(consumers, list) or len(consumers) < 4 or not all(isinstance(x, str) and x for x in consumers):
            errors.append(f"{trace_id}: consumer_path needs input, writer, consumer, and observable stages")
        case_ids = trace.get("case_ids")
        if not isinstance(case_ids, list) or not case_ids or not all(
            isinstance(case_id, str) and case_id.strip() for case_id in case_ids
        ):
            errors.append(f"{trace_id}: case_ids must be a non-empty list")
        elif len(case_ids) != len(set(case_ids)):
            errors.append(f"{trace_id}: case_ids must be unique")
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
                if action not in {"fill", "select", "click", "check", "set_enabled", "set_global", "run_script", "set_viewport", "emulate_media", "press_key", "type_text"}:
                    errors.append(f"{trace_id}: unsupported {phase_name} action {action!r}")
                if phase_name == "steps" and row.get("force"):
                    errors.append(f"{trace_id}: tested user actions must not use force")
                if phase_name == "steps" and action in {"set_global", "run_script", "set_viewport", "emulate_media"}:
                    errors.append(f"{trace_id}: tested user actions must use visible Playwright controls")
                if (
                    phase_name == "setup"
                    and (row.get("force") or action == "run_script")
                    and action not in {"set_viewport", "emulate_media"}
                    and not (isinstance(row.get("setup_only_reason"), str) and row["setup_only_reason"].strip())
                ):
                    errors.append(f"{trace_id}: forced or scripted setup needs setup_only_reason")
                selector = row.get("selector")
                if selector and selector not in selectors and phase_name == "steps":
                    errors.append(f"{trace_id}: tested selector {selector} is absent from state snapshot")
                if action == "set_global":
                    if phase_name != "setup":
                        errors.append(f"{trace_id}: set_global is allowed only during setup")
                    if row.get("name") not in globals_tracked:
                        errors.append(f"{trace_id}: setup global {row.get('name')} is not state-tracked")
                if action in {"set_viewport", "emulate_media"} and phase_name != "setup":
                    errors.append(f"{trace_id}: {action} is allowed only during setup")
                if action in {"fill", "select", "click", "check", "set_enabled"} and not selector:
                    errors.append(f"{trace_id}: {action} action needs a selector")
                if action == "press_key" and not row.get("key"):
                    errors.append(f"{trace_id}: press_key action needs key")
                if action == "type_text" and not row.get("text"):
                    errors.append(f"{trace_id}: type_text action needs text")
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
              disabled: 'disabled' in el ? el.disabled : null,
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


_CANONICAL_DEPTH_SELECTORS = {
    "#travelGasManualDepth",
    "#cylBot_size",
    "#bestMixDepth",
    "#cnsDepth",
    "#tecDepth",
    "#tecBT",
    "#recDepth",
    "#recBT",
}

# Bound to index.html input debounce: setTimeout(() => appSettings.save(false), 1000)
SETTINGS_SAVE_DEBOUNCE_MS = 1000
SETTINGS_SAVE_DEBOUNCE_SETTLE_MS = 100
SETTINGS_SAVE_DEBOUNCE_WAIT_MS = SETTINGS_SAVE_DEBOUNCE_MS + SETTINGS_SAVE_DEBOUNCE_SETTLE_MS

_RESTORE_SESSION_BEGIN_JS = """() => {
  const session = {
    hadAppSettings: typeof appSettings !== 'undefined',
    previousRestoreInProgress: false,
    patched: false,
  };
  if (!session.hadAppSettings) {
    window.__traceRestoreSession = session;
    return session;
  }
  session.previousRestoreInProgress = !!appSettings._restoreInProgress;
  appSettings._restoreInProgress = true;
  session.origSave = appSettings.save.bind(appSettings);
  appSettings.save = function(v) {
    if (window.__traceRestoreSession) return;
    return session.origSave(v);
  };
  session.patched = true;
  window.__traceRestoreSession = session;
  return session;
}"""

_RESTORE_SESSION_END_JS = """() => {
  const session = window.__traceRestoreSession;
  if (!session) return;
  if (session.patched && typeof appSettings !== 'undefined') {
    appSettings.save = session.origSave;
    appSettings._restoreInProgress = session.previousRestoreInProgress;
  }
  delete window.__traceRestoreSession;
}"""

_APPLY_STORAGE_SNAPSHOT_JS = """(state) => {
  localStorage.clear();
  sessionStorage.clear();
  for (const [key, value] of Object.entries(state.localStorage || {})) localStorage.setItem(key, value);
  for (const [key, value] of Object.entries(state.sessionStorage || {})) sessionStorage.setItem(key, value);
  for (const [key, value] of Object.entries(state.globals || {})) window[key] = value;
}"""

_INVOKE_RESTORE_FIELDS_JS = """() => {
  if (typeof appSettings === 'undefined' || typeof appSettings._restoreFields !== 'function') {
    return { invoked: false };
  }
  const raw = localStorage.getItem('lspDiveSettings_v6');
  if (!raw) return { invoked: false };
  try { appSettings._restoreFields(JSON.parse(raw)); } catch (_) {}
  if (window.__traceRestoreSession) appSettings._restoreInProgress = true;
  return { invoked: true };
}"""

_SYNC_DOM_FROM_STORAGE_JS = """() => {
  const raw = localStorage.getItem('lspDiveSettings_v6');
  if (!raw) return { synced: false };
  let values;
  try { values = JSON.parse(raw); } catch (_) { return { synced: false }; }
  for (const id of ['tecDepth', 'tecBT', 'recDepth', 'recBT']) {
    const el = document.getElementById(id);
    if (el && values[id] != null) el.value = String(values[id]);
  }
  if (values.__units__ && typeof setUnits === 'function') setUnits(values.__units__, { relabelOnly: true });
  for (const id of ['tecDepth', 'tecBT', 'recDepth', 'recBT']) {
    if (typeof syncDepthInputCanonical === 'function' && id.includes('Depth')) syncDepthInputCanonical(id);
  }
  return { synced: true };
}"""

_VERIFY_PERSISTED_CONSISTENCY_JS = """(expected) => {
  const raw = localStorage.getItem('lspDiveSettings_v6');
  const expectedRaw = expected.localStorage?.['lspDiveSettings_v6'];
  if (!expectedRaw) return { ok: !raw, mismatches: raw ? ['unexpected localStorage'] : [] };
  if (!raw) return { ok: false, mismatches: ['missing localStorage'] };
  let parsed;
  let expectedParsed;
  try { parsed = JSON.parse(raw); expectedParsed = JSON.parse(expectedRaw); }
  catch (_) { return { ok: false, mismatches: ['parse error'] }; }
  const fields = ['tecDepth', 'tecBT', 'recDepth', 'recBT', '__units__'];
  const mismatches = [];
  for (const field of fields) {
    if (!Object.prototype.hasOwnProperty.call(expectedParsed, field)) continue;
    if (String(parsed[field]) !== String(expectedParsed[field])) mismatches.push('ls:' + field);
    const el = document.getElementById(field.startsWith('__') ? null : field);
    if (el && String(el.value) !== String(expectedParsed[field])) mismatches.push('dom:' + field);
  }
  return { ok: mismatches.length === 0, mismatches };
}"""

_CAPTURE_RESTORE_DIAGNOSTICS_JS = """() => ({
  restoreInProgress: typeof appSettings !== 'undefined' ? !!appSettings._restoreInProgress : null,
  restoreSessionActive: !!window.__traceRestoreSession,
  plannerAlgo: typeof plannerAlgo !== 'undefined' ? plannerAlgo : null,
  navMode: typeof navMode !== 'undefined' ? navMode : null,
  units: typeof units !== 'undefined' ? units : null,
  tecDepthDom: document.getElementById('tecDepth')?.value ?? null,
  tecDepthLs: (() => {
    try {
      const raw = localStorage.getItem('lspDiveSettings_v6');
      return raw ? JSON.parse(raw).tecDepth ?? null : null;
    } catch (_) { return null; }
  })(),
  hasResults: document.getElementById('resultsPanel')?.classList.contains('has-results') ?? null,
  recMobileActive: document.getElementById('recPlannerView')?.classList.contains('mobile-active') ?? null,
  tecMobileActive: document.getElementById('tecPlannerView')?.classList.contains('mobile-active') ?? null,
})"""


def _sync_canonical_input(page, selector: str, state: dict[str, Any]) -> None:
    if selector not in _CANONICAL_DEPTH_SELECTORS:
        return
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


def _restore_session_begin(page) -> dict[str, Any]:
    return page.evaluate(_RESTORE_SESSION_BEGIN_JS)


def _restore_session_end(page) -> None:
    page.evaluate(_RESTORE_SESSION_END_JS)


def _apply_storage_snapshot(page, before: dict[str, Any]) -> None:
    page.evaluate(_APPLY_STORAGE_SNAPSHOT_JS, before)


def _invoke_restore_fields(page) -> dict[str, Any]:
    return page.evaluate(_INVOKE_RESTORE_FIELDS_JS)


def _sync_dom_from_storage(page) -> dict[str, Any]:
    return page.evaluate(_SYNC_DOM_FROM_STORAGE_JS)


def _wait_settings_debounce_contract(page) -> None:
    page.wait_for_timeout(SETTINGS_SAVE_DEBOUNCE_WAIT_MS)


def _verify_persisted_consistency(page, before: dict[str, Any]) -> None:
    check = page.evaluate(_VERIFY_PERSISTED_CONSISTENCY_JS, before)
    if not check.get("ok"):
        mismatches = check.get("mismatches") or []
        raise RuntimeError(f"persisted settings inconsistent after restore: {mismatches}")


def capture_restore_diagnostics(page) -> dict[str, Any]:
    """Post-suite probe: restore flag, planner state, and persistence alignment."""
    return page.evaluate(_CAPTURE_RESTORE_DIAGNOSTICS_JS)


def _restore_persisted_settings(page, before: dict[str, Any]) -> None:
    _restore_session_begin(page)
    try:
        _apply_storage_snapshot(page, before)
        _invoke_restore_fields(page)
        _wait_settings_debounce_contract(page)
        _apply_storage_snapshot(page, before)
        _sync_dom_from_storage(page)
        _verify_persisted_consistency(page, before)
    finally:
        _restore_session_end(page)


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
    elif kind == "set_enabled":
        locator.evaluate("(el, enabled) => { el.disabled = !enabled; }", bool(action.get("value", True)))
    elif kind == "set_global":
        page.evaluate(
            "([name, value]) => { window[name] = value; }",
            [str(action.get("name")), action.get("value")],
        )
    elif kind == "run_script":
        page.evaluate(str(action.get("script", "")))
    elif kind == "set_viewport":
        size = action.get("size") or {}
        page.set_viewport_size({"width": int(size.get("width", 1280)), "height": int(size.get("height", 800))})
        page.wait_for_timeout(100)
    elif kind == "emulate_media":
        params = {k: v for k, v in (action.get("params") or {}).items() if v is not None}
        page.emulate_media(**params)
    elif kind == "press_key":
        repeats = int(action.get("repeat", 1))
        key = str(action.get("key", ""))
        for _ in range(max(1, repeats)):
            page.keyboard.press(key)
    elif kind == "type_text":
        page.keyboard.type(str(action.get("text", "")))
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
            if "active" in (state.get("className") or ""):
                locator.click(force=True)
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
            if "disabled" in state and state["disabled"] is not None:
                locator.evaluate("(el, disabled) => { el.disabled = disabled; }", bool(state["disabled"]))
            if selector in _CANONICAL_DEPTH_SELECTORS:
                _sync_canonical_input(page, selector, state)
        dataset = state.get("dataset") or {}
        locator.evaluate(
            """(el, ds) => {
              for (const key of Object.keys(el.dataset)) delete el.dataset[key];
              for (const [k, v] of Object.entries(ds)) el.dataset[k] = v;
            }""",
            dataset,
        )
    _restore_persisted_settings(page, before)
    for selector in selectors:
        state = before["elements"].get(selector)
        if state is None:
            continue
        _sync_canonical_input(page, selector, state)


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
                delay_ms = step.get("delay_ms")
                if delay_ms:
                    page.wait_for_timeout(int(delay_ms))
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
                first["case_ids"] = trace.get("case_ids", [])
                first["runs"] = runs
                first["passed"] = repeatable and all(row.get("passed") is True for row in runs)
                results.append(first)
        finally:
            browser.close()
    from tools.seven_lens_protocol import _file_sha256

    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True, check=True
    ).stdout.strip()
    artifact = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "runner_version": 2,
        "spec": str(args.spec),
        "spec_sha256": _file_sha256(spec_path),
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
