/**
 * CCR Bühlmann tissue loading (Tier 3) — pure functions, no DOM.
 * Included in zhl-engine-bundle.js via tools/build_zhl_bundle.py.
 */
function canonicalCircuit(circuit) {
  if (circuit == null || circuit === '') return 'OC';
  const u = String(circuit).trim().toUpperCase();
  if (u === 'CCR') return 'CCR';
  if (u === 'PSCR') return 'pSCR';
  return 'OC';
}

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

/** pSCR loop fractions; metO2/loopVol yields bar/bar ppO2 drop (L/min ÷ L). */
function computePSCRFractions(pAmb, fO2, fHe, ccr) {
  fO2 = Math.max(0, Math.min(1, fO2 || 0));
  fHe = Math.max(0, Math.min(1 - fO2, fHe || 0));
  const fN2src = Math.max(0, 1 - fO2 - fHe);
  const sourceInert = Math.max(0.001, fHe + fN2src);
  if (sourceInert <= 0.001 && fO2 >= 0.999) return { fO2: 1, fHe: 0, fN2: 0 };
  const loopVol = parseFloat(ccr.scrLoopVolume);
  if (!Number.isFinite(loopVol) || loopVol <= 0) {
    throw new Error('Invalid pSCR loop volume');
  }
  const metO2 = getCcrMetabolicO2Rate(ccr);
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
