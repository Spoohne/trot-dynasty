#!/usr/bin/env bash
# Nightly: a dated copy of the save, keeping the last 14. (The host's weekly whole-server backups cover the rest.)
set -euo pipefail
SRC=/opt/trotdynasty/game/save.pkl
DST=/var/backups/trotdynasty
[ -f "$SRC" ] || exit 0
cp "$SRC" "$DST/save-$(date +%Y-%m-%d).pkl"
ls -1t "$DST"/save-*.pkl | tail -n +15 | xargs -r rm --
