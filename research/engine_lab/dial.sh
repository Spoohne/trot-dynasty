#!/bin/sh
# The pace dial (DECISIONS 188): Part 1 trips (200 races per track) and trait worth (32 fields), on PyPy.
cd "$(dirname "$0")"
PY=/c/Users/spooh/tools/pypy3.12-v8.0.1-win64/pypy3.exe
for lp in 1.5 2.0 2.5 3.0; do
  CFG="{\"lead_push\":$lp,\"lead_push_mile\":0.0,\"pace_k\":1.094,\"c_turn\":0.00034,\"s_top\":1.5,\"s_pocket\":3.0}"
  SCFG="{\"d_lead_push\":$lp,\"d_lead_push_mile\":0.0,\"pace_k\":1.094,\"c_turn\":0.00034,\"d_s_top\":1.5,\"d_s_pocket\":3.0}"
  echo "=== lead_push $lp"
  P1_RUN=dial_$lp P1_SET="$CFG" PY=$PY sh p1run.sh 2>&1 | grep -E "==|trips|margin"
  $PY v3_sens.py run dial$lp "$SCFG" 32 71 >/dev/null 2>&1
  $PY v3_sens.py show dial$lp 2>&1 | tail -1
done
