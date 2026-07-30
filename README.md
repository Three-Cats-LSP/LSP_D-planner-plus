# LSP D-Planner+

LSP D-Planner+ is a free, open-source decompression planning app for recreational and technical divers.

It runs in the browser, installs as a PWA, works offline after first load, and is also available as a direct Android APK. There is no account, no ads, no Play Store requirement, and no server-side decompression calculation.

- Live app: https://threecats-lsp.com/d-planner-plus/
- Android APK: https://threecats-lsp.com/d-planner-plus/download.html
- Official release: https://github.com/Three-Cats-LSP/LSP_D-planner-plus/releases/latest
- Toolkit hub: https://threecats-lsp.com
- Current version: 3.1.2
- License: MIT

## Safety Notice

This software is a planning aid, not life-support equipment and not a replacement for training, certification, tables, dive computers, instructor guidance, team procedures, or conservative judgment.

Always verify plans independently, analyze gases, confirm MOD and ppO2 limits, carry adequate bailout/reserve gas, and follow your training agency and team protocols. The authors accept no responsibility for dive outcomes.

## Three Cats LSP Toolkit

| App | Purpose | Live app | Repository | Android APK |
| --- | --- | --- | --- | --- |
| LSP D-Planner+ | OC, CCR, pSCR, rec and tech decompression planning | https://threecats-lsp.com/d-planner-plus/ | https://github.com/Three-Cats-LSP/LSP_D-planner-plus | https://threecats-lsp.com/d-planner-plus/download.html |
| T-Viewer | View, edit, style, and share exported TXT/PDF dive plans | https://threecats-lsp.com/t-viewer/ | https://github.com/Three-Cats-LSP/T-Viewer | https://threecats-lsp.com/t-viewer/download.html |
| Get In Water | Dive trip packing lists and exportable checklists | https://threecats-lsp.com/get-in-water/ | https://github.com/Three-Cats-LSP/Get-In-Water | https://threecats-lsp.com/get-in-water/download.html |

## What Changed Since 2.5

Version 3.1.2 is the current post-2.5 milestone release after a major UI, engine, audit, export, and release-hardening overhaul.

Highlights:

- New risk-first audit epoch covering the app from engines and safety paths outward.
- Cleaner extracted runtime modules instead of large inline logic in `index.html`.
- ZHL headless adapter extracted into its own runtime file.
- VPM and ZHL render paths aligned around shared schedule rendering contracts.
- New deco schedule layout: Phase, Depth, Stop, Run, Mix, ppO2, CNS, EAD.
- Canonical gas labels across the app: `Air`, `100%`, and `OO/HH` such as `50/00` or `18/45`.
- Redesigned gas consumption cards with per-cylinder remaining gas bars, inline no-gas warnings, and main/contingency parity.
- Main dive graph moved into the Dive Profile flow; Graphs tab removed; Tissues tab simplified.
- Better mobile navigation and compact planner cards.
- Stronger MOD, gas-label, schedule-table, graph, contingency, export, and browser visual contracts.
- Release gates, Android APK build, offline ZIP build, and GitHub Pages deploy are green for 3.1.2.

## Algorithms And Modes

| Algorithm | Supported modes | Notes |
| --- | --- | --- |
| Buhlmann ZHL-16C + Gradient Factors | OC, CCR, pSCR | 16 tissue compartments, GF presets/custom GF, shallow-gradient controls, altitude/acclimatization support |
| VPM-B | OC, CCR | Bubble-model planning with conservatism +0 to +5 |
| VPM-B/GFS | OC, CCR | VPM-B deep stop profile with GF High shallow-stop control |
| PADI RDP | Recreational OC | Narrow recreational table mode for Air, EAN32, and EAN36 |

## Core Planner Features

### Recreational Planning

