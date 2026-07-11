#!/usr/bin/env python3
"""V4 full-audit behavioral regressions: messenger Run/Mix + SI imperial depth."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_DEV = ROOT / "dev"
if str(_DEV) not in sys.path:
    sys.path.insert(0, str(_DEV))

from playwright.sync_api import sync_playwright  # noqa: E402
from playwright_boot import boot_app_page  # noqa: E402
from test_http import serve_www  # noqa: E402
from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402

PROBE_JS = r"""
async () => {
  const wait = (ms) => new Promise(r => setTimeout(r, ms));
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = String(value);
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const waitRows = async (sel, min = 5, tries = 80) => {
    for (let i = 0; i < tries; i++) {
      if (document.querySelectorAll(sel).length >= min) return true;
      await wait(250);
    }
    return document.querySelectorAll(sel).length >= min;
  };

  window._zhlHeadless = false;
  if (typeof setUnits === 'function') setUnits('metric');
  if (typeof setMainNav === 'function') setMainNav('buh');
  if (typeof setPlannerAlgo === 'function') setPlannerAlgo('ZHLC_GF');
  else {
    const algo = document.getElementById('algorithmSelect');
    if (algo) {
      algo.value = 'ZHLC_GF';
      algo.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
  setVal('tecDepth', '45');
  setVal('tecBT', '25');
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  setVal('dg1Mix', 'ean50');
  if (typeof toggleDecoCustomO2 === 'function') toggleDecoCustomO2('dg1Mix', 'dg1CustomField');
  document.getElementById('tecGenerateBtn')?.click();
  if (typeof runDecoSchedule === 'function') runDecoSchedule();
  await waitRows('#decoTableBody tr[data-phase]', 5);

  const sample = [...document.querySelectorAll('#decoTableBody tr[data-phase]')]
    .filter(tr => ['deco', 'bottom', 'switch', 'safety'].includes(tr.dataset.phase))
    .map(tr => {
      const get = (lab) => (tr.querySelector(`td[data-label="${lab}"]`)?.textContent || '').trim();
      return { phase: tr.dataset.phase, depth: get('Depth'), stop: get('Stop'), run: get('Run'), mix: get('Mix') };
    });

  const messenger = typeof buildMessengerText === 'function' ? (buildMessengerText('deco') || '') : '';
  const exportTxt = typeof buildExportText === 'function' ? (buildExportText('deco') || '') : '';
  const stpLines = messenger.split('\n').filter(l => /^Stp\s+/.test(l) && !/^Stp\s+Rounding/.test(l));
  const lvlLines = messenger.split('\n').filter(l => /^Lvl\s+/.test(l));
  const swLines = messenger.split('\n').filter(l => /^>>\s+/.test(l));

  const firstDeco = sample.find(s => s.phase === 'deco' || s.phase === 'safety');
  let messengerStopOk = !firstDeco;
  if (firstDeco && stpLines.length) {
    const parts = stpLines[0].trim().split(/\s+/);
    const mixTok = parts[parts.length - 1];
    const runTok = parts[parts.length - 2];
    const shortMix = (typeof shortMixLabel === 'function')
      ? shortMixLabel(firstDeco.mix)
      : ((typeof exportShortMix === 'function') ? exportShortMix(firstDeco.mix) : firstDeco.mix);
    messengerStopOk = mixTok === shortMix
      || mixTok.replace(/%/g, '') === String(shortMix).replace(/%/g, '')
      || (firstDeco.mix && mixTok && firstDeco.mix.includes(mixTok.replace('%', '')));
    messengerStopOk = messengerStopOk && runTok !== mixTok && /[\d']/.test(runTok);
  }

  const firstBottom = sample.find(s => s.phase === 'bottom');
  let messengerBottomOk = !firstBottom;
  if (firstBottom && lvlLines.length) {
    const parts = lvlLines[0].trim().split(/\s+/);
    const mixTok = parts[parts.length - 1];
    messengerBottomOk = /Air|100%|\d+\/\d+/i.test(mixTok);
  }

  const firstSwitch = sample.find(s => s.phase === 'switch');
  let messengerSwitchOk = true;
  let exportSwitchOk = true;
  if (firstSwitch) {
    messengerSwitchOk = swLines.some(l => /^>>\s+\S+/.test(l) && !/^>>\s+@/.test(l));
    exportSwitchOk = />>\s+\S+\s+@/.test(exportTxt);
  }

  // Contingency / emergency messenger Run↔Mix
  let contingencyOk = true;
  let contMessenger = '';
  if (typeof switchResultTab === 'function') {
    switchResultTab('contingency', document.querySelector('#tecResultTabs [data-tab="contingency"]'));
  }
  if (typeof buildContingencyButtons === 'function') buildContingencyButtons();
  await wait(200);
  const lossBtn = [...document.querySelectorAll('#gasLossButtons .cont-gas-btn')]
    .find(btn => btn.id !== 'contGas-none' && btn.id !== 'contGas-both');
  if (lossBtn) lossBtn.click();
  await wait(100);
  if (typeof calcContingency === 'function') calcContingency();
  await waitRows('#contingencyTableBody tr[data-phase], #contingencyResult tr[data-phase]', 3, 60);
  contMessenger = typeof buildMessengerText === 'function' ? (buildMessengerText('contingency') || '') : '';
  const contStp = contMessenger.split('\n').filter(l => /^Stp\s+/.test(l) && !/^Stp\s+Rounding/.test(l));
  if (contStp.length) {
    const parts = contStp[0].trim().split(/\s+/);
    const mixTok = parts[parts.length - 1];
    const runTok = parts[parts.length - 2];
    contingencyOk = runTok !== mixTok && /[\d']/.test(runTok) && /Air|100%|\d+\/\d+|EAN|\d+%/i.test(mixTok);
  } else {
    contingencyOk = contMessenger.length > 20;
  }

  // VPM PDF/text totals fallback: dash runTime + _lastVPMExport fills values
  let vpmFallbackOk = typeof applyVpmPlanSummaryFallback === 'function';
  if (vpmFallbackOk) {
    const prevAlgo = document.getElementById('algorithmSelect')?.value;
    const prevExport = window._lastVPMExport;
    try {
      setVal('algorithmSelect', 'VPMB');
      window._lastVPMExport = { rt: 77.5, deco: 12.25, tts: "65'15\"", cns: '18%', otu: '40', prt: '1.2' };
      const filled = applyVpmPlanSummaryFallback({
        runTime: '-', decoTime: '-', tts: '-', cns: '-', otu: '-', prt: '-',
        decozone: '-', decoStop: '-', surfGF: '-',
      }, 25);
      vpmFallbackOk = filled.runTime !== '-' && filled.decoTime !== '-'
        && /77'/.test(String(filled.runTime))
        && /12'/.test(String(filled.decoTime));
    } finally {
      if (prevAlgo != null) setVal('algorithmSelect', prevAlgo);
      window._lastVPMExport = prevExport;
    }
  }

  // REC blocked UX (metric): PADI NDL exceed + Bühlmann beyond-MOD → rec-block-card
  let recPadiBlockOk = false;
  let recBuhBlockOk = false;
  try {
    if (typeof setUnits === 'function') setUnits('metric');
    if (typeof setMainNav === 'function') setMainNav('rec');
    if (typeof setPlannerAlgo === 'function') setPlannerAlgo('rec');
    await wait(200);
    setVal('recDepth', '40');
    setVal('recBT', '40'); // PADI NDL @40m is 8 min
    if (typeof runRecPlan === 'function') runRecPlan();
    else if (typeof runPlanner === 'function') runPlanner();
    await wait(800);
    recPadiBlockOk = !!document.querySelector('.rec-block-card')
      && /NDL EXCEEDED|BEYOND/i.test(document.getElementById('plannerResult')?.innerText || '');

    algo = 'buh';
    setVal('ppo2Bottom', '1.2');
    setVal('gasMix', 'ean36');
    if (typeof toggleCustomO2 === 'function') toggleCustomO2();
    setVal('recDepth', '40');
    setVal('recBT', '15');
    if (typeof runRecPlan === 'function') runRecPlan();
    else if (typeof runPlanner === 'function') runPlanner();
    await wait(1000);
    recBuhBlockOk = !!document.querySelector('.rec-block-card')
      && /BEYOND MOD|NDL EXCEEDED/i.test(document.getElementById('plannerResult')?.innerText || '');
    setVal('gasMix', 'air');
    setVal('ppo2Bottom', '1.4');
  } catch (_) {
    recPadiBlockOk = false;
    recBuhBlockOk = false;
  }

  // SI imperial depth stamp (after REC probes so metric depth inputs stay valid)
  let host = document.getElementById('mainSurfIntContainer');
  if (!host) {
    host = document.createElement('div');
    host.id = 'mainSurfIntContainer';
    document.body.appendChild(host);
  }
  if (typeof renderSurfIntPanel === 'function') renderSurfIntPanel('mainSurfIntContainer', 'mainSi', 40, 25);
  if (typeof setUnits === 'function') setUnits('imperial');
  if (typeof toggleSurfIntPanel === 'function') toggleSurfIntPanel('mainSi');
  const d1 = document.getElementById('mainSiD1Depth');
  const d1Disp = document.getElementById('mainSiD1DepthDisplay')?.textContent || '';
  const d1M = d1 ? parseFloat(d1.dataset.depthM) : NaN;
  const siDepthOk = d1?.dataset?.siMetric === '1' && Math.abs(d1M - 40) < 0.1 && /13[01]\s*ft/i.test(d1Disp);

  return {
    sampleCount: sample.length,
    messengerStopOk,
    messengerBottomOk,
    messengerSwitchOk,
    exportSwitchOk,
    contingencyOk,
    siDepthOk,
    vpmFallbackOk,
    hasGasAdequacy: typeof gasPlanAdequacyStatus === 'function',
    recPadiBlockOk,
    recBuhBlockOk,
    d1M,
    d1Disp,
    stpSample: stpLines.slice(0, 2),
    lvlSample: lvlLines.slice(0, 1),
    swSample: swLines.slice(0, 2),
    contSample: contStp.slice(0, 2),
    switchPhasePresent: !!firstSwitch,
  };
}
"""


def main() -> int:
    cases = []
    with serve_www(ROOT) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_default_timeout(120000)
            try:
                boot_app_page(page, base_url)
                result = page.evaluate(PROBE_JS)
            finally:
                browser.close()

    print(json.dumps(result, indent=2))

    mapping = [
        ("V4-FULL-R20-MESSENGER-STOP", result.get("messengerStopOk")),
        ("V4-FULL-R20-MESSENGER-BOTTOM", result.get("messengerBottomOk")),
        ("V4-FULL-R20-MESSENGER-SWITCH", result.get("messengerSwitchOk")),
        ("V4-FULL-R20-EXPORT-SWITCH", result.get("exportSwitchOk")),
        ("V4-FULL-R20-CONTINGENCY", result.get("contingencyOk")),
        ("V4-FULL-R15-SI-IMPERIAL", result.get("siDepthOk")),
        ("V4-FULL-R20-VPM-FALLBACK", result.get("vpmFallbackOk")),
        ("V4-FULL-R20-GAS-ADEQUACY", result.get("hasGasAdequacy")),
        ("V4-FULL-R35-REC-PADI-BLOCK", result.get("recPadiBlockOk")),
        ("V4-FULL-R35-REC-BUH-BLOCK", result.get("recBuhBlockOk")),
        ("V4-FULL-SAMPLE-ROWS", (result.get("sampleCount") or 0) >= 2),
    ]
    failed = False
    for case_id, ok in mapping:
        ok_b = bool(ok)
        cases.append(case_row(case_id, ok_b))
        if not ok_b:
            failed = True
            print("FAIL", case_id)
    code = 1 if failed else 0
    finish_suite(ROOT, cases, code)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
