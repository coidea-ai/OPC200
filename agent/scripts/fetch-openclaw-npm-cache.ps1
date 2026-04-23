#Requires -Version 5.1
# 联网执行：灌满 openclaw-npm-cache（openclaw@2026.4.15），供 pack 与离线安装器使用。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cacheDir = Join-Path $scriptDir "openclaw-npm-cache"
New-Item -ItemType Directory -Force -Path $cacheDir | Out-Null

Write-Host "npm cache -> $cacheDir"
Write-Host "npm install -g openclaw@2026.4.15 (populates cache for offline use)"
$env:npm_config_cache = $cacheDir
$env:npm_config_registry = "https://registry.npmjs.org/"
try {
    npm install -g openclaw@2026.4.15 --no-fund 2>&1 | ForEach-Object { Write-Host $_ }
    $cacheItems = @(Get-ChildItem -LiteralPath $cacheDir -ErrorAction SilentlyContinue)
    if ($cacheItems.Count -eq 0) { throw "npm install failed: cache is empty after install" }
} finally {
    Remove-Item Env:\npm_config_cache -ErrorAction SilentlyContinue
    Remove-Item Env:\npm_config_registry -ErrorAction SilentlyContinue
}
Write-Host "OK (cache items: $($cacheItems.Count)). Next: pack-openclaw-installer-release.ps1"
