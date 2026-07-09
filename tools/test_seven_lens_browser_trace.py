from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

from tools.seven_lens_browser_trace import (
    SETTINGS_SAVE_DEBOUNCE_MS,
    SETTINGS_SAVE_DEBOUNCE_SETTLE_MS,
    SETTINGS_SAVE_DEBOUNCE_WAIT_MS,
    _CANONICAL_DEPTH_SELECTORS,
    _capture_is_finite,
    capture_restore_diagnostics,
    evaluate_assertion,
    validate_trace_spec,
)

ROOT = Path(__file__).resolve().parents[1]


def _ephemeral_trace_output(suffix: str = "") -> Path:
    handle = tempfile.NamedTemporaryFile(
        suffix=f"{suffix}.json",
        prefix="seven-lens-browser-trace-suite-order-",
        delete=False,
    )
    path = Path(handle.name)
    handle.close()
    return path


def valid_spec():
    return {
        "schema_version": 3,
        "repeat": 2,
        "traces": [{
            "id": "TRACE-UNIT-ROUNDTRIP",
            "entry_event": "User changes the visible units selector.",
            "consumer_path": ["unitsSelect change", "setUnits", "physical consumer", "rendered depth"],
            "case_ids": ["TRACE-UNIT-ROUNDTRIP"],
            "state": {
                "selectors": ["#unitsSelect", "#depth"],
                "restore_order": ["#depth", "#unitsSelect"],
                "globals": [],
            },
            "setup": [],
            "steps": [
                {"capture": "before", "values": {"depth": "Number(depth.value)"}},
                {"action": "select", "selector": "#unitsSelect", "value": "imperial"},
                {"capture": "after", "values": {"depth": "Number(depth.value)"}},
            ],
            "assertions": [{
                "id": "physical-depth-preserved",
                "left": "$.before.depth",
                "op": "not_equal",
                "right": "$.after.depth",
            }],
        }],
    }


