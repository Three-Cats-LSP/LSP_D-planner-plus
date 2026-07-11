# CSS `!important` Audit

Date: 2026-07-11

This pass cleaned conflict-driven `!important` rules from editable source CSS and JS while preserving hard overrides that still serve a real state, accessibility, or export purpose. Generated copies under `www/`, `_pages/`, Android web assets, vendor/bundled code, and offline ZIP output are excluded from the source policy.

## What Changed

| Area | Action |
| --- | --- |
| Gas warnings and gas consumption cards | Removed wildcard child force rules and replaced them with explicit component selectors for inline warnings, titles, measurements, and narcotic/deco alerts. |
| Light-theme overrides | Removed broad forced component colors and converted them to normal scoped token rules. |
| Schedule and gas-plan rows | Removed legacy inline and CSS `!important` color fights from gas tight rows, gas cells, totals rows, and JS-rendered warning/status cells. |
| Buttons, reset controls, GF fields, APK banner | Removed old style-force rules where normal selector specificity is enough. |
| Mobile header/layout spacing | Removed padding/width/justification hard overrides and left only true visibility state toggles. |
| Guardrail | Added `tools.test_ui_structure_suite.UiStructureSuiteTests.test_unapproved_important_overrides_are_blocked`. New `!important` usage now fails unless it matches an allowed category. |

## Allowed Categories

| Category | Why It Remains |
| --- | --- |
| Android native select hiding | Native WebView selects are visually hidden behind the custom Android picker; the native control must remain inaccessible visually but present structurally. |
| Mobile shell/tab state | Mobile plan/results/tools/settings visibility is still controlled by shell state classes that must beat desktop layout rules. |
| Algorithm/panel state | Buhlmann-only panels and legacy panels still need hard visibility boundaries until the old panel system is fully removed. |
| Print/PDF capture | Export capture must override live tab and mobile state to render a complete PDF page. |
| Reduced motion | Accessibility setting must reliably disable transitions/transforms. |
| Explicit disabled mode locks | Rec/tools mode locks must prevent accidental interaction with controls that remain in the DOM. |

## Follow-Up

The remaining `!important` rules are now documented and guarded. Future cleanup should target one category at a time, replacing each with a clearer JS-owned state class or removing the legacy DOM path entirely.
