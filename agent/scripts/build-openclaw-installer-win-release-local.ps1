#Requires -Version 5.1
param(
    [switch]$ForcePopulateCache,
    [switch]$ForceNodeDownload,
    [switch]$VerifyCache,
    [switch]$CacheOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cache = Join-Path $scriptDir "openclaw-npm-cache"
$nodeDir = Join-Path $scriptDir "node-v22.22.2"
$z64 = Join-Path $nodeDir "node-v22.22.2-win-x64.zip"
$z86 = Join-Path $nodeDir "node-v22.22.2-win-x86.zip"
$openclawNpm = "2026.4.15"

$cacheItemCount = 0
if (Test-Path -LiteralPath $cache) {
    $cacheItemCount = @(Get-ChildItem -LiteralPath $cache -ErrorAction SilentlyContinue).Count
}
if ($CacheOnly -and $cacheItemCount -eq 0) {
    throw "openclaw-npm-cache 为空，请先联网执行: agent\scripts\fetch-openclaw-npm-cache.ps1"
}

$doPopulate = -not $CacheOnly
if ($doPopulate -and -not $ForcePopulateCache -and $cacheItemCount -gt 0) {
    $doPopulate = $false
}
if ($doPopulate) {
    New-Item -ItemType Directory -Force -Path $cache | Out-Null
    npm install -g "openclaw@$openclawNpm" --cache $cache --registry "https://registry.npmjs.org/"
    if ($LASTEXITCODE -ne 0) { throw "npm cache populate failed" }
}

if ($VerifyCache) {
    $cacheFull = (Resolve-Path -LiteralPath $cache).Path
    $probe = Join-Path $scriptDir ".offline-openclaw-probe"
    if (Test-Path -LiteralPath $probe) { Remove-Item -LiteralPath $probe -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $probe | Out-Null
    npm install --prefix $probe "openclaw@$openclawNpm" --offline --cache $cacheFull --registry "https://registry.npmjs.org/" --prefer-offline --no-audit --no-fund
    if ($LASTEXITCODE -ne 0) { throw "offline cache verify failed" }
    Remove-Item -LiteralPath $probe -Recurse -Force
}

$getNode = $true
if (-not $ForceNodeDownload -and (Test-Path -LiteralPath $z64) -and (Test-Path -LiteralPath $z86)) {
    $getNode = $false
}
if ($getNode) {
    New-Item -ItemType Directory -Force -Path $nodeDir | Out-Null
    $base = "https://nodejs.org/dist/v22.22.2"
    foreach ($name in @("node-v22.22.2-win-x64.zip", "node-v22.22.2-win-x86.zip")) {
        Invoke-WebRequest -Uri "$base/$name" -OutFile (Join-Path $nodeDir $name) -UseBasicParsing
    }
}

Push-Location $scriptDir
try {
    powershell -ExecutionPolicy Bypass -File .\build-openclaw-installer-exe.ps1
    if ($LASTEXITCODE -ne 0) { throw "build-openclaw-installer-exe failed" }
    powershell -ExecutionPolicy Bypass -File .\build-openclaw-uninstaller-exe.ps1
    if ($LASTEXITCODE -ne 0) { throw "build-openclaw-uninstaller-exe failed" }
    powershell -ExecutionPolicy Bypass -File .\pack-openclaw-installer-release.ps1 -NoZip
    if ($LASTEXITCODE -ne 0) { throw "pack-openclaw-installer-release failed" }
} finally {
    Pop-Location
}

$stage = Join-Path $scriptDir "dist\OpenClawInstaller"
Write-Output "STAGE: $stage"
