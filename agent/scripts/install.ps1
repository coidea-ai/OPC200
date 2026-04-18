#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 安装脚本 (v2)
.DESCRIPTION
    按 AGENT-001 (docs/INSTALL_SCRIPT_SPEC.md) 规范实现。
    流程: 环境检测 → OpenClaw 安装与配置 → OPC200 Agent (venv) → 计划任务 → 验证
.PARAMETER OPC200PlatformUrl
    OPC200 平台端点（第三部分；静默必填时可省略则用默认）
.PARAMETER OPC200TenantId
    OPC200 租户 ID（第三部分；静默必填，亦可由环境变量 OPC200_TENANT_ID 提供）
.PARAMETER OPC200ApiKey
    OPC200 平台 ApiKey；若已在 OpenClaw 步骤填写模型密钥则复用，无需再传
.PARAMETER InstallDir
    安装目录 (默认 ~/.opc200)
.PARAMETER OPC200Port
    OPC200 Agent 本地 HTTP 端口 (默认 8080)
.PARAMETER Silent
    静默安装模式
.PARAMETER RepoRoot
    OPC200 仓库根目录（含 agent/、src/）；默认为本脚本所在位置的 ..\..
.PARAMETER OpenClawOnboard
    显式要求执行 onboard（静默时常用）。交互安装默认即会执行，一般无需再传。
.PARAMETER SkipOpenClawOnboard
    跳过 OpenClaw 首次配置（交互默认会做；设 OPENCLAW_ONBOARD=0 亦可关闭）
.PARAMETER OpenClawAuthChoice
    与 OPENCLAW_AUTH_CHOICE 一致：apiKey | openai-api-key | gemini-api-key | custom-api-key（不再支持 skip）
.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -Silent -OPC200PlatformUrl "https://platform.opc200.co" -OPC200TenantId "opc-001" -OPC200ApiKey "sk-xxx"
#>

param(
    [string]$OPC200PlatformUrl = "",
    [string]$OPC200TenantId = "",
    [string]$OPC200ApiKey     = "",
    [string]$InstallDir = "",
    [int]$OPC200Port          = 8080,
    [switch]$Silent,
    [string]$RepoRoot   = "",
    [switch]$OpenClawOnboard,
    [switch]$SkipOpenClawOnboard,
    [string]$OpenClawAuthChoice = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── 常量 ──────────────────────────────────────────────────────────

$script:AGENT_VERSION   = "2.5.0"
$script:SERVICE_NAME    = "OPC200-Agent"
$script:SERVICE_DISPLAY = "OPC200 Agent Service"
$script:TASK_NAME       = "OPC200-Agent"
$script:DEFAULT_URL     = "https://platform.opc200.co"
$script:OPENCLAW_DEFAULT_INSTALL_URL    = "https://openclaw.ai/install.ps1"
$script:OPENCLAW_MIN_NODE_MAJOR         = 22
$script:NODEJS_DIST_INDEX               = "https://nodejs.org/dist/index.json"
$script:OPENCLAW_ALLOWED_HOSTS          = @("openclaw.ai", "www.openclaw.ai")
$script:OPENCLAW_DEFAULT_NPM_REGISTRY   = "https://registry.npmmirror.com/"
$script:OPENCLAW_INSTALL_TIMEOUT_SEC    = 900   # 15 分钟
$script:OPENCLAW_NET_CHECK_HOSTS        = @("openclaw.ai", "registry.npmmirror.com", "github.com")
$script:OPENCLAW_DEFAULT_PROFILE_DIR = Join-Path $HOME ".openclaw"
$script:OPENCLAW_DEFAULT_SKILLS = "skill-vetter"
$script:OPENCLAW_DEFAULT_SKILL_INSTALL_CMD = "openclaw skills install"
$script:OPENCLAW_DEFAULT_GATEWAY_PORT      = 18789
$script:OPENCLAW_ONBOARD_TIMEOUT_SEC      = 600
$script:OPENCLAW_GW_INSTALL_MAX_RETRY     = 3
$script:OPENCLAW_GATEWAY_WARMUP_MAX_TRIES  = 25
$script:OPENCLAW_GATEWAY_WARMUP_SLEEP_SEC  = 2
$script:MIN_WIN_BUILD   = [System.Version]"10.0.17763"   # Windows 10 1809
$script:MIN_DISK_GB     = 1

# 错误码 (AGENT-001 §6.1)
$script:E001 = 1   # 权限不足
$script:E002 = 2   # 网络连接失败
$script:E003 = 3   # 端口占用
$script:E004 = 4   # 校验失败
$script:E005 = 5   # 服务注册失败

$script:RepoRootResolved = ""
$script:RunAgentScript  = ""
$script:PlatformUrl     = ""
$script:TenantId        = ""
$script:ApiKey          = ""
$script:InstallRoot     = ""

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

function Get-NodeJsMajorVersion {
    $exeList = [System.Collections.Generic.List[string]]::new()
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) { [void]$exeList.Add($cmd.Source) }
    $pf = Join-Path $env:ProgramFiles "nodejs\node.exe"
    if (Test-Path -LiteralPath $pf) { [void]$exeList.Add($pf) }
    $pfx86 = ${env:ProgramFiles(x86)}
    if ($pfx86) {
        $pf86 = Join-Path $pfx86 "nodejs\node.exe"
        if (Test-Path -LiteralPath $pf86) { [void]$exeList.Add($pf86) }
    }
    foreach ($exe in ($exeList | Select-Object -Unique)) {
        try {
            $verLine = & $exe -v 2>&1 | Select-Object -First 1
            if (-not $verLine) { continue }
            $verStr = "$verLine".Trim()
            $m = [regex]::Match($verStr, '^v(\d+)')
            if ($m.Success) {
                return [int]$m.Groups[1].Value
            }
        }
        catch { }
    }
    return 0
}

function Install-NodeJsWinMsiFromDist {
    $ProgressPreference = "SilentlyContinue"
    $index = Invoke-RestMethod -Uri $script:NODEJS_DIST_INDEX -UseBasicParsing
    $best = $null
    $bestVer = $null
    foreach ($entry in $index) {
        if ($entry.files -notcontains "win-x64-msi") { continue }
        if ($entry.version -notmatch '^v(\d+)\.(\d+)\.(\d+)$') { continue }
        $major = [int]$Matches[1]
        if ($major -lt $script:OPENCLAW_MIN_NODE_MAJOR) { continue }
        $verObj = [version]::new([int]$Matches[1], [int]$Matches[2], [int]$Matches[3])
        if ($null -eq $bestVer -or $verObj -gt $bestVer) {
            $bestVer = $verObj
            $best = $entry
        }
    }
    if (-not $best) {
        Fail $script:E002 "E002: nodejs.org 索引中未找到 Node $($script:OPENCLAW_MIN_NODE_MAJOR)+ 的 win-x64 MSI"
    }
    $v = $best.version
    $msiUrl = "https://nodejs.org/dist/$v/node-$v-x64.msi"
    $msi = Join-Path $env:TEMP ("opc200-node-" + [Guid]::NewGuid().ToString("N") + ".msi")
    Write-Ok "下载 Node MSI: $msiUrl"
    Invoke-WebRequest -Uri $msiUrl -OutFile $msi -UseBasicParsing
    Write-Ok "msiexec 静默安装 Node（可能需要数十秒）..."
    $p = Start-Process -FilePath "msiexec.exe" -ArgumentList @("/i", $msi, "/qn", "/norestart") -Wait -PassThru
    Remove-Item -LiteralPath $msi -Force -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0 -and $p.ExitCode -ne 3010) {
        Fail $script:E002 "E002: Node MSI 安装失败 (msiexec 退出码 $($p.ExitCode))"
    }
}

function Ensure-OpenClawNodeRuntime {
    Write-Step "3/15 准备 Node.js（OpenClaw 需要 v$($script:OPENCLAW_MIN_NODE_MAJOR)+）"

    Sync-SessionPathFromRegistry
    $maj = Get-NodeJsMajorVersion
    if ($maj -ge $script:OPENCLAW_MIN_NODE_MAJOR) {
        Write-Ok "Node.js 主版本 $maj 已满足要求"
        return
    }

    if ($maj -gt 0) {
        Write-Warn "当前 Node 主版本为 $maj，需要 $($script:OPENCLAW_MIN_NODE_MAJOR)+；将尝试升级"
    }
    else {
        Write-Warn "未在 PATH 或默认目录检测到 Node.js，将尝试安装"
    }

    $wg = Get-Command winget -ErrorAction SilentlyContinue
    if ($wg) {
        Write-Ok "尝试 winget (OpenJS.NodeJS)..."
        try {
            $wingetArgs = @("install", "-e", "--id", "OpenJS.NodeJS", "--accept-package-agreements", "--accept-source-agreements", "--silent")
            if ($maj -gt 0) {
                $wingetArgs = @("upgrade", "-e", "--id", "OpenJS.NodeJS", "--accept-package-agreements", "--accept-source-agreements", "--silent")
            }
            Start-Process -FilePath "winget.exe" -ArgumentList $wingetArgs -Wait -NoNewWindow
        }
        catch { }
    }

    Sync-SessionPathFromRegistry
    $maj = Get-NodeJsMajorVersion
    if ($maj -ge $script:OPENCLAW_MIN_NODE_MAJOR) {
        Write-Ok "Node.js 已通过 winget 就绪（主版本 $maj）"
        return
    }

    Write-Warn "winget 未能提供 Node $($script:OPENCLAW_MIN_NODE_MAJOR)+，改从 nodejs.org 安装 MSI"
    Install-NodeJsWinMsiFromDist
    Sync-SessionPathFromRegistry
    $maj = Get-NodeJsMajorVersion
    if ($maj -ge $script:OPENCLAW_MIN_NODE_MAJOR) {
        Write-Ok "Node.js MSI 安装完成（主版本 $maj）"
        return
    }

    Fail $script:E002 "E002: 无法使 Node.js 达到 v$($script:OPENCLAW_MIN_NODE_MAJOR)+。请从 https://nodejs.org 安装后关闭并重新打开 PowerShell，再运行本安装程序。"
}

