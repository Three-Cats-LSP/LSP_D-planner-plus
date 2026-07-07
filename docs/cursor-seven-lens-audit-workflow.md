# Cursor Seven-Lens Audit Workflow

This workflow is for Cursor using GPT-5.5 Medium. It performs the manual review
that automated V3 gates cannot provide. The target integration branch is `dev`.
Do not target or modify `main`.

Use the role-separated prompts in `docs/cursor-seven-lens-prompts.md`. Generate
and validate each structured cycle record with `tools/seven_lens_protocol.py`;
prose reports do not replace the protocol gate.

Read `docs/seven-lens-review-playbook.md` before every phase. It is the shared
review knowledge base for recurring failure patterns and evidence standards.

Before starting any cycle after Cycle 8, read
`docs/seven-lens-protocol-simplification-pass.md`. It freezes completed cycles as
reviewed history and makes ready-to-close validation a VERIFIER responsibility.
CLOSER must not discover or repair evidence problems; if closure blockers appear,
return the cycle to VERIFIER/FIXER instead of patching protocol rules mid-cycle.

## Core Rule

Passing static checks, regressions, parity checks, or release suites is automated
evidence. It is not proof that a source unit has received a seven-lens review.

The existing V3 `VERIFIED` status records automated evidence. Until a separate
manual-review ledger is introduced, treat every unit as manually unreviewed unless
a seven-lens cycle report names the unit, its reviewed fingerprint, all seven lens
results, and the reviewing model/session.

## Branch Policy

1. Fetch GitHub and start from the current `origin/dev`.
2. Create one branch per audit cycle, for example
   `cursor/seven-lens-cycle-01-header`.
3. Open pull requests against `dev`, never `main`.
4. Keep audit reports, fixes, tests, and metadata for one cycle in the same PR.
5. Never force-push or rewrite `dev` history.
6. Run `plan` before making any branch commit. The planner refuses a dirty
   worktree or a `HEAD` that differs from `origin/dev`.
7. Never delete, downgrade, or rewrite an unresolved finding or prior-cycle
   record to make a gate pass. Resolve it through its owning cycle and evidence.

Suggested setup:

```text
git fetch origin
git switch dev
git pull --ff-only origin dev
git switch -c cursor/seven-lens-cycle-XX-short-scope
```

## Canonical Sources

Review and edit canonical sources only:

- Runtime cores: `*-core.js`, `planner-shell.js`, `results-panel.js`
- CSS: `lsp-dplanner-*.css`
- Markup: `ui/markup-*.html`
- Engines: canonical ZHL/VPM source modules
- Shell/orchestration: the registered `index.html` unit boundaries

Do not patch generated bundles, `_pages/`, `www/`, APKs, ZIPs, or assembled
copies. Regenerate them through repository tools and verify parity.

## Seven Lenses

Apply every lens to every selected unit. Write an explicit result even when no
finding is discovered.

### L1: Arithmetic And Physics

- Check units, conversions, pressure/depth formulas, rounding direction, limits,
  interpolation, accumulated time, tissue loading, gas volume, CNS, and OTU.
- Test zero, boundary, near-boundary, maximum, invalid, metric, and imperial cases.
- For safety quantities, confirm rounding is conservative and comparisons use
  unrounded values.

### L2: Control Flow

- Trace every entry, return, exception, asynchronous callback, worker response,
  timeout, retry, and cancellation path.
- Check stale-result guards, generation IDs, early returns, fallback paths, and
  cleanup in `finally` blocks.
- Confirm an error cannot silently continue with partial or old results.

### L3: State And Mutation

- List every DOM field, module variable, `window` property, cache, storage key,
  worker state, and object reference read or written.
- Check aliasing, shallow copies, save/restore completeness, re-entrancy, races,
  cross-plan contamination, and state left behind after failures.
- Confirm headless, contingency, export, and test runs cannot mutate interactive UI.

### L4: API Contracts

- Compare callers and callees for argument order, units, optional fields, nullability,
  return shape, error shape, ownership, and synchronous/asynchronous behavior.
- Check extracted modules, globals, workers, native bridges, and generated bundles.
- Reject compatibility based only on matching function names.

### L5: Canonical And Generated Parity

- Confirm canonical sources reproduce all generated artifacts exactly.
- Check script/style order, exported globals, service-worker assets, Pages assets,
  Capacitor assets, worker bundles, and offline manifests.
- Never repair parity by editing the generated side.

### L6: Safety Regression

