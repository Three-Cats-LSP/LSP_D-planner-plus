# Audit Fix Follow-up — 2026-06-29

**Scope:** Resolves findings from the read-only full-application audit at `511f2b3`, plus four documented residuals.

## Code fixes (44079be)

| ID | Fix |
|----|-----|
| H-1 | `getActiveGas` passes `fO2` to `getPPO2LimitFn` (`zhl-gas-core.js:124`) |
| M-1 | VPM `ccrSchreinerParams` syncs ZHL env from dive `settings` (not `altitude: 0`) |
| M-2 | `calcStartOfDecoZone` / `projectedAscent` use `ccrSchreinerParams(..., settings)` |
| M-3 | `buildZhlScheduleParamsFromEngine` threads `s.minDecoProfile` from settings |
| L-2 | Removed dead `zhlOnLoopAt` / `zhlGasAt` / `_ccrPpo2Opts` from `runDecoSchedule` |

## CI / tooling (44079be)

- `audit.yml`: added `bundle-sync` job; release regression via `run_all_regression.py --tier release`
- `ci.yml`: runs on all PR branches (not main-only)
- `deploy.yml` / `build-apk.yml`: static audit + bundle parity gates before publish/build
- `check_engine_parity.py`: body parity for gas/physics functions + schedule embed check
- `package.json`: `npm test` → release regression orchestrator
- `run_browser_regression.py`: warnings fail the suite

## Residual fixes (this commit)

| Residual | Fix |
|----------|-----|
| `tests-massive.html` / `tests-extended.html` manual | `runMassiveRegressionCI` / `runExtendedRegressionCI` wired in `run_browser_regression.py` (release tier) |
| CCR differential 72 inconclusive | Abysner/Subsurface goldens for all valid fixtures; `partialCoverageEngines` for multideco/divekit (C1–C3 only) |
| Export regression ZHLC_GF only | Sections H (VPM-B / VPM-B GFS) and I (CCR) in `export_regression.py` |
| Playwright serves repo root | `serve_www()` in `test_http.py` — sync `www/`, stage harness, serve APK app shell |

## Gates added

`audit.py` GROUP 23.5 + audit 2026-06-29 M-1–M-11 / L-2 / L-4; engine regression `getActiveGasF02Limit`; residual follow-up block.
