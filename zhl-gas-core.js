/**
 * ZHL gas selection and min-deco profile helpers (Tier 3) — BUILD SOURCE ONLY.
 * Not loaded by index.html at runtime.
 * Rebuilt into zhl-engine-bundle.js via tools/build_zhl_bundle.py.
 *
 * Depends on zhl-physics-core.js module globals: altSurfaceP, BAR_PER_METRE, allowO2AtMOD
 * (build order: physics → gas → ccr → schedule).
 */
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
