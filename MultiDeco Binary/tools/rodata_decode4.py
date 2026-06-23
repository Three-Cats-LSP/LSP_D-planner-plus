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
    return struct.unpack_from('<d', data, rel)[0]

def read_n_doubles(vaddr, n):
    return [read_double(vaddr + i*8) for i in range(n)]

# The N2 halftimes found at 0x16320 are WRONG (they look like a GF stop table)
# Let me look at 0x15798 more carefully
print("=== @ 0x15798 context ===")
vals = read_n_doubles(0x15780, 30)
for i, v in enumerate(vals):
    print(f"  0x{0x15780+i*8:x}: {v}")

# Search for ZHL-16C standard halftime set: 4,8,12.5,18.5,27 (Buhlmann 2002)
# or: 5,8,12.5,18.5,27 (ZHL-16C)
print("\n=== Searching for HT=4.0 (ZHL-16A start) or 5.0 (ZHL-16C) ===")
for target_val in [5.0, 4.0, 8.0]:
    target = struct.pack('<d', target_val)
    idx = 0
    found_count = 0
    while True:
        idx = data.find(target, idx)
        if idx == -1 or found_count > 5:
            break
        vaddr = base + idx
        # Check if followed by plausible halftimes
        vals = [read_double(vaddr + j*8) for j in range(8)]
        if vals[1] and 5 < vals[1] < 15 and vals[2] and 10 < vals[2] < 20:
            print(f"  CANDIDATE at vaddr 0x{vaddr:x}: {vals}")
        idx += 8
        found_count += 1

# Find a-values by searching for 1.2599 (canonical ZHL-16C a1 N2)
# Or 1.1696 (ZHL-16 a1 N2 in some versions)
# Or try 0.6200 (Subsurface a5)
# Or known: a[4] for ZHL-16C = 0.6200 (subsurface) or 0.6491 (canonical)
print("\n=== Scanning .rodata for values between 0.5 and 1.3 in sequence (a-values?) ===")
# ZHL-16C a-values N2: ~1.2599, 1.0, 0.8618, 0.7562, 0.6200, 0.5043...
# or N2 from TVPM: let's try searching
# Look for 0x015e80 which is the known b-array address
# Actually, ZHL-16C a, b, and halftimes are in .rodata
# The b values start from 0.5050 and increase to ~1.0
# Let's scan for monotonically increasing sequences ~0.5-1.0
candidates = []
for i in range(0, len(data)-128, 8):
    v0 = struct.unpack_from('<d', data, i)[0]
    if 0.48 < v0 < 0.52:  # potential b[0]
        seq = [struct.unpack_from('<d', data, i+j*8)[0] for j in range(16)]
        # ZHL-16C b: 0.5050, 0.6514, 0.7222, 0.7825, 0.8126, 0.8434, 0.8693, 0.8910, 0.9092...
        if all(0 < seq[j] < 1.1 for j in range(16)) and all(seq[j] < seq[j+1] for j in range(15)):
            candidates.append((base+i, seq))

print(f"Found {len(candidates)} monotone b-value candidate sequences")
for vaddr, seq in candidates[:3]:
    print(f"  @ 0x{vaddr:x}: {[f'{v:.4f}' for v in seq]}")

# The ZHL-16C values are stored in the BSS (.bss) as initialized by constructor
# 0x015e80 was the known b-array vaddr — that's in .data/.bss
# Let me check the TVPM constructor code: it loads from .rodata at 0x13000+2752
# 3dc2b100  ldr q0, [x8, #2752]  -> 0x13000+2752 = 0x13AC0
print("\n=== @ 0x13AC0 constructor data (0x13000+2752) ===")
for i in range(0, 512, 16):
    vaddr = 0x13ac0 + i
    v0 = read_double(vaddr)
    v1 = read_double(vaddr+8)
    if v0 is not None and v1 is not None:
        print(f"  0x{vaddr:x}: {v0:.8g}, {v1:.8g}")

