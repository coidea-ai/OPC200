#Requires -Version 5.1
<#
.SYNOPSIS
    将 opc-agent CLI 打成单文件 exe（需已安装 Python 3.10+、PyInstaller）。
.DESCRIPTION
    产物名与 install.ps1 默认下载名一致: opc-agent-windows-amd64.exe
    用法: 在仓库根目录执行 .\agent\scripts\build-windows-exe.ps1
#>

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $RepoRoot

$env:PYTHONPATH = $RepoRoot

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "Installing PyInstaller..." -ForegroundColor Cyan
    python -m pip install pyinstaller
}

$Entry = Join-Path $RepoRoot "agent\src\opc_agent\cli.py"
$OutName = "opc-agent-windows-amd64"

pyinstaller --noconfirm --clean --onefile `
    --name $OutName `
    --paths $RepoRoot `
    --hidden-import agent.src.exporter.collector `
    --hidden-import agent.src.exporter.pusher `
    --hidden-import yaml `
    --collect-submodules agent.src `
    $Entry

Write-Host "Done: dist\$OutName.exe" -ForegroundColor Green
Write-Host "联调: install.ps1 -LocalBinary `"$RepoRoot\dist\$OutName.exe`" ..." -ForegroundColor Cyan
