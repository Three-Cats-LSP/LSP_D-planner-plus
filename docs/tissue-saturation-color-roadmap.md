# Tissue Saturation Color Roadmap

## Status

- Planned for Seven-Lens Cycle 26 (`UI-TOOLS-TISSUES`).
- Not part of Cycle 8 and must not delay or alter Cycle 8 closure evidence.
- Implementation must preserve decompression calculations and change presentation only.

## Product Contract

Replace the current three-color tissue-saturation display with a value-based seven-band scale. Color represents saturation relative to the applicable GF-adjusted M-value; it must never be assigned from compartment number alone.

| Saturation | Color role |
|---:|---|
| 0% to below 20% | Cyan |
| 20% to below 40% | Teal |
| 40% to below 60% | Green |
| 60% to below 75% | Lime |
| 75% to below 90% | Yellow |
| 90% to 100% | Orange |
| Above 100% | Red |

The exact numeric percentage and a clearly labelled 100% reference line remain mandatory. Color is supplemental information and must not be the only way to identify loading or an over-limit value.

## Implementation Scope

- Apply the same canonical mapping to surface-saturation bars, compartment-detail rows, per-stop saturation views, legends, tooltips, and tissue-related exports.
- Define semantic color tokens that remain distinguishable in light and dark themes and under common color-vision deficiencies.
- Keep all 16 compartments readable at desktop, mobile-web, and Android viewport sizes.
- Preserve values above 100% without clipping the number or hiding the over-limit state.
- Update the in-app Tissue Saturation help text to describe the seven bands accurately.
- Re-review `UI-CSS-RESULTS`, `APP-EXPORT`, and any generated markup changed by the implementation; preserve canonical/generated parity.

## Regression Contract

- Test both sides of every threshold, including exact boundary values.
- Verify identical band selection across the chart, table, per-stop view, tooltip, and export consumers.
- Verify the 100% reference line, numeric labels, status text, and accessible names without relying on pixel color alone.
- Exercise light and dark themes at desktop, portrait-mobile, and landscape-mobile viewports.
- Include representative values below 0%, from 0% through 100%, exactly 100%, and above 100%; invalid non-finite inputs must not create misleading colors.
- Require clean browser console/page-error output and stable layout with all 16 compartments.