# ── Step 1: 环境检查 ─────────────────────────────────────────────

function Test-Environment {
    Write-Step "1/15 环境检查"

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
        Fail $script:E001 "E001: 磁盘可用 ${freeGB}GB, 需要 $($script:MIN_DISK_GB)GB+"
    }
    Write-Ok "磁盘可用 ${freeGB}GB"

    # 端口占用
    $portInUse = Get-NetTCPConnection -LocalPort $OPC200Port -ErrorAction SilentlyContinue
    if ($portInUse) {
        Fail $script:E003 "E003: 端口 $OPC200Port 被占用"
    }
    Write-Ok "端口 $OPC200Port 可用"

    $cli = Join-Path $script:RepoRootResolved "agent\src\opc_agent\cli.py"
    if (-not (Test-Path -LiteralPath $cli)) {
        Fail $script:E001 "E001: 非 OPC200 仓库根目录: $($script:RepoRootResolved)（请用 -RepoRoot 或在克隆仓库内执行）"
    }
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pyCmd) { Fail $script:E001 "E001: 未找到 python/python3" }
    if ($pyCmd.Source -like "*\AppData\Local\Microsoft\WindowsApps\python*.exe") {
        Fail $script:E001 "E001: 当前仅检测到 WindowsApps Python 占位符，请先安装真实 Python 3.10+（建议 python.org 或 winget）"
    }
    $pyExe = $pyCmd.Source
    $verRaw = & $pyExe -c "import sys; print('{}.{}'.format(sys.version_info[0], sys.version_info[1]))" 2>&1 | Select-Object -First 1
    $verText = if ($null -eq $verRaw) { "" } else { "$verRaw".Trim() }
    $m = [regex]::Match($verText, '\d+\.\d+')
    $ver = if ($m.Success) { $m.Value } else { "" }
    if (-not $ver) {
        Fail $script:E001 "E001: 无法解析 Python 版本（当前输出: $verText）"
    }
    $parts = $ver -split '\.'
    if ($parts.Count -lt 2) {
        Fail $script:E001 "E001: Python 版本格式异常（当前 $ver）"
    }
    if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
        Fail $script:E001 "E001: 需要 Python 3.10+（当前 $ver）"
    }
    Write-Ok "Python 与源码: $($pyCmd.Source)；$($script:RepoRootResolved)"
}

function Initialize-InstallPaths {
    Write-Step "2/15 安装目录"
    if ($InstallDir) {
        $script:InstallRoot = $InstallDir.Trim()
    }
    else {
        $script:InstallRoot = Join-Path $HOME ".opc200"
    }
    Write-Ok "InstallRoot: $($script:InstallRoot)"
}

function Get-OpcAgentPlatformConfig {
    Write-Step "10/15 平台与租户 (OPC200 Agent)"

    if ($Silent) {
        if ($OPC200PlatformUrl) { $script:PlatformUrl = $OPC200PlatformUrl } else { $script:PlatformUrl = $script:DEFAULT_URL }
        $tid = $OPC200TenantId
        if ([string]::IsNullOrWhiteSpace($tid) -and $env:OPC200_TENANT_ID) { $tid = $env:OPC200_TENANT_ID.Trim() }
        if ([string]::IsNullOrWhiteSpace($tid)) { Fail $script:E001 "E001: 静默须 -OPC200TenantId 或环境变量 OPC200_TENANT_ID" }
        $script:TenantId = $tid
        if (-not $script:ApiKey) {
            if ($OPC200ApiKey) { $script:ApiKey = $OPC200ApiKey }
            elseif ($env:OPC200_API_KEY) { $script:ApiKey = $env:OPC200_API_KEY }
            else { Fail $script:E001 "E001: 静默须 OPC200 平台 ApiKey：OpenClaw 已填模型密钥，或 -OPC200ApiKey，或 OPC200_API_KEY" }
        }
    }
    else {
        $inputUrl = Read-Host "平台地址 [$($script:DEFAULT_URL)]"
        $script:PlatformUrl = if ($inputUrl) { $inputUrl } else { $script:DEFAULT_URL }
        do {
            $script:TenantId = Read-Host "租户 ID (Tenant ID，必需)"
            if (-not $script:TenantId) { Write-Err "不能为空" }
        } while (-not $script:TenantId)
        if (-not $script:ApiKey) {
            $script:ApiKey = Read-SecureLineNonEmpty -Prompt "平台 API Key (OpenClaw 未采集密钥时必填)"
        }
        else {
            Write-Ok "已复用 OpenClaw 阶段的密钥作为平台 ApiKey"
        }
    }
    Write-Ok "平台: $($script:PlatformUrl) | Tenant: $($script:TenantId)"
}

# ── 网络预检 ─────────────────────────────────────────────────────

function Test-OpenClawNetworkReady {
    Write-Step "4/15 网络连通性预检"
    $allOk = $true
    foreach ($netHost in $script:OPENCLAW_NET_CHECK_HOSTS) {
        try {
            $result = Test-NetConnection -ComputerName $netHost -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
            if ($result) {
                Write-Ok "可达: $netHost"
            }
            else {
                Write-Warn "不可达: $netHost（安装可能变慢或失败）"
                $allOk = $false
            }
        }
        catch {
            Write-Warn "检测失败: $netHost - $_"
            $allOk = $false
        }
    }
    if (-not $allOk) {
        Write-Warn "部分主机不可达；若安装超时，请检查网络或稍后重试"
    }
}

# ── Step 3: 官方渠道安装 OpenClaw latest ─────────────────────────

