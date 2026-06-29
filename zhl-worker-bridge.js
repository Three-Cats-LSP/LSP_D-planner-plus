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
    const w = worker;
    worker = null;
    if (w) {
      try {
        w.terminate();
      } catch (_) { /* already terminated */ }
    }
  }

  function handleWorkerFailure(msg) {
    if (!worker) return;
    consecutiveWorkerFailures += 1;
    const errMsg = consecutiveWorkerFailures >= MAX_WORKER_FAILURES
      ? 'ZHL worker crashed repeatedly — reload required'
      : msg;
    rejectAll(errMsg);
    killWorker();
    if (consecutiveWorkerFailures >= MAX_WORKER_FAILURES) {
      workerPermanentlyDisabled = true;
    }
  }

  function getWorkerScriptUrl() {
    const p = (typeof location !== 'undefined' && location.pathname) || '/';
    if (p.includes('/LSP_D-planner-plus/')) return '/LSP_D-planner-plus/zhl-schedule-worker.js';
    if (p.includes('/LSP_D-planner/')) return '/LSP_D-planner/zhl-schedule-worker.js';
    if (p.includes('/d-planner-plus/')) return '/d-planner-plus/zhl-schedule-worker.js';
    if (p.includes('/d-planner-ccr/')) return '/d-planner-ccr/zhl-schedule-worker.js';
    if (p.includes('/d-planner/')) return '/d-planner/zhl-schedule-worker.js';
    const base = p.replace(/[^/]*$/, '');
    return (base || '/LSP_D-planner-plus/') + 'zhl-schedule-worker.js';
  }

  function getWorker() {
    if (workerPermanentlyDisabled) {
      throw new Error('ZHL worker crashed repeatedly — reload required');
    }
    if (!worker) {
      worker = new Worker(getWorkerScriptUrl());
      worker.onmessage = function (e) {
        const { id, ok, result, error } = e.data || {};
        if (ok) {
          consecutiveWorkerFailures = 0;
          settlePending(id, true, result);
        } else {
          handleWorkerFailure(error || 'ZHL worker calculation failed');
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
        const p = pending.get(id);
        if (!p || p.timer !== timer) return;
        settlePending(id, false, new Error('ZHL worker timeout'));
        if (worker) handleWorkerFailure('ZHL worker timeout');
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
