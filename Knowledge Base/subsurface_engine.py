"""
Subsurface deco engine — Python port of core/deco.cpp + planner logic.
Faithful to the C++ source: same ZHL-16C coefficients, same GF interpolation,
same WV=0.0627 bar. Planner uses MultiDeco-style ascent rates:
  9 m/min to first stop (deep), 6 m/min between stops, 3 m/min last 3m.

Author: ported for LSP cross-reference study, June 2026.
"""

import math
import copy

# ─── ZHL-16C Coefficients (from deco.cpp) ──────────────────────────────────

N2_a = [1.1696, 1.0, 0.8618, 0.7562, 0.62, 0.5043, 0.441, 0.4,
        0.375, 0.35, 0.3295, 0.3065, 0.2835, 0.261, 0.248, 0.2327]

N2_b = [0.5578, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.8910,
        0.9092, 0.9222, 0.9319, 0.9403, 0.9477, 0.9544, 0.9602, 0.9653]

N2_hl = [5.0, 8.0, 12.5, 18.5, 27.0, 38.3, 54.3, 77.0,
         109.0, 146.0, 187.0, 239.0, 305.0, 390.0, 498.0, 635.0]

He_a = [1.6189, 1.383, 1.1919, 1.0458, 0.922, 0.8205, 0.7305, 0.6502,
        0.595, 0.5545, 0.5333, 0.5189, 0.5181, 0.5176, 0.5172, 0.5119]

He_b = [0.4770, 0.5747, 0.6527, 0.7223, 0.7582, 0.7957, 0.8279, 0.8553,
        0.8757, 0.8903, 0.8997, 0.9073, 0.9122, 0.9171, 0.9217, 0.9267]

He_hl = [1.88, 3.02, 4.72, 6.99, 10.21, 14.48, 20.53, 29.11,
         41.20, 55.19, 70.69, 90.34, 115.29, 147.42, 188.24, 240.03]

N2_f1s = [2.30782347297664e-3, 1.44301447809736e-3, 9.23769302935806e-4, 6.24261986779007e-4,
           4.27777107246730e-4, 3.01585140931371e-4, 2.12729727268379e-4, 1.50020603047807e-4,
           1.05980191127841e-4, 7.91232600646508e-5, 6.17759153688224e-5, 4.83354552742732e-5,
           3.78761777920511e-5, 2.96212356654113e-5, 2.31974277413727e-5, 1.81926738960225e-5]

He_f1s = [6.12608039419837e-3, 3.81800836683133e-3, 2.44456078654209e-3, 1.65134647076792e-3,
           1.13084424730725e-3, 7.97503165599123e-4, 5.62552521860549e-4, 3.96776399429366e-4,
           2.80360036664540e-4, 2.09299583354805e-4, 1.63410794820518e-4, 1.27869320250551e-4,
           1.00198406028040e-4, 7.83611475491108e-5, 6.13689891868496e-5, 4.81280465299827e-5]

# ─── Constants ──────────────────────────────────────────────────────────────

WV        = 0.0627          # Bühlmann water vapour (Rq=1.0)
N2_IN_AIR = 0.7902
LN2_60    = math.log(2) / 60.0

# ─── deco_state ─────────────────────────────────────────────────────────────

class DecoState:
    def __init__(self):
        self.tissue_n2  = [0.0] * 16
        self.tissue_he  = [0.0] * 16
        self.inertgas   = [0.0] * 16
        self.a_blend    = [0.0] * 16
        self.b_blend    = [0.0] * 16
        self.tolerated  = [0.0] * 16
        self.gf_low_pressure = 0.0
        self.guiding_tissue  = 0
        self.icd_warning     = False

    def clear(self, surface_bar, gf_low_position_min=1.0):
        init_n2 = (surface_bar - WV) * N2_IN_AIR
        for ci in range(16):
            self.tissue_n2[ci] = init_n2
            self.tissue_he[ci] = 0.0
            self.inertgas[ci]  = init_n2
        self.gf_low_pressure = surface_bar + gf_low_position_min
        self.guiding_tissue  = 0
        self.icd_warning     = False

    def copy(self):
        return copy.deepcopy(self)


