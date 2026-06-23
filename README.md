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

| Suite | Scope |
|-------|-------|
| [`tests-verify.html`](https://three-cats-lsp.github.io/LSP_D-planner/tests-verify.html) | Baker/FORTRAN cross-val, coefficient checks, determinism |
| [`tests-massive.html`](https://three-cats-lsp.github.io/LSP_D-planner/tests-massive.html) | Full engine plans, UI, gas plan, MultiDeco RT cross-val |
| [`tests-massive-main.html`](https://three-cats-lsp.github.io/LSP_D-planner/tests-massive-main.html) | Mobile-optimised |
| `audit.py` | Static analysis — structure, safety rules, regression guards |

---

## License

MIT — free to use, modify, and distribute. No account, no ads, no subscription.

---

*Three Cats LSP · [threecats-lsp.com](https://threecats-lsp.com)*
