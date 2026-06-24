# LSP D-Planner+

Free open-source decompression planner for recreational and technical divers. Runs entirely in the browser — no install, no build step, no server, no account.

Part of the [Three Cats LSP](https://threecats-lsp.com) **Diver's Toolkit**.

🌐 **Live app:** https://threecats-lsp.com/d-planner-plus/  
📲 **Android APK:** https://threecats-lsp.com/d-planner-plus/download.html  

**Current version: 2.50.00**

---

## Diver's Toolkit

| App | Description | Link |
|-----|-------------|------|
| **LSP D-Planner+** ← *this app* | Unified OC + CCR/pSCR decompression planning — Bühlmann, VPM-B, Rec/Tec | [Repo](https://github.com/Three-Cats-LSP/LSP_D-planner-plus) |
| **[T-Viewer](https://threecats-lsp.com/t-viewer/)** | Open and share exported dive plan TXT/PDF files | — |
| **[Get In Water](https://threecats-lsp.com/get-in-water/)** | Dive trip packing checklists | [Repo](https://github.com/Three-Cats-LSP/Get-In-Water) |

All apps at the [Diver's Toolkit hub](https://threecats-lsp.com).

---

## Algorithms

| Algorithm | Notes |
|-----------|-------|
| **Bühlmann ZHL-16C + GF** | 16 tissue compartments. GF Low/High via presets (GUE, MultiDeco, Abysner, Subsurface, DiveKit) or custom. Shallow gradient toggle. |
| **VPM-B** | Varying Permeability Model — bubble nuclei tracking. Conservatism +0 to +5. |
| **VPM-B/GFS** | VPM-B deep stops + GF High applied at shallow stops. |
| **PADI RDP** | Recreational NDL tables with pressure group tracking (Rec mode). |

---

## Features

### Recreational Mode
- NDL tables (PADI RDP-based + Bühlmann) with GF-adjustable limits
- Multi-dive day planning with residual nitrogen tracking across up to 4 dives
- Surface interval calculator — compartment tissue loading, controlling compartment, reverse-profile warning
- Average depth converter

### Technical Mode
- **CCR / pSCR** — circuit select, setpoint scheduling, diluent & bailout gases, on-loop Bühlmann + VPM
- Full trimix entry (O₂ / He / N₂) for bottom gas and all deco gases
- Travel gas card with auto-switch depth by MOD
- Altitude support — surface pressure presets to 3000 m, acclimatization toggle
- Repetitive dive tissue carry (ZHL + VPM)
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
| **Copy** | Plain text preview → clipboard |
| **Deco Slate** | Compact monospaced waterproof format |
| **TXT** | Full plan to Downloads (Android) or browser download |
| **PDF — Dive Plan** | Gas Consumption, Dive Profile, Deco Slate, GF Curve, Tissue Saturation |
| **PDF — Emergency Plan** | Emergency Gas, Ascent Schedule, Dive Profile, GF Curve, Tissue Saturation, Slate |

---

## Web App

Open https://threecats-lsp.com/d-planner-plus/ in any modern browser — no install required.

**Install as PWA:**
1. **Safari (iPhone/iPad):** Share → Add to Home Screen → Add
2. **Chrome (Android):** ⋮ → Install app / Add to Home Screen → confirm
3. **Chrome (desktop):** Click install icon in address bar

---

## Android App

Built with [Capacitor](https://capacitorjs.com). Direct APK — no Play Store required.

**Requirements:** Android 5.0+ (API 21)

**Install:**
1. Download APK from https://threecats-lsp.com/d-planner-plus/download.html
2. Allow "Install from unknown sources" in Android settings
3. Open the downloaded APK and install

---

## Test Suites

Open any HTML suite from a local HTTP server (or the [live app](https://threecats-lsp.com/d-planner-plus/) path) so `index.html` loads correctly in the iframe.

### Browser suites

| Suite | Scope |
|-------|-------|
| [`tests.html`](tests.html) | Core regression — tissue math, GF/VPM helpers, UI wiring |
| [`tests-verify.html`](tests-verify.html) | Baker/FORTRAN cross-val, coefficient checks, determinism |
| [`tests-extended.html`](tests-extended.html) | Extended algorithm coverage — CCR setpoints, multi-gas, edge cases |
| [`tests-massive.html`](tests-massive.html) | Full engine plans, gas plan, MultiDeco RT cross-val, headless paths |
| [`tests-massive-main.html`](tests-massive-main.html) | Mobile-optimised massive suite (version guard + cache bust) |
| [`tests-pscr-otu-cns.html`](tests-pscr-otu-cns.html) | pSCR OTU/CNS accumulation, loop gas labels, consumption refs |
| [`tests-ccr-differential.html`](tests-ccr-differential.html) | CCR engine differential vs reference manifests |

### Python gates (CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) + release: [`.github/workflows/audit.yml`](.github/workflows/audit.yml))

| Script | Scope |
|--------|-------|
| [`audit.py`](audit.py) | Static analysis — structure, safety rules, regression guards (~520 checks) |
| [`dev/run_all_regression.py`](dev/run_all_regression.py) | Unified orchestrator — `--tier ci` (4 suites) or `--tier release` (9 suites) |
| [`dev/run_browser_regression.py`](dev/run_browser_regression.py) | Playwright runner for `tests-verify.html` + `tests-pscr-otu-cns.html` |
| [`dev/run_native_regression.py`](dev/run_native_regression.py) | Android select picker + Capacitor blob-export bridge (Playwright) |
| [`dev/validate_pscr_e2e.py`](dev/validate_pscr_e2e.py) | pSCR end-to-end release gate (audit + Playwright) |
| [`dev/run_ccr_differential.py`](dev/run_ccr_differential.py) | CCR differential comparison suite |
| [`dev/ccr_engine_validation_regression.py`](dev/ccr_engine_validation_regression.py) | CCR/pSCR malformed gas/profile validation |
| [`engine_validation_regression.py`](engine_validation_regression.py) | Malformed-input validation + ZHL worker timeout/recovery |

**Quick local run:**

```bash
python tools/build_pages_site.py
python dev/run_all_regression.py              # CI tier
python dev/run_all_regression.py --tier release  # full release gates
```

Requires `pip install playwright && playwright install chromium` for browser/native suites.

---

## License

MIT — free to use, modify, and distribute. No account, no ads, no subscription.

---

*Three Cats LSP · [threecats-lsp.com](https://threecats-lsp.com)*
