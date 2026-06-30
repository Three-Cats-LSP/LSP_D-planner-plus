# Audit Coverage Ledger

> Generated from `docs/audit-units.json` by `tools/audit_coverage.py`. Do not edit manually.

**Baseline:** `fd805111eab2fba349a9303a6e208106b798f82b`
**States:** `UNREAD`, `IN_PROGRESS`, `READ`, `VERIFIED`

## Summary

| Layer | Total | Unread | In progress | Read | Verified |
|---|---:|---:|---:|---:|---:|
| build_config | 2 | 0 | 1 | 1 | 0 |
| ci | 5 | 0 | 5 | 0 | 0 |
| deploy_config | 1 | 0 | 0 | 1 | 0 |
| engine | 5 | 0 | 1 | 4 | 0 |
| engine_reference | 1 | 1 | 0 | 0 | 0 |
| native_android | 16 | 15 | 0 | 1 | 0 |
| native_bridge | 2 | 0 | 0 | 2 | 0 |
| native_config | 1 | 0 | 0 | 1 | 0 |
| pwa | 3 | 0 | 1 | 2 | 0 |
| release_config | 1 | 0 | 1 | 0 | 0 |
| test_infrastructure | 34 | 16 | 13 | 5 | 0 |
| tooling | 36 | 9 | 22 | 4 | 1 |
| ui_core | 5 | 0 | 2 | 0 | 3 |
| web_css | 4 | 4 | 0 | 0 | 0 |
| web_markup | 5 | 5 | 0 | 0 | 0 |
| web_runtime | 34 | 9 | 11 | 12 | 2 |
| worker | 2 | 0 | 0 | 2 | 0 |
| **Total** | **157** | **59** | **57** | **35** | **6** |

## Units

