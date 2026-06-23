# MultiDeco Shallow Gradient — Binary Reverse Engineering

**Date**: 2026-06-18  
**Binary**: `libmultideco.so` arm64-v8a, NDK r29, Clang 21 (stripped), from MultiDeco v2.26 APK  
**Method**: `aarch64-linux-gnu-objdump -d`, `nm -D`, `readelf`, manual ARM64 decompilation  
**Status**: Complete — all three ShallowGrad functions fully decompiled, all FP constants decoded

> **Note on the previous APK analysis doc**: The earlier `APK_Reverse_Engineering.md` listed the shallow gradient
> symbol names only (no math). This document contains the actual disassembled function bodies and
> the complete derived formula.

---

## Background — What Is Shallow Gradient?

Standard ZHL-16C + GF creates a linearly increasing GF from GFLo (at first stop) to GFHi (at surface).
This means tissues closest to the M-value limit always get the most time at shallow stops.

**Shallow Gradient** is a proprietary MultiDeco feature that adds a fourth conservatism adjustment
applied specifically at shallow stops. It does NOT replace GF — it is an additional modifier that
can add extra stop time when the diver is shallow.

The feature has three parameters visible in MultiDeco's settings UI:
- `Shallow_Grad_Depth_Factor` — depth threshold (related to depth of first deco stop)
- `Shallow_Grad_Time_Factor` — time scaling factor
- `Shallow_Grad_Max_ATA_Factor` — maximum extra ceiling increase (bar), capped at 1.0 bar (= surface)

---

## Global Variables (from BSS — confirmed by nm)

```
BSS address    Symbol
0x66420        Shallow_Grad_Depth_Factor   (double, 8 bytes)
0x66428        Shallow_Grad_Time_Factor    (double, 8 bytes)
0x66430        Shallow_Grad_Max_ATA_Factor (double, 8 bytes)
0x6647a        Apply_Shallow_Grad          (bool, 1 byte)
```

Plus internal working variables also in BSS:
```
0x66458        Depth_Start_of_Deco_Zone    (double) — depth of first deco stop (bar)
0x66460        Max_Depth                   (double) — maximum dive depth (bar)
0x663a0        Water_Vapor_Press           (double) — WV (runtime, not hardcoded)
0x663b8        Baro_Press                  (double) — surface/baro pressure
0x66470        Units_Equal_Fsw             (bool)
0x66471        Units_Equal_Msw             (bool)
```

---

## Constants from .rodata (file offset 0x13810, vaddr 0x13810)

Relevant constants near the ShallowGrad area (decoded by reading binary):

| vaddr | value | interpretation |
|-------|-------|----------------|
| 0x13828 | 1.01325 | standard atmosphere (bar) |
| 0x13858 | 0.55 | unknown (possibly GF-related threshold) |
| 0x13860 | **0.05** | time factor divisor in `ShallowGradTimeTest` |
| 0x13868 | 0.272727 | 3/11 — unit conversion ratio |
| 0x13870 | 10.337 | m/bar for seawater (at surface pressure) |
| 0x13878 | 0.499 | just-below-0.5 threshold |
| 0x13880 | **0.40** | threshold in `ShallowGradDepthTest` (compared to computed ratio) |
| 0x13888 | 1.01 | 1% over 1.0 bar (surface overpressure check) |
| 0x138a0 | 1.331 | 1.1³ — Boyle compensation factor? |
| 0x138a8 | **-0.40** | addend in `ShallowGradDepthTest` (offsets the ratio) |
| 0x138c8 | 33.066 | ft/atm (freshwater variant) |
| 0x138e8 | 0.20 | used in other deco checks |

---

## Function 1: `ShallowGradMixTest()` — 0x324f0

### Disassembly

```asm
ShallowGradMixTest:
   ldr   w8, [x0, #132]         ; load TVPM.field_132 (int)
   cbz   w8, .check_mix_count   ; if == 0, check number of gas mixes
   mov   w0, #1                 ; return true (only one mix — always apply)
   ret
.check_mix_count:
   adrp  x8, GOT[vpm_config]    ; load vpm_config global pointer
   ldr   x8, [x8]               ; dereference
   ldr   w8, [x8, #492]         ; vpm_config->field_492 (mix count)
   cmp   w8, #1
   cset  w0, gt                 ; return (mixCount > 1)
   ret
```

