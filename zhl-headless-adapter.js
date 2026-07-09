/**
 * ZHL headless adapter.
 * Browser-facing test/API wrapper around zhl-engine-bundle.js and zhl-worker-bridge.js.
 * Loaded after schedule-runner-core and before planner-shell.
 */

'use strict';

function validateGasFractionsPct(o2, he, field) {
  const o = Number(o2);
  const h = (he == null || he === '') ? 0 : Number(he);
  if (!Number.isFinite(o) || !Number.isFinite(h) || o <= 0 || o > 100 || h < 0 || h > 100 || o + h > 100) {
    return {
      ok: false,
      code: 'INVALID_GAS_FRACTIONS',
      field: field || 'gas',
      message: 'O2 must be greater than 0 and at most 100 percent; He must be between 0 and 100 percent; total no more than 100 percent.',
    };
  }
  return { ok: true, o2: o, he: h };
}

// AUDIT-UNIT:UI-ZHL-HEADLESS-HELPERS
function gasFractionsFromPct(o2, he) {
  const o = Number(o2);
  const h = (he == null || he === '') ? 0 : Number(he);
  return { o2Frac: o / 100, heFrac: h / 100, o2Pct: o, hePct: h };
}
if (typeof window !== 'undefined') window.validateGasFractionsPct = validateGasFractionsPct;

function validateEngineInputs(levels, decoGases) {
  const errors = [];
  if (!Array.isArray(levels) || levels.length === 0) {
    errors.push({ code: 'INVALID_PROFILE', field: 'levels', message: 'At least one dive level is required.' });
  } else {
    levels.forEach((level, index) => {
      if (level == null) {
        errors.push({ code: 'INVALID_PROFILE', field: `levels[${index}]`, message: 'Level entry is required.' });
        return;
      }
      if (!Number.isFinite(level.depth) || level.depth <= 0) {
        errors.push({ code: 'INVALID_DEPTH', field: `levels[${index}].depth`, message: 'Depth must be a positive number.' });
      }
      if (!Number.isFinite(level.time) || level.time <= 0) {
        errors.push({ code: 'INVALID_TIME', field: `levels[${index}].time`, message: 'Bottom time must be a positive number.' });
      }
      const gasCheck = validateGasFractionsPct(level.o2, level.he, `levels[${index}]`);
      if (!gasCheck.ok) errors.push(gasCheck);
    });
  }
  if (Array.isArray(decoGases)) {
    decoGases.forEach((g, index) => {
      if (g == null) {
        errors.push({ code: 'INVALID_GAS_FRACTIONS', field: `decoGases[${index}]`, message: 'Deco gas entry is required.' });
        return;
      }
      if (g.o2 == null && g.he == null) return;
      const gasCheck = validateGasFractionsPct(g.o2, g.he, `decoGases[${index}]`);
      if (!gasCheck.ok) errors.push(gasCheck);
    });
  }
  return { ok: errors.length === 0, errors };
}
if (typeof window !== 'undefined') window.validateEngineInputs = validateEngineInputs;

function engineValidationError(validation) {
  const first = validation.errors[0];
  return {
    error: first.message || 'Invalid input.',
    code: first.code,
    field: first.field,
    errors: validation.errors,
    stops: [],
    plan: [],
    totalRuntime: 0,
    totalTime: 0,
  };
}

function collectDecoGasesPctFromDom() {
  const out = [];
  for (const idx of getAllDecoGasIds()) {
    const gas = getDomDecoGasPct(idx);
    if (!gas) continue;
    out.push(gas);
  }
  return out;
}

function validatePSCRParameterBounds(settings) {
  const loopVol = parseFloat(settings.scrLoopVolume);
  const metO2 = parseFloat(settings.scrMetabolicO2);
  const errors = [];
  if (!Number.isFinite(loopVol) || loopVol < PSCR_LOOP_VOLUME_MIN || loopVol > PSCR_LOOP_VOLUME_MAX) {
    errors.push({
      code: 'INVALID_LOOP_VOLUME', field: 'scrLoopVolume',
      message: `pSCR loop volume must be between ${PSCR_LOOP_VOLUME_MIN} and ${PSCR_LOOP_VOLUME_MAX} litres.`,
    });
  }
  if (!Number.isFinite(metO2) || metO2 < PSCR_METABOLIC_O2_MIN || metO2 > PSCR_METABOLIC_O2_MAX) {
    errors.push({
      code: 'INVALID_METABOLIC_O2', field: 'scrMetabolicO2',
      message: `pSCR metabolic O2 must be between ${PSCR_METABOLIC_O2_MIN} and ${PSCR_METABOLIC_O2_MAX} L/min.`,
    });
  }
  return errors;
}

