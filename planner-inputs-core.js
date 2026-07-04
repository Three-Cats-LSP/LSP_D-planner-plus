/**
 * REC vs TECH planner input isolation (Level 2).
 * Each mode owns disjoint depth/BT element IDs; legacy aliases resolve by active mode.
 */
(function () {
  const REC_DEPTH_ID = 'recDepth';
  const REC_BT_ID = 'recBT';
  const TEC_DEPTH_ID = 'tecDepth';
  const TEC_BT_ID = 'tecBT';

  const LEGACY_MAP = {
    depth: REC_DEPTH_ID,
    bt: REC_BT_ID,
    decoDepth: TEC_DEPTH_ID,
    decoBT: TEC_BT_ID,
  };

  function isRecMode() {
    return typeof plannerAlgo !== 'undefined' && plannerAlgo === 'rec';
  }

  function activePlannerView() {
    return isRecMode() ? 'rec' : 'tec';
  }

  function resolvePlannerInputId(id) {
    if (!id) return id;
    if (id === 'decoDepth') return isRecMode() ? REC_DEPTH_ID : TEC_DEPTH_ID;
    if (id === 'decoBT') return isRecMode() ? REC_BT_ID : TEC_BT_ID;
    if (id === 'depth' || id === 'bt') return LEGACY_MAP[id];
    return id;
  }

  function plannerDepthId() {
    return isRecMode() ? REC_DEPTH_ID : TEC_DEPTH_ID;
  }

  function plannerBtId() {
    return isRecMode() ? REC_BT_ID : TEC_BT_ID;
  }

  function getPlannerDepthEl() {
    return document.getElementById(plannerDepthId());
  }

  function getPlannerBtEl() {
    return document.getElementById(plannerBtId());
  }

  function _snapInput(id) {
    const el = document.getElementById(id);
    if (!el) return null;
    return {
      value: el.value,
      depthM: el.dataset.depthM,
      volumeL: el.dataset.volumeL,
    };
  }

  function _restoreInput(id, snap) {
    if (!snap) return;
    const el = document.getElementById(id);
    if (!el) return;
    if (snap.value != null) el.value = snap.value;
    if (snap.depthM != null) el.dataset.depthM = snap.depthM;
    else delete el.dataset.depthM;
    if (snap.volumeL != null) el.dataset.volumeL = snap.volumeL;
    else delete el.dataset.volumeL;
  }

  const _viewSnapshots = { rec: null, tec: null };

  function snapshotPlannerView(view) {
    const v = view || activePlannerView();
    const depthId = v === 'rec' ? REC_DEPTH_ID : TEC_DEPTH_ID;
    const btId = v === 'rec' ? REC_BT_ID : TEC_BT_ID;
    _viewSnapshots[v] = {
      depth: _snapInput(depthId),
      bt: _snapInput(btId),
    };
  }

  function restorePlannerView(view) {
    const v = view || activePlannerView();
    const snap = _viewSnapshots[v];
    if (!snap) return;
    const depthId = v === 'rec' ? REC_DEPTH_ID : TEC_DEPTH_ID;
    const btId = v === 'rec' ? REC_BT_ID : TEC_BT_ID;
    _restoreInput(depthId, snap.depth);
    _restoreInput(btId, snap.bt);
    if (v === 'rec') _syncRecDepthBtSteppers?.();
    else _syncTecDepthBtSteppers?.();
  }

  function onPlannerViewSwitch(fromView, toView) {
    if (fromView) snapshotPlannerView(fromView);
    restorePlannerView(toView);
  }

  window.resolvePlannerInputId = resolvePlannerInputId;
  window.activePlannerView = activePlannerView;
  window.plannerDepthId = plannerDepthId;
  window.plannerBtId = plannerBtId;
  window.getPlannerDepthEl = getPlannerDepthEl;
  window.getPlannerBtEl = getPlannerBtEl;
  window.snapshotPlannerView = snapshotPlannerView;
  window.restorePlannerView = restorePlannerView;
  window.onPlannerViewSwitch = onPlannerViewSwitch;
  window.PLANNER_REC_DEPTH_ID = REC_DEPTH_ID;
  window.PLANNER_REC_BT_ID = REC_BT_ID;
  function getPlannerInputEl(id) {
    const rid = resolvePlannerInputId(id);
    return document.getElementById(rid);
  }

  window.getPlannerInputEl = getPlannerInputEl;
  window.PLANNER_TEC_DEPTH_ID = TEC_DEPTH_ID;
  window.PLANNER_TEC_BT_ID = TEC_BT_ID;
})();
