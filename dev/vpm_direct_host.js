'use strict';

const path = require('path');

const ROOT = path.resolve(__dirname, '..');

function installVpmHostGlobals() {
  global.BAR_PER_METRE = 0.1;
  global.WATER_VAPOR = 0.0627;
  global.altSurfaceP = 1.01325;

  global.isRebreatherCircuit = (circuit) => {
    const value = String(circuit || 'OC').toUpperCase();
    return value === 'CCR' || value === 'PSCR';
  };

  global.validateEngineInputs = (levels, decoGases) => {
    const errors = [];
    if (!Array.isArray(levels) || levels.length === 0) {
      errors.push({ code: 'INVALID_PROFILE', message: 'levels must be a non-empty array' });
    }
    for (const [idx, level] of (Array.isArray(levels) ? levels : []).entries()) {
      if (!level || !Number.isFinite(Number(level.depth)) || Number(level.depth) < 0) {
        errors.push({ code: 'INVALID_PROFILE', message: `level ${idx} depth is invalid` });
      }
      if (!level || !Number.isFinite(Number(level.time)) || Number(level.time) < 0) {
        errors.push({ code: 'INVALID_PROFILE', message: `level ${idx} time is invalid` });
      }
      const o2 = Number(level && level.o2);
      const he = Number(level && (level.he || 0));
      if (!Number.isFinite(o2) || !Number.isFinite(he) || o2 <= 0 || he < 0 || o2 + he > 100) {
        errors.push({ code: 'INVALID_GAS_FRACTIONS', message: `level ${idx} gas is invalid` });
      }
    }
    for (const [idx, gas] of (Array.isArray(decoGases) ? decoGases : []).entries()) {
      if (!gas) {
        errors.push({ code: 'INVALID_GAS_FRACTIONS', message: `deco gas ${idx} is missing` });
        continue;
      }
      const o2 = Number(gas.o2);
      const he = Number(gas.he || 0);
      if (!Number.isFinite(o2) || !Number.isFinite(he) || o2 <= 0 || he < 0 || o2 + he > 100) {
        errors.push({ code: 'INVALID_GAS_FRACTIONS', message: `deco gas ${idx} is invalid` });
      }
    }
    return { ok: errors.length === 0, errors };
  };

  global.validateCcrCalculationInputs = () => ({ ok: true, errors: [] });

  global.gasFractionsFromPct = (o2Pct, hePct = 0) => {
    const o2 = Number(o2Pct);
    const he = Number(hePct || 0);
    const safeO2 = Number.isFinite(o2) ? o2 : 21;
    const safeHe = Number.isFinite(he) ? he : 0;
    const n2 = Math.max(0, 100 - safeO2 - safeHe);
    return {
      o2Pct: safeO2,
      hePct: safeHe,
      n2Pct: n2,
      o2Frac: safeO2 / 100,
      heFrac: safeHe / 100,
      n2Frac: n2 / 100,
    };
  };

  global.getInspiredInertPressures = (pAmb, setpoint, fO2, fHe) => {
    const ppH2O = global.WATER_VAPOR;
    const inertPressure = Math.max(0, Number(pAmb) - ppH2O - (Number(setpoint) || 0));
    const o2 = Number(fO2) || 0;
    const he = Number(fHe) || 0;
    const n2 = Math.max(0, 1 - o2 - he);
    const totalInertFrac = n2 + he;
    if (totalInertFrac <= 0) return { n2: 0, he: 0, pN2: 0, pHe: 0 };
    const pN2 = inertPressure * (n2 / totalInertFrac);
    const pHe = inertPressure * (he / totalInertFrac);
    return { n2: pN2, he: pHe, pN2, pHe };
  };

  global.engineValidationError = (validation) => ({
    error: (validation.errors || []).map((err) => err.message || err.code).join('; ') || 'Invalid engine input',
    code: (validation.errors || [])[0]?.code || 'INVALID_INPUT',
    errors: validation.errors || [],
    stops: [],
    plan: [],
    totalTime: 0,
    totalRuntime: 0,
  });
}

installVpmHostGlobals();

const VPMEngine = require(path.join(ROOT, 'vpm-engine-bundle.js'));

const DEFAULT_SETTINGS = Object.freeze({
  metric: true,
  gfLo: 30,
  gfHi: 85,
  stepSize: 3,
  lastStop: 3,
  minStopTime: 1,
  descentRate: 20,
  ascentRate: 10,
  decoAscentRate: 3,
  surfaceAscentRate: 3,
  ppO2Bottom: 1.4,
  ppO2Deco: 1.6,
  conservatism: 0,
  waterType: 0,
  altitude: 0,
  altSurfaceP: 1.01325,
});

function calculateVpm(levels, gases = [], settings = {}, model = 'VPMB') {
  return VPMEngine.calculate(
    levels,
    gases,
    { ...DEFAULT_SETTINGS, ...settings },
    model,
  );
}

function uniqueGasLabels(result) {
  return [...new Set((result.plan || []).map((row) => row.gas).filter(Boolean))];
}

function assertCanonicalGasLabels(labels) {
  const invalid = labels.filter((label) => (
    /^EAN/i.test(label)
    || ['21/0', '50/0', '80/0', '100/0'].includes(label)
    || /\b\d{1,2}\/0\b/.test(label)
  ));
  return {
    ok: invalid.length === 0,
    invalid,
  };
}

function summarizeVpm(result) {
  const stops = (result.stops || []).map((stop) => ({
    depth: Number(stop.depth),
    time: Number(stop.time ?? stop.dur ?? 0),
  }));
  return {
    totalRuntime: Number(result.totalRuntime || result.totalTime || 0),
    tts: Number(result.tts || 0),
    firstStop: stops.length ? Math.max(...stops.map((stop) => stop.depth)) : 0,
    stopCount: stops.length,
    gasLabels: uniqueGasLabels(result),
    stops,
  };
}

module.exports = {
  VPMEngine,
  DEFAULT_SETTINGS,
  calculateVpm,
  assertCanonicalGasLabels,
  summarizeVpm,
  uniqueGasLabels,
};
