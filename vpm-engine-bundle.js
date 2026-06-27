/**
 * VPM Engine Bundle — Tier 3 isolated VPM-B / VPM-B+GFS module.
 * Loaded on main thread; exposes window.VPMEngine for tests and runVPMSchedule().
 *
 * Host runtime deps (resolved at calculate() time, not load time):
 *   validateEngineInputs, validateCcrCalculationInputs, engineValidationError,
 *   isRebreatherCircuit, mergeCCRSettings, getEffectivePpo2, computePlanExposureTotals
 *   globals: altSurfaceP, BAR_PER_METRE (exposure fallbacks)
 */
const VPMEngine = (() => {
    const ZHL16C_N2 = [
        { ht: 5.0,    a: 1.2599, b: 0.5050 },
        { ht: 8.0,    a: 1.0000, b: 0.6514 },
        { ht: 12.5,   a: 0.8618, b: 0.7222 },
        { ht: 18.5,   a: 0.7562, b: 0.7825 },
        { ht: 27.0,   a: 0.6200, b: 0.8126 },
        { ht: 38.3,   a: 0.5043, b: 0.8434 },
        { ht: 54.3,   a: 0.4410, b: 0.8693 },
        { ht: 77.0,   a: 0.4000, b: 0.8910 },
        { ht: 109.0,  a: 0.3750, b: 0.9092 },
        { ht: 146.0,  a: 0.3500, b: 0.9222 },
        { ht: 187.0,  a: 0.3295, b: 0.9319 },
        { ht: 239.0,  a: 0.3065, b: 0.9403 },
        { ht: 305.0,  a: 0.2835, b: 0.9477 },
        { ht: 390.0,  a: 0.2610, b: 0.9544 },
        { ht: 498.0,  a: 0.2480, b: 0.9602 },
        { ht: 635.0,  a: 0.2327, b: 0.9653 }
    ];
    const ZHL16C_He = [
        { ht: 1.88,   a: 1.7424, b: 0.4245 },
        { ht: 3.02,   a: 1.3830, b: 0.5747 },
        { ht: 4.72,   a: 1.1919, b: 0.6527 },
        { ht: 6.99,   a: 1.0458, b: 0.7223 },
        { ht: 10.21,  a: 0.9220, b: 0.7582 },
        { ht: 14.48,  a: 0.8205, b: 0.7957 },
        { ht: 20.53,  a: 0.7305, b: 0.8279 },
        { ht: 29.11,  a: 0.6502, b: 0.8553 },
        { ht: 41.20,  a: 0.5950, b: 0.8757 },
        { ht: 55.19,  a: 0.5545, b: 0.8903 },
        { ht: 70.69,  a: 0.5333, b: 0.8997 },
        { ht: 90.34,  a: 0.5189, b: 0.9073 },
        { ht: 115.29, a: 0.5181, b: 0.9122 },
        { ht: 147.42, a: 0.5176, b: 0.9171 },
        { ht: 188.24, a: 0.5172, b: 0.9217 },
        { ht: 240.03, a: 0.5119, b: 0.9267 }
    ];
    const NC = 16; 
    const GAMMA = 0.0179;            
    const GAMMA_C = 0.257;           
    const INITIAL_RADIUS_N2 = 0.55e-6; 
    const INITIAL_RADIUS_He = 0.45e-6; 
    const REGEN_TIME = 20160.0;      
    function getWaterVaporPressure(settings) {
        return (settings && settings.waterVapor != null) ? settings.waterVapor : 0.0627;
    }
    const CONSTANT_PRESSURE_OTHER_GASES = (102.0 / 760.0) * 1.01325; 
    const CRIT_VOLUME_LAMBDA_FSW_MIN = 7500.0;
    function twoGammaOverR(gamma, r) {
        return (2.0 * gamma / r) / 1.0e5; 
    }
    const SLP_SW_M = 10.000;  // salt, metric — MultiDeco/DiveKit/ApexDeco standard
    const SLP_FW_M = 10.330;  // fresh, metric — matches ZHL WATER_DENSITY.fresh (0.09681 bar/m)
    const SLP_EN_M = 10.080;  // EN13319, metric — matches DiveKit EN13319
    const SLP_SW_F = 32.808;  // salt, imperial — 10.000 × 3.28084
    const SLP_FW_F = 33.891;  // fresh, imperial — 10.330 × 3.28084
    const SLP_EN_F = 33.071;  // EN13319, imperial — 10.080 × 3.28084
    function getSLP(settings) {
        if (settings.waterType === 3) {
            const barPerM = settings.barPerM
                || (settings.customWaterDensity
                    ? (settings.customWaterDensity * 9.80665) / 100000 : 0);
            if (barPerM > 0) {
                const slpM = 1 / barPerM;
                return settings.metric ? slpM : slpM * 3.28084;
            }
        }
        if (settings.metric) {
            if (settings.waterType === 2) return SLP_EN_M;
            return settings.waterType === 0 ? SLP_SW_M : SLP_FW_M;
        }
        if (settings.waterType === 2) return SLP_EN_F;
        return settings.waterType === 0 ? SLP_SW_F : SLP_FW_F;
    }
    function getSurfacePressure(settings) {
        const alt = settings.altitude || 0;
        return 1.01325 * Math.exp(-alt / 8434);
    }
    function getAmbientPressure(depth, settings) {
        return getSurfacePressure(settings) + depth / getSLP(settings);
    }
    function createVPMState(settings) {
        const surfP = getSurfacePressure(settings);
        const ppH2O = getWaterVaporPressure(settings);
        const inspiredN2 = 0.7902 * (surfP - ppH2O);
        const tissues = [];
        const critRadiiN2 = [];
        const critRadiiHe = [];
        const maxActualGradientN2 = [];
        const maxActualGradientHe = [];
        const maxCrushingPressureN2 = [];
        const maxCrushingPressureHe = [];
        const allowableGradientN2 = [];
        const allowableGradientHe = [];
        const decoGradientN2 = [];
        const decoGradientHe = [];
        const initialAllowableGradientN2 = [];
        const initialAllowableGradientHe = [];
        const adjustedCritRadiiN2 = [];
        const adjustedCritRadiiHe = [];
        const regeneratedRadiiN2 = [];
        const regeneratedRadiiHe = [];
        const adjustedCrushingPressureN2 = [];
        const adjustedCrushingPressureHe = [];
        const surfacePhaseVolumeTime = [];
        const lastPhaseVolumeTime = [];
        // ── Feature A: Altitude-adjusted critical radii ────────────────────────────────
        // At altitude, surface pressure is lower, so bubbles equilibrate to a larger
        // radius (less crushing pressure). Formula: r_alt = r_0 * (P_SL / P_alt)^(1/3)
        // Volume scales linearly with pressure (ideal gas); radius is the cube root.
        // At sea level surfP == 1.01325 so the factor is exactly 1.0 — no change.
        const P_SL = 1.01325; // bar — standard sea-level pressure
        const altFactor = Math.pow(P_SL / surfP, 1.0 / 3.0);
        const initRadN2 = INITIAL_RADIUS_N2 * altFactor; // enlarged at altitude
        const initRadHe = INITIAL_RADIUS_He * altFactor;
        // ─────────────────────────────────────────────────────────────────────────────
        for (let i = 0; i < NC; i++) {
            tissues.push({ pN2: inspiredN2, pHe: 0 });
            critRadiiN2.push(initRadN2);
            critRadiiHe.push(initRadHe);
            maxActualGradientN2.push(0);
            maxActualGradientHe.push(0);
            maxCrushingPressureN2.push(0);
            maxCrushingPressureHe.push(0);
            const gN2 = twoGammaOverR(GAMMA, initRadN2)
                * (GAMMA_C - GAMMA) / GAMMA_C;
            const gHe = twoGammaOverR(GAMMA, initRadHe)
                * (GAMMA_C - GAMMA) / GAMMA_C;
            allowableGradientN2.push(gN2);
            allowableGradientHe.push(gHe);
            decoGradientN2.push(gN2);
            decoGradientHe.push(gHe);
            initialAllowableGradientN2.push(gN2);
            initialAllowableGradientHe.push(gHe);
            adjustedCritRadiiN2.push(initRadN2);
            adjustedCritRadiiHe.push(initRadHe);
            regeneratedRadiiN2.push(initRadN2);
            regeneratedRadiiHe.push(initRadHe);
            adjustedCrushingPressureN2.push(0);
            adjustedCrushingPressureHe.push(0);
            surfacePhaseVolumeTime.push(0);
            lastPhaseVolumeTime.push(0);
        }
        if (settings._preTissues && settings._preTissues.length === NC) {
            for (let i = 0; i < NC; i++) {
                tissues[i].pN2 = settings._preTissues[i].pN2;
                tissues[i].pHe = settings._preTissues[i].pHe;
            }
            if (settings._surfaceInterval > 0) {
                const inspN2 = 0.7902 * (surfP - ppH2O);
                for (let i = 0; i < NC; i++) {
                    const kN2 = Math.LN2 / ZHL16C_N2[i].ht;
                    const kHe = Math.LN2 / ZHL16C_He[i].ht;
                    tissues[i].pN2 = inspN2 + (tissues[i].pN2 - inspN2) * Math.exp(-kN2 * settings._surfaceInterval);
                    tissues[i].pHe = tissues[i].pHe * Math.exp(-kHe * settings._surfaceInterval);
                }
            }
        }
        // ── Feature B: Repetitive dive bubble state carry ────────────────────────────
        // When _prevBubbleState is provided (from a previous VPM dive), carry the
        // end-of-dive adjusted critical radii and regenerated radii into this dive,
        // applying surface-interval partial regeneration (exponential, same REGEN_TIME).
        // This is the correct VPM treatment: nuclei that were crushed and compressed
        // during the previous dive don't fully return to their original size overnight —
        // they partially regenerate, and subsequent dives start with those smaller radii
        // (conservative: smaller radius → larger allowable gradient → less deco time
        //  is WRONG; actually smaller nucleus = harder to grow = LESS bubble risk;
        //  but larger nuclei survive surface interval better → more conservative for next dive).
        // Net effect: carrying state is conservative — correct VPM-B behaviour.
        if (settings._prevBubbleState && settings._prevBubbleState.adjustedCritRadiiN2
                && settings._prevBubbleState.adjustedCritRadiiN2.length === NC) {
            const si = settings._surfaceInterval != null ? settings._surfaceInterval : 0;
            const regenFactor = Math.exp(-si / REGEN_TIME);
            const pb = settings._prevBubbleState;
            for (let i = 0; i < NC; i++) {
                // End-of-previous-dive radius (after nuclear regeneration was applied)
                const prevN2 = pb.regeneratedRadiiN2[i];
                const prevHe = pb.regeneratedRadiiHe[i];
                // During surface interval, radii regenerate toward the altitude-adjusted
                // initial values (baseline for this altitude). Partial regeneration:
                //   r(t) = r_init + (r_prev - r_init) * exp(-t / REGEN_TIME)
                const carriedN2 = initRadN2 + (prevN2 - initRadN2) * regenFactor;
                const carriedHe = initRadHe + (prevHe - initRadHe) * regenFactor;
                critRadiiN2[i]         = carriedN2;
                critRadiiHe[i]         = carriedHe;
                adjustedCritRadiiN2[i] = carriedN2;
                adjustedCritRadiiHe[i] = carriedHe;
                regeneratedRadiiN2[i]  = carriedN2;
                regeneratedRadiiHe[i]  = carriedHe;
                // Recalculate allowable gradients from carried radii
                const gN2c = twoGammaOverR(GAMMA, carriedN2) * (GAMMA_C - GAMMA) / GAMMA_C;
                const gHec = twoGammaOverR(GAMMA, carriedHe) * (GAMMA_C - GAMMA) / GAMMA_C;
                allowableGradientN2[i]        = gN2c;
                allowableGradientHe[i]        = gHec;
                decoGradientN2[i]             = gN2c;
                decoGradientHe[i]             = gHec;
                initialAllowableGradientN2[i] = gN2c;
                initialAllowableGradientHe[i] = gHec;
            }
        }
        // ─────────────────────────────────────────────────────────────────────────────
        return {
            tissues,
            critRadiiN2,
            critRadiiHe,
            maxActualGradientN2,
            maxActualGradientHe,
            maxCrushingPressureN2,
            maxCrushingPressureHe,
            allowableGradientN2,
            allowableGradientHe,
            decoGradientN2,
            decoGradientHe,
            initialAllowableGradientN2,
            initialAllowableGradientHe,
            adjustedCritRadiiN2,
            adjustedCritRadiiHe,
            regeneratedRadiiN2,
            regeneratedRadiiHe,
            adjustedCrushingPressureN2,
            adjustedCrushingPressureHe,
            surfacePhaseVolumeTime,
            lastPhaseVolumeTime,
            maxDepth: 0,
            maxAmbientPressure: surfP,
            firstStopDepth: 0,
            useDecoGradients: false
        };
    }
    function cloneVPMState(baseState) {
        return {
            ...baseState,
            tissues: cloneTissues(baseState.tissues),
            critRadiiN2: baseState.critRadiiN2.slice(),
            critRadiiHe: baseState.critRadiiHe.slice(),
            maxActualGradientN2: baseState.maxActualGradientN2.slice(),
            maxActualGradientHe: baseState.maxActualGradientHe.slice(),
            maxCrushingPressureN2: baseState.maxCrushingPressureN2.slice(),
            maxCrushingPressureHe: baseState.maxCrushingPressureHe.slice(),
            allowableGradientN2: baseState.allowableGradientN2.slice(),
            allowableGradientHe: baseState.allowableGradientHe.slice(),
            decoGradientN2: baseState.decoGradientN2.slice(),
            decoGradientHe: baseState.decoGradientHe.slice(),
            initialAllowableGradientN2: baseState.initialAllowableGradientN2.slice(),
            initialAllowableGradientHe: baseState.initialAllowableGradientHe.slice(),
            adjustedCritRadiiN2: baseState.adjustedCritRadiiN2.slice(),
            adjustedCritRadiiHe: baseState.adjustedCritRadiiHe.slice(),
            regeneratedRadiiN2: baseState.regeneratedRadiiN2.slice(),
            regeneratedRadiiHe: baseState.regeneratedRadiiHe.slice(),
            adjustedCrushingPressureN2: baseState.adjustedCrushingPressureN2.slice(),
            adjustedCrushingPressureHe: baseState.adjustedCrushingPressureHe.slice(),
            surfacePhaseVolumeTime: baseState.surfacePhaseVolumeTime.slice(),
            lastPhaseVolumeTime: baseState.lastPhaseVolumeTime.slice()
        };
    }
    function haldane(pStart, pInspired, ht, time) {
        const k = Math.LN2 / ht;
        return pStart + (pInspired - pStart) * (1 - Math.exp(-k * time));
    }
    function schreiner(pInspiredStart, rate, time, ht, pStart) {
        const k = Math.LN2 / ht;
        return pInspiredStart + rate * (time - 1 / k)
            - (pInspiredStart - pStart - rate / k) * Math.exp(-k * time);
    }
    function cloneTissues(tissues) {
        return tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe }));
    }
    function restoreTissues(state, tissues) {
        for (let i = 0; i < NC; i++) {
            state.tissues[i].pN2 = tissues[i].pN2;
            state.tissues[i].pHe = tissues[i].pHe;
        }
    }
    function loadTissuesConstant(state, depth, time, o2Frac, heFrac, settings, setpoint) {
        const pAmb = getAmbientPressure(depth, settings);
        const ccr = {
            circuit: settings.circuit || 'OC',
            setpoint,
            descentSetpoint: settings.descentSetpoint,
            bailout: settings.bailout,
            scrLoopVolume: settings.scrLoopVolume,
            scrMetabolicO2: settings.scrMetabolicO2,
            scrRuntimeMin: settings._scrRuntimeMin || 0,
        };
        const insp = getInspiredInertPressures(pAmb, setpoint, o2Frac, heFrac, ccr);
        if (pAmb > state.maxAmbientPressure) {
            state.maxAmbientPressure = pAmb;
            state.maxDepth = depth;
        }
        for (let i = 0; i < NC; i++) {
            state.tissues[i].pN2 = haldane(state.tissues[i].pN2, insp.pN2, ZHL16C_N2[i].ht, time);
            state.tissues[i].pHe = haldane(state.tissues[i].pHe, insp.pHe, ZHL16C_He[i].ht, time);
        }
    }
    function loadTissuesLinear(state, startDepth, endDepth, rate, o2Frac, heFrac, settings, setpoint) {
        const time = Math.abs(endDepth - startDepth) / rate;
        if (time <= 0) return 0;
        const slp = getSLP(settings);
        const surfP = getSurfacePressure(settings);
        const maxP = Math.max(getAmbientPressure(startDepth, settings), getAmbientPressure(endDepth, settings));
        if (maxP > state.maxAmbientPressure) {
            state.maxAmbientPressure = maxP;
            state.maxDepth = Math.max(startDepth, endDepth);
        }
        const ccr = {
            circuit: settings.circuit || 'OC',
            setpoint,
            descentSetpoint: settings.descentSetpoint,
            bailout: settings.bailout,
            scrLoopVolume: settings.scrLoopVolume,
            scrMetabolicO2: settings.scrMetabolicO2,
            scrRuntimeMin: settings._scrRuntimeMin || 0,
        };
        const segments = splitSegmentAtSetpoint(startDepth, endDepth, setpoint, surfP);
        let elapsed = 0;
        for (const seg of segments) {
            const segTime = Math.abs(seg.toDepth - seg.fromDepth) / rate;
            if (!(segTime > 0)) continue;
            const pAmbStart = surfP + seg.fromDepth / slp;
            const pAmbEnd = surfP + seg.toDepth / slp;
            const pressureRate = (pAmbEnd - pAmbStart) / segTime;
            const midDepth = (seg.fromDepth + seg.toDepth) / 2;
            const segSP = getEffectiveSetpointAtDepth(midDepth, ccr, surfP);
            const params = getCCRInertSchreinerParams(pAmbStart, segSP, o2Frac, heFrac, pressureRate, { ...ccr, setpoint: segSP });
            for (let i = 0; i < NC; i++) {
                const kN2 = Math.LN2 / ZHL16C_N2[i].ht;
                const kHe = Math.LN2 / ZHL16C_He[i].ht;
                state.tissues[i].pN2 = params.inspN2Start + params.rN2 * (segTime - 1/kN2)
                    - (params.inspN2Start - state.tissues[i].pN2 - params.rN2/kN2) * Math.exp(-kN2 * segTime);
                state.tissues[i].pHe = params.inspHeStart + params.rHe * (segTime - 1/kHe)
                    - (params.inspHeStart - state.tissues[i].pHe - params.rHe/kHe) * Math.exp(-kHe * segTime);
            }
            elapsed += segTime;
        }
        return elapsed || time;
    }
    function getWeightedAllowableGradient(state, i, pHe, pN2, useDecoGradients) {
        const gradHe = useDecoGradients ? state.decoGradientHe[i] : state.allowableGradientHe[i];
        const gradN2 = useDecoGradients ? state.decoGradientN2[i] : state.allowableGradientN2[i];
        const gasLoading = pHe + pN2;
        if (gasLoading > 0) {
            return (gradHe * pHe + gradN2 * pN2) / gasLoading;
        }
        return Math.min(gradHe, gradN2);
    }
    function calcCrushing(state, settings) {
        const surfP = getSurfacePressure(settings);
        const pMaxAmb = state.maxAmbientPressure;
        const pCrush = Math.max(0, pMaxAmb - surfP);
        for (let i = 0; i < NC; i++) {
            state.maxCrushingPressureN2[i] = Math.max(state.maxCrushingPressureN2[i], pCrush);
            state.maxCrushingPressureHe[i] = Math.max(state.maxCrushingPressureHe[i], pCrush);
        }
    }
    function calcCrushRadius(r0, pCrush) {
        const twoGammaC = (2.0 * GAMMA_C / r0) / 1.0e5; 
        if (twoGammaC + pCrush <= 0) return r0;
        return r0 * twoGammaC / (twoGammaC + pCrush);
    }
    function applyNuclearRegeneration(state, diveTime) {
        const regenFactor = Math.exp(-diveTime / REGEN_TIME);
        for (let i = 0; i < NC; i++) {
            const crushN2 = state.maxCrushingPressureN2[i];
            const crushHe = state.maxCrushingPressureHe[i];
            const baseN2 = state.adjustedCritRadiiN2[i];
            const baseHe = state.adjustedCritRadiiHe[i];
            const endingRadiusN2 = calcCrushRadius(baseN2, crushN2);
            const endingRadiusHe = calcCrushRadius(baseHe, crushHe);
            const regeneratedN2 = baseN2 + (endingRadiusN2 - baseN2) * regenFactor;
            const regeneratedHe = baseHe + (endingRadiusHe - baseHe) * regenFactor;
            state.regeneratedRadiiN2[i] = regeneratedN2;
            state.regeneratedRadiiHe[i] = regeneratedHe;
            const ratioN2Den = regeneratedN2 * (baseN2 - endingRadiusN2);
            const ratioHeDen = regeneratedHe * (baseHe - endingRadiusHe);
            const ratioN2 = Math.abs(ratioN2Den) > 1e-18
                ? (endingRadiusN2 * (baseN2 - regeneratedN2)) / ratioN2Den
                : 1;
            const ratioHe = Math.abs(ratioHeDen) > 1e-18
                ? (endingRadiusHe * (baseHe - regeneratedHe)) / ratioHeDen
                : 1;
            state.adjustedCrushingPressureN2[i] = crushN2 * ratioN2;
            state.adjustedCrushingPressureHe[i] = crushHe * ratioHe;
        }
    }
    function calcSurfacePhaseVolumeTime(state, settings) {
        const surfP = getSurfacePressure(settings);
        const surfaceInspiredN2 = 0.7902 * (surfP - getWaterVaporPressure(settings));
        for (let i = 0; i < NC; i++) {
            const pHe = state.tissues[i].pHe;
            const pN2 = state.tissues[i].pN2;
            if (pN2 > surfaceInspiredN2) {
                state.surfacePhaseVolumeTime[i] = (
                    pHe / (Math.LN2 / ZHL16C_He[i].ht)
                    + (pN2 - surfaceInspiredN2) / (Math.LN2 / ZHL16C_N2[i].ht)
                ) / (pHe + pN2 - surfaceInspiredN2);
            } else if (pN2 <= surfaceInspiredN2 && pHe + pN2 >= surfaceInspiredN2 && pHe > 0) {
                const kHe = Math.LN2 / ZHL16C_He[i].ht;
                const kN2 = Math.LN2 / ZHL16C_N2[i].ht;
                const logArg = (surfaceInspiredN2 - pN2) / pHe;
                if (logArg <= 0 || Math.abs(kN2 - kHe) < 1e-12) { state.surfacePhaseVolumeTime[i] = 0; continue; }
                const decayTime = Math.log(logArg) / (kN2 - kHe);
                if (decayTime < 0) { state.surfacePhaseVolumeTime[i] = 0; continue; }
                const integral = pHe / kHe * (1 - Math.exp(-kHe * decayTime))
                    + (pN2 - surfaceInspiredN2) / kN2 * (1 - Math.exp(-kN2 * decayTime));
                state.surfacePhaseVolumeTime[i] = integral / (pHe + pN2 - surfaceInspiredN2);
            } else {
                state.surfacePhaseVolumeTime[i] = 0;
            }
        }
    }
    function calcCriticalVolume(state, decoPhaseVolumeTime) {
        const lambdaPaMin = (CRIT_VOLUME_LAMBDA_FSW_MIN / 32.0) * 101325.0;
        for (let i = 0; i < NC; i++) {
            const phaseVolumeTime = decoPhaseVolumeTime + state.surfacePhaseVolumeTime[i];
            if (phaseVolumeTime <= 0) continue;
            const adjCrushHePa = state.adjustedCrushingPressureHe[i] * 1.0e5;
            const initAllowHePa = state.initialAllowableGradientHe[i] * 1.0e5;
            const bHe = initAllowHePa + (lambdaPaMin * GAMMA) / (GAMMA_C * phaseVolumeTime);
            const cHe = (GAMMA * GAMMA * lambdaPaMin * adjCrushHePa) / (GAMMA_C * GAMMA_C * phaseVolumeTime);
            const discHe = Math.max(0, bHe * bHe - 4.0 * cHe);
            state.allowableGradientHe[i] = (bHe + Math.sqrt(discHe)) / 2.0 / 1.0e5;
            const adjCrushN2Pa = state.adjustedCrushingPressureN2[i] * 1.0e5;
            const initAllowN2Pa = state.initialAllowableGradientN2[i] * 1.0e5;
            const bN2 = initAllowN2Pa + (lambdaPaMin * GAMMA) / (GAMMA_C * phaseVolumeTime);
            const cN2 = (GAMMA * GAMMA * lambdaPaMin * adjCrushN2Pa) / (GAMMA_C * GAMMA_C * phaseVolumeTime);
            const discN2 = Math.max(0, bN2 * bN2 - 4.0 * cN2);
            state.allowableGradientN2[i] = (bN2 + Math.sqrt(discN2)) / 2.0 / 1.0e5;
        }
    }
    function calcStartOfDecoZone(state, startingDepth, ascentRate, o2Frac, heFrac, settings, setpoint) {
        const slp = getSLP(settings);
        const surfP = getSurfacePressure(settings);
        const startAmb = getAmbientPressure(startingDepth, settings);
        const pressureRate = -Math.abs(ascentRate) / slp;
        const ccr = {
            circuit: settings.circuit || 'OC',
            setpoint,
            descentSetpoint: settings.descentSetpoint,
            bailout: settings.bailout,
            scrLoopVolume: settings.scrLoopVolume,
            scrMetabolicO2: settings.scrMetabolicO2,
            scrRuntimeMin: settings._scrRuntimeMin || 0,
        };
        const params = getCCRInertSchreinerParams(startAmb, setpoint, o2Frac, heFrac, pressureRate, ccr);
        const inspiredHe0 = params.inspHeStart;
        const inspiredN20 = params.inspN2Start;
        const heRate = params.rHe;
        const n2Rate = params.rN2;
        const lowBound = 0;
        const highBound = Math.max(0, -startAmb / pressureRate);
        let depthStart = 0;
        for (let i = 0; i < NC; i++) {
            const pHe0 = state.tissues[i].pHe;
            const pN20 = state.tissues[i].pN2;
            const f0 = pHe0 + pN20 + CONSTANT_PRESSURE_OTHER_GASES - startAmb;
            const pHeHi = schreiner(inspiredHe0, heRate, highBound, ZHL16C_He[i].ht, pHe0);
            const pN2Hi = schreiner(inspiredN20, n2Rate, highBound, ZHL16C_N2[i].ht, pN20);
            const fHi = pHeHi + pN2Hi + CONSTANT_PRESSURE_OTHER_GASES;
            if (f0 * fHi >= 0) continue;
            let t = f0 < 0 ? lowBound : highBound;
            let diff = f0 < 0 ? highBound - lowBound : lowBound - highBound;
            for (let iter = 0; iter < 100; iter++) {
                diff *= 0.5;
                const midT = t + diff;
                const midHe = schreiner(inspiredHe0, heRate, midT, ZHL16C_He[i].ht, pHe0);
                const midN2 = schreiner(inspiredN20, n2Rate, midT, ZHL16C_N2[i].ht, pN20);
                const midAmb = startAmb + pressureRate * midT;
                const fMid = midHe + midN2 + CONSTANT_PRESSURE_OTHER_GASES - midAmb;
                if (fMid <= 0) t = midT;
                if (Math.abs(diff) < 1e-3 || fMid === 0) break;
            }
            const compartmentDepth = Math.max(0, (startAmb + pressureRate * t) - surfP) * slp;
            depthStart = Math.max(depthStart, compartmentDepth);
        }
        return depthStart;
    }
    function projectedAscent(state, startingDepth, ascentRate, stopDepth, stepSize, o2Frac, heFrac, settings, setpoint) {
        const slp = getSLP(settings);
        const surfP = getSurfacePressure(settings);
        const startAmb = getAmbientPressure(startingDepth, settings);
        const pressureRate = -Math.abs(ascentRate) / slp;
        const ccr = {
            circuit: settings.circuit || 'OC',
            setpoint,
            descentSetpoint: settings.descentSetpoint,
            bailout: settings.bailout,
            scrLoopVolume: settings.scrLoopVolume,
            scrMetabolicO2: settings.scrMetabolicO2,
            scrRuntimeMin: settings._scrRuntimeMin || 0,
        };
        const params = getCCRInertSchreinerParams(startAmb, setpoint, o2Frac, heFrac, pressureRate, ccr);
        const inspiredHe0 = params.inspHeStart;
        const inspiredN20 = params.inspN2Start;
        const heRate = params.rHe;
        const n2Rate = params.rN2;
        let candidateStop = stopDepth;
        while (candidateStop > 0) {
            const endAmb = getAmbientPressure(candidateStop, settings);
            const segmentTime = (endAmb - startAmb) / pressureRate;
            let violated = false;
            for (let i = 0; i < NC; i++) {
                const tempHe = schreiner(inspiredHe0, heRate, segmentTime, ZHL16C_He[i].ht, state.tissues[i].pHe);
                const tempN2 = schreiner(inspiredN20, n2Rate, segmentTime, ZHL16C_N2[i].ht, state.tissues[i].pN2);
                const allowGrad = getWeightedAllowableGradient(state, i, tempHe, tempN2, false);
                const allowableLoading = endAmb + allowGrad - CONSTANT_PRESSURE_OTHER_GASES;
                if (tempHe + tempN2 > allowableLoading) {
                    candidateStop += stepSize;
                    violated = true;
                    break;
                }
            }
            if (!violated) return candidateStop;
        }
        return stopDepth;
    }
    const VPM_CRITICAL_RADIUS_FACTOR = [
        1.00, 
        1.05, 
        1.12, 
        1.22, 
        1.35, 
        1.50  
    ];
    function setCriticalRadiiForConservatism(state, conservatism, settings) {
        const consIdx = Math.max(0, Math.min(5, Math.round(conservatism || 0)));
        const factor = VPM_CRITICAL_RADIUS_FACTOR[consIdx];
        const surfP = settings ? getSurfacePressure(settings) : 1.01325;
        const altFactor = Math.pow(1.01325 / surfP, 1.0 / 3.0);
        const rN2 = INITIAL_RADIUS_N2 * altFactor * factor;
        const rHe = INITIAL_RADIUS_He * altFactor * factor;
        for (let i = 0; i < NC; i++) {
            state.critRadiiN2[i] = rN2;
            state.critRadiiHe[i] = rHe;
            state.adjustedCritRadiiN2[i] = rN2;
            state.adjustedCritRadiiHe[i] = rHe;
            state.regeneratedRadiiN2[i] = rN2;
            state.regeneratedRadiiHe[i] = rHe;
        }
    }
    function calcAllowableGradients(state, model, settings, conservatism) {
        for (let i = 0; i < NC; i++) {
            const rN2 = state.regeneratedRadiiN2[i];
            const baseGradN2 = twoGammaOverR(GAMMA, rN2)
                * (GAMMA_C - GAMMA) / GAMMA_C;
            const rHe = state.regeneratedRadiiHe[i];
            const baseGradHe = twoGammaOverR(GAMMA, rHe)
                * (GAMMA_C - GAMMA) / GAMMA_C;
            state.initialAllowableGradientN2[i] = baseGradN2;
            state.initialAllowableGradientHe[i] = baseGradHe;
            state.allowableGradientN2[i] = state.initialAllowableGradientN2[i];
            state.allowableGradientHe[i] = state.initialAllowableGradientHe[i];
            state.decoGradientN2[i] = state.allowableGradientN2[i];
            state.decoGradientHe[i] = state.allowableGradientHe[i];
        }
    }
    function solveBubbleRadius(a, b, c, lowBound, highBound) {
        let low = lowBound;
        let high = Math.max(highBound, lowBound);
        for (let iter = 0; iter < 80; iter++) {
            const mid = (low + high) * 0.5;
            const fMid = mid * (mid * (a * mid - b)) - c;
            if (Math.abs(fMid) < 1e-18 || Math.abs(high - low) < 1e-14) return mid;
            const fLow = low * (low * (a * low - b)) - c;
            if ((fLow <= 0 && fMid <= 0) || (fLow >= 0 && fMid >= 0)) {
                low = mid;
            } else {
                high = mid;
            }
        }
        return (low + high) * 0.5;
    }
    function boyleLawCompensation(state, firstStopDepth, decoStopDepth, stepSize, settings) {
        const surfP = getSurfacePressure(settings);
        const unitsFactor = getSLP(settings);
        const firstStop = Math.max(0, firstStopDepth || state.firstStopDepth || 0);
        const currentStop = Math.max(0, decoStopDepth || firstStop);
        const nextStop = Math.max(0, currentStop - (stepSize || 0));
        const ambFirstPa = (surfP + firstStop / unitsFactor) * 101325.0;
        const ambNextPa = (surfP + nextStop / unitsFactor) * 101325.0;
        const safeAmbNextPa = Math.max(ambNextPa, 1.0);
        const rootFactor = Math.pow(Math.max(ambFirstPa / safeAmbNextPa, 1.0), 1.0 / 3.0);
        for (let i = 0; i < NC; i++) {
            const gradHePa = Math.max(1e-9, (state.allowableGradientHe[i] / unitsFactor) * 101325.0);
            const radiusHe = (2.0 * GAMMA) / gradHePa;
            const cHe = (ambFirstPa + (2.0 * GAMMA) / radiusHe) * radiusHe * radiusHe * radiusHe;
            const endRadiusHe = solveBubbleRadius(
                safeAmbNextPa,
                -2.0 * GAMMA,
                cHe,
                radiusHe,
                radiusHe * rootFactor
            );
            state.decoGradientHe[i] = ((2.0 * GAMMA) / endRadiusHe / 101325.0) * unitsFactor;
            const gradN2Pa = Math.max(1e-9, (state.allowableGradientN2[i] / unitsFactor) * 101325.0);
            const radiusN2 = (2.0 * GAMMA) / gradN2Pa;
            const cN2 = (ambFirstPa + (2.0 * GAMMA) / radiusN2) * radiusN2 * radiusN2 * radiusN2;
            const endRadiusN2 = solveBubbleRadius(
                safeAmbNextPa,
                -2.0 * GAMMA,
                cN2,
                radiusN2,
                radiusN2 * rootFactor
            );
            state.decoGradientN2[i] = ((2.0 * GAMMA) / endRadiusN2 / 101325.0) * unitsFactor;
        }
        state.useDecoGradients = true;
    }
    function extendedCompensation(state, settings) {
        const surfP = getSurfacePressure(settings);
        const pMaxAmb = state.maxAmbientPressure;
        const maxDepthBar = pMaxAmb - surfP;
        const threshold = 6.0; 
        if (maxDepthBar <= threshold) return;
        const extFactor = 1.0 - (maxDepthBar - threshold) * 0.02;
        const clampedFactor = Math.max(0.5, Math.min(1.0, extFactor));
        for (let i = 0; i < NC; i++) {
            state.allowableGradientN2[i] *= clampedFactor;
            state.allowableGradientHe[i] *= clampedFactor;
        }
    }
    function getVPMCeiling(state, settings) {
        const surfP = getSurfacePressure(settings);
        const slp = getSLP(settings);
        let maxCeilingP = 0;
        for (let i = 0; i < NC; i++) {
            const pN2 = state.tissues[i].pN2;
            const pHe = state.tissues[i].pHe;
            const pTotal = pN2 + pHe;
            const allowGrad = getWeightedAllowableGradient(state, i, pHe, pN2, state.useDecoGradients);
            const ceilingP = pTotal + CONSTANT_PRESSURE_OTHER_GASES - allowGrad;
            if (ceilingP > maxCeilingP) {
                maxCeilingP = ceilingP;
            }
        }
        const ceilingDepth = (maxCeilingP - surfP) * slp;
        return Math.max(0, ceilingDepth);
    }
    function applyGFSurfacing(state, stopDepth, firstStopDepth, gfHi, settings) {
        if (firstStopDepth <= 0) return;
        const fraction = stopDepth / firstStopDepth; 
        const surfP = getSurfacePressure(settings);
        const pAmb = getAmbientPressure(stopDepth, settings);
        const gf = gfHi / 100;
        for (let i = 0; i < NC; i++) {
            const pN2 = state.tissues[i].pN2;
            const pHe = state.tissues[i].pHe;
            const pTotal = pN2 + pHe;
            let a, b;
            if (pTotal > 0) {
                a = (pN2 * ZHL16C_N2[i].a + pHe * ZHL16C_He[i].a) / pTotal;
                b = (pN2 * ZHL16C_N2[i].b + pHe * ZHL16C_He[i].b) / pTotal;
            } else {
                a = ZHL16C_N2[i].a;
                b = ZHL16C_N2[i].b;
            }
            const mValue = a + pAmb / b;
            const buhlGrad = gf * (mValue - pAmb);
            let vpmGrad;
            if (pTotal > 0) {
                vpmGrad = (pN2 * state.allowableGradientN2[i] + pHe * state.allowableGradientHe[i]) / pTotal;
            } else {
                vpmGrad = state.allowableGradientN2[i];
            }
            const blendedGrad = vpmGrad * fraction + buhlGrad * (1 - fraction);
            if (pTotal > 0) {
                state.allowableGradientN2[i] = blendedGrad;
                state.allowableGradientHe[i] = blendedGrad;
            }
        }
    }
    function isClearToAscendVPM(state, targetDepth, firstStopDepth, model, settings) {
        const pAmb = getAmbientPressure(targetDepth, settings);
        for (let i = 0; i < NC; i++) {
            const pN2 = state.tissues[i].pN2;
            const pHe = state.tissues[i].pHe;
            const pTotal = pN2 + pHe;
            const allowGrad = getWeightedAllowableGradient(state, i, pHe, pN2, state.useDecoGradients);
            if (pTotal + CONSTANT_PRESSURE_OTHER_GASES - allowGrad > pAmb) return false;
        }
        return true;
    }
    function getGasPpO2Limit(gas, settings) {
        const o2pct = gas.o2 * 100;
        if (settings.ppO2Low && settings.ppO2Mid && settings.ppO2High) {
            if (o2pct < 28)  return settings.ppO2Low;   // <28%: lean → 1.4
            if (o2pct < 45)  return settings.ppO2Mid;   // 28–44%: mid → 1.5
            if (o2pct < 100) return settings.ppO2High;  // ≥45%: rich → 1.6
        }
        return settings.ppO2Deco || 1.6;
    }
    function getManualDecoSwitchDepth(gas) {
        if (!gas || !(gas.depthOverrideOn === true || gas.depthOverrideOn === 1 || gas.depthOverrideOn === '1')) {
            return null;
        }
        const depth = Number(gas.depthOverride);
        return Number.isFinite(depth) && depth > 0 ? depth : null;
    }
    function selectDecoGas(depth, decoGases, ppO2Limit, settings) {
        let bestGas = null;
        let bestO2 = 0;
        const o2MaxDepth = settings.o2MaxDepth || 6;
        for (const gas of decoGases) {
            const manualSwitchDepth = getManualDecoSwitchDepth(gas);
            if (manualSwitchDepth != null) {
                if (depth <= manualSwitchDepth && gas.o2 > bestO2) {
                    bestO2 = gas.o2;
                    bestGas = gas;
                }
                continue;
            }
            const pAmb = getAmbientPressure(depth, settings);
            const ppO2 = gas.o2 * pAmb;
            const limit = getGasPpO2Limit(gas, settings);
            if (gas.o2 >= 0.995 && depth > o2MaxDepth) continue;
            // Pure O2: allowed at o2MaxDepth if allowO2AtMOD is on
            const pureO2Ok = gas.o2 >= 0.995 && (settings.allowO2AtMOD !== false);
            if (pureO2Ok || ppO2 <= limit) {
                if (gas.o2 > bestO2) { bestO2 = gas.o2; bestGas = gas; }
            }
        }
        return bestGas;
    }
    function roundUpToStop(depth, stepSize) {
        return Math.ceil(depth / stepSize) * stepSize;
    }
    function getEffectiveSetpoint(level, isCCR, settings, depthM) {
        if (!isCCR || !level) return 0;
        if (level.oc || level.scr) return 0;
        if (settings && settings.bailout) return 0;
        const surfP = settings ? getSurfacePressure(settings) : altSurfaceP;
        const ccr = {
            circuit: settings?.circuit || 'CCR',
            descentSetpoint: settings?.descentSetpoint ?? 0.7,
            bottomSetpoint: settings?.bottomSetpoint ?? 1.2,
            decoSetpoint: settings?.decoSetpoint ?? settings?.setpoint ?? 1.3,
            setpoint: settings?.setpoint ?? 1.3,
            bailout: false,
        };
        return getEffectiveSetpointAtDepth(depthM != null ? depthM : 0, ccr, surfP);
    }
    function vpmAccumPpo2(pAmb, sp, fO2, fHe, settings, depthM, useOC) {
        if (sp > 0) return Math.min(sp, pAmb);
        if (!useOC && settings.circuit === 'pSCR' && !settings.bailout && typeof getEffectivePpo2 === 'function') {
            const ccr = mergeCCRSettings({
                ...settings,
                circuit: 'pSCR',
                bailout: false,
                scrRuntimeMin: settings._scrRuntimeMin || 0,
            });
            return getEffectivePpo2(pAmb, 0, fO2, ccr, depthM, fHe);
        }
        return fO2 * pAmb;
    }
    function calculateOTU(ppO2, time) {
        if (ppO2 <= 0.5) return 0;
        return time * Math.pow((ppO2 - 0.5) / 0.5, 0.8333);
    }
    const CNS_RATE_ANDROID = [
        0.120, 0.122, 0.125, 0.127, 0.129, 0.130, 0.132, 0.134, 0.135, 0.138,
        0.140, 0.140, 0.140, 0.145, 0.150, 0.155, 0.160, 0.165, 0.170, 0.175,
        0.180, 0.180, 0.180, 0.185, 0.185, 0.190, 0.200, 0.200, 0.210, 0.210,
        0.220, 0.225, 0.230, 0.235, 0.240, 0.245, 0.250, 0.255, 0.260, 0.270,
        0.280, 0.290, 0.290, 0.300, 0.300, 0.305, 0.310, 0.315, 0.320, 0.325,
        0.330, 0.340, 0.350, 0.355, 0.360, 0.370, 0.380, 0.385, 0.400, 0.410,
        0.420, 0.430, 0.435, 0.4375, 0.439, 0.440, 0.445, 0.455, 0.460, 0.465,
        0.470, 0.475, 0.480, 0.495, 0.510, 0.515, 0.520, 0.530, 0.540, 0.550,
        0.560, 0.565, 0.570, 0.590, 0.600, 0.610, 0.620, 0.630, 0.640, 0.645,
        0.650, 0.660, 0.680, 0.695, 0.710, 0.720, 0.740, 0.770, 0.780, 0.800,
        0.830, 0.880, 0.930, 0.980, 1.040, 1.110, 1.190, 1.320, 1.470, 1.800,
        2.220, 2.500, 3.000, 3.500, 4.000, 4.500, 5.000, 6.000, 8.000, 9.000,
        10.000, 11.000, 12.500, 15.000, 20.000, 21.000, 22.000, 25.000, 31.250, 40.000,
        50.000
    ];
    function getCNSRate(ppO2) {
        if (ppO2 < 0.50) return 0;
        if (ppO2 > 2.00) return 100.0;
        if (ppO2 > 1.80) return 50.0;
        const idx = Math.max(50, Math.min(180, Math.round(ppO2 * 100))) - 50;
        return CNS_RATE_ANDROID[idx];
    }
    function calculateCNS(ppO2, time) {
        if (ppO2 < 0.50) return 0;
        return time * getCNSRate(ppO2);
    }
    function calculate(levels, decoGases, settings, model) {
        model = model || 'VPMB';
        settings = settings || {};
        if (!Array.isArray(levels) || levels.length === 0) {
            return {
                error: 'No bottom segments defined',
                code: 'INVALID_PROFILE',
                stops: [],
                plan: [],
                totalTime: 0,
                totalRuntime: 0,
            };
        }
        if (typeof validateEngineInputs === 'function') {
            const validation = validateEngineInputs(levels, decoGases);
            if (!validation.ok) return engineValidationError(validation);
        }
        const s = settings;
        if (isRebreatherCircuit(s.circuit || 'OC')) {
            const ccrVal = validateCcrCalculationInputs(levels, s, decoGases);
            if (!ccrVal.ok) return engineValidationError(ccrVal);
        }
        const safeDecoGases = Array.isArray(decoGases) ? decoGases.filter(g => g != null) : [];
        function ctxUseOCForPpo2(calcSettings) {
            return calcSettings.bailout || calcSettings.circuit !== 'pSCR';
        }
        function ctxOffLoop(ctx) {
            return !!(ctx.forcedOCMode || ctxUseOCForPpo2(settings));
        }
        const stepSize = settings.stepSize || (settings.metric ? 3 : 10);
        const lastStop = settings.lastStop || (settings.metric ? 3 : 10);
        const descentRate = settings.descentRate || (settings.metric ? 20 : 60);
        const ascentRate = settings.ascentRate || (settings.metric ? 10 : 30);
        const decoAscentRate = settings.decoAscentRate || (settings.metric ? 3 : 10);
        const surfaceAscentRate = settings.surfaceAscentRate || decoAscentRate;
        const ppO2Deco = settings.ppO2Deco || 1.6;
        const minStopTime = settings.minStopTime || 1;
        const conservatism = settings.conservatism || 0;
        const firstStop30sec = settings.firstStop30sec || false;
        const firstStopDoubleStep = settings.firstStopDoubleStep || false;
        const state = createVPMState(settings);
        setCriticalRadiiForConservatism(state, conservatism, settings);
        const normalizedDecoGases = safeDecoGases.map(g => {
            const f = gasFractionsFromPct(g.o2, g.he);
            return {
            o2: f.o2Frac,
            he: f.heFrac,
            label: `${f.o2Pct}/${f.hePct}`,
            depthOverrideOn: g.depthOverrideOn === true || g.depthOverrideOn === 1 || g.depthOverrideOn === '1',
            depthOverride: g.depthOverride != null && g.depthOverride !== '' ? Number(g.depthOverride) : null
        };
        });
        let deepestLevelIndex = 0;
        for (let i = 1; i < levels.length; i++) {
            if (levels[i].depth > levels[deepestLevelIndex].depth) {
                deepestLevelIndex = i;
            }
        }
        let continuationLevels = [];
        if (deepestLevelIndex < levels.length - 1) {
            let monotonicContinuation = true;
            for (let i = deepestLevelIndex + 1; i < levels.length; i++) {
                if (levels[i].depth > levels[i - 1].depth) {
                    monotonicContinuation = false;
                    break;
                }
            }
            if (monotonicContinuation) {
                continuationLevels = levels.slice(deepestLevelIndex + 1);
                levels = levels.slice(0, deepestLevelIndex + 1);
            }
        }
        const plan = [];
        const _origPush = plan.push;
        plan.push = function(seg) {
            try {
                if (!seg._tissues) {
                    seg._tissues = state.tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe }));
                }
                if (seg._cumOTU == null) seg._cumOTU = totalOTU;
                if (seg._cumCNS == null) seg._cumCNS = totalCNS;
                if (seg._ceilingDepth == null) {
                    seg._ceilingDepth = Math.max(0, getVPMCeiling(state, settings));
                }
            } catch (e) {  }
            return _origPush.call(this, seg);
        };
        let runtime = 0;
        let currentDepth = 0;
        let totalOTU = settings._preOTU || 0;  // carry OTU from previous dive if repetitive
        let totalCNS = settings._preCNS || 0;  // carry CNS (decayed) from previous dive if repetitive
        function addExposureToContext(ctx, fromDepth, toDepth, time) {
            if (time <= 0) return;
            const steps = Math.max(1, Math.ceil(Math.abs(toDepth - fromDepth)));
            const dt = time / steps;
            for (let s = 0; s < steps; s++) {
                const frac = s / steps;
                const depth = fromDepth + (toDepth - fromDepth) * frac;
                const pAmb = getAmbientPressure(depth, settings);
                settings._scrRuntimeMin = ctx.runtime + frac * time;
                const ppO2 = vpmAccumPpo2(pAmb, ctx.currentSP, ctx.currentO2, ctx.currentHe, settings, depth, ctxOffLoop(ctx));
                ctx.totalOTU += calculateOTU(ppO2, dt);
                ctx.totalCNS += calculateCNS(ppO2, dt);
            }
        }
        function addConstantExposure(ctx, depth, time) {
            if (time <= 0) return;
            const pAmb = getAmbientPressure(depth, settings);
            settings._scrRuntimeMin = ctx.runtime;
            const ppO2 = vpmAccumPpo2(pAmb, ctx.currentSP, ctx.currentO2, ctx.currentHe, settings, depth, ctxOffLoop(ctx));
            ctx.totalOTU += calculateOTU(ppO2, time);
            ctx.totalCNS += calculateCNS(ppO2, time);
        }
        function makeScheduleContext(baseState, startDepth, startRuntime, startOTU, startCNS, o2, he, gasLabel, sp, outPlan, forcedOCModeAtStart) {
            return {
                state: cloneVPMState(baseState),
                currentDepth: startDepth,
                runtime: startRuntime,
                totalOTU: startOTU,
                totalCNS: startCNS,
                currentO2: o2,
                currentHe: he,
                currentGasLabel: gasLabel,
                currentSP: sp,
                forcedOCMode: !!forcedOCModeAtStart,
                firstStopDepth: 0,
                plan: outPlan || null,
                continuationFinalPhase: false
            };
        }
        function appendPlan(ctx, segment) {
            if (!ctx.plan) return;
            try {
                if (segment.setpoint == null) {
                    segment.setpoint = ctx.currentSP > 0 ? ctx.currentSP : 0;
                }
                segment._tissues = ctx.state.tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe }));
                segment._cumOTU = ctx.totalOTU;
                segment._cumCNS = ctx.totalCNS;
                segment._ceilingDepth = Math.max(0, getVPMCeiling(ctx.state, settings));
            } catch (e) {  }
            ctx.plan.push(segment);
        }
        function runAscentSegment(ctx, toDepth, rate) {
            settings._scrRuntimeMin = ctx.runtime;
            const fromDepth = ctx.currentDepth;
            const segTime = loadTissuesLinear(
                ctx.state, fromDepth, toDepth, rate,
                ctx.currentO2, ctx.currentHe, settings, ctx.currentSP
            );
            ctx.runtime += segTime;
            addExposureToContext(ctx, fromDepth, toDepth, segTime);
            appendPlan(ctx, {
                type: 'ascent',
                startDepth: fromDepth,
                endDepth: toDepth,
                time: Math.round(segTime * 10) / 10,
                runtime: Math.round(ctx.runtime * 10) / 10,
                gas: ctx.currentGasLabel,
                o2: Math.round(ctx.currentO2 * 100),
                he: Math.round(ctx.currentHe * 100)
            });
            ctx.currentDepth = toDepth;
            return segTime;
        }
        function runRoundedDecoStop(ctx, stopDepth, nextStop) {
            settings._scrRuntimeMin = ctx.runtime;
            let effectiveMinStop = (firstStop30sec && stopDepth === ctx.firstStopDepth) ? 0.5 : minStopTime;
            const roundedRuntime = (ctx.continuationFinalPhase && stopDepth <= 12)
                ? ctx.runtime
                : Math.round((ctx.runtime / effectiveMinStop) + 0.5) * effectiveMinStop;
            let segmentTime = roundedRuntime - ctx.runtime;
            ctx.runtime = roundedRuntime;
            let totalStopTime = segmentTime;
            const pAmb = getAmbientPressure(stopDepth, settings);
            const ccr = {
                circuit: settings.circuit || 'OC',
                setpoint: ctx.currentSP,
                descentSetpoint: settings.descentSetpoint,
                bailout: settings.bailout,
                scrLoopVolume: settings.scrLoopVolume,
                scrMetabolicO2: settings.scrMetabolicO2,
                scrRuntimeMin: ctx.runtime,
            };
            const insp = getInspiredInertPressures(pAmb, ctx.currentSP, ctx.currentO2, ctx.currentHe, ccr);
            const inspHe = insp.pHe;
            const inspN2 = insp.pN2;
            for (let guard = 0; guard < 1000; guard++) {
                for (let i = 0; i < NC; i++) {
                    ctx.state.tissues[i].pHe = haldane(ctx.state.tissues[i].pHe, inspHe, ZHL16C_He[i].ht, segmentTime);
                    ctx.state.tissues[i].pN2 = haldane(ctx.state.tissues[i].pN2, inspN2, ZHL16C_N2[i].ht, segmentTime);
                }
                const decoCeiling = getVPMCeiling(ctx.state, settings);
                const clearTolerance = (ctx.continuationFinalPhase && stopDepth <= 6)
                    ? (nextStop <= 0 ? 0.35 : 0.1)
                    : 1e-9;
                if (decoCeiling <= nextStop + clearTolerance) break;
                segmentTime = effectiveMinStop;
                totalStopTime += effectiveMinStop;
                ctx.runtime += effectiveMinStop;
            }
            settings._scrRuntimeMin = ctx.runtime;
            const ppO2Stop = vpmAccumPpo2(pAmb, ctx.currentSP, ctx.currentO2, ctx.currentHe, settings, stopDepth, ctxOffLoop(ctx));
            ctx.totalOTU += calculateOTU(ppO2Stop, totalStopTime);
            ctx.totalCNS += calculateCNS(ppO2Stop, totalStopTime);
            appendPlan(ctx, {
                type: 'stop',
                depth: stopDepth,
                time: totalStopTime,
                runtime: Math.round(ctx.runtime * 10) / 10,
                gas: ctx.currentGasLabel,
                o2: Math.round(ctx.currentO2 * 100),
                he: Math.round(ctx.currentHe * 100)
            });
            return totalStopTime;
        }
        function maybeSwitchDecoGas(ctx, depth) {
            if (isRebreatherCircuit(settings.circuit) && !settings.bailout && !ctx.forcedOCMode) return;
            const decoGas = selectDecoGas(depth, normalizedDecoGases, ppO2Deco, settings);
            if (!decoGas) return;
            const pAmb = getAmbientPressure(depth, settings);
            const ocPpO2 = decoGas.o2 * pAmb;
            const ccrPpO2 = ctx.currentSP > 0 ? Math.min(ctx.currentSP, pAmb) : 0;
            if (decoGas.o2 > ctx.currentO2 || (ctx.currentSP > 0 && ocPpO2 > ccrPpO2)) {
                ctx.currentO2 = decoGas.o2;
                ctx.currentHe = decoGas.he;
                ctx.currentGasLabel = decoGas.label;
                ctx.currentSP = 0;
            }
        }
        function calcIntermediateFirstStopDepth(ctx, targetDepth) {
            let rawCeiling = getVPMCeiling(ctx.state, settings);
            if (rawCeiling <= targetDepth) return 0;
            let firstStopDepth = Math.floor(rawCeiling / stepSize) * stepSize;
            if (firstStopDoubleStep && firstStopDepth > Math.max(lastStop, targetDepth)) {
                const doubleStep = stepSize * 2;
                firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
            }
            if (firstStopDepth >= ctx.currentDepth) firstStopDepth = ctx.currentDepth - stepSize;
            if (firstStopDepth < targetDepth + stepSize) firstStopDepth = targetDepth + stepSize;
            ctx.state.firstStopDepth = firstStopDepth;
            if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                boyleLawCompensation(ctx.state, firstStopDepth, firstStopDepth, stepSize, settings);
                rawCeiling = getVPMCeiling(ctx.state, settings);
                firstStopDepth = Math.floor(rawCeiling / stepSize) * stepSize;
                if (firstStopDoubleStep && firstStopDepth > Math.max(lastStop, targetDepth)) {
                    const doubleStep = stepSize * 2;
                    firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
                }
                if (firstStopDepth >= ctx.currentDepth) firstStopDepth = ctx.currentDepth - stepSize;
                if (firstStopDepth < targetDepth + stepSize) firstStopDepth = targetDepth + stepSize;
                ctx.state.firstStopDepth = firstStopDepth;
            }
            return firstStopDepth;
        }
        function runStopSequenceToDepth(ctx, firstStopDepth, targetDepth, anchorFirstStopDepth) {
            if (firstStopDepth <= 0 || firstStopDepth <= targetDepth) {
                runAscentSegment(ctx, targetDepth, ascentRate);
                return ctx;
            }
            const phaseFirstStopDepth = anchorFirstStopDepth || firstStopDepth;
            ctx.firstStopDepth = phaseFirstStopDepth;
            runAscentSegment(ctx, firstStopDepth, ascentRate);
            let stopDepth = firstStopDepth;
            while (stopDepth > targetDepth) {
                maybeSwitchDecoGas(ctx, stopDepth);
                const nextStop = Math.max(targetDepth, stopDepth - stepSize);
                if (model === 'VPMB_GFS') {
                    const gfsValue = settings.gfs || settings.gfHi || 85;
                    applyGFSurfacing(ctx.state, stopDepth, phaseFirstStopDepth, gfsValue, settings);
                }
                if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                    boyleLawCompensation(ctx.state, phaseFirstStopDepth, stopDepth + stepSize, stepSize, settings);
                }
                runRoundedDecoStop(ctx, stopDepth, nextStop);
                if (nextStop <= targetDepth) {
                    const segTime = loadTissuesLinear(
                        ctx.state, stopDepth, targetDepth, decoAscentRate,
                        ctx.currentO2, ctx.currentHe, settings, ctx.currentSP
                    );
                    ctx.runtime += segTime;
                    addExposureToContext(ctx, stopDepth, targetDepth, segTime);
                    ctx.currentDepth = targetDepth;
                    break;
                }
                runAscentSegment(ctx, nextStop, decoAscentRate);
                stopDepth = nextStop;
            }
            return ctx;
        }
        function appendLevelHold(ctx, level) {
            if (level.oc) ctx.forcedOCMode = true;
            const nextLevelOffLoop = isCCR && !!(level.oc || level.scr);
            ctx.currentDepth = level.depth;
            ctx.currentO2 = level.o2 / 100;
            ctx.currentHe = level.he / 100;
            ctx.currentGasLabel = `${level.o2}/${level.he}`;
            ctx.currentSP = (ctx.forcedOCMode || nextLevelOffLoop) ? 0 : getEffectiveSetpoint(level, isCCR, settings, level.depth);
            if (level.time <= 0) return;
            settings._scrRuntimeMin = ctx.runtime;
            loadTissuesConstant(ctx.state, level.depth, level.time, ctx.currentO2, ctx.currentHe, settings, ctx.currentSP);
            ctx.runtime += level.time;
            addConstantExposure(ctx, level.depth, level.time);
            appendPlan(ctx, {
                type: 'bottom',
                depth: level.depth,
                time: Math.round(level.time * 10) / 10,
                runtime: Math.round(ctx.runtime * 10) / 10,
                gas: ctx.currentGasLabel,
                o2: level.o2,
                he: level.he
            });
        }
        function calcSurfaceFirstStopDepth(scheduleState, fromDepth, o2, he, sp, anchorFirstStopDepth) {
            let rawCeiling = getVPMCeiling(scheduleState, settings);
            if (rawCeiling <= 0) return 0;
            let firstStopDepth = roundUpToStop(rawCeiling, stepSize);
            if (firstStopDoubleStep && firstStopDepth > lastStop) {
                const doubleStep = stepSize * 2;
                firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
            }
            if (firstStopDepth >= fromDepth) firstStopDepth = fromDepth - stepSize;
            if (firstStopDepth < lastStop) firstStopDepth = lastStop;
            firstStopDepth = projectedAscent(
                scheduleState,
                Math.max(fromDepth, 0),
                ascentRate,
                firstStopDepth,
                stepSize,
                o2,
                he,
                settings,
                sp
            );
            if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                boyleLawCompensation(
                    scheduleState,
                    anchorFirstStopDepth || firstStopDepth,
                    firstStopDepth,
                    stepSize,
                    settings
                );
                rawCeiling = getVPMCeiling(scheduleState, settings);
                if (rawCeiling > 0) {
                    firstStopDepth = roundUpToStop(rawCeiling, stepSize);
                    if (firstStopDoubleStep && firstStopDepth > lastStop) {
                        const doubleStep = stepSize * 2;
                        firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
                    }
                    if (firstStopDepth >= fromDepth) firstStopDepth = fromDepth - stepSize;
                    if (firstStopDepth < lastStop) firstStopDepth = lastStop;
                    firstStopDepth = projectedAscent(
                        scheduleState,
                        Math.max(fromDepth, 0),
                        ascentRate,
                        firstStopDepth,
                        stepSize,
                        o2,
                        he,
                        settings,
                        sp
                    );
                } else {
                    firstStopDepth = 0;
                }
            }
            return firstStopDepth;
        }
        function runContinuationSchedule(baseState, startDepth, startRuntime, startOTU, startCNS, o2, he, gasLabel, sp, outPlan, forcedOCAtStart) {
            const ctx = makeScheduleContext(baseState, startDepth, startRuntime, startOTU, startCNS, o2, he, gasLabel, sp, outPlan, forcedOCAtStart);
            let phaseFirstStopDepth = 0;
            for (const level of continuationLevels) {
                const levelFirstStopDepth = calcIntermediateFirstStopDepth(ctx, level.depth);
                if (!phaseFirstStopDepth && levelFirstStopDepth > 0) {
                    phaseFirstStopDepth = levelFirstStopDepth;
                }
                runStopSequenceToDepth(ctx, levelFirstStopDepth, level.depth, phaseFirstStopDepth || levelFirstStopDepth);
                appendLevelHold(ctx, level);
            }
            const finalFirstStopDepth = calcSurfaceFirstStopDepth(
                ctx.state,
                ctx.currentDepth,
                ctx.currentO2,
                ctx.currentHe,
                ctx.currentSP,
                phaseFirstStopDepth
            );
            if (!phaseFirstStopDepth && finalFirstStopDepth > 0) {
                phaseFirstStopDepth = finalFirstStopDepth;
            }
            ctx.continuationFinalPhase = true;
            runStopSequence(ctx, finalFirstStopDepth, true, phaseFirstStopDepth || finalFirstStopDepth);
            return { ctx, firstStopDepth: phaseFirstStopDepth };
        }
        function runStopSequence(ctx, firstStopDepth, recordSurface, anchorFirstStopDepth) {
            if (firstStopDepth <= 0) {
                runAscentSegment(ctx, 0, surfaceAscentRate);
                if (recordSurface) {
                    appendPlan(ctx, { type: 'surface', depth: 0, time: 0, runtime: Math.round(ctx.runtime * 10) / 10, gas: ctx.currentGasLabel });
                }
                return ctx;
            }
            const phaseFirstStopDepth = anchorFirstStopDepth || firstStopDepth;
            ctx.firstStopDepth = phaseFirstStopDepth;
            runAscentSegment(ctx, firstStopDepth, ascentRate);
            let stopDepth = firstStopDepth;
            while (stopDepth > 0) {
                maybeSwitchDecoGas(ctx, stopDepth);
                const nextStop = stopDepth <= lastStop ? 0 : stopDepth - stepSize;
                if (model === 'VPMB_GFS') {
                    const gfsValue = settings.gfs || settings.gfHi || 85;
                    applyGFSurfacing(ctx.state, stopDepth, phaseFirstStopDepth, gfsValue, settings);
                }
                if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                    boyleLawCompensation(ctx.state, phaseFirstStopDepth, stopDepth + stepSize, stepSize, settings);
                }
                runRoundedDecoStop(ctx, stopDepth, nextStop);
                if (nextStop <= 0) {
                    runAscentSegment(ctx, 0, surfaceAscentRate);
                    break;
                }
                runAscentSegment(ctx, nextStop, decoAscentRate);
                stopDepth = nextStop;
            }
            if (recordSurface) {
                appendPlan(ctx, { type: 'surface', depth: 0, time: 0, runtime: Math.round(ctx.runtime * 10) / 10, gas: ctx.currentGasLabel });
            }
            return ctx;
        }
        const isCCR = isRebreatherCircuit(settings.circuit) && !settings.bailout;
        let curO2 = levels[0].o2 / 100;
        let curHe = levels[0].he / 100;
        let curGasLabel = `${levels[0].o2}/${levels[0].he}`;
        let forcedOCMode = isCCR && !!levels[0].oc;
        let curSP = forcedOCMode ? 0 : getEffectiveSetpoint(levels[0], isCCR, settings, levels[0].depth);
        function runInterLevelDecoAscent(targetDepth) {
            calcCrushing(state, settings);
            applyNuclearRegeneration(state, runtime);
            const offLoopPath = isCCR && settings.circuit !== 'pSCR' && (forcedOCMode || curSP <= 0);
            const interLevelConservatism = offLoopPath ? Math.max(0, conservatism - 1) : conservatism;
            calcAllowableGradients(state, model, settings, interLevelConservatism);
            if (model === 'VPMBE') extendedCompensation(state, settings);
            let rawCeiling = getVPMCeiling(state, settings);
            if (rawCeiling <= targetDepth) {
                settings._scrRuntimeMin = runtime;
                const ascTime = loadTissuesLinear(
                    state, currentDepth, targetDepth, ascentRate,
                    curO2, curHe, settings, curSP
                );
                runtime += ascTime;
                const stepsA = Math.max(1, Math.ceil(Math.abs(currentDepth - targetDepth)));
                const dtA = ascTime / stepsA;
                for (let s = 0; s < stepsA; s++) {
                    const frac = s / stepsA;
                    const depth = currentDepth + (targetDepth - currentDepth) * frac;
                    const pAmbSeg = getAmbientPressure(depth, settings);
                    const ppO2Seg = vpmAccumPpo2(pAmbSeg, curSP, curO2, curHe, settings, depth, forcedOCMode);
                    totalOTU += calculateOTU(ppO2Seg, dtA);
                    totalCNS += calculateCNS(ppO2Seg, dtA);
                }
                plan.push({
                    type: 'ascent', startDepth: currentDepth, endDepth: targetDepth,
                    time: Math.round(ascTime * 10) / 10,
                    runtime: Math.round(runtime * 10) / 10,
                    gas: curGasLabel,
                    o2: Math.round(curO2 * 100),
                    he: Math.round(curHe * 100),
                    setpoint: curSP > 0 ? curSP : 0
                });
                return { depth: targetDepth, o2: curO2, he: curHe, gasLabel: curGasLabel, sp: curSP };
            }
            let firstStopDepth = offLoopPath
                ? Math.floor(rawCeiling / stepSize) * stepSize
                : roundUpToStop(rawCeiling, stepSize);
            if (firstStopDoubleStep && firstStopDepth > Math.max(lastStop, targetDepth)) {
                const doubleStep = stepSize * 2;
                firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
            }
            if (firstStopDepth >= currentDepth) firstStopDepth = currentDepth - stepSize;
            if (firstStopDepth < targetDepth + stepSize) firstStopDepth = targetDepth + stepSize;
            state.firstStopDepth = firstStopDepth;
            if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                boyleLawCompensation(state, firstStopDepth, firstStopDepth, stepSize, settings);
                rawCeiling = getVPMCeiling(state, settings);
                firstStopDepth = offLoopPath
                    ? Math.floor(rawCeiling / stepSize) * stepSize
                    : roundUpToStop(rawCeiling, stepSize);
                if (firstStopDoubleStep && firstStopDepth > Math.max(lastStop, targetDepth)) {
                    const doubleStep = stepSize * 2;
                    firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
                }
                if (firstStopDepth >= currentDepth) firstStopDepth = currentDepth - stepSize;
                if (firstStopDepth < targetDepth + stepSize) firstStopDepth = targetDepth + stepSize;
                state.firstStopDepth = firstStopDepth;
            }
            settings._scrRuntimeMin = runtime;
            const ascTimeToFirst = loadTissuesLinear(
                state, currentDepth, firstStopDepth, ascentRate,
                curO2, curHe, settings, curSP
            );
            runtime += ascTimeToFirst;
            {
                const stepsA = Math.max(1, Math.ceil(Math.abs(currentDepth - firstStopDepth)));
                const dtA = ascTimeToFirst / stepsA;
                for (let s = 0; s < stepsA; s++) {
                    const frac = s / stepsA;
                    const depthSeg = currentDepth + (firstStopDepth - currentDepth) * frac;
                    const pAmbSeg = getAmbientPressure(depthSeg, settings);
                    const ppO2Seg = vpmAccumPpo2(pAmbSeg, curSP, curO2, curHe, settings, depthSeg, forcedOCMode);
                    totalOTU += calculateOTU(ppO2Seg, dtA);
                    totalCNS += calculateCNS(ppO2Seg, dtA);
                }
            }
            plan.push({
                type: 'ascent', startDepth: currentDepth, endDepth: firstStopDepth,
                time: Math.round(ascTimeToFirst * 10) / 10,
                runtime: Math.round(runtime * 10) / 10,
                gas: curGasLabel,
                o2: Math.round(curO2 * 100),
                he: Math.round(curHe * 100),
                setpoint: curSP > 0 ? curSP : 0
            });
            let stopDepth = firstStopDepth;
            let maxIter = 500;
            while (stopDepth > targetDepth && maxIter-- > 0) {
                if (!isCCR) {
                    const decoGas = selectDecoGas(stopDepth, normalizedDecoGases, ppO2Deco, settings);
                    if (decoGas) {
                        const pAmbHere = getAmbientPressure(stopDepth, settings);
                        const ocPpO2 = decoGas.o2 * pAmbHere;
                        const ccrPpO2 = curSP > 0 ? Math.min(curSP, pAmbHere) : 0;
                        if (decoGas.o2 > curO2 || (curSP > 0 && ocPpO2 > ccrPpO2)) {
                            curO2 = decoGas.o2;
                            curHe = decoGas.he;
                            curGasLabel = decoGas.label;
                            curSP = 0;
                        }
                    }
                }
                const nextStop = stopDepth - stepSize;
                const nextStopClamped = nextStop < targetDepth ? targetDepth : nextStop;
                if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                    boyleLawCompensation(state, firstStopDepth, stopDepth + stepSize, stepSize, settings);
                }
                const effectiveMinStop = (firstStop30sec && stopDepth === firstStopDepth) ? 0.5 : minStopTime;
                let stopTime = 0;
                while (!isClearToAscendVPM(state, nextStopClamped, firstStopDepth, model, settings) && stopTime < 999) {
                    settings._scrRuntimeMin = runtime;
                    loadTissuesConstant(state, stopDepth, effectiveMinStop, curO2, curHe, settings, curSP);
                    stopTime += effectiveMinStop;
                }
                if (stopTime < effectiveMinStop) stopTime = effectiveMinStop;
                runtime += stopTime;
                const pAmbStop = getAmbientPressure(stopDepth, settings);
                const ppO2Stop = vpmAccumPpo2(pAmbStop, curSP, curO2, curHe, settings, stopDepth, forcedOCMode);
                totalOTU += calculateOTU(ppO2Stop, stopTime);
                totalCNS += calculateCNS(ppO2Stop, stopTime);
                plan.push({
                    type: 'stop', depth: stopDepth, time: stopTime,
                    runtime: Math.round(runtime * 10) / 10,
                    gas: curGasLabel,
                    o2: Math.round(curO2 * 100),
                    he: Math.round(curHe * 100),
                    setpoint: curSP > 0 ? curSP : 0
                });
                if (nextStopClamped < stopDepth) {
                    settings._scrRuntimeMin = runtime;
                    const ascSegTime = loadTissuesLinear(state, stopDepth, nextStopClamped, decoAscentRate, curO2, curHe, settings, curSP);
                    runtime += ascSegTime;
                    const stepsA = Math.max(1, Math.ceil(Math.abs(stopDepth - nextStopClamped)));
                    const dtA = ascSegTime / stepsA;
                    for (let s = 0; s < stepsA; s++) {
                        const frac = s / stepsA;
                        const depthSeg = stopDepth + (nextStopClamped - stopDepth) * frac;
                        const pAmbSeg = getAmbientPressure(depthSeg, settings);
                        const ppO2Seg = vpmAccumPpo2(pAmbSeg, curSP, curO2, curHe, settings, depthSeg, forcedOCMode);
                        totalOTU += calculateOTU(ppO2Seg, dtA);
                        totalCNS += calculateCNS(ppO2Seg, dtA);
                    }
                }
                stopDepth = nextStopClamped;
            }
            currentDepth = targetDepth;
            return { depth: targetDepth, o2: curO2, he: curHe, gasLabel: curGasLabel, sp: curSP };
        }
        for (const level of levels) {
            const depth = level.depth;
            const time = level.time;
            const o2Frac = level.o2 / 100;
            const heFrac = level.he / 100;
            if (level.oc) forcedOCMode = true;
            const nextLevelOffLoop = isCCR && !!(level.oc || level.scr);
            const sp = (forcedOCMode || nextLevelOffLoop) ? 0 : getEffectiveSetpoint(level, isCCR, settings, depth);
            if (depth > currentDepth) {
                settings._scrRuntimeMin = runtime;
                const descTime = loadTissuesLinear(state, currentDepth, depth, descentRate, o2Frac, heFrac, settings, sp);
                runtime += descTime;
                const pAmbStart = getAmbientPressure(currentDepth, settings);
                const pAmbEnd = getAmbientPressure(depth, settings);
                const ppO2Start = vpmAccumPpo2(pAmbStart, sp, o2Frac, heFrac, settings, currentDepth, forcedOCMode || nextLevelOffLoop);
                const ppO2End = vpmAccumPpo2(pAmbEnd, sp, o2Frac, heFrac, settings, depth, forcedOCMode || nextLevelOffLoop);
                const ppO2Avg = (ppO2Start + ppO2End) / 2;
                totalOTU += calculateOTU(ppO2Avg, descTime);
                totalCNS += calculateCNS(ppO2Avg, descTime);
                plan.push({
                    type: 'descent', startDepth: currentDepth, endDepth: depth,
                    time: Math.round(descTime * 10) / 10,
                    runtime: Math.round(runtime * 10) / 10,
                    gas: `${level.o2}/${level.he}`, o2: level.o2, he: level.he,
                    setpoint: sp > 0 ? sp : 0
                });
                curO2 = o2Frac; curHe = heFrac; curGasLabel = `${level.o2}/${level.he}`; curSP = sp;
            } else if (depth < currentDepth) {
                runInterLevelDecoAscent(depth);
                curO2 = o2Frac; curHe = heFrac; curGasLabel = `${level.o2}/${level.he}`; curSP = sp;
            }
            const travelRate = depth < currentDepth ? ascentRate : descentRate;
            const descTimeFromLevel = Math.abs(depth - currentDepth) / travelRate;
            const bottomTime = Math.max(0, time - descTimeFromLevel);
            if (bottomTime > 0) {
                settings._scrRuntimeMin = runtime;
                loadTissuesConstant(state, depth, bottomTime, o2Frac, heFrac, settings, sp);
                runtime += bottomTime;
                const pAmbB = getAmbientPressure(depth, settings);
                const ppO2B = vpmAccumPpo2(pAmbB, sp, o2Frac, heFrac, settings, depth, forcedOCMode || nextLevelOffLoop);
                totalOTU += calculateOTU(ppO2B, bottomTime);
                totalCNS += calculateCNS(ppO2B, bottomTime);
                plan.push({
                    type: 'bottom', depth, time: Math.round(bottomTime * 10) / 10,
                    runtime: Math.round(runtime * 10) / 10,
                    gas: `${level.o2}/${level.he}`, o2: level.o2, he: level.he,
                    setpoint: sp > 0 ? sp : 0
                });
            }
            currentDepth = depth;
        }
        setCriticalRadiiForConservatism(state, conservatism, settings);
        calcCrushing(state, settings);
        applyNuclearRegeneration(state, runtime);
        calcAllowableGradients(state, model, settings, conservatism);
        if (model === 'VPMBE') {
            extendedCompensation(state, settings);
        }
        const lastLevel = continuationLevels.length > 0
            ? continuationLevels[continuationLevels.length - 1]
            : levels[levels.length - 1];
        const currentO2 = lastLevel.o2 / 100;
        const currentHe = lastLevel.he / 100;
        const currentGasLabel = `${lastLevel.o2}/${lastLevel.he}`;
        const currentSP = forcedOCMode ? 0 : getEffectiveSetpoint(lastLevel, isCCR, settings, lastLevel.depth);
        const startOfAscentState = cloneVPMState(state);
        const runtimeStartOfAscent = runtime;
        const totalOTUStartOfAscent = totalOTU;
        const totalCNSStartOfAscent = totalCNS;
        const depthStartOfAscent = currentDepth;
        settings._scrRuntimeMin = runtimeStartOfAscent;
        const depthStartOfDecoZone = calcStartOfDecoZone(
            startOfAscentState,
            depthStartOfAscent,
            ascentRate,
            currentO2,
            currentHe,
            settings,
            currentSP
        );
        const trialStartState = cloneVPMState(startOfAscentState);
        let runtimeStartOfDecoZone = runtimeStartOfAscent;
        if (depthStartOfDecoZone > 0 && depthStartOfDecoZone < depthStartOfAscent) {
            settings._scrRuntimeMin = runtimeStartOfAscent;
            runtimeStartOfDecoZone += loadTissuesLinear(
                trialStartState,
                depthStartOfAscent,
                depthStartOfDecoZone,
                ascentRate,
                currentO2,
                currentHe,
                settings,
                currentSP
            );
        }
        const decoPhaseRuntimeOrigin = depthStartOfDecoZone > 0 ? runtimeStartOfDecoZone : runtimeStartOfAscent;
        const decoZoneStart = depthStartOfDecoZone;
        let firstStopDepth = 0;
        let scheduleConverged = false;
        for (let cvIter = 0; cvIter < 12; cvIter++) {
            const trialBaseState = cloneVPMState(state);
            restoreTissues(trialBaseState, trialStartState.tissues);
            if (continuationLevels.length === 0) {
                let rawCeiling = getVPMCeiling(trialBaseState, settings);
                if (rawCeiling <= 0) {
                    firstStopDepth = 0;
                } else {
                    firstStopDepth = roundUpToStop(rawCeiling, stepSize);
                    if (firstStopDoubleStep && firstStopDepth > lastStop) {
                        const doubleStep = stepSize * 2;
                        firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
                    }
                    if (firstStopDepth > depthStartOfDecoZone && depthStartOfDecoZone > 0) {
                        firstStopDepth = Math.floor(depthStartOfDecoZone / stepSize) * stepSize;
                    }
                    if (firstStopDepth >= depthStartOfAscent) firstStopDepth = depthStartOfAscent - stepSize;
                    if (firstStopDepth < lastStop) firstStopDepth = rawCeiling > 0 ? lastStop : 0;
                    firstStopDepth = projectedAscent(
                        trialBaseState,
                        Math.max(depthStartOfDecoZone, 0),
                        ascentRate,
                        firstStopDepth,
                        stepSize,
                        currentO2,
                        currentHe,
                        settings,
                        currentSP
                    );
                }
                if (model === 'VPMB' || model === 'VPMBE' || model === 'VPMB_GFS' || model === 'VPMBFBO') {
                    boyleLawCompensation(trialBaseState, firstStopDepth, firstStopDepth, stepSize, settings);
                    rawCeiling = getVPMCeiling(trialBaseState, settings);
                    if (rawCeiling > 0) {
                        firstStopDepth = roundUpToStop(rawCeiling, stepSize);
                        if (firstStopDoubleStep && firstStopDepth > lastStop) {
                            const doubleStep = stepSize * 2;
                            firstStopDepth = Math.ceil(rawCeiling / doubleStep) * doubleStep;
                        }
                        if (firstStopDepth > depthStartOfDecoZone && depthStartOfDecoZone > 0) {
                            firstStopDepth = Math.floor(depthStartOfDecoZone / stepSize) * stepSize;
                        }
                        if (firstStopDepth >= depthStartOfAscent) firstStopDepth = depthStartOfAscent - stepSize;
                        if (firstStopDepth < lastStop) firstStopDepth = lastStop;
                        firstStopDepth = projectedAscent(
                            trialBaseState,
                            Math.max(depthStartOfDecoZone, 0),
                            ascentRate,
                            firstStopDepth,
                            stepSize,
                            currentO2,
                            currentHe,
                            settings,
                            currentSP
                        );
                    } else {
                        firstStopDepth = 0;
                    }
                }
            } else {
                firstStopDepth = 0;
            }
            let trialCtx;
            if (continuationLevels.length > 0) {
                trialCtx = runContinuationSchedule(
                    trialBaseState,
                    depthStartOfAscent,
                    runtimeStartOfAscent,
                    totalOTUStartOfAscent,
                    totalCNSStartOfAscent,
                    levels[levels.length - 1].o2 / 100,
                    levels[levels.length - 1].he / 100,
                    `${levels[levels.length - 1].o2}/${levels[levels.length - 1].he}`,
                    forcedOCMode ? 0 : getEffectiveSetpoint(levels[levels.length - 1], isCCR, settings, levels[levels.length - 1].depth),
                    null,
                    forcedOCMode
                ).ctx;
            } else {
                trialCtx = makeScheduleContext(
                    trialBaseState,
                    depthStartOfDecoZone > 0 ? depthStartOfDecoZone : depthStartOfAscent,
                    depthStartOfDecoZone > 0 ? runtimeStartOfDecoZone : runtimeStartOfAscent,
                    totalOTUStartOfAscent,
                    totalCNSStartOfAscent,
                    currentO2,
                    currentHe,
                    currentGasLabel,
                    currentSP,
                    null
                );
                runStopSequence(trialCtx, firstStopDepth, false);
            }
            const decoPhaseVolumeTime = trialCtx.runtime - decoPhaseRuntimeOrigin;
            calcSurfacePhaseVolumeTime(trialCtx.state, settings);
            scheduleConverged = true;
            for (let i = 0; i < NC; i++) {
                const phaseVolumeTime = decoPhaseVolumeTime + trialCtx.state.surfacePhaseVolumeTime[i];
                if (Math.abs(phaseVolumeTime - state.lastPhaseVolumeTime[i]) > 1.0) {
                    scheduleConverged = false;
                }
                state.lastPhaseVolumeTime[i] = phaseVolumeTime;
                state.surfacePhaseVolumeTime[i] = trialCtx.state.surfacePhaseVolumeTime[i];
            }
            if (scheduleConverged || cvIter === 11) {
                const finalState = cloneVPMState(state);
                restoreTissues(finalState, startOfAscentState.tissues);
                let finalCtx;
                if (continuationLevels.length > 0) {
                    finalCtx = runContinuationSchedule(
                        finalState,
                        depthStartOfAscent,
                        runtimeStartOfAscent,
                        totalOTUStartOfAscent,
                        totalCNSStartOfAscent,
                        levels[levels.length - 1].o2 / 100,
                        levels[levels.length - 1].he / 100,
                        `${levels[levels.length - 1].o2}/${levels[levels.length - 1].he}`,
                        forcedOCMode ? 0 : getEffectiveSetpoint(levels[levels.length - 1], isCCR, settings, levels[levels.length - 1].depth),
                        plan,
                        forcedOCMode
                    ).ctx;
                } else {
                    finalCtx = makeScheduleContext(
                        finalState,
                        depthStartOfAscent,
                        runtimeStartOfAscent,
                        totalOTUStartOfAscent,
                        totalCNSStartOfAscent,
                        currentO2,
                        currentHe,
                        currentGasLabel,
                        currentSP,
                        plan
                    );
                    runStopSequence(finalCtx, firstStopDepth, true);
                }
                runtime = finalCtx.runtime;
                totalOTU = finalCtx.totalOTU;
                totalCNS = finalCtx.totalCNS;
                restoreTissues(state, finalCtx.state.tissues);
                return buildResult(plan, runtime, totalOTU, totalCNS, settings, state, decoZoneStart);
            }
            calcCriticalVolume(state, decoPhaseVolumeTime);
        }
        return buildResult(plan, runtime, totalOTU, totalCNS, settings, state, decoZoneStart);
    }
    function buildResult(plan, runtime, totalOTU, totalCNS, settings, state, decoZoneStart) {
        // Expose end-of-dive bubble state so the app can pass it to a repetitive dive
        const finalBubbleState = state ? {
            adjustedCritRadiiN2:  state.adjustedCritRadiiN2.slice(),
            adjustedCritRadiiHe:  state.adjustedCritRadiiHe.slice(),
            regeneratedRadiiN2:   state.regeneratedRadiiN2.slice(),
            regeneratedRadiiHe:   state.regeneratedRadiiHe.slice()
        } : null;
        const normPlan = plan.map(seg => ({
            ...seg,
            time: seg.time != null ? seg.time : undefined,
            run: seg.run != null ? seg.run : seg.runtime,
        }));
        const botSeg = normPlan.find(s => s.type === 'bottom') || normPlan[0];
        const defaultFO2 = botSeg && botSeg.o2 != null ? (botSeg.o2 > 1 ? botSeg.o2 / 100 : botSeg.o2) : 0.21;
        const defaultFHe = botSeg && botSeg.he != null ? (botSeg.he > 1 ? botSeg.he / 100 : botSeg.he) : 0;
        const exposure = computePlanExposureTotals(
            normPlan, settings, defaultFO2, defaultFHe,
            settings.altSurfaceP || altSurfaceP || 1.01325,
            settings.barPerM || BAR_PER_METRE || 0.1
        );
        return {
            plan: normPlan,
            totalRuntime: Math.ceil(runtime),
            totalOTU: exposure.totalOTU,
            totalCNS: exposure.totalCNS,
            depthUnit: settings.metric ? 'm' : 'ft',
            decoZoneStart: decoZoneStart || 0,
            stops: plan.filter(s => s.type === 'stop'),
            finalTissues: state ? state.tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) : null,
            finalBubbleState,  // Feature B: carries per-compartment bubble state
            error: null
        };
    }
    return {
        calculate,
        load: function load() { return true; },
        createVPMState,
        /** Sync all 16 He compartment half-times from ZHL16C_HE_HT array (Baker / Bühlmann 2003). */
        _syncHeHalfTimes: function(htArray) {
            for (let i = 0; i < 16 && htArray && i < htArray.length; i++) {
                if (ZHL16C_He[i]) {
                    const v = htArray[i];
                    ZHL16C_He[i].ht = (v != null && typeof v === 'object') ? v.ht : v;
                }
            }
        },
        /** Compartment-1-only shortcut — kept for callers that pass a single ht value. */
        _setHeHT1: function(htRow) {
            if (ZHL16C_He[0]) ZHL16C_He[0].ht = (htRow != null && typeof htRow === 'object') ? htRow.ht : htRow;
        },
        MODELS: ['VPMA', 'VPMB', 'VPMBE', 'VPMB_GFS', 'VPMBFBO'],
        MODEL_NAMES: {
            'VPMA': 'VPM-A',
            'VPMB': 'VPM-B',
            'VPMBE': 'VPM-B/E',
            'VPMB_GFS': 'VPM-B/GFS',
            'VPMBFBO': 'VPM-B/FBO'
        }
    };
})();

if (typeof module !== 'undefined') module.exports = VPMEngine;
if (typeof window !== 'undefined') window.VPMEngine = VPMEngine;
