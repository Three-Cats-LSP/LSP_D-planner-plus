/**
 * Main-thread bridge to zhl-schedule-worker.js (Tier 3).
 */
(function (global) {
  'use strict';

  const WORKER_TIMEOUT_MS = (
    typeof global.__LSP_ZHL_WORKER_TIMEOUT_MS === 'number'
    && global.__LSP_ZHL_WORKER_TIMEOUT_MS > 0
  ) ? global.__LSP_ZHL_WORKER_TIMEOUT_MS : 30000;

  let worker = null;
  let nextId = 1;
  const pending = new Map();

  function settlePending(id, ok, value) {
    const p = pending.get(id);
    if (!p) return;
    pending.delete(id);
    clearTimeout(p.timer);
    if (ok) p.resolve(value);
    else p.reject(value);
  }

  function rejectAll(msg) {
    [...pending.keys()].forEach((pendingId) => {
      settlePending(pendingId, false, new Error(msg));
    });
  }

  function getWorker() {
    if (!worker) {
      worker = new Worker('zhl-schedule-worker.js');
      worker.onmessage = function (e) {
        const { id, ok, result, error } = e.data || {};
        if (ok) settlePending(id, true, result);
        else settlePending(id, false, new Error(error || 'Worker calculation failed'));
      };
      worker.onerror = function (err) {
        const msg = (err && err.message) || 'Worker error';
        rejectAll(msg);
        worker = null;
      };
    }
    return worker;
  }

  function killWorker() {
    if (worker) {
      worker.terminate();
      worker = null;
    }
  }

  function calculateInWorker(levels, decoGases, settings, profileSplit, environment) {
    return new Promise((resolve, reject) => {
      const id = nextId++;
      const timer = setTimeout(() => {
        if (!pending.has(id)) return;
        rejectAll('ZHL worker timeout');
        killWorker();
      }, WORKER_TIMEOUT_MS);
      pending.set(id, {
        resolve,
        reject,
        timer,
      });
      getWorker().postMessage({ id, levels, decoGases, settings, profileSplit, environment });
    });
  }

  function terminate() {
    rejectAll('ZHL worker terminated');
    killWorker();
  }

  global.ZhlWorkerBridge = { calculateInWorker, terminate };
})(typeof window !== 'undefined' ? window : self);