# ─── Core functions ──────────────────────────────────────────────────────────

def _factor(period_s, ci, gas):
    if period_s == 1:
        return N2_f1s[ci] if gas == 'N2' else He_f1s[ci]
    hl = N2_hl[ci] if gas == 'N2' else He_hl[ci]
    return 1.0 - math.exp(-period_s * LN2_60 / hl)


def add_segment(ds, pressure, o2_frac, he_frac, period_s):
    n2_frac = 1.0 - o2_frac - he_frac
    p_alv   = pressure - WV
    pn2_ins = p_alv * n2_frac
    phe_ins = p_alv * he_frac
    for ci in range(16):
        pn2_over = pn2_ins - ds.tissue_n2[ci]
        phe_over = phe_ins - ds.tissue_he[ci]
        ds.tissue_n2[ci] += pn2_over * _factor(period_s, ci, 'N2')
        ds.tissue_he[ci] += phe_over * _factor(period_s, ci, 'HE')
        ds.inertgas[ci]   = ds.tissue_n2[ci] + ds.tissue_he[ci]


def tissue_tolerance_calc(ds, surface_bar, gf_low, gf_high):
    """GF-modified Bühlmann ceiling. Direct port of deco.cpp tissue_tolerance_calc()."""
    for ci in range(16):
        if ds.inertgas[ci] > 0:
            ds.a_blend[ci] = (N2_a[ci]*ds.tissue_n2[ci] + He_a[ci]*ds.tissue_he[ci]) / ds.inertgas[ci]
            ds.b_blend[ci] = (N2_b[ci]*ds.tissue_n2[ci] + He_b[ci]*ds.tissue_he[ci]) / ds.inertgas[ci]
        else:
            ds.a_blend[ci] = N2_a[ci]; ds.b_blend[ci] = N2_b[ci]

    lowest_ceiling = 0.0
    for ci in range(16):
        A, B, P = ds.a_blend[ci], ds.b_blend[ci], ds.inertgas[ci]
        c = (B*P - gf_low*A*B) / ((1.0-B)*gf_low + B)
        if c > lowest_ceiling:
            lowest_ceiling = c
        if lowest_ceiling > ds.gf_low_pressure:
            ds.gf_low_pressure = lowest_ceiling

    ret = 0.0; guiding = 0
    gfl_p = ds.gf_low_pressure
    for ci in range(16):
        A, B, P = ds.a_blend[ci], ds.b_blend[ci], ds.inertgas[ci]
        at_surf  = (surface_bar/B + A - surface_bar)*gf_high + surface_bar
        at_gflow = (gfl_p/B + A - gfl_p)*gf_low + gfl_p
        if at_surf < at_gflow:
            num = (-A*B*(gf_high*gfl_p - gf_low*surface_bar)
                   - (1.0-B)*(gf_high-gf_low)*gfl_p*surface_bar
                   + B*(gfl_p-surface_bar)*P)
            den = (-A*B*(gf_high-gf_low)
                   + (1.0-B)*(gf_low*gfl_p - gf_high*surface_bar)
                   + B*(gfl_p-surface_bar))
            tol = num/den if den != 0 else ret
        else:
            tol = ret
        ds.tolerated[ci] = tol
        if tol >= ret:
            guiding = ci; ret = tol
    ds.guiding_tissue = guiding
    return ret


def depth_to_bar(depth_m, surface_bar, salt=True):
    """rho*g*h/1e5 + surface. rho=1025 (salt) or 1000 (fresh) kg/m3."""
    rho = 1025.0 if salt else 1000.0
    return surface_bar + depth_m * rho * 9.80665 / 1e5


