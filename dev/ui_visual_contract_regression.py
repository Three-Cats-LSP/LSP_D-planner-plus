#!/usr/bin/env python3
"""Cross-unit visual contracts for the technical planner and results shell."""
from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "dev") not in sys.path:
    sys.path.insert(0, str(ROOT / "dev"))

from playwright_boot import boot_app_page  # noqa: E402
from playwright_restore import CAPTURE_PROBE_STATE_JS, restore_probe_state  # noqa: E402
from test_http import serve_www  # noqa: E402
from tools.audit.suite_emit import case_row, finish_suite  # noqa: E402


CASE_IDS = (
    "SL-VIS-GAS-DOT-SINGLE-SOURCE",
    "SL-VIS-GAS-SWITCH-TOKEN-PARITY",
    "SL-VIS-DESKTOP-TWO-COLUMN-LAYOUT",
    "SL-VIS-DECO-BANNER-GAS-LABELS",
    "SL-VIS-SWITCH-ROW-THEME-PARITY",
    "V4-UI-VISUAL-MOBILE-NAV-TILE-GRID",
    "V4-UI-VISUAL-OPERATIONAL-GAS-LABEL-FORMAT",
    "V4-UI-VISUAL-MOBILE-BOTTOM-TAB-SHELL",
    "SL-C09-GAS-SWITCH-TERMINOLOGY",
    "SL-C09-MOBILE-WARNING-WRAP",
    "SL-C09-VPM-MODE-TOGGLE",
    "SL-C09-VPM-CONTINGENCY-GAS-LOSS-STABLE",
    "SL-C09-VPM-BEYOND-MOD-BLOCKS",
    "SL-C09-TRAVEL-GAS-TRIMIX-CARD",
    "SL-C09-CONTINGENCY-COPY-PLAN-CONTEXT",
    "SL-C09-SCHEDULE-COLUMN-GEOMETRY",
    "SL-C09-SWITCH-ROW-BACKGROUND-PARITY",
    "SL-C09-GRAPH-WAYPOINT-TIME-SPREAD",
    "SL-C09-MOBILE-TISSUE-TAB-VISIBLE",
    "SL-C09-SUMMARY-CHIP-PALETTE",
    "SL-C09-RESULT-TABS-GAP",
    "SL-C09-HIGH-CNS-DECO-ALERT",
    "SL-VIS-GAS-CONSUMPTION-BARS",
    "SL-VIS-CONTINGENCY-GAS-CONSUMPTION-BARS",
    "SL-VIS-CONTINGENCY-MAIN-DECO-LAYOUT",
    "SL-VIS-GAS-CONSUMPTION-VOLUME-FIRST-UNITS",
    "SL-C09-ZHL-BEYOND-MOD-BLOCKS",
    "SL-C09-VPM-GRAPH-WAYPOINT-MONOTONIC",
    "SL-BATCH2-VPM-ERROR-COLSPAN",
    "SCHEDULE-ERROR-ROW-COLUMN-CONTRACT",
    "VPM-INVALID-ERROR-ROW-GEOMETRY",
    "SCHEDULE-CANONICAL-GAS-LABELS",
)

NAV_VIEWPORTS = (
    (375, 667),
    (400, 800),
    (480, 800),
    (667, 375),
    (1280, 800),
)

NAV_BTN_IDS = (
    "navBtnRec",
    "navBtnBuh",
    "navBtnVpm",
    "navBtnTools",
    "navBtnSettings",
)

BOTTOM_NAV_VIEWPORTS = (
    (375, 667),
    (667, 375),
    (1280, 800),
)

GENERATE_JS = r"""
async () => {
  window._zhlHeadless = false;
  setMainNav('buh');
  const depth = document.getElementById('tecDepth');
  const bt = document.getElementById('tecBT');
  if (depth) depth.value = '40';
  if (bt) bt.value = '30';
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 40; i++) {
    await new Promise(resolve => setTimeout(resolve, 250));
    if (document.querySelectorAll('#decoTableBody tr').length >= 5
        && document.querySelector('.gas-pills .deco1')) return true;
  }
  return false;
}
"""


