# Seven-Lens Review Playbook

This is the portable review knowledge base for Cursor, Codex, and human auditors. It supplements the workflow and protocol; it does not replace their machine-enforced gates.

## Non-Negotiable Review Standard

1. Trace the complete path: visible user event -> writer -> normalized state -> algorithm/consumer -> rendered or exported result.
2. Test the physical contract, not a label, adapter property, helper call, or rounded display alone.
3. Establish a failing baseline at the recorded pre-fix commit. A test first written after the fix is not baseline evidence.
4. Keep AUDITOR and FIXER sessions separate. The audit checkpoint contains reports and open findings only.
5. Close only through `python tools/seven_lens_protocol.py check-all --require-artifacts` and the release profile.

## Dual-State and Unit Controls

Treat every displayed value plus canonical dataset as a replicated-state system.

- Enumerate every writer: typing, range input, stepper, preset, restore, dynamic creation, unit switch, and programmatic assignment.
- Enumerate every reader: calculator, validator, engine adapter, contingency, gas planning, persistence, and export.
- Run from metric and imperial initial states.
- Test switch -> edit -> consume -> roundtrip, not only switch -> consume.
- Use non-round values that reveal conversion drift.
- Assert that the final physical consumer receives the intended SI value.
- Verify dynamic controls and newly appended cards, not only fixed initial markup.
- For repeated controls, create at least one item while already in each unit mode;
  assert value, min, max, step, validity, canonical state, and final consumer.

## Stateful Regression Suites

- Snapshot values, checked state, datasets, classes that drive behavior, globals, storage, dynamic nodes, units, and engine caches.
- Restore in dependency order, then compare the complete snapshot.
- Run the case twice in fresh contexts.
- Run the suite twice and in shuffled order when shared state is involved.
- Fail if any case leaves tracked state changed, even when its assertions pass.
- Never let a focused green case override a red full suite.

## Browser Evidence

- Tested actions must be visible, enabled, and unforced. Force is permitted only for documented setup that is outside the tested contract.
- Capture before, immediately after the user action, at the normalized state boundary, at the final consumer, and after restoration.
- Reject empty traces, empty assertions, duplicate IDs, non-finite values, evaluation errors, console errors, and page errors.
- Require repeatable captures and assertions in fresh browser contexts.
- Hash the trace specification and artifact; bind both to the verified commit.
- Declare stable case IDs in each trace. A finding may cite a trace only when the
  trace declares every regression case used by that finding.
- Include adverse paths: invalid input, minimum, maximum, mode transition, repeated action, and navigation away/back.

## Cross-Unit Visual Invariants

- Treat the rendered page as a contract across markup, canonical writers, CSS,
  renderers, and responsive breakpoints. Reading one stylesheet is not enough.
- For two-column tools, assert the planner and result bounding boxes remain in
  their declared columns after generating results and revealing conditional
  rows. Hidden grid children becoming visible is a required test case.
- Give semantic roles canonical tokens. Gas-switch dots, graph flags, legend
  keys, banner pills, and schedule rows must not invent independent yellows.
- Compare computed RGB values in both themes; comparing class names or CSS source
  text is insufficient.
- Assert exact labels such as `Bottom:` and `Deco 1:` when punctuation is part of
  the approved design.
- Check canonical DOM writers after mode changes. Static markup with one icon can
  still render two icons when a legacy writer inserts an emoji.
- A UI cycle cannot close while the cross-unit visual suite is red, even if the
  defect originated before the cycle's nominal source boundary.

## Post-Cycle-9 App Contracts

- Deco schedule table shape is a product contract: `Phase`, `Depth`, `Stop`,
  `Run`, `Mix`, `ppO2`, `EAD`. Do not reintroduce a visible `TTS` column.
- Main deco and contingency schedules must use the same column order, widths,
  gas-switch formatting, and light/dark/mobile behavior.
- Gas-switch rows must not invent a separate background treatment unless the
  design contract changes; use the same semantic yellow for icon/text/legend.