def bar_to_depth(pressure_bar, surface_bar, salt=True):
    rho = 1025.0 if salt else 1000.0
    delta = max(0.0, pressure_bar - surface_bar)
    return delta * 1e5 / (rho * 9.80665)


def deco_allowed_depth_m(ceiling_bar, surface_bar, salt=True):
    """Snap ceiling to 3m grid (ceiling rounded UP)."""
    raw_m = bar_to_depth(ceiling_bar, surface_bar, salt)
    return math.ceil(raw_m / 3.0) * 3.0


# ─── CNS / OTU ──────────────────────────────────────────────────────────────

CNS_TABLE = [(0.50,9999),(0.60,720),(0.70,570),(0.80,450),(0.90,360),
             (1.00,270),(1.10,240),(1.20,210),(1.30,180),(1.40,150),
             (1.50,120),(1.60,45),(1.65,45)]

def cns_half_time(ppo2):
    if ppo2 <= 0.5: return 9999
    for lim, ht in CNS_TABLE:
        if ppo2 <= lim: return ht
    return 45

def add_cns(cns, ppo2, dt_min):
    ht = cns_half_time(ppo2)
    return cns if ht >= 9999 else cns + (dt_min/ht)*100.0

def add_otu(otu, ppo2, dt_min):
    if ppo2 <= 0.5: return otu
    return otu + dt_min * ((ppo2-0.5)/0.5)**0.833


# ─── Planner ─────────────────────────────────────────────────────────────────

def _asc_segment(ds, depth_from, depth_to, rate_m_min, surface_bar, salt, o2, he, cns, otu):
    """Simulate linear ascent from depth_from to depth_to at rate_m_min. Returns updated cns,otu."""
    dist   = depth_from - depth_to
    asc_s  = max(1, int(math.ceil(dist / rate_m_min * 60)))
    for t in range(asc_s):
        frac  = (t+1)/asc_s
        d     = depth_from - frac*dist
        p     = depth_to_bar(d, surface_bar, salt)
        add_segment(ds, p, o2, he, 1)
        ppo2  = p * o2
        cns   = add_cns(cns, ppo2, 1/60.0)
        otu   = add_otu(otu, ppo2, 1/60.0)
    return asc_s, cns, otu


