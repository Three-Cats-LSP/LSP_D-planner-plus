# Audit Architecture

The audit platform is a registry-driven gate for source structure, generated parity,
regression evidence, findings, and review coverage. `docs/audit-units.json` is the
machine-readable source of truth (`schema_version: 3`).

## Commands

```text
python -m tools.audit check --profile static
python -m tools.audit run --profile ci
python -m tools.audit run --profile release
python -m tools.audit refresh --unit <ID>
python tools/audit/reset_cycles_v3.py
python tools/audit/migrate_v3.py
python tools/audit_coverage.py --refresh-fingerprints --write-docs
```

The root `audit.py` remains a compatibility launcher for the static profile.
`dev/run_all_regression.py` remains a compatibility launcher for CI and release profiles.

## V3 layout model

After UI extraction and CSS redesign, canonical audit units live in:

| Layer | Paths |
|---|---|
| `web_shell` | `index.html` — boot, delegates, inline orchestration |
| `ui_core` | `*-core.js` runtime modules |
| `ui_shell` | `planner-shell.js`, `results-panel.js` |
| `web_css` | `lsp-dplanner-*.css` |
| `web_markup` | `ui/markup-*.html` partials (assembled into `index.html`) |
| `engine` | ZHL/VPM canonical cores and bundles |

`index.html` is the deploy artifact. `SUITE-UI-STRUCTURE` (`tools/run_ui_structure_suite.py`)
validates extraction markers, CSS links, markup assembly, script order, Pages assets, and SW precache.

Agent workflow: see `docs/audit-v3-runbook.md`.

## Profiles

- `static` — registry, fingerprints, parser rules, bundle parity, Pages shell, UI structure suite, legacy baseline.
- `ci` — export, engine validation, full engine regression, SW lifecycle.
- `release` — CCR validation, browser regression, pSCR E2E, CCR differential, native bridge.

## Verification semantics

A declared `VERIFIED` unit is effective only when its fingerprint is current and every
required evidence suite executed successfully in the current profile.

Reports: `dev/audit-results.json`, `dev/audit-report.md`.

## Legacy cutover

Frozen implementation: `tools/audit/legacy_v1.py`. Ledger: `docs/audit-legacy-migration.json`.
Legacy remains blocking until sites are independently replaced by V3 rules/suites and three
clean main-branch release runs are recorded.
