# Audit Architecture v2

The audit platform is a registry-driven gate for source structure, generated parity,
regression evidence, findings, and review coverage. `docs/audit-units.json` is the
machine-readable source of truth.

## Commands

```text
python -m tools.audit check --profile static
python -m tools.audit run --profile ci
python -m tools.audit run --profile release
python -m tools.audit refresh --unit <ID>
python -m tools.audit legacy
```

The root `audit.py` remains a compatibility launcher for the static profile.
`dev/run_all_regression.py` remains a compatibility launcher for CI and release profiles.

## Profiles

- `static` validates the registry, fingerprints, migration ledger, JavaScript/HTML/CSS
  parsing, bundle parity, generated Pages shell, and the frozen legacy baseline.
- `ci` adds export, malformed-input, and complete engine regression evidence.
- `release` adds CCR validation, browser regression, pSCR E2E, CCR differential,
  and native bridge evidence.

Evidence commands are leaf suites. Recursive calls to the audit CLI, root compatibility
launcher, or old regression umbrella are rejected by schema validation. Identical commands
are executed once and their result is shared by all dependent evidence cases.

## Verification Semantics

A declared `VERIFIED` unit is effective only when its fingerprint is current and every
required evidence suite executed successfully in the current profile. Failed evidence
downgrades dependent units and invalidates dependent closed findings in the report.
Static runs show release-only evidence as not executed and never claim a full release pass.

Reports are written to ignored `dev/audit-results.json` and `dev/audit-report.md` files.
Exit code 0 means pass, 1 means an audit/evidence failure, and 2 means configuration or
tooling failure.

## Legacy Cutover

The frozen implementation lives at `tools/audit/legacy_v1.py`. Its assertion sites are
tracked in `docs/audit-legacy-migration.json`. A site counts as independently replaced only
after it points to a parser-backed rule or behavioral leaf-suite case that does not depend
on the legacy audit itself.

The legacy gate remains blocking until every site is independently replaced and three
consecutive clean main-branch release runs are recorded. Only then may the compatibility
launcher stop running the legacy suite by default.
