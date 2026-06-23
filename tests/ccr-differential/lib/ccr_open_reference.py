"""Open-source CCR reference planners for Abysner and Subsurface presets.

Used at golden-build time only. Implements Bühlmann ZHL-16C + GF with CCR
inspired inert loading (p_inert = P_amb - setpoint - WV) and preset-specific
water vapour / ascent integration aligned with LSP engine presets.
"""
from __future__ import annotations

import math
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Knowledge Base"))

from subsurface_engine import (  # noqa: E402
    DecoState,
    add_cns,
    add_otu,
    tissue_tolerance_calc,
)

PRESETS = {
    "abysner": {
        "engine": "Abysner",
        "engineVersion": "open-reference",
        "waterVaporBar": 0.0627,
        "decoAscentOverride": None,
        "provenance": {
            "source": "open-reference-planner",
            "note": "ZHL-16C CCR reference with Abysner preset (WV 0.0627, Schreiner, fixture rates)",
            "repository": "https://github.com/NeoTech-Software/Abysner",
        },
    },
    "subsurface": {
        "engine": "Subsurface",
        "engineVersion": "open-reference",
        "waterVaporBar": 0.0627,
        "decoAscentOverride": 6.0,
        "provenance": {
            "source": "open-reference-planner",
            "note": "ZHL-16C CCR reference with Subsurface preset (WV 0.0627, 9/6/3 ascent, whole-minute stops)",
            "repository": "https://github.com/subsurface/subsurface",
        },
    },
}


def _factor(period_s: float, ci: int, gas: str) -> float:
    from subsurface_engine import He_f1s, He_hl, LN2_60, N2_f1s, N2_hl

    if period_s == 1:
        return N2_f1s[ci] if gas == "N2" else He_f1s[ci]
    hl = N2_hl[ci] if gas == "N2" else He_hl[ci]
    return 1.0 - math.exp(-period_s * LN2_60 / hl)


def add_ccr_segment(
    ds: DecoState,
    pressure: float,
    o2_dil: float,
    he_dil: float,
    setpoint_bar: float,
    wv: float,
    period_s: float,
) -> None:
    n2_frac = max(0.0, 1.0 - o2_dil - he_dil)
    he_frac = max(0.0, he_dil)
    inert_sum = n2_frac + he_frac
    if inert_sum <= 0:
        inert_sum = 1e-9
    p_inert = max(0.0, pressure - setpoint_bar - wv)
    pn2_ins = p_inert * (n2_frac / inert_sum)
    phe_ins = p_inert * (he_frac / inert_sum)
    for ci in range(16):
        pn2_over = pn2_ins - ds.tissue_n2[ci]
        phe_over = phe_ins - ds.tissue_he[ci]
        ds.tissue_n2[ci] += pn2_over * _factor(period_s, ci, "N2")
        ds.tissue_he[ci] += phe_over * _factor(period_s, ci, "HE")
        ds.inertgas[ci] = ds.tissue_n2[ci] + ds.tissue_he[ci]


def depth_to_bar(depth_m: float, surface_bar: float, wcm: float) -> float:
    return surface_bar + depth_m / wcm


def bar_to_depth(pressure_bar: float, surface_bar: float, wcm: float) -> float:
    return max(0.0, (pressure_bar - surface_bar) * wcm)


def deco_allowed_depth_m(ceiling_bar: float, surface_bar: float, wcm: float, step_m: float) -> float:
    raw_m = bar_to_depth(ceiling_bar, surface_bar, wcm)
    return math.ceil(raw_m / step_m) * step_m


def _asc_segment(
    ds: DecoState,
    depth_from: float,
    depth_to: float,
    rate_m_min: float,
    surface_bar: float,
    wcm: float,
    o2_dil: float,
    he_dil: float,
    setpoint: float,
    wv: float,
    cns: float,
    otu: float,
) -> tuple[int, float, float]:
    dist = depth_from - depth_to
    asc_s = max(1, int(math.ceil(dist / rate_m_min * 60)))
    for t in range(asc_s):
        frac = (t + 1) / asc_s
        d = depth_from - frac * dist
        p = depth_to_bar(d, surface_bar, wcm)
        add_ccr_segment(ds, p, o2_dil, he_dil, setpoint, wv, 1)
        cns = add_cns(cns, setpoint, 1 / 60.0)
        otu = add_otu(otu, setpoint, 1 / 60.0)
    return asc_s, cns, otu


