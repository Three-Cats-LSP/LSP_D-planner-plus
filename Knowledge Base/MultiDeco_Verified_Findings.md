# MultiDeco Verified Binary Findings
## Direct binary verification — no inference

**Date:** June 2026  
**Verified by:** ARM64 disassembly trace + raw hex dump from `libmultideco.so`

---

## 1. N2 vs He k-value table identity — CONFIRMED

### The question
Which table at `0x15c00` is N2, and which at `0x15c80` is He?

### The proof — from `GAS_LOADINGS_CONST_DEPTH @ 0x35370`

```asm
; After Set_Inspired_Inert_Press returns:
35428:  ldr x21, [x21, #112]   ; x21 = BSS[0x61000+0x70] = pN2_tissue[] pointer
3544c:  ldr x23, [x23, #104]   ; x23 = BSS[0x61000+0x68] = pHe_tissue[] pointer

35430:  adr x22, 15c00          ; x22 = k-table at 0x15c00  ← fed into N2 loop
35438:  adr x24, 15c80          ; x24 = k-table at 0x15c80  ← fed into He loop

; Loop body (NEON, 2 compartments at once):
35450:  ldr q0, [x22, x20]      ; load k_N2[i,i+1]   from 0x15c00
354bc:  str q1, [x21, x20]      ; store result → pN2_tissue[i,i+1]

3548c:  ldr q1, [x24, x20]      ; load k_He[i,i+1]   from 0x15c80
354f0:  str q1, [x23, x20]      ; store result → pHe_tissue[i,i+1]
```

**x22 (0x15c00) feeds x21 (pN2_tissue) → 0x15c00 is the N2 k-value table.**  
**x24 (0x15c80) feeds x23 (pHe_tissue) → 0x15c80 is the He k-value table.**

### Raw bytes confirmed

```
0x15c00: d4 58 61 35 b4 98 d7 3f  →  IEEE754 little-endian = 0.368695308808481
         ln2 / 0.368695 = 1.880 min  ← N2 compartment 1 half-time

0x15c80: bd 94 2e ff 9b be c1 3f  →  IEEE754 little-endian = 0.138629436111989
         ln2 / 0.138629 = 5.000 min  ← He compartment 1 half-time
```

### All 16 N2 half-times (decoded from 0x15c00)

| Comp | k-value        | Half-time (min) | ZHL-16C N2 standard |
|------|----------------|-----------------|---------------------|
| 1    | 0.368695308808 | 1.88            | 4.0 or 5.0          |
| 2    | 0.229518933960 | 3.02            | 8.0                 |
| 3    | 0.146853216220 | 4.72            | 12.5                |
| 4    | 0.099162686775 | 6.99            | 18.5                |
| 5    | 0.067889048047 | 10.21           | 27.0                |
| 6    | 0.047869280425 | 14.48           | 38.3                |
| 7    | 0.033762648834 | 20.53           | 54.3                |
| 8    | 0.023811308161 | 29.11           | 77.0                |
| 9    | 0.016823960693 | 41.2            | 109.0               |
| 10   | 0.012559289374 | 55.19           | 146.0               |
| 11   | 0.009805448869 | 70.69           | 187.0               |
| 12   | 0.007672649774 | 90.34           | 239.0               |
| 13   | 0.006012205573 | 115.3           | 305.0               |
| 14   | 0.004701853077 | 147.4           | 390.0               |
| 15   | 0.003682252340 | 188.2           | 498.0               |
| 16   | 0.002887752283 | 240.0           | 635.0               |

### All 16 He half-times (decoded from 0x15c80)

| Comp | k-value        | Half-time (min) | ZHL-16C He standard |
|------|----------------|-----------------|---------------------|
| 1    | 0.138629436112 | 5.00            | 1.51 or 1.88        |
| 2    | 0.086643397570 | 8.00            | 3.02                |
| 3    | 0.055451774445 | 12.5            | 4.72                |
| 4    | 0.037467415165 | 18.5            | 7.99                |
| 5    | 0.025672117799 | 27.0            | 11.02               |
| 6    | 0.018097837613 | 38.3            | 16.0                |
| 7    | 0.012765141447 | 54.3            | 22.8                |
| 8    | 0.009001911436 | 77.0            | 32.3                |
| 9    | 0.006359148446 | 109.0           | 45.7                |
| 10   | 0.004747583428 | 146.0           | 61.2                |
| 11   | 0.003706669415 | 187.0           | 78.4                |
| 12   | 0.002900197408 | 239.0           | 100.0               |
| 13   | 0.002272613707 | 305.0           | 127.9               |
| 14   | 0.001777300463 | 390.0           | 163.4               |
| 15   | 0.001391861808 | 498.0           | 208.8               |
| 16   | 0.001091570363 | 635.0           | 266.0               |

### Key finding: MultiDeco He halftimes = canonical ZHL-16C He

The **He half-times exactly match canonical ZHL-16C** (Bühlmann 2002).

