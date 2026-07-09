# V3 Unit Audit — Final Report

**Generated:** 2026-07-03T02:15:13+00:00
**Epoch:** v3-full-reset
**Static gate:** `python -m tools.audit check --profile static` → PASS

## Summary

- Units promoted READ this run: **79**
- Units blocked: **0**
- Registry: READ=170

## Promoted units

| Unit | Layer | Path | Closed at |
|------|-------|------|-----------|
| TOOL-AUDIT-V2-AUDIT-LEGACY-MIGRATION-JSON | tooling | `docs/audit-legacy-migration.json` | 2026-07-03T02:10:59+00:00 |
| TOOL-AUDIT-V2-CASE_REPORT-PY | tooling | `tools/audit/case_report.py` | 2026-07-03T02:11:02+00:00 |
| TOOL-AUDIT-V2-CLI-PY | tooling | `tools/audit/cli.py` | 2026-07-03T02:11:05+00:00 |
| TOOL-AUDIT-V2-LEGACY_V1-PY | tooling | `tools/audit/legacy_v1.py` | 2026-07-03T02:11:07+00:00 |
| TOOL-AUDIT-V2-MIGRATE_V2-PY | tooling | `tools/audit/migrate_v2.py` | 2026-07-03T02:11:09+00:00 |
| TOOL-AUDIT-V2-MODEL-PY | tooling | `tools/audit/model.py` | 2026-07-03T02:11:11+00:00 |
| TOOL-AUDIT-V2-PARSER_BRIDGE-MJS | tooling | `tools/audit/parser_bridge.mjs` | 2026-07-03T02:11:12+00:00 |
| TOOL-AUDIT-V2-REGISTRY-PY | tooling | `tools/audit/registry.py` | 2026-07-03T02:11:14+00:00 |
| TOOL-AUDIT-V2-REPORTING-PY | tooling | `tools/audit/reporting.py` | 2026-07-03T02:11:16+00:00 |
| TOOL-AUDIT-V2-RULES-PY | tooling | `tools/audit/rules.py` | 2026-07-03T02:11:19+00:00 |
| TOOL-AUDIT-V2-RUNNER-PY | tooling | `tools/audit/runner.py` | 2026-07-03T02:11:21+00:00 |
| TOOL-AUDIT-V2-SUITE_EMIT-PY | tooling | `tools/audit/suite_emit.py` | 2026-07-03T02:11:23+00:00 |
| TOOL-AUDIT-V2-TEST_SYSTEM-PY | tooling | `tools/audit/test_system.py` | 2026-07-03T02:12:31+00:00 |
| TOOL-AUDIT-V2-WORKSPACE-PY | tooling | `tools/audit/workspace.py` | 2026-07-03T02:12:34+00:00 |
| TOOL-AUDIT-V2-__INIT__-PY | tooling | `tools/audit/__init__.py` | 2026-07-03T02:12:36+00:00 |
| TOOL-AUDIT-V2-__MAIN__-PY | tooling | `tools/audit/__main__.py` | 2026-07-03T02:12:38+00:00 |
| TOOL-RUN-AUDIT-COVERAGE-SUITE-PY | tooling | `tools/run_audit_coverage_suite.py` | 2026-07-03T02:12:40+00:00 |
| TEST-HARNESS | test_infrastructure | `lsp-test-harness.js` | 2026-07-03T02:12:42+00:00 |
| TEST-ISSUE-140-REGRESSION | test_infrastructure | `dev/issue140_regression.py` | 2026-07-03T02:12:44+00:00 |
| TEST-ISSUE-141-REGRESSION | test_infrastructure | `dev/issue141_regression.py` | 2026-07-03T02:12:45+00:00 |
| TEST-ISSUE-142-REGRESSION | test_infrastructure | `dev/surf_interval_regression.py` | 2026-07-03T02:12:47+00:00 |
| TEST-PSCR-OTU-CNS | test_infrastructure | `tests-pscr-otu-cns.html` | 2026-07-03T02:12:49+00:00 |
| TOOL-AUDIT | tooling | `audit.py` | 2026-07-03T02:12:51+00:00 |
| TOOL-AUDIT-COVERAGE | tooling | `tools/audit_coverage.py` | 2026-07-03T02:12:53+00:00 |
| TOOL-AUDIT-COVERAGE-TEST | test_infrastructure | `tools/test_audit_coverage.py` | 2026-07-03T02:12:55+00:00 |
| TOOL-BUILD-ZHL | tooling | `tools/build_zhl_bundle.py` | 2026-07-03T02:12:57+00:00 |
| TOOL-CHECK-PARITY | tooling | `tools/check_engine_parity.py` | 2026-07-03T02:12:59+00:00 |
| TOOL-SYNC-WWW | tooling | `tools/sync_www.py` | 2026-07-03T02:13:02+00:00 |
| APP-VERSION | release_config | `version.json` | 2026-07-03T02:13:04+00:00 |
| NATIVE-BUILD-ROOT | native_android | `android/build.gradle` | 2026-07-03T02:13:05+00:00 |
| NATIVE-LAYOUT | native_android | `android/app/src/main/res/layout/activity_main.xml` | 2026-07-03T02:13:08+00:00 |
| NATIVE-SETTINGS | native_android | `android/settings.gradle` | 2026-07-03T02:13:11+00:00 |
| NATIVE-STRINGS | native_android | `android/app/src/main/res/values/strings.xml` | 2026-07-03T02:13:14+00:00 |
| NATIVE-STYLES | native_android | `android/app/src/main/res/values/styles.xml` | 2026-07-03T02:13:16+00:00 |
| NATIVE-VARIABLES | native_android | `android/variables.gradle` | 2026-07-03T02:13:17+00:00 |
| TEST-ANDROID-COMPILE | test_infrastructure | `dev/run_android_compile_check.py` | 2026-07-03T02:13:19+00:00 |
| TEST-BROWSER-RUNNER | test_infrastructure | `dev/run_browser_regression.py` | 2026-07-03T02:13:21+00:00 |
| TEST-CAP-FIXTURE | test_infrastructure | `dev/fixtures/capacitor-bridge.html` | 2026-07-03T02:13:22+00:00 |
| TEST-CCR-DIFF-BUILD | test_infrastructure | `tests/ccr-differential/build_assets.py` | 2026-07-03T02:13:24+00:00 |
| TEST-EXPORT | test_infrastructure | `export_regression.py` | 2026-07-03T02:13:26+00:00 |
| TEST-EXTENDED | test_infrastructure | `tests-extended.html` | 2026-07-03T02:13:28+00:00 |
| TEST-HTTP | test_infrastructure | `dev/test_http.py` | 2026-07-03T02:13:29+00:00 |
| TEST-MAIN | test_infrastructure | `tests.html` | 2026-07-03T02:13:31+00:00 |
| TEST-MASSIVE | test_infrastructure | `tests-massive.html` | 2026-07-03T02:13:33+00:00 |
| TEST-MASSIVE-MAIN | test_infrastructure | `tests-massive-main.html` | 2026-07-03T02:13:35+00:00 |
| TEST-NATIVE-FIXTURE | test_infrastructure | `dev/fixtures/native-select.html` | 2026-07-03T02:13:37+00:00 |
| TEST-NATIVE-RUNNER | test_infrastructure | `dev/run_native_regression.py` | 2026-07-03T02:13:38+00:00 |
| TEST-PLAYWRIGHT-BOOT | test_infrastructure | `dev/playwright_boot.py` | 2026-07-03T02:13:41+00:00 |
| TEST-VERIFY | test_infrastructure | `tests-verify.html` | 2026-07-03T02:13:43+00:00 |
| TOOL-BUILD-PAGES | tooling | `tools/build_pages_site.py` | 2026-07-03T02:13:45+00:00 |
| TOOL-EXTRACT-UI | tooling | `tools/extract_ui_cores.py` | 2026-07-03T02:13:46+00:00 |
| TOOL-EXTRACT-ZHL | tooling | `tools/extract_zhl_core.py` | 2026-07-03T02:13:48+00:00 |
| TOOL-V3-ASSEMBLE_UI_HTML-PY | tooling | `tools/assemble_ui_html.py` | 2026-07-03T02:13:50+00:00 |
| TOOL-V3-EXTRACT_UI_CSS-PY | tooling | `tools/extract_ui_css.py` | 2026-07-03T02:13:53+00:00 |
| TOOL-V3-MIGRATE_V3-PY | tooling | `tools/audit/migrate_v3.py` | 2026-07-03T02:13:55+00:00 |
| TOOL-V3-RESET-CYCLES-V3-PY | tooling | `tools/audit/reset_cycles_v3.py` | 2026-07-03T02:13:57+00:00 |
| TOOL-V3-RUN-V3-AUTOMATION-PY | tooling | `tools/audit/run_v3_automation.py` | 2026-07-03T02:13:58+00:00 |
| TOOL-V3-RUN-V3-UNITS-AUTOMATION-PY | tooling | `tools/audit/run_v3_units_automation.py` | 2026-07-03T02:14:00+00:00 |
| TOOL-V3-RUN_UI_STRUCTURE_SUITE-PY | tooling | `tools/run_ui_structure_suite.py` | 2026-07-03T02:14:02+00:00 |
| TOOL-V3-TEST_UI_STRUCTURE_SUITE-PY | tooling | `tools/test_ui_structure_suite.py` | 2026-07-03T02:14:04+00:00 |
| TOOL-V3-UI_ASSETS-PY | tooling | `tools/ui_assets.py` | 2026-07-03T02:14:06+00:00 |
| TOOL-V3-VERIFY_SW_ASSETS-PY | tooling | `tools/verify_sw_assets.py` | 2026-07-03T02:14:08+00:00 |
| TOOL-VENDOR | tooling | `tools/vendor_offline_assets.py` | 2026-07-03T02:14:10+00:00 |
| NATIVE-COLORS | native_android | `android/app/src/main/res/values/colors.xml` | 2026-07-03T02:14:12+00:00 |
| NATIVE-DRAWABLE-BG | native_android | `android/app/src/main/res/drawable/ic_launcher_background.xml` | 2026-07-03T02:14:13+00:00 |
| NATIVE-DRAWABLE-FG | native_android | `android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml` | 2026-07-03T02:14:15+00:00 |
| NATIVE-ICON | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml` | 2026-07-03T02:14:17+00:00 |
| NATIVE-ICON-ROUND | native_android | `android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml` | 2026-07-03T02:14:19+00:00 |
| NATIVE-LAUNCHER-BG | native_android | `android/app/src/main/res/values/ic_launcher_background.xml` | 2026-07-03T02:14:21+00:00 |
| TEST-ANDROID-INSTRUMENTED | test_infrastructure | `android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java` | 2026-07-03T02:14:22+00:00 |
| TEST-ANDROID-UNIT | test_infrastructure | `android/app/src/test/java/com/getcapacitor/myapp/ExampleUnitTest.java` | 2026-07-03T02:14:24+00:00 |
| TEST-LEGACY | test_infrastructure | `dev/legacy.js` | 2026-07-03T02:14:26+00:00 |
| TOOL-INSERT-ZHL | tooling | `tools/insert_zhl_tier2.py` | 2026-07-03T02:14:28+00:00 |
| TOOL-MERGE-CCR | tooling | `tools/merge_ccr_into_plus.py` | 2026-07-03T02:14:29+00:00 |
| TOOL-PATCH-DECO | tooling | `tools/patch_run_deco_schedule.py` | 2026-07-03T02:14:31+00:00 |
| TOOL-PATCH-SCHEDULE | tooling | `tools/patch_schedule_core_ccr.py` | 2026-07-03T02:14:33+00:00 |
| TOOL-PATCH-TIER3 | tooling | `tools/patch_tier3_index.py` | 2026-07-03T02:14:35+00:00 |
| TOOL-PATCH-VPM | tooling | `tools/patch_vpm_bundle_index.py` | 2026-07-03T02:14:37+00:00 |
| TOOL-PATCH-ZHL | tooling | `tools/patch_zhl_engine.py` | 2026-07-03T02:14:39+00:00 |

## Notes

- Each unit required static audit PASS before promotion to READ.
- Tooling units additionally passed py_compile or targeted test smoke where applicable.