CAPTURE_JS = r"""
() => {
  const rgb = value => value.replace(/\s+/g, '').toLowerCase();
  const style = (el, prop) => el ? getComputedStyle(el)[prop] : '';
  const resolveColor = value => {
    const probe = document.createElement('span');
    probe.style.color = value;
    document.body.appendChild(probe);
    const resolved = rgb(getComputedStyle(probe).color);
    probe.remove();
    return resolved;
  };
  const root = getComputedStyle(document.body);
  if (typeof drawDecoProfileFull === 'function') drawDecoProfileFull();
  const title = document.getElementById('diluentCardTitle');
  const titleRow = title?.closest('.gas-card-title-row');
  const dots = titleRow ? titleRow.querySelectorAll('.gas-dot') : [];
  const decoDots = [...document.querySelectorAll('.deco-gas-card .gas-dot')];
  const pills = [...document.querySelectorAll('#resultsPanel .gas-pills .gas-pill')];
  const gasSummary = document.getElementById('gasConsumptionSummary');
  const gasCards = [...document.querySelectorAll('#gasConsumptionSummary .gas-usage-card')];
  const gasLabels = gasCards.map(el => el.dataset.gasLabel || el.querySelector('.gas-usage-mix')?.textContent?.trim() || '');
  const gasFooters = gasCards.map(el => el.querySelector('.gas-usage-foot')?.textContent?.trim() || '');
  const gasRemaining = gasCards.map(el => el.querySelector('.gas-usage-remaining')?.textContent?.trim() || '');
  const gasScales = gasCards.map(el => el.querySelector('.gas-usage-scale')?.textContent?.trim() || '');
  const gasUnitSpans = [...document.querySelectorAll('#gasConsumptionSummary .gas-unit, #gasWarningBanner .gas-unit')];
  const gasMeasureSpans = [...document.querySelectorAll('#gasConsumptionSummary .gas-measure, #gasWarningBanner .gas-measure')];
  const gasUnitStyleOk = gasUnitSpans.length > 0 && gasUnitSpans.every(unit => {
    const value = unit.closest('.gas-measure')?.querySelector('.gas-value');
    if (!value) return true;
    const unitSize = parseFloat(getComputedStyle(unit).fontSize);
    const valueSize = parseFloat(getComputedStyle(value).fontSize);
    const weight = getComputedStyle(unit).fontWeight;
    return unitSize < valueSize && (parseInt(weight, 10) >= 700 || weight === 'bold');
  });
  const gasBarWidths = gasCards.map(el => {
    const remaining = el.querySelector('.gas-usage-remaining-bar');
    return remaining ? remaining.getBoundingClientRect().width : 0;
  });
  const gasTracks = gasCards.map(el => {
    const track = el.querySelector('.gas-usage-track');
    return track ? track.getBoundingClientRect().width : 0;
  });
  const switchRows = [...document.querySelectorAll('#resultsPanel .schedule-table tr[data-phase="switch"]')];
  const switchCells = switchRows.flatMap(row =>
    [...row.querySelectorAll('td:not([data-label="PPO2"])')]
  );
  const schedule = document.querySelector('#resultsPanel .schedule-table');
  const scheduleWrap = schedule?.closest('.schedule-wrap');
  const firstBodyRow = schedule?.querySelector('tbody tr:not([data-phase="switch"]):not(.row-summary)');
  const firstSwitchRow = schedule?.querySelector('tbody tr[data-phase="switch"]');
  const normalRowBg = rgb(style(firstBodyRow, 'backgroundColor'));
  const switchRowBgs = switchRows.map(row => rgb(style(row, 'backgroundColor')));
  const headers = schedule ? [...schedule.querySelectorAll('thead th')] : [];
  const cells = firstBodyRow ? [...firstBodyRow.querySelectorAll('td')] : [];
  const scheduleSwitchCells = firstSwitchRow ? [...firstSwitchRow.querySelectorAll('td')] : [];
  const headerTexts = headers.slice(1).map(el => (el.textContent || '').trim());
  const nonSummaryRows = schedule ? [...schedule.querySelectorAll('tbody tr[data-phase]:not(.row-summary)')] : [];
  const decoPhaseTexts = schedule
    ? [...schedule.querySelectorAll('tbody tr[data-phase="deco"] td:first-child')]
      .map(el => (el.textContent || '').trim())
    : [];
  const decoPhaseIcons = schedule
    ? [...schedule.querySelectorAll('tbody tr[data-phase="deco"] td:first-child .ph-deco svg')]
      .map(svg => {
        const circles = [...svg.querySelectorAll('circle')];
        return {
          circleCount: circles.length,
          outlineCircleCount: circles.filter(circle => (circle.getAttribute('fill') || '').toLowerCase() === 'none').length,
        };
      })
    : [];
  const ttsCells = schedule ? [...schedule.querySelectorAll('td[data-label="TTS"]')] : [];
  const geom = (el) => {
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    return { left: rect.left, right: rect.right, width: rect.width, center: rect.left + rect.width / 2 };
  };
  const depthHead = geom(headers[1]);
  const stopHead = geom(headers[2]);
  const runHead = geom(headers[3]);
  const mixHead = geom(headers[4]);
  const depthCell = geom(cells[1]);
  const stopCell = geom(cells[2]);
  const runCell = geom(cells[3]);
  const mixCell = geom(cells[4]);
  const switchMixCell = geom(scheduleSwitchCells[4]);
  const phaseCell = geom(cells[0]);
  const scheduleReadableCells = schedule ? [...schedule.querySelectorAll('thead th, tbody tr:not(.row-summary) td')] : [];
  const clippedScheduleCells = scheduleReadableCells.filter(el => {
    const cs = getComputedStyle(el);
    return (cs.overflowX === 'hidden' || cs.textOverflow === 'ellipsis') && el.scrollWidth > el.clientWidth + 1;
  }).map(el => ({
    text: (el.textContent || '').trim(),
    clientWidth: el.clientWidth,
    scrollWidth: el.scrollWidth,
    overflowX: getComputedStyle(el).overflowX,
    textOverflow: getComputedStyle(el).textOverflow,
  }));
  const scheduleRect = schedule ? schedule.getBoundingClientRect() : null;
  const scheduleWrapRect = scheduleWrap ? scheduleWrap.getBoundingClientRect() : null;
  const planner = document.getElementById('tecPlannerView')?.getBoundingClientRect();
  const results = document.getElementById('resultsPanel')?.getBoundingClientRect();
  const expectedBg = resolveColor(root.getPropertyValue('--gas-switch-label-bg'));
  const expectedSwitch = resolveColor('#d6ff00');
  const expectedText = resolveColor(root.getPropertyValue('--gas-switch-label-text'));
  const expectedDecoPillBg = resolveColor('#d6ff00');
  const expectedDecoPillText = resolveColor('#166534');
  const decoDotColors = decoDots.map(el => rgb(style(el, 'backgroundColor')));
  const decoPills = pills.filter(el => el.classList.contains('deco1') || el.classList.contains('deco2'));
  const graphWps = Array.isArray(window._plannerWaypoints) ? window._plannerWaypoints : [];
  const decoStopTimes = graphWps
    .filter(wp => ['deco', 'safety', 'gasswitch'].includes(wp.type) && Number.isFinite(Number(wp.t)))
    .map(wp => Number(wp.t));
  const uniqueDecoStopTimes = [...new Set(decoStopTimes.map(t => Math.round(t * 10) / 10))];
  const resultTabsNav = document.getElementById('tecResultTabs');
  const tabButtons = resultTabsNav ? [...resultTabsNav.querySelectorAll('.result-tab-btn')] : [];
  const tissueTab = resultTabsNav?.querySelector('[data-tab="tissue"]');
  const bottomTissueTab = document.querySelector('#appBottomNav [data-result-tab="tissue"]');
  const tissueRect = tissueTab?.getBoundingClientRect();
  const bottomTissueRect = bottomTissueTab?.getBoundingClientRect();
  const tabsRect = resultTabsNav?.getBoundingClientRect();
  const bottomTabsRect = document.getElementById('appBottomNav')?.getBoundingClientRect();
  const metricStripRect = document.getElementById('resultMetricStrip')?.getBoundingClientRect();
  const activeResultPane = document.querySelector('#tecResultsPanel .result-tab-pane.active');
  const activePaneRect = activeResultPane?.getBoundingClientRect();
  const fullGraphCard = document.getElementById('fullDiveGraphCard');
  const fullGraphBody = fullGraphCard?.querySelector('.card-collapsible-body');
  const fullGraphCanvas = document.getElementById('plannerProfileCanvas');
  const fullGraphCanvasRect = fullGraphCanvas?.getBoundingClientRect();
  const fullGraphBodyRect = fullGraphBody?.getBoundingClientRect();
  const gfCurveCard = document.getElementById('gfCurveInlineCard');
  const chipByLabel = label => [...document.querySelectorAll('#resultChipRow .chip')]
    .find(el => (el.textContent || '').trim().startsWith(label));
  const chipSnapshot = el => el ? ({
    text: (el.textContent || '').trim(),
    color: rgb(style(el, 'color')),
    background: rgb(style(el, 'backgroundColor')),
    border: rgb(style(el, 'borderTopColor')),
    classes: el.className,
  }) : null;
  const metricCardBackground = rgb(style(document.querySelector('#resultMetricStrip .metric-card'), 'backgroundColor'));
  const runtimeTextColor = rgb(style(document.querySelector('#resultMetricStrip .metric-val--runtime'), 'color'));
  const decoTextColor = rgb(style(document.querySelector('#resultMetricStrip .metric-val--deco'), 'color'));
  const statusGreen = resolveColor(root.getPropertyValue('--status-green'));
  const statusOrange = resolveColor(root.getPropertyValue('--status-orange'));
  const statusRed = resolveColor(root.getPropertyValue('--status-red'));
  const decoPlanCard = document.querySelector('#resultsPanel .deco-plan-card');
  const hazardAlert = document.querySelector('#resultsPanel #decoAlerts .alert.deco, #resultsPanel .gas-consumption-narcotic .alert.narcotic-warn');
  const decoPlanCardStyle = decoPlanCard ? {
    background: rgb(style(decoPlanCard, 'backgroundColor')),
    border: rgb(style(decoPlanCard, 'borderTopColor')),
    titleColor: rgb(style(decoPlanCard.querySelector('.deco-plan-title'), 'color')),
    travelBackground: rgb(style(decoPlanCard.querySelector('.gas-pill.travel-gas'), 'backgroundColor')),
    travelColor: rgb(style(decoPlanCard.querySelector('.gas-pill.travel-gas'), 'color')),
    travelBorder: rgb(style(decoPlanCard.querySelector('.gas-pill.travel-gas'), 'borderTopColor')),
  } : null;
  const hazardAlertStyle = hazardAlert ? {
    background: rgb(style(hazardAlert, 'backgroundColor')),
    border: rgb(style(hazardAlert, 'borderTopColor')),
  } : null;
  return {
    title: title?.textContent?.trim() || '',
    bottomDotCount: dots.length,
    titleHasEmoji: /[\u{1F535}\u{1F7E1}\u{1F7E0}\u{1F7E2}]/u.test(title?.textContent || ''),
    expectedBg,
    expectedText,
    expectedDecoPillBg,
    expectedDecoPillText,
    decoDotColors,
    pillTexts: pills.map(el => el.textContent.trim()),
    decoPillBackgrounds: decoPills.map(el => rgb(style(el, 'backgroundColor'))),
    decoPillColors: decoPills.map(el => rgb(style(el, 'color'))),
    decoPlanCardStyle,
    hazardAlertStyle,
    hasTravelPill: pills.some(el => el.classList.contains('travel-gas')),
    switchRowCount: switchRows.length,
    switchCellColors: switchCells.map(el => rgb(style(el, 'color'))),
    switchRowBackgrounds: switchRowBgs,
    normalRowBackground: normalRowBg,
    expectedSwitch,
    resultTabs: {
      labels: tabButtons.map(btn => btn.textContent.trim()),
      tabs: tabButtons.map(btn => btn.dataset.tab),
      hasGraphsTab: !!resultTabsNav?.querySelector('[data-tab="graphs"]'),
      tissueLabel: tissueTab?.textContent.trim() || '',
      gfInsideTissue: !!(gfCurveCard && document.getElementById('resultTab-tissue')?.contains(gfCurveCard)),
      graphInsideProfile: !!(fullGraphCard && document.getElementById('resultTab-profile')?.contains(fullGraphCard)),
      simpleGraphRemoved: !document.getElementById('decoProfileCanvas') && !document.getElementById('diveGraphCard'),
      graphLegendRemoved: document.querySelectorAll('#plannerProfileLegend .profile-legend-table, #decoProfileLegend .profile-legend-table').length === 0,
      fullGraphWithinBody: !!(fullGraphCanvasRect && fullGraphBodyRect && fullGraphCanvasRect.left >= fullGraphBodyRect.left - 1 && fullGraphCanvasRect.right <= fullGraphBodyRect.right + 1),
    },
    graphWaypoints: {
      count: decoStopTimes.length,
      uniqueCount: uniqueDecoStopTimes.length,
      minTime: decoStopTimes.length ? Math.min(...decoStopTimes) : 0,
      maxTime: decoStopTimes.length ? Math.max(...decoStopTimes) : 0,
      times: uniqueDecoStopTimes.slice(0, 20),
    },
    tissueTab: tissueTab && tissueRect && tabsRect ? {
      text: tissueTab.textContent.trim(),
      display: getComputedStyle(tissueTab).display,
      visible: tissueRect.width > 20 && tissueRect.height > 10,
      withinNav: tissueRect.left >= tabsRect.left - 1 && tissueRect.right <= tabsRect.right + 1,
    } : null,
    mobileBottomTissueTab: bottomTissueTab && bottomTissueRect && bottomTabsRect ? {
      text: bottomTissueTab.textContent.trim(),
      display: getComputedStyle(bottomTissueTab).display,
      visible: bottomTissueRect.width > 20 && bottomTissueRect.height > 10,
      withinNav: bottomTissueRect.left >= bottomTabsRect.left - 1 && bottomTissueRect.right <= bottomTabsRect.right + 1,
    } : null,
    resultTabsGap: tabsRect && activePaneRect ? {
      gap: (metricStripRect || activePaneRect).top - tabsRect.bottom,
      tabsBottom: tabsRect.bottom,
      metricTop: metricStripRect ? metricStripRect.top : null,
      metricBeforePane: metricStripRect ? metricStripRect.bottom <= activePaneRect.top : true,
      paneTop: activePaneRect.top,
    } : null,
    summaryChips: {
      surfGF: chipSnapshot(chipByLabel('Surf GF')),
      otu: chipSnapshot(chipByLabel('OTU')),
      tts: chipSnapshot(chipByLabel('TTS')),
      decozone: chipSnapshot(chipByLabel('Decozone')),
      metricCardBackground,
      runtimeTextColor,
      decoTextColor,
      statusColors: [statusGreen, statusOrange, statusRed],
    },
    scheduleColumns: {
      headerTexts,
      hasTtsHeader: headerTexts.some(text => text.toUpperCase() === 'TTS'),
      ttsCellCount: ttsCells.length,
      rowCellCounts: nonSummaryRows.map(row => row.cells.length),
      depthHead,
      stopHead,
      runHead,
      mixHead,
      depthCell,
      stopCell,
      runCell,
      mixCell,
      switchMixCell,
      phaseCell,
      tableLayout: schedule ? getComputedStyle(schedule).tableLayout : '',
      tableWidth: scheduleRect?.width || 0,
      wrapWidth: scheduleWrapRect?.width || 0,
      wrapOverflowX: scheduleWrap ? getComputedStyle(scheduleWrap).overflowX : '',
      clippedCells: clippedScheduleCells,
      decoPhaseTexts,
      decoPhaseIcons,
      decoStopPlainBullets: decoPhaseTexts.some(text => text)
        ? decoPhaseTexts.every(text => text === '\u25cf')
        : decoPhaseIcons.length > 0
          && decoPhaseIcons.every(icon => icon.circleCount === 1 && icon.outlineCircleCount === 0),
      depthAligned: !!(depthHead && depthCell && Math.abs(depthHead.center - depthCell.center) <= 4),
      stopAligned: !!(stopHead && stopCell && Math.abs(stopHead.center - stopCell.center) <= 4),
      runBeforeMix: !!(runHead && mixHead && runHead.center < mixHead.center),
      sevenCellsPerRow: nonSummaryRows.length > 0 && nonSummaryRows.every(row => row.cells.length === 8),
      noVisibleTts: !headerTexts.some(text => text.toUpperCase() === 'TTS') && ttsCells.length === 0,
      depthCompact: !!(depthHead && stopHead && mixHead && phaseCell && (
        window.innerWidth <= 640
          ? depthHead.width <= 42 && depthHead.width < mixHead.width && depthHead.width >= phaseCell.width
          : depthHead.width <= stopHead.width * 1.05 && depthHead.width < mixHead.width && depthHead.width >= phaseCell.width
      )),
      mixLaneAligned: !!(mixHead && mixCell && switchMixCell && Math.abs(mixHead.center - mixCell.center) <= 4 && Math.abs(mixCell.center - switchMixCell.center) <= 4),
      mixCompact: !!(mixHead && runHead && (
        window.innerWidth <= 640 ? mixHead.width <= 50 : mixHead.width <= runHead.width * 0.95
      )),
      mobileScrollReady: !schedule || window.innerWidth > 640 || !!(scheduleWrap && scheduleRect && scheduleWrapRect && scheduleRect.width <= scheduleWrapRect.width + 1 && getComputedStyle(scheduleWrap).overflowX !== 'scroll' && document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1),
    },
    gasConsumptionBars: {
      visible: !!(gasSummary && getComputedStyle(gasSummary).display !== 'none'),
      cardCount: gasCards.length,
      tableCount: document.querySelectorAll('#gasConsumptionSummary table.gas-plan-table').length,
      thresholdValue: document.getElementById('gasLowThresholdPct')?.value || '',
      labels: gasLabels,
      forbiddenLabels: gasLabels.filter(text => /EAN\d+/i.test(text)),
      hasAir: gasLabels.includes('Air'),
      hasO2: gasLabels.includes('100%'),
      hasDecoMix: gasLabels.some(text => /^\d{2}\/\d{2}$/.test(text)),
      footerTexts: gasFooters,
      remainingTexts: gasRemaining,
      scaleTexts: gasScales,
      compactUnits: [...gasRemaining, ...gasFooters, ...gasScales, document.getElementById('gasWarningBanner')?.textContent || ''].every(text => !/\d\s+(?:L|bar|psi|ftÃ‚Â³|ftÂ³|ft3)\b/i.test(text)),
      unitStyleOk: gasUnitStyleOk,
      measureBold: gasMeasureSpans.length > 0 && gasMeasureSpans.every(el => {
        const weight = getComputedStyle(el).fontWeight;
        return parseInt(weight, 10) >= 700 || weight === 'bold';
      }),
      hasTurnPressureInline: gasFooters.some(text => /Used:.*Turn Pressure:/i.test(text)),
      hasTurnPressColumn: /TURN\s+PRESS(?!URE)/i.test(gasSummary?.textContent || ''),
      barsPresent: gasCards.length > 0 && gasCards.every((el, i) => !!el.querySelector('.gas-usage-track') && !!el.querySelector('.gas-usage-remaining-bar') && gasBarWidths[i] >= 0 && gasTracks[i] > 0),
      remainingBarModel: gasCards.length > 0 && gasCards.every(el => !el.querySelector('.gas-usage-used')),
      metricUnits: gasRemaining.every(text => /\dL\b/.test(text) && /\(.*bar\)/.test(text))
        && gasFooters.every(text => /Used:\s*\d+(?:\.\d+)?L\s*\(.*bar\)/i.test(text))
        && gasScales.every(text => /\dL\b/.test(text) && /\(.*bar\)/.test(text)),
      metricVolumeFirst: gasRemaining.every(text => /^\d+(?:\.\d+)?L\s*\(/.test(text))
        && gasFooters.every(text => /Used:\s*\d+(?:\.\d+)?L\s*\(/i.test(text))
        && gasScales.every(text => /0\d+(?:\.\d+)?L\s*\(/.test(text)),
      sufficientLeftBorderOnly: gasCards.some(el => el.classList.contains('gas-usage-card--ok') && parseFloat(getComputedStyle(el).borderLeftWidth) > parseFloat(getComputedStyle(el).borderTopWidth)),
    },
    layout: planner && results ? {
      plannerLeft: planner.left,
      plannerRight: planner.right,
      resultsLeft: results.left,
      plannerTop: planner.top,
      resultsTop: results.top,
      sideBySide: results.left >= planner.right - 1 && Math.abs(results.top - planner.top) <= 2,
    } : null,
  };
}
"""

NAV_GRID_PROBE_JS = r"""
async (btnIds) => {
  const nav = document.getElementById('mainNavBar');
  if (!nav) return { ok: false, reason: 'missing_nav' };
  const navRect = nav.getBoundingClientRect();
  const cols = getComputedStyle(nav).gridTemplateColumns.split(' ').filter(Boolean).length;
  const width = window.innerWidth;
  const portrait = width <= 420;
  const tablet = width > 420 && width <= 720;
  const desktop = width > 720;

  const borderVisible = (el, side) => {
    const cs = getComputedStyle(el);
    const prop = side === 'bottom' ? 'borderBottomWidth' : 'borderRightWidth';
    const style = side === 'bottom' ? cs.borderBottomStyle : cs.borderRightStyle;
    return parseFloat(cs[prop]) > 0 && style !== 'none';
  };

  const probeBtn = (id) => {
    const el = document.getElementById(id);
    if (!el) return null;
    const rect = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return {
      id,
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height,
      gridColumn: cs.gridColumnStart + '/' + cs.gridColumnEnd,
      gridRow: cs.gridRowStart + '/' + cs.gridRowEnd,
      borderBottom: borderVisible(el, 'bottom'),
      borderRight: borderVisible(el, 'right'),
      active: el.classList.contains('active'),
    };
  };

  const orphanProbe = () => {
    const settings = document.getElementById('navBtnSettings');
    if (!settings) return { orphan: true, reason: 'missing_settings' };
    const sRect = settings.getBoundingClientRect();
    const x = sRect.right + Math.max(4, (navRect.right - sRect.right) / 2);
    const y = sRect.top + sRect.height / 2;
    if (x >= navRect.right - 2) return { orphan: false };
    const hit = document.elementFromPoint(x, y);
    const orphan = !hit || (hit.id !== 'navBtnSettings' && !hit.classList?.contains('main-nav-btn'));
    return { orphan, hitId: hit?.id || null, x, y };
  };

  const activeRuns = [];
  for (const id of btnIds) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.click();
    await new Promise(r => setTimeout(r, 80));
    const buttons = btnIds.map(probeBtn).filter(Boolean);
    const tools = buttons.find(b => b.id === 'navBtnTools');
    const settings = buttons.find(b => b.id === 'navBtnSettings');
    const areaSum = buttons.reduce((sum, b) => sum + b.width * b.height, 0);
    const coverage = areaSum / Math.max(1, navRect.width * navRect.height);
  const settingsFullRow = !portrait || (settings && settings.width >= navRect.width * 0.9);
    const toolsSeparated = !portrait || (tools && tools.borderBottom);
    const desktopEqual = desktop && buttons.length === 5
      && buttons.every(b => Math.abs(b.width - navRect.width / 5) < navRect.width * 0.08);
    const tabletFilled = !tablet || (
      settings && settings.gridColumn.includes('span')
        ? settings.width >= navRect.width * 0.55
        : settings && settings.width >= navRect.width * 0.28
    );
    const orphan = orphanProbe();
    activeRuns.push({
      activeId: id,
      buttons,
      coverage,
      settingsFullRow,
      toolsSeparated,
      desktopEqual,
      tabletFilled,
      orphan,
      cols,
    });
  }

  document.getElementById('navBtnBuh')?.click();
  await new Promise(r => setTimeout(r, 50));

  const finalButtons = btnIds.map(probeBtn).filter(Boolean);
  const finalOrphan = orphanProbe();
  const toolsFinal = finalButtons.find(b => b.id === 'navBtnTools');
  const settingsFinal = finalButtons.find(b => b.id === 'navBtnSettings');

  const ok = activeRuns.every(run => {
    if (run.orphan.orphan) return false;
    if (portrait && !run.settingsFullRow) return false;
    if (portrait && !run.toolsSeparated) return false;
    if (desktop && !run.desktopEqual) return false;
    if (tablet && !run.tabletFilled) return false;
    return run.buttons.length === 5;
  }) && !finalOrphan.orphan
    && (!portrait || (settingsFinal && settingsFinal.width >= navRect.width * 0.9))
    && (!portrait || (toolsFinal && toolsFinal.borderBottom));

  return {
    ok,
    width,
    portrait,
    tablet,
    desktop,
    cols,
    navRect: { width: navRect.width, height: navRect.height },
    finalButtons,
    finalOrphan,
    activeRuns,
  };
}
"""

