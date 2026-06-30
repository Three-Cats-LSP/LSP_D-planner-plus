## Cursor implementation checklist — Issue #140 (Audit #134, Audit v2)

**Cursor: implement all 8 findings. Each fix needs a stable emitted case ID in Audit v2.**

### HIGH
- [x] H-1: Surface interval — independent dive/surface gases, He carry, GF High at surface, cap handling
- [x] H-2: Gas plan pooled `maxTurnBar` proportional to bottom cylinder share
- [x] H-3: Audit v2 runner validates structured case IDs from suite JSON output

### MEDIUM
- [x] M-1: Service worker cache writes tied to `event.waitUntil()`
- [x] M-2: Release profile compiles/validates Android Java/Gradle/XML
- [x] M-3: `SUITE-COVERAGE` includes `tools.audit.test_system`
- [x] M-4: Restrict Android FileProvider paths

### LOW
- [x] L-1: Workspace drift uses content hashes for initially-dirty files

### Validation
```bash
python -m tools.audit run --profile release
python tools/audit_coverage.py --check
```
