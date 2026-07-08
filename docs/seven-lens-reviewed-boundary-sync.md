# Seven-Lens Reviewed Boundary Sync

## What Was Added

`tools/seven_lens_protocol.py` now has a focused maintenance command:

```text
python tools/seven_lens_protocol.py sync-reviewed-boundaries --write
```

It repairs reviewed-cycle record drift after source edits move line boundaries but do not require a new semantic review.

## Why

CSS and shared runtime files move often during UI work. A valid app fix can make old reviewed-cycle records fail `check-all` with stale `start_line`, `end_line`, `line_count`, or `content_fingerprint` fields. Previously this required manual JSON edits and made the simplified workflow feel bureaucratic again.

The new command moves that work into a narrow protocol step.

## Safety Rules

- It only touches reviewed-cycle record part metadata:
  - `id`
  - `path`
  - `start_line`
  - `end_line`
  - `line_count`
  - `content_fingerprint`
- It regenerates boundaries from the current audit registry.
- It preserves review notes, verifier notes, findings, evidence, ledger state, and application source.
- If the current unit split would require more or fewer reviewed parts than the record already has, it stops and reports that re-review is required.
- It does not close findings, promote ledger rows, or reinterpret old cycles.

## Workflow

When `check-all` reports reviewed-cycle boundary drift:

```text
python tools/seven_lens_protocol.py sync-reviewed-boundaries --write
python tools/audit_coverage.py --write-docs
python tools/seven_lens_protocol.py check-all --require-artifacts
```

If the sync command blocks with `re-review required`, run a bounded re-review for that unit instead of forcing metadata.

## Effect From Now On

Future app changes can keep moving quickly:

- normal app regressions still get fixed in the app;
- simple reviewed-boundary drift is repaired mechanically;
- larger drift that changes review coverage remains visible and requires real review.