GAS_LABEL_PROBE_JS = r"""
async () => {
  const forbidden = /\bEAN\s*\d+\b|\bEAN\d+\b|(?<!100)\b\d{1,2}%\b|\b[0-9]\/(?:\d{2}|\d)\b/i;
  const canonicalCases = [
    [0.21, 0, 'Air'],
    [1.0, 0, '100%'],
    [0.50, 0, '50/00'],
    [0.80, 0, '80/00'],
    [0.32, 0, '32/00'],
    [0.18, 0.45, '18/45'],
    [0.08, 0.70, '08/70'],
  ];
  const canonical = canonicalCases.map(([o2, he, expected]) => {
    const actual = getGasLabel(o2, he);
    const bundleActual = ZhlEngineBundle?.getGasLabel?.(o2, he);
    return {
      expected,
      actual,
      bundleActual,
      ok: actual === expected && bundleActual === expected,
    };
  });

  const setMix = (id, val) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = val;
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const setCustomTrimix = (prefix, o2, he) => {
    setMix(`${prefix}Mix`, 'trimix');
    const o2El = document.getElementById(`${prefix}TrimixO2`);
    const heEl = document.getElementById(`${prefix}TrimixHe`);
    if (o2El) { o2El.value = String(o2); o2El.dispatchEvent(new Event('input', { bubbles: true })); }
    if (heEl) { heEl.value = String(he); heEl.dispatchEvent(new Event('input', { bubbles: true })); }
  };

  window._zhlHeadless = false;
  setMainNav('buh');
  setMix('dg1Mix', 'ean50');
  setMix('dg2Mix', 'ean80');
  setCustomTrimix('dg3', 18, 45);
  setCustomTrimix('dg4', 8, 70);
  setMix('dg5Mix', 'o2');

  const depth = document.getElementById('tecDepth');
  const bt = document.getElementById('tecBT');
  if (depth) depth.value = '50';
  if (bt) bt.value = '20';
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  let generated = false;
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 250));
    if (document.querySelectorAll('#decoTableBody tr').length >= 5) {
      generated = true;
      break;
    }
  }

  const collectTexts = () => {
    const texts = [];
    document.querySelectorAll('#decoTableBody td[data-label="Mix"], #decoTableBody tr[data-phase="switch"] td[data-label="Mix"]')
      .forEach(td => texts.push(td.textContent.trim()));
    document.querySelectorAll('#resultsPanel .gas-pills .gas-pill')
      .forEach(el => texts.push(el.textContent.trim()));
    if (typeof buildExportText === 'function') texts.push(buildExportText('deco'));
    if (typeof buildContingencyText === 'function') {
      try { texts.push(buildContingencyText('lost_gas')); } catch (_) {}
    }
    return texts.filter(Boolean);
  };

  const labels = collectTexts();
  const joined = labels.join('\n');
  if (typeof addTravelGas === 'function') addTravelGas();
  setCustomTrimix('travelGas', 18, 45);
  if (typeof updateTravelGasMOD === 'function') updateTravelGasMOD();
  await new Promise(r => setTimeout(r, 50));
  const travelCard = document.getElementById('travelGasCard');
  const travelInfo = typeof getTravelGasInfo === 'function' ? getTravelGasInfo() : null;
  const travelCustomField = document.getElementById('travelGasCustomField');
  const travelO2Field = document.getElementById('travelGasTrimixO2Field');
  const travelHeField = document.getElementById('travelGasTrimixHeField');
  const travelModEl = document.getElementById('travelGasMODDisplay');
  const travelMod = travelModEl?.value || travelModEl?.textContent?.trim() || '';
  const travelSwitchDepth = document.getElementById('travelGasSwitchDepthDisplay')?.value || '';
  const travelMinOD = document.getElementById('travelGasMinODDisplay')?.value || '';
  const visible = el => !!el && getComputedStyle(el).display !== 'none' && el.getBoundingClientRect().width > 0;
  const travelTrimix = {
    optionExists: !!document.querySelector('#travelGasMix option[value="trimix"]'),
    cardVisible: visible(travelCard),
    customHidden: !!travelCustomField && getComputedStyle(travelCustomField).display === 'none',
    o2Visible: visible(travelO2Field),
    heVisible: visible(travelHeField),
    fieldCount: travelCard ? travelCard.querySelectorAll('.gas-card-grid .field').length : 0,
    mixField: !!travelCard?.querySelector('.gas-f-mix #travelGasMix'),
    modBadge: !!travelCard?.querySelector('.gas-mod#travelGasMODDisplay'),
    switchField: !!travelCard?.querySelector('.gas-f-switch #travelGasSwitchDepthDisplay'),
    minOdField: !!travelCard?.querySelector('.gas-f-switch #travelGasMinODDisplay'),
    noSwitchMode: !document.getElementById('travelGasSwitchMode') && !document.getElementById('travelGasManualDepth'),
    sizeFields: travelCard ? travelCard.querySelectorAll('.gas-f-num input').length : 0,
    customMin: document.getElementById('travelGasCustomO2')?.min || '',
    trimixMin: document.getElementById('travelGasTrimixO2')?.min || '',
    label: travelInfo?.label || '',
    fO2: travelInfo?.fO2,
    fHe: travelInfo?.fHe,
    fN2: travelInfo?.fN2,
    modText: travelMod,
    switchDepthText: travelSwitchDepth,
    modBadgeIsMod: /^MOD\s+\d+/.test(travelMod),
    switchUsesO2: /\(ppOÃ¢â€šâ€š\s+/.test(travelSwitchDepth) || /\(ppOâ‚‚\s+/.test(travelSwitchDepth) || /\(ppO2\s+/.test(travelSwitchDepth),
    minOdText: travelMinOD,
  };
  const forbiddenHits = (joined.match(new RegExp(forbidden.source, forbidden.flags + 'g')) || []);
  const terminologyRoots = [
    document.getElementById('resultsPanel'),
  ].filter(Boolean);
  const terminologyText = terminologyRoots.map(el => el.textContent || '').join('\n');
  const gasChangeTextHits = terminologyText.match(/Gas\s+change/gi) || [];
  const gasChangeContractHits = [...document.querySelectorAll('[id*="gas-change" i], [class*="gas-change" i]')]
    .map(el => ({ id: el.id || '', className: String(el.className || '') }));
  const operationalRequired = ['50/00', '80/00'];
  const operationalOk = operationalRequired.every(label => joined.includes(label));

  return {
    generated,
    canonical,
    canonicalOk: canonical.every(row => row.ok),
    labelsSample: labels.slice(0, 40),
    forbiddenHits: [...new Set(forbiddenHits)],
    operationalOk,
    travelTrimix,
    parityOk: canonical.every(row => row.actual === row.bundleActual),
    terminologyOk: gasChangeTextHits.length === 0
      && gasChangeContractHits.length === 0
      && /Gas\s+switch/i.test(terminologyText),
    gasChangeTextHits: [...new Set(gasChangeTextHits)],
    gasChangeContractHits,
  };
}
"""


MOBILE_WARNING_PROBE_JS = r"""
async () => {
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const rectInfo = (el) => {
    const rect = el.getBoundingClientRect();
    return {
      tag: el.tagName,
      id: el.id || '',
      className: String(el.className || ''),
      text: (el.textContent || '').trim().slice(0, 120),
      left: rect.left,
      right: rect.right,
      width: rect.width,
      clientWidth: el.clientWidth,
      scrollWidth: el.scrollWidth,
      overflowX: getComputedStyle(el).overflowX,
      whiteSpace: getComputedStyle(el).whiteSpace,
    };
  };

  window._zhlHeadless = false;
  setMainNav('buh');
  setVal('tecDepth', '40');
  setVal('tecBT', '30');
  setVal('cylBot_size', '1');
  setVal('cylBot_pres', '80');
  setVal('cylBot_reserve', '50');
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  let generated = false;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 250));
    if (document.querySelectorAll('#decoTableBody tr').length >= 5
        && getComputedStyle(document.getElementById('gasConsumptionSummary')).display !== 'none') {
      generated = true;
      break;
    }
  }

  const viewportWidth = document.documentElement.clientWidth;
  const candidates = [
    ...document.querySelectorAll('#decoAlerts .alert, #decoAlertsNarcotic .alert, #gasWarningBanner, .gas-usage-inline-warning, .gas-usage-card--critical, .gas-usage-card--nogas'),
  ].filter(el => {
    const style = getComputedStyle(el);
    const rect = el.getBoundingClientRect();
    return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
  });
  const checks = candidates.map(rectInfo);
  const overflow = checks.filter(row =>
    row.left < -1
    || row.right > viewportWidth + 1
    || row.scrollWidth > row.clientWidth + 2
    || row.whiteSpace === 'nowrap'
  );
  const bodyOverflow = document.documentElement.scrollWidth > viewportWidth + 1;
  const styleOf = el => {
    if (!el) return {};
    const s = getComputedStyle(el);
    return {
      fontFamily: s.fontFamily,
      fontSize: s.fontSize,
      fontWeight: s.fontWeight,
      letterSpacing: s.letterSpacing,
      lineHeight: s.lineHeight,
      gap: s.gap,
    };
  };
  const closePx = (a, b, tolerance = 0.75) => {
    const av = parseFloat(a);
    const bv = parseFloat(b);
    return Number.isFinite(av) && Number.isFinite(bv) && Math.abs(av - bv) <= tolerance;
  };
  const zeroLetterSpacing = value => value === 'normal' || Math.abs(parseFloat(value) || 0) <= 0.1;
  const gasWarningBanner = document.getElementById('gasWarningBanner');
  const gasWarningStyle = styleOf(gasWarningBanner);
  const inlineWarning = document.querySelector('.gas-usage-inline-warning');
  const criticalProbe = document.querySelector('.gas-usage-card--critical') || (() => {
    const host = document.querySelector('#gasConsumptionSummary .gas-consumption-bars') || document.body;
    const probe = document.createElement('div');
    probe.className = 'gas-usage-card gas-usage-card--critical';
    probe.style.position = 'absolute';
    probe.style.visibility = 'hidden';
    probe.style.pointerEvents = 'none';
    host.appendChild(probe);
    return probe;
  })();
  const noGasCard = document.querySelector('.gas-usage-card--nogas');
  const cardWarningStyle = styleOf(inlineWarning);
  const decoWarningStyle = styleOf(document.querySelector('#decoAlerts .alert, #decoAlertsNarcotic .alert'));
  const oldCardWarningCount = document.querySelectorAll('.gas-usage-card .gas-consumption-warning').length;
  const warningTypographyOk =
    /Outfit/i.test(cardWarningStyle.fontFamily || '')
    && closePx(gasWarningStyle.fontSize, decoWarningStyle.fontSize)
    && closePx(cardWarningStyle.fontSize, decoWarningStyle.fontSize)
    && closePx(cardWarningStyle.lineHeight, decoWarningStyle.lineHeight, 1.5)
    && parseInt(cardWarningStyle.fontWeight || '0', 10) >= 600
    && zeroLetterSpacing(cardWarningStyle.letterSpacing)
    && !/mono|JetBrains/i.test(cardWarningStyle.fontFamily || '');
  const topGasBannerHidden = !gasWarningBanner
    || getComputedStyle(gasWarningBanner).display === 'none'
    || !gasWarningBanner.textContent.trim();
  return {
    generated,
    viewportWidth,
    alertCount: document.querySelectorAll('#decoAlerts .alert, #decoAlertsNarcotic .alert').length,
    criticalGasCards: document.querySelectorAll('.gas-usage-card--critical, .gas-usage-card--nogas').length,
    noGasCards: document.querySelectorAll('.gas-usage-card--nogas').length,
    warningText: gasWarningBanner?.textContent?.trim() || '',
    cardWarningText: inlineWarning?.textContent?.trim() || '',
    warningIconText: document.querySelector('#gasWarningBanner > span[aria-hidden="true"]')?.textContent?.trim() || '',
    warningPseudoIconText: gasWarningBanner ? getComputedStyle(gasWarningBanner, '::before').content : '',
    warningIconCount: document.querySelectorAll('#gasWarningBanner > span[aria-hidden="true"]').length,
    topGasBannerHidden,
    cardWarningIconText: document.querySelector('.gas-usage-inline-warning span')?.textContent?.trim() || '',
    oldCardWarningCount,
    warningColor: document.getElementById('gasWarningBanner') ? getComputedStyle(document.getElementById('gasWarningBanner')).color.replace(/\s+/g, '').toLowerCase() : '',
    cardWarningColor: inlineWarning ? getComputedStyle(inlineWarning).color.replace(/\s+/g, '').toLowerCase() : '',
    warningBackground: document.getElementById('gasWarningBanner') ? getComputedStyle(document.getElementById('gasWarningBanner')).backgroundColor.replace(/\s+/g, '').toLowerCase() : '',
    cardWarningBackground: inlineWarning ? getComputedStyle(inlineWarning).backgroundColor.replace(/\s+/g, '').toLowerCase() : '',
    warningBorder: document.getElementById('gasWarningBanner') ? getComputedStyle(document.getElementById('gasWarningBanner')).borderTopColor.replace(/\s+/g, '').toLowerCase() : '',
    cardWarningBorder: inlineWarning ? getComputedStyle(inlineWarning).borderTopColor.replace(/\s+/g, '').toLowerCase() : '',
    gasWarningStyle,
    cardWarningStyle,
    decoWarningStyle,
    warningTypographyOk,
    criticalCardColor: criticalProbe ? getComputedStyle(criticalProbe).borderTopColor.replace(/\s+/g, '').toLowerCase() : '',
    noGasCardColor: noGasCard ? getComputedStyle(noGasCard).borderTopColor.replace(/\s+/g, '').toLowerCase() : '',
    noGasStatusColor: noGasCard ? getComputedStyle(noGasCard).getPropertyValue('--gas-status').trim().toLowerCase() : '',
    remainingTextColor: document.querySelector('.gas-usage-remaining') ? getComputedStyle(document.querySelector('.gas-usage-remaining')).color.replace(/\s+/g, '').toLowerCase() : '',
    remainingParenColor: document.querySelector('.gas-usage-remaining span') ? getComputedStyle(document.querySelector('.gas-usage-remaining span')).color.replace(/\s+/g, '').toLowerCase() : '',
    remainingFontWeight: document.querySelector('.gas-usage-remaining') ? getComputedStyle(document.querySelector('.gas-usage-remaining')).fontWeight : '',
    remainingParenFontWeight: document.querySelector('.gas-usage-remaining span') ? getComputedStyle(document.querySelector('.gas-usage-remaining span')).fontWeight : '',
    usedTextColor: document.querySelector('.gas-usage-foot') ? getComputedStyle(document.querySelector('.gas-usage-foot')).color.replace(/\s+/g, '').toLowerCase() : '',
    usedMeasureColor: document.querySelector('.gas-usage-foot .gas-measure') ? getComputedStyle(document.querySelector('.gas-usage-foot .gas-measure')).color.replace(/\s+/g, '').toLowerCase() : '',
    checks,
    overflow,
    bodyScrollWidth: document.documentElement.scrollWidth,
    bodyOverflow,
    ok: generated
      && candidates.length >= 2
      && document.querySelectorAll('.gas-usage-card--nogas').length >= 1
      && /Bottom|Air|No gas supply|Critical/i.test(inlineWarning?.textContent || '')
      && (document.querySelector('.gas-usage-inline-warning span')?.textContent?.trim()?.charCodeAt(0) === 9888)
      && !(inlineWarning?.textContent || '').trim().startsWith('!')
      && oldCardWarningCount === 0
      && warningTypographyOk
      && overflow.length === 0
      && !bodyOverflow,
  };
}
"""


