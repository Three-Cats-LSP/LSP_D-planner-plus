# Engine mirror rule (audit methodology)

When auditing or fixing bugs in Tier-3 engine code, **always cross-check all mirror copies** before closing a finding.

## Mirror checklist

| Canonical source | Mirror 1 | Mirror 2 |
|------------------|----------|----------|
| `zhl-ccr-core.js` | `zhl-engine-bundle.js` (CCR section) | `index.html` CCR delegates (thin delegates — single source is bundle) |
| `zhl-schedule-core.js` | `zhl-engine-bundle.js` (schedule section) | — (`index.html` delegates to `ZhlEngineBundle`) |
| `zhl-physics-core.js` | `zhl-engine-bundle.js` (physics preamble) | `index.html` via `ZhlEngineBundle.*` |
| `zhl-gas-core.js` | `zhl-engine-bundle.js` (gas helpers) | `index.html` via `ZhlEngineBundle.*` |
| `vpm-engine-core.js` | `vpm-engine-bundle.js` | — |

## UI runtime cores (extracted from index.html)

These are **loaded at runtime** via `<script src>` (not build-time bundles). Canonical source is the `*-core.js` file; `index.html` keeps only DOM markup and orchestration.

| Canonical source | Mirror | Notes |
|------------------|--------|-------|
| `surf-interval-core.js` | — | `calcSurfInt`, `renderSurfIntPanel`, `toggleSurfIntPanel` |
| `gas-table-core.js` | — | `renderGasTable`, `calcEND_tool`, `renderEADTable` |
| `gas-plan-core.js` | — | `calcGasPlan`, `setGasRule`, gas-plan PDF/text |
| `export-core.js` | — | `buildExportText`, `exportPDF`, clipboard helpers |
| `contingency-core.js` | — | `runContingencyScenario`, `calcContingency`, state vars |

## Required audit steps

1. **Mirror rule:** For every bug found in a canonical `*-core.js` file, search the mirror locations above and report separately if any mirror is also affected.
2. **Neighbor rule (issue #123):** When fixing function A, grep the same file for functions that share globals (`altSurfaceP`, `BAR_PER_METRE`, `WATER_VAPOR`, `PSCR_MIN_PPO2`) and verify they receive the same guard or fix.
3. **Bundle rebuild:** After editing any `*-core.js`, run `npm run build:bundles` and commit the regenerated bundle files.
4. **Parity check:** Run `python tools/check_engine_parity.py` to verify source/bundle alignment.
5. **UI core rule:** After editing any runtime UI `*-core.js`, run `python audit.py`. Do **not** re-inline moved logic in `index.html`. Update `docs/audit-coverage.md` unit rows when a subsystem is extracted or verified.

## Fix-once workflow

```
edit *-core.js  →  npm run build:bundles  →  python tools/check_engine_parity.py  →  python audit.py
```

Do **not** patch `zhl-engine-bundle.js` or inline duplicates in `index.html` directly — fix the canonical source and rebuild.

**UI cores:** `edit *-core.js` → `python audit.py` → update `docs/audit-coverage.md`