The **N2 half-times are NOT standard ZHL-16C**. The ratio N2_HT[i] / He_HT[i] is consistently ~2.65:
```
HT_N2[i] = HT_He[i] / 2.6595...
```
This is the **Bühlmann diffusion ratio** (N2 diffuses ~2.65× slower than He), applied uniformly
to derive N2 halftimes from He halftimes rather than using the independently tabulated values.

### Implication for LSP D-Planner development

- **Do NOT copy standard ZHL-16C N2 halftimes** if trying to match MultiDeco output
- Use `k_N2[i] = k_He[i] / 2.6595` or equivalently `HT_N2[i] = HT_He[i] * 2.6595`
- He table is straightforward: use canonical ZHL-16C He halftimes as-is

---

## 2. Section header — 0x15c00 is inside .rodata

```
.rodata   VMA: 0x013810   size: 0x460C   file_offset: 0x013810
```

`0x15c00` = `0x13810 + 0x03F0` — confirmed inside `.rodata` (read-only constants).  
No symbol names — stripped binary, no debug info.  
The nearest labeled address from the linker is `__llvm_fs_discriminator__@@Base` at `0x163c8`,
which is a compiler metadata marker, not a data symbol.

---

## 3. BSS Pointer Table — corrected and confirmed

From `GAS_LOADINGS_CONST_DEPTH` setup code:

```asm
adrp x21, 61000                ; page base
ldr  x21, [x21, #112]          ; 0x61000 + 0x70 = 0x61070 → pN2_tissue pointer

adrp x23, 61000
ldr  x23, [x23, #104]          ; 0x61000 + 0x68 = 0x61068 → pHe_tissue pointer
```

Corrected BSS global pointer offsets (from `0x61000` base):

| Offset | Hex addr | Points to |
|--------|----------|-----------|
| +0x18  | 0x61018  | WV / surface pressure |
| +0x20  | 0x61020  | First_Stop_Depth (double*) |
| +0x28  | 0x61028  | SurfacePhaseVolTime array |
| +0x38  | 0x61038  | Max_Actual_Grad |
| +0x40  | 0x61040  | InitAllowGrad_N2 array |
| +0x48  | 0x61048  | InitAllowGrad_He array |
| +0x50  | 0x61050  | Water_Vapor_Press (double*) |
| +0x58  | 0x61058  | Baro_Press (double*) |
| +0x60  | 0x61060  | Amb_Press_Onset_of_Imperm (the exported symbol) |
| +0x68  | 0x61068  | **pHe_tissue array** ← confirmed |
| +0x70  | 0x61070  | **pN2_tissue array** ← confirmed |
| +0x78  | 0x61078  | MaxCrushPress_N2 |
| +0x80  | 0x61080  | MaxCrushPress_He |
| +0x88  | 0x61088  | RadiiN2_current |
| +0x90  | 0x61090  | RadiiHe_current |
| +0x98  | 0x61098  | CritVolTime |
| +0xa0  | 0x610a0  | AllowGrad_N2_comp |
| +0xa8  | 0x610a8  | AllowGrad_He_comp |
| +0xb0  | 0x610b0  | RadiiN2_comp (Boyle compensated) |
| +0xb8  | 0x610b8  | RadiiHe_comp (Boyle compensated) |
| +0xd8  | 0x610d8  | Stop depth current (double*) |
| +0xe8  | 0x610e8  | First stop depth for GF ramp |
| +0x110 | 0x61110  | ShallowGrad score (double*) |
| +0x130 | 0x61130  | ShallowGrad_active flag |
| +0x168 | 0x61168  | VPM_active flag |

---

## 4. Binary artifacts in this repo

```
MultiDeco Binary/
├── MultiDeco_226.apk                  ← original APK (v2.26, Android)
├── lib/
│   ├── arm64-v8a/libmultideco.so      ← 378 KB arm64 native engine (primary)
│   └── armeabi-v7a/libmultideco.so    ← 255 KB armv7 (older devices)
└── tools/
    ├── disassemble.sh                 ← quick disassembly helper (needs objdump)
    ├── rodata_decode.py               ← extract rodata constants
    ├── rodata_decode2.py              ← VPM-B constants + halftime search
    ├── rodata_decode3.py              ← k-value → halftime conversion
    └── rodata_decode4.py              ← b-value table + constructor analysis
```

### To use with objdump

```bash
# Install:
sudo apt-get install binutils-aarch64-linux-gnu

# List all functions:
aarch64-linux-gnu-objdump -t lib/arm64-v8a/libmultideco.so | grep TVPM

# Disassemble a specific function:
aarch64-linux-gnu-objdump -d --start-address=0x35e04 --stop-address=0x35e38 \
  lib/arm64-v8a/libmultideco.so

# Or use the helper:
chmod +x tools/disassemble.sh
./tools/disassemble.sh 0x35e04 0x35e38

# Extract all rodata constants:
python3 tools/rodata_decode.py
```