VPM_MODE_PROBE_JS = r"""
async () => {
  window._zhlHeadless = false;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const visible = id => {
    const el = document.getElementById(id);
    if (!el) return false;
    const style = getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && el.getBoundingClientRect().width > 0;
  };
  const state = () => ({
    plannerAlgo: typeof plannerAlgo !== 'undefined' ? plannerAlgo : null,
    algorithmSelect: document.getElementById('algorithmSelect')?.value || '',
    vpmVariant: typeof vpmVariant !== 'undefined' ? vpmVariant : null,
    navVpmActive: document.getElementById('navBtnVpm')?.classList.contains('active') === true,
    vpmRowVisible: visible('vpmModeRowV3'),
    conservatismVisible: visible('conservatismRowV3'),
    gfVisible: visible('gfPresetsRowV3'),
    gfLabel: document.getElementById('gfPresetsLabelV3')?.textContent?.trim() || '',
    subtitle: document.getElementById('algoSubtitle')?.textContent?.trim() || '',
    toggleSide: document.getElementById('vpmModeToggle')?.dataset.side || '',
  });
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const gasButtonState = () => [...document.querySelectorAll('#gasLossButtons .cont-gas-btn')].map(btn => ({
    id: btn.id,
    text: (btn.textContent || '').trim(),
    border: getComputedStyle(btn).borderTopColor.replace(/\s+/g, '').toLowerCase(),
    color: getComputedStyle(btn).color.replace(/\s+/g, '').toLowerCase(),
    active: btn.id === ('contGas-' + (typeof contGasLose !== 'undefined' ? contGasLose : '')),
  }));

  setPlannerAlgo('VPMB');
  await wait(250);
  const vpm = state();
  document.getElementById('vpmModeToggle')?.click();
  await wait(250);
  const gfs = state();
  document.getElementById('vpmModeToggle')?.click();
  await wait(250);
  const back = state();

  if (typeof setMainNav === 'function') setMainNav('vpm');
  if (typeof setPlannerAlgo === 'function') setPlannerAlgo('VPMB');
  await wait(250);
  setVal('tecDepth', '40');
  setVal('tecBT', '25');
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 80; i++) {
    await wait(250);
    if (document.querySelectorAll('#decoTableBody tr[data-phase]').length >= 5
      && document.querySelectorAll('#gasLossButtons .cont-gas-btn').length >= 2) break;
  }
  if (typeof switchResultTab === 'function') {
    switchResultTab('contingency', document.querySelector('#tecResultTabs [data-tab="contingency"]'));
  }
  if (typeof buildContingencyButtons === 'function'
    && document.querySelectorAll('#gasLossButtons .cont-gas-btn').length < 2) {
    buildContingencyButtons();
  }
  await wait(250);
  const beforeGasButtons = gasButtonState();
  const lossBtn = beforeGasButtons.find(btn => btn.id !== 'contGas-none' && btn.id !== 'contGas-both');
  if (lossBtn) document.getElementById(lossBtn.id)?.click();
  await wait(100);
  const selectedBeforeCalc = typeof contGasLose !== 'undefined' ? contGasLose : '';
  if (typeof calcContingency === 'function') calcContingency();
  for (let i = 0; i < 80; i++) {
    await wait(250);
    if (document.querySelector('#contingencyResult .schedule-table')
      && document.querySelectorAll('#emergencyGasConsumption .gas-usage-card').length > 0) break;
  }
  const afterGasButtons = gasButtonState();
  const selectedAfterCalc = typeof contGasLose !== 'undefined' ? contGasLose : '';
  const emergencyGas = document.getElementById('emergencyGasConsumption');
  const emergencyGasCards = [...document.querySelectorAll('#emergencyGasConsumption .gas-usage-card')];
  const emergencyGasWarning = document.querySelector('#emergencyGasConsumption .gas-usage-inline-warning');
  const emergencyGasVisible = !!emergencyGas
    && getComputedStyle(emergencyGas).display !== 'none'
    && emergencyGas.getBoundingClientRect().width > 100;
  const mainGasCards = [...document.querySelectorAll('#gasConsumptionSummary .gas-usage-card')];
  const vpmContingencyGasOk = !!lossBtn
    && beforeGasButtons.length >= 2
    && afterGasButtons.length === beforeGasButtons.length
    && afterGasButtons.some(btn => btn.id === lossBtn.id)
    && selectedBeforeCalc === selectedAfterCalc
    && selectedAfterCalc === lossBtn.id.replace('contGas-', '')
    && afterGasButtons.some(btn => btn.id === lossBtn.id && btn.active)
    && emergencyGasVisible
    && emergencyGasCards.length > 0
    && !document.querySelector('#emergencyGasConsumption table.gas-plan-table');

  const ok = vpm.plannerAlgo === 'VPMB'
    && vpm.algorithmSelect === 'VPMB'
    && vpm.navVpmActive
    && vpm.vpmRowVisible
    && vpm.conservatismVisible
    && !vpm.gfVisible
    && gfs.plannerAlgo === 'VPMB_GFS'
    && gfs.algorithmSelect === 'VPMB_GFS'
    && gfs.vpmRowVisible
    && gfs.conservatismVisible
    && gfs.gfVisible
    && /GFS\s*Hi/i.test(gfs.gfLabel)
    && back.plannerAlgo === 'VPMB'
    && back.algorithmSelect === 'VPMB'
    && !back.gfVisible;
  return {
    vpm, gfs, back, ok,
    vpmContingencyGas: {
      beforeGasButtons,
      afterGasButtons,
      selectedBeforeCalc,
      selectedAfterCalc,
      picked: lossBtn?.id || '',
      labelsCanonical: afterGasButtons.concat(beforeGasButtons).every(btn => !/\bEAN\s*\d+\b|\bEAN\d+\b/i.test(btn.text))
        && afterGasButtons.some(btn => /^50\/00$/i.test(btn.text)),
      scenarioCanonical: !/\bEAN\s*\d+\b|\bEAN\d+\b/i.test(document.getElementById('contingencyResult')?.textContent || ''),
      emergencyGasVisible,
      emergencyGasCardCount: emergencyGasCards.length,
      emergencyGasWarningText: emergencyGasWarning?.textContent?.trim() || '',
      mainGasCardCount: mainGasCards.length,
      ok: vpmContingencyGasOk,
    },
  };
}
"""


CONTINGENCY_GAS_PROBE_JS = r"""
async () => {
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  window._zhlHeadless = false;
  setMainNav('buh');
  setVal('tecDepth', '40');
  setVal('tecBT', '30');
  setVal('cylBot_size', '1');
  setVal('cylBot_pres', '80');
  setVal('cylBot_reserve', '50');
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  let generated = false;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 250));
    if (document.querySelectorAll('#decoTableBody tr').length >= 5) {
      generated = true;
      break;
    }
  }
  if (typeof switchResultTab === 'function') {
    switchResultTab('contingency', document.querySelector('#tecResultTabs [data-tab="contingency"]'));
  }
  if (typeof selectContBT === 'function') selectContBT(3);
  if (typeof calcContingency === 'function') calcContingency();
  if (typeof switchResultTab === 'function') {
    switchResultTab('contingency', document.querySelector('#tecResultTabs [data-tab="contingency"]'));
  }
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 250));
    if (typeof switchResultTab === 'function') {
      switchResultTab('contingency', document.querySelector('#tecResultTabs [data-tab="contingency"]'));
    }
    const graphReady = document.getElementById('contingencyProfileCanvas')?.getBoundingClientRect()?.width > 100;
    const gasReady = document.querySelectorAll('#emergencyGasConsumption .gas-usage-card').length > 0;
    if (graphReady && gasReady) break;
  }
  const emergency = document.getElementById('emergencyGasConsumption');
  const cards = [...document.querySelectorAll('#emergencyGasConsumption .gas-usage-card')];
  const warnings = [...document.querySelectorAll('#emergencyGasConsumption .gas-usage-inline-warning, #emergencyGasConsumption .gas-usage-card--critical, #emergencyGasConsumption .gas-usage-card--nogas')];
  const unitSpans = [...document.querySelectorAll('#emergencyGasConsumption .gas-unit')];
  const measureSpans = [...document.querySelectorAll('#emergencyGasConsumption .gas-measure')];
  const unitStyleOk = unitSpans.length > 0 && unitSpans.every(unit => {
    const value = unit.closest('.gas-measure')?.querySelector('.gas-value');
    if (!value) return true;
    const unitSize = parseFloat(getComputedStyle(unit).fontSize);
    const valueSize = parseFloat(getComputedStyle(value).fontSize);
    const weight = getComputedStyle(unit).fontWeight;
    return unitSize < valueSize && (parseInt(weight, 10) >= 700 || weight === 'bold');
  });
  const result = document.getElementById('contingencyResult');
  const graph = document.getElementById('contingencyProfileCanvas');
  const graphLegend = document.getElementById('contingencyProfileLegend');
  const schedule = document.querySelector('#contingencyResult .schedule-table');
  const scheduleWrap = schedule?.closest('.schedule-wrap');
  const bailoutDuplicate = document.querySelector('#decoAlertsEmergency [data-warning="bailout-contingency"]');
  const copyText = typeof buildMessengerText === 'function' ? (buildMessengerText('contingency') || '') : '';
  const headers = schedule ? [...schedule.querySelectorAll('thead th')].slice(1).map(el => (el.textContent || '').trim()) : [];
  const nonSummaryRows = schedule ? [...schedule.querySelectorAll('tbody tr[data-phase]:not(.row-summary)')] : [];
  const ttsCells = schedule ? [...schedule.querySelectorAll('td[data-label="TTS"]')] : [];
  const resultRect = result?.getBoundingClientRect();
  const graphRect = graph?.getBoundingClientRect();
  const scheduleRect = scheduleWrap?.getBoundingClientRect();
  const gasRect = emergency?.getBoundingClientRect();
  return {
    generated,
    visible: !!emergency && getComputedStyle(emergency).display !== 'none',
    tableCount: document.querySelectorAll('#emergencyGasConsumption table.gas-plan-table').length,
    cardCount: cards.length,
    criticalCount: document.querySelectorAll('#emergencyGasConsumption .gas-usage-card--critical, #emergencyGasConsumption .gas-usage-card--nogas').length,
    noGasCount: document.querySelectorAll('#emergencyGasConsumption .gas-usage-card--nogas').length,
    warningText: document.querySelector('#emergencyGasConsumption .gas-usage-inline-warning')?.textContent?.trim() || '',
    oldWarningCount: document.querySelectorAll('#emergencyGasConsumption .gas-usage-card .gas-consumption-warning').length,
    compactUnits: [...cards.map(el => el.textContent || ''), document.querySelector('#emergencyGasConsumption .gas-usage-inline-warning')?.textContent || ''].every(text => !/\d\s+(?:L|bar|psi|ftÃ‚Â³|ftÂ³|ft3)\b/i.test(text)),
    unitStyleOk,
    measureBold: measureSpans.length > 0 && measureSpans.every(el => {
      const weight = getComputedStyle(el).fontWeight;
      return parseInt(weight, 10) >= 700 || weight === 'bold';
    }),
    hasThreshold: !!document.querySelector('#emergencyGasConsumption #gasLowThresholdPct'),
    labels: cards.map(el => el.dataset.gasLabel || ''),
    hasBars: cards.every(el => !!el.querySelector('.gas-usage-track') && !!el.querySelector('.gas-usage-remaining-bar')),
    hasTurnPressureInline: cards.some(el => /Used:.*Turn Pressure:/i.test(el.querySelector('.gas-usage-foot')?.textContent || '')),
    hasTurnPressColumn: /TURN\s+PRESS(?!URE)/i.test(emergency?.textContent || ''),
    warningCount: warnings.length,
    graphVisible: !!graph && graphRect.width > 100 && graphRect.height > 80,
    graphLegendText: graphLegend?.textContent?.trim() || '',
    graphStopTableCount: document.querySelectorAll('#contingencyProfileLegend .profile-legend-table').length,
    scheduleHeaders: headers,
    hasTtsHeader: headers.some(text => text.toUpperCase() === 'TTS'),
    ttsCellCount: ttsCells.length,
    sevenCellsPerRow: nonSummaryRows.length > 0 && nonSummaryRows.every(row => row.cells.length === 8),
    graphBeforeSchedule: !!(graphRect && scheduleRect && graphRect.bottom <= scheduleRect.top),
    gasBelowSchedule: !!(scheduleRect && gasRect && gasRect.top >= scheduleRect.bottom),
    resultBeforeGas: !!(resultRect && gasRect && resultRect.bottom <= gasRect.top),
    bailoutDuplicateText: bailoutDuplicate?.textContent?.trim() || '',
    bailoutDuplicateCount: document.querySelectorAll('#decoAlertsEmergency [data-warning="bailout-contingency"]').length,
    copyText,
    copyHasPlanContext: /Algorithm\s*:/.test(copyText)
      && /(?:Buhlmann|VPM-B|VPM-B\+GFS)/i.test(copyText)
      && /(?:GF\s*\d+\/\d+|Conservatism\s*\+\d+|GF Hi\s*\d+)/i.test(copyText)
      && /(?:Bottom Gas|Diluent|Loop gas)\s*:/.test(copyText)
      && /(?:Deco Gas|Bailout mix)\s+1\s*:/.test(copyText),
  };
}
"""


