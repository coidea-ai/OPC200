#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 安装脚本 (v2)
.DESCRIPTION
    按 AGENT-001 (docs/INSTALL_SCRIPT_SPEC.md) 规范实现。
    流程: 环境检查 → 配置获取 → 下载 Agent → 安装部署 → 注册计划任务(登录自启) → 启动验证 → 完成输出
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
.PARAMETER LocalBinary
    本地 opc-agent 可执行文件路径；指定时跳过从 GitHub Release 下载（适用于 Release 尚未发布或离线安装）
.PARAMETER UseBinary
    从 GitHub Release 下载单文件 exe；默认不使用二进制，而用本机 Python venv + 仓库源码运行
.PARAMETER RepoRoot
    OPC200 仓库根目录（含 agent/、src/）；默认为本脚本所在位置的 ..\..
.PARAMETER FullRuntimeDeps
    安装完整 pip 依赖（含 sentence-transformers/PyTorch，很慢）；默认仅装精简依赖（/health + 指标推送）
.EXAMPLE
    .\install.ps1
.EXAMPLE
    .\install.ps1 -PlatformUrl "https://platform.opc200.co" -CustomerId "opc-001" -ApiKey "sk-xxx" -Silent
.EXAMPLE
    .\install.ps1 -Silent -LocalBinary "C:\build\opc-agent-windows-amd64.exe" -PlatformUrl "http://127.0.0.1:9091" -CustomerId "e2e-1" -ApiKey "x"
#>

param(
    [string]$PlatformUrl = "",
    [string]$CustomerId = "",
    [string]$ApiKey     = "",
    [string]$InstallDir = "",
    [int]$Port          = 8080,
    [switch]$Silent,
    [string]$LocalBinary = "",
    [switch]$UseBinary,
    [string]$RepoRoot   = "",
    [switch]$FullRuntimeDeps
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
$script:MIN_WIN_BUILD   = [System.Version]"10.0.17763"   # Windows 10 1809
$script:MIN_DISK_GB     = 1

# 错误码 (AGENT-001 §6.1)
$script:E001 = 1   # 权限不足
$script:E002 = 2   # 网络连接失败
$script:E003 = 3   # 端口占用
$script:E004 = 4   # 校验失败
$script:E005 = 5   # 服务注册失败

$script:RepoRootResolved = ""
$script:UsePythonMode   = $true
$script:RunAgentScript  = ""

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
    Write-Step "3/10 准备 Node.js（OpenClaw 需要 v$($script:OPENCLAW_MIN_NODE_MAJOR)+）"

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
    Write-Step "1/10 环境检查"

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

    if ($script:UsePythonMode) {
        $cli = Join-Path $script:RepoRootResolved "agent\src\opc_agent\cli.py"
        if (-not (Test-Path -LiteralPath $cli)) {
            Fail $script:E001 "E001: 非 OPC200 仓库根目录: $($script:RepoRootResolved)（请用 -RepoRoot 或在克隆仓库内执行）"
        }
        $pyCmd = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pyCmd) { $pyCmd = Get-Command python3 -ErrorAction SilentlyContinue }
        if (-not $pyCmd) { Fail $script:E001 "E001: 未找到 python/python3" }
        $ver = & $pyCmd.Name -c "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
        $parts = $ver -split '\.'
        if ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 10)) {
            Fail $script:E001 "E001: 需要 Python 3.10+（当前 $ver）"
        }
        Write-Ok "Python 与源码: $($pyCmd.Source)；$($script:RepoRootResolved)"
    }
}

# ── Step 2: 获取配置 ─────────────────────────────────────────────

function Get-InstallConfig {
    Write-Step "2/10 获取配置"

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

# ── 网络预检 ─────────────────────────────────────────────────────

function Test-OpenClawNetworkReady {
    Write-Step "3.5/10 网络连通性预检"
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
        Write-Warn "部分主机不可达；若安装超时，可设置 OPENCLAW_NPM_REGISTRY 指向可用镜像后重试"
    }
}

# ── Step 3: 官方渠道安装 OpenClaw latest ─────────────────────────

