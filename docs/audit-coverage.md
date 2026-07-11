# Audit Coverage Ledger

> Generated from `docs/audit-units.json` by `tools/audit_coverage.py`. Do not edit manually.

**Baseline:** `2f4843b3d4032c07c95a08fa9407130c681998b0`
**States:** `UNREAD`, `IN_PROGRESS`, `READ`, `VERIFIED`

## Summary

| Layer | Total | Unread | In progress | Read | Verified |
|---|---:|---:|---:|---:|---:|
| build_config | 2 | 0 | 1 | 0 | 1 |
| ci | 7 | 0 | 4 | 1 | 2 |
| deploy_config | 1 | 0 | 0 | 0 | 1 |
| engine | 6 | 0 | 0 | 0 | 6 |
| engine_reference | 1 | 0 | 0 | 0 | 1 |
| native_android | 16 | 0 | 1 | 0 | 15 |
| native_bridge | 2 | 0 | 1 | 0 | 1 |
| native_config | 1 | 0 | 0 | 0 | 1 |
| pwa | 3 | 0 | 2 | 0 | 1 |
| release_config | 2 | 0 | 2 | 0 | 0 |
| test | 1 | 0 | 0 | 1 | 0 |
| test_infrastructure | 60 | 0 | 32 | 0 | 28 |
| tooling | 54 | 0 | 24 | 1 | 29 |
| ui_core | 16 | 0 | 15 | 0 | 1 |
| ui_shell | 2 | 0 | 2 | 0 | 0 |
| web_css | 5 | 0 | 5 | 0 | 0 |
| web_markup | 7 | 0 | 7 | 0 | 0 |
| web_runtime | 24 | 0 | 21 | 0 | 3 |
| worker | 2 | 0 | 0 | 0 | 2 |
| **Total** | **212** | **0** | **117** | **3** | **92** |

## Units

