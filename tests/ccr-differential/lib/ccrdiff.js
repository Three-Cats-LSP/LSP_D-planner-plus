/* CCR engine differential test library — LSP production engine adapter + comparisons */
(function (root) {
  'use strict';

  const CLASS = {
    PASS: 'PASS',
    EXPECTED_DIFFERENCE: 'EXPECTED_DIFFERENCE',
    LSP_SUSPECT: 'LSP_SUSPECT',
    COMPARATOR_SUSPECT: 'COMPARATOR_SUSPECT',
    INCONCLUSIVE: 'INCONCLUSIVE',
  };

  function levelsFromFixture(fx) {
    return fx.profile.levels.map(l => {
      const o2 = l.o2 != null
        ? Math.round(l.o2 <= 1 ? l.o2 * 100 : l.o2)
        : Math.round((fx.circuit.diluent.o2 || 0.21) * 100);
      const he = l.he != null
        ? Math.round(l.he <= 1 ? l.he * 100 : l.he)
        : Math.round((fx.circuit.diluent.he || 0) * 100);
      return { depth: l.depthM, time: l.timeMin, o2, he };
    });
  }

  function settingsFromFixture(fx) {
    const sp = fx.circuit.setpointsBar || {};
    const r = fx.ratesMPerMin || {};
    const env = fx.environment || {};
    const dec = fx.decompression || {};
    const round = fx.rounding || {};
    const s = {
      metric: true,
      waterType: 0,
      circuit: fx.circuit.type || 'CCR',
      bailout: false,
      setpoint: sp.bottom || 1.3,
      descentSetpoint: sp.descent != null ? sp.descent : 0.7,
      bottomSetpoint: sp.bottom || 1.3,
      decoSetpoint: sp.deco || sp.bottom || 1.3,
      descentRate: r.descent || 20,
      ascentRate: r.deepAscent || 9,
      decoAscentRate: r.decoAscent || 9,
      surfaceAscentRate: r.surfaceAscent || 3,
      stepSize: dec.stepM || 3,
      lastStop: dec.lastStopM || 3,
      minStopTime: (round.minimumStopSec || 60) / 60,
      gfLo: dec.gfLow || 30,
      gfHi: dec.gfHigh || 80,
      ppO2Bottom: 1.4,
      ppO2Deco: 1.6,
      conservatism: 0,
      altitude: env.altitudeM || 0,
      acclimatized: env.acclimatized !== false,
    };
    if (round.mode === 'one-second') {
      s.stopRounding = 'fractional';
      s.minStopTime = (round.minimumStopSec || 1) / 60;
    } else {
      s.stopRounding = 'wholeminute';
    }
    if (fx.bailoutGases && fx.bailoutGases.length) {
      s.bailout = true;
    }
    return s;
  }

  function decoGasesFromFixture(fx) {
    if (!fx.bailoutGases || !fx.bailoutGases.length) return [];
    return fx.bailoutGases
      .filter(g => g.available !== false)
      .map(g => ({ o2: Math.round(g.o2 * 100), he: Math.round((g.he || 0) * 100) }));
  }

  function stopsMap(result, roundMinutes) {
    const out = {};
    (result.stops || []).forEach(s => {
      const t = s.dur != null ? s.dur : s.time;
      if (!t || t <= 0) return;
      const d = Math.round(s.depth);
      const add = roundMinutes ? Math.round(t) : t;
      out[d] = (out[d] || 0) + add;
    });
    return out;
  }

  function stopsByDepth(stops) {
    const out = {};
    (stops || []).forEach(s => {
      if (s.depthM == null) return;
      const t = s.durationMin;
      if (!t || t <= 0) return;
      out[s.depthM] = (out[s.depthM] || 0) + t;
    });
    return out;
  }

  function firstStopDepth(result) {
    const depths = Object.keys(stopsMap(result, false)).map(Number);
    return depths.length ? Math.max(...depths) : 0;
  }

  function totalStopMin(result) {
    return (result.stops || []).reduce((a, s) => a + (s.dur || s.time || 0), 0);
  }

  function normalizeLsp(fx, raw, meta) {
    if (!raw || raw.error) {
      return {
        engine: 'LSP',
        engineVersion: meta.version || 'unknown',
        scenarioId: fx.id,
        error: raw && raw.error ? raw.error : 'no result',
        code: raw && raw.code ? raw.code : null,
        stops: [],
        summary: {},
      };
    }
    const sm = stopsMap(raw, false);
    const stops = Object.keys(sm).map(Number).sort((a, b) => b - a).map(d => ({
      depthM: d,
      durationMin: sm[d],
      gasLabel: 'loop',
    }));
    return {
      engine: 'LSP',
      engineVersion: meta.version || 'unknown',
      scenarioId: fx.id,
      commit: meta.commit || 'not_available',
      inputChecksum: meta.inputChecksum || 'not_available',
      segments: (raw.plan || []).map(seg => ({
        type: seg.type,
        depth: seg.depth,
        time: seg.time,
        run: seg.run,
        gas: seg.gas,
      })),
      stops,
      summary: {
        firstStopDepthM: firstStopDepth(raw),
        ttsMin: raw.tts != null ? raw.tts : 'not_available',
        runtimeMin: raw.totalRuntime,
        cnsPercent: raw.totalCNS != null ? raw.totalCNS : 'not_available',
        otu: raw.totalOTU != null ? raw.totalOTU : 'not_available',
        totalStopMin: totalStopMin(raw),
      },
      tissuesN2: raw.finalTissues ? raw.finalTissues.map(t => t.pN2) : 'not_available',
      tissuesHe: raw.finalTissues ? raw.finalTissues.map(t => t.pHe || 0) : 'not_available',
      warnings: raw.warnings || [],
    };
  }

  function assertIntegrity(raw, label) {
    if (!raw || raw.error) throw new Error(`${label}: engine error — ${raw && raw.error}`);
    if (!Number.isFinite(raw.totalRuntime) || raw.totalRuntime <= 0) {
      throw new Error(`${label}: invalid totalRuntime ${raw.totalRuntime}`);
    }
    if (!Array.isArray(raw.plan) || !raw.plan.length) throw new Error(`${label}: empty plan`);
    if (raw.finalTissues) {
      raw.finalTissues.forEach((t, i) => {
        if (!Number.isFinite(t.pN2) || t.pN2 < 0) throw new Error(`${label}: invalid tissue N2 @${i}`);
        const pHe = t.pHe || 0;
        if (!Number.isFinite(pHe) || pHe < 0) throw new Error(`${label}: invalid tissue He @${i}`);
      });
    }
    let lastRun = -Infinity;
    let lastStopD = Infinity;
    raw.plan.forEach((seg, i) => {
      if (seg.run != null && seg.run + 1e-9 < lastRun) {
        throw new Error(`${label}: runtime decreased at segment ${i}`);
      }
      if (seg.run != null) lastRun = seg.run;
      if (seg.depth != null && seg.depth < -1e-6) throw new Error(`${label}: negative depth @${i}`);
      if (seg.type === 'stop' || seg.type === 'deco') {
        if (seg.depth > lastStopD + 1e-6) throw new Error(`${label}: stop depth increased during ascent @${i}`);
        lastStopD = seg.depth;
      }
    });
  }

  function roundedTtsTol(refTts, cfg) {
    const floor = (cfg.tolerances && cfg.tolerances.roundedTtsMin && cfg.tolerances.roundedTtsMin.floor) || 2;
    const pct = (cfg.tolerances && cfg.tolerances.roundedTtsMin && cfg.tolerances.roundedTtsMin.pct) || 0.05;
    const base = Number.isFinite(refTts) ? refTts : 0;
    return Math.max(floor, pct * base);
  }

  function findExpected(expected, scenarioId, pair, field) {
    return (expected || []).find(e =>
      e.scenarioId === scenarioId &&
      e.pair && e.pair[0] === pair[0] && e.pair[1] === pair[1] &&
      (!field || e.field === field)
    );
  }

  function compareStopSchedules(lsp, ref, fx, cfg) {
    const precise = fx.rounding && fx.rounding.mode === 'one-second';
    const tolMin = precise
      ? ((cfg.tolerances && cfg.tolerances.preciseStopSec) || 15) / 60
      : ((cfg.tolerances && cfg.tolerances.roundedStopSec) || 60) / 60;
    const lmap = stopsByDepth(lsp.stops);
    const rmap = stopsByDepth(ref.stops);
    const depths = new Set([...Object.keys(lmap), ...Object.keys(rmap)].map(Number));
    const issues = [];
    depths.forEach(d => {
      const lv = lmap[d] || 0;
      const rv = rmap[d] || 0;
      if (lv === 0 && rv === 0) return;
      const delta = Math.abs(lv - rv);
      if (delta > tolMin) {
        issues.push({ field: `stop@${d}m`, lsp: lv, ref: rv, delta, tol: tolMin });
      }
    });
    return issues;
  }

  function compareSummaries(lsp, ref, fx, cfg, expected) {
    const pair = [lsp.engine, ref.engine];
    const step = (cfg.tolerances && cfg.tolerances.firstStopStepM) || 3;
    const issues = [];
    const ls = lsp.summary || {};
    const rs = ref.summary || {};

    if (ls.firstStopDepthM != null && rs.firstStopDepthM != null) {
      const d = Math.abs(ls.firstStopDepthM - rs.firstStopDepthM);
      if (d > step) {
        issues.push({
          field: 'firstStopDepthM',
          lsp: ls.firstStopDepthM,
          ref: rs.firstStopDepthM,
          delta: d,
        });
      }
    }
    if (ls.runtimeMin != null && rs.runtimeMin != null) {
      const tol = roundedTtsTol(rs.runtimeMin, cfg);
      const d = Math.abs(ls.runtimeMin - rs.runtimeMin);
      if (d > tol) {
        issues.push({ field: 'runtimeMin', lsp: ls.runtimeMin, ref: rs.runtimeMin, delta: d, tol });
      }
    }
    if (ls.ttsMin != null && rs.ttsMin != null && ls.ttsMin !== 'not_available') {
      const tol = roundedTtsTol(rs.ttsMin, cfg);
      const d = Math.abs(ls.ttsMin - rs.ttsMin);
      if (d > tol) {
        issues.push({ field: 'ttsMin', lsp: ls.ttsMin, ref: rs.ttsMin, delta: d, tol });
      }
    }
    if (ls.cnsPercent !== 'not_available' && rs.cnsPercent != null) {
      const tol = (cfg.tolerances && cfg.tolerances.cnsPercent) || 3;
      const d = Math.abs(ls.cnsPercent - rs.cnsPercent);
      if (d > tol) {
        issues.push({ field: 'cnsPercent', lsp: ls.cnsPercent, ref: rs.cnsPercent, delta: d, tol });
      }
    }
    if (ls.otu !== 'not_available' && rs.otu != null) {
      const tol = (cfg.tolerances && cfg.tolerances.otu) || 5;
      const d = Math.abs(ls.otu - rs.otu);
      if (d > tol) {
        issues.push({ field: 'otu', lsp: ls.otu, ref: rs.otu, delta: d, tol });
      }
    }

    const pairHasDocumentedLadderDiff = ['firstStopDepthM', 'runtimeMin', 'ttsMin'].some(f =>
      findExpected(expected, fx.id, pair, f)
    );
    const stopIssues = (!pairHasDocumentedLadderDiff
      && ls.firstStopDepthM != null && rs.firstStopDepthM != null
      && Math.abs(ls.firstStopDepthM - rs.firstStopDepthM) <= step)
      ? compareStopSchedules(lsp, ref, fx, cfg)
      : [];
    stopIssues.forEach(si => {
      const exp = findExpected(expected, fx.id, pair, si.field);
      if (!exp) issues.push(si);
    });

    if (!issues.length) return { classification: CLASS.PASS, issues: [] };

    const allExpected = issues.every(issue => {
      const exp = findExpected(expected, fx.id, pair, issue.field);
      return exp && exp.classification === CLASS.EXPECTED_DIFFERENCE;
    });
    if (allExpected) return { classification: CLASS.EXPECTED_DIFFERENCE, issues };

    return { classification: CLASS.LSP_SUSPECT, issues };
  }

  function runLspScenario(win, fx, meta) {
    const levels = levelsFromFixture(fx);
    const settings = settingsFromFixture(fx);
    const gases = decoGasesFromFixture(fx);

    if (fx.expectInvalid) {
      const raw = win.ZHLEngine.calculate(levels, gases, settings);
      if (raw && raw.error) {
        if (fx.expectedCode && raw.code !== fx.expectedCode) {
          throw new Error(`${fx.id}: expected code ${fx.expectedCode}, got ${raw.code || 'none'}: ${raw.error}`);
        }
        return normalizeLsp(fx, raw, meta);
      }
      throw new Error(`${fx.id}: expected rejection (${fx.expectedCode}), but a schedule was produced`);
    }

    if (fx.repetitive && fx.repetitive.repeatProfile) {
      const first = win.ZHLEngine.calculate(levels, gases, settings);
      assertIntegrity(first, fx.id + ' dive1');
      if (!first.finalTissues) throw new Error('dive1 missing finalTissues for repetitive carry');
      const repSettings = Object.assign({}, settings, {
        _preTissues: first.finalTissues.map(t => ({ pN2: t.pN2, pHe: t.pHe || 0 })),
        _surfaceInterval: fx.repetitive.surfaceIntervalMin || 60,
      });
      const raw = win.ZHLEngine.calculate(levels, gases, repSettings);
      assertIntegrity(raw, fx.id);
      return normalizeLsp(fx, raw, meta);
    }

    const raw = win.ZHLEngine.calculate(levels, gases, settings);
    assertIntegrity(raw, fx.id);
    return normalizeLsp(fx, raw, meta);
  }

  function assertFixtureEffectiveness(rows, rules) {
    const byId = {};
    rows.forEach(r => { byId[r.scenarioId] = r; });
    const failures = [];
    Object.keys(rules || {}).forEach(id => {
      const rule = rules[id];
      const row = byId[id];
      const base = byId[rule.baseline];
      if (!row || !base || !row.lsp || !base.lsp) return;
      const a = row.lsp.summary || {};
      const b = base.lsp.summary || {};
      const same = (rule.fields || []).every(f => JSON.stringify(a[f]) === JSON.stringify(b[f]));
      if (same) {
        failures.push(`${id}: identical ${(rule.fields || []).join(', ')} to ${rule.baseline}`);
      }
    });
    return failures;
  }

  function validateFixtureShape(fx) {
    const required = ['id', 'description', 'profile', 'circuit', 'decompression'];
    required.forEach(k => {
      if (!fx[k]) throw new Error(`fixture ${fx.id || '?'} missing ${k}`);
    });
    if (!fx.profile.levels || !fx.profile.levels.length) {
      throw new Error(`fixture ${fx.id} has no profile levels`);
    }
  }

  function runMetamorphic(win, baseFx, meta) {
    const results = [];
    const calc = (fx) => runLspScenario(win, fx, meta);

    const shallow = Object.assign({}, baseFx, {
      id: 'meta-shallow',
      profile: { levels: [{ depthM: 30, timeMin: 20 }], timeConvention: 'at-depth' },
    });
    const deep = Object.assign({}, baseFx, {
      id: 'meta-deep',
      profile: { levels: [{ depthM: 50, timeMin: 20 }], timeConvention: 'at-depth' },
    });
    const rSh = calc(shallow);
    const rDeep = calc(deep);
    if ((rDeep.summary.runtimeMin || 0) < (rSh.summary.runtimeMin || 0)) {
      throw new Error('metamorphic: deeper dive shortened runtime');
    }
    results.push('depth↑ → RT not shorter ✓');

    const gfHigh = Object.assign({}, baseFx, {
      id: 'meta-gf',
      decompression: Object.assign({}, baseFx.decompression, { gfHigh: 50 }),
    });
    const gfLow = Object.assign({}, baseFx, {
      id: 'meta-gf2',
      decompression: Object.assign({}, baseFx.decompression, { gfHigh: 90 }),
    });
    const r50 = calc(gfHigh);
    const r90 = calc(gfLow);
    if ((r50.summary.runtimeMin || 0) < (r90.summary.runtimeMin || 0)) {
      throw new Error('metamorphic: lower GF high shortened runtime');
    }
    results.push('GF high↓ → RT not shorter ✓');

    const a = calc(baseFx);
    const b = calc(baseFx);
    if (JSON.stringify(a.summary) !== JSON.stringify(b.summary)) {
      throw new Error('metamorphic: nondeterministic output');
    }
    results.push('deterministic repeat ✓');

    return results;
  }

  root.CCRDiff = {
    CLASS,
    levelsFromFixture,
    settingsFromFixture,
    normalizeLsp,
    assertIntegrity,
    compareSummaries,
    runLspScenario,
    runMetamorphic,
    assertFixtureEffectiveness,
    validateFixtureShape,
    stopsMap,
    firstStopDepth,
  };
})(typeof window !== 'undefined' ? window : globalThis);
