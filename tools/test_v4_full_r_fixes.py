"""Static + structure regressions for cursor_full_R_audit.md fixer findings."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestV4FullRFixes(unittest.TestCase):
    def test_export_uses_data_label_not_fragile_indexes_in_messenger(self) -> None:
        src = (ROOT / "export-core.js").read_text(encoding="utf-8")
        # Shared helpers present
        self.assertIn("function readExportScheduleCells", src)
        self.assertIn("function exportShortMix", src)
        self.assertIn("function applyVpmPlanSummaryFallback", src)
        self.assertIn("function exportCnsHighlightTier", src)
        # Messenger / contingency paths must not assign run/mix from raw c[3]/c[4]
        messenger = src.split("function buildMessengerText", 1)[1].split("// ── Download .txt file", 1)[0]
        self.assertNotRegex(messenger, r"shortMix\(c\[3\]\)")
        self.assertNotRegex(messenger, r"shortMix\(cv\[3\]\)")
        self.assertNotRegex(messenger, r"const run\s*=\s*c\[4\]")
        self.assertIn("readExportScheduleCells(tr, clean)", messenger)
        # Switch rows in text export use data-label path
        self.assertIn(">> ${shortMix(cells.mix", src)
        self.assertNotIn("if(false){", src)

    def test_vpm_pdf_uses_shared_totals_fallback(self) -> None:
        src = (ROOT / "export-core.js").read_text(encoding="utf-8")
        self.assertIn(
            "const planSumPdf = applyVpmPlanSummaryFallback(getPlanSummaryExport(totalsRowEl), btVal);",
            src,
        )
        self.assertIn("exportCnsHighlightTier(tr)", src)
        self.assertIn("data-cns-tier", (ROOT / "results-render-core.js").read_text(encoding="utf-8"))

    def test_gas_plan_adequacy_helper_shared(self) -> None:
        gp = (ROOT / "gas-plan-core.js").read_text(encoding="utf-8")
        ex = (ROOT / "export-core.js").read_text(encoding="utf-8")
        self.assertIn("function gasPlanAdequacyStatus", gp)
        self.assertIn("gasPlanAdequacyStatus(", ex)
        self.assertNotRegex(ex, r"reqL\s*\*\s*1\.10")

    def test_slate_runtime_does_not_fallback_to_bottom_time(self) -> None:
        src = (ROOT / "export-core.js").read_text(encoding="utf-8")
        slate = src.split("function buildSlateText", 1)[1].split("function showSlate", 1)[0]
        self.assertIn("applyVpmPlanSummaryFallback", slate)
        self.assertNotIn("decoBT')?.value || '-'}'00", slate)
        self.assertNotRegex(slate, r"runTime:\s*_slSum\.runTime\s*===\s*'-'")

    def test_pdf_slate_page_break_is_conditional(self) -> None:
        src = (ROOT / "export-core.js").read_text(encoding="utf-8")
        self.assertIn("function startNewPdfSectionPage()", src)
        slate_pdf = src.split("const _pdfSlate = buildSlateText();", 1)[1].split("// HIGH CNS% alert", 1)[0]
        self.assertIn("startNewPdfSectionPage();", slate_pdf)
        self.assertNotIn("doc.addPage();\n    drawHeader();", slate_pdf)

    def test_gas_supply_middle_tier_uses_low_wording(self) -> None:
        rr = (ROOT / "results-render-core.js").read_text(encoding="utf-8")
        css = (ROOT / "lsp-dplanner-results.css").read_text(encoding="utf-8")
        ex = (ROOT / "export-core.js").read_text(encoding="utf-8")
        self.assertIn("return 'low';", rr)
        self.assertIn(".gas-usage-card--low", css)
        self.assertIn("status === 'low'", ex)
        self.assertNotIn("gas-usage-card--caution", css)

    def test_si_results_panel_metric_stamp(self) -> None:
        src = (ROOT / "surf-interval-core.js").read_text(encoding="utf-8")
        self.assertIn('data-si-metric="1"', src)
        self.assertIn("dataset.depthM=this.value", src)
        self.assertIn("el.dataset.siMetric === '1'", src)

    def test_rec_buhlmann_uses_block_card(self) -> None:
        src = (ROOT / "schedule-runner-core.js").read_text(encoding="utf-8")
        self.assertIn("ndlExceededNoDeco", src)
        self.assertGreaterEqual(src.count("rec-block-card"), 2)
        self.assertNotIn("function injectTtsCells", src)

    def test_android_a2hs_and_select_a11y(self) -> None:
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("lspAndroidA2hsDismissed", html)
        picker = (ROOT / "android-select-picker.js").read_text(encoding="utf-8")
        self.assertIn("aria-expanded", picker)
        self.assertIn("aria-controls", picker)

    def test_rec_block_card_css_present(self) -> None:
        css = (ROOT / "lsp-dplanner-results.css").read_text(encoding="utf-8")
        self.assertIn(".rec-block-card", css)
        self.assertNotIn(".col-tts", css)


if __name__ == "__main__":
    unittest.main()
