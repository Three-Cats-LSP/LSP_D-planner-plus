"""Add CCR-aware tissue loading to zhl-schedule-core.js."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "zhl-schedule-core.js"
text = path.read_text(encoding="utf-8")

insert_after = "  const decoGases = params.decoGases;\n\n  function getPPO2Limit(fO2) {"
ccr_block = """  const decoGases = params.decoGases;
  const ccrSettings = params.ccr ? normalizeCCRSettings(params.ccr) : null;
  const _zhlOnLoop = !!(params.onLoop && ccrSettings && isRebreatherCircuit(ccrSettings.circuit) && !ccrSettings.bailout);
  const loopMixLabel = params.loopMixLabel || (ccrSettings ? loopMixLabelForCore(bottomMixLabel, ccrSettings) : bottomMixLabel);
  let _diveRuntimeMin = 0;

  function zhlLoadLinear(tissues, from, to, t, fO2, fHe, onLoop, phase) {
    if (onLoop && ccrSettings) {
      const out = loadTissuesWithCCR(tissues, from, to, t, fO2, fHe, { ...ccrSettings, scrRuntimeMin: _diveRuntimeMin, ccrPhase: phase });
      _diveRuntimeMin += t;
      return out;
    }
    return saturateLinear(tissues, from, to, t, Math.max(0, 1 - fO2 - (fHe || 0)), fHe || 0);
  }
  function zhlLoadConst(tissues, depth, t, fO2, fHe, onLoop, phase) {
    if (onLoop && ccrSettings) {
      const out = loadTissuesWithCCR(tissues, depth, depth, t, fO2, fHe, { ...ccrSettings, scrRuntimeMin: _diveRuntimeMin, ccrPhase: phase });
      _diveRuntimeMin += t;
      return out;
    }
    return saturate(tissues, depth, t, Math.max(0, 1 - fO2 - (fHe || 0)), fHe || 0);
  }
  function zhlOnLoopAt() { return !!_zhlOnLoop; }
  function zhlGasAt(depthM) {
    if (_zhlOnLoop) {
      return { fN2: bottomFN2, fHe: bottomFHe, fO2: bottomFO2, label: bottomMixLabel };
    }
    return getActiveGas(depthM, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
  }

  function getPPO2Limit(fO2) {"""

if insert_after not in text:
    raise SystemExit("insert anchor not found")
text = text.replace(insert_after, ccr_block, 1)

replacements = [
    (
        "    tissues = saturateLinear(tissues, 0, travelSwitchM, travelDescentTime, travelInfo.fN2);",
        "    tissues = zhlLoadLinear(tissues, 0, travelSwitchM, travelDescentTime, 1 - travelInfo.fN2, 0, _zhlOnLoop, 'descent');",
    ),
    (
        "    tissues = saturateLinear(tissues, travelSwitchM, depthM, bottomDescentTime, bottomFN2, bottomFHe);",
        "    tissues = zhlLoadLinear(tissues, travelSwitchM, depthM, bottomDescentTime, bottomFO2, bottomFHe, _zhlOnLoop, 'descent');",
    ),
    (
        "    tissues = saturateLinear(tissues, 0, depthM, descentTime, bottomFN2, bottomFHe);",
        "    tissues = zhlLoadLinear(tissues, 0, depthM, descentTime, bottomFO2, bottomFHe, _zhlOnLoop, 'descent');",
    ),
    (
        "  tissues = saturate(tissues, depthM, btAtDepth, bottomFN2, bottomFHe);",
        "  tissues = zhlLoadConst(tissues, depthM, btAtDepth, bottomFO2, bottomFHe, _zhlOnLoop, 'bottom');",
    ),
    (
        "      const gas2 = getActiveGas(simCur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);",
        "      const gas2 = zhlGasAt(simCur);",
    ),
    (
        """    if (cur > stopDepth) {
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
      });""",
        """    if (cur > stopDepth) {
      const travelGas = zhlGasAt(cur);
      const travelRate = decoZoneEntered ? decoRate : rate;
      const travelDur = (cur - stopDepth) / travelRate;
      const travelOnLoop = zhlOnLoopAt();
      if (decoZoneEntered && mdCompatMode) {
        // MultiDeco-compatible mode: treat deco-zone transit as instant for tissue loading.
        // Transit time is still counted in RT and added to the displayed stop duration below.
        // (Schreiner mode: tissues off-gas normally during transit — more accurate.)
      } else {
        const tFO2 = travelOnLoop ? bottomFO2 : (travelGas.fO2 != null ? travelGas.fO2 : Math.max(0, 1 - travelGas.fN2 - (travelGas.fHe || 0)));
        const tFHe = travelOnLoop ? bottomFHe : (travelGas.fHe || 0);
        tissues = zhlLoadLinear(tissues, cur, stopDepth, travelDur, tFO2, tFHe, travelOnLoop, decoZoneEntered ? 'deco' : 'bottom');
      }
      steps.push({
        type: 'ascent', from: cur, to: stopDepth,
        dur: travelDur, gas: travelOnLoop ? loopMixLabel : travelGas.label,
        pO2: ppO2Check(cur, travelGas.fN2, travelGas.fHe || 0), fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
        decoTransit: decoZoneEntered && mdCompatMode
      });""",
    ),
    (
        """    // Select best gas available at this stop depth
    const stopGas  = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
    const stopFN2  = stopGas.fN2;
    const stopFHe  = stopGas.fHe || 0;
    const gasLabel = stopGas.label;

    // Gas switch pause — saturate tissues at this depth during the switch
    if (gasLabel !== prevEngineGas && switchPauseT > 0) {
      tissues = saturate(tissues, cur, switchPauseT, stopFN2, stopFHe);""",
        """    // Select best gas available at this stop depth
    const stopGas  = zhlGasAt(cur);
    const onLoop = zhlOnLoopAt();
    const stopFN2  = onLoop ? bottomFN2 : stopGas.fN2;
    const stopFHe  = onLoop ? bottomFHe : (stopGas.fHe || 0);
    const stopFO2  = onLoop ? bottomFO2 : (stopGas.fO2 != null ? stopGas.fO2 : Math.max(0, 1 - stopFN2 - stopFHe));
    const gasLabel = onLoop ? loopMixLabel : stopGas.label;

    // Gas switch pause — saturate tissues at this depth during the switch
    if (gasLabel !== prevEngineGas && switchPauseT > 0) {
      tissues = zhlLoadConst(tissues, cur, switchPauseT, stopFO2, stopFHe, onLoop, 'deco');""",
    ),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit(f"replacement anchor not found: {old[:60]}...")
    text = text.replace(old, new, 1)

# Replace remaining saturate calls in deco loops with zhlLoadConst
text = text.replace(
    "        tissues = saturate(tissues, cur, holdStep, stopFN2, stopFHe);",
    "        tissues = zhlLoadConst(tissues, cur, holdStep, stopFO2, stopFHe, onLoop, 'deco');",
)
text = text.replace(
    "          tissues = saturate(tissues, cur, extra, stopFN2, stopFHe);",
    "          tissues = zhlLoadConst(tissues, cur, extra, stopFO2, stopFHe, onLoop, 'deco');",
)
text = text.replace(
    "        if (stopT < 1/60) { tissues = saturate(tissues, cur, 1/60 - stopT, stopFN2, stopFHe); rt += 1/60 - stopT; stopT = 1/60; }",
    "        if (stopT < 1/60) { tissues = zhlLoadConst(tissues, cur, 1/60 - stopT, stopFO2, stopFHe, onLoop, 'deco'); rt += 1/60 - stopT; stopT = 1/60; }",
)
text = text.replace(
    "        tissues = saturate(tissues, cur, stopT, stopFN2, stopFHe);",
    "        tissues = zhlLoadConst(tissues, cur, stopT, stopFO2, stopFHe, onLoop, 'deco');",
)
text = text.replace(
    "        tissues = saturate(tissues, cur, minStopT, stopFN2, stopFHe);",
    "        tissues = zhlLoadConst(tissues, cur, minStopT, stopFO2, stopFHe, onLoop, 'deco');",
)
text = text.replace(
    "        tissues = saturate(tissues, cur, stopT, stopFN2, stopFHe);",
    "        tissues = zhlLoadConst(tissues, cur, stopT, stopFO2, stopFHe, onLoop, 'deco');",
)

# Final ascent segments
text = text.replace(
    """  if (_zhlAscentFloor > 0 && cur > _zhlAscentFloor) {
    const travelRate = decoZoneEntered ? decoRate : rate;
    const travelDur = (cur - _zhlAscentFloor) / travelRate;
    const travelGas = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
    tissues = saturateLinear(tissues, cur, _zhlAscentFloor, travelDur, travelGas.fN2, travelGas.fHe || 0);
    steps.push({
      type: 'ascent', from: cur, to: _zhlAscentFloor,
      dur: travelDur, gas: travelGas.label,
      pO2: ppO2Check(cur, travelGas.fN2, travelGas.fHe || 0), fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
    });""",
    """  if (_zhlAscentFloor > 0 && cur > _zhlAscentFloor) {
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
      pO2: ppO2Check(cur, travelGas.fN2, travelGas.fHe || 0), fN2: travelGas.fN2, fHe: travelGas.fHe || 0,
    });""",
)
text = text.replace(
    """  } else if (_zhlAscentFloor === 0 && cur > 0) {
    const finalAscentDur = cur / surfaceRate;
    const finalGas = getActiveGas(cur, bottomFN2, decoGases, getPPO2Limit, bottomMixLabel);
    tissues = saturateLinear(tissues, cur, 0, finalAscentDur, finalGas.fN2, finalGas.fHe || 0);
    steps.push({
      type: 'ascent', from: cur, to: 0,
      dur: finalAscentDur, gas: finalGas.label,
      pO2: ppO2Check(cur, finalGas.fN2, finalGas.fHe || 0), fN2: finalGas.fN2, fHe: finalGas.fHe || 0,
    });""",
    """  } else if (_zhlAscentFloor === 0 && cur > 0) {
    const finalAscentDur = cur / surfaceRate;
    const finalGas = zhlGasAt(cur);
    const finalOnLoop = zhlOnLoopAt();
    const fFO2 = finalOnLoop ? bottomFO2 : (finalGas.fO2 != null ? finalGas.fO2 : Math.max(0, 1 - finalGas.fN2 - (finalGas.fHe || 0)));
    const fFHe = finalOnLoop ? bottomFHe : (finalGas.fHe || 0);
    tissues = zhlLoadLinear(tissues, cur, 0, finalAscentDur, fFO2, fFHe, finalOnLoop, 'deco');
    steps.push({
      type: 'ascent', from: cur, to: 0,
      dur: finalAscentDur, gas: finalOnLoop ? loopMixLabel : finalGas.label,
      pO2: ppO2Check(cur, finalGas.fN2, finalGas.fHe || 0), fN2: finalGas.fN2, fHe: finalGas.fHe || 0,
    });""",
)
text = text.replace(
    """    tissues = saturate(tissues, cur, cont.time, cN2, cHe);""",
    """    tissues = zhlLoadConst(tissues, cur, cont.time, cO2, cHe, _zhlOnLoop, 'bottom');""",
)

path.write_text(text, encoding="utf-8")
print("patched zhl-schedule-core.js for CCR")
