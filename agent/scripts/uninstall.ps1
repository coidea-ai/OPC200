#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 卸载脚本 (v2)
.PARAMETER InstallDir
    安装目录 (默认 ~/.opc200)
.PARAMETER KeepData
    保留 data/ 目录
.PARAMETER Silent
    静默卸载
.EXAMPLE
    .\uninstall.ps1
.EXAMPLE
    .\uninstall.ps1 -Silent -KeepData
#>

param(
    [string]$InstallDir = "",
    [switch]$KeepData,
    [switch]$Silent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:SERVICE_NAME = "OPC200-Agent"

function Write-Step { param([string]$M) Write-Host "[STEP] $M" -ForegroundColor Cyan }
function Write-Ok   { param([string]$M) Write-Host "  [OK] $M" -ForegroundColor Green }
function Write-Warn { param([string]$M) Write-Host " [WARN] $M" -ForegroundColor Yellow }
function Write-Err  { param([string]$M) Write-Host "  [ERR] $M" -ForegroundColor Red }

try {
    Write-Host "`nOPC200 Agent Uninstaller`n" -ForegroundColor Cyan

    # 管理员检查
    $principal = New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Err "请以管理员身份运行 PowerShell"
        exit 1
    }

    # 确定目录
    if (-not $InstallDir) {
        $InstallDir = Join-Path $HOME ".opc200"
    }

    # Step 1: 停止并删除服务
    Write-Step "1/3 移除服务"
    $svc = Get-Service -Name $script:SERVICE_NAME -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -eq "Running") {
            Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
        sc.exe delete $script:SERVICE_NAME | Out-Null
        Write-Ok "服务 $($script:SERVICE_NAME) 已删除"
    }
    else {
        Write-Warn "服务不存在，跳过"
    }

    # Step 2: 确认删除
    Write-Step "2/3 清理文件"
    if (-not (Test-Path $InstallDir)) {
        Write-Warn "目录 $InstallDir 不存在"
        exit 0
    }

    if (-not $Silent) {
        $confirm = Read-Host "确认删除 $InstallDir ? (Y/N)"
        if ($confirm -ne "Y" -and $confirm -ne "y") {
            Write-Warn "已取消"
            exit 0
        }
    }

    if ($KeepData) {
        $toRemove = @("bin", "config", "logs", ".env")
        foreach ($item in $toRemove) {
            $p = Join-Path $InstallDir $item
            if (Test-Path $p) {
                Remove-Item $p -Recurse -Force
                Write-Ok "已删除 $item"
            }
        }
        Write-Ok "data/ 已保留"
    }
    else {
        Remove-Item $InstallDir -Recurse -Force
        Write-Ok "目录已删除"
    }

    # Step 3: 完成
    Write-Step "3/3 卸载完成"
    Write-Host ""
    exit 0
}
catch {
    Write-Err "卸载失败: $_"
    exit 1
}
