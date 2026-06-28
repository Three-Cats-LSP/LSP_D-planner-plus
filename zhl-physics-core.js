/**
 * Bühlmann ZHL-16C tissue physics (Tier 3) — BUILD SOURCE ONLY.
 * Not loaded by index.html at runtime.
 * Rebuilt into zhl-engine-bundle.js via tools/build_zhl_bundle.py.
 */
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
  if (!firstStopDepth || firstStopDepth <= 0) return gfL;
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
