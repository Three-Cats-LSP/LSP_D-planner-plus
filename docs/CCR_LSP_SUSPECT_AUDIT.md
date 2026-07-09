# CCR LSP_SUSPECT Differential Audit

**Date:** 2026-07-09  
**Scope:** Optional CCR differential rows classified as `LSP_SUSPECT` in the public CCR differential page.  

## Verdict

No release-blocking CCR engine defect was proven in this pass.

The `LSP_SUSPECT` rows were caused by optional comparator limitations or documented schedule-policy differences, not by failed required goldens. The suite already reported `failures: 0`, `missingRequired: 0`, and `pass: true`; this pass removes misleading suspect labels by documenting the exact expected-difference reasons in the generated CCR expected-difference ledger.

## Findings

- `CCR-NDL`: LSP includes the configured 3-minute safety stop in runtime/TTS for no-decompression CCR. The open references model direct ascent only.
- `CCR-ML`: the open Abysner/Subsurface reference generator consumes only the first profile level, so it is not an equivalent multilevel comparison.
- `CCR-BO` and `CCR-LOST-GAS`: the open reference generator does not model OC bailout gases or unavailable bailout gas. LSP intentionally switches to configured bailout gases and extends stops when EAN50 is unavailable.
- `CCR-REP`: the open reference generator does not carry first-dive tissue state into the repetitive dive. LSP does.
- `CCR-PRECISE-A`: LSP keeps app schedule semantics: fractional first stop, minute-resolution non-first stops. The fixture name overstates one-second stop support.
- `CCR-GF-B`, `CCR-SP`, and `CCR-ALT`: residual differences are narrow stop-distribution/ascent-integration differences, already bounded by matching required scenarios and adjacent passing references.

## What Changed

- Added audited expected-difference entries to `tests/ccr-differential/build_assets.py` so the generated `expected-differences.json` remains reproducible.
- Regenerated `tests/ccr-differential/expected-differences.json`.
- Regenerated the public CCR differential report outputs.

## Remaining Recommendation

If we want these optional scenarios to become stricter parity tests later, the comparator side needs stronger reference support first:

- multilevel CCR support in the open reference generator;
- OC bailout-gas modeling in open references;
- repetitive tissue carry in open references;
- an explicit product decision on true one-second non-first CCR stop mode.

Until then, keeping these rows as documented expected differences is more honest than calling them engine defects.
