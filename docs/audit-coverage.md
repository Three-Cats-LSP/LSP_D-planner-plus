# Audit Coverage Ledger

> Generated from `docs/audit-units.json` by `tools/audit_coverage.py`. Do not edit manually.

**Baseline:** `2f4843b3d4032c07c95a08fa9407130c681998b0`
**States:** `UNREAD`, `IN_PROGRESS`, `READ`, `VERIFIED`

## Summary

| Layer | Total | Unread | In progress | Read | Verified |
|---|---:|---:|---:|---:|---:|
| build_config | 2 | 0 | 0 | 2 | 0 |
| ci | 6 | 0 | 0 | 6 | 0 |
| deploy_config | 1 | 0 | 0 | 1 | 0 |
| engine | 6 | 0 | 0 | 6 | 0 |
| engine_reference | 1 | 0 | 0 | 1 | 0 |
| native_android | 16 | 12 | 0 | 4 | 0 |
| native_bridge | 2 | 0 | 0 | 2 | 0 |
| native_config | 1 | 0 | 0 | 1 | 0 |
| pwa | 3 | 0 | 0 | 3 | 0 |
| release_config | 1 | 1 | 0 | 0 | 0 |
| test_infrastructure | 34 | 16 | 7 | 11 | 0 |
| tooling | 45 | 9 | 33 | 3 | 0 |
| ui_core | 14 | 0 | 0 | 14 | 0 |
| ui_shell | 2 | 0 | 0 | 2 | 0 |
| web_css | 4 | 0 | 0 | 4 | 0 |
| web_markup | 5 | 0 | 0 | 5 | 0 |
| web_runtime | 24 | 0 | 0 | 24 | 0 |
| worker | 2 | 0 | 0 | 2 | 0 |
| **Total** | **169** | **38** | **40** | **91** | **0** |

## Units