function validateCcrCalculationInputs(levels, settings, decoGases) {
  const errors = [];
  const s = settings || {};
  const circuit = canonicalCircuit(s.circuit || 'OC');
  if (!isRebreatherCircuit(circuit)) return { ok: true, errors: [] };

  if (!Array.isArray(levels) || levels.length === 0) {
    errors.push({ code: 'INVALID_PROFILE', message: 'At least one profile level is required.' });
  }

  for (let li = 0; li < (levels || []).length; li++) {
    const level = levels[li];
    const depth = Number(level.depth);
    const time = Number(level.time);
    if (!Number.isFinite(depth) || depth <= 0) {
      errors.push({ code: 'INVALID_PROFILE', field: 'depth', message: 'Depth must be a positive finite number.' });
    }
    if (!Number.isFinite(time) || time <= 0) {
      errors.push({ code: 'INVALID_PROFILE', field: 'time', message: 'Bottom time must be a positive finite number.' });
    }
    const gasCheck = validateGasFractionsPct(level.o2, level.he, `levels[${li}]`);
    if (!gasCheck.ok) {
      errors.push({ code: gasCheck.code, field: gasCheck.field, message: gasCheck.message });
    }
  }

  if (Array.isArray(decoGases)) {
    decoGases.forEach((g, index) => {
      if (g.o2 == null && g.he == null) return;
      const gasCheck = validateGasFractionsPct(g.o2, g.he, `decoGases[${index}]`);
      if (!gasCheck.ok) {
        errors.push({ code: gasCheck.code, field: gasCheck.field, message: gasCheck.message });
      }
    });
  }

  const descentSP = s.descentSetpoint != null ? s.descentSetpoint : 0.7;
  const bottomSP = s.bottomSetpoint != null ? s.bottomSetpoint : (s.setpoint != null ? s.setpoint : 1.2);
  const decoSP = s.decoSetpoint != null ? s.decoSetpoint : (s.setpoint != null ? s.setpoint : 1.3);

  if (circuit === 'pSCR') {
    errors.push(...validatePSCRParameterBounds(s));
    for (const [name, value, min, max] of [
      ['bottom', bottomSP, 0.7, 1.6],
      ['deco', decoSP, 0.7, 1.6],
    ]) {
      if (value === 0) continue;
      if (!Number.isFinite(value) || value < min || value > max) {
        errors.push({
          code: 'INVALID_SETPOINT',
          field: name + 'Setpoint',
          message: `${name} setpoint must be between ${min} and ${max} bar.`,
        });
      }
    }
    return { ok: errors.length === 0, errors };
  }

  for (const [name, value, min, max] of [
    ['descent', descentSP, 0.5, 1.0],
    ['bottom', bottomSP, 0.7, 1.6],
    ['deco', decoSP, 0.7, 1.6],
  ]) {
    if (!Number.isFinite(value) || value < min || value > max) {
      errors.push({
        code: 'INVALID_SETPOINT',
        field: name + 'Setpoint',
        message: `${name} setpoint must be between ${min} and ${max} bar.`,
      });
    }
  }

  return { ok: errors.length === 0, errors };
}
if (typeof window !== 'undefined') window.validateCcrCalculationInputs = validateCcrCalculationInputs;

function splitZhlProfileLevels(levels) {
  return ZhlEngineBundle.splitZhlProfileLevels(levels);
}

