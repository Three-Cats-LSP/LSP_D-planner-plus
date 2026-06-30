/**
 * Surface interval calculator — RUNTIME UI CORE.
 * Loaded by index.html before main inline script.
 * Globals read: units, altSurfaceP, BAR_PER_METRE, WATER_VAPOR, ZHL16C, ZHL16C_HE_HT,
 *   initTissues, saturate, saturateLinear, schreiner, getBottomGasFractions, FN2_AIR,
 *   updateSliderFill
 * Globals written: (none)
 */

// ═══════════════════════════════════════════════
// SURFACE INTERVAL — minimum SI between two air dives
// Reuses the app's ZH-L16C compartment data + saturate()/initTissues()
// ═══════════════════════════════════════════════
function computeSurfIntervalCore(opts) {
  const d1 = opts.d1;
  const bt1 = opts.bt1;
  const d2 = opts.d2;
  const bt2 = opts.bt2;
  const gfLow = (opts.gfLowPct != null ? opts.gfLowPct : 30) / 100;
  const gfHigh = (opts.gfHighPct != null ? opts.gfHighPct : 85) / 100;
  const dive1Gas = opts.dive1Gas || { fN2: FN2_AIR, fHe: 0 };
  const dive2Gas = opts.dive2Gas || dive1Gas;
  const surfGas = opts.surfGas || { fN2: FN2_AIR, fHe: 0 };
  const descentRate = opts.descentRate != null ? opts.descentRate : 18;

  let tissues = initTissues();
  const descTime = d1 / descentRate;
  tissues = saturateLinear(tissues, 0, d1, descTime, dive1Gas.fN2, dive1Gas.fHe || 0);
  const btAtDepth = Math.max(0, bt1 - descTime);
  tissues = saturate(tissues, d1, btAtDepth, dive1Gas.fN2, dive1Gas.fHe || 0);
  const ceilingFn = (typeof ZhlEngineBundle !== 'undefined' && ZhlEngineBundle.ceiling)
    ? (t, gf) => ZhlEngineBundle.ceiling(t, gf) : null;
  if (ceilingFn) {
    const decoStep = 3;
    const decoAscentRate = 9;
    const lastStop = 3;
    let depth = d1;
    for (let guard = 0; guard < 200 && depth > 0; guard++) {
      const ceil = ceilingFn(tissues, gfLow);
      if (ceil <= 0) {
        tissues = saturateLinear(tissues, depth, 0, depth / decoAscentRate, dive1Gas.fN2, dive1Gas.fHe || 0);
        break;
      }
      const stopDepth = Math.max(lastStop, Math.ceil(ceil / decoStep) * decoStep);
      if (depth > stopDepth) {
        const ascMin = (depth - stopDepth) / decoAscentRate;
        tissues = saturateLinear(tissues, depth, stopDepth, ascMin, dive1Gas.fN2, dive1Gas.fHe || 0);
        depth = stopDepth;
      }
      tissues = saturate(tissues, depth, 1, dive1Gas.fN2, dive1Gas.fHe || 0);
      if (depth <= lastStop) {
        tissues = saturateLinear(tissues, depth, 0, depth / decoAscentRate, dive1Gas.fN2, dive1Gas.fHe || 0);
        break;
      }
      depth = Math.max(0, depth - decoStep);
    }
  }

  const tolTension = ZHL16C.map(([ht, a, b]) => gfHigh * a + altSurfaceP * (1 - gfHigh + gfHigh / b));
  const surfP = altSurfaceP;
  const pN2surf = (surfP - WATER_VAPOR) * surfGas.fN2;
  const pHesurf = (surfP - WATER_VAPOR) * (surfGas.fHe || 0);
  const satSurface = (t0, minutes) => ZHL16C.map((c, i) => ({
    pN2: schreiner(t0[i].pN2, pN2surf, c[0], minutes),
    pHe: schreiner(t0[i].pHe, pHesurf, ZHL16C_HE_HT[i], minutes),
  }));

  const simulateDive2 = (t0) => {
    let t = t0.map(c => ({ pN2: c.pN2, pHe: c.pHe || 0 }));
    const descTime2 = d2 / descentRate;
    t = saturateLinear(t, 0, d2, descTime2, dive2Gas.fN2, dive2Gas.fHe || 0);
    const btAtDepth2 = Math.max(0, bt2 - descTime2);
    t = saturate(t, d2, btAtDepth2, dive2Gas.fN2, dive2Gas.fHe || 0);
    return t;
  };

  const allWithin = (t) => t.every((c, i) => (c.pN2 + (c.pHe || 0)) <= tolTension[i] + 1e-9);

  let minSI = 0;
  let siCapped = false;
  let driver = -1;
  if (!allWithin(simulateDive2(tissues))) {
    let found = false;
    for (let si = 1; si <= 720; si++) {
      const afterSI = satSurface(tissues, si);
      if (allWithin(simulateDive2(afterSI))) { minSI = si; found = true; break; }
    }
    if (!found) { minSI = 720; siCapped = true; }
    const tCheck = simulateDive2(satSurface(tissues, minSI));
    let worst = 0, worstIdx = 0;
    ZHL16C.forEach((c, i) => {
      const over = (tCheck[i].pN2 + (tCheck[i].pHe || 0)) - tolTension[i];
      if (over > worst) { worst = over; worstIdx = i; }
    });
    driver = worstIdx;
  }

  const recSI = siCapped ? null : Math.ceil((minSI * 1.5) / 5) * 5;
  return { minSI, recSI, siCapped, driver };
}

