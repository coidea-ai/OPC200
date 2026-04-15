#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 安装脚本 (v2)
.DESCRIPTION
    按 AGENT-001 (docs/INSTALL_SCRIPT_SPEC.md) 规范实现。
    流程: 环境检查 → 配置获取 → 下载 Agent → 安装部署 → 注册服务 → 启动验证 → 完成输出
.PARAMETER PlatformUrl
    平台端点地址 (默认 https://platform.opc200.co)
.PARAMETER CustomerId
    用户唯一标识
.PARAMETER ApiKey
    API 认证密钥
.PARAMETER InstallDir
    安装目录 (默认 ~/.opc200)
.PARAMETER Port
    本地服务端口 (默认 8080)
.PARAMETER Silent
    静默安装模式
.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -PlatformUrl "https://platform.opc200.co" -CustomerId "opc-001" -ApiKey "sk-xxx" -Silent
#>

param(
    [string]$PlatformUrl = "",
    [string]$CustomerId = "",
    [string]$ApiKey     = "",
    [string]$InstallDir = "",
    [int]$Port          = 8080,
    [switch]$Silent
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── 常量 ──────────────────────────────────────────────────────────

$script:AGENT_VERSION   = "2.3.0"
$script:DOWNLOAD_BASE   = "https://github.com/coidea-ai/OPC200/releases/download/v$($script:AGENT_VERSION)"
$script:AGENT_BINARY    = "opc-agent-windows-amd64.exe"
$script:CHECKSUM_FILE   = "SHA256SUMS"
$script:SERVICE_NAME    = "OPC200-Agent"
$script:SERVICE_DISPLAY = "OPC200 Agent Service"
$script:DEFAULT_URL     = "https://platform.opc200.co"
$script:MIN_WIN_BUILD   = [System.Version]"10.0.17763"   # Windows 10 1809
$script:MIN_DISK_GB     = 1

# 错误码 (AGENT-001 §6.1)
$script:E001 = 1   # 权限不足
$script:E002 = 2   # 网络连接失败
$script:E003 = 3   # 端口占用
$script:E004 = 4   # 校验失败
$script:E005 = 5   # 服务注册失败

# ── 辅助函数 ──────────────────────────────────────────────────────

function Write-Step  { param([string]$M) Write-Host "[STEP] $M" -ForegroundColor Cyan }
function Write-Ok    { param([string]$M) Write-Host "  [OK] $M" -ForegroundColor Green }
function Write-Warn  { param([string]$M) Write-Host " [WARN] $M" -ForegroundColor Yellow }
function Write-Err   { param([string]$M) Write-Host "  [ERR] $M" -ForegroundColor Red }

function Fail {
    param([int]$Code, [string]$M)
    Write-Err $M
    Invoke-Rollback
    exit $Code
}

# ── 回滚 ─────────────────────────────────────────────────────────

$script:RollbackActions = [System.Collections.ArrayList]::new()

function Register-Rollback {
    param([scriptblock]$Action)
    [void]$script:RollbackActions.Add($Action)
}

function Invoke-Rollback {
    if ($script:RollbackActions.Count -eq 0) { return }
    Write-Warn "正在回滚..."
    for ($i = $script:RollbackActions.Count - 1; $i -ge 0; $i--) {
        try { & $script:RollbackActions[$i] } catch { Write-Warn "回滚步骤失败: $_" }
    }
}

# ── Step 1: 环境检查 ─────────────────────────────────────────────

function Test-Environment {
    Write-Step "1/7 环境检查"

    # 管理员权限
    $principal = New-Object Security.Principal.WindowsPrincipal(
        [Security.Principal.WindowsIdentity]::GetCurrent()
    )
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Fail $script:E001 "E001: 请以管理员身份运行 PowerShell"
    }
    Write-Ok "管理员权限"

    # Windows 版本
    $osVer = [System.Version](Get-CimInstance Win32_OperatingSystem).Version
    if ($osVer -lt $script:MIN_WIN_BUILD) {
        Fail $script:E001 "E001: 需要 Windows 10 1809+ (当前 $osVer)"
    }
    Write-Ok "Windows $osVer"

    # 架构
    if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
        Fail $script:E001 "E001: 仅支持 x64 架构 (当前 $($env:PROCESSOR_ARCHITECTURE))"
    }
    Write-Ok "x64 架构"

    # 磁盘空间
    $drive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'"
    $freeGB = [math]::Round($drive.FreeSpace / 1GB, 2)
    if ($freeGB -lt $script:MIN_DISK_GB) {
        Fail $script:E001 "E001: 磁盘可用 ${freeGB}GB, 需要 ${script:MIN_DISK_GB}GB+"
    }
    Write-Ok "磁盘可用 ${freeGB}GB"

    # 端口占用
    $portInUse = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Fail $script:E003 "E003: 端口 $Port 被占用"
    }
    Write-Ok "端口 $Port 可用"
}

