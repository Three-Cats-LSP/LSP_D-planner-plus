# Audit Master Plan v2.0

> Generated schedule and totals. Policy and unit metadata live in `docs/audit-units.json`.

**Baseline:** `fd805111eab2fba349a9303a6e208106b798f82b`
**Units:** 135 total; 68 unread; 14 in progress; 51 read; 2 verified.
**Gate:** `python tools/audit_coverage.py --check`

## Operating Rules

- Audit P0 before P1, then P2/P3. Unit priority is not finding severity.
- A cycle may read at most 600 new application-source lines plus one bounded engine re-verification unit.
- Record actual findings only; there are no finding quotas or projections.
- `VERIFIED` requires a current fingerprint, review/issue reference, evidence, and stable regression case IDs.
- Generated artifacts are validated by their generator and parity command, not manual READ coverage.
- Open CRITICAL or HIGH findings fail the coverage gate and block release.

## Seven Lenses

1. Arithmetic and physics
2. Control flow
3. State and mutation
4. API contracts
5. Canonical/generated parity
6. Safety regression
7. Tooling and CI

## Cycles 5-12

| Cycle | Application units | New lines | Engine re-verification | Acceptance |
|---:|---|---:|---|---|
| 5 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 478 | ENG-ZHL-SCHEDULE | Delegate units fully READ; schedule findings linked to regression IDs |
| 6 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 554 | ENG-ZHL-CCR | Physics and schedule input paths READ; no unresolved P0 finding |
| 7 | UI-SETTINGS-CONTROLS, UI-VPM-RUNNER | 477 | ENG-VPM | Settings restoration and VPM invocation contracts READ |
| 8 | UI-VPM-RENDER | 512 | ENG-VPM | VPM rendering and safety warning propagation READ |
| 9 | UI-GAS-CARDS | 559 | ENG-ZHL-GAS | Dynamic gas-card units and persistence READ |
| 10 | UI-GAS-INPUTS, UI-ZHL-RUNNER-SETUP | 300 | ENG-ZHL-SCHEDULE | Gas validation and ZHL parameter construction READ |
| 11 | UI-ZHL-RUNNER-ENGINE | 338 | ENG-ZHL-SCHEDULE | Canonical ZHL execution path READ with parity evidence |
| 12 | UI-ZHL-RESULTS | 488 | ENG-ZHL-PHYSICS | Result construction, exposure totals, and safety fields READ |

## Definition of Done

- Every registered unit is READ and at least 85% are VERIFIED.
- No open CRITICAL or HIGH findings remain.
- `audit.py`, engine parity, audit coverage, and the complete release regression pass.
- No tracked source is unregistered, stale, overlapping, or uncovered.
- Generated bundles and deployment mirrors reproduce cleanly from canonical sources.

## Session Card

1. Pull `main`; run the coverage gate and baseline checks.
2. Read each selected unit in full and apply all seven lenses.
3. Record unit ID, exact lines, lens, severity, issue, and regression case ID.
4. Re-read fixed units, run the relevant suite, refresh fingerprints, and regenerate these reports.
5. Close the cycle only when the registry and worktree are clean.
