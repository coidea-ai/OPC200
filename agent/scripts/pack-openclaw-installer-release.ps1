#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$distDir = Join-Path $scriptDir "dist"
$stageDir = Join-Path $distDir "OpenClawInstaller"
$zipPath = Join-Path $distDir "OpenClawInstaller.zip"

$installerExe = Join-Path $distDir "OpenClawInstaller.exe"
$uninstallerExe = Join-Path $distDir "OpenClawUninstaller.exe"
$releaseDir = Join-Path $scriptDir "openclaw-releases"
$templatesDir = Join-Path $scriptDir "openclaw-templates"
$nodeOfflineDir = Join-Path $scriptDir "node-v22.22.2"
$nodeZip64 = Join-Path $nodeOfflineDir "node-v22.22.2-win-x64.zip"
$nodeZip86 = Join-Path $nodeOfflineDir "node-v22.22.2-win-x86.zip"

if (-not (Test-Path -LiteralPath $installerExe)) { throw "missing exe: $installerExe" }
if (-not (Test-Path -LiteralPath $uninstallerExe)) { throw "missing exe: $uninstallerExe" }
if (-not (Test-Path -LiteralPath $releaseDir)) { throw "missing dir: $releaseDir" }
if (-not (Test-Path -LiteralPath $templatesDir)) { throw "missing dir: $templatesDir" }
if (-not (Test-Path -LiteralPath $nodeOfflineDir)) { throw "missing dir: $nodeOfflineDir (offline Node bundles required next to pack script)" }
if (-not (Test-Path -LiteralPath $nodeZip64)) { throw "missing file: $nodeZip64" }
if (-not (Test-Path -LiteralPath $nodeZip86)) { throw "missing file: $nodeZip86" }

if (Test-Path -LiteralPath $stageDir) { Remove-Item -LiteralPath $stageDir -Recurse -Force }
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }

New-Item -ItemType Directory -Path $stageDir -Force | Out-Null
Copy-Item -LiteralPath $installerExe -Destination (Join-Path $stageDir "OpenClawInstaller.exe") -Force
Copy-Item -LiteralPath $uninstallerExe -Destination (Join-Path $stageDir "OpenClawUninstaller.exe") -Force
Copy-Item -LiteralPath $releaseDir -Destination (Join-Path $stageDir "openclaw-releases") -Recurse -Force
Copy-Item -LiteralPath $templatesDir -Destination (Join-Path $stageDir "openclaw-templates") -Recurse -Force
Copy-Item -LiteralPath $nodeOfflineDir -Destination (Join-Path $stageDir "node-v22.22.2") -Recurse -Force

Compress-Archive -LiteralPath $stageDir -DestinationPath $zipPath -Force
Write-Host "packed: $zipPath"