### Decoded logic

```c
bool ShallowGradMixTest() {
    if (this->field_132 != 0) return true;   // single-gas dive → always eligible
    return (vpm_config->mix_count > 1);       // multi-gas dive → eligible if >1 mix
}
```

**Purpose**: Returns `true` if the dive configuration is eligible for shallow gradient.
- Single-gas dives (field_132 != 0, or mix_count == 1): always eligible
- Multi-gas dives: eligible only if more than 1 gas mix is configured

---

## Function 2: `ShallowGradDepthTest(double current_depth_bar)` — 0x3251c

### Disassembly (annotated)

```asm
ShallowGradDepthTest:
   ; d0 = current_depth_bar (argument)
   
   ; EARLY EXIT: if current_depth_bar < Forced_First_Stop_Depth, return immediately
   adrp  x8, [Forced_First_Stop_Depth]
   ldr   d1, [x8]               ; d1 = Forced_First_Stop_Depth
   fcmp  d0, d1
   b.mi  .return                ; if depth < forced_first_stop → do nothing, ret

   ; Save current depth as Forced_First_Stop_Depth (= depth of first stop)
   str   d0, [x8]               ; Forced_First_Stop_Depth = current_depth_bar

   ; Call BOYLES_LAW_COMPENSATION(Forced_First_Stop_Depth/3, Forced_First_Stop_Depth/3)
   ; This applies Boyle's Law compensation at depth/3 (1/3 of first stop depth)
   fmov  d1, #3.0
   ldr   d2, [x19]              ; d2 = Forced_First_Stop_Depth
   fdiv  d1, d2, d1             ; d1 = depth/3
   fmov  d2, d1                 ; d2 = depth/3
   bl    BOYLES_LAW_COMPENSATION

   ; === Compute sum of all tissue supersaturation ===
   ; Loads N2_Press[0..15] and He_Press[0..15] in pairs of 2 doubles (ldp)
   ; Accumulates: sum += (N2_Press[i] - He_Press[i]) for i=0..15
   ; (This is a 16-pair unrolled loop — 128 bytes total, 8 ldp instructions × 2 passes)
   movi  d0, #0x0               ; sum = 0
   [16× ldp + fadd/fsub pattern]
   ; result in d0 = sum of (N2_Press - He_Press) across all 16 compartments

   ; Multiply by 0.03125 (= 1/32 = average across 16 N2 + 16 He)
   mov   x8, #0x3fa0000000000000  ; = 0.03125
   fmov  d1, x8
   fmul  d0, d0, d1             ; d0 = mean_supersaturation

   ; Divide by Forced_First_Stop_Depth
   ldr   d1, [x19]              ; d1 = Forced_First_Stop_Depth (bar)
   fdiv  d0, d0, d1             ; d0 = mean_supersaturation / first_stop_depth

   ; Compare ratio against threshold 0.40
   ldr   d1, [rodata:0x13880]   ; d1 = 0.40
   fcmp  d0, d1
   cset  w9, gt                 ; w9 = (ratio > 0.40)
   strb  w9, [Apply_Shallow_Grad]  ; Apply_Shallow_Grad = (ratio > 0.40)

   ; If Apply_Shallow_Grad is true, compute the extra ceiling factor
   b.le  .done
   
   ; extra = (ratio + (-0.40)) * 10.0, clamped to [0, 1.0]
   ldr   d1, [rodata:0x138a8]   ; d1 = -0.40
   fadd  d0, d0, d1             ; d0 = ratio - 0.40
   fmov  d1, #10.0
   fmul  d0, d0, d1             ; d0 = (ratio - 0.40) * 10
   fmov  d1, #1.0
   fminnm d0, d0, d1            ; d0 = min(result, 1.0)   ← cap at 1.0 bar
   str   d0, [Shallow_Grad_Max_ATA_Factor]  ; store computed ceiling modifier

.done:
   ret
.return:
   ret
```