- Operational gases render as `Air`, `100%`, or `OO/HH` across schedules,
  graphs, contingency controls, banners, exports, and generated bundles.
- Gas consumption is a bar-card experience, not a table. Values are
  volume-first (`L(bar)` or `ft3(psi)`), and the bar represents remaining gas
  draining from full toward zero.
- Warning banners use the unified contingency-readable warning style with one
  warning icon. Reject duplicate icons, leftover `!` prefixes, and inconsistent
  fonts between main deco and contingency.
- The full dive graph is part of Dive Profile. There is no separate Graphs tab;
  GF curve belongs under Tissues.
- Travel gas cards follow the same gas-card design as deco/bottom gases, with
  trimix support, `Switch Depth`, and a surface-breathable MinOD requirement.

## Responsive Navigation Grids

- Odd navigation-item counts on responsive grids require explicit row-filling
  rules. Do not rely on auto-placement when the final row would leave an orphan
  cell.
- Every tile must retain a coherent visible boundary: lower dividers between
  stacked rows, right dividers between columns, and a separator between Tools and
  Settings on portrait layouts.
- Reject orphan grid cells, unequal hit areas, and false navigation targets
  exposed by empty grid areas.
- Active-state styling must not erase required separators. Prefer accent borders
  that preserve row/column dividers rather than clearing them.
- Assert layout from computed grid placement, bounding boxes, and element-from-point
  probes at every required viewport in both themes.

## Canonical Display Format Propagation

- Operational plan gas labels must use one canonical formatter for schedule rows,
  banner pills, graph labels, contingency output, and text/slate/PDF exports.
- Air → `Air`, 100% oxygen → `100%`, every other mix → zero-padded `OO/HH`.
- Do not rename internal values such as `ean50`; educational copy may keep EAN
  terminology.
- Engine adapter/build-source code must not shadow or bypass the canonical
  formatter. Generated bundles must be rebuilt from canonical sources; never patch
  only the generated artifact.
- Regressions must reject `EAN50`, `EAN 50`, `EAN80`, percentage notation, and
  unpadded single-digit O2 such as `8/70`.

## Duplicate Navigation Surfaces

- Reject a second navigation bar or fixed footer control row when the same routes
  are already reachable through the main mode row and global header.
- Flag multiple state owners for one route (`setNavMode`, bottom-nav active
  writers, and main-nav highlight must not diverge).
- After removing a duplicate surface, assert the markup, CSS selectors, and
  JavaScript ID writers are deleted—not merely hidden.
- Verify mobile portrait and landscape retain canonical navigation, safe-area
  padding without reserved dead height, and no orphan spacing at the viewport
  bottom.

## Safety-Critical Copy

- Treat absolute words such as "safe", "always", and "never" as behavioral claims.
- Trace advice to oxygen exposure, gas reserve, decompression obligation, and recalculation requirements.
- Verify unit-sensitive values and examples in both unit systems.

## Closure Checklist

- Every HIGH/MEDIUM finding has pre-fix failure, post-fix observable success, stable regression IDs, and state-restoration evidence.
- Every evidence row has a schema-v4 receipt emitted by
  `tools/seven_lens_evidence.py`; hand-written exit codes and cleanliness flags
  are not evidence.
- Evidence commands ran at the verified source commit and left a clean worktree.
- Static, CI, release, browser, and engine gates report the same source commit.
- The manual ledger, cycle record, audit registry, and report contain the same units, findings, status, and commit.
- No prior finding disappeared, weakened severity, or became closed without this cycle's evidence.

## Prompting Cursor

Tell Cursor to read this playbook, the workflow, the protocol record, and the target source before reviewing. Require it to quote the exact entry event and final consumer for every L2/L4/L7 conclusion. A conclusion without a concrete consumer path is `INCOMPLETE`, not `NO_FINDING`.

Model memory or private internal training data cannot be shared between tools. This repository playbook, accumulated findings, trace fixtures, and executable gates are the durable and auditable way to transfer review behavior.