| Unit | Layer | Source | Lines | Priority | Status | Evidence |
|---|---|---|---:|---|---|---|
| UI-BOOT | web_runtime | `index.html:1` | 31 | P2 | READ | - |
| UI-CSS-FOUNDATION | web_css | `index.html:32` | 371 | P2 | UNREAD | - |
| UI-CSS-MODES | web_css | `index.html:403` | 369 | P2 | UNREAD | - |
| UI-CSS-CONTROLS | web_css | `index.html:772` | 454 | P2 | UNREAD | - |
| UI-CSS-RESULTS | web_css | `index.html:1226` | 411 | P1 | UNREAD | - |
| UI-MARKUP-HEADER | web_markup | `index.html:1637` | 554 | P2 | UNREAD | - |
| UI-MARKUP-PLANNER | web_markup | `index.html:2191` | 536 | P1 | UNREAD | - |
| UI-MARKUP-CONSUMPTION | web_markup | `index.html:2727` | 495 | P1 | UNREAD | - |
| UI-MARKUP-TOOLS | web_markup | `index.html:3222` | 269 | P2 | UNREAD | - |
| UI-MARKUP-MODALS | web_markup | `index.html:3491` | 341 | P2 | UNREAD | - |
| UI-RUNTIME-BOOTSTRAP | web_runtime | `index.html:3832` | 270 | P1 | IN_PROGRESS | - |
| UI-ENVIRONMENT | web_runtime | `index.html:4102` | 377 | P1 | READ | - |
| UI-MODE-STATE | web_runtime | `index.html:4479` | 380 | P2 | IN_PROGRESS | - |
| UI-ALGORITHM-SETTINGS | web_runtime | `index.html:4859` | 360 | P1 | IN_PROGRESS | - |
| UI-UNIT-HELPERS | web_runtime | `index.html:5219` | 388 | P1 | READ | - |
| UI-PLAN-HEADER | web_runtime | `index.html:5607` | 449 | P2 | READ | - |
| UI-UNIT-SWITCHING | web_runtime | `index.html:6056` | 310 | P1 | READ | - |
| UI-ZHL-DELEGATES | web_runtime | `index.html:6366` | 131 | P0 | VERIFIED | REG-16 |
| UI-CCR-DELEGATES | web_runtime | `index.html:6497` | 352 | P0 | VERIFIED | REG-15 |
| UI-DECO-PHYSICS | web_runtime | `index.html:6849` | 229 | P0 | IN_PROGRESS | - |
| UI-SCHEDULE-INPUTS | web_runtime | `index.html:7078` | 347 | P0 | IN_PROGRESS | - |
| UI-SETTINGS-CONTROLS | web_runtime | `index.html:7425` | 327 | P1 | READ | - |
| UI-VPM-RUNNER | web_runtime | `index.html:7752` | 165 | P0 | READ | - |
| UI-VPM-RENDER | web_runtime | `index.html:7917` | 530 | P1 | IN_PROGRESS | - |
| UI-GAS-INPUTS | web_runtime | `index.html:8447` | 184 | P1 | READ | - |
| UI-GAS-CARDS | web_runtime | `index.html:8631` | 573 | P1 | IN_PROGRESS | - |
| UI-ZHL-RUNNER-SETUP | web_runtime | `index.html:9204` | 117 | P0 | READ | - |
| UI-ZHL-RUNNER-ENGINE | web_runtime | `index.html:9321` | 340 | P0 | READ | REG-01, REG-06 |
| UI-ZHL-RESULTS | web_runtime | `index.html:9661` | 493 | P1 | IN_PROGRESS | - |
| UI-ZHL-HEADLESS-HELPERS | web_runtime | `index.html:10154` | 197 | P1 | IN_PROGRESS | - |
| UI-ZHL-HEADLESS-ENGINE | web_runtime | `index.html:10351` | 385 | P0 | READ | - |
| UI-PLOT-INIT | web_runtime | `index.html:10736` | 95 | P2 | UNREAD | - |
| UI-PLOT-RENDER | web_runtime | `index.html:10831` | 440 | P2 | UNREAD | - |
| UI-PLOT-WAYPOINTS | web_runtime | `index.html:11271` | 528 | P2 | UNREAD | - |
| UI-TOOLS-TISSUES | web_runtime | `index.html:11799` | 305 | P2 | UNREAD | - |
| UI-TOOLS-EXPOSURE | web_runtime | `index.html:12104` | 225 | P1 | IN_PROGRESS | - |
| UI-TOOLS-GF | web_runtime | `index.html:12329` | 214 | P2 | UNREAD | - |
| UI-TOOLS-PROFILE | web_runtime | `index.html:12543` | 365 | P2 | UNREAD | - |
| UI-SETTINGS | web_runtime | `index.html:12908` | 346 | P1 | IN_PROGRESS | - |
| UI-PROFILE-PRESETS | web_runtime | `index.html:13254` | 374 | P2 | UNREAD | - |
| UI-CONFIG-PRESETS | web_runtime | `index.html:13628` | 175 | P2 | UNREAD | - |
| UI-APP-INIT | web_runtime | `index.html:13803` | 164 | P1 | READ | - |
| UI-PWA-LIFECYCLE | pwa | `index.html:13967` | 84 | P1 | READ | - |
| ENG-ZHL-PHYSICS | engine | `zhl-physics-core.js:1` | 189 | P1 | READ | - |
| ENG-ZHL-GAS | engine | `zhl-gas-core.js:1` | 184 | P1 | READ | - |
| ENG-ZHL-CCR | engine | `zhl-ccr-core.js:1` | 391 | P0 | IN_PROGRESS | - |
| ENG-ZHL-SCHEDULE | engine | `zhl-schedule-core.js:1` | 591 | P0 | READ | REG-06, REG-22, REG-23 |
| ENG-VPM | engine | `vpm-engine-core.js:1` | 1955 | P0 | READ | - |
| ENG-VPM-REFERENCE | engine_reference | `vpmb.py:1` | 2574 | P2 | UNREAD | - |
| APP-ANDROID-SELECT | native_bridge | `android-select-picker.js:1` | 270 | P1 | READ | - |
| APP-CAPACITOR-BRIDGE | native_bridge | `capacitor-bridge.js:1` | 278 | P1 | READ | - |
| APP-CONTINGENCY | ui_core | `contingency-core.js:1` | 987 | P1 | IN_PROGRESS | - |
| APP-EXPORT | ui_core | `export-core.js:1` | 1761 | P2 | IN_PROGRESS | - |
| APP-GAS-PLAN | ui_core | `gas-plan-core.js:1` | 559 | P1 | VERIFIED | REG-10, REG-12, REG-13 |
| APP-GAS-TABLE | ui_core | `gas-table-core.js:1` | 302 | P2 | VERIFIED | REG-11, REG-14 |
| APP-SURFACE-INTERVAL | ui_core | `surf-interval-core.js:1` | 372 | P1 | VERIFIED | REG-17, REG-19, REG-20, REG-21 |
| APP-SERVICE-WORKER | pwa | `sw.js:1` | 252 | P1 | IN_PROGRESS | - |
| APP-ZHL-WORKER-BRIDGE | worker | `zhl-worker-bridge.js:1` | 135 | P1 | READ | - |
| APP-ZHL-WORKER | worker | `zhl-schedule-worker.js:1` | 23 | P1 | READ | - |
| APP-DOWNLOAD | web_runtime | `download.html:1` | 119 | P3 | UNREAD | - |
| APP-MANIFEST | pwa | `manifest.json:1` | 41 | P2 | READ | - |
| APP-VERSION | release_config | `version.json:1` | 6 | P2 | IN_PROGRESS | - |
| APP-CAPACITOR-CONFIG | native_config | `capacitor.config.json:1` | 14 | P1 | READ | - |
| APP-CLOUDFLARE-CONFIG | deploy_config | `wrangler.jsonc:1` | 14 | P2 | READ | - |
| APP-PACKAGE | build_config | `package.json:1` | 40 | P1 | IN_PROGRESS | - |
| APP-NODE-VERSION | build_config | `.nvmrc:1` | 1 | P2 | READ | - |
| NATIVE-MAIN-ACTIVITY | native_android | `android/app/src/main/java/com/threecats/lsp/dplannerplus/MainActivity.java:1` | 61 | P1 | UNREAD | - |
| NATIVE-MANIFEST | native_android | `android/app/src/main/AndroidManifest.xml:1` | 50 | P1 | READ | - |
| NATIVE-BUILD-ROOT | native_android | `android/build.gradle:1` | 29 | P2 | UNREAD | - |
| NATIVE-BUILD-APP | native_android | `android/app/build.gradle:1` | 82 | P1 | UNREAD | - |
| NATIVE-SETTINGS | native_android | `android/settings.gradle:1` | 5 | P2 | UNREAD | - |
| NATIVE-VARIABLES | native_android | `android/variables.gradle:1` | 16 | P2 | UNREAD | - |
| NATIVE-LAYOUT | native_android | `android/app/src/main/res/layout/activity_main.xml:1` | 12 | P2 | UNREAD | - |
| NATIVE-FILE-PATHS | native_android | `android/app/src/main/res/xml/file_paths.xml:1` | 9 | P1 | UNREAD | - |
| NATIVE-STRINGS | native_android | `android/app/src/main/res/values/strings.xml:1` | 7 | P2 | UNREAD | - |
| NATIVE-STYLES | native_android | `android/app/src/main/res/values/styles.xml:1` | 26 | P2 | UNREAD | - |
| NATIVE-COLORS | native_android | `android/app/src/main/res/values/colors.xml:1` | 7 | P3 | UNREAD | - |
| NATIVE-LAUNCHER-BG | native_android | `android/app/src/main/res/values/ic_launcher_background.xml:1` | 4 | P3 | UNREAD | - |
| NATIVE-DRAWABLE-BG | native_android | `android/app/src/main/res/drawable/ic_launcher_background.xml:1` | 170 | P3 | UNREAD | - |
| NATIVE-DRAWABLE-FG | native_android | `android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml:1` | 34 | P3 | UNREAD | - |
| NATIVE-ICON | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml:1` | 5 | P3 | UNREAD | - |
| NATIVE-ICON-ROUND | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml:1` | 5 | P3 | UNREAD | - |
| TEST-ENGINE-REGRESSION | test_infrastructure | `dev/engine_regression.py:1` | 1429 | P1 | IN_PROGRESS | - |
| TEST-ISSUE-140-REGRESSION | test_infrastructure | `dev/issue140_regression.py:1` | 99 | P1 | IN_PROGRESS | - |
| TEST-GAS-CORE-REGRESSION | test_infrastructure | `dev/gas_core_regression.py:1` | 129 | P1 | IN_PROGRESS | - |
| TEST-ISSUE-141-REGRESSION | test_infrastructure | `dev/issue141_regression.py:1` | 108 | P1 | IN_PROGRESS | - |
| TEST-ISSUE-142-REGRESSION | test_infrastructure | `dev/surf_interval_regression.py:1` | 124 | P1 | IN_PROGRESS | - |
| TEST-ANDROID-COMPILE | test_infrastructure | `dev/run_android_compile_check.py:1` | 101 | P2 | IN_PROGRESS | - |
| TEST-ENGINE-VALIDATION | test_infrastructure | `engine_validation_regression.py:1` | 521 | P1 | IN_PROGRESS | - |
| TEST-CCR-VALIDATION | test_infrastructure | `dev/ccr_engine_validation_regression.py:1` | 359 | P1 | IN_PROGRESS | - |
| TEST-EXPORT | test_infrastructure | `export_regression.py:1` | 596 | P2 | IN_PROGRESS | - |
| TEST-RUN-ALL | test_infrastructure | `dev/run_all_regression.py:1` | 36 | P1 | IN_PROGRESS | - |
| TEST-BROWSER-RUNNER | test_infrastructure | `dev/run_browser_regression.py:1` | 191 | P2 | UNREAD | - |
| TEST-NATIVE-RUNNER | test_infrastructure | `dev/run_native_regression.py:1` | 264 | P2 | UNREAD | - |
| TEST-CCR-DIFF-RUNNER | test_infrastructure | `dev/run_ccr_differential.py:1` | 110 | P1 | IN_PROGRESS | - |
| TEST-PSCR-E2E | test_infrastructure | `dev/validate_pscr_e2e.py:1` | 430 | P1 | IN_PROGRESS | - |
| TEST-SW-LIFECYCLE | test_infrastructure | `dev/sw_lifecycle_test.py:1` | 62 | P1 | READ | - |
| TEST-PLAYWRIGHT-BOOT | test_infrastructure | `dev/playwright_boot.py:1` | 54 | P2 | UNREAD | - |
| TEST-HTTP | test_infrastructure | `dev/test_http.py:1` | 101 | P2 | UNREAD | - |
| TEST-LEGACY | test_infrastructure | `dev/legacy.js:1` | 517 | P3 | UNREAD | - |
| TEST-HARNESS | test_infrastructure | `lsp-test-harness.js:1` | 155 | P1 | IN_PROGRESS | - |
| TEST-MAIN | test_infrastructure | `tests.html:1` | 848 | P2 | UNREAD | - |
| TEST-EXTENDED | test_infrastructure | `tests-extended.html:1` | 1312 | P2 | UNREAD | - |
| TEST-MASSIVE | test_infrastructure | `tests-massive.html:1` | 4103 | P2 | UNREAD | - |
| TEST-MASSIVE-MAIN | test_infrastructure | `tests-massive-main.html:1` | 3342 | P2 | UNREAD | - |
| TEST-VERIFY | test_infrastructure | `tests-verify.html:1` | 936 | P2 | UNREAD | - |
| TEST-PSCR-OTU-CNS | test_infrastructure | `tests-pscr-otu-cns.html:1` | 574 | P1 | UNREAD | - |
| TEST-CCR-DIFF-HTML | test_infrastructure | `tests-ccr-differential.html:1` | 406 | P1 | READ | - |
| TEST-NATIVE-FIXTURE | test_infrastructure | `dev/fixtures/native-select.html:1` | 18 | P2 | UNREAD | - |
| TEST-CAP-FIXTURE | test_infrastructure | `dev/fixtures/capacitor-bridge.html:1` | 30 | P2 | UNREAD | - |
| TEST-ANDROID-UNIT | test_infrastructure | `android/app/src/test/java/com/getcapacitor/myapp/ExampleUnitTest.java:1` | 18 | P3 | UNREAD | - |
| TEST-ANDROID-INSTRUMENTED | test_infrastructure | `android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java:1` | 26 | P3 | UNREAD | - |
| TEST-CCR-DIFF-BUILD | test_infrastructure | `tests/ccr-differential/build_assets.py:1` | 634 | P2 | UNREAD | - |
| TEST-CCR-DIFF-LIB-PY | test_infrastructure | `tests/ccr-differential/lib/ccr_open_reference.py:1` | 325 | P1 | READ | - |
| TEST-CCR-DIFF-LIB-JS | test_infrastructure | `tests/ccr-differential/lib/ccrdiff.js:1` | 418 | P1 | READ | - |
| TOOL-AUDIT | tooling | `audit.py:1` | 16 | P1 | IN_PROGRESS | - |
| TOOL-AUDIT-COVERAGE | tooling | `tools/audit_coverage.py:1` | 450 | P1 | IN_PROGRESS | - |
| TOOL-AUDIT-COVERAGE-TEST | test_infrastructure | `tools/test_audit_coverage.py:1` | 198 | P1 | READ | - |
| TOOL-BUILD-PAGES | tooling | `tools/build_pages_site.py:1` | 131 | P2 | IN_PROGRESS | - |
| TOOL-BUILD-VPM | tooling | `tools/build_vpm_bundle.py:1` | 104 | P1 | READ | - |
| TOOL-BUILD-ZHL | tooling | `tools/build_zhl_bundle.py:1` | 382 | P1 | IN_PROGRESS | - |
| TOOL-CHECK-PARITY | tooling | `tools/check_engine_parity.py:1` | 307 | P1 | IN_PROGRESS | - |
| TOOL-RUN-AUDIT-COVERAGE-SUITE-PY | tooling | `tools/run_audit_coverage_suite.py:1` | 46 | P0 | IN_PROGRESS | - |
| TOOL-EXTRACT-UI | tooling | `tools/extract_ui_cores.py:1` | 375 | P2 | VERIFIED | EXT-01 |
| TOOL-EXTRACT-ZHL | tooling | `tools/extract_zhl_core.py:1` | 124 | P2 | UNREAD | - |
| TOOL-INSERT-ZHL | tooling | `tools/insert_zhl_tier2.py:1` | 223 | P3 | UNREAD | - |
| TOOL-MERGE-CCR | tooling | `tools/merge_ccr_into_plus.py:1` | 477 | P3 | UNREAD | - |
| TOOL-PATCH-DECO | tooling | `tools/patch_run_deco_schedule.py:1` | 66 | P3 | UNREAD | - |
| TOOL-PATCH-SCHEDULE | tooling | `tools/patch_schedule_core_ccr.py:1` | 215 | P3 | UNREAD | - |
| TOOL-PATCH-TIER3 | tooling | `tools/patch_tier3_index.py:1` | 244 | P3 | UNREAD | - |
| TOOL-PATCH-VPM | tooling | `tools/patch_vpm_bundle_index.py:1` | 25 | P3 | UNREAD | - |
| TOOL-PATCH-ZHL | tooling | `tools/patch_zhl_engine.py:1` | 121 | P3 | UNREAD | - |
| TOOL-SYNC-WWW | tooling | `tools/sync_www.py:1` | 104 | P1 | READ | - |
| TOOL-UPDATE-VERSION | tooling | `tools/update_sw_version.py:1` | 104 | P2 | READ | - |
| TOOL-VENDOR | tooling | `tools/vendor_offline_assets.py:1` | 115 | P2 | UNREAD | - |
| TOOL-VERIFY-ASSETS | tooling | `tools/verify_site_assets.py:1` | 132 | P2 | READ | - |
| CI-AUDIT | ci | `.github/workflows/audit.yml:1` | 131 | P1 | IN_PROGRESS | - |
| CI-APK | ci | `.github/workflows/build-apk.yml:1` | 159 | P1 | IN_PROGRESS | - |
| CI-MAIN | ci | `.github/workflows/ci.yml:1` | 189 | P1 | IN_PROGRESS | - |
| CI-DEPLOY | ci | `.github/workflows/deploy.yml:1` | 128 | P1 | IN_PROGRESS | - |
| CI-NOTIFY | ci | `.github/workflows/notify-site.yml:1` | 50 | P2 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-__INIT__-PY | tooling | `tools/audit/__init__.py:1` | 3 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-__MAIN__-PY | tooling | `tools/audit/__main__.py:1` | 5 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-CLI-PY | tooling | `tools/audit/cli.py:1` | 188 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-LEGACY_V1-PY | tooling | `tools/audit/legacy_v1.py:1` | 7321 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-MIGRATE_V2-PY | tooling | `tools/audit/migrate_v2.py:1` | 185 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-MODEL-PY | tooling | `tools/audit/model.py:1` | 72 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-PARSER_BRIDGE-MJS | tooling | `tools/audit/parser_bridge.mjs:1` | 111 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-REGISTRY-PY | tooling | `tools/audit/registry.py:1` | 199 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-REPORTING-PY | tooling | `tools/audit/reporting.py:1` | 92 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-RULES-PY | tooling | `tools/audit/rules.py:1` | 136 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-RUNNER-PY | tooling | `tools/audit/runner.py:1` | 99 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-CASE_REPORT-PY | tooling | `tools/audit/case_report.py:1` | 93 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-SUITE_EMIT-PY | tooling | `tools/audit/suite_emit.py:1` | 32 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-WORKSPACE-PY | tooling | `tools/audit/workspace.py:1` | 89 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-AUDIT-LEGACY-MIGRATION-JSON | tooling | `docs/audit-legacy-migration.json:1` | 31682 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-TEST_SYSTEM-PY | tooling | `tools/audit/test_system.py:1` | 184 | P0 | IN_PROGRESS | - |
