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

if (typeof window !== 'undefined') window.runZhlScheduleCore = runZhlScheduleCore;