function Install-OpenClawOfficial {
    Write-Step "5/15 官方渠道安装 OpenClaw latest"

    # 允许通过环境变量覆写安装入口，但必须经过官方域名白名单校验。
    $installUrl = if ($env:OPENCLAW_INSTALL_URL) { $env:OPENCLAW_INSTALL_URL } else { $script:OPENCLAW_DEFAULT_INSTALL_URL }
    $channel = if ($env:OPENCLAW_CHANNEL) { $env:OPENCLAW_CHANNEL } else { "latest" }

    try { $u = [Uri]$installUrl } catch { Fail $script:E002 "E002: OPENCLAW_INSTALL_URL 非法: $installUrl" }
    if ($u.Scheme -ne "https") {
        Fail $script:E002 "E002: OPENCLAW_INSTALL_URL 必须使用 https: $installUrl"
    }
    if ($script:OPENCLAW_ALLOWED_HOSTS -notcontains $u.Host.ToLowerInvariant()) {
        Fail $script:E002 "E002: OPENCLAW_INSTALL_URL 非官方域名: $($u.Host)"
    }
    if ($channel -ne "latest") {
        Write-Warn "OPENCLAW_CHANNEL=$channel；当前策略要求 latest，继续按 latest 执行"
        $channel = "latest"
    }

    # npm registry：优先使用环境变量，默认淘宝镜像加速
    $npmRegistry = $script:OPENCLAW_DEFAULT_NPM_REGISTRY
    $prevRegistry          = $env:NPM_CONFIG_REGISTRY
    $prevFetchRetries      = $env:NPM_CONFIG_FETCH_RETRIES
    $prevFetchRetryTimeout = $env:NPM_CONFIG_FETCH_RETRY_MINTIMEOUT
    $prevFetchTimeout      = $env:NPM_CONFIG_FETCH_TIMEOUT
    $env:NPM_CONFIG_REGISTRY              = $npmRegistry
    $env:NPM_CONFIG_FETCH_RETRIES         = "3"
    $env:NPM_CONFIG_FETCH_RETRY_MINTIMEOUT = "10000"
    $env:NPM_CONFIG_FETCH_TIMEOUT         = "60000"

    Write-Ok "OpenClaw 安装源: $installUrl"
    Write-Ok "OpenClaw 渠道: $channel"
    Write-Ok "npm registry: $npmRegistry"
    Write-Host "  [i] 本步将执行官方安装器（内含 npm 全局安装 openclaw，依赖大，首次常见 5–20 分钟；长时间无新行仍可能在下载/编译）。" -ForegroundColor DarkGray
    Write-Host "  [i] 下方 [openclaw] 为实时输出；若暂时无输出，将每 15s 提示已运行时长与日志末行。" -ForegroundColor DarkGray

    # 实时日志落文件，超时 $OPENCLAW_INSTALL_TIMEOUT_SEC 秒后强制失败
    $logFile = Join-Path $env:TEMP ("opc200-openclaw-install-" + [Guid]::NewGuid().ToString("N") + ".log")
    Write-Ok "安装日志: $logFile"

    # 在父进程设好 npm 加速环境变量，子进程自动继承
    $env:NPM_CONFIG_REGISTRY               = $npmRegistry
    $env:NPM_CONFIG_FETCH_RETRIES          = "3"
    $env:NPM_CONFIG_FETCH_RETRY_MINTIMEOUT = "10000"
    $env:NPM_CONFIG_FETCH_TIMEOUT          = "60000"
    $env:NODE_LLAMA_CPP_SKIP_DOWNLOAD      = "1"
    $env:OPENCLAW_NO_ONBOARD               = "1"

    $tmpScript = $null
    try {
        $ProgressPreference = "SilentlyContinue"
        $officialInstaller = Invoke-RestMethod -Uri $installUrl -UseBasicParsing

        $tmpScript = Join-Path $env:TEMP ("opc200-openclaw-" + [Guid]::NewGuid().ToString("N") + ".ps1")
        # 官方脚本可能以 param() 块开头，PowerShell 要求 param() 必须是第一条语句。
        # 将 param() 块原样保留在最前，环境变量注入紧随其后。
        $envInject = @"

`$env:NPM_CONFIG_REGISTRY               = '$npmRegistry'
`$env:NPM_CONFIG_FETCH_RETRIES          = '3'
`$env:NPM_CONFIG_FETCH_RETRY_MINTIMEOUT = '10000'
`$env:NPM_CONFIG_FETCH_TIMEOUT          = '60000'
`$env:NODE_LLAMA_CPP_SKIP_DOWNLOAD      = '1'
`$env:OPENCLAW_NO_ONBOARD               = '1'

"@
        # 找到 param 块结束位置（匹配最外层括号）
        $paramEnd = -1
        $depth = 0
        $inParam = $false
        for ($ci = 0; $ci -lt $officialInstaller.Length; $ci++) {
            $ch = $officialInstaller[$ci]
            if (-not $inParam) {
                $stripped = $officialInstaller.Substring($ci).TrimStart()
                if ($stripped -match '(?i)^param\s*\(') {
                    $ci = $officialInstaller.Length - $stripped.Length + $stripped.IndexOf('(')
                    $inParam = $true; $depth = 1
                    continue
                }
                elseif ($ch -eq '#') {
                    while ($ci -lt $officialInstaller.Length -and $officialInstaller[$ci] -ne "`n") { $ci++ }
                    continue
                }
                elseif ($ch -match '\S') { break }
            }
            else {
                if ($ch -eq '(') { $depth++ }
                elseif ($ch -eq ')') {
                    $depth--
                    if ($depth -eq 0) { $paramEnd = $ci; break }
                }
            }
        }
        if ($paramEnd -ge 0) {
            $paramBlock  = $officialInstaller.Substring(0, $paramEnd + 1)
            $scriptBody  = $officialInstaller.Substring($paramEnd + 1)
            $patchedScript = $paramBlock + $envInject + $scriptBody
        }
        else {
            $patchedScript = $envInject + $officialInstaller
        }
        [System.IO.File]::WriteAllText($tmpScript, $patchedScript, [System.Text.UTF8Encoding]::new($false))

        # Start-Process 继承父进程全部环境变量；stdout/stderr 重定向到日志文件
        $proc = Start-Process -FilePath "powershell.exe" `
            -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $tmpScript, "-NoOnboard") `
            -RedirectStandardOutput $logFile `
            -RedirectStandardError  ($logFile + ".err") `
            -PassThru -NoNewWindow

        # 实时跟踪日志输出 + 心跳（npm 常长时间无 stdout，避免误以为卡死）
        $lastSize = 0
        $deadline = [DateTime]::UtcNow.AddSeconds($script:OPENCLAW_INSTALL_TIMEOUT_SEC)
        $installStartedAt = Get-Date
        $lastHeartbeatAt = $installStartedAt
        while (-not $proc.HasExited) {
            if ([DateTime]::UtcNow -gt $deadline) {
                try { $proc.Kill() } catch { }
                Fail $script:E002 ("E002: OpenClaw 官方安装超时（>{0}s）。日志: {1}" -f $script:OPENCLAW_INSTALL_TIMEOUT_SEC, $logFile)
            }
            Start-Sleep -Milliseconds 500
            if (Test-Path -LiteralPath $logFile) {
                $content = Get-Content -LiteralPath $logFile -Raw -Encoding utf8 -ErrorAction SilentlyContinue
                if ($content -and $content.Length -gt $lastSize) {
                    $newLines = $content.Substring($lastSize) -split "`n"
                    foreach ($line in $newLines) {
                        $trimmed = $line.TrimEnd("`r")
                        if ($trimmed -ne "") { Write-Host "  [openclaw] $trimmed" }
                    }
                    $lastSize = $content.Length
                }
            }
            $nowHb = Get-Date
            if (($nowHb - $lastHeartbeatAt).TotalSeconds -ge 15) {
                $lastHeartbeatAt = $nowHb
                $elapsed = [int](($nowHb - $installStartedAt).TotalSeconds)
                $kb = 0.0
                if (Test-Path -LiteralPath $logFile) {
                    try { $kb = [math]::Round((Get-Item -LiteralPath $logFile).Length / 1KB, 1) } catch { }
                }
                $tail = ""
                if (Test-Path -LiteralPath $logFile) {
                    try {
                        $lastLine = Get-Content -LiteralPath $logFile -Tail 1 -Encoding utf8 -ErrorAction SilentlyContinue
                        if ($lastLine) {
                            $tail = "$lastLine".Trim()
                            if ($tail.Length -gt 100) { $tail = $tail.Substring(0, 100) + "..." }
                        }
                    }
                    catch { }
                }
                $hbMsg = "仍运行中（已 ${elapsed}s，日志约 ${kb} KB"
                if ($tail) { $hbMsg += "，末行: $tail" }
                else { $hbMsg += "，末行尚空（npm 可能仍在缓冲）" }
                $hbMsg += "）"
                Write-Host "  [openclaw] $hbMsg" -ForegroundColor DarkGray
            }
        }

        # 打印剩余未输出内容
        if (Test-Path -LiteralPath $logFile) {
            $content = Get-Content -LiteralPath $logFile -Raw -Encoding utf8 -ErrorAction SilentlyContinue
            if ($content -and $content.Length -gt $lastSize) {
                $newLines = $content.Substring($lastSize) -split "`n"
                foreach ($line in $newLines) {
                    $trimmed = $line.TrimEnd("`r")
                    if ($trimmed -ne "") { Write-Host "  [openclaw] $trimmed" }
                }
            }
        }
        if (Test-Path -LiteralPath ($logFile + ".err")) {
            $errContent = Get-Content -LiteralPath ($logFile + ".err") -Raw -Encoding utf8 -ErrorAction SilentlyContinue
            if ($errContent -and $errContent.Trim() -ne "") {
                foreach ($line in ($errContent -split "`n")) {
                    $trimmed = $line.TrimEnd("`r")
                    if ($trimmed -ne "") { Write-Host "  [openclaw:err] $trimmed" -ForegroundColor Yellow }
                }
            }
        }

        $exitCode = if ($null -ne $proc.ExitCode) { $proc.ExitCode } else { 0 }
        if ($exitCode -ne 0) {
            Fail $script:E002 ("E002: OpenClaw 官方安装失败（退出码 {0}）。日志: {1}" -f $exitCode, $logFile)
        }
    }
    catch {
        if ($_.Exception.Message -match "E002:") { throw }
        Fail $script:E002 "E002: OpenClaw 官方安装失败 - $_"
    }
    finally {
        if ($tmpScript) { Remove-Item -LiteralPath $tmpScript -Force -ErrorAction SilentlyContinue }
        $env:NPM_CONFIG_REGISTRY               = $prevRegistry
        $env:NPM_CONFIG_FETCH_RETRIES          = $prevFetchRetries
        $env:NPM_CONFIG_FETCH_RETRY_MINTIMEOUT = $prevFetchRetryTimeout
        $env:NPM_CONFIG_FETCH_TIMEOUT          = $prevFetchTimeout
        $env:NODE_LLAMA_CPP_SKIP_DOWNLOAD      = $null
        $env:OPENCLAW_NO_ONBOARD               = $null
    }
    Write-Ok "OpenClaw 官方安装完成"
    Write-Host "  [i] 若日志里出现 openclaw doctor 提示 gateway.mode 未设置、属安装器收尾阶段尚未 onboard；下一步将 onboard / 轻预装 / 复查。" -ForegroundColor DarkGray
}

# ── Step 4: 轻预装层（skills + 文档）────────────────────────────

function Write-DocTemplate {
    param([string]$TargetPath, [string]$Content)
    if (Test-Path -LiteralPath $TargetPath) {
        [System.IO.File]::WriteAllText("$TargetPath.new", $Content + "`n", [System.Text.UTF8Encoding]::new($false))
        Write-Warn "已存在，写入增量文件: $TargetPath.new"
    }
    else {
        [System.IO.File]::WriteAllText($TargetPath, $Content + "`n", [System.Text.UTF8Encoding]::new($false))
        Write-Ok "已写入模板: $TargetPath"
    }
}

