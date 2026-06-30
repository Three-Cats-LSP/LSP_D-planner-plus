# Audit Master Plan v2.1

> Generated schedule and totals. Policy and unit metadata live in `docs/audit-units.json`.

**Baseline:** `fd805111eab2fba349a9303a6e208106b798f82b`
**Units:** 155 total; 59 unread; 48 in progress; 45 read; 3 verified.
**Gate:** `python -m tools.audit check --profile static`

## Operating Rules

- Audit P0 before P1, then P2/P3. Unit priority is not finding severity.
- A cycle may read at most 600 new application-source lines plus one bounded engine re-verification unit.
- Record actual findings only; there are no finding quotas or projections.
- `VERIFIED` requires a current fingerprint and evidence that passes in the current audit profile.
- Generated artifacts are validated by their generator and parity command, not manual READ coverage.
- **Open findings of ANY severity (CRITICAL, HIGH, MEDIUM, LOW) fail the coverage gate and block release.**
- Every finding — regardless of severity — must be fixed, regression-tested, and closed before the cycle is marked done.

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
| 5 | UI-ZHL-DELEGATES, UI-CCR-DELEGATES | 484 | ENG-ZHL-SCHEDULE | Delegate units fully READ; **all findings (any severity) fixed and closed** |
| 6 | UI-DECO-PHYSICS, UI-SCHEDULE-INPUTS | 566 | ENG-ZHL-CCR | Physics and schedule input paths READ; **zero open findings at any severity** |
| 7 | UI-SETTINGS-CONTROLS, UI-VPM-RUNNER | 492 | ENG-VPM | Settings restoration and VPM invocation contracts READ; **zero open findings** |
| 8 | UI-VPM-RENDER | 530 | ENG-VPM | VPM rendering and safety warning propagation READ; **zero open findings** |
| 9 | UI-GAS-CARDS | 565 | ENG-ZHL-GAS | Dynamic gas-card units and persistence READ; **zero open findings** |
| 10 | UI-GAS-INPUTS, UI-ZHL-RUNNER-SETUP | 301 | ENG-ZHL-SCHEDULE | Gas validation and ZHL parameter construction READ; **zero open findings** |
| 11 | UI-ZHL-RUNNER-ENGINE | 340 | ENG-ZHL-SCHEDULE | Canonical ZHL execution path READ with parity evidence; **zero open findings** |
| 12 | UI-ZHL-RESULTS | 493 | ENG-ZHL-PHYSICS | Result construction, exposure totals, and safety fields READ; **zero open findings** |

## Severity Handling Policy

| Severity | Fix deadline | Blocks cycle close? | Blocks release? |
|----------|-------------|-------------------|----------------|
| CRITICAL | Same cycle, before any new READ | ✅ Yes | ✅ Yes |
| HIGH | Same cycle | ✅ Yes | ✅ Yes |
| MEDIUM | Same cycle | ✅ Yes | ✅ Yes |
| LOW | Same cycle | ✅ Yes | ✅ Yes |
| Enhancement (scoped future work) | Tracked as open issue, not a finding | ❌ No | ❌ No |

> **Enhancement vs. finding distinction:** A finding is a bug, logic error, safety defect, or incorrect behaviour in existing code. An enhancement is new functionality not yet built (e.g. #142 Dive 2 gas selector). Enhancements do not block cycle close or release. Findings at any severity do.

## Definition of Done

- Every registered unit is READ and at least 85% are VERIFIED.
- **Zero open findings of any severity (CRITICAL, HIGH, MEDIUM, LOW) remain.**
- All enhancement issues are logged and triaged; none are mislabelled as findings.
- `python -m tools.audit run --profile release` passes with every required leaf suite.
- No tracked source is unregistered, stale, overlapping, or uncovered.
- Generated bundles and deployment mirrors reproduce cleanly from canonical sources.

## Session Card

1. Pull `main`; run `python -m tools.audit check --profile static`.
2. Read each selected unit in full and apply all seven lenses.
3. Record unit ID, exact lines, lens, severity, issue, and regression case ID.
4. Fix **every** finding this cycle — no severity is deferred to a later cycle unless explicitly reclassified as an enhancement with justification.
5. Re-read fixed units, run the relevant suite, refresh fingerprints, and regenerate these reports.
6. Close the cycle only when the registry, worktree, and issue tracker are all clean (zero open findings).
