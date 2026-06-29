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
function calcSurfInt(prefix) {
  const P = prefix || 'si';
  const gid = (suffix) => document.getElementById(P + suffix);
  const d1 = parseFloat(gid('D1Depth')?.value) || 30;
  const bt1 = parseFloat(gid('D1BT')?.value) || 25;
  const d2 = parseFloat(gid('D2Depth')?.value) || 30;
  const bt2 = parseFloat(gid('D2BT')?.value) || 25;
  const gfLow = (parseFloat(gid('GfLow')?.value) || 30) / 100;
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
  const fN2 = botFracs ? botFracs.fN2 : FN2_AIR;

  // ── Simulate Dive 1: descent, bottom, then deco ascent to surface ──
  let tissues = initTissues();
  const descTime = d1 / descentRate;
  tissues = saturateLinear(tissues, 0, d1, descTime, fN2, 0);
  const btAtDepth = Math.max(0, bt1 - descTime);
  tissues = saturate(tissues, d1, btAtDepth, fN2, 0);
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
        const ascentT = depth / decoAscentRate;
        tissues = saturateLinear(tissues, depth, 0, ascentT, fN2, 0);
        break;
      }
      const stopDepth = Math.max(lastStop, Math.ceil(ceil / decoStep) * decoStep);
      if (depth > stopDepth) {
        const ascentT = (depth - stopDepth) / decoAscentRate;
        tissues = saturateLinear(tissues, depth, stopDepth, ascentT, fN2, 0);
        depth = stopDepth;
      }
      tissues = saturate(tissues, depth, 1, fN2, 0);
      if (depth <= lastStop) {
        const ascentT = depth / decoAscentRate;
        tissues = saturateLinear(tissues, depth, 0, ascentT, fN2, 0);
        break;
      }
      depth = Math.max(0, depth - decoStep);
    }
  }

  // ── Tolerated tissue tension at the SURFACE, using GF-Lo ──
  // The surface interval must be long enough that the diver can safely
  // surface (ceiling = 0m). Using pAmbD2 would incorrectly allow deeper
  // Dive 2 entries to bypass the off-gassing check entirely.
  const tolTension = ZHL16C.map(([ht, a, b]) => gfLow * a + altSurfaceP * (1 - gfLow + gfLow / b));

  // ── Off-gas at surface (air) and find minimum SI ──
  const surfP = altSurfaceP;
  const pN2surf = (surfP - WATER_VAPOR) * fN2;
  // Helium ignored on air dives (pHe ~ 0). Use N2-only saturation at surface.
  const satSurface = (t0, minutes) => ZHL16C.map((c, i) => ({
    pN2: schreiner(t0[i].pN2, pN2surf, c[0], minutes),
    pHe: schreiner(t0[i].pHe, 0, ZHL16C_HE_HT[i], minutes),
  }));

  const simulateDive2 = (t0) => {
    let t = t0.map(c => ({ pN2: c.pN2, pHe: c.pHe || 0 }));
    const descTime2 = d2 / descentRate;
    t = saturateLinear(t, 0, d2, descTime2, fN2, 0);
    const btAtDepth2 = Math.max(0, bt2 - descTime2);
    t = saturate(t, d2, btAtDepth2, fN2, 0);
    return t;
  };

  const allWithin = (t) => t.every((c, i) => (c.pN2 + (c.pHe || 0)) <= tolTension[i] + 1e-9);

  let minSI = 0;
  let driver = -1;
  if (!allWithin(simulateDive2(tissues))) {
    let found = false;
    for (let si = 1; si <= 720; si++) {
      const afterSI = satSurface(tissues, si);
      if (allWithin(simulateDive2(afterSI))) { minSI = si; found = true; break; }
    }
    if (!found) minSI = 720;
    const tCheck = simulateDive2(satSurface(tissues, minSI));
    let worst = 0, worstIdx = 0;
    ZHL16C.forEach((c, i) => {
      const over = (tCheck[i].pN2 + (tCheck[i].pHe || 0)) - tolTension[i];
      if (over > worst) { worst = over; worstIdx = i; }
    });
    driver = worstIdx;
  }

  const recSI = Math.ceil((minSI * 1.5) / 5) * 5;
  const fmtHM = (mins) => {
    const h = Math.floor(mins / 60), m = Math.round(mins % 60);
    return h > 0 ? `${h}h ${String(m).padStart(2,'0')}m` : `${m} min`;
  };

  if (gid('MinResult')) gid('MinResult').textContent = minSI === 0 ? 'None' : fmtHM(minSI);
  if (gid('RecResult')) gid('RecResult').textContent = recSI === 0 ? 'None' : fmtHM(recSI);
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
  const chartT = satSurface(tissues, recSI);
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
        <div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center;">
          <div style="flex:1;min-width:150px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;">
              <label style="font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);">Dive 2 Planned Depth</label>
              <span id="${P}D2DepthDisplay" style="font-family:'Bebas Neue',sans-serif;font-size:22px;color:var(--accent);line-height:1;">${fmtD(d1Init)}</span>
            </div>
            <div class="slider-wrap">
              <input type="range" id="${P}D2Depth" class="lsp-slider" min="5" max="60" value="${d1Init}" step="1" oninput="updateSliderFill(this);calcSurfInt('${P}')">
            </div>
          </div>
          <div style="display:flex;align-items:center;gap:6px;margin-bottom:14px;">
            <span style="font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);">GF Lo:</span>
            <select id="${P}GfLow" onchange="calcSurfInt('${P}');if(typeof appSettings!=='undefined')appSettings.save(false)" style="padding:4px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:11px;cursor:pointer;">
              <option value="20">20</option><option value="25">25</option><option value="30" selected>30</option>
              <option value="35">35</option><option value="40">40</option><option value="45">45</option><option value="50">50</option>
            </select>
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
