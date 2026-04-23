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
$nodeDir = Join-Path $scriptDir "node-v24.15.0"
$z64 = Join-Path $nodeDir "node-v24.15.0-win-x64.zip"
$z86 = Join-Path $nodeDir "node-v24.15.0-win-x86.zip"
$openclawNpm = "2026.4.15"

<# ── openclaw-npm-cache 已不再打包，以下逻辑注释保留 ──
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
#>

$getNode = $true
if (-not $ForceNodeDownload -and (Test-Path -LiteralPath $z64) -and (Test-Path -LiteralPath $z86)) {
    $getNode = $false
}
if ($getNode) {
    New-Item -ItemType Directory -Force -Path $nodeDir | Out-Null
    $base = "https://nodejs.org/dist/v24.15.0"
    foreach ($name in @("node-v24.15.0-win-x64.zip", "node-v24.15.0-win-x86.zip")) {
        Invoke-WebRequest -Uri "$base/$name" -OutFile (Join-Path $nodeDir $name) -UseBasicParsing
    }
}

function New-LocalOpenClawInstallerFolder {
    $distDir = Join-Path $scriptDir "dist"
    $stageDir = Join-Path $distDir "OpenClawInstaller"
    $installerExe = Join-Path $distDir "OpenClawInstaller.exe"
    $uninstallerExe = Join-Path $distDir "OpenClawUninstaller.exe"
    $templatesDir = Join-Path $scriptDir "openclaw-templates"
    $nodeOfflineDir = Join-Path $scriptDir "node-v24.15.0"
    $nodeZip64 = Join-Path $nodeOfflineDir "node-v24.15.0-win-x64.zip"
    $nodeZip86 = Join-Path $nodeOfflineDir "node-v24.15.0-win-x86.zip"
    # $npmCacheDir = Join-Path $scriptDir "openclaw-npm-cache"  # 不再打包
    $skillsDir = Join-Path $scriptDir "openclaw-skills"
    if (-not (Test-Path -LiteralPath $installerExe)) { throw "missing exe: $installerExe" }
    if (-not (Test-Path -LiteralPath $uninstallerExe)) { throw "missing exe: $uninstallerExe" }
    if (-not (Test-Path -LiteralPath $templatesDir)) { throw "missing dir: $templatesDir" }
    if (-not (Test-Path -LiteralPath $nodeOfflineDir)) { throw "missing dir: $nodeOfflineDir" }
    if (-not (Test-Path -LiteralPath $nodeZip64)) { throw "missing file: $nodeZip64" }
    if (-not (Test-Path -LiteralPath $nodeZip86)) { throw "missing file: $nodeZip86" }
    $skillsZip = Join-Path $skillsDir "skills.zip"
    if (-not (Test-Path -LiteralPath $skillsDir)) { throw "missing dir: $skillsDir" }
    if (-not (Test-Path -LiteralPath $skillsZip)) { throw "missing file: $skillsZip" }
    if (Test-Path -LiteralPath $stageDir) { Remove-Item -LiteralPath $stageDir -Recurse -Force }
    New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
    Copy-Item -LiteralPath $installerExe -Destination (Join-Path $stageDir "OpenClawInstaller.exe") -Force
    Copy-Item -LiteralPath $uninstallerExe -Destination (Join-Path $stageDir "OpenClawUninstaller.exe") -Force
    Copy-Item -LiteralPath $templatesDir -Destination (Join-Path $stageDir "openclaw-templates") -Recurse -Force
    $stageNodeDir = Join-Path $stageDir "node-v24.15.0"
    New-Item -ItemType Directory -Path $stageNodeDir -Force | Out-Null
    Copy-Item -LiteralPath $nodeZip64 -Destination (Join-Path $stageNodeDir "node-v24.15.0-win-x64.zip") -Force
    Copy-Item -LiteralPath $nodeZip86 -Destination (Join-Path $stageNodeDir "node-v24.15.0-win-x86.zip") -Force
    # Copy-Item -LiteralPath $npmCacheDir -Destination (Join-Path $stageDir "openclaw-npm-cache") -Recurse -Force  # 不再打包
    Copy-Item -LiteralPath $skillsDir -Destination (Join-Path $stageDir "openclaw-skills") -Recurse -Force
    Remove-Item -LiteralPath $installerExe, $uninstallerExe -Force
    return $stageDir
}

$localStage = $null
Push-Location $scriptDir
try {
    powershell -ExecutionPolicy Bypass -File .\build-openclaw-installer-exe.ps1
    if ($LASTEXITCODE -ne 0) { throw "build-openclaw-installer-exe failed" }
    powershell -ExecutionPolicy Bypass -File .\build-openclaw-uninstaller-exe.ps1
    if ($LASTEXITCODE -ne 0) { throw "build-openclaw-uninstaller-exe failed" }
    $localStage = New-LocalOpenClawInstallerFolder
    Write-Host "staged: $localStage"
} finally {
    Pop-Location
}

Write-Output "STAGE: $localStage"
