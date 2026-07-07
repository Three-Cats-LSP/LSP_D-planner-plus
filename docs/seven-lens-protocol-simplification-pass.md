# Seven-Lens Protocol Simplification Pass

Date: 2026-07-07

## Summary

Seven-Lens found real defects, especially in layout, gas labeling, navigation state, and responsive behavior. The review method is valuable. The closure machinery became too expensive.

Cycle 8 exposed the failure mode clearly: the team spent more time reconciling mirrored records, receipt hashes, historical migrations, static/CI special cases, and closure metadata than fixing the app. A small post-merge UI color/layout fix then took hours because the protocol repeatedly reinterpreted old cycles.

This pass separates the useful audit rigor from the bureaucracy. It is an infrastructure cleanup task, not Cycle 9. Cycle 9 should not start until the simplified operating rules below are treated as authoritative for new cycles.

## What Was Done

1. Declared completed cycles as frozen reviewed history.

   Completed cycle records are evidence of what was reviewed at that time. New protocol rules must not retroactively fail completed cycles unless there is an explicit source invalidation touching the reviewed unit.

2. Defined one authoritative cycle record.

   New cycles should use one canonical record under `docs/seven-lens-records/`. Prose reports may summarize that record, but they must not be a second source of truth. Mirrored JSON records under both `docs/seven-lens-records/` and `docs/seven-lens-reports/` created avoidable drift and should be phased out.

3. Defined a single ready-to-close gate.

   Closure should not discover missing evidence. Before CLOSER starts, VERIFIER must run one command:

   ```text
   python tools/seven_lens_ready_to_close.py --cycle <N>
   ```

   Until that command exists, the operational equivalent is:

   ```text
   python tools/seven_lens_protocol.py check-all --require-artifacts
   python -m tools.audit check --profile static
   python -m tools.audit run --profile ci
   ```

   CLOSER should only proceed when the ready-to-close gate is already green.

4. Simplified closure responsibility.

   CLOSER should only:

   - Flip verified findings from `OPEN` to `CLOSED`.
   - Set resolution commits already proven by VERIFIER.
   - Promote the ledger entry to `SEVEN_LENS_REVIEWED`.
   - Open or merge the PR after CI is green.

   CLOSER must not debug missing evidence, regenerate traces, reinterpret old cycles, or repair protocol rules.

5. Normalized the evidence model.

   All evidence should be treated the same way: command, commit, exit code, artifact path, artifact hash, case IDs, and clean-worktree result. Static, CI, release, browser trace, and regression receipts should not have separate closure semantics. If special evidence handling is needed, it should happen before ready-to-close.

6. Moved blocker detection earlier.

   Missing receipts, stale hashes, trace artifact drift, dirty worktrees, stale reviewed fingerprints, and source/test changes after verification are VERIFIER failures. They must not be discovered for the first time during CLOSER.

7. Stopped mid-cycle protocol mutation as normal practice.

   Protocol changes during a cycle caused historical evidence to become invalid while the team was trying to close unrelated app fixes. Future protocol changes must be versioned and handled as infrastructure tasks with explicit migration notes.

8. Preserved completed-cycle results.

   Existing Cycle 1-8 results remain valid historical review records. This pass does not discard their findings, fixes, or evidence. It changes how future workflow should treat them.

## Why It Was Needed

The protocol had accumulated too many responsibilities:

- It was both a review checklist and a closure validator.
- It had two record locations that could diverge.
- It treated static, CI, trace, and receipt evidence as separate legal categories.
- It revalidated old cycles whenever new protocol rules changed.
- It made CLOSER responsible for discovering and repairing evidence problems.
- It allowed protocol fixes to be patched mid-cycle, which created new blockers while trying to close old ones.

The result was expensive and frustrating:

- Small app fixes triggered large metadata cascades.
- Old cycles were repeatedly pulled back into validation.
- Cursor/Codex spent time fighting hashes and mirrors instead of testing user-visible behavior.
- The process consumed time, tokens, and money without proportional safety gain.

The audit system should protect the app, not become the app's main development bottleneck.

## New Workflow Effect

### For Future Cycles

Future cycles should use this order:

