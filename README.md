# LSP D-Planner+

> **Free, open-source decompression planner for recreational and technical divers.**  
> Runs entirely in the browser — no install, no build step, no server, no account required.

Part of the [Three Cats LSP **Diver's Toolkit**](https://threecats-lsp.com) — a suite of free open-source diving apps for every stage of your dive.

🌐 **Live app:** https://threecats-lsp.com/d-planner-plus/  
📲 **Android APK:** https://threecats-lsp.com/d-planner-plus/download.html  
📦 **Current version:** 2.52.00 (stable)  
📄 **License:** MIT

---

## 🧰 Diver's Toolkit

Three free apps covering everything from planning to packing.

| App | What it does | Live | Repo |
|-----|-------------|------|------|
| **LSP D-Planner+** ← *this app* | Unified OC + CCR/pSCR decompression planner — Bühlmann ZHL-16C, VPM-B, Rec/Tec | [Open app](https://threecats-lsp.com/d-planner-plus/) | [GitHub](https://github.com/Three-Cats-LSP/LSP_D-planner-plus) |
| **T-Viewer** | Open, view and share exported dive plan TXT/PDF files with your buddy or surface support | [Open app](https://threecats-lsp.com/t-viewer/) | [GitHub](https://github.com/Three-Cats-LSP/T-Viewer) |
| **Get In Water** | Dive trip packing checklists — master gear list, per-trip lists, TXT/PDF export | [Open app](https://threecats-lsp.com/get-in-water/) | [GitHub](https://github.com/Three-Cats-LSP/Get-In-Water) |

All apps run offline, install as PWA, and are available as direct Android APKs. No Play Store, no account, no ads.

**Toolkit hub:** https://threecats-lsp.com

---

## ⚗️ Algorithms

| Algorithm | Mode | Notes |
|-----------|------|-------|
| **Bühlmann ZHL-16C + GF** | OC · CCR · pSCR | 16 tissue compartments. GF Low/High via presets (GUE, MultiDeco, Abysner, Subsurface, DiveKit) or custom. Shallow gradient toggle. |
| **VPM-B** | OC · CCR | Varying Permeability Model — bubble nuclei tracking. Conservatism +0 to +5. |
| **VPM-B/GFS** | OC · CCR | VPM-B deep stops + GF High at shallow stops. |
| **PADI RDP** | Rec | Recreational NDL tables with pressure group tracking. |

Engines run in an isolated **Web Worker** (ZHL Tier 3 bundle) and a dedicated IIFE bundle (`window.VPMEngine`) — no shared global state, deterministic output.

---

## 🤿 Features

### Recreational Mode
- NDL tables (PADI RDP + Bühlmann) with GF-adjustable limits
- Multi-dive day planning — residual nitrogen tracking across up to 4 dives
- Surface interval calculator — controlling compartment, tissue loading, reverse-profile warning
- Average depth converter

### Technical Mode
- **CCR / pSCR** — circuit select, setpoint scheduling, diluent & bailout gases, on-loop Bühlmann + VPM tissue loading, pSCR Baker steady-state loop model
- Full trimix entry (O₂ / He / N₂) for bottom gas and all deco gases
- Travel gas card with auto-switch depth by MOD
- Altitude support — surface pressure presets to 3 000 m, acclimatisation toggle
- Repetitive dive tissue carry (ZHL + VPM bubble state)
- Contingency plans — extended bottom time, went deeper (+3 m / +5 m)
- Surface GF footer metric

### Gas Management
- Gas consumption card — total volume, rule of thirds / half tank, turn pressure, reserve, sufficiency
- Up to 2 deco gas cards + travel gas (metric and imperial)
- SAC-based consumption in litres or cubic feet

### Tools
- **MOD Calculator** — ppO₂ limits, altitude-aware
- **Best Mix** — optimal O₂% for target depth and ppO₂
- **END Calculator** — narcotic equivalent depth
- **EAD Table** — nitrox EAD at common depths
- **Gas Table** — ppO₂, EAD, MOD for common mixes
- **Unit Converter** — depth, pressure, volume, SAC rate
- **CNS / OTU Tracker** — standalone oxygen toxicity calculator

### Export

| Format | Contents |
|--------|----------|
| **Copy** | Plain text plan → clipboard |
| **Deco Slate** | Compact monospaced waterproof format |
| **TXT** | Full plan to Downloads (Android) or browser download |
| **PDF — Dive Plan** | Gas Consumption · Dive Profile · Deco Slate · GF Curve · Tissue Saturation |
| **PDF — Emergency Plan** | Emergency Gas · Ascent Schedule · Dive Profile · GF Curve · Tissue Saturation · Slate |

---

## 📱 Install

### Web / PWA

Open https://threecats-lsp.com/d-planner-plus/ in any modern browser — no install required.

| Platform | Steps |
|----------|-------|
| **Safari (iPhone/iPad)** | Share → Add to Home Screen → Add |
| **Chrome (Android)** | ⋮ → Install app / Add to Home Screen → confirm |
| **Chrome (desktop)** | Click install icon in address bar |

### Android APK

Built with [Capacitor](https://capacitorjs.com). Direct APK — no Play Store required.

- **Requirements:** Android 5.0+ (API 21)
- **Download:** https://threecats-lsp.com/d-planner-plus/download.html

Install steps: download APK → allow "Install from unknown sources" in Android settings → open and install.

---

## 🧪 Test Suites

All browser suites must be opened from a local HTTP server (or the [live app path](https://threecats-lsp.com/d-planner-plus/)) so `index.html` loads correctly inside the iframe.

### Browser Suites

| Suite | Live link | Scope |
|-------|-----------|-------|
| [`tests.html`](tests.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests.html) | Core regression — tissue maths, GF/VPM helpers, UI wiring |
| [`tests-verify.html`](tests-verify.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-verify.html) | Baker/FORTRAN cross-validation, coefficient checks, determinism |
| [`tests-extended.html`](tests-extended.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-extended.html) | Extended algorithm coverage — CCR setpoints, multi-gas, edge cases |
| [`tests-massive.html`](tests-massive.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-massive.html) | Full engine plans, gas plan, MultiDeco RT cross-validation, headless paths |
| [`tests-massive-main.html`](tests-massive-main.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-massive-main.html) | Mobile-optimised massive suite (version guard + cache bust) |
| [`tests-pscr-otu-cns.html`](tests-pscr-otu-cns.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-pscr-otu-cns.html) | pSCR OTU/CNS accumulation, loop gas labels, consumption references |
| [`tests-ccr-differential.html`](tests-ccr-differential.html) | [▶ Run](https://threecats-lsp.com/d-planner-plus/tests-ccr-differential.html) | CCR engine differential vs reference manifests |

### Python / CI Gates

| Script | CI tier | Scope |
|--------|---------|-------|
| [`audit.py`](audit.py) | CI + Release | Static analysis — structure, safety rules, regression guards (684 checks) |
| [`dev/run_all_regression.py`](dev/run_all_regression.py) | Both | Unified orchestrator — `--tier ci` (4 suites) or `--tier release` (9 suites) |
| [`dev/run_browser_regression.py`](dev/run_browser_regression.py) | CI | Playwright runner — `tests-verify.html` + `tests-pscr-otu-cns.html` |
| [`dev/run_native_regression.py`](dev/run_native_regression.py) | Release | Android select picker + Capacitor blob-export bridge (Playwright) |
| [`dev/validate_pscr_e2e.py`](dev/validate_pscr_e2e.py) | Release | pSCR end-to-end release gate (audit + Playwright) |
| [`dev/run_ccr_differential.py`](dev/run_ccr_differential.py) | Release | CCR differential comparison suite |
| [`dev/ccr_engine_validation_regression.py`](dev/ccr_engine_validation_regression.py) | Release | CCR/pSCR malformed gas/profile input validation |
| [`engine_validation_regression.py`](engine_validation_regression.py) | Release | Malformed-input validation + ZHL worker timeout/recovery |
| [`export_regression.py`](export_regression.py) | Release | TXT/PDF export format regression |

**Quick local run:**

```bash
pip install playwright && playwright install chromium
python tools/build_pages_site.py
python dev/run_all_regression.py                   # CI tier (fast)
python dev/run_all_regression.py --tier release    # full release gates
```

CI workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)  
Release audit workflow: [`.github/workflows/audit.yml`](.github/workflows/audit.yml)

---

## 🏛️ Engine Architecture

```
index.html
├── zhl-engine-bundle.js      ← ZHL Tier 3 (Bühlmann ZHL-16C + GF + CCR/pSCR)
│     └── zhl-schedule-worker.js  (Web Worker shell)
│           └── zhl-worker-bridge.js  (Promise bridge, terminate() API)
├── vpm-engine-bundle.js      ← VPM Tier 3 (VPM-B / VPM-B+GFS) → window.VPMEngine
└── lsp-test-harness.js       ← Dual-engine test router
```

Build sources (not loaded at runtime): `zhl-schedule-core.js` · `zhl-ccr-core.js` · `vpm-engine-core.js`  
Bundle rebuild tools: `tools/build_zhl_bundle.py` · `tools/build_vpm_bundle.py`

---

## 🗂️ Legacy Editions (Archived)

Development continues in **LSP D-Planner+** only. The two predecessor apps are frozen.

| App | URL | Frozen at |
|-----|-----|-----------|
| LSP D-Planner (OC only) | https://threecats-lsp.com/d-planner/ | v2.40.02-final |
| LSP D-Planner + CCR | https://threecats-lsp.com/d-planner-ccr/ | v2.30.31-final |

---

## 📜 License

MIT — free to use, modify, and distribute.

---

*Three Cats LSP · [threecats-lsp.com](https://threecats-lsp.com) · [GitHub org](https://github.com/Three-Cats-LSP)*