- PADI RDP and Buhlmann NDL workflows.
- Multi-dive day planning with residual nitrogen / tissue carryover.
- Surface interval support.
- Average-depth and unit helper tools.
- Rec mode deliberately keeps gas choices narrow for safety-contract clarity.

### Technical Planning

- OC, CCR, and pSCR circuit modes.
- Trimix bottom, travel, and deco gases.
- Travel gas with switch depth and MinOD/MOD display.
- Deco gas switching with explicit ppO2, MOD, and gas-label contracts.
- Altitude and acclimatization controls.
- Repetitive Buhlmann and VPM state carry.
- Contingency plans for gas loss, extra bottom time, and deeper-than-planned scenarios.
- Bailout and emergency gas consumption views.

### Safety And Warnings

- MOD blocking for unsafe bottom-gas depth.
- Narcotic depth warning tied to the affected gas.
- High CNS warning placement below the deco card.
- No-gas and critical-gas warnings inside the affected gas card.
- Low, critical, and no-gas states use distinct visual severity.
- Gas supply is shown per cylinder, not only as a total.

### Results Views

- Deco plan card with gas chips and plan metadata.
- Full dive graph in the Dive Profile tab.
- Main schedule table with consistent columns across Buhlmann, VPM, and contingency plans.
- Gas consumption cards with remaining gas bars.
- Tissue saturation and GF/tissue tools under the Tissues view.
- Light and dark themes.
- Desktop two-column layout and mobile compact layout.

### Tools

- MOD calculator.
- Best Mix.
- END calculator.
- EAD table.
- Gas table.
- NDL table.
- Unit converter.
- CNS / OTU calculator.

### Export

| Export | Description |
| --- | --- |
| Copy | Plain text plan copied to clipboard |
| Deco Slate | Compact monospaced slate format |
| TXT | Full text plan download/share |
| PDF | Dive plan PDF with schedule, gas, graph, tissue, and summary sections |
| Emergency Plan | Contingency plan export for gas-loss and emergency scenarios |

T-Viewer can open and style exported TXT/PDF dive plans:

- https://threecats-lsp.com/t-viewer/

## Install

### Web / PWA

Open:

```text
https://threecats-lsp.com/d-planner-plus/
```

Then install from your browser:

| Platform | Install path |
| --- | --- |
| iPhone / iPad Safari | Share -> Add to Home Screen |
| Android Chrome | Menu -> Install app or Add to Home Screen |
| Desktop Chrome / Edge / Vivaldi | Install icon in address bar |

### Android APK

Download:

```text
https://threecats-lsp.com/d-planner-plus/download.html
```

Requirements:

- Android 5.0+ / API 21+
- Allow "Install unknown apps" for your browser or file manager

The update manifest is:

```text
https://threecats-lsp.com/d-planner-plus/version.json
```

## Runtime Architecture

The app is a static web app with extracted runtime modules and generated engine bundles.

High-level runtime:

```text
index.html
|-- app-version.js
|-- settings-core.js
|-- planner-shell.js
|-- results-render-core.js
|-- results-panel.js
|-- plot-core.js
|-- zhl-engine-bundle.js
|-- zhl-headless-adapter.js
|-- zhl-worker-bridge.js
|-- zhl-schedule-worker.js
|-- vpm-engine-bundle.js
|-- schedule-runner-core.js
|-- vpm-runner-core.js
|-- export-core.js
`-- native bridge / PWA / UI support modules
```

Engine sources:

```text
zhl-physics-core.js
zhl-gas-core.js
zhl-schedule-core.js
zhl-ccr-core.js
vpm-engine-core.js
vpmb.py
```

Generated bundles:

```text
zhl-engine-bundle.js
vpm-engine-bundle.js
```

The engine bundles are rebuilt with:

```bash
npm run build:bundles
```

Engine parity is checked with:

```bash
npm run check:engine-parity
```

## Local Development

Install dependencies:

```bash
npm ci
python -m pip install playwright
python -m playwright install chromium
```

Useful commands:

```bash
npm run build
npm run sync:www
python tools/assemble_ui_html.py --verify
python tools/seven_lens_protocol.py check-all --require-artifacts
python -m tools.audit check --profile static
python -m tools.audit run --profile ci
python -m tools.audit run --profile release
```

Android sync:

```bash
npm run cap:sync
```

Open Android project:

```bash
npm run cap:open
```

## Test And Audit Gates

The 3.1.2 release uses a simplified risk-first audit workflow. Older Seven-Lens cycle records are preserved as historical evidence, but active development uses the newer V4 risk-first records and focused regression contracts.

Primary local gates:

| Command | Purpose |
| --- | --- |
| `python dev/engine_regression.py` | Engine and schedule regression cases |
| `node dev/vpm_direct_regression.js` | Direct VPM smoke and reference checks |
| `python dev/ui_visual_contract_regression.py` | UI visual contracts for schedule, gas cards, graph, labels, and mobile layout |
| `python dev/ui_shell_results_regression.py` | Shell/results navigation and state contracts |
| `python dev/ui_results_css_regression.py` | Results CSS contracts |
| `python dev/ui_css_regression.py` | Controls/CSS contracts |
| `python tools/assemble_ui_html.py --verify` | Generated `index.html` parity with UI partials |
| `python tools/seven_lens_protocol.py check-all --require-artifacts` | Reviewed-boundary and audit protocol sanity |
| `python -m tools.audit check --profile static` | Static audit profile |
| `python -m tools.audit run --profile ci` | CI audit profile |
| `python -m tools.audit run --profile release` | Full release profile |

Live browser suites:

| Suite | Link |
| --- | --- |
| Core tests | https://threecats-lsp.com/d-planner-plus/tests.html |
| Verify tests | https://threecats-lsp.com/d-planner-plus/tests-verify.html |
| Extended tests | https://threecats-lsp.com/d-planner-plus/tests-extended.html |
| Massive suite | https://threecats-lsp.com/d-planner-plus/tests-massive.html |
| Mobile massive suite | https://threecats-lsp.com/d-planner-plus/tests-massive-main.html |
| pSCR OTU/CNS suite | https://threecats-lsp.com/d-planner-plus/tests-pscr-otu-cns.html |
| CCR differential suite | https://threecats-lsp.com/d-planner-plus/tests-ccr-differential.html |

GitHub workflows:

| Workflow | Purpose |
| --- | --- |
| CI | Core checks and regression gates |
| Release gates | Full release audit profile |
| Deploy to GitHub Pages | Publishes the web/PWA app |
| Build Android APK | Builds and publishes the Android APK |
| Build Offline ZIP | Publishes an offline web package |

## Repository Layout

```text
.
|-- index.html
|-- ui/
|   |-- markup-header.html
|   |-- markup-modals.html
|   `-- ...
|-- *.js
|-- *.css
|-- dev/
|   `-- regression and audit helper scripts
|-- tools/
|   `-- build, audit, bundle, sync, and validation tools
|-- docs/
|   `-- audit, review, architecture, and release documentation
|-- android/
|   `-- Capacitor Android project
|-- www/
|   `-- synced web assets for Android/packaging
`-- tests/
    `-- browser and differential fixtures
```

## Legacy Editions

Development continues in LSP D-Planner+ only. Older editions are archived:

| App | URL | Status |
| --- | --- | --- |
| LSP D-Planner | https://threecats-lsp.com/d-planner/ | Archived OC-only version |
| LSP D-Planner + CCR | https://threecats-lsp.com/d-planner-ccr/ | Archived predecessor |

## License

MIT. You may use, modify, and distribute this project under the terms of the MIT license.

## Links

- Three Cats LSP: https://threecats-lsp.com
- GitHub organization: https://github.com/Three-Cats-LSP
- Instagram: https://www.instagram.com/threecats_lsp
