import struct, math

SO_PATH = "/home/user/workspace/apk_study/multideco_extracted/lib/arm64-v8a/libmultideco.so"
RODATA_FILE_OFFSET = 0x13810
RODATA_SIZE = 0x460c

with open(SO_PATH, "rb") as f:
    f.seek(RODATA_FILE_OFFSET)
    data = f.read(RODATA_SIZE)

base = 0x13810

def read_double(vaddr):
    rel = vaddr - base
    if rel < 0 or rel + 8 > len(data):
        return None
    val, = struct.unpack_from('<d', data, rel)
    return val

def read_n_doubles(vaddr, n):
    return [read_double(vaddr + i*8) for i in range(n)]

# ZHL-16C halftimes found at 0x16320 — 16 entries
print("=== ZHL-16C N2 halftimes @ 0x16320 ===")
n2_ht = read_n_doubles(0x16320, 16)
print(n2_ht)

# Look for He halftimes nearby — should start at 1.51 (He HT1)
print("\n=== 0x163A0 area (He halftimes?) ===")
he_ht = read_n_doubles(0x163a0, 16)
print(he_ht)
print("\n=== 0x16420 area ===")
vals = read_n_doubles(0x16420, 16)
print(vals)

# Look for ZHL-16C a and b values
# a-values for N2 (canonical): 1.2599, 1.0, 0.8618, 0.7562, 0.62, 0.5043, 0.441, 0.4, ...
print("\n=== Searching for a1=1.2599 ===")
target = struct.pack('<d', 1.2599)
idx = 0
while True:
    idx = data.find(target, idx)
    if idx == -1:
        break
    print(f"  Found 1.2599 at vaddr 0x{base+idx:x}")
    vals = read_n_doubles(base+idx, 16)
    print("  16 doubles:", vals)
    idx += 1

# Approximate search for 1.259 family
print("\n=== Searching for ~1.26 in 8-byte steps from ZHL table ===")
for i in range(0, 0x800, 8):
    vaddr = 0x16320 + i
    val = read_double(vaddr)
    if val is not None and 1.25 < val < 1.27:
        print(f"  0x{vaddr:x}: {val}")

# VPM-B constants: critical_radius_N2 and critical_radius_He 
# Stored in .bss typically, but initial values may be in .rodata
# Initial critical radii: N2~0.55 microns, He~0.55 microns (in cm: 5.5e-5)
# In VPM-B reference: r_N2=0.55, r_He=0.55 in units of micrometers
# Some implementations: lambda = 1.25 e-5 cm (0.125 μm)
print("\n=== VPM-B constants area @ 0x13ac0 ===")
print("0x13ac0 =", read_double(0x13ac0), " (0.257 = Gamma_c/Gamma_s ratio?)")
print("0x13ac8 =", read_double(0x13ac8), " (0.0179 = gamma_c bubble surface tension N/m?)")

# Verify: 0x15c00 are k-values = ln2/halftime for all 16 compartments
print("\n=== k-values (ln2/ht) @ 0x15c00 ===")
for i in range(16):
    kval = read_double(0x15c00 + i*8)
    # ht = ln2/k
    ht = math.log(2)/kval if kval else None
    print(f"  [{i:2d}] k={kval:.8g}, implied HT_N2={ht:.4g}")

print("\n=== k-values (ln2/ht He) @ 0x15c80 ===")
for i in range(16):
    kval = read_double(0x15c80 + i*8)
    ht = math.log(2)/kval if kval else None
    print(f"  [{i:2d}] k={kval:.8g}, implied HT_He={ht:.4g}")

# ZHL-16C b-values: look for b1=0.5050
print("\n=== Searching for b1=0.5050 ===")
for target_val in [0.5050, 0.505, 0.50499]:
    target = struct.pack('<d', target_val)
    idx = 0
    while True:
        idx = data.find(target, idx)
        if idx == -1:
            break
        print(f"  Found {target_val} at vaddr 0x{base+idx:x}")
        vals = read_n_doubles(base+idx, 16)
        print("  16 doubles:", vals)
        idx += 1

