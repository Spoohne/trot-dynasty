# Push Trot Dynasty from this PC to the server, and restart it there.
#   .\deploy\push.ps1 -Server 203.0.113.10            code and art only: the server keeps its own save
#   .\deploy\push.ps1 -Server 203.0.113.10 -WithSave  also carry this PC's save across (the one-time move)
# The first run also copies this deploy folder up, for setup.sh.
param([Parameter(Mandatory)][string]$Server, [switch]$WithSave)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$pkg = Join-Path $env:TEMP "trotdynasty.tgz"

if ($WithSave) {
    $local = Get-NetTCPConnection -LocalPort 8111 -State Listen -ErrorAction SilentlyContinue
    if ($local) { throw "The game is still running on this PC. Stop it first, so the save you carry across is final." }
}

$exclude = @("--exclude=./exports", "--exclude=./snapshots", "--exclude=./.claude", "--exclude=__pycache__",
             "--exclude=*.bak*", "--exclude=./save.before-*.pkl", "--exclude=./save.pkl")
if ($WithSave) { $exclude = $exclude | Where-Object { $_ -ne "--exclude=./save.pkl" } }
Write-Host "Packaging..."
tar -czf $pkg -C $root @exclude .
"{0:N0} MB" -f ((Get-Item $pkg).Length / 1MB) | Write-Host

Write-Host "Uploading..."
scp $pkg "root@${Server}:/tmp/trotdynasty.tgz"
ssh "root@$Server" @"
set -e
systemctl stop trotdynasty || true
mkdir -p /opt/trotdynasty/game
tar -xzf /tmp/trotdynasty.tgz -C /opt/trotdynasty/game
chown -R trot:trot /opt/trotdynasty/game
rm /tmp/trotdynasty.tgz
if [ -f /opt/trotdynasty/game/save.pkl ]; then systemctl start trotdynasty; echo 'Game started.'; else echo 'No save on the server yet: push once with -WithSave.'; fi
"@
Remove-Item $pkg
Write-Host "Done."
