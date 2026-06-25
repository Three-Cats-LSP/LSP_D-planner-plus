/**
 * CCR Bühlmann tissue loading (Tier 3) — pure functions, no DOM.
 * Included in zhl-engine-bundle.js preamble via tools/build_zhl_bundle.py.
 */
function normalizeCCRSettings(s) {
  s = s || {};
  return {
    circuit: s.circuit || 'OC',
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
  return circuit === 'CCR' || circuit === 'pSCR';
}

function loopMixLabelForCore(diluentLabel, ccr) {
  const cfg = normalizeCCRSettings(ccr);
  if (!isRebreatherCircuit(cfg.circuit) || cfg.bailout) return diluentLabel;
  if (typeof diluentLabel === 'string' && /^(CCR|pSCR)\s/i.test(diluentLabel)) return diluentLabel;
  const prefix = cfg.circuit === 'pSCR' ? 'pSCR' : 'CCR';
  return `${prefix} ${diluentLabel}`;
}

function depthAtSetpointCrossing(setpoint, surfP) {
  if (!setpoint || setpoint <= 0) return null;
  return Math.max(0, (setpoint + WATER_VAPOR - (surfP || altSurfaceP)) / BAR_PER_METRE);
}

function getEffectiveSetpointAtDepth(depthM, ccr, surfP, phase) {
  if (!ccr || ccr.bailout || !isRebreatherCircuit(ccr.circuit)) return 0;
  if (ccr.circuit === 'pSCR') return 0;
  const descSP = ccr.descentSetpoint != null ? ccr.descentSetpoint : 0.7;
  const bottomSP = ccr.bottomSetpoint != null ? ccr.bottomSetpoint : 1.2;
  const decoSP = ccr.decoSetpoint != null ? ccr.decoSetpoint : (ccr.setpoint != null ? ccr.setpoint : 1.3);
  if (phase === 'descent') return descSP;
  if (phase === 'bottom') return bottomSP;
  if (phase === 'deco' || phase === 'ascent') return decoSP;
  const pAmb = (surfP || altSurfaceP) + depthM * BAR_PER_METRE;
  // Phase-inferred fallback: use the setpoint appropriate for the current depth.
  // descSP activates when ambient hasn't reached the bottomSP level (shallow/descent);
  // bottomSP activates between those levels; decoSP at depth or on ascent.
  // Previous code used pAmb <= descSP + WATER_VAPOR (~0.76 bar) which is always
  // below surface pressure and made the descent setpoint unreachable.
  if (pAmb <= bottomSP) return descSP;
  if (pAmb <= decoSP) return bottomSP;
  return decoSP;
}

function getCcrMetabolicO2Rate(ccr) {
  const cfg = normalizeCCRSettings(ccr);
  const v = parseFloat(cfg.scrMetabolicO2);
  return v > 0 ? v : 1.5;
}

function computePSCRFractions(pAmb, fO2, fHe, runtimeMin, ccr) {
  fO2 = Math.max(0, Math.min(1, fO2 || 0));
  fHe = Math.max(0, Math.min(1 - fO2, fHe || 0));
  const fN2src = Math.max(0, 1 - fO2 - fHe);
  const sourceInert = Math.max(0.001, fHe + fN2src);
  if (sourceInert <= 0.001 && fO2 >= 0.999) return { fO2: 1, fHe: 0, fN2: 0 };
  const loopVol = ccr.scrLoopVolume || 7.0;
  const metO2 = getCcrMetabolicO2Rate(ccr);
  // Steady-state pSCR model: ppO2_loop = ppO2_supply - VO2/loopVol (Baker drop formula).
  // Previous model subtracted cumulative dive runtime × VO2 from a fixed loop volume,
  // which drove loop O2 to near-zero after a few minutes, zeroing N2 loading for the
  // rest of the dive. The steady-state formula is time-independent and depth-correct.
  const ppO2Drop = metO2 / loopVol;
  const ppO2Supply = fO2 * pAmb;
  const newPpO2 = Math.max(PSCR_MIN_PPO2, ppO2Supply - ppO2Drop);
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

function getInspiredInertPressures(pAmb, setpoint, fO2, fHe, ccr) {
  const ppH2O = WATER_VAPOR;
  const cfg = normalizeCCRSettings(ccr);
  if (cfg.bailout || !isRebreatherCircuit(cfg.circuit)) {
    const fN2 = Math.max(0, 1 - fO2 - fHe);
    return { pN2: (pAmb - ppH2O) * fN2, pHe: (pAmb - ppH2O) * fHe, fO2, fHe, fN2 };
  }
  if (cfg.circuit === 'pSCR') {
    const fr = computePSCRFractions(pAmb, fO2, fHe, cfg.scrRuntimeMin, cfg);
    return {
      pN2: (pAmb - ppH2O) * fr.fN2,
      pHe: (pAmb - ppH2O) * fr.fHe,
      fO2: fr.fO2, fHe: fr.fHe, fN2: fr.fN2,
    };
  }
  if (!setpoint || setpoint <= 0 || pAmb <= setpoint + ppH2O) {
    return { pN2: 0, pHe: 0, fO2, fHe, fN2: 0 };
  }
  const pInert = pAmb - setpoint - ppH2O;
  const den = Math.max(0.001, 1 - fO2);
  const fN2d = Math.max(0, 1 - fO2 - fHe);
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
    const fr0 = computePSCRFractions(pAmbStart, fO2, fHe, cfg.scrRuntimeMin, cfg);
    const pEnd = pAmbStart + pressureRate * 1;
    const fr1 = computePSCRFractions(pEnd, fO2, fHe, cfg.scrRuntimeMin, cfg);
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
  if (!setpoint || setpoint <= 0 || pAmbStart <= setpoint + WATER_VAPOR) {
    return { inspN2Start: 0, inspHeStart: 0, rN2: 0, rHe: 0 };
  }
  const den = Math.max(0.001, 1 - fO2);
  const fN2d = Math.max(0, 1 - fO2 - fHe);
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
  const sp = getEffectiveSetpointAtDepth((fromDepth + toDepth) / 2, cfg, surfP, phase);
  const segments = splitSegmentAtSetpoint(fromDepth, toDepth, sp, surfP);
  let out = tissues;
  const totalTime = t;
  for (const seg of segments) {
    const segTime = Math.abs(seg.toDepth - seg.fromDepth) / Math.abs(toDepth - fromDepth) * totalTime;
    if (segTime <= 0) continue;
    const p0Amb = depthBar(seg.fromDepth);
    const pEndAmb = depthBar(seg.toDepth);
    const R = (pEndAmb - p0Amb) / segTime;
    const segSP = getEffectiveSetpointAtDepth(seg.fromDepth, cfg, surfP, phase);
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
