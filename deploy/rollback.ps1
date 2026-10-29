# Put an earlier commit of Trot Dynasty back on the server (code and art; the server keeps its save).
#   .\deploy\rollback.ps1 -Server 203.0.113.10            the commit before the current one
#   .\deploy\rollback.ps1 -Server 203.0.113.10 -To 09ee23a  a specific commit (git log --oneline)
param([Parameter(Mandatory)][string]$Server, [string]$To = "HEAD~1")
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Push-Location $root
try {
    if (git status --porcelain) { throw "Uncommitted changes here: commit or stash them first, so the rollback is clean." }
    $was = git rev-parse --short HEAD
    git checkout -q $To
    $now = git rev-parse --short HEAD
    Write-Host "Rolling the server back from $was to $now"
    & "$PSScriptRoot\push.ps1" -Server $Server
    git checkout -q -
    Write-Host "Back on $was locally. The server runs $now until the next push."
} finally { Pop-Location }
