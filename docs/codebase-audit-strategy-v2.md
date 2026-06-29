# Codebase Audit Strategy v3.0

The v2 handwritten coverage model was replaced after commit `fd80511` exposed inconsistent totals, stale line ranges, overlapping units, and unverifiable regression counts.

## Authoritative data

- `docs/audit-units.json` is the only editable source of audit units, statuses, findings, evidence IDs, exclusions, and cycle assignments.
- `docs/audit-coverage.md` and `docs/audit-master-plan.md` are generated views. Do not edit them manually.
- `tools/audit_coverage.py` validates the registry and regenerates both views.

## Unit rules

Every tracked source file must be one of:

1. A registered whole-file audit unit.
2. A marker-partitioned source whose first marker is on line 1 and whose ordered spans cover the complete file without overlap.
3. A generated artifact with a named generator and verification command.
4. An excluded reference or test-data artifact with a documented reason.

The only valid statuses are `UNREAD`, `IN_PROGRESS`, `READ`, and `VERIFIED`. Partial work is `IN_PROGRESS`, never `READ partial`. `VERIFIED` requires a current content fingerprint, review or issue reference, evidence command, and stable regression case ID.

## Audit cycle

1. Run `python tools/audit_coverage.py --check` and the baseline audit before reading code.
2. Select the cycle's P0/P1 application units from the generated master plan. Read no more than 600 new application-source lines in one cycle, plus the listed engine re-verification unit.
3. Read every selected unit in full and apply the seven lenses: arithmetic/physics, control flow, state/mutation, API contracts, generated parity, safety regression, and tooling/CI.
4. Record actual findings only. Each finding needs a unit ID, exact lines, severity, issue link, status, and regression evidence where applicable.
5. Open CRITICAL or HIGH findings block release through the coverage gate.
6. After fixes, re-read the complete affected units, run their evidence commands, refresh fingerprints, and regenerate the Markdown views.

## Commands

```text
python -m unittest tools/test_audit_coverage.py
python tools/audit_coverage.py --refresh-fingerprints --write-docs
python tools/audit_coverage.py --check
python tools/check_engine_parity.py
python audit.py
python dev/run_all_regression.py --tier release
```

Refreshing a changed `READ` or `VERIFIED` unit automatically downgrades it to `IN_PROGRESS` and clears its evidence. Reviewers must explicitly restore the stronger status only after re-reading and rerunning the declared evidence.