- Compare behavior with known-good fixtures, engine goldens, and prior bug cases.
- Check whether invalid input fails closed and whether warnings remain visible.
- Treat misleading safety guidance, plausible output from invalid input, or lost
  warnings as defects even when calculations later reject the plan.

### L7: Tooling And CI

- Verify tests exercise behavior rather than source strings alone.
- Check that gates cannot bless stale fingerprints, skip suites, recursively invoke
  themselves, or claim evidence that was not executed.
- Confirm CI, Pages, APK, offline ZIP, and local commands use equivalent sources.

## Mandatory Cross-Unit Visual Contract Gate

Every cycle that reads or changes markup, CSS, rendering, navigation, or a
canonical DOM writer must validate the assembled application as a whole. A
selector-level or source-string assertion is not sufficient.

- Exercise dark and light themes at 1280x800, 1024x768, 768x720, 667x600,
  375x667, and 667x375 when the affected surface exists at those sizes.
- Assert layout relationships from bounding boxes: required columns, ordering,
  containment, visibility, and absence of overlap or unused collapsed columns.
- Compare computed colors to semantic design tokens. Related graph, legend,
  card, banner, and table roles must resolve to the same token where the design
  contract says they are equivalent.
- Assert exact user-facing labels and punctuation when wording identifies a
  safety role, gas role, unit, algorithm, or state.
- Trace both static markup and every canonical writer that can replace its text,
  classes, inline styles, or children. Fail on duplicated decoration produced by
  markup plus a legacy writer.
- Generate the real result through visible controls before inspecting output.
  Injecting fixture markup or changing a hidden compatibility select cannot
  prove the visible contract.
- Capture full-surface screenshots before and after UI fixes. Screenshot review
  supplements computed assertions; it never replaces them.
- Run `SUITE-UI-VISUAL-CONTRACT-REGRESSION` after every UI/CSS/rendering fix.
  Any failure invalidates verification even when the cycle's focused suite is
  green.
- For responsive main-navigation grids with an odd item count, assert every
  viewport fills intentional complete rows: no orphan cells, no dead hit areas,
  visible separators including Tools→Settings, and preserved desktop five-column
  parity above the tablet breakpoint.
- For operational gas labels, trace the canonical formatter through engine
  adapters, generated bundles, schedule renderers, graph labels, contingency
  output, and exports. Reject adapter special-cases such as `EAN50`/`EAN80` that
  bypass zero-padded `OO/HH` notation.
- Reject duplicate navigation surfaces that expose the same routes through both
  the main mode row and a fixed mobile footer bar. Removing a duplicate bar must
  delete markup, CSS, and JavaScript writers—not merely hide them with
  `display:none`.

## Cycle Scope

1. Read `docs/audit-master-plan.md` and `docs/audit-units.json`.
2. Select the next units in priority order: P0, then P1, P2, and P3.
3. Limit each manual review or verification session to at most 600 new
   application-source lines. Do not combine several documented parts into a
   single session when their combined boundary exceeds this limit.
4. Split any larger unit into stable marker or function boundaries and document
   the split. Track review and verification separately for every part. Do not
   claim the whole unit was reviewed until every part has been verified against
   the final source fingerprint.
5. Add at most one bounded engine re-verification scope to a UI cycle.
6. Read the complete selected boundary plus direct callers and callees needed to
   validate contracts. Dependency context does not count as reviewed coverage.

The existing 41-cycle V3 schedule contains several scopes above 600 lines. Split
those scopes for manual work instead of closing them in one session.

## Phase A: Baseline

Run before reading or editing:

```text
python tools/seven_lens_protocol.py plan --cycle <N> --output docs/seven-lens-reports/cycle-<NN>-record.json
python -m tools.audit check --profile static
git status --short
```

Run the release profile at the start of a new audit epoch and after high-risk fixes:

```text
python -m tools.audit run --profile release
```

Record the branch, exact commit SHA, commands, results, and worktree state.

The schema-v2 plan snapshots the integration commit, registry fingerprint, and
all historical findings. Audit, verify, and close reject deleted findings,
severity downgrades, unsupported closures, prior-cycle record edits, or a cycle
that was planned after work had already begun.

Do not run fingerprint refresh before the baseline staleness check. A tool that
refreshes fingerprints before checking them can hide unreviewed source changes.

## Phase B: Audit Pass

The audit pass is read-only. Do not fix code while discovering findings.

For each unit:

1. Read the entire declared boundary.
2. Identify inputs, outputs, state, side effects, globals, and dependencies.
3. Trace normal, boundary, invalid, failure, repeated, and concurrent paths.
4. Apply L1 through L7 separately.
5. Run focused probes when behavior cannot be established from source.
6. Record findings without changing application code.