| Unit | Layer | Source | Lines | Priority | Status | Evidence |
|---|---|---|---:|---|---|---|
| UI-BOOT | web_runtime | `index.html:1` | 2369 | P2 | READ | - |
| UI-RUNTIME-BOOTSTRAP | web_runtime | `index.html:2370` | 218 | P1 | READ | - |
| UI-ALGORITHM-SETTINGS | web_runtime | `index.html:2588` | 284 | P1 | READ | - |
| UI-UNIT-HELPERS | web_runtime | `index.html:2872` | 472 | P1 | READ | - |
| UI-UNIT-SWITCHING | web_runtime | `index.html:3344` | 323 | P1 | READ | - |
| UI-ZHL-DELEGATES | web_runtime | `index.html:3667` | 141 | P0 | READ | - |
| UI-CCR-DELEGATES | web_runtime | `index.html:3808` | 370 | P0 | READ | - |
| UI-DECO-PHYSICS | web_runtime | `index.html:4178` | 232 | P0 | READ | - |
| UI-SCHEDULE-INPUTS | web_runtime | `index.html:4410` | 365 | P0 | READ | - |
| UI-SETTINGS-CONTROLS | web_runtime | `index.html:4775` | 387 | P1 | READ | - |
| UI-VPM-RUNNER | web_runtime | `index.html:5162` | 473 | P0 | READ | - |
| UI-ZHL-RUNNER-SETUP | web_runtime | `index.html:5635` | 127 | P0 | READ | - |
| UI-ZHL-RUNNER-ENGINE | web_runtime | `index.html:5762` | 352 | P0 | READ | - |
| UI-ZHL-HEADLESS-HELPERS | web_runtime | `index.html:6114` | 201 | P1 | READ | - |
| UI-ZHL-HEADLESS-ENGINE | web_runtime | `index.html:6315` | 387 | P0 | READ | - |
| UI-PLOT-INIT | web_runtime | `index.html:6702` | 439 | P2 | READ | - |
| UI-TOOLS-TISSUES | web_runtime | `index.html:7141` | 310 | P2 | READ | - |
| UI-TOOLS-EXPOSURE | web_runtime | `index.html:7451` | 225 | P1 | READ | - |
| UI-TOOLS-GF | web_runtime | `index.html:7676` | 316 | P2 | READ | - |
| UI-SETTINGS | web_runtime | `index.html:7992` | 368 | P1 | READ | - |
| UI-PROFILE-PRESETS | web_runtime | `index.html:8360` | 374 | P2 | READ | - |
| UI-CONFIG-PRESETS | web_runtime | `index.html:8734` | 185 | P2 | READ | - |
| UI-APP-INIT | web_runtime | `index.html:8919` | 175 | P1 | READ | - |
| UI-PWA-LIFECYCLE | pwa | `index.html:9094` | 99 | P1 | READ | - |
| UI-CSS-FOUNDATION | web_css | `lsp-dplanner-foundation.css:1` | 454 | P2 | READ | - |
| UI-CSS-MODES | web_css | `lsp-dplanner-modes.css:1` | 372 | P2 | READ | - |
| UI-CSS-CONTROLS | web_css | `lsp-dplanner-controls.css:1` | 528 | P2 | READ | - |
| UI-CSS-RESULTS | web_css | `lsp-dplanner-results.css:1` | 924 | P1 | READ | - |
| UI-MARKUP-HEADER | web_markup | `ui/markup-header.html:1` | 840 | P2 | READ | - |
| UI-MARKUP-PLANNER | web_markup | `ui/markup-planner.html:1` | 493 | P1 | READ | - |
| UI-MARKUP-CONSUMPTION | web_markup | `ui/markup-consumption.html:1` | 381 | P1 | READ | - |
| UI-MARKUP-TOOLS | web_markup | `ui/markup-tools.html:1` | 271 | P2 | READ | - |
| UI-MARKUP-MODALS | web_markup | `ui/markup-modals.html:1` | 341 | P2 | READ | - |
| UI-ENVIRONMENT | ui_core | `settings-core.js:39` | 361 | P1 | READ | - |
| UI-MODE-STATE | ui_core | `settings-core.js:400` | 571 | P2 | READ | - |
| UI-VPM-RENDER | ui_core | `results-render-core.js:17` | 531 | P1 | READ | - |
| UI-ZHL-RESULTS | ui_core | `results-render-core.js:548` | 533 | P1 | READ | - |
| UI-GAS-INPUTS | ui_core | `gas-cards-core.js:15` | 217 | P1 | READ | - |
| UI-GAS-CARDS | ui_core | `gas-cards-core.js:232` | 280 | P1 | READ | - |
| UI-PLOT-RENDER | ui_core | `plot-core.js:109` | 439 | P2 | READ | - |
| UI-PLOT-WAYPOINTS | ui_core | `plot-core.js:548` | 182 | P2 | READ | - |
| UI-TOOLS-PROFILE | ui_core | `plot-core.js:730` | 262 | P2 | READ | - |
| ENG-ZHL-PHYSICS | engine | `zhl-physics-core.js:1` | 189 | P1 | READ | - |
| ENG-ZHL-GAS | engine | `zhl-gas-core.js:1` | 184 | P1 | READ | - |
| ENG-ZHL-CCR | engine | `zhl-ccr-core.js:1` | 404 | P0 | READ | - |
| ENG-ZHL-SCHEDULE | engine | `zhl-schedule-core.js:1` | 657 | P0 | READ | - |
| ENG-VPM | engine | `vpm-engine-core.js:1` | 2099 | P0 | READ | - |
| ENG-VPM-REFERENCE | engine_reference | `vpmb.py:1` | 2574 | P2 | READ | - |
| ENG-RDP | engine | `padi-engine.js:1` | 101 | P1 | READ | - |
| APP-ANDROID-SELECT | native_bridge | `android-select-picker.js:1` | 270 | P1 | READ | - |
| APP-CAPACITOR-BRIDGE | native_bridge | `capacitor-bridge.js:1` | 278 | P1 | READ | - |
| APP-CONTINGENCY | ui_core | `contingency-core.js:1` | 562 | P1 | READ | - |
| APP-EXPORT | ui_core | `export-core.js:1` | 3255 | P2 | READ | - |
| APP-GAS-PLAN | ui_core | `gas-plan-core.js:1` | 546 | P1 | READ | - |
| APP-GAS-TABLE | ui_core | `gas-table-core.js:1` | 302 | P2 | READ | - |
| APP-SURFACE-INTERVAL | ui_core | `surf-interval-core.js:1` | 372 | P1 | READ | - |
| APP-SERVICE-WORKER | pwa | `sw.js:1` | 298 | P1 | READ | - |
| APP-ZHL-WORKER-BRIDGE | worker | `zhl-worker-bridge.js:1` | 136 | P1 | READ | - |
| APP-ZHL-WORKER | worker | `zhl-schedule-worker.js:1` | 23 | P1 | READ | - |
| APP-DOWNLOAD | web_runtime | `download.html:1` | 119 | P3 | READ | - |
| APP-MANIFEST | pwa | `manifest.json:1` | 41 | P2 | READ | - |
| APP-VERSION | release_config | `version.json:1` | 7 | P2 | UNREAD | - |
| APP-CAPACITOR-CONFIG | native_config | `capacitor.config.json:1` | 14 | P1 | READ | - |
| APP-CLOUDFLARE-CONFIG | deploy_config | `wrangler.jsonc:1` | 14 | P2 | READ | - |
| APP-PACKAGE | build_config | `package.json:1` | 40 | P1 | READ | - |
| APP-NODE-VERSION | build_config | `.nvmrc:1` | 1 | P2 | READ | - |
| NATIVE-MAIN-ACTIVITY | native_android | `android/app/src/main/java/com/threecats/lsp/dplannerplus/MainActivity.java:1` | 61 | P1 | READ | - |
| NATIVE-MANIFEST | native_android | `android/app/src/main/AndroidManifest.xml:1` | 50 | P1 | READ | - |
| NATIVE-BUILD-ROOT | native_android | `android/build.gradle:1` | 29 | P2 | UNREAD | - |
| NATIVE-BUILD-APP | native_android | `android/app/build.gradle:1` | 82 | P1 | READ | - |
| NATIVE-SETTINGS | native_android | `android/settings.gradle:1` | 5 | P2 | UNREAD | - |
| NATIVE-VARIABLES | native_android | `android/variables.gradle:1` | 16 | P2 | UNREAD | - |
| NATIVE-LAYOUT | native_android | `android/app/src/main/res/layout/activity_main.xml:1` | 12 | P2 | UNREAD | - |
| NATIVE-FILE-PATHS | native_android | `android/app/src/main/res/xml/file_paths.xml:1` | 9 | P1 | READ | - |
| NATIVE-STRINGS | native_android | `android/app/src/main/res/values/strings.xml:1` | 7 | P2 | UNREAD | - |
| NATIVE-STYLES | native_android | `android/app/src/main/res/values/styles.xml:1` | 26 | P2 | UNREAD | - |
| NATIVE-COLORS | native_android | `android/app/src/main/res/values/colors.xml:1` | 7 | P3 | UNREAD | - |
| NATIVE-LAUNCHER-BG | native_android | `android/app/src/main/res/values/ic_launcher_background.xml:1` | 4 | P3 | UNREAD | - |
| NATIVE-DRAWABLE-BG | native_android | `android/app/src/main/res/drawable/ic_launcher_background.xml:1` | 170 | P3 | UNREAD | - |
| NATIVE-DRAWABLE-FG | native_android | `android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml:1` | 34 | P3 | UNREAD | - |
| NATIVE-ICON | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml:1` | 5 | P3 | UNREAD | - |
| NATIVE-ICON-ROUND | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml:1` | 5 | P3 | UNREAD | - |
| TEST-ENGINE-REGRESSION | test_infrastructure | `dev/engine_regression.py:1` | 2200 | P1 | READ | - |
| TEST-ISSUE-140-REGRESSION | test_infrastructure | `dev/issue140_regression.py:1` | 99 | P1 | IN_PROGRESS | - |
| TEST-GAS-CORE-REGRESSION | test_infrastructure | `dev/gas_core_regression.py:1` | 129 | P1 | READ | - |
| TEST-ISSUE-141-REGRESSION | test_infrastructure | `dev/issue141_regression.py:1` | 108 | P1 | IN_PROGRESS | - |
| TEST-ISSUE-142-REGRESSION | test_infrastructure | `dev/surf_interval_regression.py:1` | 124 | P1 | IN_PROGRESS | - |
| TEST-ANDROID-COMPILE | test_infrastructure | `dev/run_android_compile_check.py:1` | 101 | P2 | IN_PROGRESS | - |
| TEST-ENGINE-VALIDATION | test_infrastructure | `engine_validation_regression.py:1` | 521 | P1 | READ | - |
| TEST-CCR-VALIDATION | test_infrastructure | `dev/ccr_engine_validation_regression.py:1` | 359 | P1 | READ | - |
| TEST-EXPORT | test_infrastructure | `export_regression.py:1` | 596 | P2 | IN_PROGRESS | - |
| TEST-RUN-ALL | test_infrastructure | `dev/run_all_regression.py:1` | 36 | P1 | READ | - |
| TEST-BROWSER-RUNNER | test_infrastructure | `dev/run_browser_regression.py:1` | 191 | P2 | UNREAD | - |
| TEST-NATIVE-RUNNER | test_infrastructure | `dev/run_native_regression.py:1` | 264 | P2 | UNREAD | - |
| TEST-CCR-DIFF-RUNNER | test_infrastructure | `dev/run_ccr_differential.py:1` | 110 | P1 | READ | - |
| TEST-PSCR-E2E | test_infrastructure | `dev/validate_pscr_e2e.py:1` | 435 | P1 | READ | REG-46 |
| TEST-SW-LIFECYCLE | test_infrastructure | `dev/sw_lifecycle_test.py:1` | 86 | P1 | READ | REG-45 |
| TEST-PLAYWRIGHT-BOOT | test_infrastructure | `dev/playwright_boot.py:1` | 54 | P2 | UNREAD | - |
| TEST-HTTP | test_infrastructure | `dev/test_http.py:1` | 101 | P2 | UNREAD | - |
| TEST-LEGACY | test_infrastructure | `dev/legacy.js:1` | 517 | P3 | UNREAD | - |
| TEST-HARNESS | test_infrastructure | `lsp-test-harness.js:1` | 155 | P1 | IN_PROGRESS | - |
| TEST-MAIN | test_infrastructure | `tests.html:1` | 848 | P2 | UNREAD | - |
| TEST-EXTENDED | test_infrastructure | `tests-extended.html:1` | 1312 | P2 | UNREAD | - |
| TEST-MASSIVE | test_infrastructure | `tests-massive.html:1` | 4104 | P2 | UNREAD | - |
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
| TOOL-AUDIT-COVERAGE | tooling | `tools/audit_coverage.py:1` | 453 | P1 | IN_PROGRESS | - |
| TOOL-AUDIT-COVERAGE-TEST | test_infrastructure | `tools/test_audit_coverage.py:1` | 211 | P1 | IN_PROGRESS | - |
| TOOL-BUILD-PAGES | tooling | `tools/build_pages_site.py:1` | 144 | P2 | IN_PROGRESS | - |
| TOOL-BUILD-VPM | tooling | `tools/build_vpm_bundle.py:1` | 104 | P1 | READ | - |
| TOOL-BUILD-ZHL | tooling | `tools/build_zhl_bundle.py:1` | 390 | P1 | IN_PROGRESS | - |
| TOOL-CHECK-PARITY | tooling | `tools/check_engine_parity.py:1` | 311 | P1 | IN_PROGRESS | - |
| TOOL-RUN-AUDIT-COVERAGE-SUITE-PY | tooling | `tools/run_audit_coverage_suite.py:1` | 52 | P0 | IN_PROGRESS | - |
| TOOL-EXTRACT-UI | tooling | `tools/extract_ui_cores.py:1` | 474 | P2 | IN_PROGRESS | - |
| TOOL-EXTRACT-ZHL | tooling | `tools/extract_zhl_core.py:1` | 124 | P2 | UNREAD | - |
| TOOL-INSERT-ZHL | tooling | `tools/insert_zhl_tier2.py:1` | 223 | P3 | UNREAD | - |
| TOOL-MERGE-CCR | tooling | `tools/merge_ccr_into_plus.py:1` | 477 | P3 | UNREAD | - |
| TOOL-PATCH-DECO | tooling | `tools/patch_run_deco_schedule.py:1` | 66 | P3 | UNREAD | - |
| TOOL-PATCH-SCHEDULE | tooling | `tools/patch_schedule_core_ccr.py:1` | 215 | P3 | UNREAD | - |
| TOOL-PATCH-TIER3 | tooling | `tools/patch_tier3_index.py:1` | 244 | P3 | UNREAD | - |
| TOOL-PATCH-VPM | tooling | `tools/patch_vpm_bundle_index.py:1` | 25 | P3 | UNREAD | - |
| TOOL-PATCH-ZHL | tooling | `tools/patch_zhl_engine.py:1` | 121 | P3 | UNREAD | - |
| TOOL-SYNC-WWW | tooling | `tools/sync_www.py:1` | 119 | P1 | IN_PROGRESS | - |
| TOOL-UPDATE-VERSION | tooling | `tools/update_sw_version.py:1` | 104 | P2 | READ | - |
| TOOL-VENDOR | tooling | `tools/vendor_offline_assets.py:1` | 173 | P2 | UNREAD | - |
| TOOL-VERIFY-ASSETS | tooling | `tools/verify_site_assets.py:1` | 132 | P2 | READ | - |
| CI-AUDIT | ci | `.github/workflows/audit.yml:1` | 131 | P1 | READ | - |
| CI-APK | ci | `.github/workflows/build-apk.yml:1` | 161 | P1 | READ | - |
| CI-MAIN | ci | `.github/workflows/ci.yml:1` | 189 | P1 | READ | - |
| CI-DEPLOY | ci | `.github/workflows/deploy.yml:1` | 128 | P1 | READ | - |
| CI-NOTIFY | ci | `.github/workflows/notify-site.yml:1` | 50 | P2 | READ | - |
| CI-OFFLINE-ZIP | ci | `.github/workflows/build-offline-zip.yml:1` | 119 | P2 | READ | - |
| TOOL-AUDIT-V2-__INIT__-PY | tooling | `tools/audit/__init__.py:1` | 3 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-__MAIN__-PY | tooling | `tools/audit/__main__.py:1` | 5 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-CLI-PY | tooling | `tools/audit/cli.py:1` | 188 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-LEGACY_V1-PY | tooling | `tools/audit/legacy_v1.py:1` | 7446 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-MIGRATE_V2-PY | tooling | `tools/audit/migrate_v2.py:1` | 185 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-MODEL-PY | tooling | `tools/audit/model.py:1` | 72 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-PARSER_BRIDGE-MJS | tooling | `tools/audit/parser_bridge.mjs:1` | 125 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-REGISTRY-PY | tooling | `tools/audit/registry.py:1` | 228 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-REPORTING-PY | tooling | `tools/audit/reporting.py:1` | 92 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-RULES-PY | tooling | `tools/audit/rules.py:1` | 194 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-RUNNER-PY | tooling | `tools/audit/runner.py:1` | 99 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-CASE_REPORT-PY | tooling | `tools/audit/case_report.py:1` | 93 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-SUITE_EMIT-PY | tooling | `tools/audit/suite_emit.py:1` | 32 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-WORKSPACE-PY | tooling | `tools/audit/workspace.py:1` | 89 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-AUDIT-LEGACY-MIGRATION-JSON | tooling | `docs/audit-legacy-migration.json:1` | 31876 | P0 | IN_PROGRESS | - |
| TOOL-AUDIT-V2-TEST_SYSTEM-PY | tooling | `tools/audit/test_system.py:1` | 184 | P0 | IN_PROGRESS | - |
| UI-PLANNER-SHELL | ui_shell | `planner-shell.js:1` | 205 | P1 | READ | - |
| UI-RESULTS-PANEL | ui_shell | `results-panel.js:1` | 301 | P1 | READ | - |
| TOOL-V3-ASSEMBLE_UI_HTML-PY | tooling | `tools/assemble_ui_html.py:1` | 122 | P2 | IN_PROGRESS | - |
| TOOL-V3-EXTRACT_UI_CSS-PY | tooling | `tools/extract_ui_css.py:1` | 136 | P2 | IN_PROGRESS | - |
| TOOL-V3-MIGRATE_V3-PY | tooling | `tools/audit/migrate_v3.py:1` | 407 | P2 | IN_PROGRESS | - |
| TOOL-V3-RUN_UI_STRUCTURE_SUITE-PY | tooling | `tools/run_ui_structure_suite.py:1` | 94 | P2 | IN_PROGRESS | - |
| TOOL-V3-UI_ASSETS-PY | tooling | `tools/ui_assets.py:1` | 54 | P2 | IN_PROGRESS | - |
| TOOL-V3-VERIFY_SW_ASSETS-PY | tooling | `tools/verify_sw_assets.py:1` | 59 | P2 | IN_PROGRESS | - |
| TOOL-V3-TEST_UI_STRUCTURE_SUITE-PY | tooling | `tools/test_ui_structure_suite.py:1` | 29 | P2 | IN_PROGRESS | - |
| TOOL-V3-RESET-CYCLES-V3-PY | tooling | `tools/audit/reset_cycles_v3.py:1` | 219 | P2 | IN_PROGRESS | - |
| TOOL-V3-RUN-V3-AUTOMATION-PY | tooling | `tools/audit/run_v3_automation.py:1` | 217 | P2 | IN_PROGRESS | - |