function calcSurfInt(prefix) {
  const P = prefix || 'si';
  const gid = (suffix) => document.getElementById(P + suffix);
  const d1 = parseFloat(gid('D1Depth')?.value) || 30;
  const bt1 = parseFloat(gid('D1BT')?.value) || 25;
  const d2 = parseFloat(gid('D2Depth')?.value) || 30;
  const bt2 = parseFloat(gid('D2BT')?.value) || 25;
  const gfLow = (parseFloat(gid('GfLow')?.value) || 30) / 100;
  const gfHigh = (typeof mGF !== 'undefined' && Number.isFinite(mGF.high) ? mGF.high : 85) / 100;
  const dU = units === 'metric';
  const conv = dU ? 1 : 3.28084;
  const uLbl = dU ? 'm' : 'ft';
  const fmtD = (m) => Math.round(m * conv) + ' ' + uLbl;

  // Update slider displays
  const setD = (suffix, txt) => { const el = gid(suffix); if (el) el.textContent = txt; };
  setD('D1DepthDisplay', fmtD(d1));
  setD('D1BTDisplay', bt1 + ' min');
  setD('D2DepthDisplay', fmtD(d2));
  setD('D2BTDisplay', bt2 + ' min');

  const descentRate = 18; // m/min (per spec)
  const botFracs = typeof getBottomGasFractions === 'function' ? getBottomGasFractions() : null;
  const dive1Gas = botFracs
    ? { fN2: botFracs.fN2, fHe: botFracs.fHe || 0 }
    : { fN2: FN2_AIR, fHe: 0 };
  const d2O2El = document.getElementById(P + 'D2O2');
  const d2HeEl = document.getElementById(P + 'D2He');
  const d2O2Pct = d2O2El ? parseFloat(d2O2El.value) : NaN;
  const d2HePct = d2HeEl ? parseFloat(d2HeEl.value) : 0;

  const errEl = document.getElementById(P + 'D2GasErr');
  if (Number.isFinite(d2O2Pct) && Number.isFinite(d2HePct) && d2O2Pct + d2HePct > 100) {
    if (errEl) { errEl.textContent = 'O₂ + He > 100% — impossible mix'; errEl.style.display = 'block'; }
    return;
  }
  if (errEl) errEl.style.display = 'none';

  let dive2Gas;
  if (Number.isFinite(d2O2Pct) && d2O2Pct >= 21 && d2O2Pct <= 100) {
    const fO2 = d2O2Pct / 100;
    const fHe = Math.max(0, Math.min((100 - d2O2Pct) / 100, (d2HePct || 0) / 100));
    dive2Gas = { fO2, fN2: Math.max(0, 1 - fO2 - fHe), fHe };
  } else {
    dive2Gas = dive1Gas;
  }
  const surfGas = { fN2: FN2_AIR, fHe: 0 };

  const result = computeSurfIntervalCore({
    d1, bt1, d2, bt2, gfLowPct: gfLow * 100, gfHighPct: gfHigh * 100,
    dive1Gas, dive2Gas, surfGas, descentRate,
  });
  const { minSI, recSI, siCapped, driver } = result;
  const chartSI = recSI != null ? recSI : minSI;
  const chartT = (() => {
    const surfP = altSurfaceP;
    const pN2surf = (surfP - WATER_VAPOR) * surfGas.fN2;
    const pHesurf = (surfP - WATER_VAPOR) * (surfGas.fHe || 0);
    let tissues = initTissues();
    const descTime = d1 / descentRate;
    const btAtDepth = Math.max(0, bt1 - descTime);
    tissues = saturateLinear(tissues, 0, d1, descTime, dive1Gas.fN2, dive1Gas.fHe || 0);
    tissues = saturate(tissues, d1, btAtDepth, dive1Gas.fN2, dive1Gas.fHe || 0);
    const satSurface = (t0, minutes) => ZHL16C.map((c, i) => ({
      pN2: schreiner(t0[i].pN2, pN2surf, c[0], minutes),
      pHe: schreiner(t0[i].pHe, pHesurf, ZHL16C_HE_HT[i], minutes),
    }));
    return satSurface(tissues, chartSI);
  })();
  const tolTension = ZHL16C.map(([ht, a, b]) => gfHigh * a + altSurfaceP * (1 - gfHigh + gfHigh / b));
  const fmtHM = (mins) => {
    const h = Math.floor(mins / 60), m = Math.round(mins % 60);
    return h > 0 ? `${h}h ${String(m).padStart(2,'0')}m` : `${m} min`;
  };

  if (gid('MinResult')) {
    gid('MinResult').textContent = minSI === 0 ? 'None' : (siCapped ? '>12h (cap)' : fmtHM(minSI));
    if (siCapped) gid('MinResult').style.color = 'var(--orange)';
    else if (gid('MinResult').style) gid('MinResult').style.color = 'var(--accent)';
  }
  if (gid('RecResult')) gid('RecResult').textContent = recSI == null ? '—' : (recSI === 0 ? 'None' : fmtHM(recSI));
  if (gid('DriverResult')) gid('DriverResult').textContent = driver < 0
    ? 'No off-gassing required'
    : `Compartment ${driver + 1} (${ZHL16C[driver][0]} min t½)`;

  // ── Reverse profile warning ──
  const warnEl = gid('ReverseWarn');
  if (warnEl && d2 > d1) {
    warnEl.style.display = 'block';
    warnEl.style.borderLeft = '3px solid var(--orange)';
    warnEl.innerHTML = `<strong>⚠ Reverse profile.</strong> Dive 2 (${fmtD(d2)}) is deeper than Dive 1 (${fmtD(d1)}). Add extra surface interval and consider a more conservative plan.`;
  } else if (warnEl) {
    warnEl.style.display = 'none';
  }

  // ── Tissue loading chart at recommended SI ──
  const chart = gid('TissueChart');
  if (chart) {
    chart.innerHTML = '';
    ZHL16C.forEach((c, i) => {
      const tension = chartT[i].pN2 + (chartT[i].pHe || 0);
      const pct = Math.max(0, Math.min(120, Math.round((tension / tolTension[i]) * 100)));
      const barCol = pct >= 100 ? 'var(--red)' : pct >= 85 ? 'var(--yellow)' : 'var(--green)';
      chart.innerHTML += `<div style="display:flex;align-items:center;gap:8px;">
        <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);width:42px;flex-shrink:0;">C${i+1}</span>
        <div style="flex:1;background:var(--card2);border-radius:3px;height:12px;overflow:hidden;">
          <div style="width:${Math.min(100,pct)}%;height:100%;background:${barCol};"></div>
        </div>
        <span style="font-family:'JetBrains Mono',monospace;font-size:9px;color:${barCol};width:38px;text-align:right;flex-shrink:0;">${pct}%</span>
      </div>`;
    });
  }
}
// ── Reusable Surface Interval panel for REC/TEC results areas ──
// Builds a compact collapsible panel with prefixed input/output IDs so the
// calcSurfInt() engine can drive it without colliding with the Tools tab ('si').
// preDepthM / preBtMin pre-fill Dive 1 from the just-calculated dive.
function renderSurfIntPanel(containerId, prefix, preDepthM, preBtMin) {
  const c = document.getElementById(containerId);
  if (!c) return;
  const P = prefix;
  const dU = units === 'metric';
  const conv = dU ? 1 : 3.28084;
  const uLbl = dU ? 'm' : 'ft';
  // Clamp pre-fill values to the slider ranges
  const d1Init = Math.round(Math.max(5, Math.min(60, preDepthM || 30)));
  const btInit = Math.round(Math.max(5, Math.min(120, preBtMin || 25)));
  const fmtD = (m) => Math.round(m * conv) + ' ' + uLbl;
  c.innerHTML = `
    <div class="card" style="margin-top:16px;padding:0;overflow:hidden;">
      <button type="button" onclick="toggleSurfIntPanel('${P}')" id="${P}Toggle"
        style="width:100%;display:flex;justify-content:space-between;align-items:center;background:var(--card2);border:none;border-radius:10px;padding:12px 16px;cursor:pointer;color:var(--text);font-family:'JetBrains Mono',monospace;font-size:12px;font-weight:600;letter-spacing:0.5px;">
        <span>Surface Interval</span><span id="${P}Caret" style="color:var(--accent);">▾</span>
      </button>
      <div id="${P}Body" style="display:none;padding:14px 16px;">
        <div class="info-box" style="margin-top:0;">Minimum surface interval before a second dive, using the Bühlmann ZH-L16C tissue model. Dive 1 is pre-filled from your current plan.</div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;">
          <div style="flex:1;min-width:150px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
              <label style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);">Dive 1 Depth</label>
              <span id="${P}D1DepthDisplay" style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--accent);line-height:1;">${fmtD(d1Init)}</span>
            </div>
            <div class="slider-wrap">
              <input type="range" id="${P}D1Depth" class="lsp-slider" min="5" max="60" value="${d1Init}" step="1" oninput="updateSliderFill(this);calcSurfInt('${P}')">
            </div>
          </div>
          <div style="flex:1;min-width:150px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
              <label style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);">Dive 1 Bottom Time</label>
              <span id="${P}D1BTDisplay" style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--accent);line-height:1;">${btInit} min</span>
            </div>
            <div class="slider-wrap">
              <input type="range" id="${P}D1BT" class="lsp-slider" min="5" max="120" value="${btInit}" step="1" oninput="updateSliderFill(this);calcSurfInt('${P}')">
            </div>
          </div>
        </div>
        <div style="display:flex;gap:16px;flex-wrap:wrap;">
          <div style="flex:1;min-width:150px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
              <label style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);">Dive 2 Planned Depth</label>
              <span id="${P}D2DepthDisplay" style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--accent);line-height:1;">${fmtD(d1Init)}</span>
            </div>
            <div class="slider-wrap">
              <input type="range" id="${P}D2Depth" class="lsp-slider" min="5" max="60" value="${d1Init}" step="1" oninput="updateSliderFill(this);calcSurfInt('${P}')">
            </div>
          </div>
          <div style="flex:1;min-width:150px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
              <label style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);">Dive 2 Bottom Time</label>
              <span id="${P}D2BTDisplay" style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--accent);line-height:1;">${btInit} min</span>
            </div>
            <div class="slider-wrap">
              <input type="range" id="${P}D2BT" class="lsp-slider" min="5" max="120" value="${btInit}" step="1" oninput="updateSliderFill(this);calcSurfInt('${P}')">
            </div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:14px;">
          <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);">GF Lo:</span>
          <select id="${P}GfLow" onchange="calcSurfInt('${P}');if(typeof appSettings!=='undefined')appSettings.save(false)" style="padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;">
            <option value="20">20</option><option value="25">25</option><option value="30" selected>30</option>
            <option value="35">35</option><option value="40">40</option><option value="45">45</option><option value="50">50</option>
          </select>
        </div>
        <div style="margin-bottom:14px;">
          <button type="button" onclick="toggleD2Gas('${P}')" id="${P}D2GasToggle"
            style="display:flex;align-items:center;gap:7px;width:100%;background:none;
                   border:1px solid var(--border);border-radius:6px;padding:7px 12px;
                   cursor:pointer;color:var(--muted);font-family:inherit;font-size:11px;
                   font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
                   text-align:left;transition:all .2s;">
            <span id="${P}D2GasChevron" style="transition:transform .25s;">▶</span>
            <span>Dive 2 Gas Override</span>
            <span id="${P}D2GasSummary"
              style="margin-left:auto;font-size:10px;font-weight:400;letter-spacing:0;
                     text-transform:none;opacity:.7;color:var(--accent);">
            </span>
          </button>
          <div id="${P}D2GasBody" style="display:none;padding:10px 4px 0;">
            <div class="info-box" style="margin-top:0;margin-bottom:10px;">
              Optional. Leave blank to use the same gas as Dive 1 (common case).
              Set O₂% to override — e.g. switch to EAN32 after a trimix Dive 1.
            </div>
            <div style="display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;">
              <div class="field" style="flex:1;min-width:80px;">
                <label>Dive 2 O₂ %</label>
                <input type="number" id="${P}D2O2" min="21" max="100" step="1"
                  placeholder="inherit"
                  oninput="updateD2GasSummary('${P}');calcSurfInt('${P}')"/>
              </div>
              <div class="field" style="flex:1;min-width:80px;">
                <label>Dive 2 He %</label>
                <input type="number" id="${P}D2He" min="0" max="79" step="1" value="0"
                  oninput="updateD2GasSummary('${P}');calcSurfInt('${P}')"/>
              </div>
            </div>
            <div id="${P}D2GasErr"
              style="display:none;margin-top:6px;font-family:'JetBrains Mono',monospace;
                     font-size:10px;color:var(--red);">
            </div>
          </div>
        </div>
        <div class="stats" style="grid-template-columns:repeat(2,1fr);margin-top:4px;">
          <div class="stat"><div class="stat-val" id="${P}MinResult" style="color:var(--accent);">—</div><div class="stat-lbl">Minimum SI</div></div>
          <div class="stat"><div class="stat-val" id="${P}RecResult" style="color:var(--green);">—</div><div class="stat-lbl">Recommended (×1.5)</div></div>
          <div class="stat" style="grid-column:1/-1;"><div class="stat-val" id="${P}DriverResult" style="font-size:13px;color:var(--muted);">—</div><div class="stat-lbl">Controlling Compartment</div></div>
        </div>
        <div id="${P}ReverseWarn" style="display:none;margin-top:12px;" class="info-box"></div>
        <div style="margin-top:14px;">
          <div style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:8px;">Tissue Loading at Recommended SI</div>
          <div id="${P}TissueChart" style="display:flex;flex-direction:column;gap:3px;"></div>
        </div>
      </div>
    </div>`;
  c.style.display = 'block';
}
function toggleSurfIntPanel(prefix) {
  const body = document.getElementById(prefix + 'Body');
  const caret = document.getElementById(prefix + 'Caret');
  if (!body) return;
  const open = body.style.display === 'none';
  body.style.display = open ? 'block' : 'none';
  if (caret) caret.textContent = open ? '▴' : '▾';
  if (open) {
    document.querySelectorAll('#' + prefix + 'Body .lsp-slider').forEach(s => updateSliderFill(s));
    calcSurfInt(prefix);
  }
}

function toggleD2Gas(prefix) {
  const body = document.getElementById(prefix + 'D2GasBody');
  const chevron = document.getElementById(prefix + 'D2GasChevron');
  if (!body) return;
  const open = body.style.display === 'none';
  body.style.display = open ? 'block' : 'none';
  if (chevron) chevron.style.transform = open ? 'rotate(90deg)' : '';
}

function updateD2GasSummary(prefix) {
  const o2El = document.getElementById(prefix + 'D2O2');
  const heEl = document.getElementById(prefix + 'D2He');
  const sumEl = document.getElementById(prefix + 'D2GasSummary');
  if (!sumEl) return;
  const o2 = o2El ? parseFloat(o2El.value) : NaN;
  const he = heEl ? parseFloat(heEl.value) : 0;
  if (!Number.isFinite(o2) || o2 < 21) { sumEl.textContent = ''; return; }
  if (Number.isFinite(he) && he > 0) {
    sumEl.textContent = `Tx${Math.round(o2)}/${Math.round(he)}`;
  } else {
    sumEl.textContent = o2 === 21 ? 'Air' : `EAN${Math.round(o2)}`;
  }
}
