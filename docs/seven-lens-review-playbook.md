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
- Include adverse paths: invalid input, minimum, maximum, mode transition, repeated action, and navigation away/back.

## Safety-Critical Copy

- Treat absolute words such as "safe", "always", and "never" as behavioral claims.
- Trace advice to oxygen exposure, gas reserve, decompression obligation, and recalculation requirements.
- Verify unit-sensitive values and examples in both unit systems.

## Closure Checklist

- Every HIGH/MEDIUM finding has pre-fix failure, post-fix observable success, stable regression IDs, and state-restoration evidence.
- Evidence commands ran at the verified source commit and left a clean worktree.
- Static, CI, release, browser, and engine gates report the same source commit.
- The manual ledger, cycle record, audit registry, and report contain the same units, findings, status, and commit.
- No prior finding disappeared, weakened severity, or became closed without this cycle's evidence.

## Prompting Cursor

Tell Cursor to read this playbook, the workflow, the protocol record, and the target source before reviewing. Require it to quote the exact entry event and final consumer for every L2/L4/L7 conclusion. A conclusion without a concrete consumer path is `INCOMPLETE`, not `NO_FINDING`.

Model memory or private internal training data cannot be shared between tools. This repository playbook, accumulated findings, trace fixtures, and executable gates are the durable and auditable way to transfer review behavior.
