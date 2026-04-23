#Requires -Version 5.1
param(
    [string]$ZipName = "",
    [switch]$NoZip
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $scriptDir "dist"
$stageDir = Join-Path $distDir "OpenClawInstaller"
$zipPath = $null
if (-not $NoZip) {
    if ([string]::IsNullOrWhiteSpace($ZipName)) {
        $ZipName = "OpenClawInstaller-win-{0}.zip" -f (Get-Date -Format "yyyy.M.d")
    }
    $zipPath = Join-Path $distDir $ZipName
}

$installerExe = Join-Path $distDir "OpenClawInstaller.exe"
$uninstallerExe = Join-Path $distDir "OpenClawUninstaller.exe"
$templatesDir = Join-Path $scriptDir "openclaw-templates"
$nodeOfflineDir = Join-Path $scriptDir "node-v24.15.0"
$nodeZip64 = Join-Path $nodeOfflineDir "node-v24.15.0-win-x64.zip"
$nodeZip86 = Join-Path $nodeOfflineDir "node-v24.15.0-win-x86.zip"
$npmCacheDir = Join-Path $scriptDir "openclaw-npm-cache"
$skillsDir = Join-Path $scriptDir "openclaw-skills"

if (-not (Test-Path -LiteralPath $installerExe)) { throw "missing exe: $installerExe" }
if (-not (Test-Path -LiteralPath $uninstallerExe)) { throw "missing exe: $uninstallerExe" }
if (-not (Test-Path -LiteralPath $templatesDir)) { throw "missing dir: $templatesDir" }
if (-not (Test-Path -LiteralPath $nodeOfflineDir)) { throw "missing dir: $nodeOfflineDir (offline Node bundles required next to pack script)" }
if (-not (Test-Path -LiteralPath $nodeZip64)) { throw "missing file: $nodeZip64" }
if (-not (Test-Path -LiteralPath $nodeZip86)) { throw "missing file: $nodeZip86" }
if (-not (Test-Path -LiteralPath $npmCacheDir)) { throw "missing dir: $npmCacheDir (run fetch-openclaw-npm-cache.ps1 with network first)" }
$skillsZip = Join-Path $skillsDir "skills.zip"
if (-not (Test-Path -LiteralPath $skillsDir)) { throw "missing dir: $skillsDir" }
if (-not (Test-Path -LiteralPath $skillsZip)) { throw "missing file: $skillsZip" }
$cacheItems = @(Get-ChildItem -LiteralPath $npmCacheDir -ErrorAction SilentlyContinue)
if ($cacheItems.Count -eq 0) { throw "openclaw-npm-cache is empty; run fetch-openclaw-npm-cache.ps1" }

if (Test-Path -LiteralPath $stageDir) { Remove-Item -LiteralPath $stageDir -Recurse -Force }
if (-not $NoZip -and (Test-Path -LiteralPath $zipPath)) { Remove-Item -LiteralPath $zipPath -Force }

New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
Copy-Item -LiteralPath $installerExe -Destination (Join-Path $stageDir "OpenClawInstaller.exe") -Force
Copy-Item -LiteralPath $uninstallerExe -Destination (Join-Path $stageDir "OpenClawUninstaller.exe") -Force
Copy-Item -LiteralPath $templatesDir -Destination (Join-Path $stageDir "openclaw-templates") -Recurse -Force
$stageNodeDir = Join-Path $stageDir "node-v24.15.0"
New-Item -ItemType Directory -Path $stageNodeDir -Force | Out-Null
Copy-Item -LiteralPath $nodeZip64 -Destination (Join-Path $stageNodeDir "node-v24.15.0-win-x64.zip") -Force
Copy-Item -LiteralPath $nodeZip86 -Destination (Join-Path $stageNodeDir "node-v24.15.0-win-x86.zip") -Force
Copy-Item -LiteralPath $npmCacheDir -Destination (Join-Path $stageDir "openclaw-npm-cache") -Recurse -Force
Copy-Item -LiteralPath $skillsDir -Destination (Join-Path $stageDir "openclaw-skills") -Recurse -Force

if ($NoZip) {
    Write-Host "staged: $stageDir"
} else {
    Compress-Archive -LiteralPath $stageDir -DestinationPath $zipPath -Force
    Write-Host "packed: $zipPath"
}
