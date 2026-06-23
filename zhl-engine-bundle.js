/**
 * ZHL Engine Bundle — Tier 3 isolated Bühlmann module.
 * Loaded on main thread and in zhl-schedule-worker.js (importScripts).
 */
(function (global) {
  'use strict';

  const ZHL16C = [
    [4.0,1.2599,0.5050],[8.0,1.0000,0.6514],[12.5,0.8618,0.7222],[18.5,0.7562,0.7825],
    [27.0,0.6200,0.8126],[38.3,0.5043,0.8434],[54.3,0.4410,0.8693],[77.0,0.4000,0.8910],
    [109.0,0.3750,0.9092],[146.0,0.3500,0.9222],[187.0,0.3295,0.9319],[239.0,0.3065,0.9403],
    [305.0,0.2835,0.9477],[390.0,0.2610,0.9544],[498.0,0.2480,0.9602],[635.0,0.2327,0.9653],
  ];
  const ZHL16C_HE_HT = [1.88,3.02,4.72,6.99,10.21,14.48,20.53,29.11,41.20,55.19,70.69,90.34,115.29,147.42,188.24,240.03];
  const ZHL16C_HE_AB = [
    [1.7424,0.4245],[1.3830,0.5747],[1.1919,0.6527],[1.0458,0.7223],[0.9220,0.7582],[0.8205,0.7957],
    [0.7305,0.8279],[0.6502,0.8553],[0.5950,0.8757],[0.5545,0.8903],[0.5333,0.8997],[0.5189,0.9073],
    [0.5181,0.9122],[0.5176,0.9171],[0.5172,0.9217],[0.5119,0.9267],
  ];
  const OTU_EXPONENT = 0.8333;
  const SEA_LEVEL_P = 1.01325;

  let altSurfaceP = SEA_LEVEL_P;
  let BAR_PER_METRE = 0.1;
  let WATER_VAPOR = 0.0627;
  let altAcclimatized = true;
  let allowO2AtMOD = true;

  function applyEnvironment(env) {
    env = env || {};
    altSurfaceP = env.altSurfaceP ?? SEA_LEVEL_P;
    BAR_PER_METRE = env.barPerMetre ?? 0.1;
    WATER_VAPOR = env.waterVapor ?? 0.0627;
    altAcclimatized = env.altAcclimatized !== false;
    allowO2AtMOD = env.allowO2AtMOD !== false;
  }

  function defaultEnvironment() {
    return {
      altSurfaceP: SEA_LEVEL_P,
      barPerMetre: 0.1,
      waterVapor: 0.0627,
      altAcclimatized: true,
      allowO2AtMOD: true,
    };
  }

  function depthBar(m) { return altSurfaceP + m * BAR_PER_METRE; }
  function schreiner(p0, pGas, ht, t) { return pGas + (p0 - pGas) * Math.exp(-Math.LN2 / ht * t); }
  function schreinerLinear(p0, fN2, ht, t, p0Amb, R) {
    const k = Math.LN2 / ht;
    const piN2 = (p0Amb - WATER_VAPOR) * fN2;
    const rN2 = R * fN2;
    return piN2 + rN2 * (t - 1 / k) - (piN2 - p0 - rN2 / k) * Math.exp(-k * t);
  }

  function initTissues() {
    const surfP = altAcclimatized ? altSurfaceP : SEA_LEVEL_P;
    const pN2 = (surfP - WATER_VAPOR) * 0.7902;
    return ZHL16C.map(() => ({ pN2, pHe: 0 }));
  }

  function saturateLinear(tissues, fromDepth, toDepth, t, fN2, fHe) {
    if (t <= 0) return tissues;
    const p0Amb = depthBar(fromDepth);
    const pEndAmb = depthBar(toDepth);
    const R = (pEndAmb - p0Amb) / t;
    const fH = fHe || 0;
    return tissues.map((t0, i) => ({
      pN2: schreinerLinear(t0.pN2, fN2, ZHL16C[i][0], t, p0Amb, R),
      pHe: fH > 0 ? schreinerLinear(t0.pHe, fH, ZHL16C_HE_HT[i], t, p0Amb, R) : t0.pHe,
    }));
  }

  function saturate(tissues, depthM, t, fN2, fHe) {
    const pAmb = depthBar(depthM);
    const pN2insp = (pAmb - WATER_VAPOR) * fN2;
    const pHeinsp = (pAmb - WATER_VAPOR) * (fHe || 0);
    return tissues.map((t0, i) => ({
      pN2: schreiner(t0.pN2, pN2insp, ZHL16C[i][0], t),
      pHe: schreiner(t0.pHe, pHeinsp, ZHL16C_HE_HT[i], t),
    }));
  }

  function ceiling(tissues, gfHigh) {
    let maxC = 0;
    tissues.forEach((t0, i) => {
      const pN2 = t0.pN2;
      const pHe = t0.pHe || 0;
      const pTotal = pN2 + pHe;
      let a, b;
      if (pHe > 0 && pTotal > 0) {
        a = (pN2 * ZHL16C[i][1] + pHe * ZHL16C_HE_AB[i][0]) / pTotal;
        b = (pN2 * ZHL16C[i][2] + pHe * ZHL16C_HE_AB[i][1]) / pTotal;
      } else {
        [, a, b] = ZHL16C[i];
      }
      const pAmbMin = (pTotal - gfHigh * a) / (1 - gfHigh + gfHigh / b);
      const cM = Math.max(0, (pAmbMin - altSurfaceP) / BAR_PER_METRE);
      if (cM > maxC) maxC = cM;
    });
    return maxC;
  }

  function computeSurfaceGF(tissues) {
    if (!tissues || !tissues.length) return null;
    const P_surf = altSurfaceP;
    let maxGF = -Infinity;
    tissues.forEach((t, i) => {
      const pTotal = (t.pN2 || 0) + (t.pHe || 0);
      if (pTotal <= 0) return;
      let a, b;
      const pN2 = t.pN2 || 0, pHe = t.pHe || 0;
      if (pHe > 0 && pTotal > 0) {
        a = (pN2 * ZHL16C[i][1] + pHe * ZHL16C_HE_AB[i][0]) / pTotal;
        b = (pN2 * ZHL16C[i][2] + pHe * ZHL16C_HE_AB[i][1]) / pTotal;
      } else {
        [, a, b] = ZHL16C[i];
      }
      const mValue = a + P_surf / b - P_surf;
      if (mValue <= 0) return;
      const gf = (pTotal - P_surf) / mValue;
      if (gf > maxGF) maxGF = gf;
    });
    return maxGF === -Infinity ? 0 : Math.max(0, maxGF * 100);
  }

  function ambientCrossingDepth(tissues) {
    let maxD = 0;
    tissues.forEach(t0 => {
      const pTotal = t0.pN2 + (t0.pHe || 0);
      const d = (pTotal - altSurfaceP) / BAR_PER_METRE;
      if (d > maxD) maxD = d;
    });
    return Math.max(0, maxD);
  }


function getActiveGas(curDepthM, bottomFN2, decoGases, getPPO2LimitFn, bottomLabel) {
  let best = null;
  let bestFO2 = -1;
  for (const dg of decoGases) {
    if (curDepthM > dg.depth) continue;
    // fO2 = 1-fN2-fHe for trimix; dg.fO2 is stored when available (Bug fix: 1-fN2 wrong for trimix)
    const fO2 = dg.fO2 != null ? dg.fO2 : Math.max(0, 1 - dg.fN2 - (dg.fHe || 0));
    // Pure O2 (≥99.5%): allowed at its switch depth regardless of ppO2
    // ApexDeco uses o2MaxDepth special-case — we mirror that here
    const isPureO2 = fO2 >= 0.995 && allowO2AtMOD;
    if (!isPureO2) {
      const limit = getPPO2LimitFn ? getPPO2LimitFn(dg.fN2) : 1.6;
      const ppO2AtCur = (altSurfaceP + curDepthM * BAR_PER_METRE) * fO2;
      if (ppO2AtCur > limit + 0.001) continue;
    }
    // BUGFIX: select by highest O2 fraction, not lowest N2.
    // Selecting by min-fN2 incorrectly prefers trimix deco gases (e.g. Tx21/35, fN2=0.44)
    // over high-O2 nitrox (e.g. EAN50, fN2=0.50) even when the nitrox has more O2 (0.50 vs 0.21).
    // Max-fO2 is the correct criterion: always use the richest available O2 gas within ppO2 limits.
    if (fO2 > bestFO2) {
      best = dg;
      bestFO2 = fO2;
    }
  }
  return best || { fN2: bottomFN2, fHe: 0, label: bottomLabel || 'Bottom' };
}

// Truncate ppO2 to 1 decimal place (floor, not round) — 1.67 → 1.6

function ppO2Check(depthM, fN2, fHe) {
  // He is inert: fO2 = 1 - fN2 - fHe (trimix-safe)
  const o2frac = Math.max(0, 1 - fN2 - (fHe || 0));
  return ((altSurfaceP + depthM * BAR_PER_METRE) * o2frac).toFixed(2);
}

function enforceMinDecoProfile(steps, enabled, min9m, min6m, isMetric, fallbackGas, fallbackFN2, fallbackFHe) {
  if (!enabled || (!min9m && !min6m)) return steps;
  const depth9 = 9;  // 9 m / 30 ft
  const depth6 = 6;  // 6 m / 20 ft

  // ── Pass 1: build result, extending existing stops if present ──
  const result = [];
  const enforced = { 9: false, 6: false };

  for (const s of steps) {
    if (s.type === 'deco' || s.type === 'safety') {
      const depthM = isMetric ? s.depth : Math.round(s.depth / 3.28084);
      if (depthM === depth9 && min9m > 0) {
        result.push({ ...s, type: 'deco', dur: Math.max(s.dur, min9m) });
        enforced[9] = true;
        continue;
      }
      if (depthM === depth6 && min6m > 0) {
        result.push({ ...s, type: 'deco', dur: Math.max(s.dur, min6m) });
        enforced[6] = true;
        continue;
      }
    }
    result.push({ ...s });
  }

  // ── Pass 2: resolve active gas at any depth by scanning the step sequence ──
  // Build a list of gas-change events: { fromDepthM, gas, fN2, fHe }
  // Steps are ordered deepest-first on ascent; gas switches happen as depth decreases.
  function resolveGasAtDepth(targetDepthM) {
    // Walk through steps in order. Track current active gas.
    // A gas change occurs when s.gas differs from the previous step's gas.
    // The active gas at targetDepthM is the gas being breathed when depth <= s.depth (or s.to).
    let activeGas = fallbackGas || '';
    let activeFN2 = fallbackFN2 ?? null;
    let activeFHe = fallbackFHe ?? 0;
    for (const s of steps) {
      if (!s.gas || s.gas.trim() === '') continue;
      // Determine the depth range this step covers
      const stepDepthM = isMetric
        ? (s.depth ?? s.from ?? s.to)
        : Math.round((s.depth ?? s.from ?? s.to) / 3.28084);
      if (stepDepthM == null) continue;
      // Update active gas for steps at or deeper than target
      if (stepDepthM >= targetDepthM) {
        activeGas = s.gas;
        activeFN2 = s.fN2 ?? activeFN2;
        activeFHe = s.fHe ?? activeFHe ?? 0;
      }
    }
    return { gas: activeGas, fN2: activeFN2, fHe: activeFHe ?? 0 };
  }

  // ── Pass 3: inject missing stops in correct position ──
  function injectStop(targetDepthM, minDur) {
    const targetDisplay = isMetric ? targetDepthM : Math.round(targetDepthM * 3.28084);
    // Find insertion point: first ascent-phase step shallower than targetDepthM
    let insertIdx = result.length;
    for (let i = 0; i < result.length; i++) {
      const s = result[i];
      if (s.type === 'descent' || s.type === 'bottom') continue;
      const rawD = s.type === 'ascent' ? (s.to ?? s.depth) : s.depth;
      if (rawD == null) continue;
      const d = isMetric ? rawD : Math.round(rawD / 3.28084);
      if (d < targetDepthM) { insertIdx = i; break; }
    }
    // Resolve the gas the diver is breathing at this depth
    const { gas, fN2, fHe } = resolveGasAtDepth(targetDepthM);
    // If the step at insertIdx is an ascent row that STRADDLES the injection
    // depth, split it so the stop sits between its deep and shallow pieces.
    const straddle = result[insertIdx];
    if (straddle && straddle.type === 'ascent') {
      const sFromM = isMetric ? straddle.from : Math.round(straddle.from / 3.28084);
      const sToM   = isMetric ? straddle.to   : Math.round(straddle.to   / 3.28084);
      if (sFromM > targetDepthM && sToM < targetDepthM) {
        const lowerDur = straddle.dur * (sFromM - targetDepthM) / (sFromM - sToM);
        const upperDur = straddle.dur * (targetDepthM - sToM) / (sFromM - sToM);
        const lowerPiece = { ...straddle, to: targetDisplay, dur: lowerDur };
        const upperPiece = { ...straddle, from: targetDisplay, dur: upperDur };
        const injectRow = {
          type: 'deco',
          depth: targetDisplay,
          to: targetDisplay,
          dur: minDur,
          gas,
          fN2,
          fHe,
          pO2: null,
        };
        result.splice(insertIdx, 1, lowerPiece, injectRow, upperPiece);
        return;
      }
    }
    result.splice(insertIdx, 0, {
      type: 'deco',
      depth: targetDisplay,
      to: targetDisplay,
      dur: minDur,
      gas,
      fN2,
      fHe,
      pO2: null,
    });
  }

  if (!enforced[9] && min9m > 0) injectStop(depth9, min9m);
  if (!enforced[6] && min6m > 0) injectStop(depth6, min6m);

  return result;
}

function runZhlScheduleCore(params) {
  applyEnvironment(params.environment || defaultEnvironment());
  const depthM = params.depthM;
  const bt = params.bt;
  const rate = params.ascentRate;
  const decoRate = params.decoAscentRate;
  const surfaceRate = params.surfaceAscentRate;
  const descentRate = params.descentRate;
  const gfL = params.gfL;
  const gfH = params.gfH;
  const ppo2Bottom = params.ppo2Bottom;
  const ppo2Deco = params.ppo2Deco;
  const minStopT = params.minStopTime;
  const switchPauseT = params.switchPauseT || 0;
  const mdCompatMode = params.mdCompatMode !== false;
  const lastStop = params.lastStop;
  const decoStep = params.decoStep;
  const ppo2High = ppo2Deco;
  const ppo2Mid = 1.5;
  const ppo2Low = params.ppo2Bottom;
  const bottomFN2 = params.bottomFN2;
  const bottomFHe = params.bottomFHe;
  const bottomFO2 = params.bottomFO2;
  const bottomMixLabel = params.bottomMixLabel;
  const decoGases = params.decoGases;

  function getPPO2Limit(fO2) {
    const fO2pct = fO2 * 100;
    if (fO2pct >= 45) return ppo2High;
    if (fO2pct >= 28) return ppo2Mid;
    return ppo2Low;
  }

  const travelInfo = params.travelInfo || null;
  const travelSwitchM = travelInfo ? Math.min(travelInfo.switchDepthM, depthM) : 0;

  // Saturate tissues at depth for bottom time
  let tissues = initTissues();

  // ── Repetitive dive tissue carry (ZHL) ───────────────────────────────────
  // ZHLEngine.calculate() sets window._zhlRepState before calling runDecoSchedule
  // to carry end-of-dive tissues from a previous dive with a surface interval.
  if (params.repState && Array.isArray(params.repState.tissues)) {
    const rep = params.repState;
    for (let i = 0; i < tissues.length && i < rep.tissues.length; i++) {
      tissues[i].pN2 = rep.tissues[i].pN2;
      tissues[i].pHe = rep.tissues[i].pHe || 0;
    }
    if (rep.surfaceIntervalMin > 0) {
      const siMin = rep.surfaceIntervalMin;
      const wv = WATER_VAPOR || 0.0627;
      const inspN2 = 0.7902 * ((altSurfaceP || 1.01325) - wv);
      for (let i = 0; i < tissues.length; i++) {
        const kN2 = Math.LN2 / ZHL16C_N2[i].ht;
        const kHe = Math.LN2 / (ZHL16C_He[i].ht || 1);
        tissues[i].pN2 = inspN2 + (tissues[i].pN2 - inspN2) * Math.exp(-kN2 * siMin);
        tissues[i].pHe = (tissues[i].pHe || 0) * Math.exp(-kHe * siMin);
      }
    }
  }

  // Descent phase — split by travel gas switch depth if travel gas is active
  const descentTime = depthM / descentRate;
  if (travelInfo && travelSwitchM > 0 && travelSwitchM < depthM) {
    // Phase 1: surface → travel switch depth on travel gas
    const travelDescentTime = travelSwitchM / descentRate;
    tissues = saturateLinear(tissues, 0, travelSwitchM, travelDescentTime, travelInfo.fN2);
    // Phase 2: travel switch depth → bottom on bottom gas
    const bottomDescentTime = (depthM - travelSwitchM) / descentRate;
    tissues = saturateLinear(tissues, travelSwitchM, depthM, bottomDescentTime, bottomFN2, bottomFHe);
  } else {
    // No travel gas or switch depth >= bottom: entire descent on bottom gas
    tissues = saturateLinear(tissues, 0, depthM, descentTime, bottomFN2, bottomFHe);
  }

  // Bottom time input = total time from leaving surface (industry standard).
  // Subtract descent time to get actual time spent at depth.
  const btAtDepth = Math.max(0, bt - descentTime);
  tissues = saturate(tissues, depthM, btAtDepth, bottomFN2, bottomFHe);
  const tissuesAtBottom = [...tissues]; // snapshot for ceiling graph overlay

  // ── Decozone start (GF-INDEPENDENT) ──────────────────────────────────────
  // Evaluated at end-of-bottom tissue state, matching DiveKit's convention:
  // the depth where the leading compartment's raw inert-gas tension first
  // exceeds ambient pressure, with NO GF/M-value involved. Must NOT vary with
  // gfLo/gfHi for the same physical dive (see ambientCrossingDepth() above).
  const trueDecoZoneStart = ambientCrossingDepth(tissuesAtBottom);

  const steps = [];
  let cur = depthM;
  let rt  = bt; // run time = full BT input (descent already counted in BT)


  // ── Multi-level headless: monotonic-shallower continuation after deepest level ──
  const _zhlContLevels = Array.isArray(params.continuationLevels) ? params.continuationLevels : [];
  const _zhlAscentFloors = _zhlContLevels.length
    ? _zhlContLevels.map(c => c.depth).concat([0]) : [0];

  let firstStopDepth = 0;

  // gfAt must live outside the phase loop — block-scoped function declarations are
  // not visible after the loop in strict mode (Tier 3 bundle uses 'use strict').
  function gfAt(depthM) {
    if (!firstStopDepth || firstStopDepth <= 0) return gfL;
    if (depthM >= firstStopDepth) return gfL;
    const sgOn = !!params.shallowGradient;
    if (sgOn && depthM <= lastStop) return gfH;
    const interpBase = sgOn ? lastStop : 0;
    const gf = gfL + (gfH - gfL) * (firstStopDepth - depthM) / (firstStopDepth - interpBase);
    return Math.min(gfH, Math.max(gfL, gf));
  }

  for (let _zhlPhaseIdx = 0; _zhlPhaseIdx < _zhlAscentFloors.length; _zhlPhaseIdx++) {
  const _zhlAscentFloor = _zhlAscentFloors[_zhlPhaseIdx];
  firstStopDepth = 0;

  // ── GF anchor: candidate stop list built from ceiling(bottom_tissues, gfL) ──
  // firstStopDepth is NOT pre-computed here — it is anchored dynamically at the
  // FIRST depth where mustStop actually fires. This matches MultiDeco/Baker:
  // GF line is pinned at the actual first required stop, not at a pre-computed
  // ceiling that may be one step above the real first stop.
  const bottomCeil = ceiling(tissues, gfL);
  const candidateFirstStop = bottomCeil > 0
    ? Math.max(lastStop, Math.ceil(bottomCeil / decoStep) * decoStep)
    : 0;

  // firstStopDepth: mutable — set when the first ceiling-forced stop is reached.
  // Until it is set, gfAt() returns gfL (GF Low determines the search for the
  // first stop, per Baker; GF line is not yet anchored/interpolated).

  // ── Stop-based ascent engine ──
  // Start stop iteration from candidateFirstStop — ascent from bottom to first stop
  // is a single linear segment. Gas switch happens at the first stop where it's available.
  // This matches ApexDeco: ascend to first stop, then iterate stops down to lastStop.
  const startStop = candidateFirstStop > 0 ? candidateFirstStop : lastStop;
  const stopDepths = [];
  const floorStopMin = _zhlAscentFloor > 0 ? Math.max(lastStop, _zhlAscentFloor) : lastStop;
  for (let d = startStop; d >= floorStopMin; d -= decoStep) {
    stopDepths.push(d);
  }
  if (_zhlAscentFloor > 0) {
    if (stopDepths.length === 0 || stopDepths[stopDepths.length - 1] !== floorStopMin) stopDepths.push(floorStopMin);
  } else if (stopDepths.length === 0 || stopDepths[stopDepths.length - 1] !== lastStop) {
    stopDepths.push(lastStop);
  }

  let prevEngineGas = bottomMixLabel; // track gas for switch pause
  let decoZoneEntered = _zhlPhaseIdx > 0; // true once first ceiling-forced stop fires

  // firstSwitchDepth — find first deco gas switch depth
  let firstDecoDepth   = null;
  let firstSwitchDepth = null;
  {
    let simCur = cur;
    let simPrevGas = bottomMixLabel;
    for (const sd of stopDepths) {
      if (simCur > sd) simCur = sd;
      const gas2 = getActiveGas(simCur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
      if (gas2.label !== simPrevGas) { firstSwitchDepth = simCur; break; }
      simPrevGas = gas2.label;
    }
  }

  // minStop zone: only enforce minimum stops within the GF-anchored deco zone.
  // Dynamically updated when firstStopDepth is set — starts null (no min-stop
  // enforcement until the first required stop depth is known).
  let minStopZoneDepth = null;

  for (let si = 0; si < stopDepths.length; si++) {
    const stopDepth = stopDepths[si];
    const nextStop  = si + 1 < stopDepths.length ? stopDepths[si + 1] : 0;

    // Travel from cur to stopDepth — use appropriate ascent rate:
    // - Before first deco stop: use main ascent rate
    // - Between deco stops: use decoRate
    if (cur > stopDepth) {
      const travelGas = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
      const travelRate = decoZoneEntered ? decoRate : rate;
      const travelDur = (cur - stopDepth) / travelRate;
      if (decoZoneEntered && mdCompatMode) {
        // MultiDeco-compatible mode: treat deco-zone transit as instant for tissue loading.
        // Transit time is still counted in RT and added to the displayed stop duration below.
        // (Schreiner mode: tissues off-gas normally during transit — more accurate.)
      } else {
        tissues = saturateLinear(tissues, cur, stopDepth, travelDur, travelGas.fN2, travelGas.fHe || 0);
      }
      steps.push({
        type: 'ascent', from: cur, to: stopDepth,
        dur: travelDur, gas: travelGas.label,
        pO2: ppO2Check(cur, travelGas.fN2, travelGas.fHe || 0), fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
        decoTransit: decoZoneEntered && mdCompatMode
      });
      rt  += travelDur;
      cur  = stopDepth;
    }

    // Transit time for minimum stop rounding (ApexDeco style):
    // si=0: arrived via fast ascent (rate m/min), transitDur=0 for min-stop purposes
    // si>0: travelled at decoRate between stops
    const transitDur = (si === 0) ? 0 : (stopDepths[si - 1] - stopDepth) / decoRate;

    // Select best gas available at this stop depth
    const stopGas  = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
    const stopFN2  = stopGas.fN2;
    const stopFHe  = stopGas.fHe || 0;
    const gasLabel = stopGas.label;

    // Gas switch pause — saturate tissues at this depth during the switch
    if (gasLabel !== prevEngineGas && switchPauseT > 0) {
      tissues = saturate(tissues, cur, switchPauseT, stopFN2, stopFHe);
      rt += switchPauseT;
    }
    prevEngineGas = gasLabel;

    // Ceiling clearance: evaluate GF at the TARGET (next stop or surface),
    // not the current stop. Baker/ApexDeco: "can I ascend TO the next stop?"
    // At last stop: target=0 → uses gfH (surface GF). This is correct.
    // Use nextStop exactly — ceiling must be strictly below the next stop.
    const phaseNextStop = (_zhlAscentFloor > 0) ? Math.max(_zhlAscentFloor, nextStop) : nextStop;
    const ceilTarget = (phaseNextStop < lastStop) ? 0 : phaseNextStop;
    const gfForClear = gfAt((phaseNextStop < lastStop) ? 0 : phaseNextStop);

    const isFirstDecoStop = (firstDecoDepth === null);
    // Step resolution: first deco stop uses fine (10-sec) resolution, matching
    // ApexDeco/MultiDeco's fractional first-stop snap. Subsequent stops use
    // 1-min steps for ceiling resolution (MultiDeco behaviour), regardless of
    // minStopT, ensuring stops don't under-count.
    // BUGFIX (v2.10.44): headless mode previously forced holdStep=1 even for
    // the first stop (a test-speed shortcut), which coarsened the while-loop's
    // own resolution and inflated the first-stop time relative to what the
    // real app and headless test harnesses both expect — this is the only
    // _zhlHeadless branch in the file that changes a computed RESULT rather
    // than skipping DOM rendering, so it was silently producing different
    // RT/TTS numbers in headless tests than the real app would for the same
    // inputs. Subsequent (non-first) stops still use the coarser 1-min step
    // in headless mode for speed, since that resolution already matches the
    // real app's own non-first-stop behavior.
    const holdStep = isFirstDecoStop ? 1/6 : 1;

    const ceil     = ceiling(tissues, gfForClear);
    const mustStop = ceil > ceilTarget;

    if (mustStop) {
      // Record the first depth where ceiling forces a stop.
      // CRITICAL: anchor firstStopDepth here (not pre-computed from bottom tissues).
      // This matches MultiDeco/Baker: GF line is anchored at the ACTUAL first stop depth.
      if (firstDecoDepth === null) {
        firstDecoDepth  = cur;
        firstStopDepth  = cur;   // anchor GF line at real first stop
        minStopZoneDepth = cur;  // enable min-stop enforcement from here down
      }
      decoZoneEntered = true;
      // Capture RT before ceiling loop — ApexDeco snaps the arrival RT to next minute
      const rtOnArrival = rt;
      let stopT = 0;
      while (ceiling(tissues, gfForClear) > ceilTarget && stopT < 360) {
        tissues = saturate(tissues, cur, holdStep, stopFN2, stopFHe);
        stopT += holdStep; rt += holdStep;
      }
      if (isFirstDecoStop) {
        // First stop: always use RT-snap (fractional) — both ApexDeco and MultiDeco
        // keep the exact first-stop time (e.g. 0:33, 0:27) regardless of rounding mode.
        const rawRounded = Math.round(stopT * 60) / 60;
        const minFirstStop = Math.round((Math.ceil(rtOnArrival / minStopT) * minStopT - rtOnArrival) * 60) / 60;
        const actualStop = Math.max(rawRounded, minFirstStop);
        if (actualStop > stopT) {
          const extra = actualStop - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          rt += extra; stopT = actualStop;
        }
        if (stopT < 1/60) { tissues = saturate(tissues, cur, 1/60 - stopT, stopFN2, stopFHe); rt += 1/60 - stopT; stopT = 1/60; }
      } else {
        let roundedStop;
        {
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitDur + stopT) / minStopT) * minStopT);
          roundedStop = totalAtLevel - transitDur;
        }
        if (roundedStop > stopT) {
          const extra = roundedStop - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          rt += extra; stopT = roundedStop;
        }
        // Enforce minimum stop time — every non-first deco stop gets at least minStopT
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          rt += extra; stopT = minStopT;
        }
      }
      const mustStopDisplay = (mdCompatMode && !isFirstDecoStop) ? stopT + transitDur : stopT;
      steps.push({ type: 'deco', depth: cur, dur: mustStopDisplay, gas: gasLabel, pO2: ppO2Check(cur, stopFN2, stopFHe), fN2: stopFN2, fHe: stopFHe, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
    } else if (minStopT > 0 && minStopZoneDepth !== null && cur <= minStopZoneDepth && cur !== lastStop) {
      decoZoneEntered = true;
      let stopT = 0;
      if (isFirstDecoStop) {
        if (firstDecoDepth === null) firstDecoDepth = cur;
        const minFirstStop = Math.ceil(rt / minStopT) * minStopT - rt;
        const snapped = Math.max(0, Math.round(minFirstStop * 60) / 60);
        // Always keep meaningful fractional first stop (RT-snap). MultiDeco behaviour.
        // Never pad first stop to full minStopT — only enforce 1-sec minimum.
        stopT = Math.max(snapped, 1/60);
      } else {
        const needed = Math.max(0, minStopT - transitDur);
        stopT = needed;
      }
      if (stopT > 0) {
        tissues = saturate(tissues, cur, stopT, stopFN2, stopFHe);
        rt += stopT;
      }
      while (ceiling(tissues, gfForClear) > ceilTarget && stopT < 360) {
        tissues = saturate(tissues, cur, minStopT, stopFN2, stopFHe);
        stopT += minStopT; rt += minStopT;
      }
      if (!isFirstDecoStop) {
        // Round up and enforce minimum — only for non-first stops
        const totalAtLevel = Math.max(minStopT, Math.ceil((transitDur + stopT) / minStopT) * minStopT);
        const roundedStop = totalAtLevel - transitDur;
        if (roundedStop > stopT) {
          const extra = roundedStop - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          rt += extra; stopT = roundedStop;
        }
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          rt += extra; stopT = minStopT;
        }
      }
      if (stopT > 0) {
        const minStopDisplay = (mdCompatMode && !isFirstDecoStop) ? stopT + transitDur : stopT;
        steps.push({ type: 'deco', depth: cur, dur: minStopDisplay, gas: gasLabel, pO2: ppO2Check(cur, stopFN2, stopFHe), fN2: stopFN2, fHe: stopFHe, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
      }
    } else if (cur === lastStop) {
      const isDecoNeeded = steps.some(s => s.type === 'deco');
      const stopType = isDecoNeeded ? 'deco' : 'safety';
      let stopT = 0;
      let transitToLastStop = 0;
      if (isDecoNeeded) {
        transitToLastStop = (stopDepths.length > 1) ? (stopDepths[stopDepths.length - 2] - lastStop) / decoRate : 0;
        while (ceiling(tissues, gfAt(0)) > 0.01 && stopT < 180) {
          tissues = saturate(tissues, cur, minStopT, stopFN2, stopFHe);
          stopT += minStopT; rt += minStopT;
        }
        let roundedLastStop;
        {
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitToLastStop + stopT) / minStopT) * minStopT);
          roundedLastStop = totalAtLevel - transitToLastStop;
        }
        if (roundedLastStop > stopT) {
          const extra = roundedLastStop - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          stopT += extra; rt += extra;
        }
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);
          stopT += extra; rt += extra;
        }
      } else {
        stopT = Math.max(3, minStopT);
        tissues = saturate(tissues, cur, stopT, stopFN2, stopFHe);
        rt += stopT;
      }
      const lastStopDisplay = mdCompatMode ? stopT + transitToLastStop : stopT;
      steps.push({ type: stopType, depth: cur, dur: lastStopDisplay, gas: gasLabel, pO2: ppO2Check(cur, stopFN2, stopFHe), fN2: stopFN2, fHe: stopFHe, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
    }
    // No stop needed and not lastStop — continue ascending
    if (_zhlAscentFloor > 0 && cur <= _zhlAscentFloor && stopDepth <= _zhlAscentFloor) break;
  }

  if (_zhlAscentFloor > 0 && cur > _zhlAscentFloor) {
    const travelRate = decoZoneEntered ? decoRate : rate;
    const travelDur = (cur - _zhlAscentFloor) / travelRate;
    const travelGas = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
    tissues = saturateLinear(tissues, cur, _zhlAscentFloor, travelDur, travelGas.fN2, travelGas.fHe || 0);
    steps.push({
      type: 'ascent', from: cur, to: _zhlAscentFloor,
      dur: travelDur, gas: travelGas.label,
      pO2: ppO2Check(cur, travelGas.fN2, travelGas.fHe || 0), fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
    });
    rt += travelDur;
    cur = _zhlAscentFloor;
  } else if (_zhlAscentFloor === 0 && cur > 0) {
    const finalAscentDur = cur / surfaceRate;
    const finalGas = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
    tissues = saturateLinear(tissues, cur, 0, finalAscentDur, finalGas.fN2, finalGas.fHe || 0);
    steps.push({
      type: 'ascent', from: cur, to: 0,
      dur: finalAscentDur, gas: finalGas.label,
      pO2: ppO2Check(cur, finalGas.fN2, finalGas.fHe || 0), fN2: finalGas.fN2, fHe: finalGas.fHe || 0,
    });
    rt += finalAscentDur;
    cur = 0;
  }

  if (_zhlPhaseIdx < _zhlContLevels.length) {
    const cont = _zhlContLevels[_zhlPhaseIdx];
    cur = cont.depth;
    const cO2 = cont.o2 / 100;
    const cHe = (cont.he || 0) / 100;
    const cN2 = Math.max(0, 1 - cO2 - cHe);
    tissues = saturate(tissues, cur, cont.time, cN2, cHe);
    rt += cont.time;
    steps.push({
      type: 'bottom', depth: cur, dur: cont.time,
      gas: getGasLabel(cO2, cHe), pO2: ppO2Check(cur, cN2, cHe),
      fN2: cN2, fHe: cHe,
    });
  }

  } // end multi-level ascent phase

  // Collapse consecutive ascent steps with the same gas into single rows
  const collapsed = [];
  for (const s of steps) {
    const prev = collapsed[collapsed.length - 1];
    if (s.type === 'ascent' && prev && prev.type === 'ascent' && prev.gas === s.gas) {
      prev.to   = s.to;
      prev.dur += s.dur;
      prev.pO2  = s.pO2; // keep last ppO2
    } else {
      collapsed.push({ ...s });
    }
  }

  // ── Min Deco Profile enforcement ──────────────
  const _mdpEnabled   = !!params.minDecoProfile?.enabled;
  const _mdp9m        = params.minDecoProfile?.m9 ?? 1;
  const _mdp6m        = params.minDecoProfile?.m6 ?? 3;
  const _mdpIsMetric  = params.minDecoProfile?.isMetric !== false;
  const collapsedMDP  = enforceMinDecoProfile(collapsed, _mdpEnabled, _mdp9m, _mdp6m, _mdpIsMetric, bottomMixLabel, bottomFN2, bottomFHe);

  const decoStops = collapsedMDP.filter(s => s.type === 'deco');
  const decoTime  = Math.round(decoStops.reduce((a, s) => a + s.dur, 0) * 60) / 60;
  const hasDeco   = decoStops.length > 0;
  const gasUsed   = [...new Set(collapsed.map(s => s.gas))];

  // ── Headless hook: store plan for Node testing ──
  const runTimeMin = Math.round(rt);
  // TTS (time-to-surface): ascent+deco only. rt was initialized to bt (the full
  // descent-inclusive bottom-time input) and only grows via ascent/deco `rt +=`
  // additions in the loop above, so `rt - bt` is exactly the ascent+deco portion —
  // matches MultiDeco/DiveKit's published TTS definition. Computed here (before
  // the headless early-return below) so it's available in both headless tests
  // and the live DOM-rendered footer.
  const ttsMin = Math.max(0, rt - bt);
  const lastPlan = {
    rt: runTimeMin,
    tts: Math.round(ttsMin * 10) / 10,
    decoTime: Math.round(decoTime),
    stops: decoStops.map(s => ({ depth: s.depth, dur: s.dur, gas: s.gas })),
    steps: collapsed,
    decoZoneStart: trueDecoZoneStart,
    firstStopDepth: firstStopDepth || 0,
    finalTissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0 })),  // for ZHL repetitive dive carry
    surfaceGF: computeSurfaceGF(tissues),
  };

  return {
    lastPlan,
    collapsed,
    collapsedMDP,
    tissuesAtBottom,
    decoStops,
    decoTime,
    hasDeco,
    gasUsed,
    descentTime,
    trueDecoZoneStart,
    firstStopDepth,
    gfAt,
    depthM,
    bt,
    rate,
    decoRate,
    surfaceRate,
    descentRate,
    bottomFN2,
    bottomFHe,
    bottomFO2,
    bottomMixLabel,
    rawD: params.rawD,
    dU: params.metric,
  };
}




  function getGasLabel(fO2, fHe) {
    const o2 = Math.round(fO2 * 100);
    const he = Math.round((fHe || 0) * 100);
    if (he > 0) return o2 + '/' + he;
    if (o2 === 21) return 'Air';
    if (o2 === 32) return 'EAN32';
    if (o2 === 36) return 'EAN36';
    if (o2 === 50) return 'EAN50';
    if (o2 >= 99) return '100%';
    return 'EAN' + o2;
  }

  function zhlOptimalSwitchDepth(fO2, ctx) {
    const ppo2High = ctx.ppo2Deco;
    const ppo2Mid = 1.5;
    const ppo2Low = ctx.ppo2Bottom;
    function getPPO2Limit(fo2) {
      const pct = fo2 * 100;
      if (pct >= 45) return ppo2High;
      if (pct >= 28) return ppo2Mid;
      return ppo2Low;
    }
    if (fO2 <= 0) return 0;
    if (fO2 >= 0.995) return Math.max(ctx.lastStop, ctx.metric ? 6 : 20);
    const limit = getPPO2Limit(fO2);
    const exactMOD = (limit / fO2 - altSurfaceP) / BAR_PER_METRE;
    const snapped = Math.floor(exactMOD / ctx.decoStep) * ctx.decoStep;
    return Math.max(ctx.lastStop, Math.max(0, snapped));
  }

  function buildZhlDecoGasesFromEngine(decoGases, ctx) {
    const list = (decoGases || []).map(g => {
      const o2pct = g.o2;
      const hePct = g.he || 0;
      const fO2 = o2pct / 100;
      const fHe = hePct / 100;
      const fN2 = Math.max(0, 1 - fO2 - fHe);
      let label;
      if (o2pct === 100) label = '100%';
      else if (o2pct === 50 && hePct === 0) label = 'EAN50';
      else if (o2pct === 80 && hePct === 0) label = 'EAN80';
      else label = getGasLabel(fO2, fHe);
      const depth = zhlOptimalSwitchDepth(fO2, ctx);
      return { depth, fN2, fHe, fO2, label };
    });
    list.sort((a, b) => b.depth - a.depth);
    return list;
  }

  function splitZhlProfileLevels(levels) {
    if (!levels || levels.length <= 1) return { primary: levels || [], continuation: [] };
    let deepest = 0;
    for (let i = 1; i < levels.length; i++) {
      if (levels[i].depth > levels[deepest].depth) deepest = i;
    }
    let continuation = [];
    let primary = levels;
    if (deepest < levels.length - 1) {
      let monotonic = true;
      for (let i = deepest + 1; i < levels.length; i++) {
        if (levels[i].depth > levels[i - 1].depth) { monotonic = false; break; }
      }
      if (monotonic) {
        continuation = levels.slice(deepest + 1);
        primary = levels.slice(0, deepest + 1);
      }
    }
    return { primary, continuation };
  }

  function buildZhlScheduleParamsFromEngine(levels, decoGases, settings, profileSplit, environment) {
    const s = settings || {};
    const level = levels[0];
    const metric = s.metric !== false;
    const fO2bot = level.o2 / 100;
    const fHeBot = (level.he || 0) / 100;
    const fN2bot = Math.max(0, 1 - fO2bot - fHeBot);
    const switchCtx = {
      ppo2Bottom: s.ppO2Bottom || 1.4,
      ppo2Deco: s.ppO2Deco || 1.6,
      lastStop: s.lastStop || 3,
      decoStep: s.stepSize || 3,
      metric,
    };
    const gases = buildZhlDecoGasesFromEngine(decoGases, switchCtx);
    return {
      depthM: level.depth,
      bt: level.time,
      rawD: metric ? level.depth : Math.round(level.depth * 3.28084),
      metric,
      ascentRate: Math.max(1, s.ascentRate || 10),
      decoAscentRate: Math.max(1, s.decoAscentRate || 3),
      surfaceAscentRate: Math.max(1, s.surfaceAscentRate || s.decoAscentRate || 3),
      descentRate: Math.max(1, s.descentRate || 20),
      gfL: (s.gfLo || s.gfLow || 30) / 100,
      gfH: (s.gfHi || s.gfHigh || 85) / 100,
      ppo2Bottom: switchCtx.ppo2Bottom,
      ppo2Deco: switchCtx.ppo2Deco,
      minStopTime: s.minStopTime || 1,
      switchPauseT: 0,
      mdCompatMode: s.mdCompatMode !== false,
      lastStop: switchCtx.lastStop,
      decoStep: switchCtx.decoStep,
      shallowGradient: !!s.shallowGradient,
      bottomFN2: fN2bot,
      bottomFHe: fHeBot,
      bottomFO2: fO2bot,
      bottomMixLabel: getGasLabel(fO2bot, fHeBot),
      travelInfo: null,
      repState: (s._preTissues && s._preTissues.length)
        ? { tissues: s._preTissues, surfaceIntervalMin: s._surfaceInterval || 0 }
        : null,
      continuationLevels: (profileSplit && profileSplit.continuation) || [],
      minDecoProfile: { enabled: false, m9: 1, m6: 3, isMetric: true },
      decoGases: gases,
      environment: environment || defaultEnvironment(),
    };
  }

  function addHeadlessExposure(hCNSfrac, hOTU, ppO2, dur) {
    if (ppO2 > 0.5 && dur > 0) {
      hOTU.v += dur * Math.pow((ppO2 - 0.5) / 0.5, OTU_EXPONENT);
      const lims = {6:720,7:570,8:450,9:360,10:300,11:240,12:210,13:180,14:150,15:120,16:45};
      const lo = Math.floor(ppO2 * 10), hi = lo + 1;
      const lim = (lims[lo] || 0) + ((lims[hi] || 0) - (lims[lo] || 0)) * (ppO2 * 10 - lo);
      const safeLim = lim > 0 ? lim : 45;
      hCNSfrac.v += dur / safeLim;
    }
  }

  function computeHeadlessCnsOtu(lp, level, s) {
    if (!lp || lp.totalCNS != null) return;
    const fO2bot = level.o2 / 100;
    const hCNSfrac = { v: 0 };
    const hOTU = { v: 0 };
    const hDescentRate = s.descentRate || 20;
    const hDescentTime = level.depth / hDescentRate;
    addHeadlessExposure(hCNSfrac, hOTU, (altSurfaceP + (level.depth / 2) * BAR_PER_METRE) * fO2bot, hDescentTime);
    addHeadlessExposure(hCNSfrac, hOTU, (altSurfaceP + level.depth * BAR_PER_METRE) * fO2bot, level.time);
    (lp.steps || []).forEach(seg => {
      const d = seg.depth != null ? seg.depth : (seg.type === 'ascent' ? (seg.from + seg.to) / 2 : 0);
      const fO2s = seg.fN2 !== undefined ? Math.max(0, 1 - seg.fN2 - (seg.fHe || 0)) : fO2bot;
      addHeadlessExposure(hCNSfrac, hOTU, fO2s * (altSurfaceP + d * BAR_PER_METRE), seg.dur || 0);
    });
    lp.totalCNS = parseFloat((hCNSfrac.v * 100).toFixed(1));
    lp.totalOTU = Math.round(hOTU.v);
  }

  function mapToEngineReturn(lp, level, s, isMetric) {
    const fO2bot = level.o2 / 100;
    const stops = (lp.stops || []).map(st => ({
      depth: st.depth, time: st.dur, gas: st.gas, type: 'stop',
    }));
    const plan = (lp.steps || []).map(st => ({
      type: st.type === 'deco' ? 'stop' : st.type === 'safety' ? 'stop' : st.type,
      depth: st.type === 'ascent' ? st.to : st.depth,
      time: st.dur,
      run: null,
      gas: st.gas,
      o2: Math.round((st.fN2 !== undefined ? (1 - st.fN2 - (st.fHe || 0)) : fO2bot) * 100),
      he: Math.round((st.fHe || 0) * 100),
    }));
    if (plan.length === 0 || plan[0].type !== 'descent') {
      const descentTime = level.depth / (s.descentRate || 20);
      const bottomGasLabel = plan.length > 0 ? (plan[0].gas || 'bottom') : 'bottom';
      plan.unshift({ type: 'bottom', depth: level.depth, time: level.time, run: descentTime + level.time, gas: bottomGasLabel, o2: level.o2, he: level.he || 0 });
      plan.unshift({ type: 'descent', depth: level.depth, time: descentTime, run: descentTime, gas: bottomGasLabel, o2: level.o2, he: level.he || 0 });
    }
    let runAccum = 0;
    plan.forEach(seg => {
      if (seg.run == null) {
        runAccum += (seg.time || 0);
        seg.run = Math.round(runAccum * 10) / 10;
      } else {
        runAccum = seg.run;
      }
    });
    return {
      plan, stops,
      totalRuntime: lp.rt || 0,
      tts: lp.tts || 0,
      totalOTU: lp.totalOTU || 0,
      totalCNS: lp.totalCNS || 0,
      finalTissues: lp.finalTissues || null,
      depthUnit: isMetric ? 'm' : 'ft',
      error: null,
    };
  }

  function calculate(levels, decoGases, settings, profileSplit, environment) {
    const s = settings || {};
    const isMetric = s.metric !== false;
    const level = levels[0];
    const params = buildZhlScheduleParamsFromEngine(levels, decoGases, s, profileSplit, environment);
    let coreResult;
    try {
      coreResult = runZhlScheduleCore(params);
    } catch (e) {
      return { error: e.message, stops: [], plan: [], totalRuntime: 0 };
    }
    const lp = coreResult.lastPlan;
    if (!lp) return { error: 'No plan generated', stops: [], plan: [], totalRuntime: 0 };
    computeHeadlessCnsOtu(lp, level, s);
    return mapToEngineReturn(lp, level, s, isMetric);
  }

  const api = {
    runZhlScheduleCore,
    buildZhlScheduleParamsFromEngine,
    splitZhlProfileLevels,
    zhlOptimalSwitchDepth,
    calculate,
    defaultEnvironment,
    applyEnvironment,
    OTU_EXPONENT,
  };

  global.ZhlEngineBundle = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof self !== 'undefined' ? self : globalThis);
