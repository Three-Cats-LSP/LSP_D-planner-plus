// =============================================================================
// LSP D-PLANNER — legacy.js
// Dead code archive — functions removed during cleanup/dead-code refactor
// These were confirmed unused (0 calls, 0 references) in Beta 6.0
// Kept for reference in case any feature is revived in future.
// DO NOT include this file in production builds.
// =============================================================================


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: ftToM
// ────────────────────────────────────────────────────────────────────────────
function ftToM(ft)   { return (ft / 3.28084).toFixed(1); }


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: setNDLUnits
// ────────────────────────────────────────────────────────────────────────────
function setNDLUnits(u)   { setUnits(u); }


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: setMultiUnits
// ────────────────────────────────────────────────────────────────────────────
function setMultiUnits(u) { setUnits(u); }


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: updateGF
// ────────────────────────────────────────────────────────────────────────────
function updateGF() {
  // gfStr now holds "30/70" format — no separate display elements needed
  // Just validate on input via autoSlashGF
}


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: floorPPO2
// ────────────────────────────────────────────────────────────────────────────
function floorPPO2(val) {
  return Math.floor(val * 10) / 10;
}


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: depthFromPressure
// ────────────────────────────────────────────────────────────────────────────
function depthFromPressure(pAmb, settings) {
        return (pAmb - getSurfacePressure(settings)) * getSLP(settings);
    }


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: getEl
// ────────────────────────────────────────────────────────────────────────────
function getEl(id) {
    return document.getElementById(id);
  }


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: switchMultiMode
// ────────────────────────────────────────────────────────────────────────────
function switchMultiMode() {}


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: runMulti
// ────────────────────────────────────────────────────────────────────────────
function runMulti() {
  try {
  const isM = multiUnits === 'metric';
  const isBuh = algo === 'buh';
  const gfHF = mGF.high/100;
  const gfLF = mGF.low/100;

  let tissues = isBuh ? initTissues() : initTissues(); // always track tissues for RNT
  let cardsHTML = '', warnings = '', allSafe = true, anyDeco = false;

  for (let i = 0; i < diveCount; i++) {
    const rawD  = parseFloat(document.getElementById('mD'+i).value)||20;
    const depthM = isM ? rawD : rawD/3.28084;
    const bt    = parseInt(document.getElementById('mBT'+i).value)||20;
    const fN2   = getMultiGasFN2(i);
    const mix   = document.getElementById('mGas'+i)?.value || 'air';
    const fO2   = 1 - fN2;
    const o2pct = Math.round(fO2 * 100);
    const gasName = o2pct === 21 ? 'Air' : `EAN ${o2pct}`;
    const dDisp = isM ? rawD+' m' : rawD+' ft';

    let ndl, ceil=0, sat=0, safe=false, group='';

    if (isBuh) {
      ndl  = buhNDL(depthM, fN2, mGF.low, mGF.high);
      tissues = saturate(tissues, depthM, bt, fN2, 0);
      ceil = ceiling(tissues, gfHF);
      sat  = maxSatPct(tissues, mGF.high);
      safe = bt <= ndl && ceil <= 0;
    } else {
      // Rec mode: use correct PADI nitrox NDL table for selected mix
      const fO2Multi = 1 - fN2;
      const modM = mix !== 'air' ? nitroxMOD(fO2Multi, 1.4) : Infinity;
      const beyondMOD = depthM > modM;
      ndl   = padiNDL(depthM, mix);
      tissues = saturate(tissues, depthM, bt, fN2, 0);
      group = padiGroup(depthM, bt, mix);
      safe  = bt <= ndl && !beyondMOD;
    }

    if (!safe) allSafe = false;
    if (ceil > 0) anyDeco = true;

    const pct = Math.min(100, Math.round((bt/ndl)*100));
    const bc  = pct>=100?'var(--red)':pct>=85?'var(--orange)':pct>=70?'var(--yellow)':'var(--green)';
    const cc  = ceil>0?'c-deco':!safe?'c-dang':pct>=85?'c-warn':'c-ok';
    const icon = ceil>0?'🔴':!safe?'⚠':pct>=85?'⚡':'✓';

    // Nitrox info for rec mode
    const recIsNitrox = !isBuh && mix !== 'air';
    const recFO2 = 1 - fN2;
    const recPpO2 = parseFloat((depthBar(depthM) * recFO2).toFixed(2));
    const recModM = recIsNitrox ? nitroxMOD(recFO2, 1.4) : null;
    const recBeyondMOD = recIsNitrox && depthM > recModM;

    const extraStats = isBuh
      ? `<div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:18px; color:${sat>=100?'var(--red)':sat>=85?'var(--orange)':'var(--green)'};">${sat}%</div><div class="stat-lbl">Max Sat</div></div>
         <div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:18px; color:${ceil>0?'var(--red)':'var(--green)'};">${ceil>0?Math.ceil(ceil)+' m':'0 m'}</div><div class="stat-lbl">Ceiling</div></div>`
      : `<div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:22px;"><span class="group-badge">${group}</span></div><div class="stat-lbl">Group After</div></div>
         ${recIsNitrox ? `<div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:18px;color:${recPpO2>1.4?'var(--red)':'var(--green)'};">${recPpO2.toFixed(2)}</div><div class="stat-lbl">ppO₂</div></div>` : ''}`;

    cardsHTML += `<div class="result-card ${cc}">
      <div class="rc-hdr">
        <div class="rc-title"><span class="dive-num">${i+1}</span>DIVE ${i+1}</div>
        <span>${icon}</span>
      </div>
      <div class="stats" style="margin-top:0;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:8px;">
        <div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:18px;">${dDisp}</div><div class="stat-lbl">Depth</div></div>
        <div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:18px;">${bt}</div><div class="stat-lbl">BT (min)</div></div>
        <div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:18px;color:${ndl>=400?'var(--green)':'var(--accent)'};">${ndl>=400?'400+':ndl}</div><div class="stat-lbl">NDL (min)</div></div>
        ${(isBuh || recIsNitrox) ? `<div class="stat" style="padding:10px;"><div class="stat-val" style="font-size:15px;color:var(--muted);">${gasName}</div><div class="stat-lbl">Gas</div></div>` : ''}
        ${extraStats}
      </div>
      <div style="margin-top:10px;">
        <div style="display:flex;justify-content:space-between;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--muted);margin-bottom:4px;letter-spacing:1px;"><span>NDL USAGE${recIsNitrox?' · '+gasName:''}</span><span>${pct}%</span></div>
        <div class="bar-wrap"><div class="bar-fill" style="width:${pct}%;background:${bc};"></div></div>
      </div>
      ${recBeyondMOD ? `<div class="alert dang" style="margin-top:8px;padding:8px 12px;font-size:11px;"><span>⚠</span><div><strong>BEYOND MOD.</strong> Depth exceeds ${gasName} MOD of ${isM?recModM+' m':Math.floor(recModM*3.28084)+' ft'}.</div></div>` : ''}
      ${ceil>0?`<div class="alert deco" style="margin-top:8px;padding:8px 12px;font-size:11px;"><span>🔴</span><div>Deco ceiling ${Math.ceil(ceil)} m after this dive.</div></div>`:''}
      ${!safe&&ceil<=0&&!recBeyondMOD?`<div class="alert" style="margin-top:8px;padding:8px 12px;font-size:11px;background:#FF4433;border-color:#cc2200;color:#fff;font-weight:700;"><span>⚠</span><div>NDL exceeded by ${bt-ndl} min.</div></div>`:''}
    </div>`;

    // Surface interval strip
    if (i < diveCount-1) {
      const siMins = parseInt(document.getElementById('mSI'+i).value)||60;
      const siHrs  = Math.floor(siMins/60);
      const siRem  = siMins%60;
      const siStr  = siHrs>0?`${siHrs}h${siRem>0?' '+siRem+'m':''}`:`${siMins} min`;

      let clearText = '';
      let recommendedSI = '';
      
      if (isBuh) {
        tissues = saturate(tissues, 0, siMins, fN2, 0);
        const ceilAfter = ceiling(tissues, gfHF);
        clearText = ceilAfter>0.5
          ? `<span style="color:var(--orange);">⚠ Ceiling still ${Math.ceil(ceilAfter)} m</span>`
          : `<span style="color:var(--green);">✓ Cleared</span>`;
      } else {
        // Rec mode — calculate recommended SI based on PADI RDP pressure groups
        tissues = saturate(tissues, 0, siMins, fN2, 0);
        
        // Get current dive pressure group after this dive
        const currentGroup = group;
        
        // Get next dive depth and mix if available
        const nextDepthVal = i < diveCount-1 ? parseFloat(document.getElementById('mD'+(i+1)).value)||20 : 20;
        const nextDepthM = isM ? nextDepthVal : nextDepthVal/3.28084;
        const nextMix = document.getElementById('mGas'+(i+1))?.value || 'air';
        const nextNDL = padiNDL(nextDepthM, nextMix);
        
        // PADI RDP: given a pressure group and desired next dive depth,
        // find minimum SI so that Adjusted No-Decompression Limit for next dive is safe
        // Approximation: each SI minute reduces pressure group slightly
        // Conservative estimate: need SI such that residual nitrogen + new dive doesn't exceed NDL
        
        // Pressure group off-gas rates (min to drop one group, approximate)
        const groupOffGasTime = {
          'A': 10,  'B': 12,  'C': 15,  'D': 18,  'E': 22,  'F': 25,  'G': 30,
          'H': 35,  'I': 40,  'J': 50,  'K': 60,  'L': 70,  'M': 80,  'N': 100,
          'O': 110, 'P': 130, 'Q': 150, 'R': 170, 'S': 200, 'T': 240, 'U': 300,
          'V': 360, 'W': 450, 'X': 600, 'Y': 800, 'Z': 1200
        };
        
        // Simplified algorithm: for given next depth, recommend SI to get to a safe pressure group
        let minSI = 10; // absolute minimum
        if (currentGroup && currentGroup !== 'Z') {
          // For deeper next dives, need to off-gas more (longer SI)
          const depthPenalty = nextDepthM > 30 ? 25 : nextDepthM > 21 ? 15 : nextDepthM > 12 ? 5 : 0;
          const groupIndex = currentGroup.charCodeAt(0) - 65; // A=0...Z=25
          
          // Conservative: assume we need to drop at least 2 groups before next dive
          // Each group drop takes roughly groupOffGasTime[group] minutes
          if (groupIndex >= 2) {
            minSI = (groupOffGasTime[currentGroup] || 10) + depthPenalty;
          } else {
            minSI = 10 + depthPenalty;
          }
          
          // Cap at reasonable maximum for this scenario
          minSI = Math.min(minSI, 600);
        }
        
        const siAdequate = siMins >= minSI;
        const siStatus = siAdequate 
          ? `<span style="color:var(--green);">✓ Adequate (${minSI} min recommended for ${Math.round(nextDepthM)}m dive)</span>`
          : `<span style="color:var(--orange);">⚠ Recommend ${minSI - siMins} more min (total ${minSI} min)</span>`;
        
        clearText = siStatus;
        recommendedSI = `<div style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--muted);">
          After dive: <strong style="color:var(--accent);">Group ${currentGroup}</strong> · 
          Next dive depth: <strong>${Math.round(nextDepthM)}m</strong> · 
          Recommended SI: <strong>${minSI} min</strong>
        </div>`;
      }

      cardsHTML += `<div class="si-strip">
        <span>⏱</span>
        <strong style="color:var(--text);">SI: ${siStr}</strong>
        <span style="margin-left:auto;">${clearText}</span>
        ${recommendedSI}
      </div>`;
    }
  }

  if (allSafe)  warnings += `<div class="alert ok"><span>✓</span><div><strong>ALL DIVES WITHIN LIMITS.</strong> Perform 3 min safety stop at 5 m on every dive.</div></div>`;
  if (anyDeco)  warnings += `<div class="alert deco"><span>🔴</span><div><strong>DECOMPRESSION OBLIGATION</strong> on one or more dives. Mandatory stops must not be skipped.</div></div>`;
  if (diveCount>=3) warnings += `<div class="alert warn"><span>⚡</span><div><strong>${diveCount}-DIVE DAY:</strong> Cumulative nitrogen load is significant. Always dive deepest first and allow full surface intervals.</div></div>`;

  const _mc = document.getElementById('multiCards'); if(_mc) _mc.innerHTML = cardsHTML;
  const _mw = document.getElementById('multiWarnings'); if(_mw) _mw.innerHTML = warnings;
  const _mr2 = document.getElementById('multiResult'); if(_mr2) _mr2.style.display = 'block';
  } catch(err) {
    const _mce = document.getElementById('multiCards'); if(_mce) _mce.innerHTML = `<div class="alert dang"><span>⚠</span><div><strong>Error:</strong> ${err.message}</div></div>`;
    const _mr3 = document.getElementById('multiResult'); if(_mr3) _mr3.style.display = 'block';
  }
}


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: buildBuhRef
// ────────────────────────────────────────────────────────────────────────────
(function buildBuhRef() {
  const tbody = document.getElementById('buhRefBody');
  if (!tbody) return;
  const speeds = ['Fast','Fast','Fast','Fast','Med','Med','Med','Med','Slow','Slow','Slow','Slow','V.Slow','V.Slow','V.Slow','V.Slow'];
  ZHL16C.forEach(([ht,a,b],i) => {
    tbody.innerHTML += `<tr><td>${i+1}</td><td>${ht}</td><td>${a}</td><td>${b}</td><td>${speeds[i]}</td></tr>`;
  });
})


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: initPWA
// ────────────────────────────────────────────────────────────────────────────
(function initPWA() {
  // Generate SVG icon as data URL
  const iconSVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
    <rect width="512" height="512" rx="100" fill="#000000"/>
    <rect width="512" height="512" rx="100" fill="url(#bg)"/>
    <defs>
      <radialGradient id="bg" cx="30%" cy="70%" r="80%">
        <stop offset="0%" stop-color="#0d4080"/>
        <stop offset="100%" stop-color="#000000"/>
      </radialGradient>
    </defs>
    <!-- Diver silhouette -->
    <text x="256" y="300" font-size="220" text-anchor="middle" fill="#00d9ff" opacity="0.95">🤿</text>
    <!-- App name -->
    <text x="256" y="390" font-family="Arial,sans-serif" font-size="48" font-weight="bold"
      text-anchor="middle" fill="#00d9ff" letter-spacing="4">DIVE</text>
    <text x="256" y="440" font-family="Arial,sans-serif" font-size="36"
      text-anchor="middle" fill="#7ac8e0" letter-spacing="3">PLANNER</text>
    <!-- Glowing ring -->
    <circle cx="256" cy="256" r="230" fill="none" stroke="#00d9ff" stroke-width="6" opacity="0.2"/>
  </svg>`;

  const iconURL = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(iconSVG)));

  // Set favicon and apple touch icon
  document.getElementById('faviconSVG').href = iconURL;
  document.getElementById('appleTouchIcon').href = iconURL;

  // Inject Web App Manifest as blob URL
  const manifest = {
    name: 'LSP D-Planner',
    short_name: 'Dive Planner',
    description: 'Recreational NDL tables and Bühlmann ZH-L16C decompression planner',
    start_url: '.',
    display: 'standalone',
    orientation: 'portrait-primary',
    background_color: '#030c18',
    theme_color: '#030c18',
    categories: ['sports', 'utilities'],
    icons: [
      { src: iconURL, sizes: '192x192', type: 'image/svg+xml', purpose: 'any maskable' },
      { src: iconURL, sizes: '512x512', type: 'image/svg+xml', purpose: 'any maskable' }
    ]
  };

  const manifestBlob = new Blob([JSON.stringify(manifest)], { type: 'application/json' });
  document.getElementById('pwaManifest').href = URL.createObjectURL(manifestBlob);

  // Register service worker for offline support
  if ('serviceWorker' in navigator) {
    const swCode = `
const CACHE = 'dive-planner-v1';
const ASSETS = [self.location.href];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  e.respondWith(
    caches.match(e.request).then(r => r || fetch(e.request).catch(() =>
      caches.match(self.location.href)
    ))
  );
});`;

    const swBlob = new Blob([swCode], { type: 'application/javascript' });
    const swURL  = URL.createObjectURL(swBlob);
    navigator.serviceWorker.register(swURL, { scope: './' })
      .then(() => console.log('[PWA] Service worker registered'))
      .catch(e => console.warn('[PWA] SW registration failed:', e));
  }

  // Show install prompt banner
  let deferredPrompt = null;
  window.addEventListener('beforeinstallprompt', e => {
    e.preventDefault();
    deferredPrompt = e;
    showInstallBanner();
  });

  function showInstallBanner() {
    if (document.getElementById('installBanner')) return;
    const banner = document.createElement('div');
    banner.id = 'installBanner';
    banner.innerHTML = `
      <div style="
        position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
        background: var(--surface);
        border:1px solid var(--border-hi); border-radius:12px;
        padding:14px 20px; display:flex; align-items:center; gap:14px;
        z-index:9999; box-shadow:0 8px 32px rgba(0,0,0,0.3);
        font-family:'Outfit',sans-serif; max-width:340px; width:90%;
      ">
        <span style="font-size:28px;">🤿</span>
        <div style="flex:1;">
          <div style="color: var(--text); font-weight:600;font-size:14px;">Install Dive Planner</div>
          <div style="color: var(--muted); font-size:12px;margin-top:2px;">Add to home screen for offline use</div>
        </div>
        <button onclick="installPWA()" style="
          background:linear-gradient(135deg,#00d9ff,#00b8a0);
          border:none; border-radius:8px; padding:8px 14px;
          color:#030c18; font-weight:700; font-size:12px; cursor:pointer;
          font-family:'Outfit',sans-serif; letter-spacing:0.5px;
        ">INSTALL</button>
        <button onclick="this.closest('#installBanner').remove()" style="
          background:none; border:none; color: var(--muted); font-size:20px;
          cursor:pointer; padding:0; line-height:1;
        ">×</button>
      </div>`;
    document.body.appendChild(banner);
  }

  // Redirected to unified exportTXT — kept for backward compat
  window.exportDecoSchedule = function() { exportTXT('deco'); };

  window.installPWA = async function() {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    document.getElementById('installBanner')?.remove();
  };

  // iOS — show manual instructions since iOS doesn't support beforeinstallprompt
  const isIOS = /iphone|ipad|ipod/i.test(navigator.userAgent) && !window.MSStream;
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
  if (isIOS && !isStandalone) {
    setTimeout(() => {
      const banner = document.createElement('div');
      banner.id = 'installBanner';
      banner.innerHTML = `
        <div style="
          position:fixed; bottom:20px; left:50%; transform:translateX(-50%);
          background: var(--surface);
          border:1px solid var(--border-hi); border-radius:12px;
          padding:14px 20px; display:flex; align-items:center; gap:12px;
          z-index:9999; box-shadow:0 8px 32px rgba(0,0,0,0.6);
          font-family:'Outfit',sans-serif; max-width:340px; width:90%;
        ">
          <span style="font-size:24px;">🤿</span>
          <div style="flex:1;">
            <div style="color: var(--text); font-weight:600;font-size:13px;">Install on iPhone</div>
            <div style="color: var(--muted); font-size:11px;margin-top:3px;">Tap <strong style="color: var(--accent);">Share ↑</strong> then <strong style="color: var(--accent);">Add to Home Screen</strong></div>
          </div>
          <button onclick="this.closest('#installBanner').remove()" style="
            background:none; border:none; color: var(--muted); font-size:20px;
            cursor:pointer; padding:0; line-height:1;
          ">×</button>
        </div>`;
      document.body.appendChild(banner);
    }, 2000);
  }
})


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: calcMaxDepth
// ────────────────────────────────────────────────────────────────────────────
function calcMaxDepth() {
  const o2 = parseFloat(document.getElementById('maxDepthO2')?.value) || 0;
  if (!o2 || o2 <= 0 || o2 > 100) return;
  const fO2 = o2 / 100;
  const mod14  = Math.floor((1.4 / fO2 - 1) * 10);
  const mod16  = Math.floor((1.6 / fO2 - 1) * 10);
  const col14 = mod14 < 20 ? 'var(--red)' : mod14 < 30 ? 'var(--yellow)' : 'var(--green)';
  const col16 = mod16 < 20 ? 'var(--red)' : mod16 < 30 ? 'var(--yellow)' : 'var(--yellow)';
  document.getElementById('maxDepth14').textContent  = mod14 + ' m';
  document.getElementById('maxDepth14').style.color  = col14;
  document.getElementById('maxDepth16').textContent  = mod16 + ' m';
  document.getElementById('maxDepth16').style.color  = col16;
  document.getElementById('maxDepth14ft').textContent = Math.floor(mod14 * 3.281) + ' ft';
  document.getElementById('maxDepth16ft').textContent = Math.floor(mod16 * 3.281) + ' ft';
}


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: exportContingencyTXT
// ────────────────────────────────────────────────────────────────────────────
function exportContingencyTXT() { exportTXT('contingency'); }


// ────────────────────────────────────────────────────────────────────────────
// FUNCTION: buildPdfGasCards
// ────────────────────────────────────────────────────────────────────────────
function buildPdfGasCards(gcEl, titleColor) {
  if (!gcEl || gcEl.style.display === 'none') return '';
  const statDivs = Array.from(gcEl.querySelectorAll('div.stat'));
  if (!statDivs.length) return '';
  const tc = titleColor || '#0055aa';
  const titleBg = tc === '#bb2233' ? '#fff0f0' : '#e8f0ff';
  const titleBorder = tc;
  const titleEl = gcEl.querySelector('.card-title');
  const title = titleEl ? titleEl.textContent.trim()
               : (tc === '#bb2233' ? 'Emergency Gas Consumption' : 'Gas Consumption');

  let cards = '';
  statDivs.forEach(card => {
    const val    = card.querySelector('.stat-val')?.textContent?.trim() || '';
    const lbl    = card.querySelector('.stat-lbl')?.textContent?.trim() || '';
    const valEl  = card.querySelector('.stat-val');
    const colStyle = valEl?.style?.color || '';
    const isOver = colStyle.includes('red') || colStyle.includes('255, 0') || colStyle.includes('204, 0');
    const valColor  = isOver ? '#cc0000' : '#111';
    const cardBg    = isOver ? '#fff5f5' : '#f0f4ff';
    const cardBorder = isOver ? '#ffcccc' : '#ccd6f0';
    const barFill  = card.querySelector('div[style*="width:"]');
    const pct      = barFill ? parseFloat(barFill.style.width) || 0 : 0;
    let barColor = '#228833';
    if (pct > 0) {
      const barStyle = barFill?.style?.background || '';
      if (isOver || barStyle.includes('red')) barColor = '#cc0000';
      else if (barStyle.includes('yellow') || barStyle.includes('204,136')) barColor = '#cc8800';
    }
    const allDivs  = Array.from(card.querySelectorAll('div'));
    const availDiv = allDivs.filter(d => d.textContent.trim()).pop();
    const availTxt = availDiv?.textContent?.trim() || '';
    const availColor = availTxt.includes('SHORT') ? '#cc0000' : '#228833';

    cards += `<div style="flex:1;min-width:130px;background:${cardBg};border:1px solid ${cardBorder};border-radius:8px;padding:10px 14px;print-color-adjust:exact;-webkit-print-color-adjust:exact;">` +
      `<div style="font-size:20px;font-weight:900;color:${valColor};font-family:Arial,sans-serif;line-height:1.1;">${val}</div>` +
      `<div style="font-size:10px;letter-spacing:0.5px;text-transform:uppercase;color:#555;margin:3px 0 6px;">${lbl}</div>` +
      (pct > 0 ? `<div style="background:#e0e0e0;border-radius:3px;height:7px;overflow:hidden;margin-bottom:5px;print-color-adjust:exact;-webkit-print-color-adjust:exact;">` +
        `<div style="width:${Math.min(100,pct)}%;height:100%;background:${barColor};border-radius:3px;print-color-adjust:exact;-webkit-print-color-adjust:exact;"></div></div>` : '') +
      (availTxt ? `<div style="font-size:10px;color:${availColor};font-weight:${availTxt.includes('SHORT')?'700':'400'};font-family:monospace;">${availTxt}</div>` : '') +
      `</div>`;
  });

  // Warning cards
  const alertDivs = Array.from(gcEl.querySelectorAll('div.alert, div[class*="dang"], div[class*="warn"]'));
  let warnHTML = '';
  alertDivs.forEach(div => {
    const txt = div.textContent.replace(/^[⚠⚡\s]+/, '').trim();
    if (txt) warnHTML += `<div style="background:#fff0f0;border:1px solid #cc0000;border-left:4px solid #cc0000;border-radius:6px;padding:8px 12px;margin-top:8px;font-size:11px;color:#cc0000;font-weight:700;print-color-adjust:exact;-webkit-print-color-adjust:exact;page-break-inside:avoid;break-inside:avoid;">🚨 ${txt}</div>`;
  });

  const sacLine = gcEl.querySelector('div[style*="muted"]')?.textContent?.trim() || '';

  const titleHtml = `<div class="page-title" style="color:${tc};border-left-color:${titleBorder};">${title}${sacLine ? `<span style="font-size:9px;font-weight:normal;letter-spacing:0.5px;color:#888;text-transform:none;margin-left:10px;">${sacLine}</span>` : ''}</div>`;
  const cardsHtml = `<div style="display:flex;gap:10px;flex-wrap:wrap;">` + cards + `</div>`;
  return titleHtml + cardsHtml + warnHTML;
}

