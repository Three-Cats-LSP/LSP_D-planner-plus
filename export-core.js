/**
 * Unified export / clipboard / PDF — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, mGF, altitudeM, altAcclimatized, window._lastPlan, window._lastContingency,
 *   window._lastGasPlan, getExportCircuitTag, getContingencySummaryExport, validateDomDecoGases,
 *   waterDensityDisplayLabel, ensurePDFFontsForPDF, cleanPDF, drawDecoPlanBannerPDF, and DOM ids
 * Globals written: (toast DOM only)
 */

// ═══════════════════════════════════════════════
// COPY DIVE PROFILE TO CLIPBOARD
// ═══════════════════════════════════════════════

// ═══════════════════════════════════════════════════════
//  UNIFIED EXPORT SYSTEM — v5.7.0
//  buildExportText(mode) → clean plain text, messenger-friendly
//  copyDiveProfile(mode) → clipboard
//  exportTXT(mode)       → .txt file download
// ═══════════════════════════════════════════════════════

function buildExportText(mode) {
  const now     = new Date();
  const dateStr = now.toLocaleDateString('en-GB', { day:'2-digit', month:'short', year:'numeric' });
  const timeStr = now.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' });
  // Short timestamp for headers: YYYY/DD/MM HH:MM
  const _dd  = String(now.getDate()).padStart(2,'0');
  const _mm  = String(now.getMonth()+1).padStart(2,'0');
  const _yy  = now.getFullYear();
  const _hh  = String(now.getHours()).padStart(2,'0');
  const _min = String(now.getMinutes()).padStart(2,'0');
  const stamp = `${_yy}/${_mm}/${_dd} ${_hh}:${_min}`;
  const density = waterDensityDisplayLabel();
  const depthUnit = units === 'imperial' ? 'ft' : 'm';  // use live global
  const du = depthUnit; // shorthand - used without space: `${val}${du}`

  // ── altitude + acclimatize helper ──
  const altM      = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const altAccl   = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const altLabel  = altM === 0 ? 'Sea level (0 m)' : `${altM} m`;
  const acclLabel = altAccl ? 'Yes' : 'No';

  // ── helper: clean DOM text (strip emoji, fix subscripts) ──
  const clean = t => t
    .replace(/[🔵🔴🟢🔴⇄↓↑⚠️🤿✓⚡🚨⏱ℹ]/g, '')
    .replace(/\s*·\s*/g, ' - ')
    .replace(/ppO₂/g, 'ppO2').replace(/O₂/g, 'O2')
    .replace(/[—–]/g, '-')
    .replace(/[≈~]/g, '~')
    .replace(/[≥]/g, '>=').replace(/[≤]/g, '<=')
    .replace(/Bühlmann/g, 'Buhlmann')
    .replace(/(\d)\s+(m|ft)\b/g, '$1$2')
    .replace(/\s*→\s*/g, '>')
    .replace(/\s+/g, ' ').trim();

  // ── helper: horizontal rules ──
  const hr    = '='.repeat(40);          // planner/generic section divider
  const decoHr = '='.repeat(22);         // matches "DECOMPRESSION SCHEDULE" width

  let lines = [];

  // ────────────────────────────────────────
  if (mode === 'planner') {
    const depth   = document.getElementById('depth')?.value  || '-';
    const bt      = document.getElementById('bt')?.value     || '-';
    const algo    = document.body.classList.contains('algo-buh') ? 'Bühlmann ZH-L16C' : 'PADI Rec Tables';
    const isRec   = !document.body.classList.contains('algo-buh');
    const gfStr   = !isRec ? `GF ${mGF?.low ?? '-'}/${mGF?.high ?? '-'}` : '';
    const gasEl   = document.getElementById('gasMix');
    const gasStr  = gasEl?.options[gasEl?.selectedIndex]?.text || '';
    const o2pct   = document.getElementById('customO2')?.value;

    lines.push('DECO PLAN (OC)');
    lines.push(stamp);
    lines.push(hr);
    lines.push(`Algorithm : ${algo}${gfStr ? '  ' + gfStr : ''}`);
    lines.push(`Depth     : ${depth}${du}`);
    lines.push(`Bottom T. : ${bt} min`);
    if (gasStr)  lines.push(`Gas       : ${gasStr}`);
    lines.push(`Water     : ${density}`);
    lines.push(`Altitude  : ${altLabel}  Acclimatized: ${acclLabel}`);
    lines.push('');

    // Pull results from rendered stats
    const statsEl = document.getElementById('plannerResult');
    if (statsEl) {
      const stats = statsEl.querySelectorAll('.stat');
      if (stats.length) {
        lines.push('RESULTS');
        lines.push(hr);
        stats.forEach(s => {
          const val = clean(s.querySelector('.stat-val')?.textContent || '');
          const lbl = clean(s.querySelector('.stat-lbl')?.textContent || '');
          if (val && lbl) lines.push(`${lbl.padEnd(20)}: ${val}`);
        });
        lines.push('');
      }
      // Alerts
      const alerts = statsEl.querySelectorAll('.alert');
      if (alerts.length) {
        lines.push('!! STATUS');
        lines.push(hr);
        alerts.forEach(a => lines.push('- ' + clean(a.textContent)));
        lines.push('');
      }
    }

  // ────────────────────────────────────────
  } else if (mode === 'deco') {
    const depth = document.getElementById('decoDepth')?.value || '-';
    const bt    = document.getElementById('decoBT')?.value    || '-';

    // ── helper: shorten mix names for table (trimix-aware) ──
    const shortMix = m => {
      const s = (m||'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy '100% O2' fallback
      const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
      const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
      return s;
    };

    // Read Deco Time and Run Time — always from table totals footer row (exists for both Bühlmann and VPM)
    const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
    const isVPMExport  = decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS';

    const totalsRowEl = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
    let planSum = getPlanSummaryExport(totalsRowEl);

    // Fallback for VPM if totals row not yet rendered: use _lastVPMExport
    if (isVPMExport && planSum.runTime === '-' && window._lastVPMExport) {
      const vx = window._lastVPMExport;
      const toMMSS = (n) => { const m = Math.floor(n), s = Math.round((n - m) * 60); return `${m}'${String(s).padStart(2,'0')}"`; };
      planSum.runTime  = toMMSS(vx.rt);
      planSum.decoTime = toMMSS(vx.deco);
      planSum.tts      = vx.tts || toMMSS(Math.max(0, vx.rt - parseFloat(bt)));
      planSum.cns      = vx.cns;
      planSum.otu      = vx.otu;
      planSum.prt      = vx.prt;
      planSum.decozone = vx.decozone || planSum.decozone;
      planSum.decoStop = vx.decoStop || planSum.decoStop;
    }

    // PrT fallback if not in totals row
    if (planSum.prt === '-') {
      const prtN = calcPrTBarMin(domDepthToM('decoDepth'), bt);
      if (!isNaN(prtN)) planSum.prt = prtN.toFixed(1);
    }

    lines.push(...buildDecoPlanHeaderLines());
    lines.push(...formatPlanSummaryBlock(planSum));
    lines.push('');

    // Ascent schedule table
    const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
    if (rows.length) {
      const shr = '-'.repeat(56);
      lines.push('ASCENT SCHEDULE');
      lines.push(shr);
      lines.push('Phase Depth  Stop   Mix   Run   TTS   PPO2  EAD');
      lines.push(shr);
      const phaseLabel = { descent:'Des', bottom:'Lvl', ascent:'Asc', deco:'Stp', safety:'Stp', totals:'TOT' };
      rows.forEach(tr => {
        const ph  = tr.dataset.phase;
        if (ph === 'totals') return; // handled below
        const tds = tr.querySelectorAll('td');
        if (ph === 'switch') {
          const cSw = Array.from(tds).map(td => clean(td.textContent));
          const mixSw = shortMix(cSw[3] || '');
          const depSw = (cSw[1] || '').trim();
          lines.push(`>> ${mixSw} @ ${depSw}`);
          return;
        }
        const c   = Array.from(tds).map(td => clean(td.textContent));
        const lbl = (phaseLabel[ph] || ph).padEnd(5);

        // Depth: descent may use 0→dest; ascent rows are destination-only
        let depRaw = c[1] || '';
        if (ph === 'descent') {
          const arrowMatch = depRaw.match(/[→>](.+)$/);
          if (arrowMatch) depRaw = arrowMatch[1].trim();
        }
        const dep  = (depRaw.length <= 2 ? depRaw.padStart(3) : depRaw).padEnd(6);
        const stpRaw = c[2] || '';
        const stpVal = /^\d+:\d+$/.test(stpRaw) ? stpRaw : '';
        const stp  = (stpVal.length > 0 && stpVal.length <= 4 ? stpVal.padStart(5) : stpVal).padEnd(7);
        const mix  = shortMix(c[3] || '').padEnd(5);
        const runRaw = c[4] || '';
        const run  = (runRaw.length <= 4 ? runRaw.padStart(5) : runRaw).padEnd(6);
        const ttsRaw = (c[5] || '').trim() || '-';
        const tts  = (ttsRaw.length <= 4 ? ttsRaw.padStart(5) : ttsRaw).padEnd(6);
        const ppo2  = (c[6] || '').padStart(4).padEnd(5);
        const eadVal = (c[7] || '-').trim() || '-';
        const ead  = (eadVal === '-' ? eadVal.padStart(2) : eadVal.padStart(3)).padEnd(6);
        lines.push(`${lbl} ${dep}${stp}${mix}${run}${tts} ${ppo2}${ead}`);
      });

      // Totals row — use values already read from table footer (runTimeVal etc.)
      lines.push(shr);
      lines.push(...formatPlanSummaryBlock(planSum, true));
      lines.push('');
    }

    // ── Gas Consumption ──
    const _gcEl = document.getElementById('gasConsumptionSummary');
    if (_gcEl && _gcEl.style.display !== 'none') {
      calcGasPlan();
      const _gp = window._lastGasPlan;
      if (_gp && _gp.rows && _gp.rows.length) {
        const volU2  = units === 'imperial' ? 'cu ft' : 'L';
        const presU2 = units === 'imperial' ? 'psi'   : 'bar';
        const sacBot2 = document.getElementById('sacBottom')?.value || '20';
        const sacDec2 = document.getElementById('sacDeco')?.value   || '15';
        const ruleName2 = _gp.rule === 'half' ? 'Half Tank' : 'Thirds';
        lines.push('GAS CONSUMPTION');
        lines.push(`Rule: ${ruleName2}  SAC: bottom ${sacBot2} L/min, deco ${sacDec2} L/min`);
        lines.push('-'.repeat(48));
        _gp.rows.forEach(r => {
          if (r.kind === 'bottom') {
            const ruleTxt = _gp.rule === 'half' ? '1/2' : '1/3';
            const lbl = r.label.includes('(+Travel)') ? r.label.replace('(+Travel)', '+ Travel') : r.label;
            lines.push(`  ${lbl.toUpperCase().padEnd(14)} ${gpVolDisp(r.totalL)} ${volU2} avail   reserve: ${gpPresDisp(r.reserveBar)} ${presU2}`);
            if (r.shortL != null && r.shortL > 0) {
              lines.push(`    STATUS : INSUFFICIENT — need ${gpVolDisp(r.reqL)} ${volU2}, have ${gpVolDisp(r.totalL)} ${volU2} (short ${gpVolDisp(r.shortL)} ${volU2})`);
              if (r.maxBTmin != null) {
                lines.push(`    FIX    : Shorten BT to ${r.maxBTmin} min, turn at ${gpPresDisp(r.maxTurnBar)} ${presU2}`);
                lines.push(`           : Or use a larger cylinder / add a stage`);
              }
            } else {
              lines.push(`    TURN   : ${gpPresDisp(r.turnBar)} ${presU2}  (${ruleTxt} of ${gpVolDisp(r.portionL)} ${volU2})`);
              if (r.reqL != null) lines.push(`    PLAN   : needs ${gpVolDisp(r.reqL)} ${volU2}  ✓ OK`);
            }
          } else {
            lines.push(`  ${r.label.toUpperCase().padEnd(14)} ${gpVolDisp(r.totalL)} ${volU2} avail   reserve: ${gpPresDisp(r.reserveBar)} ${presU2}`);
            if (r.reqL == null) {
              lines.push(`    STATUS : run deco plan first`);
            } else {
              const margin2 = r.totalL - r.reqL;
              const status2 = r.totalL >= r.reqL * 1.10 ? 'OK' : r.totalL >= r.reqL ? 'TIGHT' : 'INSUFFICIENT';
              lines.push(`    NEED   : ${gpVolDisp(r.reqL)} ${volU2}   MARGIN: ${gpVolDisp(margin2)} ${volU2}   STATUS: ${status2}`);
              if (status2 === 'INSUFFICIENT') lines.push(`    FIX    : Add more gas or reduce deco obligation`);
            }
          }
        });
        lines.push('-'.repeat(48));
        lines.push('');
      }
    }

    lines.push('!! SAFETY REMINDERS');
    lines.push('- Do NOT skip mandatory deco stops');
    lines.push('- Check ppO2 before each gas switch');
    lines.push('- Plan conservatively - never dive tables exactly');
    lines.push('- Carry 3+ min of reserve gas');
    lines.push('- Use your dive computer for backup');
    // CNS toxicity warning
    const cnsNumExport = parseFloat((planSum.cns || '0').replace('%', ''));
    if (!isNaN(cnsNumExport) && cnsNumExport >= 80) {
      lines.push('');
      lines.push('!! CNS OXYGEN TOXICITY WARNING');
      lines.push(`!! CNS% = ${planSum.cns} — exceeds 80% threshold.`);
      if (cnsNumExport >= 100) {
        lines.push('!! DANGER: CNS >= 100% — oxygen convulsion risk. Reduce O2 exposure.');
      } else {
        lines.push('!! Reduce deco gas ppO2, extend switch depths, or shorten bottom time.');
      }
    }
    lines.push('');

  // ────────────────────────────────────────
  } else if (mode === 'contingency') {
    const c = window._lastContingency;
    if (!c) return null;
    const depth = document.getElementById('decoDepth')?.value || '-';
    const bt    = document.getElementById('decoBT')?.value    || '-';
    const shortMix = m => {
      const s = (m||'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy '100% O2' fallback
      const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
      const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
      return s;
    };

    lines.push('EMERGENCY PLAN');
    lines.push(stamp);
    lines.push(hr);
    // Algorithm + settings (reuse same logic as main deco export)
    const eAlgoSel  = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
    const eAlgoNames = { ZHLC_GF: 'Buhlmann ZH-L16C + GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B / GFS' };
    const eAlgoName  = eAlgoNames[eAlgoSel] || eAlgoSel;
    const eGfLow     = mGF?.low  ?? '-';
    const eGfHigh    = mGF?.high ?? '-';
    const eConsVal   = document.getElementById('conservatismSelect')?.value ?? '0';
    const eAlgoSettings = eAlgoSel === 'ZHLC_GF'
      ? `GF ${eGfLow}/${eGfHigh}`
      : eAlgoSel === 'VPMB' ? `Conservatism +${eConsVal}` : `GF Hi ${eGfHigh}  Conservatism +${eConsVal}`;
    const eAscentRate     = document.getElementById('ascentRate')?.value      || '-';
    const eDecoAscentRate = document.getElementById('decoAscentRate')?.value  || '-';
    const eSurfAscentRate = document.getElementById('surfaceAscentRate')?.value || '-';
    const eDescentRate    = document.getElementById('descentRate')?.value || '-';
    const eLastStop       = document.getElementById('lastDecoStop')?.value || '-';
    const eDecoStep       = document.getElementById('decoStep')?.value    || '-';
    const eRnd = (document.getElementById('stopRounding')?.value||'fractional')==='wholeminute'?'Yes':'No';
    const eWV  = parseFloat(document.getElementById('waterVapor')?.value||'0.0627');
    const eWVL = eWV<=0.058?'M':'B';
    // shortMix matching main deco export style (number+%)
    const eShortMix = m => {
      const s = (m||'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy '100% O2' fallback
      const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
      const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
      return s;
    };
    lines.push(`Scenario    : ${c.label}`);
    lines.push(`Algorithm   : ${eAlgoName}  (${eAlgoSettings})`);
    lines.push(`Depth       : ${depth}${du}    BT: ${bt} min`);
    lines.push(`Water       : ${density}`);
    lines.push(`Descent     : ${eDescentRate}${du}/min  Ascent: ${eAscentRate}${du}/min  Deco: ${eDecoAscentRate}${du}/min  Surface: ${eSurfAscentRate}${du}/min`);
    lines.push(`Last Stop   : ${eLastStop}${du}  Step: ${eDecoStep}${du}`);
    lines.push(`Stop Rounding: ${eRnd}  WV: ${eWV}(${eWVL})`);
    lines.push(`Altitude     : ${altLabel}  Acclimatized: ${acclLabel}`);
    const _eMdpEn = document.getElementById('minDecoProfileEnable')?.value === 'yes';
    const _eMdp9m = document.getElementById('minDeco9m')?.value || '1';
    const _eMdp6m = document.getElementById('minDeco6m')?.value || '3';
    const _eDu    = units === 'imperial' ? 'ft' : 'm';
    if (_eMdpEn) lines.push(`Min Deco Profile: ON  (9${_eDu}: ${_eMdp9m} min  6${_eDu}: ${_eMdp6m} min)`);
    const _eHdr = typeof buildDecoPlanHeaderData === 'function' ? buildDecoPlanHeaderData() : null;
    if (_eHdr && _eHdr.circuit && _eHdr.circuit !== 'OC') {
      lines.push(`Circuit     : ${_eHdr.ccrLabel || _eHdr.circuit}${_eHdr.ccrBailout ? ' (bailout)' : ''}`);
    }
    if (c.msg) lines.push(`Note        : ${clean(c.msg)}`);
    lines.push('');

    const rows = document.querySelectorAll('#contingencyResult .deco-table tbody tr');
    if (rows.length) {
      lines.push('EMERGENCY ASCENT SCHEDULE');
      lines.push('-'.repeat(56));
      lines.push('Phase Depth  Stop   Mix   Run   TTS   PPO2  EAD');
      lines.push('-'.repeat(56));
      const phaseLabel = { descent:'Des', bottom:'Lvl', ascent:'Asc', deco:'Stp', safety:'Stp', switch:'>>' };
      rows.forEach(tr => {
        const ph  = tr.dataset.phase;
        if (ph === 'totals' || ph === 'info') return;
        const tds = tr.querySelectorAll('td');
        if (ph === 'switch') {
          const cSw = Array.from(tds).map(td => clean(td.textContent));
          const mixSw = eShortMix(cSw[3] || '');
          const depSw = (cSw[1] || '').trim();
          lines.push(`>> ${mixSw} @ ${depSw}`);
          return;
        }
        const c2   = Array.from(tds).map(td => clean(td.textContent));
        const lbl  = (phaseLabel[ph]||ph).padEnd(5);

        // Ascent rows are destination-only; descent may use 0→dest
        let depRaw = c2[1] || '';
        if (ph === 'descent') {
          const arrowMatch = depRaw.match(/[→>](.+)$/);
          if (arrowMatch) depRaw = arrowMatch[1].trim();
        }
        const dep  = (depRaw.length <= 2 ? depRaw.padStart(3) : depRaw).padEnd(6);
        const stpRaw = c2[2]||'';
        const stpVal = parseStopDisplayTime(stpRaw);
        const stp  = (stpVal.length > 0 && stpVal.length <= 4 ? stpVal.padStart(5) : stpVal).padEnd(7);
        const mix  = eShortMix(c2[3]||'').padEnd(5);
        const runRaw2 = c2[4]||'';
        const run  = (runRaw2.length <= 4 ? runRaw2.padStart(5) : runRaw2).padEnd(6);
        const ttsRaw = (c2[5] || '').trim() || '-';
        const tts  = (ttsRaw.length <= 4 ? ttsRaw.padStart(5) : ttsRaw).padEnd(6);
        const ppo2  = (c2[6]||'').padStart(4).padEnd(5);
        const eadVal = (c2[7]||'-').trim() || '-';
        const ead  = (eadVal === '-' ? eadVal.padStart(2) : eadVal.padStart(3)).padEnd(6);
        lines.push(`${lbl} ${dep}${stp}${mix}${run}${tts} ${ppo2}${ead}`);
      });

      // Totals line
      const emSum = getContingencySummaryExport();
      lines.push('-'.repeat(56));
      lines.push(...formatPlanSummaryBlock(emSum, true));
      lines.push('');
    }
    lines.push('!! SAFETY REMINDERS');
    lines.push('- Do NOT skip mandatory deco stops');
    lines.push('- Check ppO2 before each gas switch');
    lines.push('- Plan conservatively - never dive tables exactly');
    lines.push('- Carry 3+ min of reserve gas');
    lines.push('- Use your dive computer for backup');
    lines.push('');

  // ────────────────────────────────────────
  } else if (mode === 'multi') {
    lines.push('LSP D-PLANNER + CCR - MULTI DIVE DAY PLAN');
    lines.push(hr);
    lines.push(`Water : ${density}`);
    lines.push('');

    // Pull each dive result card
    // Pull each dive card from unifiedDivePlan
    const diveCards = document.querySelectorAll('#unifiedDivePlan [id^="udp-dive-"]');
    let diveNum = 1;
    diveCards.forEach(card => {
      lines.push(`* DIVE ${diveNum}`);
      lines.push('-'.repeat(30));
      const dEl   = card.querySelector('[id^="udp-d"][id$="-disp"]');
      const btEl  = card.querySelector('[id^="udp-bt"][id$="-disp"]');
      const advEl = card.querySelector('[id^="udp-adv"]');
      if (dEl)  lines.push(`  ${'Depth'.padEnd(22)}: ${clean(dEl.textContent)}`);
      if (btEl) lines.push(`  ${'Bottom Time'.padEnd(22)}: ${clean(btEl.textContent)}`);
      if (advEl?.textContent?.trim()) lines.push(`  !! ${clean(advEl.textContent)}`);
      lines.push('');
      diveNum++;
    });

    // Warnings block
    const warns = document.getElementById('multiWarnings');
    if (warns?.textContent?.trim()) {
      lines.push('!! WARNINGS');
      lines.push(hr);
      lines.push(clean(warns.textContent));
      lines.push('');
    }

  // ────────────────────────────────────────
  } else if (mode === 'cns') {
    const depth    = document.getElementById('cnsDepth')?.value || '-';
    const bt       = document.getElementById('cnsBT')?.value    || '-';
    const o2       = document.getElementById('cnsO2')?.value    || '-';
    const dives    = document.getElementById('cnsDives')?.value || '-';
    const ppo2     = document.getElementById('cnsPPO2')?.textContent    || '-';
    const single   = document.getElementById('cnsSinglePct')?.textContent || '-';
    const daily    = document.getElementById('cnsDailyPct')?.textContent  || '-';
    const otu      = document.getElementById('cnsOTU')?.textContent      || '-';
    const statusEl = document.getElementById('cnsStatusText');
    const status   = statusEl ? clean(statusEl.textContent) : '';

    lines.push('LSP D-PLANNER + CCR - CNS O2 TRACKER');
    lines.push(hr);
    lines.push(`Depth         : ${depth}${du}`);
    lines.push(`BT Time      : ${bt} min`);
    lines.push(`Gas O2%       : ${o2}%`);
    lines.push(`Dives today   : ${dives}`);
    lines.push('');
    lines.push('RESULTS');
    lines.push(hr);
    lines.push(`ppO2          : ${ppo2} bar`);
    lines.push(`CNS% single   : ${single}`);
    lines.push(`CNS% daily    : ${daily}`);
    lines.push(`OTU           : ${otu}`);
    if (status) {
      lines.push('');
      lines.push(`Status        : ${status}`);
    }
    lines.push('');
    lines.push('Limits (NOAA): CNS < 80% per dive, < 100% per day');
    lines.push('');
  }

  // ── Footer (all modes) ──
  lines.push(hr);
  lines.push('Planning Aid Only - Not a substitute for training, certification, or a dive computer.');
  lines.push(`Generated by LSP D-PLANNER + CCR  ${dateStr} ${timeStr}`);
  lines.push('https://threecats-lsp.com/d-planner-plus/');
  lines.push('');
  lines.push('*'.repeat(43));
  lines.push('*       WARNING & DISCLAIMER              *');
  lines.push('*'.repeat(43));
  lines.push('This LSP Planner generated dive schedule could indirectly kill you.');
  lines.push('The author does not warrant that it accurately reflects the selected');
  lines.push('decompression model algorithms, that it won\'t get you bent or dead,');
  lines.push('or that it will produce safe, reliable results. This dive schedule is');
  lines.push('experimental and you use it at your own risk. Diving in general is');
  lines.push('fraught with risk, and decompression diving adds significantly more');
  lines.push('risk. Deep diving utilizing multiple gasses, including Helium, is');
  lines.push('about as risky as it gets.');
  lines.push('This schedule is not intended for uneducated users. LSP Planner and');
  lines.push('the decompression schedules it produces are tools for experienced');
  lines.push('mixed-gas decompression divers ONLY. If you have not been properly');
  lines.push('trained in mixed-gas decompression diving by an internationally');
  lines.push('recognized technical certification agency and/or don\'t have a firm');
  lines.push('handle on decompression planning and mixed-gas diving, then');
  lines.push('DO NOT USE THIS DIVE SCHEDULE.');
  lines.push('*'.repeat(43));

  return lines.join('\n');
}

function decoPlanRowsExist() {
  return document.querySelectorAll('#decoTableBody tr[data-phase]').length > 0;
}
function notifyInvalidGasExport(toastId) {
  const gasVal = validateDomDecoGases();
  const msg = gasVal.errors[0]?.message || 'Invalid gas mixture — check bottom and deco gas fields.';
  showToast('Invalid gas: ' + msg, toastId || 'copy', true);
}
function notifyScheduleError(msg) {
  showToast('Cannot generate schedule: ' + msg, 'schedule', true);
}

function exportNeedsDecoBottomGas(mode) {
  return mode === 'deco' || mode === 'contingency'
    || (mode === 'planner' && decoPlanRowsExist());
}

// ── Copy to clipboard - shows preview modal ──
function copyDiveProfile(mode) {
  if (mode === 'deco' && !decoPlanRowsExist()) { showToast('Run a dive plan first', 'copy', true); return; }
  if (mode === 'contingency' && !window._lastContingency) { showToast('Run an emergency plan first', 'copy', true); return; }
  if (exportNeedsDecoBottomGas(mode) && !getBottomGasFractions()) { notifyInvalidGasExport('copy'); return; }
  const text = buildMessengerText(mode);
  if (!text) { showToast('Run a dive plan first', 'copy', true); return; }
  const titles = { deco: 'Deco Plan', contingency: 'Emergency Plan', planner: 'Dive Plan' };
  document.getElementById('copyModalTitle').textContent = titles[mode] || 'Copy Plan';
  document.getElementById('copyModalBody').textContent = text;
  document.getElementById('copyModal').style.display = 'flex';
}
function closeCopyModal() {
  document.getElementById('copyModal').style.display = 'none';
}
function copyCopyModal() {
  const text = document.getElementById('copyModalBody').textContent || '';
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard', 'copy')).catch(() => copyFallback(text));
  } else {
    copyFallback(text);
  }
}

// ── Deco Slate: compact waterproof-slate format (deco stops only) ──
function buildSlateText() {
  const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
  if (!rows.length) return null;
  const du = units === 'metric' ? 'm' : 'ft';
  const clean = t => (t || '').replace(/[📋⚠️🤿✓⚡🔵🔴🟢🚨⏱ℹ⇄↓↑]/g,'').replace(/\s*·\s*/g,' ').replace(/ppO₂/g,'ppO2').replace(/O₂/g,'O2').replace(/[—–]/g,'-').replace(/Bühlmann/g,'Buhlmann').replace(/\s+/g,' ').trim();
  const shortMix = m => {
    const s = clean(m);
    if (!s) return '-';
    if (/^\d+\/\d+$/.test(s)) return s;
    if (s === '100%' || /^100/i.test(s)) return '100%';
    if (/^air$/i.test(s)) return 'Air';
    const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
    const pct = s.match(/(\d+)\s*%/); if (pct) return pct[1] + '/00';
    return s;
  };

  // Header bits
  const _sNow = new Date();
  const _sD = String(_sNow.getDate()).padStart(2,'0'), _sMo = String(_sNow.getMonth()+1).padStart(2,'0');
  const _sH = String(_sNow.getHours()).padStart(2,'0'), _sMi = String(_sNow.getMinutes()).padStart(2,'0');
  const dateStr = _sNow.toISOString().slice(0, 10);
  const stamp = `${_sNow.getFullYear()}/${_sMo}/${_sD} ${_sH}:${_sMi}`;
  const algoSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const algoNames = { ZHLC_GF: 'Buhlmann GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B/GFS' };
  const algoName = algoNames[algoSel] || algoSel;
  const algoLine = algoSel === 'ZHLC_GF'
    ? `${algoName} ${(mGF && mGF.low != null) ? mGF.low : '-'}/${(mGF && mGF.high != null) ? mGF.high : '-'}`
    : algoSel === 'VPMB'
      ? `${algoName} +${document.getElementById('conservatismSelect')?.value ?? '0'}`
      : `${algoName} GF Hi ${mGF.high}`;

  const botFracs = getBottomGasFractions();
  if (!botFracs) return null;
  const botLabel = shortMix(getGasLabel(botFracs.fO2, botFracs.fHe));

  // Switch gases with depths from rendered switch rows
  const gswRows = Array.from(document.querySelectorAll('#decoTableBody tr[data-phase="switch"]'));
  const switchParts = gswRows.map(tr => {
    const dep = clean(tr.querySelector('td[data-label="Depth"]')?.textContent || '');
    const gas = shortMix(tr.querySelector('td[data-label="Mix"]')?.textContent || '');
    return gas && dep ? `${gas} @ ${dep}` : '';
  }).filter(Boolean);
  const _slTravel = getTravelGasExport();
  const travelPart = _slTravel ? `${_slTravel.gas} (TRV @ ${_slTravel.depth})` : '';
  const mixLine = [botLabel + ' (BTM)', travelPart, ...switchParts].filter(Boolean).join(' | ');

  // Stop rows: only deco + safety stops (skip descent/bottom/ascent/switch/totals)
  const out = [];
  rows.forEach(tr => {
    const ph = tr.dataset.phase;
    if (ph !== 'deco' && ph !== 'safety') return;
    const tds = tr.querySelectorAll('td');
    const depRaw = clean(tds[1]?.textContent).replace(/(m|ft)$/i, '');
    const dep = (depRaw + du).padStart(5);
    const run = clean(tds[4]?.textContent).padStart(5);
    const gas = shortMix(tds[3]?.textContent).padEnd(6);
    const ppo2 = clean(tds[6]?.textContent).padStart(4);
    out.push(`${dep}  ${run}  ${gas} ${ppo2}`);
  });

  // Footer: TRT/TTS/DECO/CNS/OTU/PrT/Decozone/Deco stop — read from totals row
  const _stotRow = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  const _slSum = getPlanSummaryExport(_stotRow);
  const _toMMSS = s => {
    if (!s || s === '-') return '-';
    s = String(s).trim();
    const mm = s.match(/(\d+)'(\d+)"/);
    if (mm) return `${mm[1]}'${mm[2]}"`;
    const colon = s.match(/(\d+):(\d+)/);
    if (colon) return `${colon[1]}'${colon[2]}"`;
    const plain = s.replace(/[^\d]/g,'');
    return plain ? `${plain}'00"` : '-';
  };
  let tbt = _toMMSS(_slSum.runTime);
  let ttsDisp = _slSum.tts;
  let decoDisp = _toMMSS(_slSum.decoTime);
  const _sCNS = _slSum.cns;
  const _sOTU = _slSum.otu;
  const _sPrT = _slSum.prt;
  const _sDz = _slSum.decozone;
  const _sDs = _slSum.decoStop;
  const _sSGF = _slSum.surfGF || '-';
  if (tbt === '-') tbt = `${document.getElementById('decoBT')?.value || '-'}'00"`;

  const bar = '========================';
  const lines = [];
  lines.push('DECO SLATE');
  lines.push(stamp);
  lines.push(bar);
  lines.push(`Algo: ${algoLine}`);
  lines.push(`Mix: ${mixLine}`);
  lines.push('');
  lines.push('DEPTH  TIME   GAS    PPO2');
  if (out.length) {
    out.forEach(l => lines.push(l));
  } else {
    lines.push('  (no decompression stops)');
  }
  lines.push(bar);
  lines.push(`TRT: ${tbt} | TTS: ${ttsDisp} | DECO: ${decoDisp}`);
  lines.push(`CNS: ${_sCNS} OTU: ${_sOTU} PrT: ${_sPrT} Surf GF: ${_sSGF} Decozone: ${_sDz} First deco: ${_sDs}`);
  return lines.join('\n');
}

function showSlate() {
  if (!decoPlanRowsExist()) { showToast('Run a dive plan first', 'slate', true); return; }
  if (!getBottomGasFractions()) { notifyInvalidGasExport('slate'); return; }
  const text = buildSlateText();
  if (!text) { showToast('Run a dive plan first', 'slate', true); return; }
  document.getElementById('slateModalBody').textContent = text;
  document.getElementById('slateModal').style.display = 'flex';
}
function closeSlate() {
  document.getElementById('slateModal').style.display = 'none';
}
function copySlate() {
  const text = document.getElementById('slateModalBody').textContent || '';
  if (!text) return;
  if (navigator.clipboard?.writeText) {
    navigator.clipboard.writeText(text).then(() => showToast('Slate copied', 'slate')).catch(() => copyFallback(text));
  } else {
    copyFallback(text);
  }
}

function buildMessengerText(mode) {
  if (mode === 'contingency') {
    const c = window._lastContingency;
    if (!c) return null;
    const depth = c.scenarioDepth ?? document.getElementById('decoDepth')?.value ?? '-';
    const bt    = c.scenarioBT    ?? document.getElementById('decoBT')?.value    ?? '-';
    const du    = units === 'metric' ? 'm' : 'ft';
    const shortMix = m => {
      const s = (m||'').trim().replace(/[📋⚠️🤿]/g,'').trim();
      if (!s) return '-';
      if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
      if (s === '100%') return '100%';          // pure O2
      if (/^air$/i.test(s)) return 'Air';
      if (/^100/i.test(s)) return '100%';       // legacy fallback
      const ean = s.match(/(\d+)%/); if (ean) return ean[1] + '/00';
      return s;
    };
    const clean = t => t.replace(/[📋⚠️🤿✓⚡🔵🔴🟢🚨⏱ℹ⇄↓↑]/g,'').replace(/\s*·\s*/g,' - ').replace(/ppO₂/g,'ppO2').replace(/O₂/g,'O2').replace(/[—–]/g,'-').replace(/Bühlmann/g,'Buhlmann').replace(/(\d)\s+(m|ft)\b/g,'$1$2').replace(/\s*→\s*/g,'>').replace(/\s+/g,' ').trim();
    const _cn = new Date(); const _cStamp = `${_cn.getFullYear()}/${String(_cn.getMonth()+1).padStart(2,'0')}/${String(_cn.getDate()).padStart(2,'0')} ${String(_cn.getHours()).padStart(2,'0')}:${String(_cn.getMinutes()).padStart(2,'0')}`;
    const result = [];
    result.push('EMERGENCY PLAN');
    result.push(_cStamp);
    result.push('-'.repeat(28));
    result.push(`${depth}${du} / ${bt}min / ${c.label}`);

    const cRnd = (document.getElementById('stopRounding')?.value||'fractional')==='wholeminute'?'Yes':'No';
    const cWV  = parseFloat(document.getElementById('waterVapor')?.value||'0.0627');
    const cWVL = cWV<=0.058?'M':'B';
    result.push(`Stp Rounding: ${cRnd}  WV: ${cWV}(${cWVL})`);
    const _cAltM   = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
    const _cAltLbl = _cAltM === 0 ? 'Sea level' : `${_cAltM}m`;
    const _cAccl   = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : false;
    result.push(`Altitude    : ${_cAltLbl}  Acclimatized: ${_cAccl ? 'Yes' : 'No'}`);
    const _cLastStop = document.getElementById('lastDecoStop')?.value || '-';
    const _cDecoStep = document.getElementById('decoStep')?.value    || '-';
    const _cAscRate  = document.getElementById('ascentRate')?.value      || '-';
    const _cDecRate  = document.getElementById('decoAscentRate')?.value  || '-';
    const _cSurfRate = document.getElementById('surfaceAscentRate')?.value || '-';
    const _cDesRate  = document.getElementById('descentRate')?.value || '-';
    result.push(`Last Stop   : ${_cLastStop}${du}  Step: ${_cDecoStep}${du}`);
    result.push(`Descent     : ${_cDesRate}${du}/min  Ascent: ${_cAscRate}${du}/min`);
    result.push(`Deco        : ${_cDecRate}${du}/min  Surface: ${_cSurfRate}${du}/min`);
    result.push('-'.repeat(28));
    const rows = document.querySelectorAll('#contingencyResult .deco-table tbody tr');
    rows.forEach(tr => {
      const ph = tr.dataset.phase;
      if (!ph || ph === 'totals') return;
      const tds = tr.querySelectorAll('td');
      const cv  = Array.from(tds).map(td => clean(td.textContent));
      if (ph === 'switch') { const switchTxt = Array.from(tds).slice(1).map(t=>clean(t.textContent)).filter(Boolean).join(' '); result.push('>> ' + switchTxt); return; }
      if (ph === 'descent' || ph === 'ascent') return;
      if (ph === 'bottom') { result.push(`Lvl  ${cv[1]}  ${cv[2]}  ${shortMix(cv[3])}`); return; }
      const stop = parseStopDisplayTime(cv[2]);
      result.push(`Stp  ${cv[1]}  ${stop}  ${cv[4]}  ${shortMix(cv[3])}`);
    });
    result.push('-'.repeat(28));
    result.push(...formatPlanSummaryBlock(getContingencySummaryExport(), true));
    return result.join('\n');
  }

  const rows = document.querySelectorAll('#decoTableBody tr[data-phase]');
  if (!rows.length) return buildExportText(mode);

  // One-line context header
  const depth = document.getElementById('decoDepth')?.value || '-';
  const bt    = document.getElementById('decoBT')?.value    || '-';
  const gfL   = mGF.low;
  const gfH   = mGF.high;
  const du    = units === 'metric' ? 'm' : 'ft';
  const unitsPref = units;

  const shortMix = m => {
    const s = (m||'').trim();
    if (!s) return '-';
    if (/^\d+\/\d+$/.test(s)) return s; // O2/He format already
    if (s === '100%') return '100%';          // pure O2
    if (/^air$/i.test(s)) return 'Air';
    if (/^100/i.test(s)) return '100%';       // legacy fallback
    const ean = s.match(/[Ee][Aa][Nn]\s*(\d+)/); if (ean) return ean[1] + '/00';
    const pct = s.match(/(\d+)%/); if (pct) return pct[1] + '/00';
    return s;
  };
  const clean = t => t
    .replace(/[🔵🔴🟢🔴⇄↓↑⚠️🤿✓⚡🚨⏱ℹ]/g, '')
    .replace(/\s*·\s*/g, ' - ')
    .replace(/ppO₂/g, 'ppO2').replace(/O₂/g, 'O2')
    .replace(/[—–]/g, '-')
    .replace(/[≈~]/g, '~')
    .replace(/[≥]/g, '>=').replace(/[≤]/g, '<=')
    .replace(/Bühlmann/g, 'Buhlmann')
    .replace(/(\d)\s+(m|ft)\b/g, '$1$2')
    .replace(/\s*→\s*/g, '>')
    .replace(/\s+/g, ' ').trim();

  // ── bottom gas header for messenger (trimix-aware) ──
  const _msgBotFracs = getBottomGasFractions();
  if (!_msgBotFracs) return null;
  const _msgBotLabel = getGasLabel(_msgBotFracs.fO2, _msgBotFracs.fHe);
  const _msgBotHe    = Math.round((_msgBotFracs.fHe || 0) * 100);
  const _msgBotDetail = _msgBotHe > 0
    ? `${_msgBotLabel} (O2:${Math.round(_msgBotFracs.fO2*100)}% He:${_msgBotHe}% N2:${Math.round(_msgBotFracs.fN2*100)}%)`
    : _msgBotLabel;

  const _msgNow = new Date();
  const _msgStamp = `${_msgNow.getFullYear()}/${String(_msgNow.getMonth()+1).padStart(2,'0')}/${String(_msgNow.getDate()).padStart(2,'0')} ${String(_msgNow.getHours()).padStart(2,'0')}:${String(_msgNow.getMinutes()).padStart(2,'0')}`;
  const _msgHr = '-'.repeat(28);
  const _msgGasHdr = buildDecoPlanHeaderData();

  const result = [];
  result.push(getDecoPlanTitle(_msgGasHdr));
  result.push(_msgStamp);
  result.push(_msgHr);
  // Algorithm + settings line
  const _algoSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const _algoNames = { ZHLC_GF: 'ZHL16C+GF', VPMB: 'VPM-B', VPMB_GFS: 'VPM-B/GFS' };
  const _algoShort = _algoNames[_algoSel] || _algoSel;
  const _cons = document.getElementById('conservatismSelect')?.value ?? '0';
  const _algoStr = _algoSel === 'ZHLC_GF'
    ? `${_algoShort} GF${gfL}/${gfH}`
    : _algoSel === 'VPMB'
      ? `${_algoShort} C+${_cons}`
      : `${_algoShort} GFHi${gfH} C+${_cons}`;
  result.push(`${depth}${du} / ${bt}min / ${_algoStr}`);
  if (isCcrOnLoopProfile({ circuit: _msgGasHdr.circuit, bailout: _msgGasHdr.ccrBailout })) {
    result.push(`Loop gas    : ${loopMixLabelFor(_msgBotLabel, { circuit: _msgGasHdr.circuit, bailout: _msgGasHdr.ccrBailout })} (on-loop)`);
  } else {
    const botLine = (_msgGasHdr.circuit === 'CCR' || _msgGasHdr.circuit === 'pSCR') ? 'Diluent     ' : 'Bottom Gas  ';
    result.push(`${botLine}: ${_msgBotDetail}`);
  }
  if (_msgGasHdr.travelGas) result.push(`Travel Gas  : ${_msgGasHdr.travelGas.gas} (switch @ ${_msgGasHdr.travelGas.depth})`);
  if (!isCcrOnLoopProfile({ circuit: _msgGasHdr.circuit, bailout: _msgGasHdr.ccrBailout })) {
    const gasPrefix = (_msgGasHdr.circuit === 'CCR' || _msgGasHdr.circuit === 'pSCR') ? 'Bailout mix' : 'Deco Gas';
    _msgGasHdr.decoGases.forEach((g, i) => result.push(`${gasPrefix} ${i + 1}  : ${g.gas} (switch @ ${g.depth})`));
  }
  const rndVal = (document.getElementById('stopRounding')?.value||'fractional')==='wholeminute'?'Yes':'No';
  const wvVal  = parseFloat(document.getElementById('waterVapor')?.value||'0.0627');
  const wvLbl  = wvVal<=0.058?'M':'B';
  result.push(`Stp Rounding: ${rndVal}  WV: ${wvVal}(${wvLbl})`);
  const _cpMdpEn = document.getElementById('minDecoProfileEnable')?.value === 'yes';
  const _cpMdp9m = document.getElementById('minDeco9m')?.value || '1';
  const _cpMdp6m = document.getElementById('minDeco6m')?.value || '3';
  const _cpDu    = units === 'imperial' ? 'ft' : 'm';
  if (_cpMdpEn) result.push(`Min Deco Profile: ON  (9${_cpDu}: ${_cpMdp9m} min  6${_cpDu}: ${_cpMdp6m} min)`);
  const _mAltM   = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const _mAltLbl = _mAltM === 0 ? 'Sea level' : `${_mAltM}m`;
  const _mAccl   = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const _mIsVPM  = _algoSel === 'VPMB' || _algoSel === 'VPMB_GFS';
  const _mAltSurfP = 1.01325 * Math.exp(-_mAltM / 8434);
  const _mAltRadii = _mIsVPM && _mAltM > 0
    ? `  Radii x${Math.pow(1.01325 / _mAltSurfP, 1/3).toFixed(3)}`
    : '';
  result.push(`Altitude    : ${_mAltLbl}  Acclimatized: ${_mAccl ? 'Yes' : 'No'}${_mAltRadii}`);
  // VPM repetitive dive
  const _mRepEl = document.getElementById('vpmRepMode');
  if (_mIsVPM && _mRepEl && _mRepEl.checked && typeof _lastVPMResult !== 'undefined' && _lastVPMResult) {
    const _mSI = parseFloat(document.getElementById('vpmSurfaceInterval')?.value || '60');
    result.push(`Repetitive  : SI ${_mSI} min (bubble state + tissue carried)`);
  }
  const _lastStop2    = document.getElementById('lastDecoStop')?.value || '-';
  const _decoStep2    = document.getElementById('decoStep')?.value    || '-';
  const _ascentRate2     = document.getElementById('ascentRate')?.value      || '-';
  const _decoAscentRate2 = document.getElementById('decoAscentRate')?.value  || '-';
  const _surfAscentRate2 = document.getElementById('surfaceAscentRate')?.value || '-';
  const _descentRate2 = document.getElementById('descentRate')?.value || '-';
  result.push(`Last Stop   : ${_lastStop2}${du}  Step: ${_decoStep2}${du}`);
  result.push(`Descent     : ${_descentRate2}${du}/min  Ascent: ${_ascentRate2}${du}/min`);
  result.push(`Deco        : ${_decoAscentRate2}${du}/min  Surface: ${_surfAscentRate2}${du}/min`);
  result.push('-'.repeat(28));

  rows.forEach(tr => {
    const ph  = tr.dataset.phase;
    if (ph === 'totals') return;
    const tds = tr.querySelectorAll('td');
    const c   = Array.from(tds).map(td => clean(td.textContent));

    if (ph === 'switch') {
      // Gas switch: ">> EAN50 @ 21m"
      const info = clean(Array.from(tds).map(td => td.textContent).join(' '));
      result.push(`>> ${info}`);
      return;
    }
    if (ph === 'descent' || ph === 'ascent') return; // skip travel rows - clutter

    // bottom level
    if (ph === 'bottom') {
      result.push(`Lvl  ${c[1]}  ${c[2]}  ${shortMix(c[3])}`);
      return;
    }

    // deco / safety stop
    const dep  = c[1] || '';
    const stop = parseStopDisplayTime(c[2]);
    const run  = c[4] || '';
    const mix  = shortMix(c[3]);
    result.push(`Stp  ${dep}  ${stop}  ${run}  ${mix}`);
  });

  // Totals line — VPM has no table footer row, use stat cards
  const _algoForCopy = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const _isVPMCopy   = _algoForCopy === 'VPMB' || _algoForCopy === 'VPMB_GFS';
  const totRow = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  let planSumCopy = getPlanSummaryExport(totRow);
  if (!totRow && _isVPMCopy && window._lastVPMExport) {
    const vx2 = window._lastVPMExport;
    const toMMSS = (n) => { const m = Math.floor(n), s = Math.round((n - m) * 60); return `${m}'${String(s).padStart(2,'0')}"`; };
    planSumCopy = {
      runTime: toMMSS(vx2.rt),
      tts: vx2.tts || toMMSS(Math.max(0, vx2.rt - parseFloat(document.getElementById('decoBT')?.value || '0'))),
      decoTime: toMMSS(vx2.deco),
      cns: vx2.cns,
      otu: vx2.otu,
      prt: vx2.prt,
      decozone: vx2.decozone || planSumCopy.decozone,
      decoStop: vx2.decoStop || planSumCopy.decoStop,
    };
  } else if (!totRow && _isVPMCopy) {
    const rtV  = document.getElementById('decoRunTimeDisplay')?.textContent?.trim().replace(/['\s]/g,'') || '-';
    const dtV  = document.getElementById('decoDecoTimeDisplay')?.textContent?.trim().replace(/\s*min\s*/,'') || '-';
    const cnsV = document.getElementById('decoCNSDisplay')?.textContent?.trim() || '-';
    const otuV = document.getElementById('decoOTUDisplay')?.textContent?.trim() || '-';
    const prtN = calcPrTBarMin(domDepthToM('decoDepth'), document.getElementById('decoBT')?.value || '0');
    planSumCopy.runTime = `${rtV}'00"`;
    planSumCopy.decoTime = `${dtV}'00"`;
    planSumCopy.cns = cnsV;
    planSumCopy.otu = otuV;
    planSumCopy.prt = isNaN(prtN) ? '-' : prtN.toFixed(1);
  }
  if (planSumCopy.prt === '-') {
    const prtN = calcPrTBarMin(domDepthToM('decoDepth'), document.getElementById('decoBT')?.value || '0');
    if (!isNaN(prtN)) planSumCopy.prt = prtN.toFixed(1);
  }
  result.push('-'.repeat(28));
  result.push(...formatPlanSummaryBlock(planSumCopy, true));

  return result.join('\n');
}

// ── Download .txt file ──
function exportTXT(mode) {
  if (mode === 'contingency' && !window._lastContingency) { showToast('Run an emergency plan first', 'export', true); return; }
  if (exportNeedsDecoBottomGas(mode) && !getBottomGasFractions()) { notifyInvalidGasExport('export'); return; }
  let text = mode === 'gasplan' ? buildGasPlanText() : buildExportText(mode);
  if (!text) return;
  if (mode === 'gasplan') {
    const dateStr = new Date().toISOString().split('T')[0];
    const blob = new Blob([text], { type: 'text/plain' });
    const a    = document.createElement('a');
    a.href     = URL.createObjectURL(blob);
    a.download = `LSP_${getExportCircuitTag()}_${dateStr}_GasPlan_${_gasRule}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
    showExportToast();
    return;
  }
  if (mode === 'deco') {
    const slate = buildSlateText();
    if (slate) text += '\n\n' + slate;
  }
  const now     = new Date();
  const dateStr = now.toISOString().split('T')[0];
  const du      = units === 'metric' ? 'm' : 'ft';
  // altitude suffix for filename
  const _expAltM  = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const _expAccl  = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const _altSuffix = _expAltM === 0 ? '' : `_Alt${_expAltM}m${_expAccl ? 'Accl' : 'NoAccl'}`;
  let tag = '';
  if (mode === 'deco') {
    const d    = document.getElementById('decoDepth')?.value || '0';
    const bt   = document.getElementById('decoBT')?.value    || '0';
    const algo = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
    const cons = document.getElementById('conservatismSelect')?.value || '0';
    const gfHi = mGF?.high || 85;
    const gfLo = mGF?.low  || 30;
    let algoTag = '';
    if (algo === 'ZHLC_GF')  algoTag = `GF${gfLo}-${gfHi}_Buhlmann`;
    else if (algo === 'VPMB') algoTag = `C${cons}_VPM-B`;
    else                      algoTag = `GF${gfHi}_C${cons}_VPM-B_GFS`;
    tag = `Deco_${d}${du}_${bt}min_${algoTag}${_altSuffix}`;
  } else if (mode === 'planner') {
    const d  = document.getElementById('depth')?.value || '0';
    const bt = document.getElementById('bt')?.value    || '0';
    tag = `Plan_${d}${du}_${bt}min${_altSuffix}`;
  } else if (mode === 'contingency') {
    const d  = document.getElementById('decoDepth')?.value || '0';
    const bt = document.getElementById('decoBT')?.value    || '0';
    const sc = (window._lastContingency?.label || 'Contingency')
               .replace(/\s+/g, '_').replace(/[^a-zA-Z0-9_-]/g, '');
    tag = `Emergency_${d}${du}_${bt}min_${sc}${_altSuffix}`;
  } else if (mode === 'multi') {
    tag = 'Multi_Dive';
  } else if (mode === 'cns') {
    tag = 'CNS_O2_Tracker';
  } else {
    tag = mode;
  }
  const blob = new Blob([text], { type: 'text/plain' });
  const a    = document.createElement('a');
  a.href     = URL.createObjectURL(blob);
  a.download = `LSP_${getExportCircuitTag()}_${dateStr}_${tag}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(a.href);
  showExportToast();
}

// ── Clipboard fallback (execCommand) ──
function copyFallback(text) {
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;left:-9999px;top:-9999px;opacity:0;width:1px;height:1px;padding:0;border:none;';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    if (ok) showCopyToast();
    else showToast('Copy failed — select text manually', 'copy', true);
  } catch(e) {
    console.error('Copy fallback error:', e);
    showToast('Copy failed', 'copy', true);
  }
}





function showCopyToast()   { showToast('📋 Copied!', 'copy'); }
function showExportToast() { showToast('📥 Saved!',  'export'); }
function showToast(msg, id, isError) {
  let toast = document.getElementById('toast-' + id);
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast-' + id;
    toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);padding:10px 22px;border-radius:20px;font-family:"JetBrains Mono",monospace;font-size:13px;font-weight:700;letter-spacing:1px;z-index:9999;transition:opacity 0.4s;pointer-events:none;max-width:min(90vw,480px);text-align:center;';
    document.body.appendChild(toast);
  }
  toast.style.background = isError ? 'var(--red)' : 'var(--accent)';
  toast.style.color = isError ? '#fff' : 'var(--bg)';
  toast.textContent = msg;
  toast.style.opacity = '1';
  setTimeout(() => { toast.style.opacity = '0'; }, isError ? 4000 : 2200);
}


function runPdfExportFromDialog() {
  const opts = {};
  ['gas', 'profile', 'slate', 'gfCurve', 'tissue'].forEach(k => {
    opts[k] = document.getElementById('pdfOpt_' + k)?.checked !== false;
  });
  document.getElementById('pdfExportDialog')?.remove();
  exportPDF(opts).catch(function(e) {
    console.error('[PDF export]', e);
    alert('PDF export failed: ' + (e && e.message ? e.message : e));
  });
}

function showPDFExportDialog() {
  // Remove any existing dialog
  const old = document.getElementById('pdfExportDialog');
  if (old) old.remove();

  const overlay = document.createElement('div');
  overlay.id = 'pdfExportDialog';
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:9999;display:flex;align-items:center;justify-content:center;';

  const box = document.createElement('div');
  box.style.cssText = 'background:var(--surface,#1a1e2e);border:1px solid var(--border,#2a3050);border-radius:12px;padding:24px 28px;width:340px;max-width:92vw;font-family:\'Outfit\',sans-serif;box-shadow:0 8px 40px rgba(0,0,0,0.5);';

  const sections = [
    { key:'gas',     label:'Gas Consumption',       checked:true  },
    { key:'profile', label:'Dive Profile Graph',     checked:true  },
    { key:'slate',   label:'Deco Slate',             checked:true  },
    { key:'gfCurve', label:'GF Gradient Factor Curve', checked:false },
    { key:'tissue',  label:'Tissue Saturation',      checked:false },
  ];

  let rows = sections.map(s => `
    <label style="display:flex;align-items:center;gap:10px;padding:7px 0;cursor:pointer;border-bottom:1px solid var(--border,#2a3050);">
      <input type="checkbox" id="pdfOpt_${s.key}" ${s.checked?'checked':''} style="width:15px;height:15px;accent-color:var(--accent,#00d9ff);cursor:pointer;">
      <span style="font-size:13px;color:var(--text,#e8eaf6);">${s.label}</span>
    </label>`).join('');

  box.innerHTML = `
    <div style="font-family:'Bebas Neue',sans-serif;font-size:18px;letter-spacing:2px;color:var(--accent,#00d9ff);margin-bottom:16px;">PDF EXPORT</div>
    <div style="font-size:11px;color:var(--muted,#8890b0);margin-bottom:14px;letter-spacing:0.5px;">SELECT SECTIONS TO INCLUDE</div>
    <div style="margin-bottom:18px;">${rows}</div>
    <div style="display:flex;gap:10px;justify-content:flex-end;">
      <button onclick="document.getElementById('pdfExportDialog').remove()"
        style="padding:9px 18px;background:transparent;color:var(--muted,#8890b0);border:1px solid var(--border,#2a3050);border-radius:6px;cursor:pointer;font-family:'Outfit',sans-serif;font-size:13px;font-weight:600;">
        Cancel
      </button>
      <button onclick="runPdfExportFromDialog()"
        style="padding:9px 18px;background:var(--accent,#00d9ff);color:#000;border:none;border-radius:6px;cursor:pointer;font-family:'Outfit',sans-serif;font-size:13px;font-weight:700;letter-spacing:1px;">
        EXPORT PDF
      </button>
    </div>`;

  overlay.appendChild(box);
  // Click outside to cancel
  overlay.addEventListener('click', e => { if(e.target===overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

// Force light theme for a canvas draw + capture, then restore original theme.
// PDF is always a light-background document — dark canvas graphs look bad in it.
function _drawForPDF(drawFn) {
  const body = document.body;
  const wasLight = body.classList.contains('light-theme');
  if (!wasLight) body.classList.add('light-theme');
  try { drawFn(); } finally {
    if (!wasLight) body.classList.remove('light-theme');
  }
}

async function exportPDF(opts) {
  opts = opts || {};
  if (!window._zhlHeadless) {
    const gasVal = validateDomDecoGases();
    if (!gasVal.ok) {
      throw new Error(gasVal.errors[0]?.message || 'Invalid gas mixture.');
    }
  }
  const _incGas      = opts.gas      !== false;
  const _incProfile  = opts.profile  !== false;
  const _incSlate    = opts.slate    !== false;
  const _incGFCurve  = opts.gfCurve  !== false;
  const _incTissue   = opts.tissue   !== false;

  if (!window.jspdf || !window.jspdf.jsPDF) { alert('PDF library not loaded. Please check your internet connection.'); return; }
  const { jsPDF } = window.jspdf;

  const doc = new jsPDF({ unit:'mm', format:'a4', orientation:'portrait' });
  if (!(await ensurePDFFontsForPDF(doc))) return;
  const now = new Date();
  const dateStr = now.toLocaleDateString('en-GB',{day:'2-digit',month:'short',year:'numeric'});
  const timeStr = now.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'});
  const isoDate = now.toISOString().split('T')[0];

  const decoModelSel = document.getElementById('algorithmSelect')?.value || 'ZHLC_GF';
  const isVPM = decoModelSel === 'VPMB' || decoModelSel === 'VPMB_GFS';
  const algoNames = { ZHLC_GF:'Bühlmann ZH-L16C+GF', VPMB:'VPM-B', VPMB_GFS:'VPM-B/GFS' };
  const algo = algoNames[decoModelSel] || 'Bühlmann ZH-L16C+GF';
  const cons = document.getElementById('conservatismSelect')?.value || '0';
  const gfStr = decoModelSel==='ZHLC_GF' ? `GF ${mGF.low}/${mGF.high}`
              : decoModelSel==='VPMB'     ? `C+${cons}`
              :                             `GFHi ${mGF.high} · C+${cons}`;
  // VPM extras
  const _pdfAltM      = (typeof altitudeM !== 'undefined') ? altitudeM : 0;
  const _pdfAccl      = (typeof altAcclimatized !== 'undefined') ? altAcclimatized : true;
  const _pdfAltLbl    = _pdfAltM === 0 ? 'Sea level' : `${_pdfAltM} m`;
  const _pdfAltSurfP  = 1.01325 * Math.exp(-_pdfAltM / 8434);
  const _pdfRadii     = isVPM && _pdfAltM > 0 ? Math.pow(1.01325 / _pdfAltSurfP, 1/3).toFixed(3) : null;
  const _pdfHeHt      = document.getElementById('heHalfTimeMode')?.value || 'baker';
  const _pdfHeHtLbl   = _pdfHeHt === 'baker' ? 'Baker 1.88 min' : 'Buhlmann 2003 1.51 min';
  const _pdfRepEl     = document.getElementById('vpmRepMode');
  const _pdfRepActive = isVPM && _pdfRepEl && _pdfRepEl.checked && typeof _lastVPMResult !== 'undefined' && _lastVPMResult;
  const _pdfSI        = _pdfRepActive ? (parseFloat(document.getElementById('vpmSurfaceInterval')?.value || '60')) : null;
  const _pdfSacUnit   = units === 'imperial' ? 'cu ft/min' : 'L/min';
  const du       = units === 'imperial' ? 'ft' : 'm';
  const depthVal = document.getElementById('decoDepth')?.value || '—';
  const btVal    = document.getElementById('decoBT')?.value    || '—';
  const densityLabel = waterDensityDisplayLabel();
  const _pdfHdr = buildDecoPlanHeaderData();
  const _pdfTravelInfo = _pdfHdr.travelGas;
  // Bottom gas: use fractions directly for accurate trimix label
  const _pdfBotFracs  = getBottomGasFractions();
  if (!_pdfBotFracs) throw new Error('Invalid bottom gas configuration.');
  const _pdfBotLabel  = getGasLabel(_pdfBotFracs.fO2, _pdfBotFracs.fHe);
  const _pdfBotO2     = Math.round(_pdfBotFracs.fO2 * 100);
  const _pdfBotHe     = Math.round((_pdfBotFracs.fHe || 0) * 100);
  const _pdfBotN2     = Math.round(_pdfBotFracs.fN2 * 100);
  const _pdfIsTrimix  = _pdfBotHe > 0;
  const bottomGasVal  = _pdfIsTrimix
    ? `${_pdfBotLabel} (O2:${_pdfBotO2}% He:${_pdfBotHe}% N2:${_pdfBotN2}%)`
    : _pdfBotLabel;
  const totalsRowEl = document.querySelector('#decoTableBody tr[data-phase="totals"] td');
  const planSumPdf = getPlanSummaryExport(totalsRowEl);
  let decoTimeVal = planSumPdf.decoTime;
  let totalRTVal = planSumPdf.runTime;
  let ttsVal = planSumPdf.tts;
  let cnsVal = planSumPdf.cns;
  let otuVal = planSumPdf.otu;
  let prtVal = planSumPdf.prt;
  let decoZoneVal = planSumPdf.decozone;
  let decoStopVal = planSumPdf.decoStop;
  let surfGFVal = planSumPdf.surfGF || '-';
  const algoTag = decoModelSel==='ZHLC_GF'?`GF${mGF.low}-${mGF.high}_Buhlmann`:decoModelSel==='VPMB'?`C${cons}_VPM-B`:`GFHi${mGF.high}_C${cons}_VPM-B_GFS`;
  const fileName = `LSP_${getExportCircuitTag()}_${isoDate}_Deco_${depthVal}${du}_${btVal}min_${algoTag}.pdf`;
  const PW=210, PH=297, ML=14, MR=14, MT=10, MB=10, CW=182;
  let y=MT;

  function cleanPDF(s){
    if(!s) return '';
    s = s.replace(/[₀-₉]/g, c => String.fromCharCode(c.charCodeAt(0)-0x2050));
    s = s.replace(/[²³¹]/g, c => ({'\u00B2':'2','\u00B3':'3','\u00B9':'1'}[c]||c));
    s = s.replace(/·|•|‧/g,'*').replace(/—/g,'--').replace(/–/g,'-').replace(/‘|’/g,"'").replace(/“|”/g,'"');
    // Strip decorative emoji/icon blocks but preserve ✓✗⚠ and arrows ↑↓←→
    s = s.replace(/[\u2600-\u269F\u26A1-\u26FF\u2700-\u2712\u2714-\u2716\u2718-\u27FF\u2B00-\u2BFF\u2300-\u23FF\uFE0F]/g,'');
    s = s.replace(/[^\x20-\x7E\xA0-\u024F\u2190-\u2193\u2713\u2717\u26A0]/g,'');
    return s.replace(/^\s*[!&*#^~]+\s*/,'').trim();
  }
  function checkY(n) { if(y+n>PH-MB){ drawFooter(); doc.addPage(); y=MT; drawHeader(); } }
  function drawHeader() {
    doc.setFillColor(0,85,170); doc.rect(0,0,PW,8,'F');
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
    doc.text('LSP D-PLANNER + CCR', ML, 5.5);
    doc.setFont('DejaVuSans','normal');
    doc.setFontSize(8);
    const hdrMid = `${btVal}min @ ${depthVal}${du} | ${bottomGasVal} | ${gfStr} | ${algo} | ${densityLabel}`;
    doc.text(hdrMid, PW/2, 5.5, {align:'center'});
    doc.setFontSize(8); doc.text(`${dateStr} ${timeStr}`, PW-MR, 5.5, {align:'right'});
    doc.setTextColor(0,0,0); y=MT;
  }
  function drawFooter() {
    doc.setFillColor(248,249,255); doc.rect(0,PH-6,PW,6,'F');
    doc.setFontSize(7); doc.setTextColor(100,100,120); doc.setFont('DejaVuSans','normal');
    doc.text('Planning Aid Only — Not a substitute for training, certification, or a dive computer · @threecats_lsp', ML, PH-2);
    doc.text(`${dateStr} ${timeStr}`, PW-MR, PH-2,{align:'right'});
    doc.setTextColor(0,0,0);
  }
  function sectionTitle(title, sub) {
    checkY(sub ? 14 : 12);
    let subLines = [];
    if (sub) {
      doc.setFont('DejaVuSans', 'normal');
      doc.setFontSize(7);
      subLines = doc.splitTextToSize(cleanPDF(sub), CW);
    }
    const subH = subLines.length ? 3.8 + subLines.length * 3.6 : 0;
    const boxH = (sub ? 5 + subH : 5);
    doc.setFillColor(232,240,255); doc.rect(ML-2,y,CW+4,boxH,'F');
    doc.setDrawColor(0,85,170); doc.setLineWidth(0.8); doc.line(ML-2,y,ML-2,y+boxH);
    doc.setFontSize(8); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,85,170);
    doc.text(cleanPDF(title), ML+1, y+4.8);
    if(subLines.length){
      doc.setFont('DejaVuSans','normal'); doc.setFontSize(7); doc.setTextColor(80,80,100);
      subLines.forEach((line, i) => doc.text(line, ML+1, y + 8.2 + i * 3.6));
    }
    doc.setTextColor(0,0,0); doc.setDrawColor(0,0,0); doc.setLineWidth(0.2); y += boxH + 4;
  }

  drawHeader();
  const _hasDecoPdf = (() => {
    const d = String(decoTimeVal || '');
    if (!d || d === '-') return false;
    if (/^0['"]|^0:00|^0 min/i.test(d)) return false;
    return true;
  })();
  y = drawDecoPlanBannerPdf(doc, y, { ML, CW, checkY, cleanPDF }, _pdfHdr, planSumPdf, _hasDecoPdf);
  const alertEls=document.querySelectorAll('#decoSummary .alert');
  [...alertEls].forEach(el=>{
    const txt=cleanPDF(el.textContent);
    const isNarc=txt.includes('NARCOTIC')||txt.includes('NDL');
    const isDeco=txt.includes('DECOMPRESSION');
    const isCNS=txt.includes('CNS');
    const bg=isNarc||isDeco?[255,68,51]:isCNS?[255,255,0]:[255,68,51];
    const tx=isNarc||isDeco?[255,255,255]:isCNS?[17,17,17]:[255,255,255];
    checkY(9); doc.setFillColor(...bg); doc.roundedRect(ML,y,CW,7,1.5,1.5,'F');
    doc.setFontSize(7.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(...tx);
    const ls=doc.splitTextToSize(txt,CW-4); const lh=5.5*ls.length;
    doc.setFillColor(...bg); doc.roundedRect(ML,y,CW,lh+2,1.5,1.5,'F');
    doc.text(ls,ML+2,y+4);
    doc.setTextColor(0,0,0); y+=lh+4;
  });
  y+=3;

  const _dRate  = document.getElementById('descentRate')?.value || '22';
  const _aRate  = document.getElementById('ascentRate')?.value || '9';
  const _daRate = document.getElementById('decoAscentRate')?.value || '9';
  const _saRate = document.getElementById('surfaceAscentRate')?.value || '9';
  const _wv     = parseFloat(document.getElementById('waterVapor')?.value || '0.0627');
  const _wvL    = _wv <= 0.058 ? 'M' : 'B';
  const _rnd    = (document.getElementById('stopRounding')?.value || 'fractional') === 'wholeminute' ? 'Yes' : 'No';
  // Build trimix detail + travel gas + VPM extras for profile subtitle
  const _pdfBotDetail = _pdfIsTrimix ? `${_pdfBotLabel} (O2:${_pdfBotO2}% He:${_pdfBotHe}% N2:${_pdfBotN2}%)` : _pdfBotLabel;
  const _pdfTravelStr = _pdfTravelInfo ? `  Travel:${_pdfTravelInfo.gas} @ ${_pdfTravelInfo.depth}` : '';
  const _pdfRepStr    = _pdfRepActive ? `  Rep.dive SI:${_pdfSI}min` : '';
  const _pdfAltStr    = _pdfAltM > 0 ? `  Alt:${_pdfAltLbl}${_pdfRadii?` Radii x${_pdfRadii}`:''}` : '';
  const _pdfHeHtStr   = isVPM ? `  He t½:${_pdfHeHtLbl}` : '';
  const _pdfMdpEn  = document.getElementById('minDecoProfileEnable')?.value === 'yes';
  const _pdfMdp9m  = document.getElementById('minDeco9m')?.value || '1';
  const _pdfMdp6m  = document.getElementById('minDeco6m')?.value || '3';
  const _pdfMdpStr = _pdfMdpEn ? `  MinDeco:ON(9${du}:${_pdfMdp9m}' 6${du}:${_pdfMdp6m}')` : '';
  sectionTitle('DIVE PROFILE', `${depthVal}${du} / ${btVal}min / ${cleanPDF(_pdfBotDetail)} / ${gfStr}`);
  const _pdfTbl = _pdfDecoTableLayout(ML, CW);
  const { colW, colX, tblMl, tblCw } = _pdfTbl;
  checkY(7);
  _pdfDrawDecoTableHeader(doc, y, _pdfTbl, [0, 85, 170]);
  y += 6;
  document.querySelectorAll('#decoTableBody tr').forEach((tr,rowI)=>{
    const phase=tr.dataset.phase; if(!phase) return;
    const tds=Array.from(tr.querySelectorAll('td')); const c=tds.map(td=>cleanPDF(td.textContent.trim()));
    checkY(5.5);
    if(phase==='switch'){
      _pdfDrawSwitchRow(doc, y, _pdfTbl, tr, cleanPDF);
      y+=5; return;
    }
    if(phase==='totals'){
      const t = `Run: ${planSumPdf.runTime}  TTS: ${planSumPdf.tts}  Deco: ${planSumPdf.decoTime}  CNS: ${planSumPdf.cns}  OTU: ${planSumPdf.otu}  PrT: ${planSumPdf.prt}  Surf GF: ${planSumPdf.surfGF||'-'}  Decozone: ${planSumPdf.decozone}  First deco: ${planSumPdf.decoStop}`;
      const tLines = doc.splitTextToSize(cleanPDF(t), tblCw - 4);
      const tH = 4.2 * tLines.length + 1.5;
      checkY(tH);
      doc.setFillColor(240,244,255); doc.rect(tblMl,y,tblCw,tH,'F');
      doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,60,130);
      tLines.forEach((line, li) => doc.text(line, tblMl+2, y + 3.8 + li * 4.2));
      doc.setTextColor(0,0,0); y+=tH; return;
    }
    const sa=tr.getAttribute('style')||'';
    const hasCnsHi=tr.hasAttribute('data-cnshi');
    const hi100=hasCnsHi && (sa.includes('#ffff00')||(sa.includes('255,255,0')&&!sa.includes('0.25')));
    const hi80=hasCnsHi && (sa.includes('rgba(255,255,0')||sa.includes('255,255,0,0.25'));
    if(hi100) doc.setFillColor(255,255,0);
    else if(hi80) doc.setFillColor(255,252,180);
    else if(rowI%2===0) doc.setFillColor(248,249,255);
    else doc.setFillColor(255,255,255);
    doc.rect(tblMl,y,tblCw,5,'F');
    const isDeco=phase==='deco',isAsc=phase==='ascent',isBtm=phase==='bottom',isSafe=phase==='safety',isDes=phase==='descent';
    const txC=(hi100||hi80)?[150,0,0]:isDeco?[180,0,0]:isAsc?[30,130,60]:isBtm?[0,60,160]:isSafe?[20,140,50]:[160,50,50];
    const icon=isDeco?'Stp':isAsc?'Asc':isBtm?'Lvl':isSafe?'Stp':isDes?'Des':'---';
    doc.setFontSize(7); doc.setFont('DejaVuSans','normal');
    doc.setTextColor(...txC); _pdfDrawDecoPhaseLabel(doc, y, _pdfTbl, icon);
    _pdfDrawDecoTableCells(doc, y, _pdfTbl, c.slice(1, 9), txC);
    y+=5;
  });
  y+=3; checkY(7); doc.setFontSize(7); doc.setFont('DejaVuSans','normal');
  const leg=['Des = Descent','Lvl = Bottom','Asc = Ascent','Stp = Deco/Safety Stop','>> = Gas Switch'];
  const lc=[[80,80,80],[80,80,80],[80,80,80],[80,80,80],[80,80,80],[100,0,150]];
  let lx=tblMl; leg.forEach((l,i)=>{doc.setTextColor(...lc[i]);doc.text(l,lx,y+3.5);lx+=doc.getTextWidth(l)+5;});
  doc.setTextColor(0,0,0); y+=8;

  // DECO SLATE section — compact waterproof-slate format (same as SLATE modal)
  const _pdfSlate = buildSlateText();
  if (_incSlate && _pdfSlate) {
    checkY(14); sectionTitle('DECO SLATE','Compact waterproof-slate format');
    const _slLines = _pdfSlate.split('\n').slice(1); // drop title line (already in section header)
    doc.setFontSize(7.5); doc.setFont('DejaVuSans','normal'); doc.setTextColor(20,20,20);
    _slLines.forEach(l=>{ checkY(4.2); doc.text(cleanPDF(l)||' ', ML+2, y+3); y+=4.2; });
    doc.setTextColor(0,0,0); y+=4;
  }

  // HIGH CNS% alert if applicable
  const _cnsPctMain = cnsVal ? parseFloat(cnsVal) : 0;
  if (_cnsPctMain >= 80) {
    checkY(10);
    doc.setFillColor(255,255,0); doc.setDrawColor(180,180,0);
    const _cnsMsgM = `HIGH CNS%. CNS oxygen load ${_cnsPctMain.toFixed(0)}% exceeds 80%. Reduce deco gas ppO2, switch depth, or bottom time.`;
    const _cnsLinesM = doc.splitTextToSize(_cnsMsgM, CW-4);
    const _cnsHM = 5.5*_cnsLinesM.length+2;
    doc.roundedRect(ML,y,CW,_cnsHM,1.5,1.5,'FD');
    doc.setFontSize(7.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(17,17,17);
    doc.text(_cnsLinesM,ML+2,y+4);
    doc.setTextColor(0,0,0); y+=_cnsHM+4;
  }

  const gasConsEl=document.getElementById('gasConsumptionSummary');
  if(_incGas&&gasConsEl&&gasConsEl.style.display!=='none'){
    calcGasPlan();
    const _gpPDF=window._lastGasPlan;
    if(_gpPDF&&_gpPDF.rows&&_gpPDF.rows.length){
      doc.addPage(); drawHeader();
      const sacBot=document.getElementById('sacBottom')?.value||'20';
      const sacDec=document.getElementById('sacDeco')?.value||'15';
      const pdfVolU=units==='imperial'?'cu ft':'L';
      const pdfPresU=units==='imperial'?'psi':'bar';
      const pdfRuleName=_gpPDF.rule==='half'?'Half Tank':'Thirds';
      sectionTitle('GAS CONSUMPTION',`${pdfRuleName} rule  •  SAC bottom: ${sacBot} ${_pdfSacUnit}  deco: ${sacDec} ${_pdfSacUnit}`);

      // ── Table header ──────────────────────────────────────────────────────
      // Column widths (sum = CW ~170mm)
      const gc={
        gas:   26, vol: 22, thirds: 18, turn: 22,
        res:   18, suf: 38, margin: 22
      };
      const gx={
        gas: ML,
        vol: ML+gc.gas,
        thirds: ML+gc.gas+gc.vol,
        turn: ML+gc.gas+gc.vol+gc.thirds,
        res:  ML+gc.gas+gc.vol+gc.thirds+gc.turn,
        suf:  ML+gc.gas+gc.vol+gc.thirds+gc.turn+gc.res,
        margin: ML+gc.gas+gc.vol+gc.thirds+gc.turn+gc.res+gc.suf
      };
      const hdrs=['GAS','TOTAL VOL','THIRDS','TURN PRESS','RESERVE','SUFFICIENT','MARGIN'];
      const hkeys=['gas','vol','thirds','turn','res','suf','margin'];
      const ROW_H=6.5, HDR_H=6;

      checkY(HDR_H + _gpPDF.rows.length*(ROW_H+1) + 20);

      // Header background
      doc.setFillColor(30,40,60);
      doc.rect(ML, y, Object.values(gc).reduce((a,b)=>a+b,0), HDR_H, 'F');
      doc.setFontSize(6); doc.setFont('DejaVuSans','bold'); doc.setTextColor(0,200,255);
      hdrs.forEach((h,i)=>{
        const k=hkeys[i];
        doc.text(h, gx[k]+gc[k]/2, y+4, {align:'center'});
      });
      y += HDR_H;

      // ── Data rows ──────────────────────────────────────────────────────────
      const ruleTxt = _gpPDF.rule==='half'?'1/2':'1/3';

      _gpPDF.rows.forEach((r, ri)=>{
        // Alternate row background
        ri%2===0 ? doc.setFillColor(245,247,252) : doc.setFillColor(255,255,255);
        doc.rect(ML, y, Object.values(gc).reduce((a,b)=>a+b,0), ROW_H, 'F');

        const lbl = cleanPDF(r.label);
        const isBottom = r.kind === 'bottom';
        const insufficient = isBottom ? (r.shortL!=null && r.shortL>0) : (r.reqL!=null && r.totalL < r.reqL);

        // ── GAS cell ──
        doc.setFontSize(7); doc.setFont('DejaVuSans','bold');
        doc.setTextColor(insufficient ? 180 : 40, insufficient ? 0 : 40, insufficient ? 0 : 40);
        doc.text(lbl, gx.gas+1, y+4.2);

        // ── TOTAL VOL ──
        const volCol = insufficient ? [180,0,0] : [0,120,60];
        doc.setFont('DejaVuSans','normal'); doc.setFontSize(6.5);
        doc.setTextColor(...volCol);
        doc.text(`${gpVolDisp(r.totalL)} ${pdfVolU}`, gx.vol+gc.vol/2, y+4.2, {align:'center'});

        // ── THIRDS (bottom only) ──
        if(isBottom && r.portionL!=null){
          doc.setTextColor(100,100,100);
          doc.text(`${gpVolDisp(r.portionL)} ${pdfVolU}`, gx.thirds+gc.thirds/2, y+4.2, {align:'center'});
        } else {
          doc.setTextColor(160,160,160);
          doc.text('—', gx.thirds+gc.thirds/2, y+4.2, {align:'center'});
        }

        // ── TURN PRESS (bottom only) ──
        if(isBottom && r.turnBar!=null && !insufficient){
          doc.setTextColor(0,150,200);
          doc.text(`${gpPresDisp(r.turnBar)} ${pdfPresU}`, gx.turn+gc.turn/2, y+4.2, {align:'center'});
        } else if(isBottom){
          doc.setTextColor(160,160,160);
          doc.text('—', gx.turn+gc.turn/2, y+4.2, {align:'center'});
        } else {
          doc.setTextColor(160,160,160);
          doc.text('one-way', gx.turn+gc.turn/2, y+4.2, {align:'center'});
        }

        // ── RESERVE ──
        doc.setTextColor(100,100,100);
        doc.text(`${gpPresDisp(r.reserveBar)} ${pdfPresU}`, gx.res+gc.res/2, y+4.2, {align:'center'});

        // ── SUFFICIENT ──
        if(isBottom){
          if(insufficient){
            doc.setFont('DejaVuSans','bold'); doc.setTextColor(180,0,0);
            doc.text(`SHORT ${gpVolDisp(r.shortL)} ${pdfVolU}`, gx.suf+1, y+2.8);
            if(r.maxBTmin!=null){
              doc.setFont('DejaVuSans','normal'); doc.setFontSize(5.5); doc.setTextColor(140,0,0);
              doc.text(`BT→${r.maxBTmin}min, turn ${gpPresDisp(r.maxTurnBar)}${pdfPresU}`, gx.suf+1, y+5.8);
            }
          } else {
            doc.setFont('DejaVuSans','normal'); doc.setTextColor(0,130,60);
            doc.text(`turn ${gpPresDisp(r.turnBar)}${pdfPresU}  OK ${gpVolDisp(r.reqL)}${pdfVolU}`, gx.suf+1, y+4.2);
          }
        } else {
          if(r.reqL==null){
            doc.setFont('DejaVuSans','normal'); doc.setTextColor(160,160,160);
            doc.text('run plan first', gx.suf+1, y+4.2);
          } else {
            const stat3sym = r.totalL>=r.reqL*1.10?'✓':r.totalL>=r.reqL?'⚠':'✗';
            const stat3txt = r.totalL>=r.reqL*1.10?' OK':r.totalL>=r.reqL?' TIGHT':' SHORT';
            const tc3 = r.totalL>=r.reqL*1.10?[0,130,60]:r.totalL>=r.reqL?[180,80,0]:[180,0,0];
            doc.setFont('DejaVuSans','bold'); doc.setTextColor(...tc3);
            doc.text(stat3sym+stat3txt, gx.suf+1, y+2.8);
            doc.setFont('DejaVuSans','normal'); doc.setFontSize(5.5); doc.setTextColor(100,100,100);
            doc.text(`need ${gpVolDisp(r.reqL)} ${pdfVolU}`, gx.suf+1, y+5.8);
          }
        }

        // ── MARGIN ──
        doc.setFontSize(6.5);
        if(isBottom && r.reqL!=null){
          const mg = r.totalL - r.reqL;
          const mgCol = mg >= 0 ? [0,130,60] : [180,0,0];
          doc.setFont('DejaVuSans','bold'); doc.setTextColor(...mgCol);
          doc.text(`${mg>=0?'+':''}${gpVolDisp(mg)} ${pdfVolU}`, gx.margin+gc.margin/2, y+4.2, {align:'center'});
        } else if(!isBottom && r.reqL!=null){
          const mg3 = r.totalL - r.reqL;
          const mgCol3 = mg3 >= 0 ? [0,130,60] : [180,0,0];
          doc.setFont('DejaVuSans','bold'); doc.setTextColor(...mgCol3);
          doc.text(`${mg3>=0?'+':''}${gpVolDisp(mg3)} ${pdfVolU}`, gx.margin+gc.margin/2, y+4.2, {align:'center'});
        } else {
          doc.setTextColor(160,160,160);
          doc.text('—', gx.margin+gc.margin/2, y+4.2, {align:'center'});
        }

        // Row border
        doc.setDrawColor(210,215,225); doc.setFont('DejaVuSans','normal'); doc.setFontSize(7);
        doc.line(ML, y+ROW_H, ML+Object.values(gc).reduce((a,b)=>a+b,0), y+ROW_H);
        y += ROW_H;
      });
      y += 4;
    }
  }

  if(_incProfile) _drawForPDF(() => drawDecoProfile());
  const pc=document.getElementById('decoProfileCanvas');
  if(_incProfile&&pc){
    doc.addPage(); drawHeader();
    sectionTitle('DIVE PROFILE GRAPH',`${depthVal}${du} / ${btVal}min / ${algo} / ${gfStr}`);
    const _pcCap=_canvasToDataURLForPDF(pc,CW); const id=_pcCap.dataURL; const ih=CW*pc.height/pc.width;
    checkY(ih); doc.addImage(id,'PNG',ML,y,CW,ih); y+=ih+4;
    y = drawGraphLegend(doc, y, ML, CW, checkY);
  }

  if(!isVPM){
    if(_incGFCurve) _drawForPDF(() => drawGFCurve());
    if(_incGFCurve){
    doc.addPage(); drawHeader();
    const gc=document.getElementById('gfCurveCanvas');
    if(gc){
      checkY(60); sectionTitle('GRADIENT FACTOR CURVE',`GF Low ${mGF.low}%  GF High ${mGF.high}%`);
      const _gcCap=_canvasToDataURLForPDF(gc,CW); const gd=_gcCap.dataURL; const gh=CW*gc.height/gc.width;
      doc.addImage(gd,'PNG',ML,y,CW,gh); y+=gh+4;
      // GF curve legend — same numbered stops as web view
      const gfLegEl=document.getElementById('gfCurveLegend');
      const gfRows=gfLegEl?Array.from(gfLegEl.querySelectorAll('tbody tr')):[];
      if(gfRows.length){
        checkY(gfRows.length*5+10);
        doc.setFillColor(240,244,255); doc.rect(ML,y,CW,5.5,'F');
        doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(80,80,120);
        const gcw=[8,80,30,24]; const gcx=[ML,ML+8,ML+88,ML+118];
        ['#','Stop','Run','ppO2'].forEach((h,i)=>doc.text(h,gcx[i]+gcw[i]/2,y+3.8,{align:'center'}));
        doc.setTextColor(0,0,0); y+=5.5;
        gfRows.forEach((tr,ri)=>{
          const cells=Array.from(tr.querySelectorAll('td'));
          const num=cells[0]?.textContent.trim()||'';
          const stop=cells[1]?.textContent.trim().replace(/[^\x20-\x7E]/g,'').trim()||'';
          const run=cells[2]?.textContent.trim()||'';
          const ppo=cells[3]?.textContent.trim()||'';
          const ppoV=parseFloat(ppo)||0;
          const tc=ppoV>=1.6?[200,0,0]:ppoV>=1.4?[180,100,0]:[60,120,60];
          ri%2===0?doc.setFillColor(248,249,255):doc.setFillColor(255,255,255);
          doc.rect(ML,y,CW,5,'F');
          doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal');
          doc.setTextColor(180,0,0); doc.text(num,gcx[0]+gcw[0]/2,y+3.5,{align:'center'});
          doc.setTextColor(60,60,60); doc.text(stop,gcx[1]+2,y+3.5);
          doc.setTextColor(80,80,80); doc.text(run,gcx[2]+gcw[2],y+3.5,{align:'right'});
          doc.setTextColor(...tc); doc.text(ppo,gcx[3]+gcw[3],y+3.5,{align:'right'});
          doc.setTextColor(0,0,0); y+=5;
        });
        y+=4;
      }
    }
    } // end if(_incGFCurve)
    if(_incTissue){
      // Ensure tissue data is populated
      const ttb=document.getElementById('tissueTableBody');
      if(ttb&&ttb.rows.length===0&&lastTissues) updateTissueViz(lastTissues, mGF.high);

      if(lastTissues&&lastTissues.length){
        doc.addPage(); drawHeader();
        sectionTitle('TISSUE SATURATION — SURFACE SNAPSHOT','Bühlmann ZH-L16C · GF High applied · end-of-dive compartment loading');

        // ── Section 1: Surface Saturation bars ──
        const gfF = mGF.high/100;
        const BAR_X=ML+28, BAR_W=CW-52, BAR_H=5, ROW=6.5;
        // Column headers
        checkY(7);
        doc.setFontSize(6); doc.setFont('DejaVuSans','bold'); doc.setTextColor(100,100,140);
        doc.text('#',   ML+2,  y+4);
        doc.text('t½',  ML+14, y+4);
        doc.text('Saturation vs GF-adjusted M-value at surface', BAR_X+2, y+4);
        doc.text('%',   ML+CW-3, y+4, {align:'right'});
        doc.setTextColor(0,0,0); y+=6;

        lastTissues.forEach((t0pdf,i)=>{
          const pN2pdf=t0pdf.pN2; const pHepdf=t0pdf.pHe||0; const pTotpdf=pN2pdf+pHepdf;
          checkY(ROW);
          const [ht,a_n2pdf,b_n2pdf]=ZHL16C[i];
          let a=a_n2pdf, b=b_n2pdf;
          if(pHepdf>0&&pTotpdf>0){
            a=(pN2pdf*a_n2pdf+pHepdf*ZHL16C_HE_AB[i][0])/pTotpdf;
            b=(pN2pdf*b_n2pdf+pHepdf*ZHL16C_HE_AB[i][1])/pTotpdf;
          }
          const mv = gfAdjustedMValue(a, b, altSurfaceP, gfF);
          const pct=Math.min(100,Math.round((pTotpdf/mv)*100));
          const cr=pct>=100?[220,0,0]:pct>=90?[200,80,0]:pct>=75?[180,150,0]:[20,160,60];
          // Labels
          doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal'); doc.setTextColor(100,100,120);
          doc.text(`${i+1}`, ML+4, y+4, {align:'center'});
          doc.text(`${ht}`, ML+18, y+4, {align:'center'});
          // Bar bg
          doc.setFillColor(220,222,235); doc.roundedRect(BAR_X,y+0.5,BAR_W,BAR_H,1,1,'F');
          // Bar fill
          doc.setFillColor(...cr); doc.roundedRect(BAR_X,y+0.5,BAR_W*pct/100,BAR_H,1,1,'F');
          // Pct
          doc.setFontSize(6.5); doc.setTextColor(...cr); doc.setFont('DejaVuSans','bold');
          doc.text(`${pct}%`, ML+CW-2, y+4, {align:'right'});
          doc.setTextColor(0,0,0); y+=ROW;
        });

        // Color legend
        y+=2; checkY(5);
        doc.setFontSize(6); doc.setFont('DejaVuSans','normal');
        const legItems=[[20,160,60,'<75% clear'],[180,150,0,'75-90% loaded'],[200,80,0,'90-99% near limit'],[220,0,0,'>=100% at M-value']];
        let lx=ML;
        legItems.forEach(([r,g,b2,lbl])=>{
          doc.setFillColor(r,g,b2); doc.roundedRect(lx,y+1,3,3,0.5,0.5,'F');
          doc.setTextColor(80,80,100); doc.text(lbl,lx+5,y+4);
          lx+=doc.getTextWidth(lbl)+11;
        });
        doc.setTextColor(0,0,0); y+=7;

        // ── Section 2: Compartment Detail table ──
        checkY(12);
        doc.setFillColor(220,228,248); doc.rect(ML,y,CW,5,'F');
        doc.setFontSize(7); doc.setFont('DejaVuSans','bold'); doc.setTextColor(30,50,120);
        doc.text('COMPARTMENT DETAIL', ML+2, y+3.5);
        doc.setFontSize(6); doc.setFont('DejaVuSans','normal'); doc.setTextColor(80,90,130);
        doc.text('exact N₂/He loads, M-values, and saturation status at surfacing', ML+CW-2, y+3.5, {align:'right'});
        doc.setTextColor(0,0,0); y+=6;

        const th2=['#','t½ (min)','N₂+He (bar)','M-val (bar)','Sat %','Status'];
        const tw=[8,22,30,28,22,28]; const tx2=[ML]; tw.forEach((w,i)=>{if(i<tw.length-1)tx2.push(tx2[i]+tw[i]);});
        checkY(6);
        doc.setFillColor(0,85,170); doc.rect(ML,y,CW,5.5,'F');
        doc.setFontSize(6.5); doc.setFont('DejaVuSans','bold'); doc.setTextColor(255,255,255);
        th2.forEach((h,i)=>doc.text(h, tx2[i]+tw[i]/2, y+3.8, {align:'center'}));
        doc.setTextColor(0,0,0); y+=5.5;

        lastTissues.forEach((t0pdf,i)=>{
          checkY(5);
          const pN2pdf=t0pdf.pN2; const pHepdf=t0pdf.pHe||0; const pTotpdf=pN2pdf+pHepdf;
          const [ht,a_n2pdf,b_n2pdf]=ZHL16C[i];
          let a=a_n2pdf, b=b_n2pdf;
          if(pHepdf>0&&pTotpdf>0){
            a=(pN2pdf*a_n2pdf+pHepdf*ZHL16C_HE_AB[i][0])/pTotpdf;
            b=(pN2pdf*b_n2pdf+pHepdf*ZHL16C_HE_AB[i][1])/pTotpdf;
          }
          const mv = gfAdjustedMValue(a, b, altSurfaceP, gfF);
          const pct=Math.min(100,Math.round((pTotpdf/mv)*100));
          const cr=pct>=100?[200,0,0]:pct>=90?[180,80,0]:pct>=75?[150,120,0]:[20,140,50];
          const status=pct>=100?'LIMIT':pct>=90?'HIGH':pct>=75?'MED':'OK';
          const loadStr=pHepdf>0?`${pTotpdf.toFixed(3)} (${pN2pdf.toFixed(2)}+${pHepdf.toFixed(2)})`:pTotpdf.toFixed(3);
          i%2===0?doc.setFillColor(248,249,255):doc.setFillColor(255,255,255);
          doc.rect(ML,y,CW,5,'F');
          doc.setFontSize(6.5); doc.setFont('DejaVuSans','normal');
          doc.setTextColor(80,80,100); doc.text(`${i+1}`,      tx2[0]+tw[0]/2, y+3.5, {align:'center'});
          doc.setTextColor(80,80,100); doc.text(`${ht}`,        tx2[1]+tw[1]/2, y+3.5, {align:'center'});
          doc.setTextColor(60,60,100); doc.text(loadStr,        tx2[2]+1,       y+3.5);
          doc.setTextColor(60,60,100); doc.text(mv.toFixed(3),  tx2[3]+tw[3]/2, y+3.5, {align:'center'});
          doc.setFont('DejaVuSans','bold'); doc.setTextColor(...cr);
          doc.text(`${pct}%`,  tx2[4]+tw[4]/2, y+3.5, {align:'center'});
          doc.text(status,     tx2[5]+tw[5]/2, y+3.5, {align:'center'});
          doc.setTextColor(0,0,0); y+=5;
        });
        y+=4;

        // ── Section 3: Per-Stop Saturation ──
        const lp=window._lastPlan;
        if(lp&&lp.steps){
          const decoSteps=lp.steps.filter(s=>(s.type==='deco'||s.type==='safety')&&s._tissues&&s._tissues.length===16);
          if(decoSteps.length>0){
            doc.addPage(); drawHeader();
            sectionTitle('TISSUE SATURATION — PER-STOP ASCENT PROFILE','Each column = one deco stop · each row = one compartment · bars = tension / GF-adjusted M-value at stop depth');

            const dU=units==='metric'; const conv=dU?1:3.28084; const uLbl=dU?'m':'ft';
            const gfApplied=mGF.high/100;
            const nStops=decoSteps.length;

            // Layout: comp col + t½ col + one col per stop
            const COMP_W=10, HT_W=14;
            const stopColW=Math.min(16, Math.floor((CW-COMP_W-HT_W)/nStops));
            const totalW=COMP_W+HT_W+stopColW*nStops;
            const startX=ML+(CW-totalW)/2; // center the table

            // Header row — stop depths
            checkY(12);
            doc.setFontSize(5.5); doc.setFont('DejaVuSans','bold');
            doc.setFillColor(20,30,60); doc.rect(startX,y,totalW,10,'F');
            doc.setTextColor(150,180,220);
            doc.text('C#',  startX+COMP_W/2, y+4, {align:'center'});
            doc.text('t½',  startX+COMP_W+HT_W/2, y+4, {align:'center'});
            decoSteps.forEach((s,si)=>{
              const cx=startX+COMP_W+HT_W+si*stopColW;
              const depthD=Math.round(s.depth*conv);
              const stopM=s.dur>=1?Math.round(s.dur)+"'":'<1\'';
              doc.setTextColor(0,200,255);
              doc.text(`${depthD}${uLbl}`, cx+stopColW/2, y+3.5, {align:'center'});
              doc.setTextColor(120,150,180);
              doc.text(stopM, cx+stopColW/2, y+8, {align:'center'});
            });
            doc.setTextColor(0,0,0); y+=11;

            // One row per compartment
            const CROW=7.5;
            for(let i=0;i<16;i++){
              checkY(CROW);
              const [htN2,a_n2r,b_n2r]=ZHL16C[i];
              i%2===0?doc.setFillColor(245,247,252):doc.setFillColor(252,252,255);
              doc.rect(startX,y,totalW,CROW,'F');
              // Comp # and half-time
              doc.setFontSize(6); doc.setFont('DejaVuSans','normal');
              doc.setTextColor(100,110,140);
              doc.text(`C${i+1}`, startX+COMP_W/2, y+4.5, {align:'center'});
              doc.text(`${htN2}`, startX+COMP_W+HT_W/2, y+4.5, {align:'center'});
              // Bar per stop
              decoSteps.forEach((s,si)=>{
                const t=s._tissues[i];
                const pN2r=t.pN2||0; const pHer=t.pHe||0; const pTr=pN2r+pHer;
                const pAmb=altSurfaceP+s.depth * BAR_PER_METRE;
                let ar=a_n2r, br=b_n2r;
                if(pTr>0&&pHer>0){
                  const wN2=pN2r/pTr, wHe=pHer/pTr;
                  ar=wN2*a_n2r+wHe*ZHL16C_HE_AB[i][0];
                  br=wN2*b_n2r+wHe*ZHL16C_HE_AB[i][1];
                }
                const mValR = gfAdjustedMValue(ar, br, pAmb, gfApplied);
                const pctR=mValR>0?Math.round((pTr/mValR)*100):0;
                const clampR=Math.max(0,Math.min(120,pctR));
                const barPctR=Math.min(100,clampR);
                const crR=clampR>=100?[220,0,0]:clampR>=90?[200,80,0]:clampR>=75?[180,150,0]:[20,160,60];
                const cx=startX+COMP_W+HT_W+si*stopColW;
                const bx=cx+1, bw=stopColW-2, bh=4;
                // Bar bg
                doc.setFillColor(210,215,230); doc.roundedRect(bx,y+0.8,bw,bh,0.8,0.8,'F');
                // Bar fill
                if(barPctR>0){ doc.setFillColor(...crR); doc.roundedRect(bx,y+0.8,bw*barPctR/100,bh,0.8,0.8,'F'); }
                // Pct label
                doc.setFontSize(5); doc.setTextColor(...crR); doc.setFont('DejaVuSans','bold');
                doc.text(`${clampR}%`, cx+stopColW/2, y+6.8, {align:'center'});
              });
              doc.setTextColor(0,0,0); y+=CROW;
            }
            // Legend
            y+=3; checkY(5);
            doc.setFontSize(6); doc.setFont('DejaVuSans','normal');
            let lx2=ML;
            [[20,160,60,'<75% clear'],[180,150,0,'75-90% loaded'],[200,80,0,'90-99% near limit'],[220,0,0,'>=100% at M-value']].forEach(([r,g,b2,lbl])=>{
              doc.setFillColor(r,g,b2); doc.roundedRect(lx2,y+1,3,3,0.5,0.5,'F');
              doc.setTextColor(80,80,100); doc.text(lbl,lx2+5,y+4);
              lx2+=doc.getTextWidth(lbl)+11;
            });
            doc.setTextColor(0,0,0); y+=7;
          }
        }
      }
    } // end if(_incTissue)
  } else {
    if(_incTissue||_incGFCurve){
    checkY(12);
    sectionTitle('TISSUE SATURATION & GF CURVE',`N/A for ${algo} - Buhlmann ZH-L16C only`);
    doc.setFontSize(8);doc.setTextColor(100,100,120);
    doc.text('Tissue saturation and gradient factor analysis require Bühlmann ZH-L16C algorithm.',ML,y+4);
    doc.setTextColor(0,0,0);y+=9;
    } // end if(_incTissue||_incGFCurve)
  }

  // Emergency plan intentionally excluded from main deco PDF.
  // Use the dedicated Emergency Plan PDF button for that.
  if(false){
    const colX = [ML, ML + 12, ML + 30, ML + 48, ML + 66, ML + 84, ML + 102, ML + 120, ML + 138, ML + 156];
    const colW = [12, 18, 18, 18, 18, 18, 18, 18, 18, 18];
    doc.addPage(); drawHeader();
    const cc=window._lastContingency;
    doc.setFillColor(255,240,240);doc.setDrawColor(200,100,100);
    doc.roundedRect(ML,y,CW,18,2,2,'FD');
    doc.setFontSize(11);doc.setFont('DejaVuSans','bold');doc.setTextColor(180,30,30);
    doc.text('EMERGENCY PLAN: '+cc.label,ML+3,y+6);
    doc.setFontSize(8);doc.setFont('DejaVuSans','normal');doc.setTextColor(100,0,0);
    doc.text(`Run: ${cc.lastRunFmt||cc.lastRun+"'00\""} | TTS: ${cc.tts||'—'} | Deco: ${cc.decoTimeFmt||cc.decoTime+"'00\""} | CNS: ${cc.totalCNS||'—'} | OTU: ${cc.totalOTU||'—'} | PrT: ${cc.totalPrT||'—'} | Decozone: ${cc.decozoneDisp||formatDecoZoneStart(cc.decoZoneStart)} | First deco: ${cc.decoStop||'—'}`,ML+3,y+11);
    doc.setTextColor(150,0,0);doc.text(cc.msg||'',ML+3,y+15.5);
    doc.setTextColor(0,0,0);y+=22;
    sectionTitle('EMERGENCY ASCENT SCHEDULE', cc.label);
    doc.setFillColor(180,30,30);doc.rect(ML,y,CW,6,'F');
    doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(255,255,255);
    ['Phase','Depth','Stop','Run','TTS','Mix','EAD','END','PPO2','CNS%'].forEach((h,i)=>doc.text(h,colX[i]+colW[i]/2,y+4,{align:'center'}));
    doc.setTextColor(0,0,0);y+=6;
    document.querySelectorAll('#contingencyResult .deco-table tbody tr').forEach((tr,ri)=>{
      const ph=tr.dataset.phase; const tds2=Array.from(tr.querySelectorAll('td')); const cv=tds2.map(td=>td.textContent.trim());
      checkY(5.5);
      if(ph==='switch'){const t=tds2.slice(1).map(td=>td.textContent.trim()).filter(Boolean).join(' ');doc.setDrawColor(0,122,51);doc.setLineWidth(1);doc.line(ML,y,ML+CW,y);doc.setFillColor(255,215,0);doc.rect(ML,y,CW,5,'F');doc.line(ML,y+5,ML+CW,y+5);doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(0,100,40);doc.text('>> '+cleanPDF(t),ML+2,y+3.5);doc.setTextColor(0,0,0);doc.setLineWidth(0.2);y+=5;return;}
      if(ph==='totals'){const sps=tds2[0]?.querySelectorAll('span')||[];let t='';sps.forEach(s=>{const v=s.textContent.trim();if(v)t+=(t?'  ':'')+v;});if(!t&&tds2[0])t=tds2[0].textContent.replace(/\s+/g,' ').trim();doc.setFillColor(255,240,240);doc.rect(ML,y,CW,5.5,'F');doc.setFontSize(7);doc.setFont('DejaVuSans','bold');doc.setTextColor(150,0,0);doc.text(t,ML+2,y+3.8);doc.setTextColor(0,0,0);y+=5.5;return;}
      const id2=ph==='deco',ia=ph==='ascent',ib=ph==='bottom',is2=ph==='safety',id3=ph==='descent';
      ri%2===0?doc.setFillColor(255,250,250):doc.setFillColor(255,255,255);doc.rect(ML,y,CW,5,'F');
      const tc=id2?[180,0,0]:ia?[30,130,60]:ib?[0,60,160]:is2?[20,140,50]:[160,50,50];
      const ic=id2?'●':ia?'↑':ib?'●':is2?'●':id3?'↓':'·';
      doc.setFontSize(7);doc.setFont('DejaVuSans','normal');doc.setTextColor(...tc);doc.text(ic,colX[0]+colW[0]/2,y+3.5,{align:'center'});
      [cv[1],cv[2],cv[3],cv[4],cv[5],cv[6],cv[7],cv[8],cv[9]].forEach((v,i)=>{if(v&&v!=='-'&&v!=='—')doc.text(v,colX[i+1]+colW[i+1]/2,y+3.5,{align:'center'});});
      doc.setTextColor(0,0,0);y+=5;
    });
  }

  const tp=doc.getNumberOfPages(); for(let p=1;p<=tp;p++){doc.setPage(p);drawFooter();}
  doc.save(fileName);
  showExportToast();
}