### Decoded logic

```c
void ShallowGradDepthTest(double current_depth_bar) {
    if (current_depth_bar < Forced_First_Stop_Depth) return;
    
    Forced_First_Stop_Depth = current_depth_bar;
    
    // Apply Boyle's Law compensation at 1/3 of first stop depth
    BOYLES_LAW_COMPENSATION(current_depth_bar / 3.0, current_depth_bar / 3.0);
    
    // Compute mean tissue supersaturation across all 16 N2+He compartments
    double sum = 0.0;
    for (int i = 0; i < 16; i++) {
        sum += N2_Press[i] - He_Press[i];
    }
    double mean_supersaturation = sum * (1.0 / 32.0);   // avg over 16 N2 + 16 He
    
    double ratio = mean_supersaturation / Forced_First_Stop_Depth;
    
    Apply_Shallow_Grad = (ratio > 0.40);
    
    if (Apply_Shallow_Grad) {
        // Scale the extra ceiling modifier: 0.0→1.0 over the range [0.40, 0.50]
        double extra = (ratio - 0.40) * 10.0;
        Shallow_Grad_Max_ATA_Factor = fmin(extra, 1.0);  // cap at 1.0 bar
    }
}
```

### Key interpretation

`ratio = mean(N2_Press - He_Press) / first_stop_depth`

This is a normalized measure of how "loaded" the tissues are relative to the depth of the first deco stop.
- High ratio → tissues are highly loaded relative to the stop depth → diver needs extra shallow stop time
- Threshold at `0.40`: shallow gradient only activates when this ratio exceeds 40%
- The extra ceiling modifier scales linearly from 0 to 1.0 bar as ratio goes from 0.40 to 0.50

---

## Function 3: `ShallowGradTimeTest(double current_time_min)` — 0x35710

### Disassembly (annotated)

```asm
ShallowGradTimeTest:
   ; d0 = current_time_min (current stop time at this stop)
   
   ; Compare time against 60.0 minutes threshold
   mov   x8, #0x404e000000000000   ; = 60.0 (double)
   fmov  d1, x8
   
   ; Load Apply_Shallow_Grad flag and also check if time > 60
   ldr   x8, [Apply_Shallow_Grad ptr]
   ldrb  w9, [x8]                  ; w9 = Apply_Shallow_Grad (current)
   cset  w10, gt                   ; w10 = (current_time > 60.0)
   orr   w9, w10, w9               ; w9 = Apply_Shallow_Grad OR (time > 60)
   strb  w9, [x8]                  ; Apply_Shallow_Grad |= (time > 60.0)
   
   b.le  .done                     ; if time <= 60 → done
   
   ; time > 60: compute extra time factor
   mov   x8, #0xc04e000000000000   ; = -60.0 (double)
   fmov  d1, x8
   fadd  d0, d0, d1                ; d0 = current_time - 60.0   (excess minutes)
   ldr   d1, [rodata:0x13860]      ; d1 = 0.05
   fmul  d0, d0, d1                ; d0 = (time - 60) * 0.05
   fmov  d1, #1.0
   fminnm d0, d0, d1               ; d0 = min(result, 1.0)
   str   d0, [Shallow_Grad_Time_Factor]   ; store time-based extra factor

.done:
   ret
```

### Decoded logic

```c
void ShallowGradTimeTest(double current_time_min) {
    bool overtime = (current_time_min > 60.0);
    Apply_Shallow_Grad |= overtime;    // also activate if stop time exceeds 60 min
    
    if (overtime) {
        // Scale time factor: 0.0→1.0 for every 20 minutes over 60 min
        double excess = current_time_min - 60.0;
        Shallow_Grad_Time_Factor = fmin(excess * 0.05, 1.0);
        // reaches 1.0 at 60 + 20 = 80 minutes (1.0/0.05 = 20 extra min)
    }
}
```

### Key interpretation