# ── Step 2: 获取配置 ─────────────────────────────────────────────

function Get-InstallConfig {
    Write-Step "2/7 获取配置"

    if ($Silent) {
        if (-not $PlatformUrl)  { $script:PlatformUrl = $script:DEFAULT_URL } else { $script:PlatformUrl = $PlatformUrl }
        if (-not $CustomerId)   { Fail $script:E001 "E001: 静默模式必须提供 -CustomerId" }
        if (-not $ApiKey)       { Fail $script:E001 "E001: 静默模式必须提供 -ApiKey" }
        $script:CustomerId = $CustomerId
        $script:ApiKey     = $ApiKey
    }
    else {
        $inputUrl = Read-Host "平台地址 [$($script:DEFAULT_URL)]"
        $script:PlatformUrl = if ($inputUrl) { $inputUrl } else { $script:DEFAULT_URL }

        do {
            $script:CustomerId = Read-Host "Customer ID (必需)"
            if (-not $script:CustomerId) { Write-Err "Customer ID 不能为空" }
        } while (-not $script:CustomerId)

        do {
            $sec = Read-Host "API Key (必需)" -AsSecureString
            $script:ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
            )
            if (-not $script:ApiKey) { Write-Err "API Key 不能为空" }
        } while (-not $script:ApiKey)
    }

    # 安装目录
    if ($InstallDir) {
        $script:InstallRoot = $InstallDir
    }
    else {
        $script:InstallRoot = Join-Path $HOME ".opc200"
    }

    Write-Ok "平台: $($script:PlatformUrl)"
    Write-Ok "用户: $($script:CustomerId)"
    Write-Ok "目录: $($script:InstallRoot)"
}

# ── Step 3: 下载 Agent ───────────────────────────────────────────

function Get-AgentBinary {
    Write-Step "3/7 下载 Agent"

    $binUrl  = "$($script:DOWNLOAD_BASE)/$($script:AGENT_BINARY)"
    $shaUrl  = "$($script:DOWNLOAD_BASE)/$($script:CHECKSUM_FILE)"
    $tmpDir  = Join-Path $env:TEMP "opc200-install"
    $binDest = Join-Path $tmpDir $script:AGENT_BINARY
    $shaDest = Join-Path $tmpDir $script:CHECKSUM_FILE

    if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
    New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

    try {
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $binUrl -OutFile $binDest -UseBasicParsing
        Write-Ok "已下载 $($script:AGENT_BINARY)"
    }
    catch {
        Fail $script:E002 "E002: 下载失败 - $_"
    }

    # SHA256 校验
    try {
        Invoke-WebRequest -Uri $shaUrl -OutFile $shaDest -UseBasicParsing
        $expectedHash = (Get-Content $shaDest | Where-Object { $_ -match $script:AGENT_BINARY } | ForEach-Object { ($_ -split '\s+')[0] })
        if ($expectedHash) {
            $actualHash = (Get-FileHash -Path $binDest -Algorithm SHA256).Hash.ToLower()
            if ($actualHash -ne $expectedHash.ToLower()) {
                Fail $script:E004 "E004: SHA256 校验失败 (期望 $expectedHash, 实际 $actualHash)"
            }
            Write-Ok "SHA256 校验通过"
        }
        else {
            Write-Warn "SHA256SUMS 中未找到对应条目，跳过校验"
        }
    }
    catch {
        Write-Warn "无法下载 SHA256SUMS，跳过校验"
    }

    $script:TmpBinary = $binDest
}

# ── Step 4: 安装部署 ─────────────────────────────────────────────

function Install-Agent {
    Write-Step "4/7 安装部署"

    $root = $script:InstallRoot

    # 目录结构 (AGENT-001 §3.1)
    $dirs = @(
        $root,
        (Join-Path $root "bin"),
        (Join-Path $root "config"),
        (Join-Path $root "data"),
        (Join-Path $root "data\exporter"),
        (Join-Path $root "logs")
    )

    foreach ($d in $dirs) {
        if (-not (Test-Path $d)) {
            New-Item -ItemType Directory -Path $d -Force | Out-Null
        }
    }

    Register-Rollback {
        if (Test-Path $root) { Remove-Item $root -Recurse -Force -ErrorAction SilentlyContinue }
    }

    Write-Ok "目录结构已创建"

    # 复制二进制
    $agentDest = Join-Path $root "bin\opc-agent.exe"
    Copy-Item -Path $script:TmpBinary -Destination $agentDest -Force
    Write-Ok "Agent 二进制已部署"

    # config.yml (AGENT-001 §3.2)
    $configYml = @"
platform:
  url: "$($script:PlatformUrl)"
  metrics_endpoint: "/metrics/job"

customer:
  id: "$($script:CustomerId)"

agent:
  version: "$($script:AGENT_VERSION)"
  check_interval: 60
  push_interval: 30

gateway:
  host: "127.0.0.1"
  port: $Port

journal:
  storage_path: "$($root -replace '\\','/')/data/journal"
  max_size: "1GB"

logging:
  level: "info"
  file: "$($root -replace '\\','/')/logs/agent.log"
  max_size: "100MB"
  max_backups: 5
"@
    $configPath = Join-Path $root "config\config.yml"
    [System.IO.File]::WriteAllText($configPath, $configYml, [System.Text.UTF8Encoding]::new($false))
    Write-Ok "config.yml 已写入"

    # .env (权限受限)
    $envPath = Join-Path $root ".env"
    [System.IO.File]::WriteAllText($envPath, "OPC200_API_KEY=$($script:ApiKey)`n", [System.Text.UTF8Encoding]::new($false))

    $acl = Get-Acl $envPath
    $acl.SetAccessRuleProtection($true, $false)
    $rule = New-Object System.Security.AccessControl.FileSystemAccessRule(
        [System.Security.Principal.WindowsIdentity]::GetCurrent().Name,
        "FullControl", "Allow"
    )
    $acl.AddAccessRule($rule)
    Set-Acl -Path $envPath -AclObject $acl
    Write-Ok ".env 已写入 (权限受限)"

    $script:AgentExe  = $agentDest
    $script:ConfigYml = $configPath
}