GAS_VOLUME_FIRST_UNITS_PROBE_JS = r"""
async () => {
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  const captureCard = root => {
    const cards = [...document.querySelectorAll(`${root} .gas-usage-card`)];
    const remaining = cards.map(el => el.querySelector('.gas-usage-remaining')?.textContent?.trim() || '');
    const footers = cards.map(el => el.querySelector('.gas-usage-foot')?.textContent?.trim() || '');
    return {
      cardCount: cards.length,
      remaining,
      footers,
      compactUnits: !remaining.concat(footers).some(text => /\d\s+(?:L|bar|psi|ftÃ‚Â³|ftÂ³|ft3)\b/i.test(text)),
      volumeFirst: remaining.every(text => /^\d+(?:\.\d+)?ft/i.test(text) && /\(.*psi\)/i.test(text))
        && footers.every(text => /Used:\s*\d+(?:\.\d+)?ft/i.test(text) && /\(.*psi\)/i.test(text)),
      noBarLitresOrder: !remaining.concat(footers).some(text => /\b(?:bar|psi)\s*\(/i.test(text)),
    };
  };
  window._zhlHeadless = false;
  setMainNav('buh');
  if (typeof setUnits === 'function') setUnits('imperial');
  await new Promise(r => setTimeout(r, 200));
  setVal('tecDepth', '131');
  setVal('tecBT', '30');
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  let generated = false;
  for (let i = 0; i < 60; i++) {
    await new Promise(r => setTimeout(r, 250));
    if (document.querySelectorAll('#gasConsumptionSummary .gas-usage-card').length >= 3) {
      generated = true;
      break;
    }
  }
  const main = captureCard('#gasConsumptionSummary');
  if (typeof switchResultTab === 'function') {
    switchResultTab('contingency', document.querySelector('#tecResultTabs [data-tab="contingency"]'));
  }
  if (typeof selectContBT === 'function') selectContBT(3);
  if (typeof calcContingency === 'function') calcContingency();
  for (let i = 0; i < 40; i++) {
    await new Promise(r => setTimeout(r, 250));
    if (document.querySelectorAll('#emergencyGasConsumption .gas-usage-card').length > 0) break;
  }
  const contingency = captureCard('#emergencyGasConsumption');
  return {
    generated,
    units: typeof units !== 'undefined' ? units : '',
    main,
    contingency,
  };
}
"""


BOTTOM_NAV_PROBE_JS = r"""
async () => {
  const vis = (id) => {
    const el = document.getElementById(id);
    if (!el) return 'missing';
    return getComputedStyle(el).display;
  };
  const width = window.innerWidth;
  const mobile = width <= 720;

  const bottomNav = document.getElementById('bottomNav');
  const bottomNavPresent = !!bottomNav;
  const bottomNavVisible = !!(bottomNav && getComputedStyle(bottomNav).display !== 'none');
  const bottomNavHeight = bottomNav?.getBoundingClientRect().height || 0;
  const appBottomNav = document.getElementById('appBottomNav');
  const appBottomNavPresent = !!appBottomNav;
  const appBottomNavVisible = !!(appBottomNav && getComputedStyle(appBottomNav).display !== 'none');
  const appBottomNavHeight = appBottomNav?.getBoundingClientRect().height || 0;
  const appBottomLabels = appBottomNav
    ? Array.from(appBottomNav.querySelectorAll('.nav-item:not([hidden])')).map(btn => btn.textContent.trim())
    : [];
  const appBottomHiddenItemsVisible = appBottomNav
    ? Array.from(appBottomNav.querySelectorAll('.nav-item[hidden]')).some(btn => getComputedStyle(btn).display !== 'none')
    : false;
  const appBottomGroupGeometry = () => {
    if (!appBottomNav) return { centerError: 999, left: 0, right: 0 };
    const navRect = appBottomNav.getBoundingClientRect();
    const buttons = Array.from(appBottomNav.querySelectorAll('.nav-item:not([hidden])'))
      .filter(btn => getComputedStyle(btn).display !== 'none');
    if (!buttons.length) return { centerError: 999, left: 0, right: 0 };
    const first = buttons[0].getBoundingClientRect();
    const last = buttons[buttons.length - 1].getBoundingClientRect();
    return {
      centerError: Math.abs(((first.left + last.right) / 2) - ((navRect.left + navRect.right) / 2)),
      left: Math.round(first.left),
      right: Math.round(last.right),
    };
  };
  const appBottomHasGhostIcons = appBottomNav ? /\b(DP|CP|TS)\b/.test(appBottomNav.textContent || '') : false;
  const appBottomPlanEnabled = !!document.querySelector('#appBottomNav [data-tab="plan"]:not(:disabled)');
  const mainVersion = document.getElementById('mainVersionLabel');
  const mainVersionRect = mainVersion?.getBoundingClientRect();
  const mainVersionVisible = !!(mainVersion && getComputedStyle(mainVersion).display !== 'none' && mainVersionRect.height > 0 && mainVersionRect.width > 0);
  const refRect = document.getElementById('navRef')?.getBoundingClientRect();
  const headerRefCompact = !mobile || (!!refRect && refRect.width <= 32 && refRect.height <= 32);
  const appShellFooter = document.querySelector('.app-shell-footer-links');
  const appShellFooterHidden = !appShellFooter || getComputedStyle(appShellFooter).display === 'none';
  const chipSamples = [];
  const sampleChips = (label) => {
    const chips = document.getElementById('mobileAlgoChips');
    if (!chips) return;
    const r = chips.getBoundingClientRect();
    const buttons = Array.from(chips.querySelectorAll('.mobile-algo-chip')).map(btn => btn.getBoundingClientRect());
    const groupCenter = buttons.length
      ? (buttons[0].left + buttons[buttons.length - 1].right) / 2
      : 0;
    chipSamples.push({
      label,
      top: Math.round(r.top),
      bottom: Math.round(r.bottom),
      gapFromHeader: Math.round(r.top - (document.querySelector('header')?.getBoundingClientRect().bottom || 0)),
      centerError: Math.abs(groupCenter - window.innerWidth / 2),
      active: Array.from(chips.querySelectorAll('.active')).map(btn => btn.textContent.trim()),
    });
  };
  sampleChips('initial');

  const bnavButtons = document.querySelectorAll('.bnav-btn').length;
  const duplicateControls = {
    planner: !!document.getElementById('bnavPlanner') && !!document.getElementById('navBtnBuh'),
    tools: !!document.getElementById('bnavTools') && !!document.getElementById('navBtnTools'),
    settings: !!document.getElementById('bnavSettings') && !!document.getElementById('navBtnSettings'),
    ref: !!document.getElementById('bnavRef') && !!document.getElementById('navRef'),
  };

  let cssHasBottomNav = false;
  for (const sheet of document.styleSheets) {
    try {
      for (const rule of sheet.cssRules || []) {
        const text = rule.cssText || '';
        if (text.includes('.bottom-nav') || text.includes('.bnav-btn')) {
          cssHasBottomNav = true;
          break;
        }
      }
    } catch (_) {}
    if (cssHasBottomNav) break;
  }

  const setNavModeSrc = typeof setNavMode === 'function' ? setNavMode.toString() : '';
  const shellHasBnavWriters = /bnav|bottomNav|bottom-nav/.test(setNavModeSrc);

  const app = document.querySelector('.app');
  const appPaddingBottom = app ? parseFloat(getComputedStyle(app).paddingBottom) : 0;
  const appRect = app?.getBoundingClientRect();
  const bottomGap = appRect ? Math.max(0, window.innerHeight - appRect.bottom) : 0;

  const navChecks = {};
  document.getElementById('navBtnRec')?.click();
  await new Promise(r => setTimeout(r, 120));
  navChecks.rec = vis('plannerView') !== 'none';
  const recBottomLabels = appBottomNav
    ? Array.from(appBottomNav.querySelectorAll('.nav-item:not([hidden])')).map(btn => btn.textContent.trim())
    : [];
  const recBottomGeometry = appBottomGroupGeometry();

  document.getElementById('navBtnBuh')?.click();
  await new Promise(r => setTimeout(r, 120));
  navChecks.buh = vis('tecPlannerView') !== 'none';
  const tecBottomLabels = appBottomNav
    ? Array.from(appBottomNav.querySelectorAll('.nav-item:not([hidden])')).map(btn => btn.textContent.trim())
    : [];
  const tecBottomGeometry = appBottomGroupGeometry();

  document.getElementById('navBtnVpm')?.click();
  await new Promise(r => setTimeout(r, 120));
  navChecks.vpm = vis('tecPlannerView') !== 'none';

  document.getElementById('navBtnTools')?.click();
  await new Promise(r => setTimeout(r, 120));
  navChecks.tools = document.getElementById('toolsPageWrap')?.classList.contains('visible') === true;
  sampleChips('tools');
  const toolsBottomHidden = !appBottomNav || getComputedStyle(appBottomNav).display === 'none';
  const mobileToolsListVisible = mobile
    ? getComputedStyle(document.getElementById('mobileToolsList')).display !== 'none'
    : true;
  const mobileToolRows = document.querySelectorAll('#mobileToolsList .mobile-tool-row').length;
  const mobileToolKeys = Array.from(document.querySelectorAll('#mobileToolsList .mobile-tool-row')).map(row => row.dataset.tool);
  const desktopToolKeys = Array.from(document.querySelectorAll('#toolsBar .tools-bar-btn'))
    .map(btn => (btn.id || '').replace(/^tool-/, ''));
  const movedRecToolsPresent = ['surfint', 'ndlref'].every(key => mobileToolKeys.includes(key))
    && ['surfint', 'ndlref'].every(key => desktopToolKeys.includes(key))
    && ['surfint', 'ndlref'].every(key => !!document.getElementById('tool-panel-' + key))
    && !mobileToolKeys.includes('avgdepth')
    && !desktopToolKeys.includes('avgdepth')
    && recBottomLabels.includes('Avg Depth')
    && !!document.getElementById('resultTab-avgdepth');
  const mobileToolsPanelHiddenOnList = mobile
    ? getComputedStyle(document.getElementById('toolsPanelMount')).display === 'none'
    : true;
  if (mobile) {
    document.querySelector('#mobileToolsList .mobile-tool-row[data-tool="mod"]')?.click();
    await new Promise(r => setTimeout(r, 160));
  }
  const mobileToolDetailVisible = mobile
    ? document.getElementById('toolsPageWrap')?.classList.contains('mobile-tool-detail') === true
      && getComputedStyle(document.getElementById('mobileToolDetailBar')).display !== 'none'
      && getComputedStyle(document.getElementById('toolsPanelMount')).display !== 'none'
    : true;
  const mobileToolTitle = document.getElementById('mobileToolTitle')?.textContent?.trim() || '';
  if (mobile) {
    document.querySelector('#mobileToolDetailBar .mobile-tool-back')?.click();
    await new Promise(r => setTimeout(r, 120));
  }
  const mobileToolsBackToList = mobile
    ? document.getElementById('toolsPageWrap')?.classList.contains('mobile-tool-list') === true
      && getComputedStyle(document.getElementById('mobileToolsList')).display !== 'none'
      && getComputedStyle(document.getElementById('toolsPanelMount')).display === 'none'
    : true;

  document.getElementById('navBtnSettings')?.click();
  await new Promise(r => setTimeout(r, 120));
  navChecks.settings = document.getElementById('settingsPageWrap')?.classList.contains('visible') === true;
  sampleChips('settings');
  const settingsBottomHidden = !appBottomNav || getComputedStyle(appBottomNav).display === 'none';
  const settingsLinkCount = document.querySelectorAll('.settings-app-link-list a').length;
  const settingsDonateCount = document.querySelectorAll('.settings-donate-link').length;

  document.getElementById('navRef')?.click();
  await new Promise(r => setTimeout(r, 120));
  const refModal = document.getElementById('referenceModal');
  navChecks.ref = refModal ? getComputedStyle(refModal).display !== 'none' : false;
  const referenceLinksVisible = (() => {
    const block = document.querySelector('#referenceModal .reference-links-block');
    return !!block && getComputedStyle(block).display !== 'none' && block.querySelectorAll('a').length >= 6;
  })();
  if (refModal && getComputedStyle(refModal).display !== 'none') {
    document.querySelector('#referenceModal button[onclick*="toggleReference"]')?.click();
    await new Promise(r => setTimeout(r, 80));
  }

  document.getElementById('navBtnBuh')?.click();
  await new Promise(r => setTimeout(r, 120));
  const prevHeadless = window._zhlHeadless;
  window._zhlHeadless = false;
  try {
    document.getElementById('tecGenerateBtn')?.click();
    const deadline = Date.now() + 15000;
    while (Date.now() < deadline) {
      const hasResults = document.getElementById('resultsPanel')?.classList.contains('has-results') === true;
      const rows = document.querySelectorAll('#decoTableBody tr').length;
      if (hasResults && rows >= 5) break;
      await new Promise(r => setTimeout(r, 200));
    }
  } finally {
    window._zhlHeadless = prevHeadless;
  }
  const onResults = vis('resultsPanel') !== 'none';
  if (mobile && typeof setMobileTab === 'function') {
    setMobileTab('results', { skipNavMode: true, force: true });
    await new Promise(r => setTimeout(r, 120));
    navChecks.mobileResults = vis('resultsPanel') !== 'none';
    setMobileTab('plan', { skipNavMode: true, force: true });
    await new Promise(r => setTimeout(r, 120));
  } else {
    document.getElementById('navBtnBuh')?.click();
    await new Promise(r => setTimeout(r, 120));
  }
  const backToPlanner = vis('tecPlannerView') !== 'none';

  const desktopNavCount = width > 640
    ? document.querySelectorAll('#mainNavBar .main-nav-btn').length
    : null;

  const ok = !bottomNavPresent
    && bnavButtons === 0
    && !shellHasBnavWriters
    && !cssHasBottomNav
    && Object.values(navChecks).every(Boolean)
    && (mobile ? backToPlanner : true)
    && (mobile
      ? appBottomNavPresent
        && appBottomNavHeight >= 48
        && JSON.stringify(recBottomLabels) === JSON.stringify(['Plan', 'Profile', 'Avg Depth', 'Multi Dive'])
        && JSON.stringify(tecBottomLabels) === JSON.stringify(['Plan', 'Profile', 'Contingency', 'Tissues'])
        && !appBottomHiddenItemsVisible
        && recBottomGeometry.centerError <= 4
        && tecBottomGeometry.centerError <= 4
        && !appBottomHasGhostIcons
        && appBottomPlanEnabled
        && toolsBottomHidden
        && settingsBottomHidden
        && !mainVersionVisible
        && headerRefCompact
        && appShellFooterHidden
        && settingsLinkCount >= 7
        && settingsDonateCount >= 1
        && referenceLinksVisible
        && mobileToolsListVisible
        && mobileToolRows >= 10
        && movedRecToolsPresent
        && mobileToolsPanelHiddenOnList
        && mobileToolDetailVisible
        && mobileToolTitle === 'MOD'
        && mobileToolsBackToList
        && chipSamples.length >= 3
        && chipSamples.every(s => Math.abs(s.top - chipSamples[0].top) <= 1)
        && chipSamples.every(s => s.centerError <= 2 && s.gapFromHeader >= 4)
      : desktopNavCount === 5 && (!appBottomNavVisible || appBottomNavHeight < 1))
    && bottomGap < 8;

  return {
    width,
    mobile,
    bottomNavPresent,
    bottomNavVisible,
    bottomNavHeight,
    appBottomNavPresent,
    appBottomNavVisible,
    appBottomNavHeight,
    appBottomLabels,
    recBottomLabels,
    tecBottomLabels,
    appBottomHiddenItemsVisible,
    recBottomGeometry,
    tecBottomGeometry,
    appBottomHasGhostIcons,
    appBottomPlanEnabled,
    mainVersionVisible,
    headerRefCompact,
    appShellFooterHidden,
    settingsLinkCount,
    settingsDonateCount,
    referenceLinksVisible,
    mobileToolsListVisible,
    mobileToolRows,
    mobileToolKeys,
    desktopToolKeys,
    movedRecToolsPresent,
    toolsBottomHidden,
    settingsBottomHidden,
    mobileToolsPanelHiddenOnList,
    mobileToolDetailVisible,
    mobileToolTitle,
    mobileToolsBackToList,
    chipSamples,
    duplicateControls,
    bnavButtons,
    cssHasBottomNav,
    shellHasBnavWriters,
    appPaddingBottom,
    bottomGap,
    navChecks,
    onResults,
    backToPlanner,
    desktopNavCount,
    ok,
  };
}
"""