Do not use expected-finding quotas. Zero findings is acceptable only after all
seven lens notes are complete.

Commit the completed read-only audit report before Phase C begins. Record that
commit as `audit_commit` in the cycle report. This checkpoint must contain no
application fix for a finding first documented by the same audit pass.

## Finding Format

Use stable IDs: `SL-C<cycle>-<severity>-<number>`.

```text
### SL-C01-H-01: Short title

- Severity: CRITICAL | HIGH | MEDIUM | LOW
- Lens: L1-L7
- Unit: registry unit ID
- Location: canonical/path.js:line
- Root cause: precise technical cause
- Failure path: concrete inputs and execution sequence
- Impact: user, engine, UI, deployment, or audit consequence
- Evidence: source trace, runtime probe, or failing regression
- Recommendation: required behavior, without unrelated refactoring
- Regression ID: proposed stable case ID
- Status: OPEN
```

Record findings in the V3 findings registry and in a cycle Markdown report. Do not
mark a finding closed in the audit pass.

## Phase C: Fix Pass

Start only after the audit report is complete.

1. Fix canonical sources only.
2. Keep each change tied to a recorded finding.
3. Add a behavioral regression that fails before the fix and passes afterward.
4. Use stable evidence IDs and register them in the actual leaf suite.
5. Regenerate bundles and assembled artifacts through repository tools.
6. Avoid unrelated refactors and formatting churn.
7. For UI changes, update or add cross-unit visual contracts before changing
   production styling. Preserve the failing pre-fix capture and passing final
   capture at the same themes and viewports.

Behavioral regressions must exercise the public or user event path that failed;
calling the repaired helper directly is insufficient when event wiring is part of
the contract. Every regression must restore all DOM values, globals, storage,
workers, timers, and generated state it changes in a `finally` block. A finding
that names several entry paths must have evidence for every named path.

For every MEDIUM/HIGH/CRITICAL finding, record a failing run on the pre-fix
commit and a passing run on the fix commit. Assertions must inspect an observable
schedule, rendered value, validation result, persisted value, or API result. A
test that only checks an internal flag, helper existence, or source string is not
behavioral evidence. Record a separate before/after state snapshot proving the
test leaves DOM, globals, storage, and workers unchanged.

For UI, unit, state, and engine-consumer findings, add a declarative browser trace
under `docs/seven-lens-traces/` and run:

```text
python tools/seven_lens_browser_trace.py --spec <trace-spec>
```

Each trace must capture all four stages: user/API input, canonical physical value,
the value received by the consumer, and the observable output. Do not use equal
rounded labels as proof of physical equivalence. The trace must also hash bounded
DOM/global/storage snapshots before and after cleanup; the hashes must match.
Tested actions must be visible, enabled, and unforced. Run each trace at least
twice in fresh browser contexts; reject non-finite captures and console/page
errors.
`run_script` and `set_global` are setup-only and require a setup reason; they may
never perform the user action being tested.

For unit-sensitive controls, review the complete physical tuple: value, label,
minimum, maximum, step, default, persistence, and both conversion directions.
Test a non-default value and each boundary, then require metric -> imperial ->
metric and imperial -> metric -> imperial round trips to preserve physical state.
Every such control must also execute switch -> user edit -> final consumer ->
roundtrip. Unit-switch-only evidence is incomplete.

Cursor may perform up to three fix attempts. After each attempt, return to the
verification phase. Do not repeatedly edit without a fresh failure explanation.

## Phase D: Independent Verification

Use a fresh Cursor chat or a distinct reviewer context. This is mandatory for an
independent-verification claim. The verifier must not rely on the fix author's
explanation and must start from the committed audit report and source.

1. Re-read every changed line and the complete affected unit.
2. Reproduce the original failure input.
3. Confirm the new regression would detect the old defect.
4. Reapply all seven lenses to changed behavior and adjacent paths.
5. Check canonical/generated parity.
6. Run the required profiles.
7. Record `verified_source_commit`, `verified_fingerprint`, verifier
   identity/session, and the exact evidence run IDs. The verified source commit
   must be the latest commit that changes reviewed application source, regression
   code, or generated artifacts.
8. Inspect browser-trace captures, not only their pass/fail result. Confirm the
   consumer received the expected unrounded physical value and the state hashes
   are equal.

Any later change to reviewed application source, regression code, or generated
artifacts invalidates Phase D. Repeat verification at the new source commit before
merge. A later attestation-only commit may update cycle reports and ledger metadata
without creating a self-referential commit hash, provided its diff is limited to
those records. Automated review and CI evidence count only for the exact commit
they evaluated; required CI must still run on the final PR HEAD.