function validateZhlHeadlessProfile(levels) {
  if (!levels || levels.length <= 1) return { ok: true };
  let deepestIdx = 0;
  for (let i = 1; i < levels.length; i++) {
    if (levels[i].depth > levels[deepestIdx].depth) deepestIdx = i;
  }
  if (deepestIdx !== 0) {
    return {
      ok: false,
      code: 'INVALID_PROFILE',
      field: 'levels',
      message: 'ZHL profiles must start at the deepest level; add deeper segments before shallower ones.',
    };
  }
  for (let i = 1; i < levels.length; i++) {
    if (levels[i].depth > levels[i - 1].depth) {
      return {
        ok: false,
        code: 'INVALID_PROFILE',
        field: `levels[${i}].depth`,
        message: 'ZHL profiles cannot re-descend after a shallower level.',
      };
    }
  }
  return { ok: true };
}
if (typeof window !== 'undefined') window.validateZhlHeadlessProfile = validateZhlHeadlessProfile;

// AUDIT-UNIT:UI-ZHL-HEADLESS-ENGINE
const ZHLEngine = (() => {
  function mergeRepSettings(settings) {
    const s = settings || {};
    if (s._preTissues && s._preTissues.length) {
      const repSnap = peekZhlRepState();
      if (repSnap && s.totalCNSCarry == null && repSnap.totalCNS != null) {
        return {
          ...s,
          totalCNSCarry: repSnap.totalCNS,
          totalOTUCarry: repSnap.totalOTU,
        };
      }
      return s;
    }
    const repSnap = peekZhlRepState();
    if (repSnap) {
      return {
        ...s,
        _preTissues: repSnap.tissues,
        _surfaceInterval: repSnap.surfaceIntervalMin || 0,
        totalCNSCarry: repSnap.totalCNS,
        totalOTUCarry: repSnap.totalOTU,
      };
    }
    return s;
  }

  function applyPlanExposureTotals(result, levels, settings) {
    if (!result || result.error || !levels || !levels.length) return result;
    const level = levels[0];
    const s = settings || {};
    const fO2bot = level.o2 / 100;
    const fHeBot = (level.he || 0) / 100;
    const exposure = computePlanExposureTotals(
      result.plan, s, fO2bot, fHeBot, altSurfaceP || 1.01325, BAR_PER_METRE || 0.1
    );
    const _pdCarry = window._priorDiveCarry;
    const otuCarry = _pdCarry ? (_pdCarry.otuCarry || 0) : (s.totalOTUCarry != null ? s.totalOTUCarry : 0);
    const cnsCarry = _pdCarry ? (_pdCarry.cnsCarry || 0) : (s.totalCNSCarry != null ? s.totalCNSCarry : 0);
    return Object.assign({}, result, {
      totalOTU: Math.round(exposure.totalOTU + otuCarry),
      totalCNS: parseFloat((exposure.totalCNS + cnsCarry).toFixed(1)),
    });
  }

  function calculate(levels, decoGases, settings) {
    _syncZhlBundleEnv();
    const s = mergeRepSettings(settings);
    const ccrVal = validateCcrCalculationInputs(levels, s, decoGases);
    if (!ccrVal.ok) return engineValidationError(ccrVal);
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {
      return engineValidationError({ ok: false, errors: [profileVal] });
    }
    const profileSplit = ZhlEngineBundle.splitZhlProfileLevels(levels);
    return applyPlanExposureTotals(
      ZhlEngineBundle.calculate(levels, decoGases, s, profileSplit, getZhlEnvironment(s)),
      levels,
      s
    );
  }

  async function calculateInWorker(levels, decoGases, settings) {
    _syncZhlBundleEnv();
    const s = mergeRepSettings(settings);
    const ccrVal = validateCcrCalculationInputs(levels, s, decoGases);
    if (!ccrVal.ok) return engineValidationError(ccrVal);
    const validation = validateEngineInputs(levels, decoGases);
    if (!validation.ok) return engineValidationError(validation);
    const profileVal = validateZhlHeadlessProfile(levels);
    if (!profileVal.ok) {
      return engineValidationError({ ok: false, errors: [profileVal] });
    }
    const profileSplit = ZhlEngineBundle.splitZhlProfileLevels(levels);
    try {
      const result = await ZhlWorkerBridge.calculateInWorker(
        levels, decoGases, s, profileSplit, getZhlEnvironment(s)
      );
      return applyPlanExposureTotals(result, levels, s);
    } catch (e) {
      return { error: e.message, stops: [], plan: [], totalRuntime: 0 };
    }
  }

  return { calculate, calculateInWorker, MODEL: 'ZHLC_GF' };
})();

if (typeof window !== 'undefined') window.ZHLEngine = ZHLEngine;
