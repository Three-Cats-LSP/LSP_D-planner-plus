# V3 Release Audit — Final Report

**Generated:** 2026-07-03T03:01:30+00:00
**Commit:** `40021d7110384748af62eb98f6e31b0da4a58d83`
**Release gate:** `python -m tools.audit run --profile release` → PASS

## Registry

- Unit statuses: VERIFIED=173

## Legacy cutover

- Independently replaced: **2293** / 2293
- Recorded clean runs: **3** / 3
- Cutover ready: **True**
- SUITE-LEGACY profiles: **retired** (empty profiles in suite_catalog)

## Release fixes in this cutover

- CCR export regression: enable diluent-as-bailout before schedule run
- Browser GF row test: assert `gfPresetsRowV3` after V3 layout migration
- Cutover run ledger: timestamped release run IDs for same-commit automation

## Release runs

- Post-cutover verification: 18 suites PASS (SUITE-LEGACY no longer in release profile)

## Notes

- All 173 registry units are VERIFIED with release-grade evidence.
- Legacy migration ledger certifies 2293/2293 independent replacements.
- `promote_verified.py` now promotes IN_PROGRESS units after fingerprint refresh.