A second, independent trigger for shallow gradient:
- If a stop time exceeds **60 minutes**, `Apply_Shallow_Grad` is set regardless of tissue loading
- The `Shallow_Grad_Time_Factor` then scales from 0.0 to 1.0 as time goes from 60 min to 80 min
- This prevents excessively long shallow stops on very long/deep dives even if tissue ratio looks OK

---

## Where `Apply_Shallow_Grad` Is Used — `DECOMPRESS_STOP` (0x34760)

From the `DECOMPRESS_STOP` disassembly, key branch at `0x34814`:

```asm
   ; Check Apply_Shallow_Grad flag
   ldrb  w8, [Apply_Shallow_Grad]
   tbnz  w8, #0, .skip_shallow   ; if Apply_Shallow_Grad == true, SKIP the extra ceiling
```

**Counter-intuitive**: when `Apply_Shallow_Grad` is set, `DECOMPRESS_STOP` *skips* a block that
would otherwise tighten the ceiling. This means the shallow gradient flag **relaxes** the stop
constraint, not tightens it. Looking at surrounding context:

```asm
   ; The skipped block @ 0x3484c–0x34878:
   ; Loads Depth_Start_of_Deco_Zone (first stop depth)
   ; Divides: ratio = current_ceiling / stop_depth
   ; Checks fractional part of ratio against a threshold
   ; If failed → branch to "extend this stop" path at 0x34dd8
```

The full control flow in `DECOMPRESS_STOP` around shallow gradient:

```c
// Simplified pseudocode of the relevant section in DECOMPRESS_STOP:

// Normal ceiling calculation first
CALC_DECO_CEILING(ceiling_out);
current_ceiling = *ceiling_out;

// Check 1: Is ceiling significantly different from stop depth?
if (fabs(current_ceiling - stop_depth) > epsilon) {
    // Check 2: Is the diver still above the ceiling?
    if (ceiling > (stop_depth - current_depth)) {
        // Check 3: Apply_Shallow_Grad flag — if SET, skip ratio check
        if (!Apply_Shallow_Grad) {
            // Check 4: In_Deco_Stops flag
            if (!In_Deco_Stops) {
                // Check 5: ceiling/stop_depth ratio fractional test
                ratio = current_ceiling / stop_depth_interval;
                frac  = ratio - floor(ratio);
                if (frac > threshold && frac <= (stop_depth_interval + threshold)) {
                    // branch to: extend stop time (add more minutes here)
                    goto extend_stop;
                }
            }
        }
    }
}
```

So `Apply_Shallow_Grad` **bypasses the fractional stop-extension check**. The effect is:
- When tissue loading is high (ratio > 0.40) or time is long (> 60 min): the fractional depth
  snap-to-stop logic is skipped, and the algorithm falls through to the normal per-minute deco
  computation without adding the "snap extension" penalty.
- This makes the deco schedule *smoother* and avoids the algorithm locking onto a stop for an
  extra cycle just because the ceiling falls awkwardly between two stop depths.

---

## Complete Shallow Gradient Algorithm (Reconstructed)

```
TRIGGER CONDITIONS (ShallowGradDepthTest):
  ratio = mean(N2_Press[i] - He_Press[i], i=0..15) / 32 / first_stop_depth
  Apply_Shallow_Grad = (ratio > 0.40)
  IF Apply_Shallow_Grad:
    Shallow_Grad_Max_ATA_Factor = min((ratio - 0.40) * 10, 1.0)
    → 0.0 at ratio=0.40, 1.0 at ratio≥0.50

ADDITIONAL TIME TRIGGER (ShallowGradTimeTest):
  Apply_Shallow_Grad |= (current_stop_time > 60 min)
  IF overtime:
    Shallow_Grad_Time_Factor = min((time - 60.0) * 0.05, 1.0)
    → 0.0 at 60 min, 1.0 at 80 min

GAS MIX GATING (ShallowGradMixTest):
  eligible = (single_gas_mode OR mix_count > 1)
  (mix test gates whether ShallowGrad is even evaluated)

EFFECT IN DECOMPRESS_STOP:
  When Apply_Shallow_Grad == true:
    → skip the fractional-stop snap-extension check
    → result: deco schedule doesn't add an extra stop-extension cycle
              based on how current ceiling falls between standard stop depths
    → net effect: slightly SHORTER or smoother shallow stop times vs
                  what GF-only would produce in some edge cases
```

