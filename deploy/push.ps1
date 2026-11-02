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

$exclude = @("--exclude=./exports", "--exclude=./snapshots", "--exclude=./.claude", "--exclude=./.git", "--exclude=__pycache__",
             "--exclude=*.bak*", "--exclude=./save.before-*.pkl", "--exclude=./save.pkl",
             # work files the game never reads: art pipelines (it needs only art/*.py, art/hero, art/cache), previews, 3D tests
             "--exclude=./art/astra_run", "--exclude=./art/barns", "--exclude=./art/blender", "--exclude=./art/day", "--exclude=./art/emblem", "--exclude=./art/legcode", "--exclude=./art/letters", "--exclude=./art/local", "--exclude=./art/marquee2", "--exclude=./art/overhead", "--exclude=./art/portrait_mock", "--exclude=./art/reference", "--exclude=./art/rig", "--exclude=./art/seedance_in", "--exclude=./art/seedance_out", "--exclude=./art/social", "--exclude=./art/spritelab", "--exclude=./art/styles", "--exclude=./art/styles2", "--exclude=./art/tack_layers", "--exclude=./art/top", "--exclude=./art/tracks", "--exclude=./art/wc_mock",
             "--exclude=./review", "--exclude=./mockups/*.glb", "--exclude=./mockups/*.gif", "--exclude=./research/encyclopedia/*.db*")
if ($WithSave) { $exclude = $exclude | Where-Object { $_ -ne "--exclude=./save.pkl" } }
# every deploy is a commit, so what's on the server is always a commit you can go back to
Push-Location $root
try {
    if (git status --porcelain) {
        git add -A
        git commit -q -m "Deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
    }
    $commit = git rev-parse --short HEAD
    if (git remote) { git push -q 2>$null }
} finally { Pop-Location }
Write-Host "Deploying commit $commit"
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