# ── Step 5: 注册系统服务 ─────────────────────────────────────────

function Register-Service {
    Write-Step "5/7 注册系统服务"

    $existing = Get-Service -Name $script:SERVICE_NAME -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Warn "服务已存在，先停止并删除"
        Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
        sc.exe delete $script:SERVICE_NAME | Out-Null
        Start-Sleep -Seconds 2
    }

    $binPath = "`"$($script:AgentExe)`" --config `"$($script:ConfigYml)`" service run"
    $result  = sc.exe create $script:SERVICE_NAME `
        binPath= $binPath `
        DisplayName= $script:SERVICE_DISPLAY `
        start= auto `
        obj= "NT AUTHORITY\LocalService" 2>&1

    if ($LASTEXITCODE -ne 0) {
        Fail $script:E005 "E005: 服务注册失败 - $result"
    }

    Register-Rollback {
        Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
        sc.exe delete $script:SERVICE_NAME 2>&1 | Out-Null
    }

    Write-Ok "服务 $($script:SERVICE_NAME) 已注册 (自动启动)"
}

# ── Step 6: 启动验证 ─────────────────────────────────────────────

function Start-AndVerify {
    Write-Step "6/7 启动验证"

    try {
        Start-Service -Name $script:SERVICE_NAME -ErrorAction Stop
    }
    catch {
        Fail $script:E005 "E005: 服务启动失败 - $_"
    }

    Start-Sleep -Seconds 2
    $svc = Get-Service -Name $script:SERVICE_NAME
    if ($svc.Status -ne "Running") {
        Fail $script:E005 "E005: 服务状态异常 ($($svc.Status))"
    }
    Write-Ok "服务已启动"

    # 健康检查
    $healthUrl = "http://127.0.0.1:$Port/health"
    $healthy   = $false
    for ($i = 1; $i -le 10; $i++) {
        try {
            $resp = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
            if ($resp.StatusCode -eq 200) { $healthy = $true; break }
        }
        catch { Start-Sleep -Seconds 2 }
    }

    if ($healthy) {
        Write-Ok "健康检查通过 ($healthUrl)"
    }
    else {
        Write-Warn "健康检查超时，Agent 可能仍在启动中"
    }
}

# ── Step 7: 完成输出 ─────────────────────────────────────────────

function Show-Summary {
    Write-Step "7/7 安装完成"

    $root = $script:InstallRoot
    Write-Host ""
    Write-Host "  安装目录 : $root" -ForegroundColor Cyan
    Write-Host "  配置文件 : $root\config\config.yml" -ForegroundColor Cyan
    Write-Host "  日志文件 : $root\logs\agent.log" -ForegroundColor Cyan
    Write-Host "  服务名称 : $($script:SERVICE_NAME)" -ForegroundColor Cyan
    Write-Host "  健康检查 : http://127.0.0.1:$Port/health" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  查看状态 : Get-Service $($script:SERVICE_NAME)" -ForegroundColor Gray
    Write-Host "  查看日志 : Get-Content '$root\logs\agent.log' -Tail 50" -ForegroundColor Gray
    Write-Host "  卸载     : .\uninstall.ps1 -InstallDir '$root'" -ForegroundColor Gray
    Write-Host ""
}

# ── 主流程 ────────────────────────────────────────────────────────

function Main {
    Write-Host "`nOPC200 Agent Installer v$($script:AGENT_VERSION) (Windows)`n" -ForegroundColor Cyan

    Test-Environment
    Get-InstallConfig
    Get-AgentBinary
    Install-Agent
    Register-Service
    Start-AndVerify
    Show-Summary

    return 0
}

$exitCode = Main
exit $exitCode
