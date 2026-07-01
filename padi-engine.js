/**
 * PADI RDP Engine — recreational NDL lookup (Air, EAN32, EAN36).
 * Pure table lookup against PADI / Enriched Air Diver standard tables.
 * Loaded before main inline script; exposes window.PadiEngine and legacy globals.
 */
const PadiEngine = (() => {
  'use strict';

  const REC_MIXES = Object.freeze(['air', 'ean32', 'ean36']);

  const PADI_DEPTHS_M = [10, 12, 15, 18, 21, 24, 27, 30, 33, 36, 40];
  const PADI_DEPTHS_FT = [35, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130];
  const PADI_NDL_M = [310, 230, 100, 60, 35, 25, 20, 15, 13, 10, 8];
  const PADI_NDL_FT = [310, 230, 100, 60, 35, 25, 20, 15, 13, 10, 8];
  const PADI_GROUPS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K'];
  const PADI_TABLE_MAX_M = PADI_DEPTHS_M[PADI_DEPTHS_M.length - 1];
  const PADI_TABLE_MAX_FT = PADI_DEPTHS_FT[PADI_DEPTHS_FT.length - 1];

  // IANTD/PADI Enriched Air Diver standard tables — indexed to PADI_DEPTHS_M
  const NITROX_NDL_EAN32 = [310, 230, 145, 75, 55, 30, 25, 20, 16, 13, 9];
  const NITROX_NDL_EAN36 = [310, 230, 170, 100, 60, 40, 30, 25, 20, 15, 10];

  /** Normalize mix to one of air / ean32 / ean36 (Rec mode standard gases only). */
  function normalizeRecMix(mix) {
    if (mix === 'ean32' || mix === 'ean36') return mix;
    return 'air';
  }

  /** PADI RDP row: first table depth >= dive depth (conservative ceiling lookup). */
  function padiTableRowIndex(depthM) {
    if (!Number.isFinite(depthM) || depthM <= 0) return null;
    if (depthM > PADI_TABLE_MAX_M + 1e-6) return null;
    for (let i = 0; i < PADI_DEPTHS_M.length; i++) {
      if (PADI_DEPTHS_M[i] >= depthM - 1e-9) return i;
    }
    return PADI_DEPTHS_M.length - 1;
  }

  function getNitroxNDL(depthM, mix) {
    const idx = padiTableRowIndex(depthM);
    if (idx == null) return 0;
    const m = normalizeRecMix(mix);
    if (m === 'ean32') return NITROX_NDL_EAN32[idx];
    if (m === 'ean36') return NITROX_NDL_EAN36[idx];
    return PADI_NDL_M[idx];
  }

  function padiNDL(depthM, mix) {
    return getNitroxNDL(depthM, mix || 'air');
  }

  function padiGroup(depthM, time, mix) {
    const ndl = getNitroxNDL(depthM, mix || 'air');
    const pct = ndl > 0 ? time / ndl : 1;
    const gi = Math.min(PADI_GROUPS.length - 1, Math.floor(pct * PADI_GROUPS.length * 0.7));
    return PADI_GROUPS[gi];
  }

  function recMixFO2(mix) {
    const m = normalizeRecMix(mix);
    if (m === 'ean32') return 0.32;
    if (m === 'ean36') return 0.36;
    return 0.21;
  }

  return {
    REC_MIXES,
    PADI_DEPTHS_M,
    PADI_DEPTHS_FT,
    PADI_NDL_M,
    PADI_NDL_FT,
    PADI_GROUPS,
    PADI_TABLE_MAX_M,
    PADI_TABLE_MAX_FT,
    NITROX_NDL_EAN32,
    NITROX_NDL_EAN36,
    normalizeRecMix,
    padiTableRowIndex,
    getNitroxNDL,
    padiNDL,
    padiGroup,
    recMixFO2,
  };
})();

if (typeof window !== 'undefined') {
  window.PadiEngine = PadiEngine;
  window.PADI_DEPTHS_M = PadiEngine.PADI_DEPTHS_M;
  window.PADI_DEPTHS_FT = PadiEngine.PADI_DEPTHS_FT;
  window.PADI_NDL_M = PadiEngine.PADI_NDL_M;
  window.PADI_NDL_FT = PadiEngine.PADI_NDL_FT;
  window.PADI_GROUPS = PadiEngine.PADI_GROUPS;
  window.PADI_TABLE_MAX_M = PadiEngine.PADI_TABLE_MAX_M;
  window.PADI_TABLE_MAX_FT = PadiEngine.PADI_TABLE_MAX_FT;
  window.NITROX_NDL_EAN32 = PadiEngine.NITROX_NDL_EAN32;
  window.NITROX_NDL_EAN36 = PadiEngine.NITROX_NDL_EAN36;
  window.padiTableRowIndex = PadiEngine.padiTableRowIndex;
  window.getNitroxNDL = PadiEngine.getNitroxNDL;
  window.padiNDL = PadiEngine.padiNDL;
  window.padiGroup = PadiEngine.padiGroup;
}
