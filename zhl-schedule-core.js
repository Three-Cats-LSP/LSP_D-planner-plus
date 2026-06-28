/**
 * ZHL Bühlmann schedule core (Tier 2) — BUILD SOURCE ONLY.
 * Not loaded by index.html or zhl-schedule-worker.js at runtime.
 * Rebuilt into zhl-engine-bundle.js via tools/build_zhl_bundle.py.
 * Requires Bühlmann helpers that the bundle preamble provides.
 */
function runZhlScheduleCore(params) {
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
    return getActiveGas(depthM, bottomFN2, bottomFHe, decoGases, getPPO2Limit, bottomMixLabel);
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

  // gfAt must live outside the phase loop — block-scoped function declarations are
  // not visible after the loop in strict mode (Tier 3 bundle uses 'use strict').
  function gfAt(depthM) {
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
        {
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitDur + stopT) / minStopT) * minStopT);
          roundedStop = totalAtLevel - transitDur;
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
      while (ceiling(tissues, gfForClear) > ceilTarget && stopT < 360) {
        tissues = zhlLoadConst(tissues, cur, minStopT, stopFO2, stopFHe, onLoop, 'deco');
        stopT += minStopT; rt += minStopT;
      }
      if (!isFirstDecoStop) {
        // Round up and enforce minimum — only for non-first stops
        const totalAtLevel = Math.max(minStopT, Math.ceil((transitDur + stopT) / minStopT) * minStopT);
        const roundedStop = totalAtLevel - transitDur;
        if (roundedStop > stopT) {
          const extra = roundedStop - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          rt += extra; stopT = roundedStop;
        }
        if (stopT < minStopT) {
          const extra = minStopT - stopT;
          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');
          rt += extra; stopT = minStopT;
        }
      }
      if (stopT > 0) {
        const minStopDisplay = (mdCompatMode && !isFirstDecoStop) ? stopT + transitDur : stopT;
        steps.push({ type: 'deco', depth: cur, dur: minStopDisplay, gas: gasLabel, pO2: zhlStepPpo2(cur, stopFN2, stopFHe, 'deco'), fN2: stopFN2, fHe: stopFHe, _tissues: tissues.map(t => ({ pN2: t.pN2, pHe: t.pHe })) });
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
        {
          const totalAtLevel = Math.max(minStopT, Math.ceil((transitToLastStop + stopT) / minStopT) * minStopT);
          roundedLastStop = totalAtLevel - transitToLastStop;
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
    steps: collapsed,
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

if (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;
