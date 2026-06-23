import struct

SO_PATH = "/home/user/workspace/apk_study/multideco_extracted/lib/arm64-v8a/libmultideco.so"
RODATA_FILE_OFFSET = 0x13810
RODATA_SIZE = 0x460c

with open(SO_PATH, "rb") as f:
    f.seek(RODATA_FILE_OFFSET)
    data = f.read(RODATA_SIZE)

base = 0x13810  # vaddr base of .rodata

def read_double(vaddr):
    rel = vaddr - base
    if rel < 0 or rel + 8 > len(data):
        return None
    val, = struct.unpack_from('<d', data, rel)
    return val

# Dump big block 0x13A10 to 0x15C00 looking for ZHL-16C tables 
# ZHL-16C tables have 16 entries each: a-values, b-values, half-times N2 and He
print("=== Doubles 0x13A10 - 0x13C00 ===")
for i in range(0, 512, 8):
    vaddr = 0x13a10 + i
    val = read_double(vaddr)
    if val:
        print(f"  0x{vaddr:05x}: {val:.15g}")

# Look for the half-time tables (known values for ZHL-16C)
# N2 halftimes: 5,8,12.5,18.5,27,38.3,54.3,77,109,146,187,239,305,390,498,635
print()
print("=== Searching for ZHL-16C N2 halfTime=5.0 ===")
target = struct.pack('<d', 5.0)
idx = 0
while True:
    idx = data.find(target, idx)
    if idx == -1:
        break
    print(f"  Found 5.0 at file_off 0x{RODATA_FILE_OFFSET+idx:x}, vaddr 0x{base+idx:x}")
    # dump 16 doubles from here
    for j in range(16):
        rel = idx + j*8
        if rel+8 > len(data):
            break
        v, = struct.unpack_from('<d', data, rel)
        print(f"    [{j:2d}] {v:.8g}")
    idx += 1

print()
print("=== Searching for VPM initial critical radii N2=0.5 or He=0.5 ===")
# VPM-B critical radii typically ~0.5 micrometers expressed as 5e-4 mm
# or stored as actual micrometers
for target_val in [0.5, 0.0005, 5e-4]:
    target = struct.pack('<d', target_val)
    idx = 0
    while True:
        idx = data.find(target, idx)
        if idx == -1:
            break
        print(f"  Found {target_val} at vaddr 0x{base+idx:x}")
        idx += 1

# Also look for known VPM-B constants: lambda_N2 = 7599.74 (surface tension factor)
# or gamma = 0.0179 N/m
for target_val in [7599.74, 0.0179, 179.0, 0.179]:
    target = struct.pack('<d', target_val)
    idx = 0
    while True:
        idx = data.find(target, idx)
        if idx == -1:
            break
        print(f"  Found {target_val} at vaddr 0x{base+idx:x}")
        idx += 1

# Dump 0x15c00 area — the half-time lookup table for SET_CRITICAL_RADII
print()
print("=== 0x15c00 area (halfTime table for SET_CRITICAL_RADII) ===")
for i in range(0, 256, 8):
    vaddr = 0x15c00 + i
    val = read_double(vaddr)
    if val is not None:
        print(f"  0x{vaddr:05x}: {val:.15g}")

