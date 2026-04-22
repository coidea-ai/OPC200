#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourcePs1 = Join-Path $scriptDir "openclaw-uninstaller.ps1"
$outDir = Join-Path $scriptDir "dist"
$outExe = Join-Path $outDir "OpenClawUninstaller.exe"

if (-not (Test-Path -LiteralPath $sourcePs1)) {
    throw "missing source script: $sourcePs1"
}

if (-not (Test-Path -LiteralPath $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

if (-not (Get-Module -ListAvailable -Name ps2exe)) {
    Install-Module -Name ps2exe -Scope CurrentUser -Force
}

Import-Module ps2exe -Force

Invoke-ps2exe `
    -inputFile $sourcePs1 `
    -outputFile $outExe `
    -iconFile "" `
    -noConsole:$false `
    -x64

Write-Host "built: $outExe"