class RestorationSimulator:
    """Deterministic fake page for browser-trace settings restoration."""

    def __init__(self, *, has_app_settings: bool = True, has_restore_fields: bool = True):
        self.has_app_settings = has_app_settings
        self.has_restore_fields = has_restore_fields
        self.restore_in_progress = False
        self.local_storage: dict[str, str] = {}
        self.session_storage: dict[str, str] = {}
        self.globals: dict[str, Any] = {}
        self.dom: dict[str, str] = {
            "tecDepth": "45",
            "tecBT": "25",
            "recDepth": "30",
            "recBT": "20",
        }
        self.units = "metric"
        self.save_calls = 0
        self.restore_fields_calls = 0
        self.timeouts: list[int] = []
        self.restore_session: dict[str, Any] | None = None
        self.pending_save_timer: int | None = None
        self.clock = 0
        self.raise_on_restore = False

    def _settings_blob(self) -> dict[str, Any]:
        return {
            "tecDepth": self.dom.get("tecDepth", "45"),
            "tecBT": self.dom.get("tecBT", "25"),
            "recDepth": self.dom.get("recDepth", "30"),
            "recBT": self.dom.get("recBT", "20"),
            "__units__": self.units,
        }

    def save(self, _verbose: bool = True) -> None:
        if self.restore_session is not None:
            return
        if self.restore_in_progress:
            return
        self.save_calls += 1
        self.local_storage["lspDiveSettings_v6"] = json.dumps(self._settings_blob())

    def restore_fields(self, values: dict[str, Any]) -> None:
        if self.raise_on_restore:
            raise RuntimeError("restore_fields failed")
        self.restore_fields_calls += 1
        self.restore_in_progress = True
        try:
            for field in ("tecDepth", "tecBT", "recDepth", "recBT"):
                if field in values:
                    self.dom[field] = str(values[field])
            if values.get("__units__"):
                self.units = str(values["__units__"])
        finally:
            self.restore_in_progress = False
        self.save(False)

    def schedule_debounced_save(self) -> None:
        self.pending_save_timer = self.clock + SETTINGS_SAVE_DEBOUNCE_MS

    def tick(self, ms: int) -> None:
        self.clock += ms
        if self.pending_save_timer is not None and self.clock >= self.pending_save_timer:
            self.pending_save_timer = None
            self.save(False)

    def apply_snapshot(self, before: dict[str, Any]) -> None:
        self.local_storage = dict(before.get("localStorage") or {})
        self.session_storage = dict(before.get("sessionStorage") or {})
        self.globals = dict(before.get("globals") or {})

    def sync_dom_from_storage(self) -> None:
        raw = self.local_storage.get("lspDiveSettings_v6")
        if not raw:
            return
        values = json.loads(raw)
        for field in ("tecDepth", "tecBT", "recDepth", "recBT"):
            if field in values:
                self.dom[field] = str(values[field])
        if values.get("__units__"):
            self.units = str(values["__units__"])

    def verify_consistency(self, before: dict[str, Any]) -> bool:
        expected_raw = (before.get("localStorage") or {}).get("lspDiveSettings_v6")
        if not expected_raw:
            return not self.local_storage.get("lspDiveSettings_v6")
        expected = json.loads(expected_raw)
        actual_raw = self.local_storage.get("lspDiveSettings_v6")
        if not actual_raw:
            return False
        actual = json.loads(actual_raw)
        for field in ("tecDepth", "tecBT", "recDepth", "recBT", "__units__"):
            if field in expected and str(actual.get(field)) != str(expected[field]):
                return False
            dom_field = field if not field.startswith("__") else None
            if dom_field and str(self.dom.get(dom_field)) != str(expected[field]):
                return False
        return True

    def session_begin(self) -> dict[str, Any]:
        session = {
            "hadAppSettings": self.has_app_settings,
            "previousRestoreInProgress": self.restore_in_progress if self.has_app_settings else False,
            "patched": False,
        }
        if not self.has_app_settings:
            self.restore_session = session
            return session
        self.restore_in_progress = True
        session["patched"] = True
        self.restore_session = session
        return session

    def session_end(self) -> None:
        session = self.restore_session
        if not session:
            return
        if session.get("patched") and self.has_app_settings:
            self.restore_in_progress = bool(session.get("previousRestoreInProgress"))
        self.restore_session = None

    def invoke_restore_fields(self) -> dict[str, Any]:
        if not self.has_app_settings or not self.has_restore_fields:
            return {"invoked": False}
        raw = self.local_storage.get("lspDiveSettings_v6")
        if not raw:
            return {"invoked": False}
        self.restore_fields(json.loads(raw))
        if self.restore_session is not None:
            self.restore_in_progress = True
        return {"invoked": True}

    def wait_debounce_contract(self) -> None:
        self.timeouts.append(SETTINGS_SAVE_DEBOUNCE_WAIT_MS)
        self.tick(SETTINGS_SAVE_DEBOUNCE_WAIT_MS)


def restore_persisted_settings_prefix(sim: RestorationSimulator, before: dict[str, Any]) -> None:
    """Pre-fix f8074d7 runner: sets save-block without guaranteed finally cleanup."""
    if sim.has_app_settings:
        sim.restore_in_progress = True
    sim.apply_snapshot(before)
    sim.invoke_restore_fields()
    sim.wait_debounce_contract()
    sim.apply_snapshot(before)
    # No finally: nested prior-true is lost because _restoreFields clears the flag.


def restore_persisted_settings_fixed(sim: RestorationSimulator, before: dict[str, Any]) -> None:
    sim.session_begin()
    try:
        sim.apply_snapshot(before)
        sim.invoke_restore_fields()
        sim.wait_debounce_contract()
        sim.apply_snapshot(before)
        sim.sync_dom_from_storage()
        if not sim.verify_consistency(before):
            raise RuntimeError("persisted settings inconsistent after restore")
    finally:
        sim.session_end()