def run_dive(scenario, shared, verbose=False):
    dive      = scenario['dive']
    water     = dive.get('waterType','salt')
    salt      = (water == 'salt')
    gf_low    = dive.get('gfLow', 30) / 100.0
    gf_high   = dive.get('gfHigh', 70) / 100.0
    levels    = dive['levels']
    raw_gases = dive['gases']
    alt_m     = dive.get('altitudeM', 0)
    last_stop_m  = float(shared.get('lastStopDepth', 3))
    deco_step_m  = float(shared.get('decoStepSize', 3))
    min_deco_s   = shared.get('minDecoStopTimeSec', 60)
    switch_mod   = shared.get('switchGasAtMod', True)
    gas_switch_s = shared.get('gasSwitchTimeSec', 60)
    desc_rate    = float(shared.get('descentRate', 20))

    surface_bar = 1.01325 * math.exp(-alt_m / 8434.5)

    # Ascent rates: 9 m/min deep, 6 m/min between deco stops, 3 m/min last 3m
    DEEP_ASC    = 9.0
    DECO_ASC    = 6.0
    SHALLOW_ASC = 3.0

    def max_ppo2_for(o2):
        if o2 <= 0.22: return 1.4
        if o2 <= 0.50: return 1.6
        return 1.6

    gases = [(g['o2'], g['he'], max_ppo2_for(g['o2'])) for g in raw_gases]
    bottom_gas = gases[0]
    deco_gases = sorted(gases[1:], key=lambda g: g[0], reverse=True)
    all_gases  = [bottom_gas] + deco_gases

    def best_gas(depth_m):
        amb = depth_to_bar(depth_m, surface_bar, salt)
        best_i, best_o2 = 0, all_gases[0][0]
        for i, (o2, he, mpp) in enumerate(all_gases):
            if o2 > 0 and amb <= mpp/o2 + 1e-9 and o2 > best_o2:
                best_i, best_o2 = i, o2
        return best_i

    # ── Init ──
    ds  = DecoState()
    ds.clear(surface_bar)
    cns = 0.0; otu = 0.0; run_time_s = 0

    # ── Descent ──
    target_m   = float(levels[0]['depthM'])
    bottom_min = float(levels[0]['bottomTimeMin'])
    desc_s     = int(round(target_m / desc_rate * 60))
    o2b, heb, _ = all_gases[0]
    for t in range(desc_s):
        frac = (t+0.5)/desc_s
        p    = depth_to_bar(target_m*frac, surface_bar, salt)
        add_segment(ds, p, o2b, heb, 1)
        ppo2 = p * o2b
        cns = add_cns(cns, ppo2, 1/60.0)
        otu = add_otu(otu, ppo2, 1/60.0)
    run_time_s += desc_s

    # ── Bottom ──
    p_bot  = depth_to_bar(target_m, surface_bar, salt)
    bottom_s = int(round(bottom_min * 60))
    ppo2_bot = p_bot * o2b
    decozone_m = None

    for t in range(bottom_s):
        add_segment(ds, p_bot, o2b, heb, 1)
        cns = add_cns(cns, ppo2_bot, 1/60.0)
        otu = add_otu(otu, ppo2_bot, 1/60.0)
        if decozone_m is None and t % 30 == 0:
            ds_snap = ds.copy()
            c = tissue_tolerance_calc(ds_snap, surface_bar, 1.0, 1.0)
            if c > surface_bar + 0.001:
                decozone_m = bar_to_depth(c, surface_bar, salt)
    if decozone_m is None:
        ds_snap = ds.copy()
        c = tissue_tolerance_calc(ds_snap, surface_bar, 1.0, 1.0)
        if c > surface_bar + 0.001:
            decozone_m = bar_to_depth(c, surface_bar, salt)
    run_time_s += bottom_s

    # ── Ascent + Deco ──
    tts_start_s   = run_time_s
    first_stop_m  = None
    stops         = []
    current_gas   = 0
    in_deco       = False
    depth_m       = target_m

    while depth_m > 0.01:
        # Gas switch check
        if switch_mod:
            ng = best_gas(depth_m)
            if ng != current_gas:
                current_gas = ng
                o2s, hes, _ = all_gases[current_gas]
                p_sw = depth_to_bar(depth_m, surface_bar, salt)
                for _ in range(gas_switch_s):
                    add_segment(ds, p_sw, o2s, hes, 1)
                    cns = add_cns(cns, p_sw*o2s, 1/60.0)
                    otu = add_otu(otu, p_sw*o2s, 1/60.0)
                run_time_s += gas_switch_s

        o2c, hec, _ = all_gases[current_gas]

        # Check ceiling NOW (before ascending)
        ds_pre = ds.copy()
        ceil_bar = tissue_tolerance_calc(ds_pre, surface_bar, gf_low, gf_high)
        ceil_m   = deco_allowed_depth_m(ceil_bar, surface_bar, salt)

        # Next candidate stop (shallower)
        if depth_m <= last_stop_m:
            candidate = 0.0
        elif depth_m - deco_step_m < last_stop_m:
            candidate = last_stop_m
        else:
            candidate = math.floor((depth_m - deco_step_m) / deco_step_m) * deco_step_m

        # If ceiling is above candidate, we can't go there yet — stop here
        if ceil_m > candidate and ceil_m <= depth_m:
            # Deco stop at current depth
            if first_stop_m is None:
                first_stop_m = depth_m
            in_deco = True
            p_here  = depth_to_bar(depth_m, surface_bar, salt)
            stop_s  = 0
            while True:
                for _ in range(60):
                    add_segment(ds, p_here, o2c, hec, 1)
                    cns = add_cns(cns, p_here*o2c, 1/60.0)
                    otu = add_otu(otu, p_here*o2c, 1/60.0)
                run_time_s += 60; stop_s += 60
                ds_ck = ds.copy()
                nc_bar = tissue_tolerance_calc(ds_ck, surface_bar, gf_low, gf_high)
                nc_m   = deco_allowed_depth_m(nc_bar, surface_bar, salt)
                if nc_m <= candidate and stop_s >= min_deco_s:
                    break
                if stop_s > 600*60: break
            stops.append({'depth': depth_m, 'stop_min': stop_s//60})
            # Now ascend to candidate
            if candidate <= 0.01:
                run_time_s += max(1, int(math.ceil(depth_m / SHALLOW_ASC * 60)))
                depth_m = 0.0
                break
            rate = SHALLOW_ASC if depth_m <= last_stop_m + 0.01 else DECO_ASC
            s, cns, otu = _asc_segment(ds, depth_m, candidate, rate, surface_bar, salt, o2c, hec, cns, otu)
            run_time_s += s
            depth_m = candidate
            continue

        # Ceiling allows ascending to candidate — do it
        if candidate <= 0.01:
            # Final ascent to surface
            rate = SHALLOW_ASC if in_deco else DEEP_ASC
            s, cns, otu = _asc_segment(ds, depth_m, 0.0, rate, surface_bar, salt, o2c, hec, cns, otu)
            run_time_s += s
            depth_m = 0.0
            break

        rate = DEEP_ASC if not in_deco else (SHALLOW_ASC if candidate <= last_stop_m else DECO_ASC)
        s, cns, otu = _asc_segment(ds, depth_m, candidate, rate, surface_bar, salt, o2c, hec, cns, otu)
        run_time_s += s
        depth_m = candidate

        # Check ceiling again at new depth
        if depth_m <= 0.01:
            break
        ds_at = ds.copy()
        cb2   = tissue_tolerance_calc(ds_at, surface_bar, gf_low, gf_high)
        cm2   = deco_allowed_depth_m(cb2, surface_bar, salt)
        if cm2 > depth_m:
            # Need a stop here too
            if first_stop_m is None:
                first_stop_m = depth_m
            in_deco = True
            p_here = depth_to_bar(depth_m, surface_bar, salt)
            next_c = 0.0 if depth_m <= last_stop_m else (last_stop_m if depth_m - deco_step_m < last_stop_m else math.floor((depth_m-deco_step_m)/deco_step_m)*deco_step_m)
            stop_s = 0
            while True:
                for _ in range(60):
                    add_segment(ds, p_here, o2c, hec, 1)
                    cns = add_cns(cns, p_here*o2c, 1/60.0)
                    otu = add_otu(otu, p_here*o2c, 1/60.0)
                run_time_s += 60; stop_s += 60
                ds_ck = ds.copy()
                nc_bar = tissue_tolerance_calc(ds_ck, surface_bar, gf_low, gf_high)
                nc_m   = deco_allowed_depth_m(nc_bar, surface_bar, salt)
                if nc_m <= next_c and stop_s >= min_deco_s:
                    break
                if stop_s > 600*60: break
            stops.append({'depth': depth_m, 'stop_min': stop_s//60})

    tts_min = (run_time_s - tts_start_s) / 60.0
    rt_min  = run_time_s / 60.0

    return {
        'TTS':       round(tts_min, 1),
        'RT':        round(rt_min, 1),
        'firstStop': first_stop_m if first_stop_m is not None else 0,
        'CNS':       round(cns, 1),
        'OTU':       round(otu, 1),
        'decozone':  round(decozone_m, 1) if decozone_m else 0,
        'stops':     stops,
    }