function Install-OpenClawOfficial {
    Write-Step "4/10 官方渠道安装 OpenClaw latest"

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
    $npmRegistry = if ($env:OPENCLAW_NPM_REGISTRY) { $env:OPENCLAW_NPM_REGISTRY } else { $script:OPENCLAW_DEFAULT_NPM_REGISTRY }
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

        # 实时跟踪日志输出
        $lastSize = 0
        $deadline = [DateTime]::UtcNow.AddSeconds($script:OPENCLAW_INSTALL_TIMEOUT_SEC)
        while (-not $proc.HasExited) {
            if ([DateTime]::UtcNow -gt $deadline) {
                try { $proc.Kill() } catch { }
                Fail $script:E002 ("E002: OpenClaw 官方安装超时（>{0}s）。日志: {1}" -f $script:OPENCLAW_INSTALL_TIMEOUT_SEC, $logFile)
            }
            Start-Sleep -Milliseconds 500
            if (Test-Path -LiteralPath $logFile) {
                $content = Get-Content -LiteralPath $logFile -Raw -ErrorAction SilentlyContinue
                if ($content -and $content.Length -gt $lastSize) {
                    $newLines = $content.Substring($lastSize) -split "`n"
                    foreach ($line in $newLines) {
                        $trimmed = $line.TrimEnd("`r")
                        if ($trimmed -ne "") { Write-Host "  [openclaw] $trimmed" }
                    }
                    $lastSize = $content.Length
                }
            }
        }

        # 打印剩余未输出内容
        if (Test-Path -LiteralPath $logFile) {
            $content = Get-Content -LiteralPath $logFile -Raw -ErrorAction SilentlyContinue
            if ($content -and $content.Length -gt $lastSize) {
                $newLines = $content.Substring($lastSize) -split "`n"
                foreach ($line in $newLines) {
                    $trimmed = $line.TrimEnd("`r")
                    if ($trimmed -ne "") { Write-Host "  [openclaw] $trimmed" }
                }
            }
        }
        if (Test-Path -LiteralPath ($logFile + ".err")) {
            $errContent = Get-Content -LiteralPath ($logFile + ".err") -Raw -ErrorAction SilentlyContinue
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
    Write-Step "5/10 轻预装层（skills + 文档）"

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

# ── Step 5: 下载 Agent ───────────────────────────────────────────

function Get-AgentBinary {
    if ($LocalBinary) {
        Write-Step "6/10 使用本地 Agent 二进制 (跳过下载)"
        if (-not (Test-Path -LiteralPath $LocalBinary)) {
            Fail $script:E002 "E002: 本地文件不存在: $LocalBinary"
        }
        $script:TmpBinary = (Resolve-Path -LiteralPath $LocalBinary).Path
        Write-Ok "本地二进制: $($script:TmpBinary)"
        return
    }

    if ($script:UsePythonMode) {
        if ($FullRuntimeDeps) {
            Write-Step "6/10 Python 运行环境 (venv + pip，完整依赖，较慢)"
            $reqName = "requirements-agent-runtime-full.txt"
        }
        else {
            Write-Step "6/10 Python 运行环境 (venv + pip，精简依赖)"
            $reqName = "requirements-agent-runtime.txt"
        }
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
        $script:TmpBinary = ""
        return
    }

    Write-Step "6/10 下载 Agent"

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

# ── Step 6: 安装部署 ─────────────────────────────────────────────

function Install-Agent {
    Write-Step "7/10 安装部署"

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
        $ir = $script:InstallRoot
        if ($ir -and (Test-Path -LiteralPath $ir)) {
            Remove-Item -LiteralPath $ir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }

    Write-Ok "目录结构已创建"

    if ($script:UsePythonMode -and -not $LocalBinary) {
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
    }
    else {
        $agentDest = Join-Path $root "bin\opc-agent.exe"
        Copy-Item -Path $script:TmpBinary -Destination $agentDest -Force
        Write-Ok "Agent 二进制已部署"
        $script:AgentExe = $agentDest
    }

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

    $script:ConfigYml = $configPath
}

# ── Step 7: 注册自动启动（计划任务；opc-agent 为普通进程，非 Windows 服务 SCM 宿主）──

function Register-Service {
    Write-Step "8/10 注册计划任务(登录时启动)"

    $legacy = Get-Service -Name $script:SERVICE_NAME -ErrorAction SilentlyContinue
    if ($legacy) {
        Write-Warn "检测到旧版 Windows 服务项，正在移除"
        Stop-Service -Name $script:SERVICE_NAME -Force -ErrorAction SilentlyContinue
        sc.exe delete $script:SERVICE_NAME 2>&1 | Out-Null
        Start-Sleep -Seconds 2
    }

    Unregister-ScheduledTask -TaskName $script:TASK_NAME -Confirm:$false -ErrorAction SilentlyContinue

    try {
        if ($script:UsePythonMode -and -not $LocalBinary) {
            $ra = $script:RunAgentScript
            $wdir = Split-Path -Parent $ra
            $action = New-ScheduledTaskAction -Execute "powershell.exe" `
                -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$ra`"" -WorkingDirectory $wdir
        }
        else {
            $exe = $script:AgentExe
            $cfg = $script:ConfigYml
            $arg = "--config `"$cfg`" run"
            $wdir = Split-Path -Parent $exe
            $action = New-ScheduledTaskAction -Execute $exe -Argument $arg -WorkingDirectory $wdir
        }
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
    Write-Step "9/10 启动验证"

    try {
        Start-ScheduledTask -TaskName $script:TASK_NAME -ErrorAction Stop
    }
    catch {
        Fail $script:E005 "E005: 计划任务启动失败 - $_"
    }

    Start-Sleep -Seconds 3
    Write-Ok "已触发计划任务启动 Agent"

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

# ── Step 9: 完成输出 ─────────────────────────────────────────────

function Show-Summary {
    Write-Step "10/10 安装完成"

    $root = $script:InstallRoot
    Write-Host ""
    Write-Host "  安装目录 : $root" -ForegroundColor Cyan
    Write-Host "  配置文件 : $root\config\config.yml" -ForegroundColor Cyan
    Write-Host "  日志文件 : $root\logs\agent.log" -ForegroundColor Cyan
    Write-Host "  计划任务 : $($script:TASK_NAME) (登录时运行)" -ForegroundColor Cyan
    Write-Host "  健康检查 : http://127.0.0.1:$Port/health" -ForegroundColor Cyan
    if ($script:UsePythonMode -and -not $LocalBinary) {
        Write-Host "  运行方式 : Python venv + 仓库 $($script:RepoRootResolved)" -ForegroundColor Cyan
    }
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
    $script:UsePythonMode = $true
    if ($UseBinary) { $script:UsePythonMode = $false }
    if ($LocalBinary) { $script:UsePythonMode = $false }

    Test-Environment
    Get-InstallConfig
    Ensure-OpenClawNodeRuntime
    Test-OpenClawNetworkReady
    Install-OpenClawOfficial
    Install-OpenClawPreload
    Get-AgentBinary
    Install-Agent
    Register-Service
    Start-AndVerify
    Show-Summary

    return 0
}

$exitCode = Main
exit $exitCode