def sample_before(*, tec_depth: str = "45", units: str = "metric") -> dict[str, Any]:
    blob = {
        "tecDepth": tec_depth,
        "tecBT": "25",
        "recDepth": "30",
        "recBT": "20",
        "__units__": units,
    }
    return {
        "localStorage": {"lspDiveSettings_v6": json.dumps(blob)},
        "sessionStorage": {},
        "globals": {},
        "elements": {
            "#tecDepth": {"value": tec_depth},
            "#tecBT": {"value": "25"},
            "#recDepth": {"value": "30"},
            "#recBT": {"value": "20"},
        },
    }


class SevenLensBrowserTraceTests(unittest.TestCase):
    def test_empty_trace_list_is_rejected(self):
        spec = valid_spec()
        spec["traces"] = []
        self.assertIn("traces must be a non-empty list", validate_trace_spec(spec))

    def test_empty_assertion_list_is_rejected(self):
        spec = valid_spec()
        spec["traces"][0]["assertions"] = []
        self.assertTrue(any("assertions must be non-empty" in error for error in validate_trace_spec(spec)))

    def test_forced_tested_action_is_rejected(self):
        spec = valid_spec()
        spec["traces"][0]["steps"][1]["force"] = True
        self.assertTrue(any("tested user actions must not use force" in error for error in validate_trace_spec(spec)))

    def test_single_run_cannot_claim_repeatability(self):
        spec = valid_spec()
        spec["repeat"] = 1
        self.assertTrue(any("repeat must be" in error for error in validate_trace_spec(spec)))

    def test_scripted_tested_action_is_rejected(self):
        spec = valid_spec()
        spec["traces"][0]["steps"][1] = {"action": "run_script", "script": "() => {}"}
        self.assertTrue(any("visible Playwright controls" in error for error in validate_trace_spec(spec)))

    def test_trace_requires_case_ids_and_full_consumer_path(self):
        spec = valid_spec()
        del spec["traces"][0]["case_ids"]
        spec["traces"][0]["consumer_path"] = ["input", "consumer"]
        errors = validate_trace_spec(spec)
        self.assertTrue(any("case_ids" in error for error in errors))
        self.assertTrue(any("input, writer, consumer, and observable" in error for error in errors))

    def test_non_finite_or_evaluation_error_capture_is_rejected(self):
        self.assertFalse(_capture_is_finite({"physical_depth": float("nan")}))
        self.assertFalse(_capture_is_finite({"consumer": {"traceError": "missing function"}}))

    def test_close_assertion_uses_exact_captured_value(self):
        captures = {"metric": {"canonical_m": 30.0}, "imperial": {"canonical_m": 29.870399}}
        ok, _ = evaluate_assertion(
            {"left": "$.metric.canonical_m", "op": "close", "right": 30, "tolerance": 1e-9},
            captures,
        )
        drifted, _ = evaluate_assertion(
            {"left": "$.imperial.canonical_m", "op": "close", "right": 30, "tolerance": 1e-9},
            captures,
        )
        self.assertTrue(ok)
        self.assertFalse(drifted)

    def test_equal_assertion_resolves_both_capture_paths(self):
        captures = {"before": {"value": "30"}, "after": {"value": "30"}}
        ok, _ = evaluate_assertion(
            {"left": "$.before.value", "op": "equal", "right": "$.after.value"}, captures
        )
        self.assertTrue(ok)

    def test_setup_viewport_and_emulate_media_are_accepted(self):
        spec = valid_spec()
        spec["traces"][0]["setup"] = [
            {"action": "set_viewport", "size": {"width": 375, "height": 667}},
            {"action": "emulate_media", "params": {"reduced_motion": "reduce"}},
        ]
        self.assertEqual(validate_trace_spec(spec), [])

    def test_setup_press_key_and_type_text_require_fields(self):
        spec = valid_spec()
        spec["traces"][0]["setup"] = [{"action": "press_key"}]
        self.assertTrue(any("press_key action needs key" in error for error in validate_trace_spec(spec)))
        spec["traces"][0]["setup"] = [{"action": "type_text"}]
        self.assertTrue(any("type_text action needs text" in error for error in validate_trace_spec(spec)))

    def test_viewport_and_emulate_media_rejected_in_tested_steps(self):
        spec = valid_spec()
        spec["traces"][0]["steps"] = [
            {"capture": "before", "values": {"depth": "Number(depth.value)"}},
            {"action": "set_viewport", "size": {"width": 375, "height": 667}},
            {"capture": "after", "values": {"depth": "Number(depth.value)"}},
        ]
        errors = validate_trace_spec(spec)
        self.assertTrue(any("set_viewport is allowed only during setup" in error for error in errors))

    def test_press_key_and_type_text_allowed_in_tested_steps(self):
        spec = valid_spec()
        spec["traces"][0]["steps"] = [
            {"capture": "before", "values": {"depth": "Number(depth.value)"}},
            {"action": "click", "selector": "#depth"},
            {"action": "press_key", "key": "Tab"},
            {"action": "type_text", "text": "0"},
            {"capture": "after", "values": {"depth": "Number(depth.value)"}},
        ]
        spec["traces"][0]["assertions"] = [{
            "id": "changed",
            "left": "$.before.depth",
            "op": "not_equal",
            "right": "$.after.depth",
        }]
        self.assertEqual(validate_trace_spec(spec), [])

    def test_restore_uses_planner_depth_selectors(self):
        self.assertIn("#tecDepth", _CANONICAL_DEPTH_SELECTORS)
        self.assertIn("#recDepth", _CANONICAL_DEPTH_SELECTORS)
        self.assertIn("#tecBT", _CANONICAL_DEPTH_SELECTORS)
        self.assertIn("#recBT", _CANONICAL_DEPTH_SELECTORS)

    def test_debounce_contract_is_bound_to_1000ms(self):
        self.assertEqual(SETTINGS_SAVE_DEBOUNCE_MS, 1000)
        self.assertEqual(SETTINGS_SAVE_DEBOUNCE_WAIT_MS, 1100)
        self.assertEqual(SETTINGS_SAVE_DEBOUNCE_SETTLE_MS, 100)

    def test_prefix_loses_nested_prior_true(self):
        sim = RestorationSimulator()
        sim.restore_in_progress = True
        before = sample_before()
        restore_persisted_settings_prefix(sim, before)
        self.assertFalse(sim.restore_in_progress)

    def test_fixed_restores_save_block_false_when_prior_false(self):
        sim = RestorationSimulator()
        before = sample_before()
        sim.dom["tecDepth"] = "999"
        restore_persisted_settings_fixed(sim, before)
        self.assertFalse(sim.restore_in_progress)

    def test_fixed_preserves_save_block_true_when_prior_true(self):
        sim = RestorationSimulator()
        sim.restore_in_progress = True
        before = sample_before()
        restore_persisted_settings_fixed(sim, before)
        self.assertTrue(sim.restore_in_progress)

    def test_fixed_exception_cleanup_restores_prior_false(self):
        sim = RestorationSimulator()
        sim.raise_on_restore = True
        before = sample_before()
        with self.assertRaises(RuntimeError):
            restore_persisted_settings_fixed(sim, before)
        self.assertFalse(sim.restore_in_progress)
        self.assertIsNone(sim.restore_session)

    def test_missing_app_settings_is_safe(self):
        sim = RestorationSimulator(has_app_settings=False)
        before = sample_before()
        restore_persisted_settings_fixed(sim, before)
        self.assertFalse(sim.restore_in_progress)

    def test_missing_restore_fields_is_safe(self):
        sim = RestorationSimulator(has_restore_fields=False)
        before = sample_before()
        restore_persisted_settings_fixed(sim, before)
        self.assertFalse(sim.restore_in_progress)

    def test_restore_fields_invoked(self):
        sim = RestorationSimulator()
        before = sample_before()
        restore_persisted_settings_fixed(sim, before)
        self.assertGreaterEqual(sim.restore_fields_calls, 1)

    def test_delayed_debounced_save_does_not_overwrite_snapshot(self):
        sim = RestorationSimulator()
        before = sample_before(tec_depth="45")
        sim.dom["tecDepth"] = "999"
        sim.schedule_debounced_save()
        restore_persisted_settings_fixed(sim, before)
        stored = json.loads(sim.local_storage["lspDiveSettings_v6"])
        self.assertEqual(stored["tecDepth"], "45")

    def test_snapshot_reapplication_after_debounce(self):
        sim = RestorationSimulator()
        before = sample_before(tec_depth="45")
        sim.dom["tecDepth"] = "999"
        restore_persisted_settings_fixed(sim, before)
        self.assertEqual(sim.dom["tecDepth"], "45")

    def test_rec_depth_and_bt_restore(self):
        sim = RestorationSimulator()
        before = sample_before()
        before["localStorage"]["lspDiveSettings_v6"] = json.dumps({
            "tecDepth": "45", "tecBT": "25", "recDepth": "18", "recBT": "42", "__units__": "metric",
        })
        sim.dom["recDepth"] = "99"
        sim.dom["recBT"] = "99"
        restore_persisted_settings_fixed(sim, before)
        self.assertEqual(sim.dom["recDepth"], "18")
        self.assertEqual(sim.dom["recBT"], "42")

    def test_tec_depth_and_bt_restore(self):
        sim = RestorationSimulator()
        before = sample_before(tec_depth="45")
        sim.dom["tecDepth"] = "999"
        sim.dom["tecBT"] = "99"
        restore_persisted_settings_fixed(sim, before)
        self.assertEqual(sim.dom["tecDepth"], "45")
        self.assertEqual(sim.dom["tecBT"], "25")

    def test_metric_mode_values_remain_correct(self):
        sim = RestorationSimulator()
        before = sample_before(units="metric", tec_depth="45")
        sim.dom["tecDepth"] = "999"
        sim.units = "imperial"
        restore_persisted_settings_fixed(sim, before)
        self.assertEqual(sim.units, "metric")
        self.assertEqual(sim.dom["tecDepth"], "45")

    def test_imperial_mode_values_remain_correct(self):
        sim = RestorationSimulator()
        before = sample_before(units="imperial", tec_depth="148")
        sim.dom["tecDepth"] = "999"
        sim.units = "metric"
        restore_persisted_settings_fixed(sim, before)
        self.assertEqual(sim.units, "imperial")
        self.assertEqual(sim.dom["tecDepth"], "148")

    def test_repeated_restoration_is_idempotent(self):
        sim = RestorationSimulator()
        before = sample_before()
        sim.dom["tecDepth"] = "999"
        restore_persisted_settings_fixed(sim, before)
        first = dict(sim.dom)
        restore_persisted_settings_fixed(sim, before)
        self.assertEqual(sim.dom, first)
        self.assertFalse(sim.restore_in_progress)

    def test_fixed_blocks_save_during_restore_session(self):
        sim = RestorationSimulator()
        sim.dom["tecDepth"] = "999"
        sim.session_begin()
        try:
            sim.save(False)
            self.assertEqual(sim.save_calls, 0)
        finally:
            sim.session_end()

    def test_fixed_allows_save_after_restore_when_prior_false(self):
        sim = RestorationSimulator()
        before = sample_before()
        restore_persisted_settings_fixed(sim, before)
        sim.save(False)
        self.assertEqual(sim.save_calls, 1)

    def test_prefix_exception_leaves_save_block_true(self):
        sim = RestorationSimulator()
        sim.restore_in_progress = True
        before = sample_before()
        if sim.has_app_settings:
            sim.restore_in_progress = True
        sim.apply_snapshot(before)
        sim.raise_on_restore = True
        with self.assertRaises(RuntimeError):
            sim.invoke_restore_fields()
        self.assertTrue(sim.restore_in_progress)

    def test_prepared_baseline_deterministic_failures(self):
        failures = []
        sim = RestorationSimulator()
        sim.restore_in_progress = True
        before = sample_before()
        restore_persisted_settings_prefix(sim, before)
        if not sim.restore_in_progress:
            failures.append("nested-save-block-not-preserved")
        sim2 = RestorationSimulator()
        before2 = sample_before(tec_depth="45")
        sim2.dom["tecDepth"] = "999"
        if sim2.has_app_settings:
            sim2.restore_in_progress = True
        sim2.apply_snapshot(before2)
        sim2.invoke_restore_fields()
        sim2.dom["tecDepth"] = "999"
        sim2.schedule_debounced_save()
        sim2.restore_in_progress = False
        sim2.tick(SETTINGS_SAVE_DEBOUNCE_MS)
        if json.loads(sim2.local_storage["lspDiveSettings_v6"])["tecDepth"] == "999":
            failures.append("delayed-save-contract-violated")
        sim3 = RestorationSimulator()
        sim3.restore_in_progress = True
        sim3.apply_snapshot(before)
        sim3.raise_on_restore = True
        try:
            sim3.invoke_restore_fields()
        except RuntimeError:
            pass
        if sim3.restore_in_progress:
            failures.append("exception-cleanup-failure")
        self.assertEqual(
            failures,
            [
                "nested-save-block-not-preserved",
                "delayed-save-contract-violated",
                "exception-cleanup-failure",
            ],
        )


