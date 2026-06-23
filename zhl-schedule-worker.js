/**
 * ZHL schedule Web Worker — Tier 3 isolated Bühlmann engine.
 */
importScripts('zhl-engine-bundle.js');

self.onmessage = function (e) {
  const msg = e.data || {};
  const { id, levels, decoGases, settings, profileSplit, environment } = msg;
  try {
    const result = ZhlEngineBundle.calculate(
      levels,
      decoGases,
      settings,
      profileSplit,
      environment
    );
    self.postMessage({ id, ok: true, result });
  } catch (err) {
    self.postMessage({ id, ok: false, error: err && err.message ? err.message : String(err) });
  }
};