1. **AUDITOR**

   Reads the bounded unit scope and files findings. No app fixes.

2. **FIXER**

   Fixes findings and adds regressions. No closure.

3. **VERIFIER**

   Independently reruns behavior, traces, evidence, and gates. VERIFIER must leave the cycle in a ready-to-close state.

4. **READY-TO-CLOSE**

   A single pre-closure gate confirms:

   - One canonical cycle record is valid.
   - Evidence exists and is bound to the verified source commit.
   - Static and CI profiles pass.
   - Trace artifacts match the trace specs.
   - Reviewed fingerprints are current or explicitly invalidated.
   - Historical frozen cycles are not being reinterpreted.

5. **CLOSER**

   Performs metadata-only closure and merge bookkeeping. No investigation.

### For Historical Cycles

Historical cycles should be treated as frozen snapshots.

Allowed checks:

- The reviewed source fingerprint still matches, or a later cycle explicitly records a dependency re-review.
- A finding that is marked closed still has its original resolution evidence.
- The cycle record file is not malformed.

Disallowed checks:

- Applying new closure rules to old cycles.
- Requiring old evidence to be re-run because protocol code changed.
- Requiring old records to gain new fields unless a migration is explicitly versioned and non-blocking.
- Blocking a new app fix because an old record uses an older valid schema.

### For Protocol Changes

Protocol changes must be rare and versioned.

Every protocol change should declare:

- Protocol version.
- New rule.
- Whether it applies only to new cycles or also to historical cycles.
- Migration behavior.
- Whether migration is blocking or informational.

Default rule: new protocol rules apply only to new cycles.

### For Evidence

Evidence should become a uniform object:

```json
{
  "id": "ER-CXX-NAME",
  "command": ["python", "dev/suite.py"],
  "commit": "<verified-source-or-closure-commit>",
  "exit_code": 0,
  "case_ids": ["CASE-ID"],
  "artifacts": [
    {
      "path": "dev/artifact.json",
      "sha256": "<hash>"
    }
  ],
  "worktree_clean": true
}
```

No special static/CI/release/trace branches should be needed at closure time.

### For CLOSER

CLOSER should be boring.

If CLOSER discovers missing evidence, stale hashes, red gates, or source drift, the workflow already failed earlier. CLOSER should stop and return the cycle to VERIFIER/FIXER. It should not repair the issue.

## Recommended Implementation Queue

1. Add `tools/seven_lens_ready_to_close.py`.

   This command should collect all existing required checks and print one concise blocker list before CLOSER starts.

2. Deprecate mirrored cycle records.

   Keep existing mirrors for history, but do not create new JSON mirrors. New cycles should have one authoritative record in `docs/seven-lens-records/`.

3. Add a frozen-cycle manifest.

   Example:

   ```json
   {
     "frozen_cycles": [
       {
         "cycle": 8,
         "record": "docs/seven-lens-records/cycle-08-shell-results.json",
         "schema_version": 5,
         "reviewed_commit": "<commit>",
         "frozen_at": "<commit>"
       }
     ]
   }
   ```

4. Make historical-cycle validation shallow.

   For frozen cycles, validate existence and basic integrity only. Do not apply new active-cycle closure rules.

5. Collapse evidence validators.

   Replace special static/CI/release/trace close paths with one evidence validator.

6. Rewrite CLOSER prompts.

   CLOSER prompt should say: run ready-to-close; if green, flip status/promote ledger/merge. If red, stop.

7. Update Cursor workflow.

   Cursor should not attempt closure repair. Missing evidence means VERIFIER failed.

## Expected Result

The audit will remain strict where it matters:

- Real browser behavior.
- Safety warnings.
- Engine and gas calculations.
- Cross-unit visual contracts.
- Regressions with stable case IDs.
- CI and release gates.

But it will stop wasting time on:

- Mirrored record drift.
- Rebinding old evidence after every protocol tweak.
- Reopening old cycles because a new rule exists.
- CLOSER debugging evidence.
- Mid-cycle protocol surgery.

The practical effect: future cycles should focus again on the app, not on repeatedly proving that old paperwork still satisfies new paperwork.

