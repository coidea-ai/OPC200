#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 卸载脚本 (v2)
.PARAMETER InstallDir
    安装目录 (默认 ~/.opc200)
.PARAMETER KeepData
    保留 data/ 目录
.PARAMETER Silent
    静默卸载（须配合 -KeepOpenClaw 明确表示是否保留 OpenClaw：传参=保留，不传=一并卸载）
.PARAMETER KeepOpenClaw
    保留本机 OpenClaw；不传时交互模式将**在开头**询问（必填）；静默模式不传则表示不保留并执行官方卸载
.EXAMPLE
    .\uninstall.ps1
.EXAMPLE
    .\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200" -KeepData
.EXAMPLE
    .\uninstall.ps1 -Silent -KeepOpenClaw
.EXAMPLE
    .\uninstall.ps1 -Silent
#>

param(
    [string]$InstallDir = "",
    [switch]$KeepData,
    [switch]$Silent,
    [switch]$KeepOpenClaw
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:SERVICE_NAME = "OPC200-Agent"
$script:TASK_NAME    = "OPC200-Agent"
$script:OPENCLAW_DEFAULT_GATEWAY_PORT = 18789
$script:KeepOpenClawChoice = $false
$script:TotalSteps   = 3

function Write-Step { param([string]$M) Write-Host "[STEP] $M" -ForegroundColor Cyan }
function Write-Ok   { param([string]$M) Write-Host "  [OK] $M" -ForegroundColor Green }
function Write-Warn { param([string]$M) Write-Host " [WARN] $M" -ForegroundColor Yellow }
function Write-Err  { param([string]$M) Write-Host "  [ERR] $M" -ForegroundColor Red }

function Sync-SessionPathFromRegistry {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $parts = @()
    if ($machinePath) { $parts += $machinePath }
    if ($userPath) { $parts += $userPath }
    if ($parts.Count -gt 0) {
        $env:Path = ($parts -join ";")
    }
}

function Resolve-KeepOpenClawChoice {
    param(
        [switch]$KeepOpenClawSwitch,
        [switch]$SilentMode
    )
    if ($KeepOpenClawSwitch) {
        $script:KeepOpenClawChoice = $true
        Write-Ok "已选择：保留 OpenClaw（命令行 -KeepOpenClaw）"
        return
    }
    if ($SilentMode) {
        $script:KeepOpenClawChoice = $false
        Write-Ok "静默模式：未指定 -KeepOpenClaw，将不保留 OpenClaw（若存在 CLI 则执行官方卸载）"
        return
    }
    Write-Host ""
    Write-Host "OpenClaw 是否与 OPC200 一并处理（必填）" -ForegroundColor Cyan
    do {
        $ans = Read-Host "是否保留本机已安装的 OpenClaw？(Y=保留 OpenClaw / N=全部卸载)"
        if ($null -eq $ans) { $ans = "" }
        $ans = "$ans".Trim()
        if ($ans -eq "Y" -or $ans -eq "y") {
            $script:KeepOpenClawChoice = $true
            Write-Ok "已选择：保留 OpenClaw"
            break
        }
        if ($ans -eq "N" -or $ans -eq "n") {
            $script:KeepOpenClawChoice = $false
            Write-Ok "已选择：将卸载 OpenClaw（在 OPC200 目录删除之后执行）"
            break
        }
        Write-Err "请输入 Y 或 N"
    } while ($true)
}

function Get-OpenClawGatewayPort {
    param([Parameter(Mandatory)][string]$ExePath)
    $gwPort = $script:OPENCLAW_DEFAULT_GATEWAY_PORT
    try {
        $raw = & $ExePath @("config", "get", "gateway.port") 2>$null
        $t = "$raw".Trim()
        if ($t.StartsWith('"') -and $t.EndsWith('"')) { $t = $t.Trim('"') }
        if ($t -match '^\d+$') { $gwPort = [int]$t }
    }
    catch { }
    return $gwPort
}

function Stop-OpenClawGatewayBeforeUninstall {
    param([Parameter(Mandatory)][string]$ExePath)
    $gwPort = Get-OpenClawGatewayPort -ExePath $ExePath
    Write-Ok "OpenClaw gateway 端口（配置或默认）: $gwPort"

    $rpcOk = $false
    try {
        $null = & $ExePath @("gateway", "status", "--json", "--require-rpc") 2>&1
        if ($LASTEXITCODE -eq 0) { $rpcOk = $true }
    }
    catch { }

    $listening = $false
    try {
        $conns = @(Get-NetTCPConnection -State Listen -LocalPort $gwPort -ErrorAction SilentlyContinue)
        if ($conns.Count -gt 0) { $listening = $true }
    }
    catch { }

    if (-not $rpcOk -and -not $listening) {
        Write-Ok "未发现运行中的 gateway（RPC 不可用且端口未监听），跳过 gateway stop"
        return
    }

    Write-Warn "正在停止 OpenClaw gateway（openclaw gateway stop）..."
    try {
        $null = & $ExePath @("gateway", "stop") 2>&1
    }
    catch {
        Write-Warn "gateway stop 调用异常: $_"
    }
    Start-Sleep -Seconds 2

    for ($i = 0; $i -lt 15; $i++) {
        $still = @()
        try {
            $still = @(Get-NetTCPConnection -State Listen -LocalPort $gwPort -ErrorAction SilentlyContinue)
        }
        catch { }
        if ($still.Count -eq 0) {
            Write-Ok "端口 $gwPort 已释放"
            return
        }
        Start-Sleep -Seconds 2
    }

    $final = @()
    try {
        $final = @(Get-NetTCPConnection -State Listen -LocalPort $gwPort -ErrorAction SilentlyContinue)
    }
    catch { }
    if ($final.Count -eq 0) {
        Write-Ok "端口 $gwPort 已释放"
        return
    }

    foreach ($c in $final) {
        $ownPid = $c.OwningProcess
        if (-not $ownPid) { continue }
        Write-Warn "强制结束仍占用端口 $gwPort 的进程 PID=$ownPid"
        Stop-Process -Id $ownPid -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 2
    Write-Ok "已尝试释放端口 $gwPort"
}

function Get-OpenClawConfigDirs {
    $dirs = New-Object System.Collections.Generic.List[string]
    if ($env:OPENCLAW_STATE_HOME) {
        $p = Join-Path $env:OPENCLAW_STATE_HOME ".openclaw"
        if (-not $dirs.Contains($p)) { $dirs.Add($p) }
    }
    if ($HOME) {
        $p = Join-Path $HOME ".openclaw"
        if (-not $dirs.Contains($p)) { $dirs.Add($p) }
    }
    if ($env:USERPROFILE) {
        $p = Join-Path $env:USERPROFILE ".openclaw"
        if (-not $dirs.Contains($p)) { $dirs.Add($p) }
    }
    return $dirs
}

try {
    Write-Host ""
    Write-Host "OPC200 Agent Uninstaller" -ForegroundColor Cyan
    Write-Host ""

    $principal = New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Err "请以管理员身份运行 PowerShell"
        exit 1
    }

    Resolve-KeepOpenClawChoice -KeepOpenClawSwitch:$KeepOpenClaw -SilentMode:$Silent

    if (-not $InstallDir) {
        $InstallDir = Join-Path $HOME ".opc200"
    }

    $script:TotalSteps = if ($script:KeepOpenClawChoice) { 3 } else { 4 }

    Write-Step "1/$($script:TotalSteps) 移除 OPC200 自动启动（计划任务 / 旧版服务）"
    Unregister-ScheduledTask -TaskName $script:TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue
    Write-Ok "计划任务已移除 (若存在)"

    $svc = Get-Service -Name $script:SERVICE_NAME -ErrorAction SilentlyContinue
    if ($svc) {
        if ($svc.Status -eq "Running") {
            Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 2
        }
        sc.exe delete $script:SERVICE_NAME | Out-Null
        Write-Ok "旧版 Windows 服务已删除 (若存在)"
    }

    Write-Step "2/$($script:TotalSteps) 清理 OPC200 安装目录"
    if (-not (Test-Path -LiteralPath $InstallDir)) {
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
                if (Test-Path -LiteralPath $p) {
                    Remove-Item -LiteralPath $p -Recurse -Force
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
            Remove-Item -LiteralPath $InstallDir -Recurse -Force
            Write-Ok "目录已删除"
        }
    }

    if (-not $script:KeepOpenClawChoice) {
        Write-Step "3/$($script:TotalSteps) 卸载 OpenClaw（先停 gateway，再执行官方卸载）"
        Sync-SessionPathFromRegistry
        Write-Ok "进度 1/6：检查 openclaw 命令"
        $oc = Get-Command openclaw -ErrorAction SilentlyContinue
        if (-not $oc) {
            Write-Warn "未找到 openclaw 命令（PATH），跳过 gateway 停止与官方卸载"
        }
        else {
            $exe = $oc.Source
            try {
                Write-Ok "进度 2/6：若 gateway 在运行则先停止并释放端口"
                Stop-OpenClawGatewayBeforeUninstall -ExePath $exe
                Write-Ok "进度 3/6：openclaw uninstall --all --yes --non-interactive"
                & $exe @("uninstall", "--all", "--yes", "--non-interactive")
                Write-Ok "OpenClaw 官方卸载命令已执行"
            }
            catch {
                Write-Warn "OpenClaw 卸载过程异常（OPC200 目录已按上文处理）: $_"
            }
        }
        Write-Ok "进度 4/6：sudo npm -g uninstall openclaw || true（Windows 等价命令）"
        $npmCmd = Get-Command npm -ErrorAction SilentlyContinue
        if ($npmCmd) {
            try {
                & $npmCmd.Source @("-g", "uninstall", "openclaw")
            }
            catch {
                Write-Warn "npm 全局卸载失败（已忽略）: $_"
            }
        }
        else {
            Write-Warn "未找到 npm 命令，跳过 npm 全局卸载"
        }
        Write-Ok "进度 5/6：复查 openclaw 命令是否仍可用"
        $ocAll = @(Get-Command openclaw -All -ErrorAction SilentlyContinue)
        if ($ocAll.Count -gt 0) {
            Write-Warn "检测到仍存在 openclaw 命令："
            foreach ($item in $ocAll) {
                Write-Host ("  - " + $item.Source) -ForegroundColor Yellow
            }
            Write-Warn "可继续执行以下命令清理残留："
            Write-Host "  npm -g uninstall openclaw" -ForegroundColor Yellow
            Write-Host "  if (Get-Command nvm -ErrorAction SilentlyContinue) { nvm list | Out-Null }" -ForegroundColor Yellow
            Write-Host "  # WSL/Linux 可再执行：for v in ~/.nvm/versions/node/*; do [ -x \"`$v/bin/npm\" ] && \"`$v/bin/npm\" -g uninstall openclaw || true; done" -ForegroundColor Yellow
            Write-Host "  Get-Command openclaw -All" -ForegroundColor Yellow
        }
        else {
            Write-Ok "未检测到残留 openclaw 命令"
        }
        Write-Ok "进度 6/6：删除 OpenClaw 配置目录（若存在）"
        $openclawDirs = @(Get-OpenClawConfigDirs)
        $removedAny = $false
        foreach ($openclawDir in $openclawDirs) {
            if (Test-Path -LiteralPath $openclawDir) {
                try {
                    Remove-Item -LiteralPath $openclawDir -Recurse -Force
                    Write-Ok "已删除 $openclawDir"
                    $removedAny = $true
                }
                catch {
                    Write-Warn "删除 $openclawDir 失败，请手动处理: $_"
                }
            }
        }
        if (-not $removedAny) {
            Write-Ok ("未发现配置目录，已检查: " + ($openclawDirs -join ", "))
        }
    }

    Write-Step "$($script:TotalSteps)/$($script:TotalSteps) 卸载完成"
    Write-Host "  OPC200 自动启动与安装目录已处理；OpenClaw 按你的选择保留或已尝试卸载。" -ForegroundColor Green
    Write-Host ""
    exit 0
}
catch {
    Write-Err "卸载失败: $_"
    exit 1
}
