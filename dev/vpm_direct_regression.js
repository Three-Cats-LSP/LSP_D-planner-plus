'use strict';

const fs = require('fs');
const path = require('path');
const {
  calculateVpm,
  assertCanonicalGasLabels,
  summarizeVpm,
} = require('./vpm_direct_host');

const ROOT = path.resolve(__dirname, '..');
const SUITE_ID = 'SUITE-VPM-DIRECT';
const RESULTS_PATH = path.join(ROOT, 'dev', 'audit-suite-results', `${SUITE_ID}.json`);

const CASES = [
  'VPM-DIRECT-OC-SMOKE',
  'VPM-DIRECT-TRIMIX-SMOKE',
  'VPM-REFERENCE-OC-SMOKE',
  'VPM-REFERENCE-TRIMIX-SMOKE',
  'RDP-REC-MIX-NARROWNESS',
];

const PROFILES = {
  oc: {
    levels: [{ depth: 40, time: 25, o2: 21, he: 0 }],
    gases: [{ depth: 21, o2: 50, he: 0 }, { depth: 6, o2: 100, he: 0 }],
    settings: {},
    expectedLabels: ['Air', '50/00', '100%'],
    sanity: { minRuntime: 30, maxRuntime: 180, minFirstStop: 3, maxFirstStop: 30, minStopCount: 1, maxStopCount: 20 },
    reference: { totalRuntime: 108, tts: 0, firstStop: 30, stopCount: 10 },
  },
  trimix: {
    levels: [{ depth: 60, time: 20, o2: 18, he: 45 }],
    gases: [{ depth: 30, o2: 32, he: 0 }, { depth: 21, o2: 50, he: 0 }, { depth: 6, o2: 100, he: 0 }],
    settings: {},
    expectedLabels: ['18/45', '32/00', '50/00', '100%'],
    sanity: { minRuntime: 40, maxRuntime: 240, minFirstStop: 3, maxFirstStop: 60, minStopCount: 1, maxStopCount: 25 },
    reference: { totalRuntime: 95, tts: 0, firstStop: 48, stopCount: 16 },
  },
};

// Narrow deterministic smoke baselines for the current VPM reference path.
// These intentionally compare stable summaries, not full profile equivalence.
function pass(caseId) {
  return { case_id: caseId, status: 'PASS' };
}

function fail(caseId, message) {
  return { case_id: caseId, status: 'FAIL', message };
}

function finiteSchedule(summary) {
  return Number.isFinite(summary.totalRuntime)
    && summary.totalRuntime > 0
    && Number.isFinite(summary.tts)
    && summary.stopCount > 0
    && summary.stops.every((stop) => Number.isFinite(stop.depth) && Number.isFinite(stop.time));
}

function directSmoke(caseId, profile) {
  const result = calculateVpm(profile.levels, profile.gases, profile.settings, 'VPMB');
  if (result.error || result.code) return fail(caseId, `engine error: ${result.code || result.error}`);
  const summary = summarizeVpm(result);
  const labelCheck = assertCanonicalGasLabels(summary.gasLabels);
  const missing = profile.expectedLabels.filter((label) => !summary.gasLabels.includes(label));
  const s = profile.sanity;
  const ok = finiteSchedule(summary)
    && labelCheck.ok
    && missing.length === 0
    && summary.totalRuntime >= s.minRuntime
    && summary.totalRuntime <= s.maxRuntime
    && summary.firstStop >= s.minFirstStop
    && summary.firstStop <= s.maxFirstStop
    && summary.stopCount >= s.minStopCount
    && summary.stopCount <= s.maxStopCount;
  return ok ? pass(caseId) : fail(caseId, JSON.stringify({ summary, invalidLabels: labelCheck.invalid, missing }));
}

function referenceSmoke(caseId, profile) {
  const result = calculateVpm(profile.levels, profile.gases, profile.settings, 'VPMB');
  if (result.error || result.code) return fail(caseId, `engine error: ${result.code || result.error}`);
  const summary = summarizeVpm(result);
  const ref = profile.reference;
  const ok = Math.abs(summary.totalRuntime - ref.totalRuntime) <= 2
    && Math.abs(summary.tts - ref.tts) <= 2
    && Math.abs(summary.firstStop - ref.firstStop) <= 3
    && Math.abs(summary.stopCount - ref.stopCount) <= 2;
  return ok ? pass(caseId) : fail(caseId, JSON.stringify({ summary, reference: ref }));
}

function rdpNarrowness() {
  global.window = {};
  require(path.join(ROOT, 'padi-engine.js'));
  const pe = global.window.PadiEngine;
  const ok = pe
    && pe.normalizeRecMix('air') === 'air'
    && pe.normalizeRecMix('ean32') === 'ean32'
    && pe.normalizeRecMix('ean36') === 'ean36'
    && pe.normalizeRecMix('ean50') === 'air'
    && pe.normalizeRecMix('50/00') === 'air'
    && pe.normalizeRecMix('18/45') === 'air'
    && pe.getNitroxNDL(18, 'ean50') === pe.getNitroxNDL(18, 'air');
  return ok ? pass('RDP-REC-MIX-NARROWNESS') : fail('RDP-REC-MIX-NARROWNESS', 'RDP accepted or distinguished a non-rec gas');
}

function main() {
  const rows = [
    directSmoke('VPM-DIRECT-OC-SMOKE', PROFILES.oc),
    directSmoke('VPM-DIRECT-TRIMIX-SMOKE', PROFILES.trimix),
    referenceSmoke('VPM-REFERENCE-OC-SMOKE', PROFILES.oc),
    referenceSmoke('VPM-REFERENCE-TRIMIX-SMOKE', PROFILES.trimix),
    rdpNarrowness(),
  ];
  fs.mkdirSync(path.dirname(RESULTS_PATH), { recursive: true });
  const payload = { suite_id: SUITE_ID, cases: rows };
  fs.writeFileSync(RESULTS_PATH, `${JSON.stringify(payload, null, 2)}\n`);
  for (const row of rows) {
    console.log(`${row.status === 'PASS' ? 'PASS' : 'FAIL'} [${row.case_id}]${row.message ? ` ${row.message}` : ''}`);
  }
  console.log('---LSP-AUDIT-CASES---');
  console.log(JSON.stringify(payload));
  return rows.every((row) => row.status === 'PASS') ? 0 : 1;
}

process.exitCode = main();