class ShellRestoreDebounceTests(unittest.TestCase):
    def test_shell_regression_waits_settings_debounce_contract(self):
        """Shell regression must reuse browser-trace restore session + debounce contract."""
        shell_src = (ROOT / "dev/ui_shell_results_regression.py").read_text(encoding="utf-8")
        restore_src = (ROOT / "dev/playwright_restore.py").read_text(encoding="utf-8")
        self.assertIn("restore_probe_state", shell_src)
        self.assertIn("SETTINGS_SAVE_DEBOUNCE_WAIT_MS", restore_src)
        self.assertIn("_restore_session_begin", restore_src)


class SuiteOrderRegressionTests(unittest.TestCase):
    def test_repeated_trace_then_shell(self):
        spec = ROOT / "docs/seven-lens-traces/cycle-08-shell-results.json"
        trace_out = _ephemeral_trace_output("temp")
        try:
            # The trace spec already repeats each trace in fresh contexts; this
            # test only needs one full trace process before the shell regression.
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/seven_lens_browser_trace.py"),
                    "--spec", str(spec),
                    "--output", str(trace_out),
                    "--case-id", "V4-UI-SHELL-NAV-PRESERVES-RESULTS",
                ],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            shell_proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "dev/ui_shell_results_regression.py"),
                    "--case-id", "V4-UI-SHELL-NAV-PRESERVES-RESULTS",
                ],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(shell_proc.returncode, 0, shell_proc.stdout + shell_proc.stderr)
            self.assertIn("[V4-UI-SHELL-NAV-PRESERVES-RESULTS]", shell_proc.stdout)
            self.assertNotIn("✗ [V4-UI-SHELL-NAV-PRESERVES-RESULTS]", shell_proc.stdout)
        finally:
            trace_out.unlink(missing_ok=True)

    def test_shell_then_trace(self):
        spec = ROOT / "docs/seven-lens-traces/cycle-08-shell-results.json"
        trace_out = _ephemeral_trace_output("temp2")
        try:
            shell_proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "dev/ui_shell_results_regression.py"),
                    "--case-id", "V4-UI-SHELL-NAV-PRESERVES-RESULTS",
                ],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(shell_proc.returncode, 0, shell_proc.stdout + shell_proc.stderr)
            trace_proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "tools/seven_lens_browser_trace.py"),
                    "--spec", str(spec),
                    "--output", str(trace_out),
                    "--case-id", "V4-UI-SHELL-NAV-PRESERVES-RESULTS",
                ],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(trace_proc.returncode, 0, trace_proc.stdout + trace_proc.stderr)
        finally:
            trace_out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
