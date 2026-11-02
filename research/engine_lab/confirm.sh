#!/bin/sh
# Confirm one setting: trait worth on 64 fields and Part 1 trips (200 races per track), on PyPy.
cd "$(dirname "$0")"
PY=/c/Users/spooh/tools/pypy3.12-v8.0.1-win64/pypy3.exe
TAG=$1; CFG=$2
$PY v3_sens.py run $TAG "$CFG" 64 71 >/dev/null 2>&1
$PY v3_sens.py show $TAG 2>&1 | tail -1
P1CFG=$(echo "$CFG" | sed 's/"d_/"/g')
P1_RUN=p1_$TAG P1_SET="$P1CFG" PY=$PY sh p1run.sh 2>&1 | grep -E "==|trips|margin|by post"
