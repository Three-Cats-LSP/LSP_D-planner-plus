from __future__ import annotations

import unittest
from pathlib import Path

from tools.seven_lens_browser_trace import (
    _CANONICAL_DEPTH_SELECTORS,
    _capture_is_finite,
    evaluate_assertion,
    validate_trace_spec,
)


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

    def test_restore_persisted_settings_uses_restore_fields(self):
        source = Path(__file__).resolve().parents[0].joinpath("seven_lens_browser_trace.py").read_text(encoding="utf-8")
        self.assertIn("appSettings._restoreFields", source)
        self.assertNotIn("_syncUiAfterRestore?.(JSON.parse(raw))", source)


if __name__ == "__main__":
    unittest.main()
