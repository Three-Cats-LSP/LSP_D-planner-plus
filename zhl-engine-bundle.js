/**
 * ZHL Engine Bundle — Tier 3 isolated Bühlmann module.
 * Loaded on main thread and in zhl-schedule-worker.js (importScripts).
 */
(function (global) {
  'use strict';

const ZHL16C = [
  [5.0,1.2599,0.5050],[8.0,1.0000,0.6514],[12.5,0.8618,0.7222],[18.5,0.7562,0.7825],
  [27.0,0.6200,0.8126],[38.3,0.5043,0.8434],[54.3,0.4410,0.8693],[77.0,0.4000,0.8910],
  [109.0,0.3750,0.9092],[146.0,0.3500,0.9222],[187.0,0.3295,0.9319],[239.0,0.3065,0.9403],
  [305.0,0.2835,0.9477],[390.0,0.2610,0.9544],[498.0,0.2480,0.9602],[635.0,0.2327,0.9653],
];
const ZHL16C_HE_HT_BAKER = [1.88,3.02,4.72,6.99,10.21,14.48,20.53,29.11,41.20,55.19,70.69,90.34,115.29,147.42,188.24,240.03];
const ZHL16C_HE_HT_BUHL2003 = [1.51,3.02,4.72,6.99,10.21,14.48,20.53,29.11,41.20,55.19,70.69,90.34,115.29,147.42,188.24,240.03];
let ZHL16C_HE_HT = ZHL16C_HE_HT_BAKER.slice();
const ZHL16C_HE_AB = [
  [1.7424,0.4245],[1.3830,0.5747],[1.1919,0.6527],[1.0458,0.7223],[0.9220,0.7582],[0.8205,0.7957],
  [0.7305,0.8279],[0.6502,0.8553],[0.5950,0.8757],[0.5545,0.8903],[0.5333,0.8997],[0.5189,0.9073],
  [0.5181,0.9122],[0.5176,0.9171],[0.5172,0.9217],[0.5119,0.9267],
];
const OTU_EXPONENT = 0.8333;
const SEA_LEVEL_P = 1.01325;
const PSCR_MIN_PPO2 = 0.16;

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

function setHeHalfTimeMode(mode) {
  const src = mode === 'buhl2003' ? ZHL16C_HE_HT_BUHL2003 : ZHL16C_HE_HT_BAKER;
  for (let i = 0; i < 16; i++) ZHL16C_HE_HT[i] = src[i];
}

function depthBar(m) { return altSurfaceP + m * BAR_PER_METRE; }
function schreiner(p0, pGas, ht, t) { return pGas + (p0 - pGas) * Math.exp(-Math.LN2 / ht * t); }
/** @param {number} R - pressure rate bar/min; may be 0 for constant depth (standard Schreiner). */
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
  if (!(gfHigh > 0)) return 0;
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
    const mValue = a + P_surf / b;
    const mMargin = mValue - P_surf;
    if (mMargin <= 0) return;
    const gf = (pTotal - P_surf) / mMargin;
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

function gfAtDepth(depthM, gfL, gfH, firstStopDepth, lastStop, shallowGradient) {
  if (!firstStopDepth || firstStopDepth <= 0) return gfH;
  if (depthM >= firstStopDepth) return gfL;
  if (shallowGradient && depthM <= lastStop) return gfH;
  const interpBase = shallowGradient ? lastStop : 0;
  if (firstStopDepth <= interpBase) return gfH;
  const gf = gfL + (gfH - gfL) * (firstStopDepth - depthM) / (firstStopDepth - interpBase);
  return Math.min(gfH, Math.max(gfL, gf));
}

function ndlClearAtDepth(tissues, depthM, gfL, gfH, lastStop, decoStep, shallowGradient) {
  if (!(decoStep > 0)) decoStep = 3;
  if (!(lastStop >= 0)) lastStop = 3;
  const ceilL = ceiling(tissues, gfL);
  if (ceilL <= 0) return true;
  const firstStop = Math.max(lastStop, Math.ceil(ceilL / decoStep) * decoStep);
  const depths = [depthM];
  for (let d = firstStop; d >= 0; d -= decoStep) {
    if (d < depthM - 1e-6) depths.push(d);
  }
  if (depths[depths.length - 1] !== 0) depths.push(0);
  for (const d of depths) {
    const ceil = ceiling(tissues, gfAtDepth(d, gfL, gfH, firstStop, lastStop, !!shallowGradient));
    if (ceil > d + 0.01) return false;
  }
  return true;
}

function buhNDL(depthM, fN2, gfLow, gfHigh, fHe, lastStop, decoStep, shallowGradient) {
  const fH = fHe || 0;
  const gfL = gfLow / 100;
  const gfH = gfHigh / 100;
  let tissues = initTissues();
  for (let t = 0; t <= 500; t++) {
    const next = saturate(tissues, depthM, 1, fN2, fH);
    if (ndlClearAtDepth(next, depthM, gfL, gfH, lastStop, decoStep, shallowGradient)) {
      tissues = next;
      continue;
    }
    return t;
  }
  return 500;
}


// Depends on zhl-physics-core.js: altSurfaceP, BAR_PER_METRE, allowO2AtMOD
function enforceMinDecoProfile(steps, enabled, min9m, min6m, isMetric, fallbackGas, fallbackFN2, fallbackFHe) {
  if (!enabled || (!min9m && !min6m)) return steps;
  const depth9 = 9;
  const depth6 = 6;
  const FT_PER_M = 3.28084;

  function stepDepthToM(s) {
    const raw = s.depth ?? s.from ?? s.to;
    if (raw == null) return null;
    return isMetric ? raw : raw / FT_PER_M;
  }
  function matchesStdMinStop(depthM, targetM) {
    return depthM != null && Math.abs(depthM - targetM) < 0.25;
  }

  const result = [];
  const enforced = { 9: false, 6: false };

  for (const s of steps) {
    if (s.type === 'deco' || s.type === 'safety') {
      const depthM = stepDepthToM(s);
      if (matchesStdMinStop(depthM, depth9) && min9m > 0) {
        result.push({ ...s, type: 'deco', dur: Math.max(s.dur, min9m) });
        enforced[9] = true;
        continue;
      }
      if (matchesStdMinStop(depthM, depth6) && min6m > 0) {
        result.push({ ...s, type: 'deco', dur: Math.max(s.dur, min6m) });
        enforced[6] = true;
        continue;
      }
    }
    result.push({ ...s });
  }

  function resolveGasAtDepth(targetDepthM) {
    let activeGas = fallbackGas || '';
    let activeFN2 = fallbackFN2 ?? 0;
    let activeFHe = fallbackFHe ?? 0;
    for (let i = result.length - 1; i >= 0; i--) {
      const s = result[i];
      if (!s.gas || s.gas.trim() === '') continue;
      const stepDepthM = stepDepthToM(s);
      if (stepDepthM == null) continue;
      if (stepDepthM >= targetDepthM) {
        return { gas: s.gas, fN2: (s.fN2 ?? activeFN2) ?? 0, fHe: s.fHe ?? activeFHe ?? 0 };
      }
    }
    return { gas: activeGas, fN2: activeFN2 ?? 0, fHe: activeFHe ?? 0 };
  }

  function injectStop(targetDepthM, minDur) {
    const targetDisplay = isMetric ? targetDepthM : Math.round(targetDepthM * 3.28084);
    let insertIdx = result.length;
    for (let i = 0; i < result.length; i++) {
      const s = result[i];
      if (s.type === 'descent' || s.type === 'bottom') continue;
      const rawD = s.type === 'ascent' ? (s.to ?? s.depth) : s.depth;
      if (rawD == null) continue;
      const d = isMetric ? rawD : rawD / FT_PER_M;
      if (d != null && d <= targetDepthM) { insertIdx = i; break; }
    }
    const { gas, fN2, fHe } = resolveGasAtDepth(targetDepthM);
    const straddle = result[insertIdx];
    if (straddle && straddle.type === 'ascent') {
      const sFromM = stepDepthToM({ depth: straddle.from, from: straddle.from, to: straddle.to });
      const sToM = stepDepthToM({ depth: straddle.to, from: straddle.from, to: straddle.to });
      if (sFromM > targetDepthM && sToM <= targetDepthM) {
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

function getActiveGas(curDepthM, bottomFN2, bottomFHe, decoGases, getPPO2LimitFn, bottomLabel) {
  const fHeBottom = bottomFHe || 0;
  let best = null;
  let bestFO2 = -1;
  for (const dg of decoGases) {
    if (curDepthM > dg.depth) continue;
    const fO2 = dg.fO2 != null ? dg.fO2 : Math.max(0, 1 - dg.fN2 - (dg.fHe || 0));
    const isPureO2 = fO2 >= 0.995 && allowO2AtMOD;
    if (!isPureO2) {
      const limit = getPPO2LimitFn ? getPPO2LimitFn(fO2) : 1.6;
      const ppO2AtCur = (altSurfaceP + curDepthM * BAR_PER_METRE) * fO2;
      if (ppO2AtCur > limit + 0.001) continue;
    }
    if (fO2 > bestFO2) {
      best = dg;
      bestFO2 = fO2;
    }
  }
  return best || { fN2: bottomFN2, fHe: fHeBottom, label: bottomLabel || 'Bottom' };
}

function ppO2Check(depthM, fN2, fHe, opts) {
  const fHeVal = fHe || 0;
  const fO2 = 1 - fN2 - fHeVal;
  const o2frac = Math.max(0, fO2);
  const pAmb = altSurfaceP + depthM * BAR_PER_METRE;
  if (opts && opts.onLoop && opts.ccr && isRebreatherCircuit(opts.ccr.circuit) && !opts.ccr.bailout) {
    const ccrFO2 = opts.fO2 != null ? opts.fO2 : o2frac;
    const surfP = opts.surfP != null ? opts.surfP : altSurfaceP;
    const sp = opts.setpoint != null ? opts.setpoint : getEffectiveSetpointAtDepth(depthM, opts.ccr, surfP);
    return getEffectivePpo2(pAmb, sp, ccrFO2, opts.ccr, depthM, fHeVal);
  }
  return pAmb * o2frac;
}

function n2FracFromCustomO2(o2pct) {
  const o2 = Number.isFinite(o2pct) ? o2pct : 21;
  return Math.max(0, (100 - o2) / 100);
}

function n2FracFromPercentages(o2pct, hepct) {
  if (Number.isFinite(o2pct) && Number.isFinite(hepct)) {
    const n2 = (100 - o2pct - hepct) / 100;
    if (n2 < 0 || n2 > 1) return null;
    return n2;
  }
  return null;
}

function validateHypoxicDecoGas(o2, he, field, circuit) {
  const heVal = he || 0;
  const label = String(field).replace(/^dg/, '');
  if (o2 + heVal > 100 + 1e-6) {
    return {
      ok: false,
      code: 'ERR_TOTAL_EXCEEDS_100',
      field,
      message: `Deco gas ${label}: O₂ + He exceeds 100%.`,
    };
  }
  const isCCR = circuit === 'CCR' || circuit === 'pSCR';
  if (!isCCR && o2 < 18) {
    return {
      ok: false,
      code: 'HYPOXIC_DECO_GAS',
      field,
      message: `Deco gas ${label}: O₂ below 18% is hypoxic at stop depths.`,
    };
  }
  return null;
}


function canonicalCircuit(circuit) {
  if (circuit == null || circuit === '') return 'OC';
  const u = String(circuit).trim().toUpperCase();
  if (u === 'CCR') return 'CCR';
  if (u === 'PSCR') return 'pSCR';
  return 'OC';
}

const PSCR_LOOP_VOLUME_MIN = 3;
const PSCR_LOOP_VOLUME_MAX = 15;
const PSCR_METABOLIC_O2_MIN = 0.5;
const PSCR_METABOLIC_O2_MAX = 2.5;

/** Closed field list — unknown keys on input are dropped; extend here when adding CCR settings. */
function normalizeCCRSettings(s) {
  s = s || {};
  return {
    circuit: canonicalCircuit(s.circuit || 'OC'),
    setpoint: s.setpoint != null ? s.setpoint : s.decoSetpoint,
    decoSetpoint: s.decoSetpoint != null ? s.decoSetpoint : s.setpoint,
    bottomSetpoint: s.bottomSetpoint,
    descentSetpoint: s.descentSetpoint,
    bailout: !!s.bailout,
    bailoutGfLow: s.bailoutGfLow,
    bailoutGfHigh: s.bailoutGfHigh,
    scrLoopVolume: s.scrLoopVolume,
    scrMetabolicO2: s.scrMetabolicO2,
    sacStress: s.sacStress,
    sacDecoCcr: s.sacDecoCcr,
    stressTimeMin: s.stressTimeMin,
    problemSolveMin: s.problemSolveMin,
    ccrPhase: s.ccrPhase || null,
    scrRuntimeMin: s.scrRuntimeMin || 0,
  };
}

function mergeCCRSettings(ccr) {
  return normalizeCCRSettings(ccr);
}

function isRebreatherCircuit(circuit) {
  const c = canonicalCircuit(circuit);
  return c === 'CCR' || c === 'pSCR';
}

function loopMixLabelForCore(diluentLabel, ccr) {
  const cfg = normalizeCCRSettings(ccr);
  if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout) return diluentLabel;
  if (typeof diluentLabel === 'string' && /^(CCR|pSCR)\s/i.test(diluentLabel)) return diluentLabel;
  const prefix = cfg.circuit === 'pSCR' ? 'pSCR' : 'CCR';
  return `${prefix} ${diluentLabel}`;
}

function depthAtSetpointCrossing(setpoint, surfP) {
  if (!Number.isFinite(setpoint) || setpoint <= 0) return null;
  const sp = surfP != null ? surfP : altSurfaceP;
  if (!Number.isFinite(sp) || sp <= 0) return null;
  const d = (setpoint + WATER_VAPOR - sp) / BAR_PER_METRE;
  return Number.isFinite(d) && d > 0 ? d : null;
}

function getEffectiveSetpointAtDepth(depthM, ccr, surfP, phase) {
  const cfg = normalizeCCRSettings(ccr);
  if (!cfg || cfg.bailout || !isRebreatherCircuit(cfg.circuit)) return 0;
  if (cfg.circuit === 'pSCR') return 0;
  const descSP = cfg.descentSetpoint != null ? cfg.descentSetpoint : 0.7;
  const bottomSP = cfg.bottomSetpoint != null ? cfg.bottomSetpoint : 1.2;
  const decoSP = cfg.decoSetpoint != null ? cfg.decoSetpoint : (cfg.setpoint != null ? cfg.setpoint : 1.3);
  if (phase === 'descent') return descSP;
  if (phase === 'bottom') return bottomSP;
  if (phase === 'deco' || phase === 'ascent') return decoSP;
  const spSurf = surfP != null ? surfP : altSurfaceP;
  const descCross = depthAtSetpointCrossing(descSP, spSurf);
  const bottomCross = depthAtSetpointCrossing(bottomSP, spSurf);
  const decoCross = depthAtSetpointCrossing(decoSP, spSurf);
  if (descCross == null && bottomCross == null && decoCross == null) {
    const pDry = (spSurf + depthM * BAR_PER_METRE) - WATER_VAPOR;
    if (pDry >= decoSP) return decoSP;
    if (pDry >= bottomSP) return bottomSP;
    return descSP;
  }
  const pAmb = spSurf + depthM * BAR_PER_METRE;
  const pDry = pAmb - WATER_VAPOR;
  if (depthM < 0.5) {
    if (pDry >= decoSP) return decoSP;
    if (pDry >= bottomSP) return bottomSP;
    return descSP;
  }
  const crossDepths = [descCross, bottomCross, decoCross].filter(d => d != null);
  if (crossDepths.length === 0) {
    if (pDry >= decoSP) return decoSP;
    if (pDry >= bottomSP) return bottomSP;
    return descSP;
  }
  if (descCross != null && depthM <= descCross) {
    if (pDry >= bottomSP + 0.005) return bottomSP;
    return descSP;
  }
  if (descCross == null && bottomCross != null && depthM < bottomCross) {
    if (pDry >= bottomSP) return bottomSP;
    return descSP;
  }
  if (decoCross != null && depthM <= decoCross) return bottomSP;
  return decoSP;
}

/** @param {object} ccr — CCR settings; scrMetabolicO2 in L/min (Baker steady-state). */
function getCcrMetabolicO2Rate(ccr) {
  const cfg = normalizeCCRSettings(ccr);
  const v = parseFloat(cfg.scrMetabolicO2);
  return v > 0 ? v : 1.5;
}

function parsePSCRParameters(ccr) {
  const loopVol = parseFloat(ccr.scrLoopVolume);
  if (!Number.isFinite(loopVol) || loopVol < PSCR_LOOP_VOLUME_MIN || loopVol > PSCR_LOOP_VOLUME_MAX) {
    throw new RangeError(`pSCR loop volume must be between ${PSCR_LOOP_VOLUME_MIN} and ${PSCR_LOOP_VOLUME_MAX} litres`);
  }
  const metO2 = parseFloat(ccr.scrMetabolicO2);
  if (!Number.isFinite(metO2) || metO2 < PSCR_METABOLIC_O2_MIN || metO2 > PSCR_METABOLIC_O2_MAX) {
    throw new RangeError(`pSCR metabolic O2 must be between ${PSCR_METABOLIC_O2_MIN} and ${PSCR_METABOLIC_O2_MAX} L/min`);
  }
  return { loopVol, metO2 };
}

/** pSCR loop fractions; metO2/loopVol yields bar/bar ppO2 drop (L/min ÷ L). */
function computePSCRFractions(pAmb, fO2, fHe, ccr) {
  fO2 = Math.max(0, Math.min(1, fO2 || 0));
  fHe = Math.max(0, Math.min(1 - fO2, fHe || 0));
  const fN2src = Math.max(0, 1 - fO2 - fHe);
  const sourceInert = Math.max(0.001, fHe + fN2src);
  if (sourceInert <= 0.001 && fO2 >= 0.999) return { fO2: 1, fHe: 0, fN2: 0 };
  const { loopVol, metO2 } = parsePSCRParameters(ccr);
  // Steady-state pSCR model: ppO2_loop = ppO2_supply - VO2/loopVol (Baker drop formula).
  // Previous model subtracted cumulative dive runtime × VO2 from a fixed loop volume,
  // which drove loop O2 to near-zero after a few minutes, zeroing N2 loading for the
  // rest of the dive. The steady-state formula is time-independent and depth-correct.
  const ppO2Drop = metO2 / loopVol;
  const ppO2Supply = fO2 * pAmb;
  const cappedDrop = Math.min(ppO2Drop, Math.max(0, ppO2Supply - PSCR_MIN_PPO2));
  const newPpO2 = ppO2Supply - cappedDrop;
  const newFO2 = Math.min(0.999, newPpO2 / Math.max(0.001, pAmb));
  const inertTotal = Math.max(0, 1 - newFO2);
  const heShare = fHe / sourceInert;
  const n2Share = fN2src / sourceInert;
  return {
    fO2: newFO2,
    fHe: inertTotal * heShare,
    fN2: inertTotal * n2Share,
  };
}

function ccrLoopGasBelowSetpoint(pAmb, fO2, fHe, setpoint) {
  const ppH2O = WATER_VAPOR;
  const pDry = Math.max(0, pAmb - ppH2O);
  if (pDry <= 0.001) {
    return { fO2: 1, fN2: 0, fHe: 0, pN2: 0, pHe: 0 };
  }
  const spTarget = setpoint > 0 ? Math.min(setpoint, pDry) : pDry;
  const fO2dry = Math.min(1, spTarget / pDry);
  const loopInertDry = Math.max(0, 1 - fO2dry);
  const fN2d = Math.max(0, 1 - fO2 - fHe);
  const inertSrc = Math.max(0.001, fHe + fN2d);
  const fHeEffDry = loopInertDry * (fHe / inertSrc);
  const fN2effDry = loopInertDry * (fN2d / inertSrc);
  const wetScale = pDry / Math.max(0.001, pAmb);
  return {
    fO2: fO2dry * wetScale,
    fN2: fN2effDry * wetScale,
    fHe: fHeEffDry * wetScale,
    pN2: pDry * fN2effDry,
    pHe: pDry * fHeEffDry,
  };
}

function getInspiredInertPressures(pAmb, setpoint, fO2, fHe, ccr) {
  const ppH2O = WATER_VAPOR;
  const cfg = normalizeCCRSettings(ccr);
  if (cfg.bailout || !isRebreatherCircuit(cfg.circuit)) {
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    return { pN2: (pAmb - ppH2O) * fN2, pHe: (pAmb - ppH2O) * fHe, fO2, fHe, fN2 };
  }
  if (cfg.circuit === 'pSCR') {
    const fr = computePSCRFractions(pAmb, fO2, fHe, cfg);
    return {
      pN2: (pAmb - ppH2O) * fr.fN2,
      pHe: (pAmb - ppH2O) * fr.fHe,
      fO2: fr.fO2, fHe: fr.fHe, fN2: fr.fN2,
    };
  }
  if (!setpoint || setpoint <= 0) {
    const fN2d = Math.max(0, 1 - fO2 - fHe);
    const pInert = Math.max(0, pAmb - ppH2O);
    return { pN2: pInert * fN2d, pHe: pInert * fHe, fO2, fHe, fN2: fN2d };
  }
  if (pAmb <= setpoint + ppH2O) {
    const loop = ccrLoopGasBelowSetpoint(pAmb, fO2, fHe, setpoint);
    return { pN2: loop.pN2, pHe: loop.pHe, fO2: loop.fO2, fHe: loop.fHe, fN2: loop.fN2 };
  }
  const pInert = pAmb - setpoint - ppH2O;
  const fN2d = Math.max(0, 1 - fO2 - fHe);
  const den = Math.max(0.001, fN2d + fHe);
  return {
    pN2: pInert * fN2d / den,
    pHe: pInert * fHe / den,
    fO2, fHe, fN2: fN2d,
  };
}

function getCCRInertSchreinerParams(pAmbStart, setpoint, fO2, fHe, pressureRate, ccr) {
  const cfg = normalizeCCRSettings(ccr);
  if (cfg.bailout || !isRebreatherCircuit(cfg.circuit)) {
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    const ppH2O = WATER_VAPOR;
    return {
      inspN2Start: (pAmbStart - ppH2O) * fN2,
      inspHeStart: (pAmbStart - ppH2O) * fHe,
      rN2: fN2 * pressureRate,
      rHe: fHe * pressureRate,
    };
  }
  if (cfg.circuit === 'pSCR') {
    const fr0 = computePSCRFractions(pAmbStart, fO2, fHe, cfg);
    const pEnd = pAmbStart + pressureRate * 1;
    const fr1 = computePSCRFractions(pEnd, fO2, fHe, cfg);
    const ppH2O = WATER_VAPOR;
    const inspN2Start = (pAmbStart - ppH2O) * fr0.fN2;
    const inspHeStart = (pAmbStart - ppH2O) * fr0.fHe;
    return {
      inspN2Start,
      inspHeStart,
      rN2: (pEnd - ppH2O) * fr1.fN2 - inspN2Start,
      rHe: (pEnd - ppH2O) * fr1.fHe - inspHeStart,
    };
  }
  if (!setpoint || setpoint <= 0) {
    const fN2d = Math.max(0, 1 - fO2 - fHe);
    const ppH2O = WATER_VAPOR;
    return {
      inspN2Start: (pAmbStart - ppH2O) * fN2d,
      inspHeStart: (pAmbStart - ppH2O) * fHe,
      rN2: fN2d * pressureRate,
      rHe: fHe * pressureRate,
    };
  }
  if (pAmbStart <= setpoint + WATER_VAPOR) {
    const loop0 = ccrLoopGasBelowSetpoint(pAmbStart, fO2, fHe, setpoint);
    const loop1 = ccrLoopGasBelowSetpoint(pAmbStart + pressureRate, fO2, fHe, setpoint);
    return {
      inspN2Start: loop0.pN2,
      inspHeStart: loop0.pHe,
      rN2: loop1.pN2 - loop0.pN2,
      rHe: loop1.pHe - loop0.pHe,
    };
  }
  const fN2d = Math.max(0, 1 - fO2 - fHe);
  const den = Math.max(0.001, fN2d + fHe);
  const coeffN2 = fN2d / den;
  const coeffHe = fHe / den;
  const inspN2Start = Math.max(0, pAmbStart - setpoint - WATER_VAPOR) * coeffN2;
  const inspHeStart = Math.max(0, pAmbStart - setpoint - WATER_VAPOR) * coeffHe;
  return {
    inspN2Start,
    inspHeStart,
    rN2: coeffN2 * pressureRate,
    rHe: coeffHe * pressureRate,
  };
}

function getSetpointBoundaryDepths(ccr, surfP) {
  const cfg = normalizeCCRSettings(ccr);
  if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout || cfg.circuit === 'pSCR') return [];
  const descSP = cfg.descentSetpoint != null ? cfg.descentSetpoint : 0.7;
  const bottomSP = cfg.bottomSetpoint != null ? cfg.bottomSetpoint : 1.2;
  const decoSP = cfg.decoSetpoint != null ? cfg.decoSetpoint : (cfg.setpoint != null ? cfg.setpoint : 1.3);
  return [descSP, bottomSP, decoSP]
    .map(sp => depthAtSetpointCrossing(sp, surfP))
    .filter(d => d != null);
}

function splitLinearDepthAtBoundaries(fromDepth, toDepth, boundaryDepths) {
  const lo = Math.min(fromDepth, toDepth);
  const hi = Math.max(fromDepth, toDepth);
  const ascending = toDepth >= fromDepth;
  const interior = boundaryDepths
    .filter(d => d > lo + 1e-6 && d < hi - 1e-6)
    .sort((a, b) => ascending ? a - b : b - a);
  const pts = [fromDepth, ...interior, toDepth];
  const segs = [];
  for (let i = 0; i < pts.length - 1; i++) {
    if (Math.abs(pts[i] - pts[i + 1]) > 1e-6) segs.push({ fromDepth: pts[i], toDepth: pts[i + 1] });
  }
  return segs.length ? segs : [{ fromDepth, toDepth }];
}

function splitSegmentAtSetpoint(fromDepth, toDepth, setpoint, surfP) {
  if (!setpoint || setpoint <= 0) return [{ fromDepth, toDepth }];
  const cross = depthAtSetpointCrossing(setpoint, surfP);
  if (cross == null) return [{ fromDepth, toDepth }];
  const lo = Math.min(fromDepth, toDepth);
  const hi = Math.max(fromDepth, toDepth);
  if (cross <= lo + 1e-6 || cross >= hi - 1e-6) return [{ fromDepth, toDepth }];
  if (cross > lo && cross < hi) {
    return [
      { fromDepth, toDepth: cross },
      { fromDepth: cross, toDepth },
    ];
  }
  return [{ fromDepth, toDepth }];
}

function schreinerLinearCCR(p0, ht, t, p0Amb, R, setpoint, fO2, fHe, ccr, isHe) {
  const params = getCCRInertSchreinerParams(p0Amb, setpoint, fO2, fHe, R, ccr);
  const pStart = isHe ? params.inspHeStart : params.inspN2Start;
  const rate = isHe ? params.rHe : params.rN2;
  const k = Math.LN2 / ht;
  return pStart + rate * (t - 1 / k) - (pStart - p0 - rate / k) * Math.exp(-k * t);
}

function saturateLinearCCR(tissues, fromDepth, toDepth, t, fO2, fHe, ccr) {
  if (t <= 0) return tissues;
  const cfg = normalizeCCRSettings(ccr);
  const surfP = altSurfaceP;
  const phase = cfg.ccrPhase || null;
  if (Math.abs(fromDepth - toDepth) < 1e-9) {
    return saturateCCR(tissues, fromDepth, t, fO2, fHe, cfg);
  }
  const segments = splitLinearDepthAtBoundaries(fromDepth, toDepth, getSetpointBoundaryDepths(cfg, surfP));
  let out = tissues;
  const totalTime = t;
  const totalDist = Math.abs(toDepth - fromDepth) || 1e-9;
  for (const seg of segments) {
    const segTime = Math.abs(seg.toDepth - seg.fromDepth) / totalDist * totalTime;
    if (!(segTime > 0)) continue;
    const p0Amb = depthBar(seg.fromDepth);
    const pEndAmb = depthBar(seg.toDepth);
    const R = (pEndAmb - p0Amb) / segTime;
    // [AUDIT-REG-07] setpoint sampled at deep segment endpoint (ascent uses fromDepth)
    const endpointDepth = seg.fromDepth < seg.toDepth ? seg.toDepth : seg.fromDepth;
    const segSP = getEffectiveSetpointAtDepth(endpointDepth, cfg, surfP, phase);
    const segCcr = { ...cfg, setpoint: segSP };
    out = out.map((t0, i) => ({
      pN2: schreinerLinearCCR(t0.pN2, ZHL16C[i][0], segTime, p0Amb, R, segSP, fO2, fHe, segCcr, false),
      pHe: fHe > 0 ? schreinerLinearCCR(t0.pHe, ZHL16C_HE_HT[i], segTime, p0Amb, R, segSP, fO2, fHe, segCcr, true) : t0.pHe,
    }));
  }
  return out;
}

function saturateCCR(tissues, depthM, t, fO2, fHe, ccr) {
  if (t <= 0) return tissues;
  const cfg = normalizeCCRSettings(ccr);
  const pAmb = depthBar(depthM);
  const phase = cfg.ccrPhase || null;
  const sp = getEffectiveSetpointAtDepth(depthM, cfg, altSurfaceP, phase);
  const segCcr = { ...cfg, setpoint: sp };
  const insp = getInspiredInertPressures(pAmb, sp, fO2, fHe, segCcr);
  return tissues.map((t0, i) => ({
    pN2: schreiner(t0.pN2, insp.pN2, ZHL16C[i][0], t),
    pHe: schreiner(t0.pHe, insp.pHe, ZHL16C_HE_HT[i], t),
  }));
}

function loadTissuesWithCCR(tissues, fromDepth, toDepth, time, fO2, fHe, ccr, constantDepth) {
  const cfg = normalizeCCRSettings(ccr);
  if (cfg.setpoint === 0 && !cfg.bailout && isRebreatherCircuit(cfg.circuit)) {
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    if (constantDepth || Math.abs(fromDepth - toDepth) < 1e-6) {
      return saturate(tissues, fromDepth, time, fN2, fHe);
    }
    return saturateLinear(tissues, fromDepth, toDepth, time, fN2, fHe);
  }
  if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout) {
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    if (constantDepth || Math.abs(fromDepth - toDepth) < 1e-6) {
      return saturate(tissues, fromDepth, time, fN2, fHe);
    }
    return saturateLinear(tissues, fromDepth, toDepth, time, fN2, fHe);
  }
  if (constantDepth || Math.abs(fromDepth - toDepth) < 1e-6) {
    return saturateCCR(tissues, fromDepth, time, fO2, fHe, cfg);
  }
  return saturateLinearCCR(tissues, fromDepth, toDepth, time, fO2, fHe, cfg);
}

function getEffectivePpo2(pAmb, setpoint, fO2, ccr, depthM, fHe) {
  const cfg = normalizeCCRSettings(ccr);
  if (cfg.bailout || !isRebreatherCircuit(cfg.circuit)) return fO2 * pAmb;
  if (cfg.circuit === 'pSCR') {
    const fHeVal = fHe != null ? fHe : 0;
    const fr = computePSCRFractions(pAmb, fO2, fHeVal, cfg);
    return fr.fO2 * pAmb;
  }
  const surfPRef = (typeof altSurfaceP !== 'undefined' ? altSurfaceP : 1.01325);
  const depthFromAmb = depthM != null ? depthM : (pAmb - surfPRef) / BAR_PER_METRE;
  const sp = setpoint != null ? setpoint : getEffectiveSetpointAtDepth(depthFromAmb, cfg, surfPRef);
  const pDry = Math.max(0, pAmb - WATER_VAPOR);
  const dilPpo2 = fO2 * pAmb;
  return Math.min(pDry, Math.max(sp, dilPpo2));
}


function getGasLabel(fO2, fHe) {
  if (fO2 === null || fO2 === undefined) return null;
  if (fO2 >= 0.995) return '100%';
  const o2pct = Math.round(fO2 * 100);
  const hePct = Math.round((fHe || 0) * 100);
  if (o2pct === 21 && hePct === 0) return 'Air';
  return `${o2pct}/${String(hePct).padStart(2, '0')}`;
}

function runZhlScheduleCore(params) {
  applyEnvironment(params.environment || defaultEnvironment());
  const depthM = params.depthM;
  const bt = params.bt;
  const rate = params.ascentRate;
  const decoRate = params.decoAscentRate ?? 3;
  const surfaceRate = params.surfaceAscentRate ?? 3;
  const descentRate = params.descentRate;
  const gfL = params.gfL;
  const gfH = params.gfH;
  const ppo2Bottom = params.ppo2Bottom;
  const ppo2Deco = params.ppo2Deco;
  const minStopT = params.minStopTime;
  const switchPauseT = params.switchPauseT || 0;
  const mdCompatMode = params.mdCompatMode !== false;
  const wholeMinStops = params.wholeMinStops !== false;
  function stopRoundGrid() { return params.wholeMinStops === true ? 1 : minStopT; }
  function snapStopToGrid(stopT) {
    if (!wholeMinStops) return stopT;
    const grid = stopRoundGrid();
    return Math.max(minStopT, Math.ceil((stopT - 1e-9) / grid) * grid);
  }
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
  const ccrSettings = params.ccr ? normalizeCCRSettings(params.ccr) : null;
  const _zhlOnLoop = !!(params.onLoop && ccrSettings && isRebreatherCircuit(ccrSettings.circuit) && !ccrSettings.bailout);
  const loopMixLabel = params.loopMixLabel || (ccrSettings ? loopMixLabelForCore(bottomMixLabel, ccrSettings) : bottomMixLabel);
  // CCR-loop elapsed time only (OC segments do not increment).
  let _ccrLoopElapsedMin = 0;
  let hitSafetyGuard = false;
  const CEILING_LOOP_GUARD_MIN = 1440;

  function zhlLoadLinear(tissues, from, to, t, fO2, fHe, onLoop, phase) {
    if (onLoop && ccrSettings) {
      const out = loadTissuesWithCCR(tissues, from, to, t, fO2, fHe, { ...ccrSettings, scrRuntimeMin: _ccrLoopElapsedMin, ccrPhase: phase });
      _ccrLoopElapsedMin += t;
      return out;
    }
    return saturateLinear(tissues, from, to, t, Math.max(0, 1 - fO2 - (fHe || 0)), fHe || 0);
  }
  function zhlLoadConst(tissues, depth, t, fO2, fHe, onLoop, phase) {
    if (onLoop && ccrSettings) {
      const out = loadTissuesWithCCR(tissues, depth, depth, t, fO2, fHe, { ...ccrSettings, scrRuntimeMin: _ccrLoopElapsedMin, ccrPhase: phase });
      _ccrLoopElapsedMin += t;
      return out;
    }
    return saturate(tissues, depth, t, Math.max(0, 1 - fO2 - (fHe || 0)), fHe || 0);
  }
  function zhlOnLoopAt() { return !!_zhlOnLoop; }
  function zhlStepPpo2(depthM, fN2, fHe, phase) {
    if (_zhlOnLoop && ccrSettings) {
      const sp = getEffectiveSetpointAtDepth(depthM, ccrSettings, altSurfaceP, phase || (decoZoneEntered ? 'deco' : 'bottom'));
      if (sp > 0) return sp;
    }
    return ppO2Check(depthM, fN2, fHe);
  }
  function zhlGasAt(depthM) {
    if (_zhlOnLoop) {
      return { fN2: bottomFN2, fHe: bottomFHe, fO2: bottomFO2, label: bottomMixLabel };
    }
    const baseN2 = _zhlActiveGas ? _zhlActiveGas.fN2 : bottomFN2;
    const baseHe = _zhlActiveGas ? _zhlActiveGas.fHe : bottomFHe;
    const baseLabel = _zhlActiveGas ? _zhlActiveGas.label : bottomMixLabel;
    return getActiveGas(depthM, baseN2, baseHe, decoGases, getPPO2Limit, baseLabel);
  }

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
  // DOM schedule writes window._zhlRepState after each Bühlmann run; repState is
  // injected when the user enables the repetitive-dive checkbox.
  if (params.repState && Array.isArray(params.repState.tissues)) {
    const rep = params.repState;
    for (let i = 0; i < tissues.length && i < rep.tissues.length; i++) {
      tissues[i].pN2 = rep.tissues[i].pN2;
      tissues[i].pHe = rep.tissues[i].pHe || 0;
    }
    if (rep.surfaceIntervalMin > 0) {
      const siMin = rep.surfaceIntervalMin;
      const wv = WATER_VAPOR || 0.0627;
      const repSurfP = rep.surfaceP != null
        ? rep.surfaceP
        : (altAcclimatized !== false ? (altSurfaceP || SEA_LEVEL_P) : SEA_LEVEL_P);
      const inspN2 = 0.7902 * (repSurfP - wv);
      for (let i = 0; i < tissues.length; i++) {
        const kN2 = Math.LN2 / ZHL16C[i][0];
        const htHe = ZHL16C_HE_HT[i];
        if (!(htHe > 0)) throw new Error('ZHL16C_HE_HT missing compartment ' + i);
        const kHe = Math.LN2 / htHe;
        tissues[i].pN2 = inspN2 + (tissues[i].pN2 - inspN2) * Math.exp(-kN2 * siMin);
        tissues[i].pHe = (tissues[i].pHe || 0) * Math.exp(-kHe * siMin);
      }
    }
  }

  // Descent phase — split by travel gas switch depth if travel gas is active
  const descentTime = depthM / descentRate;
  if (travelInfo && travelSwitchM > 0 && travelSwitchM < depthM) {
    const travelFHe = travelInfo.fHe || 0;
    let travelFO2;
    if (travelInfo.fO2 != null) {
      travelFO2 = travelInfo.fO2;
    } else {
      const inferred = 1 - travelInfo.fN2 - travelFHe;
      if (inferred < -1e-9) throw new Error('travelInfo gas fractions invalid: fN2 + fHe > 1');
      travelFO2 = Math.max(0, inferred);
    }
    // Phase 1: surface → travel switch depth on travel gas
    const travelDescentTime = travelSwitchM / descentRate;
    tissues = zhlLoadLinear(tissues, 0, travelSwitchM, travelDescentTime, travelFO2, travelFHe, _zhlOnLoop, 'descent');
    // Phase 2: travel switch depth → bottom on bottom gas
    const bottomDescentTime = (depthM - travelSwitchM) / descentRate;
    tissues = zhlLoadLinear(tissues, travelSwitchM, depthM, bottomDescentTime, bottomFO2, bottomFHe, _zhlOnLoop, 'descent');
  } else {
    // No travel gas or switch depth >= bottom: entire descent on bottom gas
    tissues = zhlLoadLinear(tissues, 0, depthM, descentTime, bottomFO2, bottomFHe, _zhlOnLoop, 'descent');
  }

  // Bottom time input = total time from leaving surface (industry standard).
  // Subtract descent time to get actual time spent at depth.
  const btAtDepth = Math.max(0, bt - descentTime);
  tissues = zhlLoadConst(tissues, depthM, btAtDepth, bottomFO2, bottomFHe, _zhlOnLoop, 'bottom');
  const tissuesAtBottom = [...tissues]; // snapshot for ceiling graph overlay (deepest level only; ML phases not included)

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
  let carriedFirstStopDepth = 0;
  let _zhlActiveGas = null; // continuation-level mix carried until deco-gas switch

  // gfAt must live outside the phase loop — block-scoped function declarations are
  // not visible after the loop in strict mode (Tier 3 bundle uses 'use strict').
  // [AUDIT-REG-06] pre-anchor gfAt returns gfL for Baker first-stop search
  function gfAt(depthM) {
    if (!firstStopDepth || firstStopDepth <= 0) return gfL;
    return gfAtDepth(depthM, gfL, gfH, firstStopDepth, lastStop, !!params.shallowGradient);
  }

  for (let _zhlPhaseIdx = 0; _zhlPhaseIdx < _zhlAscentFloors.length; _zhlPhaseIdx++) {
  const _zhlAscentFloor = _zhlAscentFloors[_zhlPhaseIdx];
  firstStopDepth = carriedFirstStopDepth;

  // ── GF anchor: candidate stop list built from ceiling(bottom_tissues, gfL) ──
  // firstStopDepth is NOT pre-computed here — it is anchored dynamically at the
  // FIRST depth where mustStop actually fires. This matches MultiDeco/Baker:
  // GF line is pinned at the actual first required stop, not at a pre-computed
  // ceiling that may be one step above the real first stop.
  const bottomCeil = ceiling(tissues, gfL);
  const candidateFirstStop = bottomCeil > 0
    ? Math.max(lastStop, Math.ceil((bottomCeil + 1e-9) / decoStep) * decoStep)
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

  let prevEngineGas = _zhlActiveGas ? _zhlActiveGas.label : bottomMixLabel; // track gas for switch pause
  let decoZoneEntered = false; // set when ceiling-forced or min-stop deco actually begins

  // firstSwitchDepth — find first deco gas switch depth
  let firstDecoDepth   = null;
  let firstSwitchDepth = null;
  {
    let simCur = cur;
    let simPrevGas = bottomMixLabel;
    for (const sd of stopDepths) {
      if (simCur > sd) simCur = sd;
      const gas2 = zhlGasAt(simCur);
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
    let legTransitDur = 0;
    if (cur > stopDepth) {
      const travelGas = zhlGasAt(cur);
      const travelRate = decoZoneEntered ? decoRate : rate;
      const travelDur = (cur - stopDepth) / travelRate;
      legTransitDur = travelDur;
      const travelOnLoop = zhlOnLoopAt();
      const travelPhase = decoZoneEntered ? 'deco' : 'bottom';
      if (decoZoneEntered && mdCompatMode) {
        // MultiDeco-compatible mode: treat deco-zone transit as instant for tissue loading.
        // Transit time is still counted in RT and added to the displayed stop duration below.
        // (Schreiner mode: tissues off-gas normally during transit — more accurate.)
        if (travelOnLoop && ccrSettings && isRebreatherCircuit(ccrSettings.circuit)) _ccrLoopElapsedMin += travelDur;
      } else {
        const tFO2 = travelOnLoop ? bottomFO2 : (travelGas.fO2 != null ? travelGas.fO2 : Math.max(0, 1 - travelGas.fN2 - (travelGas.fHe || 0)));
        const tFHe = travelOnLoop ? bottomFHe : (travelGas.fHe || 0);
        tissues = zhlLoadLinear(tissues, cur, stopDepth, travelDur, tFO2, tFHe, travelOnLoop, travelPhase);
      }
      steps.push({
        type: 'ascent', from: cur, to: stopDepth,
        dur: travelDur, gas: travelOnLoop ? loopMixLabel : travelGas.label,
        pO2: zhlStepPpo2(cur, travelGas.fN2, travelGas.fHe || 0, travelPhase),
        fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
        decoTransit: decoZoneEntered && mdCompatMode && firstDecoDepth !== null
      });
      rt  += travelDur;
      cur  = stopDepth;
    }

    // Transit time for minimum stop rounding (ApexDeco style):
    // si=0: actual ascent time to this stop (fast rate before deco zone)
    // si>0: travelled at decoRate between stops
    const transitDur = (si === 0) ? legTransitDur : (stopDepths[si - 1] - stopDepth) / decoRate;

    // Select best gas available at this stop depth
    const stopGas  = zhlGasAt(cur);
    const onLoop = zhlOnLoopAt();
    const stopFN2  = onLoop ? bottomFN2 : stopGas.fN2;
    const stopFHe  = onLoop ? bottomFHe : (stopGas.fHe || 0);
    const stopFO2  = onLoop ? bottomFO2 : (stopGas.fO2 != null ? stopGas.fO2 : Math.max(0, 1 - stopFN2 - stopFHe));
    const gasLabel = onLoop ? loopMixLabel : stopGas.label;

    // Gas switch pause — saturate tissues at this depth during the switch
    if (gasLabel !== prevEngineGas && switchPauseT > 0) {
      tissues = zhlLoadConst(tissues, cur, switchPauseT, stopFO2, stopFHe, onLoop, 'deco');
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
        carriedFirstStopDepth = cur;
        minStopZoneDepth = cur;  // enable min-stop enforcement from here down
      }
      decoZoneEntered = true;
      // Capture RT before ceiling loop — ApexDeco snaps the arrival RT to next minute
      const rtOnArrival = rt;
      let stopT = 0;
      while (ceiling(tissues, gfForClear) > ceilTarget && stopT < CEILING_LOOP_GUARD_MIN) {
        tissues = zhlLoadConst(tissues, cur, holdStep, stopFO2, stopFHe, onLoop, 'deco');
        stopT += holdStep; rt += holdStep;
      }
      if (stopT >= CEILING_LOOP_GUARD_MIN && ceiling(tissues, gfForClear) > ceilTarget) hitSafetyGuard = true;
      if (isFirstDecoStop) {
        // First stop: always use RT-snap (fractional) — both ApexDeco and MultiDeco
        // keep the exact first-stop time (e.g. 0:33, 0:27) regardless of rounding mode.
        const rawRounded = Math.round(stopT * 60) / 60;
        const minFirstStop = Math.round((Math.ceil(rtOnArrival / minStopT) * minStopT - rtOnArrival) * 60) / 60;
        const actualStop = Math.max(rawRounded, minFirstStop);
        if (actualStop > stopT) {
          const extra = actualStop - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          rt += extra; stopT = actualStop;
        }
        if (stopT < 1/60) { tissues = zhlLoadConst(tissues, cur, 1/60 - stopT, stopFO2, stopFHe, onLoop, 'deco'); rt += 1/60 - stopT; stopT = 1/60; }
      } else {
        let roundedStop;
        if (wholeMinStops) {
          const grid = stopRoundGrid();
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitDur + stopT - 1e-9) / grid) * grid);
          roundedStop = totalAtLevel - transitDur;
        } else {
          roundedStop = stopT;
        }
        if (roundedStop > stopT) {
          const extra = roundedStop - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          rt += extra; stopT = roundedStop;
        }
        // Enforce minimum stop time — every non-first deco stop gets at least minStopT
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          rt += extra; stopT = minStopT;
        }
      }
      const mustStopDisplay = (mdCompatMode && !isFirstDecoStop) ? stopT + transitDur : stopT;
      steps.push({ type: 'deco', depth: cur, dur: mustStopDisplay, gas: gasLabel, pO2: zhlStepPpo2(cur, stopFN2, stopFHe, 'deco'), fN2: stopFN2, fHe: stopFHe, hitSafetyGuard: hitSafetyGuard || undefined, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
    } else if (minStopT > 0 && minStopZoneDepth !== null && cur <= minStopZoneDepth && cur !== lastStop) {
      decoZoneEntered = true;
      let stopT = 0;
      if (isFirstDecoStop) {
        if (firstDecoDepth === null) {
          firstDecoDepth = cur;
          firstStopDepth = cur;
          carriedFirstStopDepth = cur;
          minStopZoneDepth = cur;
        }
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
        tissues = zhlLoadConst(tissues, cur, stopT, stopFO2, stopFHe, onLoop, 'deco');
        rt += stopT;
      }
      while (ceiling(tissues, gfForClear) > ceilTarget && stopT < CEILING_LOOP_GUARD_MIN) {
        tissues = zhlLoadConst(tissues, cur, minStopT, stopFO2, stopFHe, onLoop, 'deco');
        stopT += minStopT; rt += minStopT;
      }
      if (stopT >= CEILING_LOOP_GUARD_MIN && ceiling(tissues, gfForClear) > ceilTarget) hitSafetyGuard = true;
      if (!isFirstDecoStop) {
        // Round up and enforce minimum — only for non-first stops
        if (wholeMinStops) {
          const grid = stopRoundGrid();
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitDur + stopT - 1e-9) / grid) * grid);
          const roundedStop = totalAtLevel - transitDur;
          if (roundedStop > stopT) {
            const extra = roundedStop - stopT;
            tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
            rt += extra; stopT = roundedStop;
          }
        }
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          rt += extra; stopT = minStopT;
        }
      }
      if (stopT > 0) {
        const minStopDisplay = (mdCompatMode && !isFirstDecoStop) ? stopT + transitDur : stopT;
        steps.push({ type: 'deco', depth: cur, dur: minStopDisplay, gas: gasLabel, pO2: zhlStepPpo2(cur, stopFN2, stopFHe, 'deco'), fN2: stopFN2, fHe: stopFHe, hitSafetyGuard: hitSafetyGuard || undefined, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
      }
    } else if (cur === lastStop) {
      const isDecoNeeded = steps.some(s => s.type === 'deco');
      const stopType = isDecoNeeded ? 'deco' : 'safety';
      const isFinalAscentPhase = (_zhlPhaseIdx >= _zhlAscentFloors.length - 1);
      const lastClearGf = isFinalAscentPhase ? gfAt(0) : gfAt(floorStopMin);
      const lastCeilTarget = isFinalAscentPhase ? 0 : floorStopMin;
      let stopT = 0;
      let transitToLastStop = 0;
      if (isDecoNeeded) {
        transitToLastStop = (stopDepths.length > 1) ? (stopDepths[stopDepths.length - 2] - lastStop) / decoRate : 0;
        while (ceiling(tissues, lastClearGf) > lastCeilTarget + 0.01 && stopT < CEILING_LOOP_GUARD_MIN) {
          tissues = zhlLoadConst(tissues, cur, minStopT, stopFO2, stopFHe, onLoop, 'deco');
          stopT += minStopT; rt += minStopT;
        }
        if (stopT >= CEILING_LOOP_GUARD_MIN && ceiling(tissues, lastClearGf) > lastCeilTarget + 0.01) hitSafetyGuard = true;
        let roundedLastStop;
        if (wholeMinStops) {
          const grid = stopRoundGrid();
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitToLastStop + stopT - 1e-9) / grid) * grid);
          roundedLastStop = totalAtLevel - transitToLastStop;
        } else {
          roundedLastStop = stopT;
        }
        if (roundedLastStop > stopT) {
          const extra = roundedLastStop - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          stopT += extra; rt += extra;
        }
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          stopT += extra; rt += extra;
        }
      } else {
        stopT = Math.max(3, minStopT);
        tissues = zhlLoadConst(tissues, cur, stopT, stopFO2, stopFHe, onLoop, 'deco');
        rt += stopT;
      }
      const lastStopDisplay = mdCompatMode ? stopT + transitToLastStop : stopT;
      steps.push({ type: stopType, depth: cur, dur: lastStopDisplay, gas: gasLabel, pO2: zhlStepPpo2(cur, stopFN2, stopFHe, 'deco'), fN2: stopFN2, fHe: stopFHe, hitSafetyGuard: hitSafetyGuard || undefined, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
    }
    // No stop needed and not lastStop — continue ascending
    if (_zhlAscentFloor > 0 && cur <= _zhlAscentFloor && stopDepth <= _zhlAscentFloor) break;
  }

  if (_zhlAscentFloor > 0 && cur > _zhlAscentFloor) {
    const travelRate = decoZoneEntered ? decoRate : rate;
    const travelDur = (cur - _zhlAscentFloor) / travelRate;
    const travelGas = zhlGasAt(cur);
    const travelOnLoop = zhlOnLoopAt();
    const tFO2 = travelOnLoop ? bottomFO2 : (travelGas.fO2 != null ? travelGas.fO2 : Math.max(0, 1 - travelGas.fN2 - (travelGas.fHe || 0)));
    const tFHe = travelOnLoop ? bottomFHe : (travelGas.fHe || 0);
    tissues = zhlLoadLinear(tissues, cur, _zhlAscentFloor, travelDur, tFO2, tFHe, travelOnLoop, 'deco');
    steps.push({
      type: 'ascent', from: cur, to: _zhlAscentFloor,
      dur: travelDur, gas: travelOnLoop ? loopMixLabel : travelGas.label,
      pO2: zhlStepPpo2(cur, travelGas.fN2, travelGas.fHe || 0, 'deco'),
      fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
    });
    rt += travelDur;
    cur = _zhlAscentFloor;
  } else if (_zhlAscentFloor === 0 && cur > 0) {
    const finalAscentDur = cur / surfaceRate;
    const finalGas = zhlGasAt(cur);
    const finalOnLoop = zhlOnLoopAt();
    const fFO2 = finalOnLoop ? bottomFO2 : (finalGas.fO2 != null ? finalGas.fO2 : Math.max(0, 1 - finalGas.fN2 - (finalGas.fHe || 0)));
    const fFHe = finalOnLoop ? bottomFHe : (finalGas.fHe || 0);
    tissues = zhlLoadLinear(tissues, cur, 0, finalAscentDur, fFO2, fFHe, finalOnLoop, 'deco');
    steps.push({
      type: 'ascent', from: cur, to: 0,
      dur: finalAscentDur, gas: finalOnLoop ? loopMixLabel : finalGas.label,
      pO2: zhlStepPpo2(cur, finalGas.fN2, finalGas.fHe || 0, 'deco'),
      fN2: finalGas.fN2, fHe: finalGas.fHe || 0,
    });
    rt += finalAscentDur;
    cur = 0;
  }

  if (_zhlPhaseIdx < _zhlContLevels.length) {
    const cont = _zhlContLevels[_zhlPhaseIdx];
    if (cont.depth > cur) {
      throw new Error('continuationLevel must be shallower than current depth');
    }
    cur = cont.depth;
    const cO2 = cont.o2 / 100;
    const cHe = (cont.he || 0) / 100;
    const cN2 = Math.max(0, 1 - cO2 - cHe);
    tissues = zhlLoadConst(tissues, cur, cont.time, cO2, cHe, _zhlOnLoop, 'bottom');
    rt += cont.time;
    steps.push({
      type: 'bottom', depth: cur, dur: cont.time,
      gas: getGasLabel(cO2, cHe), pO2: (+ppO2Check(cur, cN2, cHe)).toFixed(2),
      fN2: cN2, fHe: cHe,
    });
    _zhlActiveGas = { fN2: cN2, fHe: cHe, fO2: cO2, label: getGasLabel(cO2, cHe) };
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
      prev.decoTransit = !!(prev.decoTransit || s.decoTransit);
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

  // Reconcile runtime and tissues with min-deco stop extensions/injections.
  const _mdpStepDepthM = (s) => {
    const raw = s.depth ?? s.from ?? s.to;
    if (raw == null) return null;
    return _mdpIsMetric ? raw : raw / 3.28084;
  };
  const _sumDecoAtDepth = (steps, targetM) => steps
    .filter(s => (s.type === 'deco' || s.type === 'safety')
      && _mdpStepDepthM(s) != null
      && Math.abs(_mdpStepDepthM(s) - targetM) < 0.25)
    .reduce((a, s) => a + s.dur, 0);
  const _origDecoTime = collapsed
    .filter(s => s.type === 'deco' || s.type === 'safety')
    .reduce((a, s) => a + s.dur, 0);
  const _mdpDecoTime = collapsedMDP
    .filter(s => s.type === 'deco' || s.type === 'safety')
    .reduce((a, s) => a + s.dur, 0);
  for (const targetM of [9, 6]) {
    const delta = _sumDecoAtDepth(collapsedMDP, targetM) - _sumDecoAtDepth(collapsed, targetM);
    if (delta <= 1e-9) continue;
    const step = collapsedMDP.find(s => (s.type === 'deco' || s.type === 'safety')
      && _mdpStepDepthM(s) != null
      && Math.abs(_mdpStepDepthM(s) - targetM) < 0.25);
    if (!step) continue;
    const fHe = step.fHe ?? bottomFHe ?? 0;
    const fN2 = step.fN2 ?? bottomFN2;
    const fO2 = Math.max(0, 1 - fN2 - fHe);
    tissues = zhlLoadConst(tissues, step.depth, delta, fO2, fHe, _zhlOnLoop, 'deco');
  }
  rt += _mdpDecoTime - _origDecoTime;

  const decoStops = collapsedMDP.filter(s => s.type === 'deco');
  const decoTime  = Math.round(decoStops.reduce((a, s) => a + s.dur, 0) * 60) / 60;
  const hasDeco   = decoStops.length > 0;
  const gasUsed   = [...new Set(collapsedMDP.map(s => s.gas))];

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
    steps: collapsedMDP,
    decoZoneStart: trueDecoZoneStart,
    firstStopDepth: firstStopDepth || 0,
    finalTissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0 })),  // for ZHL repetitive dive carry
    surfaceGF: computeSurfaceGF(tissues),
    hitSafetyGuard: hitSafetyGuard || undefined,
  };

  return {
    hitSafetyGuard,
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




  const _scheduleCoreGetGasLabel = getGasLabel;

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
      travelInfo: s.travelInfo || null,
      repState: (s._preTissues && s._preTissues.length)
        ? {
            tissues: s._preTissues,
            surfaceIntervalMin: s._surfaceInterval || 0,
            surfaceP: (environment || defaultEnvironment()).altSurfaceP,
          }
        : null,
      continuationLevels: (profileSplit && profileSplit.continuation) || [],
      minDecoProfile: s.minDecoProfile || { enabled: false, m9: 1, m6: 3, isMetric: metric !== false },
      decoGases: gases,
      environment: environment || defaultEnvironment(),
      ccr: {
        circuit: s.circuit || 'OC',
        setpoint: s.setpoint,
        descentSetpoint: s.descentSetpoint,
        bottomSetpoint: s.bottomSetpoint,
        decoSetpoint: s.decoSetpoint != null ? s.decoSetpoint : s.setpoint,
        bailout: !!s.bailout,
        bailoutGfLow: s.bailoutGfLow,
        bailoutGfHigh: s.bailoutGfHigh,
        scrLoopVolume: s.scrLoopVolume,
        scrMetabolicO2: s.scrMetabolicO2,
        sacStress: s.sacStress,
        sacDecoCcr: s.sacDecoCcr,
        stressTimeMin: s.stressTimeMin,
        problemSolveMin: s.problemSolveMin,
      },
      onLoop: isRebreatherCircuit(s.circuit || 'OC') && !s.bailout,
    };
  }

  function addHeadlessExposure(hCNSfrac, hOTU, ppO2, dur) {
    if (ppO2 > 0.5 && dur > 0) {
      hOTU.v += dur * Math.pow((ppO2 - 0.5) / 0.5, OTU_EXPONENT);
      if (ppO2 >= 1.6) {
        hCNSfrac.v += dur / 45;
        return;
      }
      const lims = {6:720,7:570,8:450,9:360,10:300,11:240,12:210,13:180,14:150,15:120,16:45};
      const lo = Math.floor(ppO2 * 10), hi = lo + 1;
      const lim = (lims[lo] || 0) + ((lims[hi] || 0) - (lims[lo] || 0)) * (ppO2 * 10 - lo);
      const safeLim = lim > 0 ? lim : 45;
      hCNSfrac.v += dur / safeLim;
    }
  }

  function headlessSegPpo2(depthM, fO2, fHe, s) {
    const pAmb = altSurfaceP + depthM * BAR_PER_METRE;
    const cfg = normalizeCCRSettings(s);
    if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout) return fO2 * pAmb;
    if (cfg.circuit === 'pSCR') {
      const fr = computePSCRFractions(pAmb, fO2, fHe, cfg);
      return fr.fO2 * pAmb;
    }
    const sp = getEffectiveSetpointAtDepth(depthM, cfg, altSurfaceP);
    return Math.min(pAmb, Math.max(sp, fO2 * pAmb));
  }

  function computeHeadlessCnsOtu(lp, level, s) {
    if (!lp || lp.totalCNS != null) return;
    const fO2bot = level.o2 / 100;
    const fHebot = (level.he || 0) / 100;
    const onLoop = isRebreatherCircuit(s.circuit || 'OC') && !s.bailout;
    const hCNSfrac = { v: 0 };
    const hOTU = { v: 0 };
    const hDescentRate = s.descentRate || 20;
    const hDescentTime = level.depth / hDescentRate;
    const ppO2DescMid = onLoop
      ? headlessSegPpo2(level.depth / 2, fO2bot, fHebot, s)
      : (altSurfaceP + (level.depth / 2) * BAR_PER_METRE) * fO2bot;
    const ppO2Bottom = onLoop
      ? headlessSegPpo2(level.depth, fO2bot, fHebot, s)
      : (altSurfaceP + level.depth * BAR_PER_METRE) * fO2bot;
    addHeadlessExposure(hCNSfrac, hOTU, ppO2DescMid, hDescentTime);
    const btAtDepthMin = Math.max(0, level.time - hDescentTime);
    addHeadlessExposure(hCNSfrac, hOTU, ppO2Bottom, btAtDepthMin);
    (lp.steps || []).forEach(seg => {
      if (seg.decoTransit) return; // mdCompatMode: transit folded into stop display
      const d = seg.depth != null ? seg.depth : (seg.type === 'ascent' ? (seg.from + seg.to) / 2 : 0);
      const fHeS = seg.fHe !== undefined ? seg.fHe : fHebot;
      const fO2s = seg.fN2 !== undefined ? Math.max(0, 1 - seg.fN2 - fHeS) : fO2bot;
      const ppO2 = onLoop
        ? headlessSegPpo2(d, fO2s, fHeS, s)
        : fO2s * (altSurfaceP + d * BAR_PER_METRE);
      addHeadlessExposure(hCNSfrac, hOTU, ppO2, seg.dur || 0);
    });
    lp.totalCNS = parseFloat((hCNSfrac.v * 100).toFixed(1));
    lp.totalOTU = Math.round(hOTU.v);
  }

  function mapToEngineReturn(lp, level, s, isMetric) {
    const fO2bot = level.o2 / 100;
    const stops = (lp.stops || []).map(st => ({
      depth: st.depth, time: st.dur, gas: st.gas, type: 'stop',
    }));
    const plan = (lp.steps || [])
      .filter(st => !(st.type === 'ascent' && st.decoTransit))
      .map(st => ({
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
      const btAtDepthMin = Math.max(0, level.time - descentTime);
      const bottomGasLabel = getGasLabel(fO2bot, (level.he || 0) / 100);
      plan.unshift({ type: 'bottom', depth: level.depth, time: btAtDepthMin, run: descentTime + btAtDepthMin, gas: bottomGasLabel, o2: level.o2, he: level.he || 0 });
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
    applyEnvironment(environment || defaultEnvironment());
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
    setHeHalfTimeMode,
    OTU_EXPONENT,
    PSCR_MIN_PPO2,
    PSCR_LOOP_VOLUME_MIN,
    PSCR_LOOP_VOLUME_MAX,
    PSCR_METABOLIC_O2_MIN,
    PSCR_METABOLIC_O2_MAX,
    ZHL16C,
    ZHL16C_HE_HT,
    ZHL16C_HE_HT_BAKER,
    ZHL16C_HE_HT_BUHL2003,
    ZHL16C_HE_AB,
    initTissues,
    depthBar,
    schreiner,
    schreinerLinear,
    saturateLinear,
    saturate,
    ceiling,
    computeSurfaceGF,
    ambientCrossingDepth,
    gfAtDepth,
    ndlClearAtDepth,
    buhNDL,
    getActiveGas,
    enforceMinDecoProfile,
    ppO2Check,
    n2FracFromCustomO2,
    n2FracFromPercentages,
    validateHypoxicDecoGas,
    canonicalCircuit,
    normalizeCCRSettings,
    isRebreatherCircuit,
    loopMixLabelForCore,
    depthAtSetpointCrossing,
    getEffectiveSetpointAtDepth,
    getCcrMetabolicO2Rate,
    computePSCRFractions,
    ccrLoopGasBelowSetpoint,
    getInspiredInertPressures,
    getCCRInertSchreinerParams,
    getSetpointBoundaryDepths,
    splitLinearDepthAtBoundaries,
    splitSegmentAtSetpoint,
    schreinerLinearCCR,
    saturateLinearCCR,
    saturateCCR,
    loadTissuesWithCCR,
    getEffectivePpo2,
    getGasLabel: _scheduleCoreGetGasLabel,
  };

  global.ZhlEngineBundle = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof self !== 'undefined' ? self : globalThis);
