/**
 * Main-thread bridge to zhl-schedule-worker.js (Tier 3).
 */
(function (global) {
  'use strict';

  let worker = null;
  let nextId = 1;
  const pending = new Map();

  function getWorker() {
    if (!worker) {
      worker = new Worker('zhl-schedule-worker.js');
      worker.onmessage = function (e) {
        const { id, ok, result, error } = e.data || {};
        const p = pending.get(id);
        if (!p) return;
        pending.delete(id);
        if (ok) p.resolve(result);
        else p.reject(new Error(error || 'Worker calculation failed'));
      };
      worker.onerror = function (err) {
        pending.forEach(p => p.reject(err));
        pending.clear();
        worker = null;
      };
    }
    return worker;
  }

  function calculateInWorker(levels, decoGases, settings, profileSplit, environment) {
    return new Promise((resolve, reject) => {
      const id = nextId++;
      pending.set(id, { resolve, reject });
      getWorker().postMessage({ id, levels, decoGases, settings, profileSplit, environment });
    });
  }

  global.ZhlWorkerBridge = { calculateInWorker };
})(typeof window !== 'undefined' ? window : self);
