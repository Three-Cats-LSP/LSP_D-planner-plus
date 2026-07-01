# Three Cats LSP — Diver's Toolkit

> **Three free, open-source apps covering every stage of your dive — plan it, read it, pack for it.**  
> No install required. No Play Store. No account. No ads.

🌐 **Toolkit hub:** https://threecats-lsp.com

---

## 🧰 The Apps

| App | What it does | Live | Repo | Android APK |
|-----|-------------|------|------|-------------|
| **LSP D-Planner+** ← *this app* | Unified decompression planner — OC · CCR · pSCR · Rec · Tec — Bühlmann ZHL-16C, VPM-B, VPM-B/GFS, PADI RDP | [Open](https://threecats-lsp.com/d-planner-plus/) | [GitHub](https://github.com/Three-Cats-LSP/LSP_D-planner-plus) | [Download](https://threecats-lsp.com/d-planner-plus/download.html) |
| **T-Viewer** | Open, read, edit and share exported dive plan TXT / PDF files — syntax-highlighted, font-selectable, PDF.js viewer | [Open](https://threecats-lsp.com/t-viewer/) | [GitHub](https://github.com/Three-Cats-LSP/T-Viewer) | [Download](https://threecats-lsp.com/t-viewer/download.html) |
| **Get In Water** | Dive trip packing checklists — master gear list, per-trip lists, Google sync, TXT / PDF export | [Open](https://threecats-lsp.com/get-in-water/) | [GitHub](https://github.com/Three-Cats-LSP/Get-In-Water) | [Download](https://threecats-lsp.com/get-in-water/download.html) |

All apps run **fully offline** after first load, install as **PWA** from any browser, and are available as direct **Android APKs** (Android 5.0+ / API 21).

---

## 🤿 LSP D-Planner+ — Decompression Planner

> v2.53.07 · MIT · [Live app](https://threecats-lsp.com/d-planner-plus/) · [APK](https://threecats-lsp.com/d-planner-plus/download.html)

The decompression engine at the core of the toolkit. Runs entirely in the browser — no server, no account, no build step.

### ⚗️ Algorithms

| Algorithm | Mode | Notes |
|-----------|------|-------|
| **Bühlmann ZHL-16C + GF** | OC · CCR · pSCR | 16 tissue compartments. GF Low/High via presets (GUE, MultiDeco, Abysner, Subsurface, DiveKit) or custom. Shallow gradient toggle. |
| **VPM-B** | OC · CCR | Varying Permeability Model — bubble nuclei tracking. Conservatism +0 to +5. |
| **VPM-B/GFS** | OC · CCR | VPM-B deep stops + GF High shallow stops. |
| **PADI RDP** | Rec | Recreational NDL tables with pressure group tracking. |

Engines run in an isolated **Web Worker** (ZHL Tier 3 bundle) and a dedicated IIFE bundle (`window.VPMEngine`) — no shared global state, deterministic output.

### 🤿 Features

**Recreational mode**
- NDL tables (PADI RDP + Bühlmann) with GF-adjustable limits
- Multi-dive day planning — residual nitrogen tracking across up to 4 dives
- Surface interval calculator — controlling compartment, tissue loading, reverse-profile warning
- Average depth converter

**Technical mode**
- CCR / pSCR — circuit select, setpoint scheduling, diluent & bailout gases, on-loop Bühlmann + VPM tissue loading, pSCR Baker steady-state loop model
- Full trimix entry (O₂ / He / N₂) for bottom gas and all deco gases
- Travel gas card with auto-switch depth by MOD
- Altitude support — surface pressure presets to 3 000 m, acclimatisation toggle
- Repetitive dive tissue carry (ZHL + VPM bubble state)
- Contingency plans — extended bottom time, went deeper (+3 m / +5 m)
- Surface GF footer metric

**Gas management**
- Gas consumption card — total volume, rule of thirds / half tank, turn pressure, reserve, sufficiency
- Up to 2 deco gas cards + travel gas (metric and imperial)
- SAC-based consumption in litres or cubic feet

**Tools**
- MOD Calculator — ppO₂ limits, altitude-aware
- Best Mix — optimal O₂% for target depth and ppO₂
- END Calculator — narcotic equivalent depth
- EAD Table — nitrox EAD at common depths
- Gas Table — ppO₂, EAD, MOD for common mixes
- Unit Converter — depth, pressure, volume, SAC rate
- CNS / OTU Tracker — standalone oxygen toxicity calculator

**Export**

| Format | Contents |
|--------|----------|
| **Copy** | Plain text plan → clipboard |
| **Deco Slate** | Compact monospaced waterproof format |
| **TXT** | Full plan to Downloads (Android) or browser download |
| **PDF — Dive Plan** | Gas Consumption · Dive Profile · Deco Slate · GF Curve · Tissue Saturation |
| **PDF — Emergency Plan** | Emergency Gas · Ascent Schedule · Dive Profile · GF Curve · Tissue Saturation · Slate |

### 📱 Install

| Platform | Steps |
|----------|-------|
| **Safari (iPhone/iPad)** | Share → Add to Home Screen → Add |
| **Chrome (Android)** | ⋮ → Install app / Add to Home Screen → confirm |
| **Chrome (desktop)** | Click install icon in address bar |
| **Android APK** | [Download](https://threecats-lsp.com/d-planner-plus/download.html) · Android 5.0+ / API 21 · allow "Install from unknown sources" |

### 🧪 Test Suites

All browser suites run live from the deployed app — no local setup needed for smoke testing.

| Suite | Live link | Scope |
|-------|-----------|-------|
| [`tests.html`](tests.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests.html) | Core regression — tissue maths, GF/VPM helpers, UI wiring |
| [`tests-verify.html`](tests-verify.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-verify.html) | Baker/FORTRAN cross-validation, coefficient checks, determinism |
| [`tests-extended.html`](tests-extended.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-extended.html) | Extended algorithm coverage — CCR setpoints, multi-gas, edge cases |
| [`tests-massive.html`](tests-massive.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-massive.html) | Full engine plans, gas plan, MultiDeco RT cross-validation, headless paths |
| [`tests-massive-main.html`](tests-massive-main.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-massive-main.html) | Mobile-optimised massive suite (version guard + cache bust) |
| [`tests-pscr-otu-cns.html`](tests-pscr-otu-cns.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-pscr-otu-cns.html) | pSCR OTU/CNS accumulation, loop gas labels, consumption references |
| [`tests-ccr-differential.html`](tests-ccr-differential.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-ccr-differential.html) | CCR engine differential vs reference manifests |

**Python / CI gates**

| Script | CI tier | Scope |
|--------|---------|-------|
| [`audit.py`](audit.py) | CI + Release | Static analysis — structure, safety rules, regression guards (1135 checks at v2.53.03) |
| [`tools/audit_coverage.py`](tools/audit_coverage.py) | CI + Release | Audit registry integrity, source inventory, fingerprints, evidence, and generated coverage reports |
| [`dev/run_all_regression.py`](dev/run_all_regression.py) | Both | Unified orchestrator — `--tier ci` (4 suites) or `--tier release` (9 suites) |
| [`dev/run_browser_regression.py`](dev/run_browser_regression.py) | CI | Playwright runner — `tests-verify.html` + `tests-pscr-otu-cns.html` |
| [`dev/run_native_regression.py`](dev/run_native_regression.py) | Release | Android select picker + Capacitor blob-export bridge (Playwright) |
| [`dev/validate_pscr_e2e.py`](dev/validate_pscr_e2e.py) | Release | pSCR end-to-end release gate (audit + Playwright) |
| [`dev/run_ccr_differential.py`](dev/run_ccr_differential.py) | Release | CCR differential comparison suite |
| [`dev/ccr_engine_validation_regression.py`](dev/ccr_engine_validation_regression.py) | Release | CCR/pSCR malformed gas/profile input validation |
| [`engine_validation_regression.py`](engine_validation_regression.py) | Release | Malformed-input validation + ZHL worker timeout/recovery |
| [`export_regression.py`](export_regression.py) | Release | TXT/PDF export format regression |

```bash
pip install playwright && playwright install chromium
python tools/build_pages_site.py
python dev/run_all_regression.py                   # CI tier (fast)
python dev/run_all_regression.py --tier release    # full release gates
```

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) · Release audit: [`.github/workflows/audit.yml`](.github/workflows/audit.yml)

### 🏛️ Engine Architecture

```
index.html
├── zhl-engine-bundle.js        ← ZHL Tier 3 (Bühlmann ZHL-16C + GF + CCR/pSCR, Web Worker)
│     └── zhl-schedule-worker.js
│           └── zhl-worker-bridge.js   (Promise bridge, terminate() API)
├── vpm-engine-bundle.js        ← VPM Tier 3 (VPM-B / VPM-B+GFS) → window.VPMEngine
└── lsp-test-harness.js         ← Dual-engine test router
```

Build sources (not loaded at runtime): `zhl-physics-core.js` · `zhl-gas-core.js` · `zhl-schedule-core.js` · `zhl-ccr-core.js` · `vpm-engine-core.js`  
Bundle rebuild: `npm run build:bundles` or `tools/build_zhl_bundle.py` · `tools/build_vpm_bundle.py`  
Engine parity check: `npm run check:engine-parity`  
Audit mirror rule: [`docs/AUDIT_MIRROR_RULE.md`](docs/AUDIT_MIRROR_RULE.md)  
Audit environment: [`docs/audit-units.json`](docs/audit-units.json) · [`docs/audit-master-plan.md`](docs/audit-master-plan.md) · [`docs/audit-coverage.md`](docs/audit-coverage.md) · [`docs/codebase-audit-strategy-v2.md`](docs/codebase-audit-strategy-v2.md)

**DOM adapter (index.html only):** `getCCRSettingsFromDOM` + `mergeCCRSettings` read UI state; all Bühlmann/CCR physics delegate to `ZhlEngineBundle`.

### 🗂️ Legacy Editions (Archived)

Development continues in **LSP D-Planner+** only. The two predecessor apps are frozen.

| App | URL | Frozen at |
|-----|-----|-----------|
| LSP D-Planner (OC only) | https://threecats-lsp.com/d-planner/ | v2.40.02-final |
| LSP D-Planner + CCR | https://threecats-lsp.com/d-planner-ccr/ | v2.30.31-final |

---

## 📄 T-Viewer — Dive Plan File Viewer

> [Live app](https://threecats-lsp.com/t-viewer/) · [Repo](https://github.com/Three-Cats-LSP/T-Viewer) · [APK](https://threecats-lsp.com/t-viewer/download.html)

The companion app for LSP D-Planner+. Export your dive plan as TXT or PDF, then open it in T-Viewer to share with your buddy or surface support team.

- Opens `.txt`, `.log`, `.plan`, `.div`, and `.pdf` files
- Receives shared files directly from LSP D-Planner+ on Android
- Syntax highlighting — section headers, parameter lines, depth/time data, warning keywords — all customisable per theme
- PDF viewer (PDF.js) with page navigation
- Edit mode — modify text plan, save back to device
- Font selector — System Default, Monospace, Roboto Mono, Source Code Pro, JetBrains Mono, Open Sans, Noto Sans
- Pinch-to-zoom — current font size shown in top bar
- Dark / light theme — all colors customisable via the COLORS tab
- Drag-and-drop on desktop browser

---

## 🎒 Get In Water — Dive Trip Packing Checklist

> v1.4.0 · MIT · [Live app](https://threecats-lsp.com/get-in-water/) · [Repo](https://github.com/Three-Cats-LSP/Get-In-Water) · [APK](https://threecats-lsp.com/get-in-water/download.html)

Never leave a regulator at home again. Maintain a master gear list, build per-trip checklists, tick items off as you pack, and export to TXT or PDF.

- **Master gear list** with built-in starter templates: Recreational, Underwater Photographer, Technical Diver
- **Per-trip checklists** — named trips, progress bar, item notes and quantity
- **TXT / PDF export** — plain-text or formatted packing list, share via any Android share target
- **Optional Google sync** — sign in to sync between web and Android; fully offline without an account

---

## 🏛️ Philosophy

- **Free, forever** — MIT licence on all apps
- **No account required** — everything works anonymously; cloud sync in Get In Water is opt-in
- **No Play Store** — direct APKs only, no gatekeeping
- **Offline-first** — every app works fully without a network connection after first load
- **Open source** — all code public, all engines documented and tested

---

## 📜 Licence

MIT — free to use, modify, and distribute.

---

*Three Cats LSP · [threecats-lsp.com](https://threecats-lsp.com) · [GitHub org](https://github.com/Three-Cats-LSP) · [@threecats_lsp](https://www.instagram.com/threecats_lsp)*
