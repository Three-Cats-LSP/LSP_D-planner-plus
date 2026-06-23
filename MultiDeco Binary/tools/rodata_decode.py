import struct

SO_PATH = "/home/user/workspace/apk_study/multideco_extracted/lib/arm64-v8a/libmultideco.so"
RODATA_FILE_OFFSET = 0x13810
RODATA_SIZE = 0x460c

with open(SO_PATH, "rb") as f:
    f.seek(RODATA_FILE_OFFSET)
    data = f.read(RODATA_SIZE)

print(f"Read {len(data)} bytes from .rodata at file offset 0x{RODATA_FILE_OFFSET:x}")
print()

# Key addresses referenced in disassembly (file offsets = vaddr for this .so since base=0)
# rodata vaddr starts at 0x13810
base = 0x13810

def read_double(offset_vaddr):
    rel = offset_vaddr - base
    if rel < 0 or rel + 8 > len(data):
        return None
    val, = struct.unpack_from('<d', data, rel)
    return val

def read_double_pair(offset_vaddr):
    return read_double(offset_vaddr), read_double(offset_vaddr + 8)

# Known offsets referenced in disassembly
refs = {
    0x13830: "SetGradFactor multiplier (0.01?)",
    0x13838: "?",
    0x13840: "?",
    0x13848: "?",
    0x13860: "?",
    0x13870: "ZHL-16C a-values N2 start?",
    # 2080 = 0x13810+0x270 offset from base = 0x13A80
    # fd441101 ldr d1 [x8,#2080] -> x8=0x13000, 0x13000+2080=0x138A0... let me compute
}

# The adrp instructions page-align to 0x13000, then fd44XYYY adds offset
# adrp x8,13000 -> x8 = 0x13000
# fd441101 ldr d1,[x8,#2080] -> 0x13000+2080 = 0x138A0 -> vaddr 0x138A0

offsets_to_check = {
    # From CALC_SURFACE_PHASE_VOLUME_TIME: ldr d1, [x8, #2080] with x8=0x13000
    "0x138A0 (CALC_SURFACE_PHASE_VOLUME_TIME d1)": 0x13000 + 2080,
    # SetGradFactor: 0x13830
    "0x13830 (0.01 GF scale)": 0x13830,
    "0x13838": 0x13838,
    # VPM_REPETITIVE_ALGORITHM: ldr d16,[x15,#2176] with x15=0x13000
    "0x138800 (VPM_REP d16)": 0x13000 + 2176,   # = 0x13880
    # CALC_START_OF_DECO_ZONE various  
    "0x13000+2136": 0x13000 + 2136,  # 0x13858
    "0x13000+2144": 0x13000 + 2144,  # 0x13860
    "0x13000+2152": 0x13000 + 2152,  # 0x13868
    "0x13000+2160": 0x13000 + 2160,  # 0x13870
    "0x13000+2176": 0x13000 + 2176,  # 0x13880
    "0x13000+2192": 0x13000 + 2192,  # 0x13890
    "0x13000+2200": 0x13000 + 2200,  # 0x13898
    "0x13000+2208": 0x13000 + 2208,  # 0x138A0
    "0x13000+2280": 0x13000 + 2280,  # 0x138E8
    "0x13000+2288": 0x13000 + 2288,  # 0x138F0
    "0x13000+2360": 0x13000 + 2360,  # 0x13938
    "0x13000+2408": 0x13000 + 2408,  # 0x13968
    "0x13000+2456": 0x13000 + 2456,  # 0x13998
    "0x13000+2464": 0x13000 + 2464,  # 0x139A0
    "0x13000+2472": 0x13000 + 2472,  # 0x139A8
    "0x13000+2480": 0x13000 + 2480,  # 0x139B0
    "0x13000+2504": 0x13000 + 2504,  # 0x139C8
    "0x13000+2512": 0x13000 + 2512,  # 0x139D0
    "0x13000+2520": 0x13000 + 2520,  # 0x139D8
    # DECOMPRESS_STOP constants
    "0x13000+2096": 0x13000 + 2096,  # 0x13830+... let me recalc: 2096 hex = 0x830 -> 0x13830
}

print("=== Key .rodata doubles ===")
for name, vaddr in offsets_to_check.items():
    val = read_double(vaddr)
    if val is not None:
        print(f"  [{name}] @ 0x{vaddr:05x}: {val:.15g}")
    else:
        print(f"  [{name}] @ 0x{vaddr:05x}: OUT OF RANGE")

# Dump the first 512 bytes as doubles to identify the constant tables
print()
print("=== All doubles from 0x13810 to 0x13A10 ===")
for i in range(0, 256, 8):
    vaddr = base + i
    val = read_double(vaddr)
    print(f"  0x{vaddr:05x} (+{i:3d}): {val:.15g}")

