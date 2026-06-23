#!/bin/bash
# MultiDeco libmultideco.so disassembly helper
# Requires: aarch64-linux-gnu-objdump
#   sudo apt-get install binutils-aarch64-linux-gnu
#
# Usage: ./disassemble.sh [function_name] [start_addr] [stop_addr]
# Example: ./disassemble.sh VPM_CALCULATE 0x29c18 0x2b000

SO="$(dirname "$0")/../lib/arm64-v8a/libmultideco.so"

if [ $# -eq 0 ]; then
  echo "Available TVPM functions:"
  echo "  VPM_CALCULATE              0x29c18"
  echo "  VPM_REPETITIVE_ALGORITHM   0x30c28"
  echo "  SET_CRITICAL_RADII         0x305c0"
  echo "  CALC_BARO_PRESS            0x306dc"
  echo "  GAS_LOADINGS_SURFACE_INT   0x307a8"
  echo "  NUCLEAR_REGENERATION       0x316f0"
  echo "  SetGradFactor              0x31608"
  echo "  CALC_INIT_ALLOW_GRAD       0x31844"
  echo "  CALC_START_OF_DECO_ZONE    0x318ec"
  echo "  PROJECTED_ASCENT           0x320f8"
  echo "  GAS_LOADINGS_ASCENT_DESC   0x32b9c"
  echo "  CALC_MAX_ACTUAL_GRAD       0x3416c"
  echo "  BOYLES_LAW_COMPENSATION    0x342ac"
  echo "  DECOMPRESS_STOP            0x34760"
  echo "  CALC_SURFACE_PHASE_VOL_T   0x355b8"
  echo "  CALC_CRUSH_PRESS           0x35000"
  echo "  CRIT_VOLUME                0x35b64"
  echo "  GAS_LOADINGS_CONST_DEPTH   0x35370"
  echo "  SCHREINER_EQUATION         0x35dc4"
  echo "  HALDANE_EQUATION           0x35e04"
  echo "  Set_Inspired_Inert_Press   0x35e38"
  echo "  ONSET_OF_IMPERMEABILITY    0x360d4"
  echo "  RAD_ROOT_FINDER            0x36304"
  echo "  CALC_DECO_CEILING          0x31ee0"
  echo "  CALC_DECO_CEILING_GF       0x31bf8"
  echo "  CALC_ASCENT_CEILING        0x31dc0"
  echo "  TVPM_constructor           0x3642c"
  echo ""
  echo "Usage: $0 <start_addr_hex> <stop_addr_hex>"
  echo "  e.g. $0 0x35e04 0x35e38"
else
  START=$1
  STOP=$2
  aarch64-linux-gnu-objdump -d --start-address=$START --stop-address=$STOP "$SO"
fi