def plan_ccr(fixture: dict, preset_key: str) -> dict:
    preset = PRESETS[preset_key]
    env = fixture.get("environment", {})
    dec = fixture.get("decompression", {})
    rates = fixture.get("ratesMPerMin", {})
    rnd = fixture.get("rounding", {})
    circuit = fixture.get("circuit", {})
    sp = circuit.get("setpointsBar", {})
    dil = circuit.get("diluent", {})
    o2_dil = float(dil.get("o2", 0.21))
    he_dil = float(dil.get("he", 0.0))
    wcm = float(env.get("waterColumnMPerBar", 10.0))
    alt_m = float(env.get("altitudeM", 0))
    surface_bar = float(env.get("surfacePressureBar", 1.01325))
    if alt_m > 0:
        surface_bar = 1.01325 * math.exp(-alt_m / 8434.5)
    wv = preset["waterVaporBar"]
    gf_low = float(dec.get("gfLow", 30)) / 100.0
    gf_high = float(dec.get("gfHigh", 70)) / 100.0
    step_m = float(dec.get("stepM", 3))
    last_stop_m = float(dec.get("lastStopM", 3))
    min_stop_s = int(rnd.get("minimumStopSec", 60))
    desc_rate = float(rates.get("descent", 20))
    deep_asc = float(rates.get("deepAscent", 9))
    deco_asc = float(preset["decoAscentOverride"] or rates.get("decoAscent", 9))
    shallow_asc = float(rates.get("surfaceAscent", 3))
    sp_descent = float(sp.get("descent", 0.7))
    sp_bottom = float(sp.get("bottom", 1.3))
    sp_deco = float(sp.get("deco", sp_bottom))

    levels = fixture["profile"]["levels"]
    target_m = float(levels[0]["depthM"])
    bottom_min = float(levels[0]["timeMin"])

    ds = DecoState()
    ds.clear(surface_bar)
    cns = 0.0
    otu = 0.0
    run_time_s = 0
    decozone_m = None

    desc_s = max(1, int(round(target_m / desc_rate * 60)))
    for t in range(desc_s):
        frac = (t + 0.5) / desc_s
        p = depth_to_bar(target_m * frac, surface_bar, wcm)
        add_ccr_segment(ds, p, o2_dil, he_dil, sp_descent, wv, 1)
        cns = add_cns(cns, sp_descent, 1 / 60.0)
        otu = add_otu(otu, sp_descent, 1 / 60.0)
    run_time_s += desc_s

    p_bot = depth_to_bar(target_m, surface_bar, wcm)
    bottom_s = max(1, int(round(bottom_min * 60)))
    for t in range(bottom_s):
        add_ccr_segment(ds, p_bot, o2_dil, he_dil, sp_bottom, wv, 1)
        cns = add_cns(cns, sp_bottom, 1 / 60.0)
        otu = add_otu(otu, sp_bottom, 1 / 60.0)
        if decozone_m is None and t % 30 == 0:
            snap = deepcopy(ds)
            c = tissue_tolerance_calc(snap, surface_bar, 1.0, 1.0)
            if c > surface_bar + 0.001:
                decozone_m = bar_to_depth(c, surface_bar, wcm)
    if decozone_m is None:
        snap = deepcopy(ds)
        c = tissue_tolerance_calc(snap, surface_bar, 1.0, 1.0)
        if c > surface_bar + 0.001:
            decozone_m = bar_to_depth(c, surface_bar, wcm)
    run_time_s += bottom_s

    tts_start_s = run_time_s
    first_stop_m = None
    stops: list[dict] = []
    depth_m = target_m
    in_deco = False
    setpoint = sp_deco

    while depth_m > 0.01:
        ds_pre = deepcopy(ds)
        ceil_bar = tissue_tolerance_calc(ds_pre, surface_bar, gf_low, gf_high)
        ceil_m = deco_allowed_depth_m(ceil_bar, surface_bar, wcm, step_m)

        if depth_m <= last_stop_m:
            candidate = 0.0
        elif depth_m - step_m < last_stop_m:
            candidate = last_stop_m
        else:
            candidate = math.floor((depth_m - step_m) / step_m) * step_m

        if ceil_m > candidate and ceil_m <= depth_m + 1e-6:
            if first_stop_m is None:
                first_stop_m = depth_m
            in_deco = True
            p_here = depth_to_bar(depth_m, surface_bar, wcm)
            stop_s = 0
            while True:
                chunk = 60 if min_stop_s >= 60 else min_stop_s
                for _ in range(chunk):
                    add_ccr_segment(ds, p_here, o2_dil, he_dil, setpoint, wv, 1)
                    cns = add_cns(cns, setpoint, 1 / 60.0)
                    otu = add_otu(otu, setpoint, 1 / 60.0)
                run_time_s += chunk
                stop_s += chunk
                snap = deepcopy(ds)
                nc_bar = tissue_tolerance_calc(snap, surface_bar, gf_low, gf_high)
                nc_m = deco_allowed_depth_m(nc_bar, surface_bar, wcm, step_m)
                if nc_m <= candidate + 1e-6 and stop_s >= min_stop_s:
                    break
                if stop_s > 600 * 60:
                    break
            stops.append({"depthM": depth_m, "durationMin": stop_s / 60.0, "gasLabel": "loop", "ppO2": setpoint})
            if candidate <= 0.01:
                s, cns, otu = _asc_segment(
                    ds, depth_m, 0.0, shallow_asc, surface_bar, wcm,
                    o2_dil, he_dil, setpoint, wv, cns, otu,
                )
                run_time_s += s
                depth_m = 0.0
                break
            rate = shallow_asc if depth_m <= last_stop_m + 1e-6 else deco_asc
            s, cns, otu = _asc_segment(
                ds, depth_m, candidate, rate, surface_bar, wcm,
                o2_dil, he_dil, setpoint, wv, cns, otu,
            )
            run_time_s += s
            depth_m = candidate
            continue

        if candidate <= 0.01:
            rate = shallow_asc if in_deco else deep_asc
            s, cns, otu = _asc_segment(
                ds, depth_m, 0.0, rate, surface_bar, wcm,
                o2_dil, he_dil, setpoint, wv, cns, otu,
            )
            run_time_s += s
            depth_m = 0.0
            break

        rate = deep_asc if not in_deco else (shallow_asc if candidate <= last_stop_m else deco_asc)
        s, cns, otu = _asc_segment(
            ds, depth_m, candidate, rate, surface_bar, wcm,
            o2_dil, he_dil, setpoint, wv, cns, otu,
        )
        run_time_s += s
        depth_m = candidate

        if depth_m <= 0.01:
            break
        snap = deepcopy(ds)
        cb2 = tissue_tolerance_calc(snap, surface_bar, gf_low, gf_high)
        cm2 = deco_allowed_depth_m(cb2, surface_bar, wcm, step_m)
        if cm2 > depth_m + 1e-6:
            if first_stop_m is None:
                first_stop_m = depth_m
            in_deco = True
            p_here = depth_to_bar(depth_m, surface_bar, wcm)
            next_c = (
                0.0 if depth_m <= last_stop_m
                else last_stop_m if depth_m - step_m < last_stop_m
                else math.floor((depth_m - step_m) / step_m) * step_m
            )
            stop_s = 0
            while True:
                chunk = 60 if min_stop_s >= 60 else min_stop_s
                for _ in range(chunk):
                    add_ccr_segment(ds, p_here, o2_dil, he_dil, setpoint, wv, 1)
                    cns = add_cns(cns, setpoint, 1 / 60.0)
                    otu = add_otu(otu, setpoint, 1 / 60.0)
                run_time_s += chunk
                stop_s += chunk
                snap = deepcopy(ds)
                nc_bar = tissue_tolerance_calc(snap, surface_bar, gf_low, gf_high)
                nc_m = deco_allowed_depth_m(nc_bar, surface_bar, wcm, step_m)
                if nc_m <= next_c + 1e-6 and stop_s >= min_stop_s:
                    break
                if stop_s > 600 * 60:
                    break
            stops.append({"depthM": depth_m, "durationMin": stop_s / 60.0, "gasLabel": "loop", "ppO2": setpoint})

    tts_min = (run_time_s - tts_start_s) / 60.0
    rt_min = run_time_s / 60.0
    return {
        "engine": preset["engine"],
        "engineVersion": preset["engineVersion"],
        "scenarioId": fixture["id"],
        "provenance": dict(preset["provenance"]),
        "stops": stops,
        "summary": {
            "firstStopDepthM": first_stop_m if first_stop_m is not None else 0,
            "ttsMin": round(tts_min, 1),
            "runtimeMin": round(rt_min, 1),
            "cnsPercent": round(cns, 1),
            "otu": round(otu, 1),
            "decozoneStartM": round(decozone_m, 1) if decozone_m else 0,
        },
        "gasSwitches": [],
        "tissuesN2": "not_available",
        "tissuesHe": "not_available",
    }


def normalize_open_golden(raw: dict, scenario_id: str) -> dict:
    out = dict(raw)
    out["scenarioId"] = scenario_id
    return out
