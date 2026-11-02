#!/bin/sh
# Part 1 race checks for one engine version: P1_RUN=<folder> [PY=<pypy3.exe>] sh p1run.sh   (4 seeds x 50 races per track, form 0.33)
cd "$(dirname "$0")/../.."
for s in 11 12 13 14; do
  "${PY:-python}" research/engine_lab/v3_part1.py race half $s 50 0.33 &
  "${PY:-python}" research/engine_lab/v3_part1.py race mile $s 50 0.33 &
done
wait
python research/engine_lab/v3_part1.py sum 0.33