Minimum commands:

```text
python -m tools.audit check --profile static
python -m tools.audit run --profile ci
```

Use the release profile for engine, worker, PWA, export, native, shared-state,
high-severity, or cross-module changes:

```text
python -m tools.audit run --profile release
```

## Fingerprint Rule

Fingerprint refresh happens after review, fixes, and verification, never before the
initial staleness check.

After verification:

```text
python -m tools.audit refresh --unit <UNIT-ID>
python tools/audit_coverage.py --write-docs
python -m tools.audit check --profile static
```

The cycle report must store the reviewed fingerprint. A later fingerprint mismatch
invalidates manual review for that unit until it is re-read.

## Manual Review Ledger

Keep manual review separate from automated `VERIFIED` evidence. Each reviewed unit
must record:

```text
unit_id
review_status: UNREVIEWED | IN_PROGRESS | SEVEN_LENS_REVIEWED
reviewed_fingerprint
cycle_id
reviewer: Cursor GPT-5.5 Medium
review_session
parts: boundary, reviewed_fingerprint, review_session, verification_session
lens_results: L1 through L7
finding_ids
verification_commands
audit_commit
verified_source_commit
verification_status: PENDING | PASSED | BLOCKED
reviewed_at
```

Automated scripts must not create `SEVEN_LENS_REVIEWED` entries. Only a completed
manual report may do so.

## Cycle Closure

A cycle closes only when all conditions are true:

- Every scoped boundary was read completely.
- L1-L7 each have explicit notes.
- Every finding is closed or the cycle remains blocked.
- Required regressions pass.
- Static and required runtime profiles pass.
- Fingerprints match the reviewed source.
- Every split part has final-fingerprint verification from a session within the
  600-line limit.
- Generated artifacts reproduce from canonical sources.
- No open CRITICAL or HIGH finding remains.
- The tracked worktree is clean after all commands.
- A PR targeting `dev` contains the report, fixes, tests, and metadata.
- `verified_source_commit` is the latest commit touching reviewed source, tests,
  or generated artifacts; all required CI runs evaluated the final PR HEAD; and
  the PR title/body accurately describe its final scope.
- `python tools/seven_lens_protocol.py check --phase close --record <record>`
  exits 0.
- `python tools/seven_lens_protocol.py check-all --require-artifacts` exits 0;
  all previously reviewed cycles remain valid.
- The record uses the current schema and every evidence row has a receipt made by
  `python tools/seven_lens_evidence.py`; closure scripts may not synthesize
  evidence results.
- Baseline-failure receipts run in a prepared clean detached worktree passed with
  `--execution-root`; the receipt commit must equal that worktree's HEAD.
- `docs/seven-lens-test-results.md` is updated with the cycle summary.
- The cycle PR is pushed and merged to `dev` after required CI passes on the final
  PR HEAD.

Never count repeated executions of the same commit as multiple consecutive clean
release runs. Each qualifying run must have a distinct GitHub Actions run ID and
must satisfy the repository's branch policy.

## Cursor Audit Prompt

```text
Act as a strict senior code auditor. Work only on the current cycle and do not fix
code during the audit pass. Read every scoped canonical source boundary completely.
Apply all seven lenses independently: arithmetic/physics, control flow,
state/mutation, API contracts, canonical/generated parity, safety regression, and
tooling/CI. Tests are evidence, not proof of manual review. For every finding,
provide a stable ID, severity, exact canonical file and line, root cause, concrete
failure path, impact, recommendation, and proposed regression ID. Record explicit
no-finding notes for each lens. Do not refresh fingerprints before checking
staleness. Do not modify main; target dev.
```

## Cursor Fix Prompt

```text
Implement only the recorded open findings for this seven-lens cycle. Edit canonical
sources only. Add behavioral regressions that fail on the old behavior. Regenerate
artifacts with repository tools. Do not weaken assertions or tolerances, do not
perform unrelated refactors, and do not close findings yet. Run targeted tests and
report each finding-to-test mapping.
```

## Cursor Verification Prompt

```text
Independently verify this cycle's fixes. Re-read each complete affected unit and
reapply all seven lenses. Reproduce each original failure, inspect each regression,
and check adjacent state/API/parity paths. Run static and CI profiles, plus release
for safety, engine, worker, PWA, export, native, or shared-state changes. Close a
finding only when source review and current evidence both pass. Refresh fingerprints
only after verification. Confirm the PR targets dev and the tracked worktree is
clean.
```
