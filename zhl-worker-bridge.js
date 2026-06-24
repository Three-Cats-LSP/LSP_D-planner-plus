/**
 * Main-thread bridge to zhl-schedule-worker.js (Tier 3).
 */
(function (global) {
  'use strict';

  const WORKER_TIMEOUT_MS = 30000;

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
        [...pending.entries()].forEach(([id]) => {
          settlePending(id, false, new Error(msg));
        });
        worker = null;
      };
    }
    return worker;
  }

  function calculateInWorker(levels, decoGases, settings, profileSplit, environment) {
    return new Promise((resolve, reject) => {
      const id = nextId++;
      const timer = setTimeout(() => {
        if (!pending.has(id)) return;
        settlePending(id, false, new Error('ZHL worker timeout'));
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
    [...pending.entries()].forEach(([id]) => {
      settlePending(id, false, new Error('ZHL worker terminated'));
    });
    if (worker) {
      worker.terminate();
      worker = null;
    }
  }

  global.ZhlWorkerBridge = { calculateInWorker, terminate };
})(typeof window !== 'undefined' ? window : self);
