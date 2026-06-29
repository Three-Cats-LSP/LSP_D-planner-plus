## Cursor implementation checklist — Issue #139 (Audit #133)

**Cursor: implement all 3 new findings. #138 re-verification (40/40) requires no code changes.**

### Re-verification (#138)
- [x] All 40 findings from #138 confirmed fixed on `1271d1a` (see GitHub #139 body)

### Phase 1 — LOW (3)
- [x] L-1: `ccrBottomSetpoint` / `ccrDecoSetpoint` `oninput` → append `appSettings.save(false)`
- [x] L-2: Safety stop row ppO₂ uses `pO2Val.toFixed(2)` (match deco/ascent rows)
- [x] L-3: `setCustomGF` writes swapped GF values back to both input fields

### Validation
```bash
python audit.py
python dev/engine_regression.py
python tools/audit_coverage.py --check
```