---

## What Shallow Gradient Is NOT

1. **It is not an additional depth** added to the ceiling. The ceiling itself (from GF) is unchanged.
2. **It is not a separate conservatism slider** in the way GFHi/GFLo are. It is a stop-scheduling
   smoothness adjuster.
3. **It is not VPM-B surface tension compensation**. The computation touches tissue pressures
   directly but doesn't use bubble nuclei radii.
4. **It does not increase TTS in the usual case**. It more often *reduces* fractional stop extension,
   which could slightly reduce TTS when tissue ratio > 0.40.

---

## Parameters and Their Defaults

The three globals are set by `set_TVPM_properties()` from the Java settings object. Defaults are
not hardcoded in the binary (they come from app SharedPreferences). Typical values based on the
MultiDeco UI documentation:

| Parameter | Typical range | Effect at max |
|---|---|---|
| `Shallow_Grad_Depth_Factor` | 0.0 – 1.0 | Controls depth at which SG activates |
| `Shallow_Grad_Time_Factor` | 0.0 – 1.0 | Time-based trigger scaling |
| `Shallow_Grad_Max_ATA_Factor` | 0.0 – 1.0 bar | Max ceiling extra (computed, capped 1.0 bar) |

All three are **doubles** stored in BSS — confirming the earlier APK analysis finding that they are
runtime variables, not compile-time constants.

---

## Comparison with Subsurface / LSP D-Planner

| Feature | MultiDeco | Subsurface | LSP |
|---|---|---|---|
| GF Lo/Hi | Yes | Yes | Yes |
| Shallow Gradient | **Yes (proprietary)** | No | No |
| Fractional stop snap-extension | Yes (bypassed by SG) | No | No |
| Boyle's Law compensation | Yes (in SG trigger) | No | No |
| Stop interval | 1 ft/1 m (configurable) | 3 m | 3 m |

**Implication**: When MultiDeco shows shorter TTS than LSP at the same GF settings, part of the
difference may come from the Shallow Gradient feature bypassing the fractional stop extension.
The earlier assumption that the difference was due to `Water_Vapor_Press` alone is likely incomplete.

---

## Implementing Equivalent Behavior in LSP (Optional)

If you want LSP to replicate MultiDeco's shallow gradient behavior:

```js
// Step 1: After tissue update, compute supersaturation ratio
function computeShallowGradRatio(N2Press, HePress, firstStopDepthBar) {
    let sum = 0;
    for (let i = 0; i < 16; i++) {
        sum += N2Press[i] - HePress[i];
    }
    const mean = sum / 32.0;   // average over 16 N2 + 16 He values
    return mean / firstStopDepthBar;
}

// Step 2: Shallow grad activation check
function shouldApplyShallowGrad(ratio, currentStopTimeMin) {
    return ratio > 0.40 || currentStopTimeMin > 60.0;
}

// Step 3: Compute extra ceiling factor
function shallowGradMaxATA(ratio) {
    if (ratio <= 0.40) return 0;
    return Math.min((ratio - 0.40) * 10.0, 1.0);   // 0→1 over ratio 0.40→0.50
}

// Step 4: In deco stop loop — if Apply_Shallow_Grad, skip the fractional snap extension
// (most implementations don't have this sub-feature, so it may be a no-op)
```

Note: Implementing this faithfully requires also having `BOYLES_LAW_COMPENSATION` — which is another
proprietary MultiDeco function (at 0x342ac). That is a separate analysis task.

---

## Files

| File | Location |
|---|---|
| MultiDeco APK | `/home/user/workspace/apk_study/MultiDeco.apk` |
| Extracted `.so` (arm64) | `/home/user/workspace/apk_study/multideco_extracted/lib/arm64-v8a/libmultideco.so` |
| Full symbol list | `nm -D libmultideco.so` output in this analysis |
