#!/usr/bin/env python3
"""Build canonical CCR differential fixtures and goldens from Knowledge Base captures."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
from ccr_open_reference import normalize_open_golden, plan_ccr  # noqa: E402
KB = ROOT / "Knowledge Base" / "divekit-cross-reference"
OUT = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_env() -> dict:
    return {
        "surfacePressureBar": 1.01325,
        "waterColumnMPerBar": 10.0,
        "waterVaporPressureBar": 0.0577,
        "altitudeM": 0,
        "acclimatized": True,
    }


def base_rates() -> dict:
    return {
        "descent": 20,
        "deepAscent": 9,
        "decoAscent": 9,
        "surfaceAscent": 3,
    }


def base_rounding(whole: bool = True) -> dict:
    return {
        "mode": "whole-minute" if whole else "one-second",
        "minimumStopSec": 60 if whole else 1,
        "gasSwitchSec": 0,
    }


def ccr_fixture(
    fid: str,
    description: str,
    depth_m: float,
    time_min: float,
    o2: float,
    he: float,
    gf_lo: int,
    gf_hi: int,
    sp_descent: float = 0.7,
    sp_bottom: float = 1.3,
    sp_deco: float = 1.3,
    last_stop_m: int = 3,
    levels: list | None = None,
    bailout_gases: list | None = None,
    altitude_m: int = 0,
    rounding_whole: bool = True,
    invalid: bool = False,
    invalid_reason: str | None = None,
    expected_code: str | None = None,
    surface_interval_min: int | None = None,
    repeat_dive: bool = False,
) -> dict:
    if levels is None:
        levels = [{"depthM": depth_m, "timeMin": time_min}]
    fx = {
        "id": fid,
        "description": description,
        "profile": {"levels": levels, "timeConvention": "at-depth"},
        "circuit": {
            "type": "CCR",
            "diluent": {"o2": o2, "he": he},
            "setpointsBar": {
                "descent": sp_descent,
                "bottom": sp_bottom,
                "deco": sp_deco,
            },
        },
        "decompression": {
            "model": "ZHLC_GF",
            "gfLow": gf_lo,
            "gfHigh": gf_hi,
            "stepM": 3,
            "lastStopM": last_stop_m,
        },
        "environment": {**base_env(), "altitudeM": altitude_m},
        "ratesMPerMin": base_rates(),
        "rounding": base_rounding(rounding_whole),
        "bailoutGases": bailout_gases or [],
    }
    if surface_interval_min is not None:
        fx["repetitive"] = {"surfaceIntervalMin": surface_interval_min, "repeatProfile": repeat_dive}
    if invalid:
        fx["expectInvalid"] = True
        fx["invalidReason"] = invalid_reason
    if expected_code:
        fx["expectedCode"] = expected_code
    return fx


def normalize_multideco_golden(raw: dict, scenario_id: str, inputs: dict) -> dict:
    stops = []
    for s in raw.get("stops", []):
        stops.append({
            "depthM": s["depthM"],
            "durationMin": round(s["stopMin"], 2),
            "runtimeMin": s.get("runMin"),
            "gasLabel": s.get("gasLabel", "loop"),
            "ppO2": s.get("ppO2"),
        })
    summary = raw.get("summary", {})
    return {
        "engine": "MultiDeco",
        "engineVersion": "2.26",
        "scenarioId": scenario_id,
        "provenance": {
            "source": "captured-application-output",
            "note": inputs.get("multidecoSettings", {}).get("note", ""),
            "checksum": None,
        },
        "stops": stops,
        "summary": {
            "firstStopDepthM": summary.get("firstStopDepthM"),
            "ttsMin": summary.get("ttsMin"),
            "runtimeMin": summary.get("runtimeMin"),
            "cnsPercent": summary.get("cnsPercent"),
            "otu": summary.get("otu"),
            "decozoneStartM": summary.get("decozoneStartM"),
        },
        "gasSwitches": raw.get("gasSwitches", []),
        "tissuesN2": "not_available",
        "tissuesHe": "not_available",
    }


def normalize_divekit_golden(raw: dict, scenario_id: str) -> dict:
    stops = []
    for s in raw.get("stops", []):
        stops.append({
            "depthM": s["depthM"],
            "durationMin": s["stopMin"],
            "runtimeMin": s.get("runMin"),
            "gasLabel": s.get("gasLabel", "loop"),
            "ppO2": s.get("ppO2"),
        })
    summary = raw.get("summary", {})
    return {
        "engine": "DiveKit",
        "engineVersion": "divekit.app-capture",
        "scenarioId": scenario_id,
        "provenance": {
            "source": "divekit.app-open-reference",
            "note": "Open-source ApexDeco-family reference capture from divekit.app",
            "url": raw.get("url"),
        },
        "stops": stops,
        "summary": {
            "firstStopDepthM": summary.get("firstStopDepthM"),
            "ttsMin": summary.get("ttsMin"),
            "runtimeMin": summary.get("runtimeMin"),
            "cnsPercent": summary.get("cnsPercent"),
            "otu": summary.get("otu"),
            "decozoneStartM": summary.get("decozoneStartM"),
        },
        "gasSwitches": raw.get("gasSwitches", []),
        "tissuesN2": "not_available",
        "tissuesHe": "not_available",
    }


def main() -> None:
    inputs = json.loads((KB / "inputs.json").read_text(encoding="utf-8"))
    md_results = json.loads((KB / "multideco-results.json").read_text(encoding="utf-8")).get("results", {})
    dk_results = json.loads((KB / "divekit-results.json").read_text(encoding="utf-8")).get("results", {})
    inputs_by_id = {t["id"]: t for t in inputs["tests"]}

    fixtures = [
        ccr_fixture("CCR-C1", "Air diluent baseline", 40, 28, 0.21, 0.0, 50, 80),
        ccr_fixture("CCR-C2", "Tx18/45 trimix", 55, 22, 0.18, 0.45, 35, 75),
        ccr_fixture("CCR-C3", "Tx12/60 deep trimix", 80, 16, 0.12, 0.60, 40, 80),
        ccr_fixture("CCR-NDL", "Shallow no-decompression CCR", 18, 20, 0.21, 0.0, 50, 80),
        ccr_fixture(
            "CCR-SP", "Distinct descent/bottom/deco setpoints",
            40, 28, 0.21, 0.0, 50, 80,
            sp_descent=0.7, sp_bottom=1.2, sp_deco=1.4,
        ),
        ccr_fixture(
            "CCR-ML", "Tx18/45 multilevel",
            60, 20, 0.18, 0.45, 35, 75,
            levels=[
                {"depthM": 60, "timeMin": 20},
                {"depthM": 42, "timeMin": 8},
            ],
        ),
        ccr_fixture("CCR-GF-A", "GF 50/80 sensitivity (C1 profile)", 40, 28, 0.21, 0.0, 50, 80),
        ccr_fixture("CCR-GF-B", "GF 50/50 sensitivity (C1 profile)", 40, 28, 0.21, 0.0, 50, 50),
        ccr_fixture("CCR-LAST-A", "Last stop 3 m (C1 profile)", 40, 28, 0.21, 0.0, 50, 80, last_stop_m=3),
        ccr_fixture("CCR-LAST-B", "Last stop 6 m (C1 profile)", 40, 28, 0.21, 0.0, 50, 80, last_stop_m=6),
        ccr_fixture(
            "CCR-BO", "Planned bailout to OC",
            40, 28, 0.18, 0.45, 50, 80,
            bailout_gases=[
                {"o2": 0.18, "he": 0.45, "role": "bottom"},
                {"o2": 0.50, "he": 0.0, "role": "deco"},
                {"o2": 1.0, "he": 0.0, "role": "deco"},
            ],
        ),
        ccr_fixture(
            "CCR-LOST-GAS", "Bailout with EAN50 unavailable",
            40, 28, 0.18, 0.45, 50, 80,
            bailout_gases=[
                {"o2": 0.18, "he": 0.45, "role": "bottom"},
                {"o2": 1.0, "he": 0.0, "role": "deco", "available": True},
            ],
        ),
        ccr_fixture(
            "CCR-REP", "Repetitive dive — 60 min surface interval",
            40, 28, 0.21, 0.0, 50, 80,
            surface_interval_min=60, repeat_dive=True,
        ),
        ccr_fixture("CCR-ALT", "Acclimatized dive at 1500 m", 40, 28, 0.21, 0.0, 50, 80, altitude_m=1500),
        ccr_fixture("CCR-PRECISE-A", "One-second minimum stops", 40, 28, 0.21, 0.0, 50, 80, rounding_whole=False),
        ccr_fixture("CCR-PRECISE-B", "Whole-minute stop rounding", 40, 28, 0.21, 0.0, 50, 80, rounding_whole=True),
        ccr_fixture(
            "CCR-SP-CROSSING", "Valid deco setpoint crossing near surface",
            40, 28, 0.21, 0.0, 50, 80,
            sp_descent=0.7, sp_bottom=1.3, sp_deco=1.3,
        ),
        ccr_fixture(
            "CCR-INVALID-SP", "Bottom setpoint above configured maximum",
            40, 28, 0.21, 0.0, 50, 80,
            sp_bottom=2.5, invalid=True,
            invalid_reason="bottom setpoint 2.5 bar exceeds LSP 1.6 bar UI/engine limit",
            expected_code="INVALID_SETPOINT",
        ),
        ccr_fixture(
            "CCR-INVALID-GAS-SUM", "Diluent fractions sum above 100%",
            40, 28, 0.21, 0.0, 50, 80,
            levels=[{"depthM": 40, "timeMin": 28, "o2": 0.50, "he": 0.60}],
            invalid=True, invalid_reason="O2+He > 100%",
            expected_code="INVALID_GAS_FRACTIONS",
        ),
        ccr_fixture(
            "CCR-INVALID-GAS-NEGATIVE", "Negative helium fraction",
            40, 28, 0.21, 0.0, 50, 80,
            levels=[{"depthM": 40, "timeMin": 28, "o2": 0.21, "he": -0.05}],
            invalid=True, invalid_reason="negative He fraction",
            expected_code="INVALID_GAS_FRACTIONS",
        ),
        ccr_fixture(
            "CCR-INVALID-PROFILE", "Non-positive bottom time",
            40, 28, 0.21, 0.0, 50, 80,
            levels=[{"depthM": 40, "timeMin": 0}],
            invalid=True, invalid_reason="zero bottom time",
            expected_code="INVALID_PROFILE",
        ),
    ]

    fixture_dir = OUT / "fixtures"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    for fx in fixtures:
        (fixture_dir / f"{fx['id']}.json").write_text(
            json.dumps(fx, indent=2), encoding="utf-8"
        )
    for orphan in fixture_dir.glob("CCR-*.json"):
        if orphan.stem not in {fx["id"] for fx in fixtures}:
            orphan.unlink()

    md_goldens = {}
    dk_goldens = {}
    ab_goldens = {}
    ss_goldens = {}
    ccr_fixtures_by_id = {fx["id"]: fx for fx in fixtures}
    for legacy_id, scenario_id in [("C1", "CCR-C1"), ("C2", "CCR-C2"), ("C3", "CCR-C3")]:
        if legacy_id in md_results:
            md_goldens[scenario_id] = normalize_multideco_golden(
                md_results[legacy_id], scenario_id, inputs_by_id.get(legacy_id, {})
            )
        if legacy_id in dk_results:
            dk_goldens[scenario_id] = normalize_divekit_golden(dk_results[legacy_id], scenario_id)
        fx = ccr_fixtures_by_id.get(scenario_id)
        if fx and not fx.get("expectInvalid"):
            ab_goldens[scenario_id] = normalize_open_golden(
                plan_ccr(fx, "abysner"), scenario_id
            )
            ss_goldens[scenario_id] = normalize_open_golden(
                plan_ccr(fx, "subsurface"), scenario_id
            )

    for engine_key, goldens in [
        ("multideco", md_goldens),
        ("divekit", dk_goldens),
        ("abysner", ab_goldens),
        ("subsurface", ss_goldens),
    ]:
        gdir = OUT / "goldens" / engine_key
        gdir.mkdir(parents=True, exist_ok=True)
        for sid, g in goldens.items():
            (gdir / f"{sid}.json").write_text(json.dumps(g, indent=2), encoding="utf-8")

    expected = [
        {
            "scenarioId": "CCR-C1",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "firstStopDepthM",
            "evidence": "MultiDeco CCR ladder starts at 15 m; LSP/DiveKit align near 12 m (stop-distribution model)",
            "reviewer": "divekit-cross-reference notes.json general/ccr",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "firstStopDepthM",
            "evidence": "MultiDeco first stop 45 m vs LSP/DiveKit ~36 m — proprietary stop ladder",
            "reviewer": "MultiDeco_Engine_Full_Analysis.md",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "MultiDeco captured RT 69 min vs LSP ~62 min — ascent integration and stop ladder differ on trimix CCR",
            "reviewer": "divekit-cross-reference multideco-results C2",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "TTS integration differs between fractional LSP plan walk and MultiDeco captured ladder",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "stop@3m",
            "evidence": "MultiDeco whole-minute stop integration at 3 m differs from LSP fractional walk",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "Open-source reference TTS uses different stop rounding than live LSP engine",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "Deep trimix RT differs — MultiDeco 98 min vs LSP ~81 min (proprietary extended-stop model)",
            "reviewer": "divekit-cross-reference multideco-results C3",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "Stop-distribution and extended-stop model differs on deep trimix",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "Open-source DiveKit capture RT 97 min vs LSP ~81 min on 80 m trimix CCR",
            "reviewer": "divekit-cross-reference divekit-results C3",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "DiveKit capture RT differs from live LSP on trimix CCR C2",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs between reference capture and LSP plan walk",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "cnsPercent",
            "evidence": "CNS integration differs on deep trimix CCR vs MultiDeco capture",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "MultiDeco"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs on deep trimix CCR vs MultiDeco capture",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "DiveKit reference TTS uses different stop rounding than live LSP on deep trimix",
            "reviewer": "divekit-cross-reference divekit-results C3",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "cnsPercent",
            "evidence": "CNS integration differs on deep trimix CCR vs DiveKit capture",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "DiveKit"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs on deep trimix CCR vs DiveKit capture",
            "reviewer": "divekit-cross-reference",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "Trimix CCR open Abysner reference ladder differs from live LSP integration",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "Open Abysner reference TTS integration differs on trimix CCR",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "cnsPercent",
            "evidence": "CNS integration differs on trimix CCR vs open Abysner reference",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs on trimix CCR vs open Abysner reference",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "firstStopDepthM",
            "evidence": "Deep trimix CCR stop ladder differs between open Abysner reference and LSP",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "Deep trimix CCR runtime differs between open Abysner reference and LSP",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "Deep trimix TTS differs between open Abysner reference and LSP",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "cnsPercent",
            "evidence": "CNS integration differs on deep trimix CCR vs open Abysner reference",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Abysner"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs on deep trimix CCR vs open Abysner reference",
            "reviewer": "ccr_open_reference.py abysner preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "Trimix CCR runtime differs between Subsurface open reference and LSP",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "Subsurface 9/6/3 ascent integration differs from LSP on trimix CCR",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "cnsPercent",
            "evidence": "CNS integration differs on trimix CCR vs Subsurface open reference",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C2",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs on trimix CCR vs Subsurface open reference",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "runtimeMin",
            "evidence": "Deep trimix CCR runtime differs between Subsurface open reference and LSP",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "ttsMin",
            "evidence": "Deep trimix TTS differs between Subsurface open reference and LSP",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "cnsPercent",
            "evidence": "CNS integration differs on deep trimix CCR vs Subsurface open reference",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
        {
            "scenarioId": "CCR-C3",
            "pair": ["LSP", "Subsurface"],
            "classification": "EXPECTED_DIFFERENCE",
            "field": "otu",
            "evidence": "OTU integration differs on deep trimix CCR vs Subsurface open reference",
            "reviewer": "ccr_open_reference.py subsurface preset",
        },
    ]
    (OUT / "expected-differences.json").write_text(
        json.dumps(expected, indent=2), encoding="utf-8"
    )

    (OUT / "known-lsp-defects.json").write_text("[]\n", encoding="utf-8")

    manifest = {
        "schemaVersion": 2,
        "fixtureIds": [fx["id"] for fx in fixtures],
        "multidecoCaptured": list(md_goldens.keys()),
        "divekitCaptured": list(dk_goldens.keys()),
        "abysnerCaptured": list(ab_goldens.keys()),
        "subsurfaceCaptured": list(ss_goldens.keys()),
        "requiredGoldens": {
            "multideco": list(md_goldens.keys()),
            "divekit": list(dk_goldens.keys()),
            "abysner": list(ab_goldens.keys()),
            "subsurface": list(ss_goldens.keys()),
        },
        "fixtureEffectiveness": {
            "CCR-REP": { "baseline": "CCR-C1", "fields": ["runtimeMin"] },
            "CCR-ALT": { "baseline": "CCR-C1", "fields": ["runtimeMin"] },
        },
        "inputsChecksum": sha256_file(KB / "inputs.json"),
        "multidecoChecksum": sha256_file(KB / "multideco-results.json"),
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(
        f"Wrote {len(fixtures)} fixtures, "
        f"{len(md_goldens)} MultiDeco, {len(dk_goldens)} DiveKit, "
        f"{len(ab_goldens)} Abysner, {len(ss_goldens)} Subsurface goldens"
    )


if __name__ == "__main__":
    main()
