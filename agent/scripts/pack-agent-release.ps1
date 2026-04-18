#Requires -Version 5.1
<#
.SYNOPSIS
    Build opc200-agent-<version>.zip + SHA256SUMS for GitHub Release (local).
#>
param(
    [string]$Version = "",
    [string]$OutputDir = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
if (-not $OutputDir) { $OutputDir = Join-Path $RepoRoot "dist" }
$null = New-Item -ItemType Directory -Force -Path $OutputDir

if (-not $Version) {
    $vf = Join-Path $RepoRoot "VERSION"
    if (Test-Path -LiteralPath $vf) {
        $Version = (Get-Content -LiteralPath $vf -Raw).Trim()
    }
}
if (-not $Version) { throw "Version required or VERSION file missing" }

$stage = Join-Path $env:TEMP ("opc200-bundle-" + [guid]::NewGuid().ToString("n"))
$agentStage = Join-Path $stage "agent"
try {
    New-Item -ItemType Directory -Force -Path (Join-Path $agentStage "src") | Out-Null
    Copy-Item -Recurse -Force (Join-Path $RepoRoot "agent\src\opc_agent") (Join-Path $agentStage "src\opc_agent")
    Copy-Item -Recurse -Force (Join-Path $RepoRoot "agent\src\exporter") (Join-Path $agentStage "src\exporter")
    Copy-Item -Recurse -Force (Join-Path $RepoRoot "agent\scripts") (Join-Path $agentStage "scripts")
    $stub = @"
"""Minimal package root for standalone agent bundle (no monorepo src.* imports)."""
__version__ = "$Version"
"@
    Set-Content -LiteralPath (Join-Path $agentStage "src\__init__.py") -Value $stub -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $agentStage "__init__.py") -Value '"""OPC200 agent bundle."""' -Encoding UTF8

    $zipName = "opc200-agent-$Version.zip"
    $zipPath = Join-Path $OutputDir $zipName
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path $agentStage -DestinationPath $zipPath -CompressionLevel Optimal

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
    $sumFile = Join-Path $OutputDir "SHA256SUMS"
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($sumFile, "$hash  $zipName`n", $utf8NoBom)
    Write-Host "OK: $zipPath"
    Write-Host $sumLine
}
finally {
    if (Test-Path -LiteralPath $stage) { Remove-Item -LiteralPath $stage -Recurse -Force -ErrorAction SilentlyContinue }
}