| Unit | Layer | Source | Lines | Priority | Status | Evidence |
|---|---|---|---:|---|---|---|
| UI-BOOT | web_runtime | `index.html:2` | 2457 | P2 | IN_PROGRESS | - |
| UI-RUNTIME-BOOTSTRAP | web_runtime | `index.html:2459` | 223 | P1 | IN_PROGRESS | - |
| UI-ALGORITHM-SETTINGS | web_runtime | `index.html:2682` | 293 | P1 | IN_PROGRESS | - |
| UI-UNIT-HELPERS | web_runtime | `index.html:2975` | 442 | P1 | IN_PROGRESS | - |
| UI-PLOT-INIT | web_runtime | `index.html:3417` | 493 | P2 | IN_PROGRESS | - |
| UI-TOOLS-TISSUES | web_runtime | `index.html:3910` | 372 | P2 | IN_PROGRESS | - |
| UI-TOOLS-EXPOSURE | web_runtime | `index.html:4282` | 233 | P1 | IN_PROGRESS | - |
| UI-SETTINGS | web_runtime | `index.html:4515` | 386 | P1 | IN_PROGRESS | - |
| UI-PROFILE-PRESETS | web_runtime | `index.html:4901` | 508 | P2 | IN_PROGRESS | - |
| UI-CONFIG-PRESETS | web_runtime | `index.html:5409` | 185 | P2 | VERIFIED | EXT-05, COV-01 |
| UI-APP-INIT | web_runtime | `index.html:5594` | 172 | P1 | IN_PROGRESS | - |
| UI-PWA-LIFECYCLE | pwa | `index.html:5766` | 92 | P1 | IN_PROGRESS | - |
| UI-CSS-FOUNDATION | web_css | `lsp-dplanner-foundation.css:1` | 418 | P2 | IN_PROGRESS | - |
| UI-CSS-MODES | web_css | `lsp-dplanner-modes.css:1` | 340 | P2 | IN_PROGRESS | - |
| UI-CSS-CONTROLS | web_css | `lsp-dplanner-controls.css:1` | 548 | P2 | IN_PROGRESS | - |
| UI-CSS-RESULTS | web_css | `lsp-dplanner-results.css:1` | 1075 | P1 | IN_PROGRESS | REG-89, REG-90, REG-91, REG-92, REG-93, REG-94 |
| UI-CSS-MOBILE-SHELL | web_css | `lsp-dplanner-mobile-shell.css:1` | 709 | P2 | IN_PROGRESS | - |
| UI-MARKUP-HEADER | web_markup | `ui/markup-header.html:1` | 786 | P2 | IN_PROGRESS | - |
| UI-MARKUP-REC-PLANNER | web_markup | `ui/markup-rec-planner.html:1` | 73 | P1 | IN_PROGRESS | - |
| UI-MARKUP-TEC-PLANNER | web_markup | `ui/markup-tec-planner.html:1` | 560 | P1 | IN_PROGRESS | - |
| UI-REC-PLANNER | ui_core | `rec-planner.js:1` | 9 | P1 | IN_PROGRESS | - |
| UI-MARKUP-PLANNER | web_markup | `ui/markup-planner.html:1` | 489 | P1 | IN_PROGRESS | - |
| UI-MARKUP-CONSUMPTION | web_markup | `ui/markup-consumption.html:1` | 381 | P1 | IN_PROGRESS | - |
| UI-MARKUP-TOOLS | web_markup | `ui/markup-tools.html:1` | 274 | P2 | IN_PROGRESS | - |
| UI-MARKUP-MODALS | web_markup | `ui/markup-modals.html:1` | 331 | P2 | IN_PROGRESS | - |
| UI-ENVIRONMENT | ui_core | `settings-core.js:39` | 380 | P1 | IN_PROGRESS | - |
| UI-MODE-STATE | ui_core | `settings-core.js:419` | 632 | P2 | IN_PROGRESS | - |
| UI-UNIT-SWITCHING | web_runtime | `schedule-runner-core.js:389` | 372 | P1 | IN_PROGRESS | - |
| UI-ZHL-DELEGATES | web_runtime | `schedule-runner-core.js:761` | 145 | P0 | IN_PROGRESS | - |
| UI-CCR-DELEGATES | web_runtime | `schedule-runner-core.js:906` | 370 | P0 | IN_PROGRESS | - |
| UI-DECO-PHYSICS | web_runtime | `schedule-runner-core.js:1276` | 291 | P0 | IN_PROGRESS | - |
| UI-SCHEDULE-INPUTS | web_runtime | `schedule-runner-core.js:1567` | 373 | P0 | IN_PROGRESS | - |
| UI-SETTINGS-CONTROLS | web_runtime | `schedule-runner-core.js:1940` | 428 | P1 | IN_PROGRESS | - |
| UI-VPM-RUNNER | web_runtime | `schedule-runner-core.js:2368` | 491 | P0 | IN_PROGRESS | REG-131, REG-132, REG-133, REG-134, REG-136, REG-138 |
| UI-ZHL-RUNNER-SETUP | web_runtime | `schedule-runner-core.js:2859` | 144 | P0 | IN_PROGRESS | - |
| UI-ZHL-RUNNER-ENGINE | web_runtime | `schedule-runner-core.js:3003` | 325 | P0 | IN_PROGRESS | REG-132, REG-134, REG-137 |
| UI-VPM-RENDER | ui_core | `results-render-core.js:338` | 505 | P1 | IN_PROGRESS | - |
| UI-ZHL-RESULTS | ui_core | `results-render-core.js:843` | 464 | P1 | IN_PROGRESS | - |
| UI-GAS-INPUTS | ui_core | `gas-cards-core.js:15` | 223 | P1 | IN_PROGRESS | - |
| UI-GAS-CARDS | ui_core | `gas-cards-core.js:238` | 284 | P1 | IN_PROGRESS | - |
| UI-ZHL-HEADLESS-HELPERS | web_runtime | `zhl-headless-adapter.js:23` | 194 | P1 | VERIFIED | EXT-05, COV-01 |
| UI-ZHL-HEADLESS-ENGINE | web_runtime | `zhl-headless-adapter.js:217` | 91 | P0 | VERIFIED | EXT-05, COV-01 |
| UI-PLOT-RENDER | ui_core | `plot-core.js:139` | 431 | P2 | IN_PROGRESS | - |
| UI-PLOT-WAYPOINTS | ui_core | `plot-core.js:570` | 201 | P2 | IN_PROGRESS | REG-138 |
| UI-TOOLS-PROFILE | ui_core | `plot-core.js:771` | 262 | P2 | VERIFIED | COV-01, PARITY-01, EXT-02, REG-01 |
| UI-TOOLS-GF | web_runtime | `gf-curve-core.js:1` | 317 | P2 | IN_PROGRESS | - |
| ENG-ZHL-PHYSICS | engine | `zhl-physics-core.js:1` | 189 | P1 | VERIFIED | REG-01, REG-22, REG-23 |
| ENG-ZHL-GAS | engine | `zhl-gas-core.js:1` | 184 | P1 | VERIFIED | REG-10, REG-11, REG-12, REG-13, REG-14 |
| ENG-ZHL-CCR | engine | `zhl-ccr-core.js:1` | 404 | P0 | VERIFIED | REG-06, REG-07, REG-29, REG-42 |
| ENG-ZHL-SCHEDULE | engine | `zhl-schedule-core.js:1` | 657 | P0 | VERIFIED | REG-22, REG-23, REG-62 |
| ENG-VPM | engine | `vpm-engine-core.js:1` | 2106 | P0 | VERIFIED | REG-31, REG-32, REG-33, REG-34, REG-121, REG-126, REG-127 |
| ENG-VPM-REFERENCE | engine_reference | `vpmb.py:1` | 2574 | P2 | VERIFIED | REG-01, REG-31, REG-128, REG-129 |
| ENG-RDP | engine | `padi-engine.js:1` | 101 | P1 | VERIFIED | REG-24, REG-25, REG-56, REG-57, REG-130 |
| APP-ANDROID-SELECT | native_bridge | `android-select-picker.js:1` | 294 | P1 | IN_PROGRESS | - |
| APP-CAPACITOR-BRIDGE | native_bridge | `capacitor-bridge.js:1` | 278 | P1 | VERIFIED | ANDROID-01, REG-45 |
| APP-CONTINGENCY | ui_core | `contingency-core.js:1` | 591 | P1 | IN_PROGRESS | - |
| APP-EXPORT | ui_core | `export-core.js:1` | 3394 | P2 | IN_PROGRESS | - |
| APP-GAS-PLAN | ui_core | `gas-plan-core.js:1` | 554 | P1 | IN_PROGRESS | - |
| APP-GAS-TABLE | ui_core | `gas-table-core.js:1` | 305 | P2 | IN_PROGRESS | - |
| APP-SURFACE-INTERVAL | ui_core | `surf-interval-core.js:1` | 386 | P1 | IN_PROGRESS | - |
| APP-SERVICE-WORKER | pwa | `sw.js:1` | 304 | P1 | IN_PROGRESS | - |
| APP-ZHL-WORKER-BRIDGE | worker | `zhl-worker-bridge.js:1` | 136 | P1 | VERIFIED | REG-01, REG-02, REG-03, REG-05 |
| APP-ZHL-WORKER | worker | `zhl-schedule-worker.js:1` | 23 | P1 | VERIFIED | REG-01, REG-02, REG-03, REG-05 |
| APP-DOWNLOAD | web_runtime | `download.html:1` | 120 | P3 | IN_PROGRESS | - |
| APP-MANIFEST | pwa | `manifest.json:1` | 41 | P2 | VERIFIED | REG-45, EXT-08 |
| APP-VERSION | release_config | `app-version.js:1` | 8 | P2 | IN_PROGRESS | - |
| APP-VERSION-JSON | release_config | `version.json:1` | 7 | P2 | IN_PROGRESS | - |
| APP-CAPACITOR-CONFIG | native_config | `capacitor.config.json:1` | 14 | P1 | VERIFIED | ANDROID-01, COV-01 |
| APP-CLOUDFLARE-CONFIG | deploy_config | `wrangler.jsonc:1` | 14 | P2 | VERIFIED | COV-01, EXT-07 |
| APP-PACKAGE | build_config | `package.json:1` | 40 | P1 | IN_PROGRESS | - |
| APP-NODE-VERSION | build_config | `.nvmrc:1` | 1 | P2 | VERIFIED | COV-01, EXT-07 |
| NATIVE-MAIN-ACTIVITY | native_android | `android/app/src/main/java/com/threecats/lsp/dplannerplus/MainActivity.java:1` | 61 | P1 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-MANIFEST | native_android | `android/app/src/main/AndroidManifest.xml:1` | 50 | P1 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-BUILD-ROOT | native_android | `android/build.gradle:1` | 29 | P2 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-BUILD-APP | native_android | `android/app/build.gradle:1` | 82 | P1 | IN_PROGRESS | - |
| NATIVE-SETTINGS | native_android | `android/settings.gradle:1` | 5 | P2 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-VARIABLES | native_android | `android/variables.gradle:1` | 16 | P2 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-LAYOUT | native_android | `android/app/src/main/res/layout/activity_main.xml:1` | 12 | P2 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-FILE-PATHS | native_android | `android/app/src/main/res/xml/file_paths.xml:1` | 9 | P1 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-STRINGS | native_android | `android/app/src/main/res/values/strings.xml:1` | 7 | P2 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-STYLES | native_android | `android/app/src/main/res/values/styles.xml:1` | 26 | P2 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-COLORS | native_android | `android/app/src/main/res/values/colors.xml:1` | 7 | P3 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-LAUNCHER-BG | native_android | `android/app/src/main/res/values/ic_launcher_background.xml:1` | 4 | P3 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-DRAWABLE-BG | native_android | `android/app/src/main/res/drawable/ic_launcher_background.xml:1` | 170 | P3 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-DRAWABLE-FG | native_android | `android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml:1` | 34 | P3 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-ICON | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml:1` | 5 | P3 | VERIFIED | ANDROID-01, COV-01 |
| NATIVE-ICON-ROUND | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml:1` | 5 | P3 | VERIFIED | ANDROID-01, COV-01 |
| TEST-ENGINE-REGRESSION | test_infrastructure | `dev/engine_regression.py:1` | 2771 | P1 | IN_PROGRESS | - |
| TEST-VPM-DIRECT-HOST | test_infrastructure | `dev/vpm_direct_host.js:1` | 161 | P0 | VERIFIED | REG-126, REG-127 |
| TEST-VPM-DIRECT-REGRESSION | test_infrastructure | `dev/vpm_direct_regression.js:1` | 125 | P0 | VERIFIED | REG-126, REG-127, REG-128, REG-129, REG-130 |
| TEST-ISSUE-140-REGRESSION | test_infrastructure | `dev/issue140_regression.py:1` | 99 | P1 | VERIFIED | REG-08, REG-09 |
| TEST-GAS-CORE-REGRESSION | test_infrastructure | `dev/gas_core_regression.py:1` | 129 | P1 | VERIFIED | REG-10, REG-11, REG-12 |
| TEST-ISSUE-141-REGRESSION | test_infrastructure | `dev/issue141_regression.py:1` | 108 | P1 | VERIFIED | REG-15, REG-16, REG-18 |
| TEST-ISSUE-142-REGRESSION | test_infrastructure | `dev/surf_interval_regression.py:1` | 124 | P1 | VERIFIED | REG-17, REG-19, REG-20, REG-21 |
| TEST-ANDROID-COMPILE | test_infrastructure | `dev/run_android_compile_check.py:1` | 101 | P2 | VERIFIED | ANDROID-01 |
| TEST-ENGINE-VALIDATION | test_infrastructure | `engine_validation_regression.py:1` | 585 | P1 | VERIFIED | REG-01, REG-139, COV-01 |
| TEST-CCR-VALIDATION | test_infrastructure | `dev/ccr_engine_validation_regression.py:1` | 359 | P1 | VERIFIED | REG-29, REG-42 |
| TEST-EXPORT | test_infrastructure | `export_regression.py:1` | 598 | P2 | IN_PROGRESS | - |
| TEST-RUN-ALL | test_infrastructure | `dev/run_all_regression.py:1` | 36 | P1 | VERIFIED | COV-01, PARITY-01, REG-06, REG-07, ANDROID-01, REG-45 |
| TEST-BROWSER-RUNNER | test_infrastructure | `dev/run_browser_regression.py:1` | 191 | P2 | VERIFIED | REG-06 |
| TEST-NATIVE-RUNNER | test_infrastructure | `dev/run_native_regression.py:1` | 271 | P2 | IN_PROGRESS | - |
| TEST-CCR-DIFF-RUNNER | test_infrastructure | `dev/run_ccr_differential.py:1` | 110 | P1 | VERIFIED | REG-07 |
| TEST-PSCR-E2E | test_infrastructure | `dev/validate_pscr_e2e.py:1` | 435 | P1 | VERIFIED | REG-46 |
| TEST-SW-LIFECYCLE | test_infrastructure | `dev/sw_lifecycle_test.py:1` | 86 | P1 | VERIFIED | REG-45 |
| TEST-PLAYWRIGHT-BOOT | test_infrastructure | `dev/playwright_boot.py:1` | 54 | P2 | VERIFIED | COV-01 |
| TEST-HTTP | test_infrastructure | `dev/test_http.py:1` | 231 | P2 | IN_PROGRESS | - |
| TEST-PLAYWRIGHT-RESTORE | test_infrastructure | `dev/playwright_restore.py:1` | 88 | P0 | IN_PROGRESS | - |
| TEST-TEST-HTTP | test_infrastructure | `dev/test_test_http.py:1` | 164 | P0 | IN_PROGRESS | - |
| TEST-CYCLE-08-RECORD-SYNC | test_infrastructure | `tools/test_cycle_08_record_sync.py:1` | 25 | P0 | IN_PROGRESS | - |
| TEST-LEGACY | test_infrastructure | `dev/legacy.js:1` | 517 | P3 | VERIFIED | COV-01 |
| TEST-HARNESS | test_infrastructure | `lsp-test-harness.js:1` | 155 | P1 | VERIFIED | COV-01 |
| TEST-MAIN | test_infrastructure | `tests.html:1` | 848 | P2 | VERIFIED | COV-01 |
| TEST-EXTENDED | test_infrastructure | `tests-extended.html:1` | 1312 | P2 | VERIFIED | COV-01 |
| TEST-MASSIVE | test_infrastructure | `tests-massive.html:1` | 4119 | P2 | IN_PROGRESS | - |
| TEST-MASSIVE-MAIN | test_infrastructure | `tests-massive-main.html:1` | 3353 | P2 | IN_PROGRESS | - |
| TEST-VERIFY | test_infrastructure | `tests-verify.html:1` | 936 | P2 | VERIFIED | COV-01 |
| TEST-PSCR-OTU-CNS | test_infrastructure | `tests-pscr-otu-cns.html:1` | 574 | P1 | VERIFIED | COV-01 |
| TEST-CCR-DIFF-HTML | test_infrastructure | `tests-ccr-differential.html:1` | 498 | P1 | IN_PROGRESS | - |
| TEST-NATIVE-FIXTURE | test_infrastructure | `dev/fixtures/native-select.html:1` | 18 | P2 | VERIFIED | COV-01 |
| TEST-CAP-FIXTURE | test_infrastructure | `dev/fixtures/capacitor-bridge.html:1` | 30 | P2 | VERIFIED | COV-01 |
| TEST-ANDROID-UNIT | test_infrastructure | `android/app/src/test/java/com/getcapacitor/myapp/ExampleUnitTest.java:1` | 18 | P3 | VERIFIED | ANDROID-01, COV-01 |
| TEST-ANDROID-INSTRUMENTED | test_infrastructure | `android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java:1` | 26 | P3 | VERIFIED | ANDROID-01, COV-01 |
| TEST-CCR-DIFF-BUILD | test_infrastructure | `tests/ccr-differential/build_assets.py:1` | 711 | P2 | IN_PROGRESS | - |
| TEST-CCR-DIFF-LIB-PY | test_infrastructure | `tests/ccr-differential/lib/ccr_open_reference.py:1` | 325 | P1 | VERIFIED | COV-01 |
| TEST-CCR-DIFF-LIB-JS | test_infrastructure | `tests/ccr-differential/lib/ccrdiff.js:1` | 418 | P1 | VERIFIED | COV-01 |
| TOOL-AUDIT | tooling | `audit.py:1` | 16 | P1 | VERIFIED | COV-01, PARITY-01, REG-01, REG-02, REG-03, REG-05 |
| TOOL-AUDIT-COVERAGE | tooling | `tools/audit_coverage.py:1` | 480 | P1 | IN_PROGRESS | - |
| TOOL-AUDIT-COVERAGE-TEST | test_infrastructure | `tools/test_audit_coverage.py:1` | 211 | P1 | VERIFIED | COV-01 |
| TOOL-V4-CURSOR-FULL-7-FIXES-TEST | test_infrastructure | `tools/test_v4_cursor_full_7_fixes.py:1` | 52 | P2 | IN_PROGRESS | - |
| TOOL-BUILD-PAGES | tooling | `tools/build_pages_site.py:1` | 190 | P2 | IN_PROGRESS | - |
| TOOL-ASSEMBLE-PAGES-PREVIEW | tooling | `tools/assemble_pages_preview.py:1` | 126 | P2 | READ | - |
| TEST-ASSEMBLE-PAGES-PREVIEW | test | `tools/test_assemble_pages_preview.py:1` | 48 | P2 | READ | - |
| TOOL-BUILD-VPM | tooling | `tools/build_vpm_bundle.py:1` | 104 | P1 | VERIFIED | COV-01, PARITY-01 |
| TOOL-BUILD-ZHL | tooling | `tools/build_zhl_bundle.py:1` | 374 | P1 | IN_PROGRESS | - |
| TOOL-CHECK-PARITY | tooling | `tools/check_engine_parity.py:1` | 313 | P1 | IN_PROGRESS | - |
| TOOL-RUN-AUDIT-COVERAGE-SUITE-PY | tooling | `tools/run_audit_coverage_suite.py:1` | 89 | P0 | IN_PROGRESS | - |
| TOOL-SEVEN-LENS-PROTOCOL | tooling | `tools/seven_lens_protocol.py:1` | 1417 | P0 | IN_PROGRESS | - |
| TOOL-SEVEN-LENS-PROTOCOL-MIGRATIONS | tooling | `tools/seven_lens_protocol_migrations.py:1` | 401 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-PROTOCOL | test_infrastructure | `tools/test_seven_lens_protocol.py:1` | 695 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-PROTOCOL-MIGRATIONS | test_infrastructure | `tools/test_seven_lens_protocol_migrations.py:1` | 284 | P0 | IN_PROGRESS | - |
| TOOL-SEVEN-LENS-EVIDENCE | tooling | `tools/seven_lens_evidence.py:1` | 146 | P0 | IN_PROGRESS | - |
| TOOL-SEVEN-LENS-BROWSER-TRACE | tooling | `tools/seven_lens_browser_trace.py:1` | 726 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-BROWSER-TRACE | test_infrastructure | `tools/test_seven_lens_browser_trace.py:1` | 614 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-CYCLE02-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-02-planner.json:1` | 78 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-CYCLE03-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-03-consumption.json:1` | 188 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-CYCLE04-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-04-tools-modals.json:1` | 133 | P0 | IN_PROGRESS | - |
| TOOL-EXTRACT-UI | tooling | `tools/extract_ui_cores.py:1` | 539 | P2 | IN_PROGRESS | - |
| TOOL-EXTRACT-ZHL | tooling | `tools/extract_zhl_core.py:1` | 124 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-INSERT-ZHL | tooling | `tools/insert_zhl_tier2.py:1` | 223 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-MERGE-CCR | tooling | `tools/merge_ccr_into_plus.py:1` | 477 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-PATCH-DECO | tooling | `tools/patch_run_deco_schedule.py:1` | 66 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-PATCH-SCHEDULE | tooling | `tools/patch_schedule_core_ccr.py:1` | 215 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-PATCH-TIER3 | tooling | `tools/patch_tier3_index.py:1` | 244 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-PATCH-VPM | tooling | `tools/patch_vpm_bundle_index.py:1` | 25 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-PATCH-ZHL | tooling | `tools/patch_zhl_engine.py:1` | 121 | P3 | VERIFIED | COV-01, PARITY-01 |
| TOOL-SYNC-WWW | tooling | `tools/sync_www.py:1` | 146 | P1 | IN_PROGRESS | - |
| TOOL-UPDATE-VERSION | tooling | `tools/update_sw_version.py:1` | 101 | P2 | IN_PROGRESS | - |
| TOOL-VENDOR | tooling | `tools/vendor_offline_assets.py:1` | 173 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-VERIFY-ASSETS | tooling | `tools/verify_site_assets.py:1` | 132 | P2 | VERIFIED | COV-01, PARITY-01 |
| CI-AUDIT | ci | `.github/workflows/audit.yml:1` | 143 | P1 | IN_PROGRESS | - |
| CI-APK | ci | `.github/workflows/build-apk.yml:1` | 171 | P1 | IN_PROGRESS | - |
| CI-MAIN | ci | `.github/workflows/ci.yml:1` | 199 | P1 | IN_PROGRESS | - |
| CI-DEPLOY | ci | `.github/workflows/deploy.yml:1` | 138 | P1 | IN_PROGRESS | - |
| CI-DEPLOY-DEV-PREVIEW | ci | `.github/workflows/deploy-dev-preview.yml:1` | 75 | P2 | READ | - |
| CI-NOTIFY | ci | `.github/workflows/notify-site.yml:1` | 50 | P2 | VERIFIED | COV-01 |
| CI-OFFLINE-ZIP | ci | `.github/workflows/build-offline-zip.yml:1` | 119 | P2 | VERIFIED | COV-01 |
| TOOL-AUDIT-V2-__INIT__-PY | tooling | `tools/audit/__init__.py:1` | 3 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-__MAIN__-PY | tooling | `tools/audit/__main__.py:1` | 5 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-CLI-PY | tooling | `tools/audit/cli.py:1` | 190 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-LEGACY_V1-PY | tooling | `tools/audit/legacy_v1.py:1` | 7446 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-MIGRATE_V2-PY | tooling | `tools/audit/migrate_v2.py:1` | 185 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-MODEL-PY | tooling | `tools/audit/model.py:1` | 72 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-PARSER_BRIDGE-MJS | tooling | `tools/audit/parser_bridge.mjs:1` | 132 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-REGISTRY-PY | tooling | `tools/audit/registry.py:1` | 232 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-REPORTING-PY | tooling | `tools/audit/reporting.py:1` | 92 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-RULES-PY | tooling | `tools/audit/rules.py:1` | 281 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-RUNNER-PY | tooling | `tools/audit/runner.py:1` | 99 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-CASE_REPORT-PY | tooling | `tools/audit/case_report.py:1` | 93 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-SUITE_EMIT-PY | tooling | `tools/audit/suite_emit.py:1` | 32 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-WORKSPACE-PY | tooling | `tools/audit/workspace.py:1` | 89 | P0 | VERIFIED | COV-01, PARITY-01 |
| TOOL-AUDIT-V2-AUDIT-LEGACY-MIGRATION-JSON | tooling | `docs/audit-legacy-migration.json:1` | 37671 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-TEST_SYSTEM-PY | tooling | `tools/audit/test_system.py:1` | 206 | P0 | IN_PROGRESS | - |
| UI-PLANNER-SHELL | ui_shell | `planner-shell.js:1` | 397 | P1 | IN_PROGRESS | REG-96, REG-99 |
| UI-RESULTS-PANEL | ui_shell | `results-panel.js:1` | 430 | P1 | IN_PROGRESS | COV-01, PARITY-01, EXT-02, REG-01, REG-95, REG-97, REG-98 |
| TOOL-V3-ASSEMBLE_UI_HTML-PY | tooling | `tools/assemble_ui_html.py:1` | 181 | P2 | IN_PROGRESS | - |
| TOOL-V3-EXTRACT_UI_CSS-PY | tooling | `tools/extract_ui_css.py:1` | 139 | P2 | IN_PROGRESS | - |
| TOOL-V3-MIGRATE_V3-PY | tooling | `tools/audit/migrate_v3.py:1` | 410 | P2 | IN_PROGRESS | - |
| TOOL-V3-RUN_UI_STRUCTURE_SUITE-PY | tooling | `tools/run_ui_structure_suite.py:1` | 94 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-UI_ASSETS-PY | tooling | `tools/ui_assets.py:1` | 60 | P2 | IN_PROGRESS | - |
| TOOL-V3-VERIFY_SW_ASSETS-PY | tooling | `tools/verify_sw_assets.py:1` | 59 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-TEST_UI_STRUCTURE_SUITE-PY | tooling | `tools/test_ui_structure_suite.py:1` | 98 | P2 | IN_PROGRESS | - |
| TOOL-V3-RESET-CYCLES-V3-PY | tooling | `tools/audit/reset_cycles_v3.py:1` | 219 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-RUN-V3-AUTOMATION-PY | tooling | `tools/audit/run_v3_automation.py:1` | 217 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-RUN-V3-UNITS-AUTOMATION-PY | tooling | `tools/audit/run_v3_units_automation.py:1` | 334 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-MIGRATE-LEGACY-CUTOVER-PY | tooling | `tools/audit/migrate_legacy_cutover.py:1` | 241 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-PROMOTE-VERIFIED-PY | tooling | `tools/audit/promote_verified.py:1` | 173 | P2 | VERIFIED | COV-01, PARITY-01 |
| TOOL-V3-RUN-V3-RELEASE-AUTOMATION-PY | tooling | `tools/audit/run_v3_release_automation.py:1` | 204 | P2 | VERIFIED | COV-01, PARITY-01 |
| UI-PLANNER-INPUTS | ui_core | `planner-inputs-core.js:1` | 119 | P1 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-CYCLE05-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-05-css.json:1` | 80 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-CYCLE05-EXPORT-FOCUS-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-05-export-focus.json:1` | 65 | P0 | IN_PROGRESS | - |
| TEST-UI-CSS-REGRESSION | test_infrastructure | `dev/ui_css_regression.py:1` | 286 | P0 | IN_PROGRESS | REG-76, REG-77, REG-78, REG-79, REG-80, REG-81 |
| TEST-SEVEN-LENS-CYCLE06-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-06-controls.json:1` | 251 | P0 | IN_PROGRESS | - |
| TEST-UI-CONTROLS-CSS-REGRESSION | test_infrastructure | `dev/ui_controls_css_regression.py:1` | 559 | P0 | IN_PROGRESS | REG-82, REG-83, REG-84, REG-85, REG-86, REG-87, REG-88 |
| TEST-C06-PRE-CONTROLS-REGRESSION | test_infrastructure | `dev/c06_pre_controls_regression.py:1` | 47 | P0 | IN_PROGRESS | REG-82, REG-83 |
| TEST-SEVEN-LENS-CYCLE07-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-07-results.json:1` | 526 | P0 | IN_PROGRESS | - |
| TEST-SEVEN-LENS-CYCLE08-TRACE | test_infrastructure | `docs/seven-lens-traces/cycle-08-shell-results.json:1` | 994 | P0 | IN_PROGRESS | - |
| TEST-UI-SHELL-RESULTS-REGRESSION | test_infrastructure | `dev/ui_shell_results_regression.py:1` | 485 | P0 | IN_PROGRESS | REG-95, REG-96, REG-97, REG-98, REG-99 |
| TEST-UI-RESULTS-CSS-REGRESSION | test_infrastructure | `dev/ui_results_css_regression.py:1` | 415 | P0 | IN_PROGRESS | REG-89, REG-90, REG-91, REG-92, REG-93, REG-94 |
| TEST-UI-VISUAL-CONTRACT-REGRESSION | test_infrastructure | `dev/ui_visual_contract_regression.py:1` | 2456 | P0 | IN_PROGRESS | REG-100, REG-101, REG-102, REG-103, REG-104, REG-105, REG-106, REG-107, REG-108, REG-109, REG-110, REG-111, REG-131, REG-132, REG-133, REG-134, REG-135, REG-136, REG-137, REG-138 |
| TEST-C07-PRE-RESULTS-REGRESSION | test_infrastructure | `dev/c07_pre_results_regression.py:1` | 48 | P0 | IN_PROGRESS | REG-89, REG-90 |
| TOOL-V4-FULL-R-FIXES-TEST | test_infrastructure | `tools/test_v4_full_r_fixes.py:1` | 71 | P2 | IN_PROGRESS | - |
| TEST-V4-FULL-R-EXPORT-SI | test_infrastructure | `dev/v4_full_r_export_si_regression.py:1` | 266 | P1 | IN_PROGRESS | - |
