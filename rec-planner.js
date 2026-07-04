/**
 * REC planner dispatch — reads #recPlannerView inputs only.
 * Computation stays in index.html runPlanner (PADI path); this is the Level 2 entry point.
 */
function runRecPlan() {
  if (typeof runPlanner === 'function') return runPlanner();
}

window.runRecPlan = runRecPlan;
