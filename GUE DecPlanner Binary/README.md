# GUE DecPlanner 4 — Binary Artifacts

**App:** GUE DecPlanner 4  
**Package:** `cloud.udive.app`  
**Version:** 1.4.2 (December 2024)  
**Architecture:** Capacitor (Ionic) web app — **zero native `.so` files**

---

## Files in This Directory

### APK
| File | Size | Notes |
|---|---|---|
| `DecoPlannerMobile_1.4.2.apk` | ~19 MB | Original APK from APKPure CDN |

### Minified JavaScript Bundles (from `assets/public/build/`)
| File | Size | Contents |
|---|---|---|
| `p-b31951de.js` | 3.4 MB | **Main engine bundle** — contains VPM-B engine (`tC`), ZHL-16 engine (`QI`), tissue compartment (`qI`), GF controller (`WI`), preferences (`NI`), pSCR model (`ZI`) |
| `p-0246f3f7.entry.js` | 3.6 MB | UI components — dive plan display, gas tables, settings UI |

### Beautified JavaScript (extracted + formatted)
| File | Lines | Class | Description |
|---|---|---|---|
| `extracted_js/tC_VPM_engine_pretty.js` | 2,585 | `tC` | **VPM-B primary engine** — full decompression calculation, OC/CCR/pSCR, repetitive dives, altitude |
| `extracted_js/QI_Buhlmann_engine_pretty.js` | 1,089 | `QI` | **ZHL-16B/C engine** — gradient factor Bühlmann, tissue tracking, OxTox |
| `extracted_js/NI_Preferences_pretty.js` | 379 | `NI` | Default preferences — GF defaults (20/85), units, rates, limits |

### JADX Decompilation
| File | Contents |
|---|---|
| `jadx_out_gue_capacitor.zip` | Decompiled Java: `cloud.udive.app.MainActivity` (trivial — just `extends BridgeActivity`), Capacitor plugin classes, Firebase shell |

---

## How to Read the Engine

Start with the beautified files in `extracted_js/`. The entry point for any dive calculation is:

```javascript
const engine = new tC();
engine.runVPM(missionData, isBailout);  // returns bool
// Results in: engine.outputProfileDepth[], outputProfileTime[], etc.
```

**Key classes in `p-b31951de.js`:**
- `tC` — top-level VPM-B engine (offset 820,925 in minified file)
- `QI` — ZHL-16B/C Bühlmann engine (offset 803,714)
- `qI` — single tissue compartment with `setCompartmentTimeConstants(index, tHe, tN2, aN2, bN2, aHe, bHe)`
- `WI` — gradient factor controller (linear GF slope from first stop to surface)
- `NI` — all default preferences and unit conversions
- `ZI` — pSCR oxygen partial pressure model

---

## Key Technical Facts

- **No native code** — the entire deco engine is JavaScript, directly readable
- VPM-B constants identical to canonical Baker 1998 reference implementation
- ZHL-16C He `a` table matches MultiDeco, Subsurface, and Abysner exactly
- Default model: **ZHL-16B**, switchable to ZHL-16C
- Default GF: **20/85** (OC), **90/90** (bailout)
- Firebase SDK present for license validation (gates UI, not engine)

See `Knowledge Base/GUE_DecPlanner_Analysis.md` for full technical analysis.
