/**
 * Main-thread bridge to zhl-schedule-worker.js (Tier 3).
 */
(function (global) {
  'use strict';

  const WORKER_TIMEOUT_MS = (
    typeof global.__LSP_ZHL_WORKER_TIMEOUT_MS === 'number'
    && global.__LSP_ZHL_WORKER_TIMEOUT_MS > 0
  ) ? global.__LSP_ZHL_WORKER_TIMEOUT_MS : 30000;

  const MAX_WORKER_FAILURES = 3;

  let worker = null;
  let nextId = 1;
  let consecutiveWorkerFailures = 0;
  let workerPermanentlyDisabled = false;
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

  function killWorker() {
    if (worker) {
      worker.terminate();
      worker = null;
    }
  }

  function handleWorkerFailure(msg) {
    consecutiveWorkerFailures += 1;
    rejectAll(msg);
    killWorker();
    nextId = 1;
    if (consecutiveWorkerFailures >= MAX_WORKER_FAILURES) {
      workerPermanentlyDisabled = true;
      rejectAll('ZHL worker crashed repeatedly — reload required');
    }
  }

  function getWorker() {
    if (workerPermanentlyDisabled) {
      throw new Error('ZHL worker crashed repeatedly — reload required');
    }
    if (!worker) {
      worker = new Worker('zhl-schedule-worker.js');
      worker.onmessage = function (e) {
        const { id, ok, result, error } = e.data || {};
        if (ok) {
          consecutiveWorkerFailures = 0;
          settlePending(id, true, result);
        } else {
          consecutiveWorkerFailures += 1;
          settlePending(id, false, new Error(error || 'Worker calculation failed'));
          if (consecutiveWorkerFailures >= MAX_WORKER_FAILURES) {
            workerPermanentlyDisabled = true;
            rejectAll('ZHL worker crashed repeatedly — reload required');
            killWorker();
            nextId = 1;
          }
        }
      };
      worker.onerror = function (err) {
        const msg = (err && err.message) || 'Worker error';
        handleWorkerFailure(msg);
      };
    }
    return worker;
  }

  function calculateInWorker(levels, decoGases, settings, profileSplit, environment) {
    if (workerPermanentlyDisabled) {
      return Promise.reject(new Error('ZHL worker crashed repeatedly — reload required'));
    }
    return new Promise((resolve, reject) => {
      const id = nextId++;
      const timer = setTimeout(() => {
        if (!pending.has(id)) return;
        handleWorkerFailure('ZHL worker timeout');
      }, WORKER_TIMEOUT_MS);
      pending.set(id, {
        resolve,
        reject,
        timer,
      });
      try {
        getWorker().postMessage({ id, levels, decoGases, settings, profileSplit, environment });
      } catch (e) {
        clearTimeout(timer);
        pending.delete(id);
        reject(e);
      }
    });
  }

  function terminate(resetDisabledFlag) {
    if (resetDisabledFlag === undefined) resetDisabledFlag = true;
    rejectAll('ZHL worker terminated');
    killWorker();
    nextId = 1;
    consecutiveWorkerFailures = 0;
    if (resetDisabledFlag) workerPermanentlyDisabled = false;
  }

  global.ZhlWorkerBridge = { calculateInWorker, terminate };
})(typeof window !== 'undefined' ? window : self);
