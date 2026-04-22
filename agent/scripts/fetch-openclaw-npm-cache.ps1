#Requires -Version 5.1
# 联网执行：灌满 openclaw-npm-cache（openclaw@2026.4.15），供 pack 与离线安装器使用。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cacheDir = Join-Path $scriptDir "openclaw-npm-cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

Write-Host "npm cache -> $cacheDir"
Write-Host "npm install -g openclaw@2026.4.15 (populates cache for offline use)"
npm install -g openclaw@2026.4.15 --cache $cacheDir
if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
Write-Host "OK. Next: pack-openclaw-installer-release.ps1"