def _capture(browser, base_url: str, viewport: tuple[int, int], light: bool) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        boot_app_page(page, base_url)
        page.evaluate(
            "light => document.body.classList.toggle('light-theme', light)", light
        )
        generated = bool(page.evaluate(GENERATE_JS))
        capture = page.evaluate(CAPTURE_JS)
        capture["generated"] = generated
        capture["console_errors"] = errors
        return capture
    finally:
        context.close()


def _capture_high_cns_alert(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 375, "height": 667})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        boot_app_page(page, base_url)
        generated = bool(page.evaluate(GENERATE_JS))
        result = page.evaluate(
            r"""
async () => {
  const cnsHtml = '<div class="alert" style="margin-top:8px;background:#ffff00;border-color:#cccc00;color:#111;font-weight:700;"><span>â˜¢</span><div><strong>HIGH CNS%.</strong> CNS oxygen load 83% exceeds 80%.</div></div>';
  const alerts = document.getElementById('decoAlerts');
  if (typeof renderDecoAlerts === 'function') renderDecoAlerts(alerts, cnsHtml);
  await new Promise(resolve => setTimeout(resolve, 50));
  const alert = [...document.querySelectorAll('#decoAlerts .alert')]
    .find(el => /HIGH CNS%/.test(el.textContent || '')) || null;
  const gasCardAlert = document.querySelector('#gasConsumptionSummary .gas-consumption-cns, #gasConsumptionSummary .alert strong');
  const decoCard = document.querySelector('#resultsPanel .deco-plan-card');
  const style = alert ? getComputedStyle(alert) : null;
  const rect = el => {
    const r = el?.getBoundingClientRect();
    return r ? { top: r.top, bottom: r.bottom, left: r.left, right: r.right, width: r.width, height: r.height } : null;
  };
  return {
    alertText: alert?.textContent?.trim() || '',
    alertBackground: style?.backgroundColor || '',
    alertColor: style?.color || '',
    alertRect: rect(alert),
    decoCardRect: rect(decoCard),
    inGasCard: !!(gasCardAlert && /HIGH CNS%/.test(gasCardAlert.textContent || '')),
  };
}
""",
        )
        result["generated"] = generated
        result["console_errors"] = errors
        return result
    finally:
        context.close()


def _capture_nav(browser, base_url: str, viewport: tuple[int, int], light: bool) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        page.evaluate(
            "light => document.body.classList.toggle('light-theme', light)", light
        )
        dark_probe = page.evaluate(NAV_GRID_PROBE_JS, list(NAV_BTN_IDS))
        page.evaluate("() => document.body.classList.add('light-theme')")
        light_probe = page.evaluate(NAV_GRID_PROBE_JS, list(NAV_BTN_IDS))
        return {
            "dark": dark_probe,
            "light": light_probe,
            "console_errors": errors,
        }
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_bottom_nav(browser, base_url: str, viewport: tuple[int, int], light: bool) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        page.evaluate(
            "light => document.body.classList.toggle('light-theme', light)", light
        )
        probe = page.evaluate(BOTTOM_NAV_PROBE_JS)
        probe["console_errors"] = errors
        return probe
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_contingency_gas(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 375, "height": 667})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        boot_app_page(page, base_url)
        capture = page.evaluate(CONTINGENCY_GAS_PROBE_JS)
        capture["console_errors"] = errors
        return capture
    finally:
        context.close()


