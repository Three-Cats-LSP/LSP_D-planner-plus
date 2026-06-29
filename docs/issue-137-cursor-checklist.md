## Cursor implementation checklist

**Cursor: implement all findings in this issue. Do not weaken validation or remove existing audit coverage.**

### Phase 0 — Tooling & CI
- [x] H-2: Fix unittest invocation in `ci.yml` and `audit.yml`
- [x] H-3: Extend `tools/check_engine_parity.py` for 5 UI runtime cores
- [x] L-14: Chain `check:engine-parity` into `npm run build`

### Phase 1 — Engine (mirror rule: *-core.js → build:bundles → parity)
- [x] H-7: inner `gfAt()` when `firstStopDepth === 0`
- [x] M-17: `validateHypoxicDecoGas` CCR exemption
- [x] M-18: `saturateLinearCCR` ascent setpoint boundary
- [x] M-13: `restoreInterLevelDerivedState` scalar restore
- [x] L-17: `depthAtSetpointCrossing` Number.isFinite guard

### Phase 2 — Contingency & deco schedule
- [x] H-1: hypoxic deco error visible during contingency
- [x] M-7: CCR validation during contingency
- [x] M-11: bailout restore in `runContingencyScenario` finally
- [x] M-12: contingency PDF emergency tissue data
- [x] M-20: functional contingency regression test

### Phase 3 — UI / export cores
- [x] H-4: imperial profile graph depth labels
- [x] H-5: CCR fields in contingency export
- [x] M-5/M-6: ppO2 color + MOD banner use `ppo2Bottom`
- [x] M-1/M-3: rep-dive CNS/OTU carry
- [x] M-4: surface interval deco ascent phase
- [x] M-8: VPM null deco gas warning
- [x] M-9/M-10: VPM TTS fixes
- [x] M-14: profile overlay clone guard
- [x] M-15: setDecoAlgorithm after preset restore
- [x] M-21: preset checkbox `.checked`
- [x] L-1–L-8, L-20: export/gas-table/gas-plan/surf-interval

### Phase 4 — Remaining index.html
- [x] L-4, L-9, L-10, L-11, L-12, L-16, L-18

### Phase 5 — Regression & infra
- [x] H-6: VPM worker test (sync-only guard + bubble clone)
- [x] M-19: VPM repetitive worker test (JSON clone boundary)
- [x] L-13: SW precache policy
- [x] L-15: test harness base path

### Validation
```
python tools/extract_ui_cores.py
python audit.py
python tools/check_engine_parity.py
npm run build:bundles
python dev/engine_regression.py
python dev/run_all_regression.py --tier release
```