function Install-OpenClawPreload {
    Write-Step "7/15 轻预装层（tools + skills + 文档）"

    Sync-SessionPathFromRegistry
    $ocCmd = Get-Command openclaw -ErrorAction SilentlyContinue
    if ($ocCmd) {
        Write-Ok "openclaw config set tools.profile full"
        $tpCode = Invoke-OpenClawLoggedUtf8 -ExePath $ocCmd.Source -ArgumentList @("config", "set", "tools.profile", "full") -LinePrefix "openclaw:tools-profile"
        if ($tpCode -ne 0) {
            Write-Warn "tools.profile 未写入（退出码 $tpCode）；可稍后手动: openclaw config set tools.profile full"
        }
    }
    else {
        Write-Warn "未找到 openclaw，跳过 tools.profile"
    }

    $profileDir = if ($env:OPENCLAW_PROFILE_DIR) { $env:OPENCLAW_PROFILE_DIR } else { $script:OPENCLAW_DEFAULT_PROFILE_DIR }
    $skillsCsv = if ($env:OPENCLAW_PREINSTALL_SKILLS) { $env:OPENCLAW_PREINSTALL_SKILLS } else { $script:OPENCLAW_DEFAULT_SKILLS }
    $skillInstallCmd = if ($env:OPENCLAW_SKILL_INSTALL_CMD) { $env:OPENCLAW_SKILL_INSTALL_CMD } else { $script:OPENCLAW_DEFAULT_SKILL_INSTALL_CMD }
    $templatesDir = Join-Path $PSScriptRoot "openclaw-templates"
    $skillFailed = $false

    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Ok "OpenClaw 配置目录: $profileDir"

    # skills 安装失败按策略仅告警，不中断安装流程。
    if ($skillsCsv) {
        foreach ($raw in ($skillsCsv -split ",")) {
            $skill = $raw.Trim()
            if (-not $skill) { continue }
            try {
                Invoke-Expression "$skillInstallCmd `"$skill`""
                Write-Ok "skills 已安装: $skill"
            }
            catch {
                Write-Warn "skills 安装失败（已忽略）: $skill"
                $skillFailed = $true
            }
        }
    }
    else {
        Write-Warn "未配置 OPENCLAW_PREINSTALL_SKILLS，跳过 skills 安装"
    }

    Write-DocTemplateFromFile -SourcePath (Join-Path $templatesDir "SOUL.md") -TargetPath (Join-Path $profileDir "SOUL.md")
    Write-DocTemplateFromFile -SourcePath (Join-Path $templatesDir "IDENTITY.md") -TargetPath (Join-Path $profileDir "IDENTITY.md")
    Write-DocTemplateFromFile -SourcePath (Join-Path $templatesDir "AGENTS.md") -TargetPath (Join-Path $profileDir "AGENTS.md")

    if ($skillFailed) {
        Write-Warn "部分 skills 安装失败，已按策略继续安装"
    }
}

function Build-ProcessStartInfoArguments {
    param([string[]]$ArgsAll)
    $sb = New-Object System.Text.StringBuilder
    $idx = 0
    foreach ($arg in $ArgsAll) {
        $s = "$arg"
        if ($idx -gt 0) { [void]$sb.Append(' ') }
        $idx++
        if ($s -match '[\s"]') {
            [void]$sb.Append('"')
            [void]$sb.Append(($s -replace '"', '""'))
            [void]$sb.Append('"')
        }
        else {
            [void]$sb.Append($s)
        }
    }
    return $sb.ToString()
}

function Start-OpenClawCliProcess {
    param(
        [Parameter(Mandatory)][string]$OpenclawPath,
        [Parameter(Mandatory)][string[]]$CliArguments,
        [string]$RedirectStandardOutput,
        [string]$RedirectStandardError,
        [switch]$NoNewWindow,
        [switch]$PassThru,
        [switch]$Wait
    )
    $resolved = $OpenclawPath
    if (-not (Test-Path -LiteralPath $resolved)) {
        throw "OpenClaw 路径不存在: $resolved"
    }
    $resolved = (Resolve-Path -LiteralPath $resolved).Path
    $ext = [System.IO.Path]::GetExtension($resolved).ToLowerInvariant()

    $sp = @{
        NoNewWindow = [bool]$NoNewWindow
        PassThru    = [bool]$PassThru
        Wait        = [bool]$Wait
    }
    if ($RedirectStandardOutput) { $sp['RedirectStandardOutput'] = $RedirectStandardOutput }
    if ($RedirectStandardError) { $sp['RedirectStandardError'] = $RedirectStandardError }

    function Escape-CmdArg {
        param([string]$s)
        $t = "$s"
        if ($t -match '[\s"&]') { return '"' + ($t -replace '"', '""') + '"' }
        return $t
    }

    function Start-OpenClawProcessFromStartInfo {
        param(
            [string]$FileName,
            [string]$Arguments
        )
        $pinfo = New-Object System.Diagnostics.ProcessStartInfo
        $pinfo.FileName = $FileName
        $pinfo.Arguments = $Arguments
        $pinfo.UseShellExecute = $false
        $pinfo.CreateNoWindow = [bool]$NoNewWindow
        if ($RedirectStandardOutput) {
            $pinfo.RedirectStandardOutput = $true
            $pinfo.StandardOutputEncoding = [System.Text.Encoding]::UTF8
        }
        if ($RedirectStandardError) {
            $pinfo.RedirectStandardError = $true
            $pinfo.StandardErrorEncoding = [System.Text.Encoding]::UTF8
        }
        $proc = New-Object System.Diagnostics.Process
        $proc.StartInfo = $pinfo
        [void]$proc.Start()
        if ($RedirectStandardOutput -or $RedirectStandardError) {
            if (-not $Wait) {
                throw "内部错误：重定向输出时必须 Wait"
            }
            $proc.WaitForExit()
            $outText = if ($RedirectStandardOutput) { $proc.StandardOutput.ReadToEnd() } else { "" }
            $errText = if ($RedirectStandardError) { $proc.StandardError.ReadToEnd() } else { "" }
            if ($RedirectStandardOutput) {
                [System.IO.File]::WriteAllText($RedirectStandardOutput, $outText, [System.Text.UTF8Encoding]::new($false))
            }
            if ($RedirectStandardError) {
                [System.IO.File]::WriteAllText($RedirectStandardError, $errText, [System.Text.UTF8Encoding]::new($false))
            }
        }
        elseif ($Wait) {
            $proc.WaitForExit()
        }
        return $proc
    }

    if ($ext -eq '.cmd' -or $ext -eq '.bat') {
        $tail = if ($CliArguments.Count -gt 0) { ' ' + (($CliArguments | ForEach-Object { Escape-CmdArg $_ }) -join ' ') } else { '' }
        $inner = "`"$resolved`"$tail"
        return Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', $inner) @sp
    }
    if ($ext -eq '.ps1') {
        $psExe = $null
        foreach ($name in @('pwsh.exe', 'powershell.exe')) {
            $c = Get-Command $name -ErrorAction SilentlyContinue
            if ($c) {
                $psExe = (Resolve-Path -LiteralPath $c.Source).Path
                break
            }
        }
        if (-not $psExe) {
            $psExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        }
        $allPs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $resolved) + $CliArguments
        $argLine = Build-ProcessStartInfoArguments $allPs
        return Start-OpenClawProcessFromStartInfo -FileName $psExe -Arguments $argLine
    }
    if ($ext -eq '.exe') {
        $argLine = Build-ProcessStartInfoArguments $CliArguments
        return Start-OpenClawProcessFromStartInfo -FileName $resolved -Arguments $argLine
    }

    $isPe = $false
    try {
        $fs = [System.IO.File]::OpenRead($resolved)
        $buf = New-Object byte[] 2
        $n = $fs.Read($buf, 0, 2)
        $fs.Dispose()
        if ($n -ge 2 -and $buf[0] -eq 0x4D -and $buf[1] -eq 0x5A) { $isPe = $true }
    }
    catch { }

    if ($isPe) {
        $argLine = Build-ProcessStartInfoArguments $CliArguments
        return Start-OpenClawProcessFromStartInfo -FileName $resolved -Arguments $argLine
    }

    $cmdSibling = "$resolved.cmd"
    if (Test-Path -LiteralPath $cmdSibling) {
        $tail = if ($CliArguments.Count -gt 0) { ' ' + (($CliArguments | ForEach-Object { Escape-CmdArg $_ }) -join ' ') } else { '' }
        $inner = "`"$cmdSibling`"$tail"
        return Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', $inner) @sp
    }

    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    if ($nodeCmd) {
        $nodeExe = (Resolve-Path -LiteralPath $nodeCmd.Source).Path
        $argLine = Build-ProcessStartInfoArguments (@($resolved) + $CliArguments)
        return Start-OpenClawProcessFromStartInfo -FileName $nodeExe -Arguments $argLine
    }

    throw "无法启动 openclaw（非 PE 且未找到 node.exe）：$resolved"
}

function Invoke-OpenClawLoggedUtf8 {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [Parameter(Mandatory)][string]$LinePrefix
    )
    $logOut = Join-Path $env:TEMP ("opc200-openclaw-" + [Guid]::NewGuid().ToString("N") + ".log")
    $logErr = "${logOut}.err"
    try {
        $p = Start-OpenClawCliProcess -OpenclawPath $ExePath -CliArguments $ArgumentList -NoNewWindow -PassThru -Wait `
            -RedirectStandardOutput $logOut -RedirectStandardError $logErr
        foreach ($pth in @($logOut, $logErr)) {
            if (-not (Test-Path -LiteralPath $pth)) { continue }
            $lines = Get-Content -LiteralPath $pth -Encoding utf8 -ErrorAction SilentlyContinue
            if ($null -eq $lines) { continue }
            foreach ($line in @($lines)) {
                $t = "$line".TrimEnd()
                if ($t.Length -eq 0) { continue }
                Write-Host "  [$LinePrefix] $t"
            }
        }
        return $p.ExitCode
    }
    catch {
        Write-Warn "${LinePrefix}: $_"
        return 1
    }
    finally {
        Remove-Item -LiteralPath $logOut -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $logErr -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-OpenClawCaptureUtf8 {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [Parameter(Mandatory)][string[]]$ArgumentList
    )
    $logOut = Join-Path $env:TEMP ("opc200-openclaw-" + [Guid]::NewGuid().ToString("N") + ".capture.log")
    $logErr = "${logOut}.err"
    try {
        $p = Start-OpenClawCliProcess -OpenclawPath $ExePath -CliArguments $ArgumentList -NoNewWindow -PassThru -Wait `
            -RedirectStandardOutput $logOut -RedirectStandardError $logErr
        $stdout = ""
        $stderr = ""
        if (Test-Path -LiteralPath $logOut) { $stdout = Get-Content -LiteralPath $logOut -Raw -Encoding utf8 -ErrorAction SilentlyContinue }
        if (Test-Path -LiteralPath $logErr) { $stderr = Get-Content -LiteralPath $logErr -Raw -Encoding utf8 -ErrorAction SilentlyContinue }
        return @{
            ExitCode = $p.ExitCode
            StdOut   = if ($stdout) { "$stdout" } else { "" }
            StdErr   = if ($stderr) { "$stderr" } else { "" }
        }
    }
    catch {
        return @{
            ExitCode = 1
            StdOut   = ""
            StdErr   = "$_"
        }
    }
    finally {
        Remove-Item -LiteralPath $logOut -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $logErr -Force -ErrorAction SilentlyContinue
    }
}

function Find-FirstValueByKeyLike {
    param(
        [Parameter(Mandatory)]$Node,
        [Parameter(Mandatory)][string[]]$Patterns
    )
    if ($null -eq $Node) { return $null }
    if ($Node -is [System.Collections.IDictionary]) {
        foreach ($k in $Node.Keys) {
            $name = "$k"
            foreach ($pat in $Patterns) {
                if ($name -match $pat) {
                    return $Node[$k]
                }
            }
        }
        foreach ($k in $Node.Keys) {
            $v = Find-FirstValueByKeyLike -Node $Node[$k] -Patterns $Patterns
            if ($null -ne $v) { return $v }
        }
        return $null
    }
    if (($Node -is [System.Collections.IEnumerable]) -and -not ($Node -is [string])) {
        foreach ($item in $Node) {
            $v = Find-FirstValueByKeyLike -Node $item -Patterns $Patterns
            if ($null -ne $v) { return $v }
        }
    }
    return $null
}

function Test-OpenClawGatewayInstalledFromStatusJson {
    param([string]$StatusJson)
    if ([string]::IsNullOrWhiteSpace($StatusJson)) { return $false }
    try {
        $obj = $StatusJson | ConvertFrom-Json -Depth 100
        $installedVal = Find-FirstValueByKeyLike -Node $obj -Patterns @("(?i)^installed$", "(?i)service.*installed")
        if ($installedVal -is [bool]) { return $installedVal }
        if ($installedVal) {
            $txt = "$installedVal".Trim().ToLowerInvariant()
            if ($txt -eq "true" -or $txt -eq "installed") { return $true }
            if ($txt -eq "false") { return $false }
        }
        $stateVal = Find-FirstValueByKeyLike -Node $obj -Patterns @("(?i)^state$", "(?i)service.*state")
        if ($stateVal) {
            $stateTxt = "$stateVal".Trim().ToLowerInvariant()
            if ($stateTxt -match "not[_-]?installed|missing|absent") { return $false }
        }
    }
    catch { }
    if ($StatusJson -match '(?i)"installed"\s*:\s*true') { return $true }
    if ($StatusJson -match '(?i)not[_-]?installed|not installed') { return $false }
    return $true
}

function Ensure-OpenClawCliPresentOrInstall {
    Sync-SessionPathFromRegistry
    $oc = Get-Command openclaw -ErrorAction SilentlyContinue
    if ($oc) {
        Write-Ok "已检测到 openclaw CLI"
        return $false
    }
    Install-OpenClawOfficial
    Sync-SessionPathFromRegistry
    $oc2 = Get-Command openclaw -ErrorAction SilentlyContinue
    if (-not $oc2) {
        Fail $script:E002 "E002: OpenClaw 安装后仍未在 PATH 中找到 openclaw。请关闭并重新打开 PowerShell 后重新执行本脚本。"
    }
    Write-Ok "openclaw CLI 已就绪"
    return $true
}

function Set-OpenClawGatewayPortEnvForAgent {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [int]$GwPortHint
    )
    $gwPort = $GwPortHint
    $portProbe = Invoke-OpenClawCaptureUtf8 -ExePath $ExePath -ArgumentList @("config", "get", "gateway.port")
    if ($portProbe.ExitCode -eq 0) {
        $portText = "$($portProbe.StdOut)".Trim()
        if ($portText.StartsWith('"') -and $portText.EndsWith('"')) { $portText = $portText.Trim('"') }
        if ($portText -match '^\d+$') { $gwPort = [int]$portText }
        else { Write-Warn "gateway.port 读取结果非数字（$portText），回退使用端口 $gwPort" }
    }
    else {
        Write-Warn "gateway.port 读取失败，回退使用端口 $gwPort"
    }
    $env:OPENCLAW_GATEWAY_PORT = "$gwPort"
    $env:OPENCLAW_GATEWAY_HEALTH_URL = "http://127.0.0.1:$gwPort/health"
    Write-Ok "已记录 gateway 端口 $gwPort（OPENCLAW_GATEWAY_PORT / OPENCLAW_GATEWAY_HEALTH_URL，供 OPC200 agent_health）"
}

function Install-OpenClawGatewayWithRetry {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [Parameter(Mandatory)][int]$GwPort
    )
    $lastCode = -1
    for ($attempt = 1; $attempt -le $script:OPENCLAW_GW_INSTALL_MAX_RETRY; $attempt++) {
        Write-Ok "安装 gateway 服务（第 $attempt/$($script:OPENCLAW_GW_INSTALL_MAX_RETRY) 次）：openclaw gateway install --port $GwPort"
        $instArgs = @("gateway", "install", "--port", "$GwPort")
        $codeGi = Invoke-OpenClawLoggedUtf8 -ExePath $ExePath -ArgumentList $instArgs -LinePrefix "openclaw:gw-install"
        $lastCode = $codeGi
        if ($codeGi -eq 0) {
            Write-Ok "gateway install 成功"
            return
        }
        Write-Warn "gateway install 失败（退出码 $codeGi），将重试"
    }
    Fail $script:E002 "E002: gateway install 在 $($script:OPENCLAW_GW_INSTALL_MAX_RETRY) 次重试后仍失败（最后退出码 $lastCode）。请检查网络与权限后重新执行本脚本。"
}

function Invoke-OpenClawGatewayConfigureLocal {
    param([Parameter(Mandatory)][string]$ExePath)
    Write-Ok "配置网关：gateway.mode=local"
    $codeMode = Invoke-OpenClawLoggedUtf8 -ExePath $ExePath -ArgumentList @("config", "set", "gateway.mode", "local") -LinePrefix "openclaw:cfg"
    if ($codeMode -ne 0) {
        Fail $script:E002 "E002: openclaw config set gateway.mode local 失败（退出码 $codeMode）"
    }
    Write-Ok "配置网关：gateway.tls.enabled=false（HTTP）"
    $codeTls = Invoke-OpenClawLoggedUtf8 -ExePath $ExePath -ArgumentList @("config", "set", "gateway.tls.enabled", "false") -LinePrefix "openclaw:cfg-tls"
    if ($codeTls -ne 0) {
        Write-Warn "未能写入 gateway.tls.enabled=false（退出码 $codeTls）；若 CLI 无此键可忽略"
    }
    Write-Host "  [i] config 变更后需重启网关才会完全生效（见 CLI 提示 Restart the gateway）。" -ForegroundColor DarkGray
}

function Wait-OpenClawGatewayRpcOrHttp {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [Parameter(Mandatory)][int]$GwPort
    )
    $max = $script:OPENCLAW_GATEWAY_WARMUP_MAX_TRIES
    $sec = $script:OPENCLAW_GATEWAY_WARMUP_SLEEP_SEC
    for ($i = 1; $i -le $max; $i++) {
        $cap = Invoke-OpenClawCaptureUtf8 -ExePath $ExePath -ArgumentList @("gateway", "status", "--json", "--require-rpc")
        if ($cap.ExitCode -eq 0) {
            Write-Ok "网关 RPC 探测就绪（第 $i/$max 次）"
            return $true
        }
        try {
            $hu = "http://127.0.0.1:$GwPort/health"
            $r = Invoke-WebRequest -Uri $hu -UseBasicParsing -TimeoutSec 3
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) {
                Write-Ok "网关 HTTP /health 就绪（第 $i/$max 次）"
                return $true
            }
        }
        catch { }
        if ($i -lt $max) {
            Write-Host "  [i] 等待网关监听/RPC... $i/$max" -ForegroundColor DarkGray
            Start-Sleep -Seconds $sec
        }
    }
    Write-Warn "约 $($max * $sec)s 内 gateway status --require-rpc 与 /health 均未就绪；可手动: openclaw gateway restart"
    return $false
}

function Start-OpenClawGatewayForPart2 {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [Parameter(Mandatory)][int]$GwPort
    )
    Write-Ok "应用网关配置：openclaw gateway restart（使 mode/TLS 等生效）"
    $codeRe = Invoke-OpenClawLoggedUtf8 -ExePath $ExePath -ArgumentList @("gateway", "restart") -LinePrefix "openclaw:gw-restart"
    if ($codeRe -ne 0) {
        Write-Warn "gateway restart 返回非零（$codeRe）；尝试 gateway start"
        $codeSt = Invoke-OpenClawLoggedUtf8 -ExePath $ExePath -ArgumentList @("gateway", "start") -LinePrefix "openclaw:gw-start"
        if ($codeSt -ne 0) {
            Write-Warn "gateway start 返回非零（$codeSt）"
            return $false
        }
    }
    Write-Ok "已请求 gateway restart/start"
    Start-Sleep -Seconds 2
    $null = Wait-OpenClawGatewayRpcOrHttp -ExePath $ExePath -GwPort $GwPort
    return $true
}

function Invoke-OpenClawPart2DoctorOnly {
    param([Parameter(Mandatory)][string]$ExePath)
    Write-Step "9/15 OpenClaw doctor 复查"
    $code = Invoke-OpenClawLoggedUtf8 -ExePath $ExePath -ArgumentList @("doctor", "--non-interactive") -LinePrefix "openclaw:doctor"
    if ($code -ne 0) {
        Write-Warn "openclaw doctor 返回非零（$code）；仍将继续安装 OPC200 Agent，必要时请手动排查"
    }
    else {
        Write-Ok "openclaw doctor 完成"
    }
}

function Invoke-OpenClawPart2InstallAndGateway {
    param([bool]$FreshOpenClawCliInstall)
    Write-Step "8/15 OpenClaw 网关配置"
    Sync-SessionPathFromRegistry
    $oc = Get-Command openclaw -ErrorAction SilentlyContinue
    if (-not $oc) {
        Fail $script:E002 "E002: 第二部分需要 openclaw CLI，但未找到。请先完成官方安装或检查 PATH。"
    }
    $exe = $oc.Source
    $gwPort = $script:OPENCLAW_DEFAULT_GATEWAY_PORT
    if ($env:OPENCLAW_GATEWAY_PORT -match '^\d+$') { $gwPort = [int]$env:OPENCLAW_GATEWAY_PORT }

    if ($FreshOpenClawCliInstall) {
        Write-Host "  [i] 本次为新安装 openclaw CLI；优先 RPC 探测，未就绪时再区分「未安装」与「已装需修复」。" -ForegroundColor DarkGray
    }

    $statusRpcFirst = Invoke-OpenClawCaptureUtf8 -ExePath $exe -ArgumentList @("gateway", "status", "--json", "--require-rpc")
    if ($statusRpcFirst.ExitCode -eq 0) {
        Set-OpenClawGatewayPortEnvForAgent -ExePath $exe -GwPortHint $gwPort
        $gp = $gwPort
        if ($env:OPENCLAW_GATEWAY_PORT -match '^\d+$') { $gp = [int]$env:OPENCLAW_GATEWAY_PORT }
        Write-Host "  浏览器控制台: http://127.0.0.1:$gp （HTTP）" -ForegroundColor DarkGray
        Write-Ok "网关 RPC 探测正常，跳过安装/配置/启动"
        return
    }

    Write-Warn "网关 RPC 未就绪（退出码 $($statusRpcFirst.ExitCode)）；将检查服务是否已安装"

    $statusNoProbe = Invoke-OpenClawCaptureUtf8 -ExePath $exe -ArgumentList @("gateway", "status", "--json", "--no-probe")
    $installed = $false
    if ($statusNoProbe.ExitCode -eq 0) {
        $installed = Test-OpenClawGatewayInstalledFromStatusJson -StatusJson $statusNoProbe.StdOut
    }
    else {
        Write-Warn "gateway status --no-probe 失败（退出码 $($statusNoProbe.ExitCode)），按未安装 gateway 服务处理"
    }

    if ($installed) {
        Write-Warn "服务已登记但 RPC 异常，将尝试配置并启动"
        Invoke-OpenClawGatewayConfigureLocal -ExePath $exe
        $started = Start-OpenClawGatewayForPart2 -ExePath $exe -GwPort $gwPort
        if ($started) {
            Set-OpenClawGatewayPortEnvForAgent -ExePath $exe -GwPortHint $gwPort
            $gp = $gwPort
            if ($env:OPENCLAW_GATEWAY_PORT -match '^\d+$') { $gp = [int]$env:OPENCLAW_GATEWAY_PORT }
            Write-Host "  浏览器控制台: http://127.0.0.1:$gp （HTTP）" -ForegroundColor DarkGray
            return
        }
        Invoke-OpenClawPart2DoctorOnly -ExePath $exe
        Set-OpenClawGatewayPortEnvForAgent -ExePath $exe -GwPortHint $gwPort
        return
    }

    Install-OpenClawGatewayWithRetry -ExePath $exe -GwPort $gwPort
    Invoke-OpenClawGatewayConfigureLocal -ExePath $exe
    $started = Start-OpenClawGatewayForPart2 -ExePath $exe -GwPort $gwPort
    if ($started) {
        Set-OpenClawGatewayPortEnvForAgent -ExePath $exe -GwPortHint $gwPort
        $gp = $gwPort
        if ($env:OPENCLAW_GATEWAY_PORT -match '^\d+$') { $gp = [int]$env:OPENCLAW_GATEWAY_PORT }
        Write-Host "  浏览器控制台: http://127.0.0.1:$gp （HTTP）" -ForegroundColor DarkGray
        return
    }
    Invoke-OpenClawPart2DoctorOnly -ExePath $exe
    Set-OpenClawGatewayPortEnvForAgent -ExePath $exe -GwPortHint $gwPort
}

function Write-DocTemplateFromFile {
    param([string]$SourcePath, [string]$TargetPath)
    if (-not (Test-Path -LiteralPath $SourcePath)) {
        Fail $script:E001 "E001: 模板文件不存在: $SourcePath"
    }
    if (Test-Path -LiteralPath $TargetPath) {
        Copy-Item -LiteralPath $SourcePath -Destination "$TargetPath.new" -Force
        Write-Warn "已存在，写入增量文件: $TargetPath.new"
    }
    else {
        Copy-Item -LiteralPath $SourcePath -Destination $TargetPath -Force
        Write-Ok "已写入模板: $TargetPath"
    }
}

function ConvertFrom-SecureStringPlain {
    param([System.Security.SecureString]$Secure)
    if ($null -eq $Secure) { return "" }
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try { return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr) }
    finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
}

function Test-SecretPlainLooksValid {
    param([string]$s)
    if ($null -eq $s) { return $false }
    if ($s.Length -lt 8) { return $false }
    foreach ($ch in $s.ToCharArray()) {
        if ([char]::IsControl($ch)) { return $false }
    }
    return $true
}

function Normalize-SecretPlainLine {
    param([string]$s)
    if ($null -eq $s) { return "" }
    $t = $s.Trim()
    if ($t.Length -gt 0 -and [int][char]$t[0] -eq 0xFEFF) {
        $t = $t.Substring(1).Trim()
    }
    return $t
}

function Read-SecureLineNonEmpty {
    param([Parameter(Mandatory)][string]$Prompt)
    Write-Host ""
    Write-Host $Prompt -ForegroundColor Cyan
    Write-Host "  [1] 掩码输入（仅手敲；Ctrl+V/Shift+Ins 常无效）" -ForegroundColor DarkGray
    Write-Host "  [2] 可见粘贴一行（推荐）" -ForegroundColor DarkGray
    Write-Host "  [3] 从 UTF-8 文本文件读一行" -ForegroundColor DarkGray
    $m = (Read-Host "选择 [1-3]，回车=2").Trim()
    if ($m -ne "1" -and $m -ne "3") { $m = "2" }

    while ($true) {
        $plain = $null
        if ($m -eq "1") {
            $sec = Read-Host "密钥（掩码）" -AsSecureString
            $plain = Normalize-SecretPlainLine (ConvertFrom-SecureStringPlain $sec)
        }
        elseif ($m -eq "3") {
            $fp = (Read-Host "文件完整路径").Trim('"')
            if (-not (Test-Path -LiteralPath $fp)) {
                Write-Err "文件不存在"
                continue
            }
            try {
                $plain = Normalize-SecretPlainLine (Get-Content -LiteralPath $fp -Raw -Encoding UTF8)
            }
            catch {
                Write-Err "读取失败: $($_.Exception.Message)"
                continue
            }
        }
        else {
            Write-Warn "可见输入：密钥会显示在屏幕上，输入后建议执行 cls"
            $plain = Normalize-SecretPlainLine (Read-Host "API Key 一行")
        }

        if ([string]::IsNullOrWhiteSpace($plain)) {
            Write-Err "不能为空；若粘贴失败请选 2 或 3，静默安装请设环境变量 CUSTOM_API_KEY 等"
            continue
        }
        if (-not (Test-SecretPlainLooksValid $plain)) {
            Write-Err "过短或含不可见控制字符；请选 2 可见粘贴或 3 从文件读取，或改用环境变量"
            continue
        }
        return $plain
    }
}

function Test-OpenClawOnboardRequested {
    if ($SkipOpenClawOnboard) { return $false }
    if ($env:OPENCLAW_SKIP_ONBOARD -eq "1") { return $false }
    if ($env:OPENCLAW_ONBOARD -eq "0") { return $false }
    if ($OpenClawOnboard) { return $true }
    if ($env:OPENCLAW_ONBOARD -eq "1") { return $true }
    if (-not $Silent) { return $true }
    return $false
}

function Clear-EnvIfSet {
    param([string[]]$Names)
    foreach ($n in $Names) {
        if ([string]::IsNullOrWhiteSpace($n)) { continue }
        Set-Item -Path "Env:$n" -Value $null -ErrorAction SilentlyContinue
    }
}

function Install-OpenClawOnboardIfRequested {
    if (-not (Test-OpenClawOnboardRequested)) { return }

    Write-Step "6/15 OpenClaw 首次配置（官方 onboard --non-interactive）"
    if (-not $Silent) {
        Write-Host "  OpenClaw CLI 已就绪。下面采集模型/网关所需最少信息；随后自动执行官方非交互 onboard。" -ForegroundColor Gray
    }
    Sync-SessionPathFromRegistry

    $ocCmd = Get-Command openclaw -ErrorAction SilentlyContinue
    if (-not $ocCmd) {
        Write-Warn "未找到 openclaw 命令（PATH 未刷新或安装未完成），跳过 onboard。请新开终端后执行: openclaw onboard --non-interactive ..."
        return
    }

    $gwPort = $script:OPENCLAW_DEFAULT_GATEWAY_PORT
    if ($env:OPENCLAW_GATEWAY_PORT -match '^\d+$') { $gwPort = [int]$env:OPENCLAW_GATEWAY_PORT }

    $auth = $OpenClawAuthChoice.Trim()
    if (-not $auth -and $null -ne $env:OPENCLAW_AUTH_CHOICE) {
        $auth = $env:OPENCLAW_AUTH_CHOICE.Trim()
    }

    if ($Silent) {
        if (-not $auth) {
            Fail $script:E001 "E001: 静默安装且启用 OpenClaw onboard 时必须设置 OPENCLAW_AUTH_CHOICE（或 -OpenClawAuthChoice）"
        }
    }
    elseif (-not $auth) {
        Write-Host ""
        Write-Host "OpenClaw 模型认证（输入序号，须配置模型密钥）:" -ForegroundColor Cyan
        Write-Host "  1) Anthropic API Key (apiKey)"
        Write-Host "  2) OpenAI API Key (openai-api-key)"
        Write-Host "  3) Google Gemini API Key (gemini-api-key)"
        Write-Host "  4) OpenAI 兼容自定义端点 (custom-api-key，需 base_url + model)"
        $pick = Read-Host "选择 [1-4]"
        switch ($pick.Trim()) {
            "1" { $auth = "apiKey" }
            "2" { $auth = "openai-api-key" }
            "3" { $auth = "gemini-api-key" }
            "4" { $auth = "custom-api-key" }
            default { Fail $script:E001 "E001: 无效选择（请输入 1-4）" }
        }
    }

    if ($auth -eq "skip") {
        Fail $script:E001 "E001: 已不再支持 skip（跳过密钥）；请使用 apiKey、openai-api-key、gemini-api-key 或 custom-api-key，并配置对应密钥环境变量"
    }

    $secretMode = if ($env:OPENCLAW_SECRET_INPUT_MODE) { $env:OPENCLAW_SECRET_INPUT_MODE.Trim() } else { "plaintext" }
    if ($secretMode -ne "plaintext" -and $secretMode -ne "ref") {
        Fail $script:E001 "E001: OPENCLAW_SECRET_INPUT_MODE 仅支持 plaintext 或 ref"
    }

    $toClear = [System.Collections.Generic.List[string]]::new()
    function Fail-Onboard {
        param([int]$Code, [string]$Message)
        Clear-EnvIfSet @($toClear.ToArray())
        Fail $Code $Message
    }

    if (-not $Silent) {
        switch ($auth) {
            "apiKey" {
                $plain = Read-SecureLineNonEmpty -Prompt "Anthropic API Key"
                $env:ANTHROPIC_API_KEY = $plain
                [void]$toClear.Add("ANTHROPIC_API_KEY")
            }
            "openai-api-key" {
                $plain = Read-SecureLineNonEmpty -Prompt "OpenAI API Key"
                $env:OPENAI_API_KEY = $plain
                [void]$toClear.Add("OPENAI_API_KEY")
            }
            "gemini-api-key" {
                $plain = Read-SecureLineNonEmpty -Prompt "Gemini API Key"
                $env:GEMINI_API_KEY = $plain
                [void]$toClear.Add("GEMINI_API_KEY")
            }
            "custom-api-key" {
                $bu = ""
                do {
                    $bu = Read-Host "自定义 Base URL (OPENAI 兼容 v1)"
                    if ([string]::IsNullOrWhiteSpace($bu)) { Write-Err "Base URL 不能为空，请重新输入" }
                } while ([string]::IsNullOrWhiteSpace($bu))
                $mid = ""
                do {
                    $mid = Read-Host "模型 ID (custom-model-id)"
                    if ([string]::IsNullOrWhiteSpace($mid)) { Write-Err "模型 ID 不能为空，请重新输入" }
                } while ([string]::IsNullOrWhiteSpace($mid))
                $plain = Read-SecureLineNonEmpty -Prompt "API Key (写入 CUSTOM_API_KEY)"
                $env:OPENCLAW_CUSTOM_BASE_URL = $bu
                $env:OPENCLAW_CUSTOM_MODEL_ID = $mid
                $env:CUSTOM_API_KEY = $plain
                [void]$toClear.Add("OPENCLAW_CUSTOM_BASE_URL")
                [void]$toClear.Add("OPENCLAW_CUSTOM_MODEL_ID")
                [void]$toClear.Add("CUSTOM_API_KEY")
            }
        }
    }

    switch ($auth) {
        "apiKey" {
            if ($secretMode -eq "ref") {
                if ([string]::IsNullOrWhiteSpace($env:ANTHROPIC_API_KEY)) {
                    Fail-Onboard $script:E001 "E001: ref 模式需在环境中设置 ANTHROPIC_API_KEY"
                }
            }
            else {
                if ([string]::IsNullOrWhiteSpace($env:ANTHROPIC_API_KEY)) {
                    Fail-Onboard $script:E001 "E001: 需提供 ANTHROPIC_API_KEY 环境变量（静默）或交互输入"
                }
            }
        }
        "openai-api-key" {
            if ([string]::IsNullOrWhiteSpace($env:OPENAI_API_KEY)) {
                Fail-Onboard $script:E001 "E001: 需提供 OPENAI_API_KEY（静默或 ref 模式环境）"
            }
        }
        "gemini-api-key" {
            if ([string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
                Fail-Onboard $script:E001 "E001: 需提供 GEMINI_API_KEY"
            }
        }
        "custom-api-key" {
            if ([string]::IsNullOrWhiteSpace($env:OPENCLAW_CUSTOM_BASE_URL) -or [string]::IsNullOrWhiteSpace($env:OPENCLAW_CUSTOM_MODEL_ID)) {
                Fail-Onboard $script:E001 "E001: custom-api-key 需 OPENCLAW_CUSTOM_BASE_URL 与 OPENCLAW_CUSTOM_MODEL_ID"
            }
            if ($secretMode -eq "plaintext" -and [string]::IsNullOrWhiteSpace($env:CUSTOM_API_KEY)) {
                Fail-Onboard $script:E001 "E001: custom-api-key plaintext 需 CUSTOM_API_KEY"
            }
        }
        default { Fail-Onboard $script:E001 "E001: 不支持的 OPENCLAW_AUTH_CHOICE: $auth（支持 apiKey|openai-api-key|gemini-api-key|custom-api-key）" }
    }

    $argList = [System.Collections.Generic.List[string]]::new()
    # 官方非交互 onboard 要求显式风险确认，见 https://docs.openclaw.ai/security
    [void]$argList.AddRange([string[]]@(
            "onboard", "--non-interactive", "--accept-risk", "--mode", "local",
            "--auth-choice", "$auth",
            "--secret-input-mode", "$secretMode",
            "--gateway-port", "$gwPort",
            "--gateway-bind", "loopback",
            "--install-daemon",
            "--daemon-runtime", "node",
            "--skip-skills"
        ))

    if ($auth -eq "custom-api-key") {
        [void]$argList.AddRange([string[]]@("--custom-base-url", "$($env:OPENCLAW_CUSTOM_BASE_URL)", "--custom-model-id", "$($env:OPENCLAW_CUSTOM_MODEL_ID)"))
        $compat = if ($env:OPENCLAW_CUSTOM_COMPATIBILITY) { $env:OPENCLAW_CUSTOM_COMPATIBILITY } else { "openai" }
        [void]$argList.AddRange([string[]]@("--custom-compatibility", "$compat"))
        if ($env:OPENCLAW_CUSTOM_PROVIDER_ID) {
            [void]$argList.AddRange([string[]]@("--custom-provider-id", "$($env:OPENCLAW_CUSTOM_PROVIDER_ID)"))
        }
    }

    $exePath = $ocCmd.Source
    $obTimeout = $script:OPENCLAW_ONBOARD_TIMEOUT_SEC
    if ($env:OPENCLAW_ONBOARD_TIMEOUT_SEC -match '^\d+$') { $obTimeout = [int]$env:OPENCLAW_ONBOARD_TIMEOUT_SEC }
    Write-Ok "执行 openclaw onboard --non-interactive（auth=$auth gatewayPort=$gwPort secret=$secretMode）"

    $deadline = [DateTime]::UtcNow.AddSeconds($obTimeout)
    $argArray = @($argList.ToArray())
    switch ($auth) {
        "apiKey" { if ($env:ANTHROPIC_API_KEY) { $script:ApiKey = $env:ANTHROPIC_API_KEY } }
        "openai-api-key" { if ($env:OPENAI_API_KEY) { $script:ApiKey = $env:OPENAI_API_KEY } }
        "gemini-api-key" { if ($env:GEMINI_API_KEY) { $script:ApiKey = $env:GEMINI_API_KEY } }
        "custom-api-key" { if ($env:CUSTOM_API_KEY) { $script:ApiKey = $env:CUSTOM_API_KEY } }
        default { }
    }
    try {
        $proc = Start-OpenClawCliProcess -OpenclawPath $exePath -CliArguments $argArray -NoNewWindow -PassThru
    }
    catch {
        Fail-Onboard $script:E002 "E002: 无法启动 openclaw onboard（多为 npm 的 .cmd 入口或 PATH）：$_"
    }
    while (-not $proc.HasExited) {
        if ([DateTime]::UtcNow -gt $deadline) {
            try { $proc.Kill() } catch { }
            Fail-Onboard $script:E002 ("E002: openclaw onboard 超时（>{0}s）。请检查网络与 openclaw 版本；可手动: openclaw doctor" -f $obTimeout)
        }
        Start-Sleep -Milliseconds 400
    }
    try { $null = $proc.WaitForExit(0) } catch { }
    try { $proc.Refresh() } catch { }
    # Windows 上部分 npm/cmd 链路的 ExitCode 会为 $null；$null -ne 0 在 PowerShell 中为 $true，会误判失败
    $rawExit = $null
    try { $rawExit = $proc.ExitCode } catch { }
    $code = if ($null -eq $rawExit) { 0 } else { [int]$rawExit }
    Clear-EnvIfSet $toClear

    if ($code -ne 0) {
        if ($env:OPENCLAW_ONBOARD_STRICT -eq "1") {
            Fail $script:E002 "E002: openclaw onboard 失败（退出码 $code）。请查看终端输出或运行 openclaw doctor"
        }
        Write-Warn "openclaw onboard 失败（退出码 $code），已按非严格策略继续。设置 OPENCLAW_ONBOARD_STRICT=1 可在失败时中止安装。"
        return
    }

    $healthUrl = if ($env:OPENCLAW_GATEWAY_HEALTH_URL) { $env:OPENCLAW_GATEWAY_HEALTH_URL } else { "http://127.0.0.1:$gwPort/health" }
    Write-Ok "探测网关健康: $healthUrl"
    $okHealth = $false
    for ($i = 0; $i -lt 30; $i++) {
        try {
            $r = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 2
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 300) { $okHealth = $true; break }
        }
        catch { }
        Start-Sleep -Seconds 2
    }
    if (-not $okHealth) {
        if ($env:OPENCLAW_ONBOARD_STRICT -eq "1") {
            Fail $script:E002 "E002: onboard 后网关健康检查失败。请确认计划任务/服务已拉起网关或检查 OPENCLAW_GATEWAY_HEALTH_URL"
        }
        Write-Warn "网关 HTTP 健康检查未在约 60s 内通过；opc-agent 仍会继续安装。可稍后重试网关或设置 OPENCLAW_GATEWAY_HEALTH_PROBE=0（仅 Agent 指标场景）"
    }
    else {
        Write-Ok "OpenClaw 网关健康检查通过"
    }
}

function Get-AgentBinary {
    Write-Step "11/15 Python 运行环境 (venv + pip，精简依赖)"
    $reqName = "requirements-agent-runtime.txt"
    $req = Join-Path $script:RepoRootResolved "agent\scripts\$reqName"
    if (-not (Test-Path -LiteralPath $req)) {
        Fail $script:E001 "E001: 缺少 $reqName"
    }
    $pyCmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
    if (-not $pyCmd) { Fail $script:E001 "E001: 未找到 python" }
    $root = $script:InstallRoot
    if (-not (Test-Path -LiteralPath $root)) {
        New-Item -ItemType Directory -Path $root -Force | Out-Null
    }
    $venv = Join-Path $root "venv"
    try {
        & $pyCmd.Name -m venv $venv
        $venvPy = Join-Path $venv "Scripts\python.exe"
        & $venvPy -m pip install -q -U pip
        $env:PYTHONUTF8 = "1"
        & $venvPy -m pip install -q -r $req
    }
    catch {
        if (Test-Path $venv) { Remove-Item $venv -Recurse -Force -ErrorAction SilentlyContinue }
        Fail $script:E002 "E002: venv/pip 失败 - $_"
    }
    Write-Ok "已安装运行时依赖 → $venv"
}

# ── Step 6: 安装部署 ─────────────────────────────────────────────

function Install-Agent {
    Write-Step "12/15 安装部署"

    $root = $script:InstallRoot

    # 目录结构 (AGENT-001 §3.1)
    $dirs = @(
        $root,
        (Join-Path $root "bin"),
        (Join-Path $root "config"),
        (Join-Path $root "data"),
        (Join-Path $root "data\journal"),
        (Join-Path $root "data\exporter"),
        (Join-Path $root "logs")
    )

    foreach ($d in $dirs) {
        if (-not (Test-Path $d)) {
            New-Item -ItemType Directory -Path $d -Force | Out-Null
        }
    }

    Register-Rollback {
        $ir = $script:InstallRoot
        if ($ir -and (Test-Path -LiteralPath $ir)) {
            Remove-Item -LiteralPath $ir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Ok "目录结构已创建"

    $rp = $script:RepoRootResolved -replace "'", "''"
    $pyw = Join-Path $root "venv\Scripts\python.exe"
    $cfgPath = Join-Path $root "config\config.yml"
    $script:RunAgentScript = Join-Path $root "run-agent.ps1"
    $raContent = @"
`$env:PYTHONPATH = '$rp'
& '$($pyw -replace "'", "''")' -m agent.src.opc_agent.cli --config '$($cfgPath -replace "'", "''")' run
"@
    [System.IO.File]::WriteAllText($script:RunAgentScript, $raContent.TrimEnd() + "`n", [System.Text.UTF8Encoding]::new($true))
    Write-Ok "已写入 $($script:RunAgentScript)"

    # config.yml (AGENT-001 §3.2)
    $configYml = @"
platform:
  url: "$($script:PlatformUrl)"
  metrics_endpoint: "/metrics/job"

customer:
  id: "$($script:TenantId)"

agent:
  version: "$($script:AGENT_VERSION)"
  check_interval: 60
  push_interval: 30

gateway:
  host: "127.0.0.1"
  port: $OPC200Port

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

    $script:ConfigYml = $configPath
}

# ── Step 7: 注册自动启动（计划任务；opc-agent 为普通进程，非 Windows 服务 SCM 宿主）──

function Register-Service {
    Write-Step "13/15 注册计划任务(登录时启动)"

    $legacy = Get-Service -Name $script:SERVICE_NAME -ErrorAction SilentlyContinue
    if ($legacy) {
        Write-Warn "检测到旧版 Windows 服务项，正在移除"
        Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
        sc.exe delete $script:SERVICE_NAME 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }

    Unregister-ScheduledTask -TaskName $script:TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue

    try {
        $ra = $script:RunAgentScript
        $wdir = Split-Path -Parent $ra
        $action = New-ScheduledTaskAction -Execute "powershell.exe" `
            -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ra`"" -WorkingDirectory $wdir
        $userId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
        $trigger = New-ScheduledTaskTrigger -AtLogOn -User $userId
        $principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Highest
        $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
        Register-ScheduledTask -TaskName $script:TASK_NAME -Action $action -Trigger $trigger `
            -Principal $principal -Settings $settings -Force | Out-Null
    }
    catch {
        Fail $script:E005 "E005: 计划任务注册失败 - $_"
    }

    Register-Rollback {
        Unregister-ScheduledTask -TaskName $script:TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue
    }

    Write-Ok "计划任务 $($script:TASK_NAME) 已注册 (当前用户登录后自动运行)"
}

# ── Step 8: 启动验证 ─────────────────────────────────────────────

function Start-AndVerify {
    Write-Step "14/15 启动验证"

    try {
        Start-ScheduledTask -TaskName $script:TASK_NAME -ErrorAction Stop
    }
    catch {
        Fail $script:E005 "E005: 计划任务启动失败 - $_"
    }

    Start-Sleep -Seconds 3
    Write-Ok "已触发计划任务启动 Agent"

    # 健康检查
    $healthUrl = "http://127.0.0.1:$OPC200Port/health"
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

# ── Step 9: 完成输出 ─────────────────────────────────────────────

function Show-Summary {
    Write-Step "15/15 安装完成"

    $root = $script:InstallRoot
    Write-Host ""
    Write-Host "  安装目录 : $root" -ForegroundColor Cyan
    Write-Host "  配置文件 : $root\config\config.yml" -ForegroundColor Cyan
    Write-Host "  日志文件 : $root\logs\agent.log" -ForegroundColor Cyan
    Write-Host "  计划任务 : $($script:TASK_NAME) (登录时运行)" -ForegroundColor Cyan
    Write-Host "  健康检查 : http://127.0.0.1:$OPC200Port/health" -ForegroundColor Cyan
    Write-Host "  运行方式 : Python venv + 仓库 $($script:RepoRootResolved)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  查看任务 : Get-ScheduledTask -TaskName $($script:TASK_NAME)" -ForegroundColor Gray
    Write-Host ('  查看日志 : Get-Content {0}\logs\agent.log -Tail 50' -f $root) -ForegroundColor Gray
    Write-Host ('  卸载     : .\uninstall.ps1 -InstallDir {0}' -f $root) -ForegroundColor Gray
    Write-Host ""
}

# ── 主流程 ────────────────────────────────────────────────────────

function Main {
    Write-Host ""
    Write-Host ('OPC200 Agent Installer v' + $script:AGENT_VERSION + ' (Windows)') -ForegroundColor Cyan
    Write-Host ""

    if ($RepoRoot) {
        $script:RepoRootResolved = (Resolve-Path -LiteralPath $RepoRoot).Path
    }
    else {
        $script:RepoRootResolved = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
    }

    # ── 第一部分：环境检测与 Node / 网络预检 ──
    Test-Environment
    Initialize-InstallPaths
    Ensure-OpenClawNodeRuntime
    Test-OpenClawNetworkReady

    # ── 第二部分：OpenClaw（CLI → onboard → 轻预装 → 网关）──
    $freshCli = Ensure-OpenClawCliPresentOrInstall
    Install-OpenClawOnboardIfRequested
    Install-OpenClawPreload
    Invoke-OpenClawPart2InstallAndGateway -FreshOpenClawCliInstall:$freshCli

    # ── 第三部分：OPC200 Agent ──
    Get-OpcAgentPlatformConfig
    Get-AgentBinary
    Install-Agent
    Register-Service
    Start-AndVerify
    Show-Summary

    return 0
}

$exitCode = Main
exit $exitCode