def _capture_gas_volume_first_units(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    try:
        boot_app_page(page, base_url)
        capture = page.evaluate(GAS_VOLUME_FIRST_UNITS_PROBE_JS)
        capture["console_errors"] = errors
        return capture
    finally:
        context.close()


def _capture_gas_labels(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(GAS_LABEL_PROBE_JS)
        result["console_errors"] = errors
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_mobile_warnings(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 375, "height": 667})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(MOBILE_WARNING_PROBE_JS)
        result["console_errors"] = errors
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_vpm_mode(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(VPM_MODE_PROBE_JS)
        result["console_errors"] = errors
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_vpm_beyond_mod(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(
            r"""
async () => {
  window._zhlHeadless = false;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  if (typeof setMainNav === 'function') setMainNav('vpm');
  if (typeof setPlannerAlgo === 'function') setPlannerAlgo('VPMB');
  await wait(250);
  setVal('tecDepth', '70');
  setVal('tecBT', '25');
  setVal('decoGas', 'ean32');
  setVal('ppo2Bottom', '1.4');
  if (typeof toggleDecoCustomO2 === 'function') toggleDecoCustomO2('decoGas', 'decoCustomO2Field');
  if (typeof updateGasMODDisplays === 'function') updateGasMODDisplays();
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 50; i++) {
    await wait(120);
    if (String(document.body.textContent || '').includes('BEYOND MOD')) break;
  }
  const errorRow = document.querySelector('#decoTableBody tr[data-phase="error"]');
  const cell = errorRow?.querySelector('td') || null;
  const graphCard = document.getElementById('fullDiveGraphCard');
  const gasCard = document.getElementById('gasConsumptionSummary');
  const resultEl = document.getElementById('decoResult');
  const resultsPanel = document.getElementById('resultsPanel');
  const emptyState = document.getElementById('resultEmptyState');
  const cnsText = document.getElementById('decoCNSDisplay')?.textContent || '';
  const toastText = document.getElementById('toast-schedule')?.textContent || '';
  return {
    errorRowCount: document.querySelectorAll('#decoTableBody tr[data-phase="error"]').length,
    colspan: cell ? Number(cell.getAttribute('colspan')) : null,
    expected: typeof scheduleColumnCount === 'function' ? scheduleColumnCount() : 8,
    text: toastText,
    resultVisible: !!resultEl && getComputedStyle(resultEl).display !== 'none',
    hasResults: !!resultsPanel && resultsPanel.classList.contains('has-results'),
    emptyVisible: !!emptyState && getComputedStyle(emptyState).display !== 'none',
    graphVisible: !!graphCard && getComputedStyle(graphCard).display !== 'none',
    gasVisible: !!gasCard && getComputedStyle(gasCard).display !== 'none',
    planRows: document.querySelectorAll('#decoTableBody tr[data-phase]:not([data-phase="error"])').length,
    cnsText,
    hasRunnerHelper: typeof validateVpmOcBottomGasPpo2 === 'function'
      && typeof validateOcBottomGasPpo2 === 'function'
      && typeof renderBlockingScheduleError === 'function',
  };
}
""",
        )
        result["console_errors"] = [
            err for err in errors
            if "Cannot generate schedule" not in err
        ]
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_zhl_beyond_mod(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(
            r"""
async () => {
  window._zhlHeadless = false;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  if (typeof setMainNav === 'function') setMainNav('buh');
  await wait(250);
  setVal('tecDepth', '70');
  setVal('tecBT', '25');
  setVal('decoGas', 'ean32');
  setVal('ppo2Bottom', '1.4');
  if (typeof toggleDecoCustomO2 === 'function') toggleDecoCustomO2('decoGas', 'decoCustomO2Field');
  if (typeof updateGasMODDisplays === 'function') updateGasMODDisplays();
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 50; i++) {
    await wait(120);
    if (String(document.body.textContent || '').includes('BEYOND MOD')) break;
  }
  const errorRow = document.querySelector('#decoTableBody tr[data-phase="error"]');
  const cell = errorRow?.querySelector('td') || null;
  const graphCard = document.getElementById('fullDiveGraphCard');
  const gasCard = document.getElementById('gasConsumptionSummary');
  const resultEl = document.getElementById('decoResult');
  const resultsPanel = document.getElementById('resultsPanel');
  const emptyState = document.getElementById('resultEmptyState');
  const cnsText = document.getElementById('decoCNSDisplay')?.textContent || '';
  const toastText = document.getElementById('toast-schedule')?.textContent || '';
  return {
    errorRowCount: document.querySelectorAll('#decoTableBody tr[data-phase="error"]').length,
    colspan: cell ? Number(cell.getAttribute('colspan')) : null,
    expected: typeof scheduleColumnCount === 'function' ? scheduleColumnCount() : 8,
    text: toastText,
    resultVisible: !!resultEl && getComputedStyle(resultEl).display !== 'none',
    hasResults: !!resultsPanel && resultsPanel.classList.contains('has-results'),
    emptyVisible: !!emptyState && getComputedStyle(emptyState).display !== 'none',
    graphVisible: !!graphCard && getComputedStyle(graphCard).display !== 'none',
    gasVisible: !!gasCard && getComputedStyle(gasCard).display !== 'none',
    planRows: document.querySelectorAll('#decoTableBody tr[data-phase]:not([data-phase="error"])').length,
    cnsText,
    hasRunnerHelper: typeof validateOcBottomGasPpo2 === 'function'
      && typeof renderBlockingScheduleError === 'function',
  };
}
""",
        )
        result["console_errors"] = [
            err for err in errors
            if "Cannot generate schedule" not in err
        ]
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_vpm_graph_waypoints(browser, base_url: str) -> dict:
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(
            r"""
async () => {
  window._zhlHeadless = false;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  const setVal = (id, value) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
  };
  if (typeof setMainNav === 'function') setMainNav('vpm');
  if (typeof setPlannerAlgo === 'function') setPlannerAlgo('VPMB');
  await wait(250);
  setVal('tecDepth', '50');
  setVal('tecBT', '25');
  setVal('decoGas', 'air');
  if (typeof updateGasMODDisplays === 'function') updateGasMODDisplays();
  if (typeof _syncTecDepthBtSteppers === 'function') _syncTecDepthBtSteppers();
  document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 80; i++) {
    await wait(150);
    if (document.querySelectorAll('#decoTableBody tr[data-phase]').length >= 6
        && Array.isArray(window._plannerWaypoints)
        && window._plannerWaypoints.length >= 6) break;
  }
  if (typeof drawDecoProfileFull === 'function') drawDecoProfileFull();
  await wait(100);
  const waypoints = Array.isArray(window._plannerWaypoints) ? window._plannerWaypoints : [];
  const path = waypoints
    .filter(wp => wp.type !== 'gasswitch' && Number.isFinite(Number(wp.t)) && Number.isFinite(Number(wp.depth)))
    .map(wp => ({ t: Number(wp.t), depth: Number(wp.depth), type: wp.type }));
  const verticalJumps = [];
  const backwards = [];
  for (let i = 1; i < path.length; i++) {
    const prev = path[i - 1];
    const cur = path[i];
    const dt = cur.t - prev.t;
    const dd = Math.abs(cur.depth - prev.depth);
    if (dt < -0.05) backwards.push({ prev, cur, dt });
    if (Math.abs(dt) < 0.05 && dd > 5) verticalJumps.push({ prev, cur, dt, dd });
  }
  const firstStopRun = parseFloat(document.querySelector('#decoTableBody tr[data-phase="deco"] td[data-label="Run"]')?.textContent || '0') || 0;
  return {
    rowCount: document.querySelectorAll('#decoTableBody tr[data-phase]').length,
    waypointCount: waypoints.length,
    path,
    verticalJumps,
    backwards,
    firstStopRun,
  };
}
""",
        )
        result["console_errors"] = errors
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def _capture_schedule_error_contract(browser, base_url: str, viewport: tuple[int, int]) -> dict:
    context = browser.new_context(viewport={"width": viewport[0], "height": viewport[1]})
    page = context.new_page()
    page.set_default_timeout(120_000)
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    probe_state = None
    try:
        boot_app_page(page, base_url)
        probe_state = page.evaluate(CAPTURE_PROBE_STATE_JS)
        result = page.evaluate(
            r"""
async () => {
  window._zhlHeadless = false;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  if (typeof setPlannerAlgo === 'function') setPlannerAlgo('VPMB');
  if (typeof setMainNav === 'function') setMainNav('vpm');
  await wait(250);
  const originalVpmEngine = window.VPMEngine;
  const originalHeadless = window._zhlHeadless;
  window._zhlHeadless = false;
  window.VPMEngine = null;
  if (typeof runVPMSchedule === 'function') runVPMSchedule(40, 25, 20, 10, 3, 3, 3, 3, 1, 1.4, 1.6, 'VPMB', true);
  else document.getElementById('tecGenerateBtn')?.click();
  for (let i = 0; i < 50; i++) {
    await wait(100);
    if (document.querySelector('#decoTableBody tr[data-phase="error"]')) break;
  }
  window.VPMEngine = originalVpmEngine;
  window._zhlHeadless = originalHeadless;
  const decoResult = document.getElementById('decoResult');
  const resultsPanel = document.getElementById('resultsPanel');
  if (decoResult) decoResult.style.display = 'block';
  if (resultsPanel) resultsPanel.classList.add('has-results');
  if (typeof setMobileTab === 'function') setMobileTab('results');
  if (typeof setMobilePlanView === 'function') setMobilePlanView('results');
  await wait(50);
  const tbody = document.getElementById('decoTableBody');
  const table = tbody?.closest('table');
  const errorRows = [...document.querySelectorAll('#decoTableBody tr[data-phase="error"]')];
  const cell = errorRows[0]?.querySelector('td') || null;
  const expected = typeof scheduleColumnCount === 'function' ? scheduleColumnCount() : 8;
  const tableRect = table ? table.getBoundingClientRect() : null;
  const cellRect = cell ? cell.getBoundingClientRect() : null;
  const text = cell?.textContent || '';
  return {
    expected,
    errorRowCount: errorRows.length,
    colspan: cell ? Number(cell.getAttribute('colspan')) : null,
    hasHelper: typeof scheduleErrorRowHtml === 'function' && typeof renderScheduleErrorRow === 'function',
    text,
    tableWidth: tableRect ? tableRect.width : 0,
    cellWidth: cellRect ? cellRect.width : 0,
    geometryOk: !!(tableRect && cellRect && cellRect.width > 0 && tableRect.width > 0 && cellRect.width <= tableRect.width + 2),
  };
}
""",
        )
        result["console_errors"] = [
            err for err in errors
            if "VPM engine failed to load" not in err
        ]
        return result
    finally:
        if probe_state is not None:
            restore_probe_state(page, probe_state)
        context.close()


def main() -> int:
    from playwright.sync_api import sync_playwright

    results = {case_id: True for case_id in CASE_IDS}
    details: dict[str, dict] = {}
    nav_details: dict[str, dict] = {}
    bottom_nav_details: dict[str, dict] = {}

    with serve_www(ROOT, port=0) as base_url:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for width, height in ((1280, 800), (1024, 768), (768, 720), (667, 600), (375, 667)):
                key = f"{width}x{height}-dark"
                details[key] = _capture(browser, base_url, (width, height), False)
            details["1280x800-light"] = _capture(browser, base_url, (1280, 800), True)

            for width, height in NAV_VIEWPORTS:
                key = f"{width}x{height}"
                nav_details[key] = _capture_nav(browser, base_url, (width, height), False)

            for width, height in BOTTOM_NAV_VIEWPORTS:
                for light in (False, True):
                    key = f"{width}x{height}-{'light' if light else 'dark'}"
                    bottom_nav_details[key] = _capture_bottom_nav(
                        browser, base_url, (width, height), light
                    )

            gas_details = _capture_gas_labels(browser, base_url)
            mobile_warning_details = _capture_mobile_warnings(browser, base_url)
            vpm_details = _capture_vpm_mode(browser, base_url)
            vpm_beyond_mod_details = _capture_vpm_beyond_mod(browser, base_url)
            zhl_beyond_mod_details = _capture_zhl_beyond_mod(browser, base_url)
            vpm_graph_details = _capture_vpm_graph_waypoints(browser, base_url)
            high_cns_details = _capture_high_cns_alert(browser, base_url)
            schedule_error_details = {
                f"{width}x{height}": _capture_schedule_error_contract(browser, base_url, (width, height))
                for width, height in ((1280, 800), (375, 667))
            }
            contingency_gas_details = _capture_contingency_gas(browser, base_url)
            gas_units_details = _capture_gas_volume_first_units(browser, base_url)
            browser.close()

    dark = details["1280x800-dark"]
    light = details["1280x800-light"]
    captures = list(details.values())

    results["SL-VIS-GAS-DOT-SINGLE-SOURCE"] = all(
        c["bottomDotCount"] == 1 and not c["titleHasEmoji"] for c in captures
    )
    results["SL-VIS-GAS-SWITCH-TOKEN-PARITY"] = all(
        c["generated"]
        and bool(c["decoDotColors"])
        and all(color == c["expectedBg"] for color in c["decoDotColors"])
        and c["switchRowCount"] >= 1
        and all(color == c["expectedSwitch"] for color in c["switchCellColors"])
        for c in captures
    )
    results["SL-C09-RESULT-TAB-SIMPLIFICATION"] = all(
        c["generated"]
        and c["resultTabs"]["tabs"] == ["profile", "contingency", "tissue"]
        and c["resultTabs"]["labels"] == ["Dive Profile", "Contingency Plans", "Tissues"]
        and not c["resultTabs"]["hasGraphsTab"]
        and c["resultTabs"]["gfInsideTissue"]
        and c["resultTabs"]["graphInsideProfile"]
        and c["resultTabs"]["simpleGraphRemoved"]
        and c["resultTabs"]["graphLegendRemoved"]
        and c["resultTabs"]["fullGraphWithinBody"]
        for c in captures
    )
    results["SL-VIS-DESKTOP-TWO-COLUMN-LAYOUT"] = all(
        bool(c["layout"] and c["layout"]["sideBySide"])
        for key, c in details.items() if not key.endswith("-light") and int(key.split("x", 1)[0]) >= 1024
    )
    results["SL-VIS-DECO-BANNER-GAS-LABELS"] = all(
        c["generated"]
        and any(text.startswith("Bottom: ") for text in c["pillTexts"])
        and any(text.startswith("Deco 1: ") and " @ " in text for text in c["pillTexts"])
        and bool(c["decoPillBackgrounds"])
        and all(color == c["expectedDecoPillBg"] for color in c["decoPillBackgrounds"])
        and all(color == c["expectedDecoPillText"] for color in c["decoPillColors"])
        and c["decoPlanCardStyle"]
        and c["hazardAlertStyle"]
        and c["decoPlanCardStyle"]["background"] != c["hazardAlertStyle"]["background"]
        and c["decoPlanCardStyle"]["border"] != c["hazardAlertStyle"]["border"]
        and c["decoPlanCardStyle"]["titleColor"] == "rgb(255,68,51)"
        and (
            not c["hasTravelPill"]
            or (
                c["decoPlanCardStyle"]["travelColor"] == "rgb(17,17,17)"
                and c["decoPlanCardStyle"]["travelBorder"] == "rgb(255,153,0)"
            )
        )
        for c in (dark, light)
    )
    results["SL-VIS-SWITCH-ROW-THEME-PARITY"] = all(
        c["generated"]
        and c["switchRowCount"] >= 1
        and bool(c["switchCellColors"])
        and all(color == c["expectedSwitch"] for color in c["switchCellColors"])
        for c in (dark, light)
    )
    results["SL-C09-SWITCH-ROW-BACKGROUND-PARITY"] = all(
        c["generated"]
        and c["switchRowCount"] >= 1
        and bool(c["switchRowBackgrounds"])
        and all(color == c["normalRowBackground"] for color in c["switchRowBackgrounds"])
        for c in captures
    )
    results["SL-C09-GRAPH-WAYPOINT-TIME-SPREAD"] = all(
        c["generated"]
        and c["graphWaypoints"]["count"] >= 5
        and c["graphWaypoints"]["uniqueCount"] >= 5
        and (c["graphWaypoints"]["maxTime"] - c["graphWaypoints"]["minTime"]) >= 15
        for c in captures
    )
    results["SL-C09-VPM-GRAPH-WAYPOINT-MONOTONIC"] = bool(
        vpm_graph_details.get("rowCount", 0) >= 6
        and vpm_graph_details.get("waypointCount", 0) >= 6
        and vpm_graph_details.get("firstStopRun", 0) >= 25
        and not vpm_graph_details.get("verticalJumps")
        and not vpm_graph_details.get("backwards")
        and not vpm_graph_details.get("console_errors")
    )
    results["SL-C09-MOBILE-TISSUE-TAB-VISIBLE"] = all(
        c["generated"]
        and c["mobileBottomTissueTab"]
        and "Tissues" in c["mobileBottomTissueTab"]["text"]
        and c["mobileBottomTissueTab"]["visible"]
        and c["mobileBottomTissueTab"]["withinNav"]
        for key, c in details.items() if int(key.split("x", 1)[0]) <= 640
    )
    results["SL-C09-SCHEDULE-COLUMN-GEOMETRY"] = all(
        c["generated"]
        and c["scheduleColumns"]["tableLayout"] == "fixed"
        and c["scheduleColumns"]["headerTexts"][:4] == ["Depth", "Stop", "Run", "Mix"]
        and c["scheduleColumns"]["headerTexts"][4].startswith("ppO")
        and c["scheduleColumns"]["headerTexts"][5] == "CNS"
        and c["scheduleColumns"]["headerTexts"][6] == "EAD"
        and c["scheduleColumns"]["sevenCellsPerRow"]
        and c["scheduleColumns"]["noVisibleTts"]
        and c["scheduleColumns"]["runBeforeMix"]
        and c["scheduleColumns"]["depthAligned"]
        and c["scheduleColumns"]["stopAligned"]
        and c["scheduleColumns"]["depthCompact"]
        and c["scheduleColumns"]["mixLaneAligned"]
        and c["scheduleColumns"]["mixCompact"]
        and c["scheduleColumns"]["mobileScrollReady"]
        and c["scheduleColumns"]["decoStopPlainBullets"]
        and not c["scheduleColumns"]["clippedCells"]
        for c in captures
    )
    results["SL-C09-SUMMARY-CHIP-PALETTE"] = all(
        c["generated"]
        and c["summaryChips"]["surfGF"]
        and c["summaryChips"]["surfGF"]["color"] in c["summaryChips"]["statusColors"]
        and c["summaryChips"]["otu"]
        and c["summaryChips"]["otu"]["color"] in c["summaryChips"]["statusColors"]
        and not c["summaryChips"]["tts"]
        and c["summaryChips"]["decozone"]
        and c["summaryChips"]["decozone"]["background"] == c["summaryChips"]["metricCardBackground"]
        and c["summaryChips"]["decozone"]["color"] == c["summaryChips"]["decoTextColor"]
        for c in captures
    )
    results["SL-C09-RESULT-TABS-GAP"] = all(
        c["generated"]
        and c["resultTabsGap"]
        and c["resultTabsGap"]["gap"] >= 6
        and c["resultTabsGap"].get("metricBeforePane", True)
        for c in captures
    )
    results["SL-C09-HIGH-CNS-DECO-ALERT"] = bool(
        high_cns_details.get("generated")
        and "HIGH CNS%." in high_cns_details.get("alertText", "")
        and high_cns_details.get("alertBackground") in ("rgb(255, 255, 0)", "rgb(255,255,0)")
        and high_cns_details.get("alertColor") in ("rgb(17, 17, 17)", "rgb(17,17,17)", "rgb(0, 0, 0)", "rgb(0,0,0)")
        and high_cns_details.get("alertRect")
        and high_cns_details.get("decoCardRect")
        and high_cns_details["alertRect"]["top"] >= high_cns_details["decoCardRect"]["bottom"] - 1
        and not high_cns_details.get("inGasCard")
        and not high_cns_details.get("console_errors")
    )
    results["SL-VIS-GAS-CONSUMPTION-BARS"] = all(
        c["generated"]
        and c["gasConsumptionBars"]["visible"]
        and c["gasConsumptionBars"]["cardCount"] >= 3
        and c["gasConsumptionBars"]["tableCount"] == 0
        and c["gasConsumptionBars"]["thresholdValue"] == "20"
        and c["gasConsumptionBars"]["hasAir"]
        and c["gasConsumptionBars"]["hasO2"]
        and c["gasConsumptionBars"]["hasDecoMix"]
        and not c["gasConsumptionBars"]["forbiddenLabels"]
        and c["gasConsumptionBars"]["barsPresent"]
        and c["gasConsumptionBars"]["remainingBarModel"]
        and c["gasConsumptionBars"]["metricUnits"]
        and c["gasConsumptionBars"]["metricVolumeFirst"]
        and c["gasConsumptionBars"]["compactUnits"]
        and c["gasConsumptionBars"]["unitStyleOk"]
        and c["gasConsumptionBars"]["measureBold"]
        and c["gasConsumptionBars"]["hasTurnPressureInline"]
        and not c["gasConsumptionBars"]["hasTurnPressColumn"]
        and c["gasConsumptionBars"]["sufficientLeftBorderOnly"]
        for c in captures
    )
    results["SL-VIS-CONTINGENCY-GAS-CONSUMPTION-BARS"] = bool(
        contingency_gas_details.get("generated")
        and contingency_gas_details.get("visible")
        and contingency_gas_details.get("tableCount") == 0
        and contingency_gas_details.get("cardCount", 0) >= 1
        and contingency_gas_details.get("criticalCount", 0) >= 1
        and contingency_gas_details.get("hasBars")
        and contingency_gas_details.get("hasThreshold")
        and contingency_gas_details.get("hasTurnPressureInline")
        and not contingency_gas_details.get("hasTurnPressColumn")
        and contingency_gas_details.get("compactUnits")
        and contingency_gas_details.get("unitStyleOk")
        and contingency_gas_details.get("measureBold")
        and "Air" in contingency_gas_details.get("warningText", "")
        and contingency_gas_details.get("oldWarningCount") == 0
        and not contingency_gas_details.get("console_errors")
    )
    results["SL-VIS-CONTINGENCY-MAIN-DECO-LAYOUT"] = bool(
        contingency_gas_details.get("generated")
        and contingency_gas_details.get("graphVisible")
        and not contingency_gas_details.get("graphLegendText", "")
        and contingency_gas_details.get("graphStopTableCount") == 0
        and contingency_gas_details.get("scheduleHeaders") == ["Depth", "Stop", "Run", "Mix", "ppO\u2082", "CNS", "EAD"]
        and not contingency_gas_details.get("hasTtsHeader")
        and contingency_gas_details.get("ttsCellCount") == 0
        and contingency_gas_details.get("sevenCellsPerRow")
        and contingency_gas_details.get("graphBeforeSchedule")
        and contingency_gas_details.get("gasBelowSchedule")
        and contingency_gas_details.get("resultBeforeGas")
        and contingency_gas_details.get("bailoutDuplicateCount") == 0
        and not contingency_gas_details.get("console_errors")
    )
    results["SL-C09-CONTINGENCY-COPY-PLAN-CONTEXT"] = bool(
        contingency_gas_details.get("generated")
        and contingency_gas_details.get("copyHasPlanContext")
        and not contingency_gas_details.get("console_errors")
    )
    results["SL-VIS-GAS-CONSUMPTION-VOLUME-FIRST-UNITS"] = bool(
        gas_units_details.get("generated")
        and gas_units_details.get("units") == "imperial"
        and gas_units_details.get("main", {}).get("cardCount", 0) >= 3
        and gas_units_details.get("main", {}).get("volumeFirst")
        and gas_units_details.get("main", {}).get("compactUnits")
        and gas_units_details.get("main", {}).get("noBarLitresOrder")
        and gas_units_details.get("contingency", {}).get("cardCount", 0) >= 1
        and gas_units_details.get("contingency", {}).get("volumeFirst")
        and gas_units_details.get("contingency", {}).get("compactUnits")
        and gas_units_details.get("contingency", {}).get("noBarLitresOrder")
        and not gas_units_details.get("console_errors")
    )

    nav_ok = all(
        capture["dark"]["ok"]
        and capture["light"]["ok"]
        and not capture["console_errors"]
        for capture in nav_details.values()
    )
    results["V4-UI-VISUAL-MOBILE-NAV-TILE-GRID"] = nav_ok

    gas_ok = (
        gas_details.get("generated")
        and gas_details.get("canonicalOk")
        and gas_details.get("parityOk")
        and gas_details.get("operationalOk")
        and not gas_details.get("forbiddenHits")
        and not gas_details.get("console_errors")
    )
    results["V4-UI-VISUAL-OPERATIONAL-GAS-LABEL-FORMAT"] = bool(gas_ok)

    results["SL-C09-GAS-SWITCH-TERMINOLOGY"] = bool(
        gas_details.get("generated")
        and gas_details.get("terminologyOk")
        and not gas_details.get("gasChangeTextHits")
        and not gas_details.get("gasChangeContractHits")
        and not gas_details.get("console_errors")
    )

    bottom_nav_ok = all(
        capture.get("ok")
        and not capture.get("console_errors")
        for capture in bottom_nav_details.values()
    )
    results["V4-UI-VISUAL-MOBILE-BOTTOM-TAB-SHELL"] = bottom_nav_ok

    results["SL-C09-MOBILE-WARNING-WRAP"] = bool(
        mobile_warning_details.get("ok")
        and mobile_warning_details.get("topGasBannerHidden")
        and not mobile_warning_details.get("warningText")
        and mobile_warning_details.get("warningIconText") in ("", None)
        and mobile_warning_details.get("warningPseudoIconText") in ("none", '""')
        and mobile_warning_details.get("warningIconCount") == 0
        and mobile_warning_details.get("cardWarningIconText") == "\u26a0"
        and mobile_warning_details.get("cardWarningColor") in ("rgb(255,49,49)", "rgb(255,59,48)")
        and mobile_warning_details.get("noGasCardColor") in ("rgb(255,49,49)", "rgb(220,38,38)")
        and mobile_warning_details.get("noGasStatusColor") in ("#dc2626", "rgb(220,38,38)")
        and mobile_warning_details.get("criticalCardColor") in ("rgb(232,89,12)",)
        and mobile_warning_details.get("remainingTextColor") == mobile_warning_details.get("remainingParenColor")
        and int(mobile_warning_details.get("remainingFontWeight") or 0) >= 700
        and int(mobile_warning_details.get("remainingParenFontWeight") or 0) >= 700
        and mobile_warning_details.get("usedTextColor") == mobile_warning_details.get("usedMeasureColor")
        and mobile_warning_details.get("usedTextColor") != mobile_warning_details.get("remainingTextColor")
        and not mobile_warning_details.get("console_errors")
    )
    results["SL-C09-VPM-MODE-TOGGLE"] = bool(
        vpm_details.get("ok")
        and not vpm_details.get("console_errors")
    )
    results["SL-C09-VPM-CONTINGENCY-GAS-LOSS-STABLE"] = bool(
        vpm_details.get("vpmContingencyGas", {}).get("ok")
        and vpm_details.get("vpmContingencyGas", {}).get("labelsCanonical")
        and vpm_details.get("vpmContingencyGas", {}).get("scenarioCanonical")
        and not vpm_details.get("console_errors")
    )
    results["SL-C09-VPM-BEYOND-MOD-BLOCKS"] = bool(
        vpm_beyond_mod_details.get("errorRowCount") == 0
        and vpm_beyond_mod_details.get("colspan") is None
        and vpm_beyond_mod_details.get("expected") == 8
        and "BEYOND MOD" in vpm_beyond_mod_details.get("text", "")
        and "EAN32" not in vpm_beyond_mod_details.get("text", "")
        and "32/00" in vpm_beyond_mod_details.get("text", "")
        and "actual" in vpm_beyond_mod_details.get("text", "")
        and not vpm_beyond_mod_details.get("resultVisible")
        and not vpm_beyond_mod_details.get("hasResults")
        and vpm_beyond_mod_details.get("emptyVisible")
        and not vpm_beyond_mod_details.get("graphVisible")
        and not vpm_beyond_mod_details.get("gasVisible")
        and vpm_beyond_mod_details.get("planRows") == 0
        and "2065" not in vpm_beyond_mod_details.get("cnsText", "")
        and vpm_beyond_mod_details.get("hasRunnerHelper")
        and not vpm_beyond_mod_details.get("console_errors")
    )
    results["SL-C09-ZHL-BEYOND-MOD-BLOCKS"] = bool(
        zhl_beyond_mod_details.get("errorRowCount") == 0
        and zhl_beyond_mod_details.get("colspan") is None
        and zhl_beyond_mod_details.get("expected") == 8
        and "BEYOND MOD" in zhl_beyond_mod_details.get("text", "")
        and "EAN32" not in zhl_beyond_mod_details.get("text", "")
        and "32/00" in zhl_beyond_mod_details.get("text", "")
        and "actual" in zhl_beyond_mod_details.get("text", "")
        and not zhl_beyond_mod_details.get("resultVisible")
        and not zhl_beyond_mod_details.get("hasResults")
        and zhl_beyond_mod_details.get("emptyVisible")
        and not zhl_beyond_mod_details.get("graphVisible")
        and not zhl_beyond_mod_details.get("gasVisible")
        and zhl_beyond_mod_details.get("planRows") == 0
        and "2065" not in zhl_beyond_mod_details.get("cnsText", "")
        and zhl_beyond_mod_details.get("hasRunnerHelper")
        and not zhl_beyond_mod_details.get("console_errors")
    )
    travel_trimix = gas_details.get("travelTrimix", {})
    results["SL-C09-TRAVEL-GAS-TRIMIX-CARD"] = bool(
        travel_trimix.get("optionExists")
        and travel_trimix.get("cardVisible")
        and travel_trimix.get("customHidden")
        and travel_trimix.get("o2Visible")
        and travel_trimix.get("heVisible")
        and travel_trimix.get("mixField")
        and travel_trimix.get("modBadge")
        and travel_trimix.get("switchField")
        and travel_trimix.get("minOdField")
        and travel_trimix.get("noSwitchMode")
        and travel_trimix.get("fieldCount", 0) >= 7
        and travel_trimix.get("customMin") == "18"
        and travel_trimix.get("trimixMin") == "18"
        and travel_trimix.get("label") == "18/45"
        and abs(float(travel_trimix.get("fO2", 0)) - 0.18) < 0.001
        and abs(float(travel_trimix.get("fHe", 0)) - 0.45) < 0.001
        and abs(float(travel_trimix.get("fN2", 0)) - 0.37) < 0.001
        and travel_trimix.get("modBadgeIsMod")
        and travel_trimix.get("minOdText") in ("0 m", "0 ft")
        and not gas_details.get("console_errors")
    )
    index_src = (ROOT / "index.html").read_text(encoding="utf-8")
    render_src = (ROOT / "results-render-core.js").read_text(encoding="utf-8")
    schedule_src = (ROOT / "schedule-runner-core.js").read_text(encoding="utf-8")
    vpm_runner_src = schedule_src.split("// AUDIT-UNIT:UI-VPM-RUNNER", 1)[-1].split("// AUDIT-UNIT:", 1)[0]
    zhl_runner_src = schedule_src.split("// AUDIT-UNIT:UI-ZHL-RUNNER-ENGINE", 1)[-1].split("// AUDIT-UNIT:", 1)[0]
    vpm_render_src = render_src.split("// AUDIT-UNIT:UI-VPM-RENDER", 1)[-1].split("// AUDIT-UNIT:", 1)[0]
    schedule_contract_ok = (
        "SCHEDULE_TABLE_COLUMNS" in schedule_src
        and "function scheduleColumnCount" in schedule_src
        and "function scheduleErrorRowHtml" in schedule_src
        and "function scheduleCell" in schedule_src
        and "renderScheduleErrorRow" in vpm_runner_src
        and 'colspan="8"' not in vpm_runner_src
        and 'colspan="8"' not in zhl_runner_src
        and vpm_runner_src.count("renderScheduleErrorRow") >= 5
        and "function runVPMSchedule(" not in index_src
        and "function runDecoSchedule(" not in index_src
        and "const SCHEDULE_TABLE_COLUMNS" not in index_src
    )
    vpm_error_geometry_ok = all(
        detail.get("errorRowCount") == 1
        and detail.get("colspan") == detail.get("expected") == 8
        and detail.get("hasHelper")
        and detail.get("geometryOk")
        and "VPM engine failed to load" in detail.get("text", "")
        and not detail.get("console_errors")
        for detail in schedule_error_details.values()
    )
    canonical_src_ok = (
        gas_ok
        and "getGasLabel" in vpm_render_src
        and "getGasLabel(bottomFO2" in schedule_src
        and "getGasLabel(fracs.fO2" in schedule_src
        and not gas_details.get("forbiddenHits")
    )
    results["SL-BATCH2-VPM-ERROR-COLSPAN"] = (
        'colspan="8"' not in vpm_runner_src
        and vpm_runner_src.count("renderScheduleErrorRow") >= 5
    )
    results["SCHEDULE-ERROR-ROW-COLUMN-CONTRACT"] = schedule_contract_ok
    results["VPM-INVALID-ERROR-ROW-GEOMETRY"] = vpm_error_geometry_ok
    results["SCHEDULE-CANONICAL-GAS-LABELS"] = bool(canonical_src_ok)

    for case_id, passed in results.items():
        print(f"  {'PASS' if passed else 'FAIL'} [{case_id}]")
    if not all(results.values()):
        print(json.dumps({
            "visual": details,
            "nav": nav_details,
            "bottom_nav": bottom_nav_details,
            "gas": gas_details,
            "mobile_warning": mobile_warning_details,
            "vpm": vpm_details,
            "vpm_beyond_mod": vpm_beyond_mod_details,
            "zhl_beyond_mod": zhl_beyond_mod_details,
            "vpm_graph": vpm_graph_details,
            "schedule_error": schedule_error_details,
            "contingency_gas": contingency_gas_details,
            "gas_units": gas_units_details,
        }, indent=2))

    rows = [case_row(case_id, passed) for case_id, passed in results.items()]
    finish_suite(ROOT, rows, 0 if all(results.values()) else 1)


if __name__ == "__main__":
    raise SystemExit(main())
