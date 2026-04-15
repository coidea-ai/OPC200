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
.PARAMETER PurgeOpenClaw
    勾选时才执行 OpenClaw 官方推荐卸载（openclaw uninstall --all --yes --non-interactive）；未勾选则不动 OpenClaw
.EXAMPLE
    .\uninstall.ps1
.EXAMPLE
    .\uninstall.ps1 -Silent -KeepData
.EXAMPLE
    .\uninstall.ps1 -Silent -PurgeOpenClaw
#>

param(
    [string]$InstallDir = "",
    [switch]$KeepData,
    [switch]$Silent,
    [switch]$PurgeOpenClaw
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:SERVICE_NAME = "OPC200-Agent"
$script:TASK_NAME    = "OPC200-Agent"
$script:ShouldPurgeOpenClaw = $false
$script:TotalSteps   = 3

function Write-Step { param([string]$M) Write-Host "[STEP] $M" -ForegroundColor Cyan }
function Write-Ok   { param([string]$M) Write-Host "  [OK] $M" -ForegroundColor Green }
function Write-Warn { param([string]$M) Write-Host " [WARN] $M" -ForegroundColor Yellow }
function Write-Err  { param([string]$M) Write-Host "  [ERR] $M" -ForegroundColor Red }

try {
    Write-Host ""
    Write-Host "OPC200 Agent Uninstaller" -ForegroundColor Cyan
    Write-Host ""

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

    # 交互式：询问是否卸载 OpenClaw；静默模式仅由 -PurgeOpenClaw 决定
    if ($Silent) {
        $script:ShouldPurgeOpenClaw = [bool]$PurgeOpenClaw
    }
    else {
        if ($PurgeOpenClaw) {
            $script:ShouldPurgeOpenClaw = $true
        }
        else {
            $ocConfirm = Read-Host "是否同时卸载 OpenClaw？(Y/N，默认 N)"
            if ($ocConfirm -eq "Y" -or $ocConfirm -eq "y") {
                $script:ShouldPurgeOpenClaw = $true
            }
        }
    }
    $script:TotalSteps = if ($script:ShouldPurgeOpenClaw) { 4 } else { 3 }

    # Step 1: 移除计划任务与旧版 Windows 服务
    Write-Step "1/$($script:TotalSteps) 移除自动启动"
    Unregister-ScheduledTask -TaskName $script:TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue
    Write-Ok "计划任务已移除 (若存在)"

    $svc = Get-Service -Name $script:SERVICE_NAME -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -eq "Running") {
            Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
        sc.exe delete $script:SERVICE_NAME | Out-Null
        Write-Ok "旧版 Windows 服务已删除"
    }

    # Step 2: 确认删除
    Write-Step "2/$($script:TotalSteps) 清理文件"
    if (-not (Test-Path $InstallDir)) {
        Write-Warn "目录 $InstallDir 不存在（可能已手动删除），跳过文件清理"
    }
    else {
        if (-not $Silent) {
            $confirm = Read-Host "确认删除 $InstallDir ? (Y/N)"
            if ($confirm -ne "Y" -and $confirm -ne "y") {
                Write-Warn "已取消"
                exit 0
            }
        }

        if ($KeepData) {
            $toRemove = @("bin", "config", "logs", "venv", ".env")
            foreach ($item in $toRemove) {
                $p = Join-Path $InstallDir $item
                if (Test-Path $p) {
                    Remove-Item $p -Recurse -Force
                    Write-Ok "已删除 $item"
                }
            }
            $ra = Join-Path $InstallDir "run-agent.ps1"
            if (Test-Path -LiteralPath $ra) {
                Remove-Item -LiteralPath $ra -Force
                Write-Ok "已删除 run-agent.ps1"
            }
            Write-Ok "data/ 已保留"
        }
        else {
            Remove-Item $InstallDir -Recurse -Force
            Write-Ok "目录已删除"
        }
    }

    # Step 3（可选）：在交互确认或 -PurgeOpenClaw 时执行官方文档推荐的卸载命令
    # 参考: https://docs.openclaw.ai/cli/uninstall
    if ($script:ShouldPurgeOpenClaw) {
        Write-Step "3/$($script:TotalSteps) 卸载 OpenClaw（官方 openclaw uninstall）"
        Write-Ok "进度 1/3：检查 openclaw 命令"
        $oc = Get-Command openclaw -ErrorAction SilentlyContinue
        if (-not $oc) {
            Write-Warn "未找到 openclaw 命令（PATH），跳过 OpenClaw 卸载"
        }
        else {
            try {
                Write-Ok "进度 2/3：执行 openclaw uninstall --all --yes --non-interactive"
                & openclaw uninstall --all --yes --non-interactive
                Write-Ok "进度 3/3：OpenClaw 官方卸载命令已执行"
                Write-Ok "已执行: openclaw uninstall --all --yes --non-interactive（CLI 全局包需自行 npm/pnpm 移除）"
            }
            catch {
                Write-Warn "OpenClaw 卸载命令失败（已忽略，OPC200 已清理）: $_"
            }
        }
    }

    # 最后一步
    Write-Step "$($script:TotalSteps)/$($script:TotalSteps) 卸载完成"
    Write-Host "  自动启动已处理；安装目录已清空或本就不存在。卸载结束。" -ForegroundColor Green
    Write-Host ""
    exit 0
}
catch {
    Write-Err "卸载失败: $_"
    exit 1
}
