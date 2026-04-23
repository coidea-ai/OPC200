#Requires -Version 5.1
param(
    [switch]$Silent,
    [string]$OpenClawAuthChoice = "",
    [string]$GatewayPort = "18789"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
function Set-NativeCommandStderrNoThrow {
    try { $global:PSNativeCommandUseErrorActionPreference = $false } catch {}
    try { $PSNativeCommandUseErrorActionPreference = $false } catch {}
}

Set-NativeCommandStderrNoThrow

function Invoke-Native {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Set-NativeCommandStderrNoThrow
        & $FilePath @ArgumentList 2>$null
        if ($null -eq $LASTEXITCODE) { return 0 }
        return [int]$LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Invoke-NativeText {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$ArgumentList = @()
    )
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Set-NativeCommandStderrNoThrow
        $out = & $FilePath @ArgumentList 2>$null
        $code = if ($null -eq $LASTEXITCODE) { 0 } else { [int]$LASTEXITCODE }
        return [pscustomobject]@{ ExitCode = $code; Output = $out }
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Invoke-NpmProcess {
    <#
    全局 $ErrorActionPreference 为 Stop。禁止在本脚本内改为直接 & npm / npm.cmd：
    stderr 在 PS5/7 上可触发「因为首选项变量 ErrorActionPreference（或通用参数）设置为 Stop」类终止。

    须用 Start-Process 重定向 stdout/stderr；本函数内另设 EAP=Continue 与 Set-NativeCommandStderrNoThrow
    与重定向双保险，不得省略。
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$NpmPath,
        [Parameter(Mandatory)][string[]]$ArgumentList
    )
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName() + ".err"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Set-NativeCommandStderrNoThrow
        $p = Start-Process -FilePath $NpmPath -ArgumentList $ArgumentList -WorkingDirectory (Get-Location).Path `
            -NoNewWindow -PassThru -RedirectStandardOutput $outFile -RedirectStandardError $errFile -ErrorAction Continue
        if (-not $p) { return 1 }
        $t0 = Get-Date
        $id = 91
        while ($true) {
            if ($p.WaitForExit(1000)) { break }
            $sec = [int]((Get-Date) - $t0).TotalSeconds
            Write-Progress -Id $id -Activity "OpenClaw npm 离线安装" -Status "进行中… 已 $sec 秒（大缓存可能需数分钟，请勿关闭）" -PercentComplete -1 -ErrorAction SilentlyContinue
        }
        Write-Progress -Id $id -Activity "OpenClaw npm 离线安装" -Completed -ErrorAction SilentlyContinue
        if ($p.ExitCode -is [int]) { return $p.ExitCode }
        if ($null -ne $p.ExitCode) { return [int]$p.ExitCode }
        return 0
    } finally {
        $ErrorActionPreference = $prevEap
        Write-Progress -Id 91 -Activity "OpenClaw npm 离线安装" -Completed -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $outFile -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
    }
}

$script:ScriptDir = $null
if (-not [string]::IsNullOrWhiteSpace($PSScriptRoot)) {
    $script:ScriptDir = $PSScriptRoot
} elseif (-not [string]::IsNullOrWhiteSpace($PSCommandPath)) {
    $script:ScriptDir = Split-Path -Parent $PSCommandPath
} elseif ($MyInvocation -and $MyInvocation.MyCommand -and ($MyInvocation.MyCommand.PSObject.Properties.Name -contains "Path")) {
    $script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    $script:ScriptDir = (Get-Location).Path
}
$script:TemplatesDir = Join-Path $script:ScriptDir "openclaw-templates"
$script:NodeOfflineDir = Join-Path $script:ScriptDir "node-v22.22.2"
$script:NpmCacheDir = Join-Path $script:ScriptDir "openclaw-npm-cache"
$script:OpenClawSkillsDir = Join-Path $script:ScriptDir "openclaw-skills"
$script:OpenClawSkillsZip = Join-Path $script:OpenClawSkillsDir "skills.zip"
$script:OpenClawNpmVersion = "2026.4.15"
$script:DefaultSkills = "skill-vetter"
$script:DashboardUrl = ""
$script:SkipInstallOpenClawFromNpm = $false

function Write-Step([string]$m) { Write-Host "[STEP] $m" -ForegroundColor Cyan }
function Write-Ok([string]$m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host " [WARN] $m" -ForegroundColor Yellow }
function Fail([string]$m) { Write-Host "  [ERR] $m" -ForegroundColor Red; exit 1 }

function Get-CommandInvocationPath {
    param($Cmd)
    if ($null -eq $Cmd) { return $null }
    if ($Cmd -is [string]) { return $Cmd }
    if ($Cmd -is [Array]) { $Cmd = $Cmd | Select-Object -First 1 }
    if ($null -eq $Cmd) { return $null }
    foreach ($n in @("Source", "Path")) {
        $prop = $Cmd.PSObject.Properties[$n]
        if ($null -ne $prop) {
            $p = $prop.Value
            if ($null -ne $p) {
                $s = $p.ToString()
                if (-not [string]::IsNullOrWhiteSpace($s)) { return $s.Trim() }
            }
        }
    }
    return $null
}

function Get-OpenClawCmd {
    $a = Get-Command -Name "openclaw" -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($a) { return (Get-CommandInvocationPath $a) }
    $cmd = Get-Command "openclaw" -ErrorAction SilentlyContinue
    return (Get-CommandInvocationPath $cmd)
}

function Get-NodeVersionLine {
    $node = Get-Command node -ErrorAction SilentlyContinue
    $nodePath = Get-CommandInvocationPath $node
    if ([string]::IsNullOrWhiteSpace($nodePath)) { return "" }
    $nv = Invoke-NativeText -FilePath $nodePath -ArgumentList @("-v")
    if ($nv.ExitCode -ne 0) { return "" }
    return ("$($nv.Output)").Trim()
}

function Test-NodeMatchesPinned {
    $v = Get-NodeVersionLine
    if ([string]::IsNullOrWhiteSpace($v)) { return $false }
    return $v.StartsWith("v22.22.2")
}

function Install-NodeFromOfflineBundle {
    Write-Step "1/6 环境检测：Node 离线安装"
    if (-not (Test-Path -LiteralPath $script:NodeOfflineDir)) {
        Fail "未找到离线 Node 目录: $($script:NodeOfflineDir)"
    }
    $arch = $env:PROCESSOR_ARCHITECTURE
    $zipName = "node-v22.22.2-win-x64.zip"
    if ($arch -eq "x86") { $zipName = "node-v22.22.2-win-x86.zip" }
    $zipPath = Join-Path $script:NodeOfflineDir $zipName
    if (-not (Test-Path -LiteralPath $zipPath)) {
        Fail "离线 Node 安装包缺失: $zipPath"
    }
    Write-Ok "使用离线 Node 安装包: $zipPath"
    $nodeRoot = Join-Path $env:LOCALAPPDATA "node-v22.22.2"
    if (Test-Path -LiteralPath $nodeRoot) {
        Remove-Item -LiteralPath $nodeRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
    New-Item -ItemType Directory -Path $nodeRoot -Force | Out-Null
    Expand-Archive -LiteralPath $zipPath -DestinationPath $nodeRoot -Force
    $nodeExe = Get-ChildItem -LiteralPath $nodeRoot -Recurse -File -Filter "node.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $nodeExe) {
        Fail "离线 Node 解压后未找到 node.exe: $zipPath"
    }
    $nodeBin = Split-Path -Parent $nodeExe.FullName
    $oldUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if (-not "$oldUserPath".ToLower().Contains($nodeBin.ToLower())) {
        [Environment]::SetEnvironmentVariable("Path", "$nodeBin;$oldUserPath", "User")
    }
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$nodeBin;$machinePath;$userPath"
}

function Test-NetworkReachable {
    try {
        $ok = Test-NetConnection -ComputerName "openclaw.ai" -Port 443 -InformationLevel Quiet -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        return [bool]$ok
    } catch {
        return $false
    }
}

function Get-LocalPortConnSummary {
    param([int]$Port)
    $rows = @(Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 16)
    $parts = foreach ($r in $rows) {
        $owningPid = [int]$r.OwningProcess
        $nm = ""
        if ($owningPid -gt 0) {
            $pr = Get-Process -Id $owningPid -ErrorAction SilentlyContinue
            if ($pr) { $nm = $pr.ProcessName }
        }
        "pid=$owningPid state=$($r.State) name=$nm"
    }
    if ($parts.Count -eq 0) { return "(无明细)" }
    return ($parts -join "; ")
}

function Test-NoListenerOnGatewayPort {
    param([int]$Port)
    $listen = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
    return ($listen.Count -eq 0)
}

function Try-ReleaseLocalPort {
    param([int]$Port)
    if (Test-NoListenerOnGatewayPort $Port) { return $true }

    $oc = Get-OpenClawCmd
    if ($oc) {
        try { [void](Invoke-Native -FilePath $oc -ArgumentList @("gateway", "stop")) } catch {}
    }
    foreach ($t in @(Get-ScheduledTask -TaskName "OpenClaw Gateway" -ErrorAction SilentlyContinue)) {
        try { Stop-ScheduledTask -InputObject $t -ErrorAction SilentlyContinue } catch {}
    }

    for ($attempt = 1; $attempt -le 4; $attempt++) {
        $conns = @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
        if ($conns.Count -eq 0) { return $true }
        $ids = $conns | Select-Object -ExpandProperty OwningProcess -Unique | Where-Object { $_ -gt 0 }
        foreach ($procId in $ids) {
            try {
                $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
                if ($p) { Stop-Process -Id $procId -Force -ErrorAction Stop }
            } catch {}
        }
        Start-Sleep -Seconds 2
        if (Test-NoListenerOnGatewayPort $Port) { return $true }
    }
    return $false
}

function Test-IsAdministrator {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Run-HardChecks {
    Write-Step "1/6 环境检测（硬检测）"
    if (-not (Test-IsAdministrator)) {
        Fail "请使用管理员身份运行本安装脚本（右键「以管理员身份运行」打开 PowerShell 后再执行）。"
    }
    Write-Ok "当前以管理员身份运行"
    $portInt = 0
    if (-not [int]::TryParse($GatewayPort, [ref]$portInt)) {
        Fail "GatewayPort 非法: $GatewayPort"
    }

    $targetRoot = Join-Path $env:LOCALAPPDATA "OpenClaw"
    if (-not (Test-Path -LiteralPath $targetRoot)) {
        New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
    }
    $probeFile = Join-Path $targetRoot ".write_probe"
    try {
        [System.IO.File]::WriteAllText($probeFile, "ok")
        Remove-Item -LiteralPath $probeFile -Force -ErrorAction SilentlyContinue
    } catch {
        Fail "安装目录不可写: $targetRoot"
    }
    Write-Ok "安装目录可写: $targetRoot"

    $listeners = @(Get-NetTCPConnection -LocalPort $portInt -State Listen -ErrorAction SilentlyContinue)
    $anyTcp = @(Get-NetTCPConnection -LocalPort $portInt -ErrorAction SilentlyContinue)
    if ($listeners.Count -gt 0) {
        Write-Warn "网关端口 $portInt 已有进程在监听（Listen），正在尝试结束占用进程..."
        if (-not (Try-ReleaseLocalPort -Port $portInt)) {
            $detail = Get-LocalPortConnSummary -Port $portInt
            Fail "网关端口 $portInt 仍有 Listen 占用（已尝试 openclaw gateway stop、结束计划任务「OpenClaw Gateway」及结束占用进程）。当前: $detail。请手动关闭占用程序或使用 -GatewayPort 指定其他端口。"
        }
        Write-Ok "网关端口已释放: $portInt"
    } elseif ($anyTcp.Count -gt 0) {
        Write-Warn "网关端口 $portInt 仅有 TCP 过渡状态（如 TimeWait/FinWait2），无 Listen，不阻塞本机网关绑定，继续。"
    }
    Write-Ok "网关端口可用: $portInt"

    if (-not (Test-NetworkReachable)) {
        Write-Warn "网络不可达 openclaw.ai:443（离线安装仍可继续）"
    } else {
        Write-Ok "网络可达: openclaw.ai:443"
    }

    if (-not (Test-NodeMatchesPinned)) {
        $cur = Get-NodeVersionLine
        Write-Warn "Node 未对齐 22.22.2 LTS（当前: $cur），使用离线 Node 安装包"
        Install-NodeFromOfflineBundle
        if (-not (Test-NodeMatchesPinned)) {
            Fail "Node 版本仍非 22.22.2，请检查离线 Node 包或 PATH"
        }
    }
    Write-Ok "Node 版本: $(Get-NodeVersionLine)"

    $script:SkipInstallOpenClawFromNpm = $false
    $ocExe = Get-OpenClawCmd
    if ($ocExe) {
        $ov = ""
        $verOut = Invoke-NativeText -FilePath $ocExe -ArgumentList @("--version")
        $vtext = if ($null -eq $verOut.Output) { "" } elseif ($verOut.Output -is [string]) { $verOut.Output } else { ($verOut.Output | ForEach-Object { "$_" }) -join [Environment]::NewLine }
        foreach ($line in ($vtext -split "\r?\n")) {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                $ov = $line.Trim()
                break
            }
        }
        if ([string]::IsNullOrWhiteSpace($ov)) { $ov = "（未能读取版本）" }
        Write-Ok "OpenClaw 版本: $ov"
        $script:SkipInstallOpenClawFromNpm = $true
    }
}

function Install-OpenClawFromOfflineNpm {
    Write-Step "2/6 安装 OpenClaw（npm 离线缓存，openclaw@$($script:OpenClawNpmVersion)）"
    if (-not (Test-Path -LiteralPath $script:NpmCacheDir)) {
        Fail "未找到 npm 离线缓存目录: $($script:NpmCacheDir)（发布前需执行 fetch-openclaw-npm-cache.ps1 灌 cache）"
    }
    $cacheProbe = Get-ChildItem -LiteralPath $script:NpmCacheDir -ErrorAction SilentlyContinue
    if (-not $cacheProbe -or $cacheProbe.Count -eq 0) {
        Fail "npm 离线缓存目录为空: $($script:NpmCacheDir)"
    }
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCmd) { $npmCmd = Get-Command npm -ErrorAction SilentlyContinue }
    if (-not $npmCmd) {
        Fail "未找到 npm 命令，请确认 Node 22.22.2 安装目录含 npm.cmd"
    }
    $cacheFull = (Resolve-Path -LiteralPath $script:NpmCacheDir).Path
    $env:npm_config_cache = $cacheFull
    $env:npm_config_registry = "https://registry.npmjs.org/"
    $env:npm_config_loglevel = "warn"
    $spec = "openclaw@$($script:OpenClawNpmVersion)"
    $npmPath = Get-CommandInvocationPath $npmCmd
    if ([string]::IsNullOrWhiteSpace($npmPath)) { Fail "无法解析 npm 可执行文件路径" }
    $npmExit = Invoke-NpmProcess -NpmPath $npmPath -ArgumentList @(
        "install", "-g", $spec, "--offline", "--prefer-offline", "--no-audit", "--no-fund"
    )
    if ($npmExit -ne 0) {
        Fail "npm install -g $spec 失败（离线）。请确认 cache 与当前 Windows/Node 22.22.2 匹配。"
    }
    $npmGlobalBin = Join-Path $env:APPDATA "npm"
    if (Test-Path -LiteralPath $npmGlobalBin) {
        $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $env:Path = "$npmGlobalBin;$machinePath;$userPath"
        $oldUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if (-not "$oldUserPath".ToLower().Contains($npmGlobalBin.ToLower())) {
            [Environment]::SetEnvironmentVariable("Path", "$npmGlobalBin;$oldUserPath", "User")
        }
    }
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Fail "未找到 openclaw 命令。请确认 npm 全局目录在 PATH: $npmGlobalBin"
    }
    Write-Ok "openclaw 命令可用"
}

function Read-RequiredLine([string]$prompt) {
    while ($true) {
        $v = Read-Host $prompt
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    }
}

function Format-CmdExeMetacharToken([string]$Text) {
    if ($null -eq $Text) { return '""' }
    $t = "$Text"
    if ($t -match '[\s"&|<>^]') { '"' + ($t -replace '"', '""') + '"' } else { $t }
}

function Read-DashboardUrlFromCliOutput([string]$Raw) {
    if ([string]::IsNullOrWhiteSpace($Raw)) { return $null }
    $c = [regex]::Replace($Raw, '\x1b\[[0-?]*[ -/]*[@-~]', '')
    foreach ($pattern in @(
        '(?i)https?://(?:127\.0\.0\.1|localhost)(?::\d+)?[^\s\r\n"\x1b<>]*#(?:token|access_token)=[^\s\r\n"\x1b<>`]+',
        '(?i)https?://(?:127\.0\.0\.1|localhost)(?::\d+)?[^\s\r\n"\x1b<>]*\?(?:[^\s\r\n#]*&)*(?:token|access_token)=[^&\s\r\n"\x1b<>]+[^\s\r\n"\x1b<>]*'
    )) {
        $mx = [regex]::Match($c, $pattern)
        if ($mx.Success) { return $mx.Value.Trim() }
    }
    $m = [regex]::Match($c, '(?i)Dashboard\s+URL:\s*(https?://[^\r\n]+)')
    if ($m.Success) {
        $u = ($m.Groups[1].Value.Trim().Trim('"').Trim() -replace '\s+$', '')
        if ($u -match '(?i)#(?:token|access_token)=') { return $u }
        if ($u -match '(?i)(?:\?|&)(?:token|access_token)=') { return $u }
        $fh = [regex]::Match($c, '(?i)#(?:token|access_token)=[a-zA-Z0-9_.+\-]{8,}')
        if ($fh.Success) {
            return ($u.TrimEnd('/')) + $fh.Value
        }
        return $u
    }
    return $null
}

function Invoke-OpenClawLongRunning {
    param(
        [Parameter(Mandatory)][string]$ExePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [string]$StepLabel = "openclaw"
    )
    $outPath = [System.IO.Path]::GetTempFileName()
    $errPath = $outPath + ".err"
    $maxSec = 1800
    if ($env:OPENCLAW_ONBOARD_TIMEOUT_SEC) {
        $t = 0
        if ([int]::TryParse($env:OPENCLAW_ONBOARD_TIMEOUT_SEC, [ref]$t) -and $t -gt 0) { $maxSec = $t }
    }
    $start = [DateTime]::UtcNow
    try {
        $ext = [System.IO.Path]::GetExtension($ExePath).ToLowerInvariant()
        if ($ext -eq ".exe") {
            $p = Start-Process -FilePath $ExePath -ArgumentList $ArgumentList -WorkingDirectory $PWD.Path `
                -PassThru -NoNewWindow -RedirectStandardOutput $outPath -RedirectStandardError $errPath
        } else {
            $cmdExe = if ($env:ComSpec) { $env:ComSpec } else { Join-Path $env:SystemRoot "System32\cmd.exe" }
            $tokens = [System.Collections.Generic.List[string]]::new()
            [void]$tokens.Add((Format-CmdExeMetacharToken $ExePath))
            foreach ($a in $ArgumentList) { [void]$tokens.Add((Format-CmdExeMetacharToken $a)) }
            $cmdLine = $tokens -join " "
            $p = Start-Process -FilePath $cmdExe -ArgumentList @("/d", "/s", "/c", $cmdLine) -WorkingDirectory $PWD.Path `
                -PassThru -NoNewWindow -RedirectStandardOutput $outPath -RedirectStandardError $errPath
        }
        if (-not $p) { return -1 }
        while (-not $p.HasExited) {
            if ($p.WaitForExit(8000)) { break }
            $sec = [int]([DateTime]::UtcNow - $start).TotalSeconds
            Write-Host "  [..] $StepLabel 进行中，已等待 ${sec}s…" -ForegroundColor DarkGray
            if ($sec -ge $maxSec) {
                try { if (-not $p.HasExited) { $p.Kill() } } catch {}
                Remove-Item -LiteralPath $outPath -Force -ErrorAction SilentlyContinue
                Remove-Item -LiteralPath $errPath -Force -ErrorAction SilentlyContinue
                Fail "$StepLabel 超时（>${maxSec}s），已中止进程。可提高环境变量 OPENCLAW_ONBOARD_TIMEOUT_SEC 后重试。"
            }
        }
        $p.WaitForExit()
        $code = $p.ExitCode
        if ($null -eq $code) { return 0 }
        return [int]$code
    } finally {
        Remove-Item -LiteralPath $outPath -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $errPath -Force -ErrorAction SilentlyContinue
    }
}

function Get-CustomProviderApiMode {
    param([string]$Compat)
    $c = if ($Compat) { $Compat.Trim().ToLowerInvariant() } else { "openai" }
    if ($c -like "anthropic*") { return "anthropic-messages" }
    return "openai-completions"
}

function New-SafeProviderId {
    param([string]$Raw, [string]$Fallback = "custom")
    if ([string]::IsNullOrWhiteSpace($Raw)) { return $Fallback }
    $s = $Raw.Trim().ToLowerInvariant() -replace "\.+", "-"
    if ($s -notmatch "^[a-z][a-z0-9_-]*$") { return $Fallback }
    return $s
}

function Configure-OpenClawModel {
    Write-Step "3/6 模型配置（config + models）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令，请重新打开 PowerShell 后重试" }

    $auth = $OpenClawAuthChoice.Trim()
    if (-not $auth -and $env:OPENCLAW_AUTH_CHOICE) { $auth = $env:OPENCLAW_AUTH_CHOICE.Trim() }
    if (-not $auth -and -not $Silent) {
        Write-Host "请选择需要配置的模型"
        Write-Host "A) Claude API Key"
        Write-Host "B) OpenAI API Key"
        Write-Host "C) Gemini API Key"
        Write-Host "D) 自定义 API Key"
        $pick = (Read-Host "选择 [ABCD 其中一个]").Trim().ToUpperInvariant()
        switch ($pick) {
            "A" { $auth = "apiKey" }
            "B" { $auth = "openai-api-key" }
            "C" { $auth = "gemini-api-key" }
            "D" { $auth = "custom-api-key" }
            default { Fail "无效选择，请输入 A、B、C 或 D" }
        }
    }
    if (-not $auth) { Fail "静默模式必须指定 OpenClawAuthChoice 或 OPENCLAW_AUTH_CHOICE" }

    $defaultBundled = @{
        "apiKey"            = "anthropic/claude-sonnet-4-5"
        "openai-api-key"    = "openai/gpt-4.1"
        "gemini-api-key"    = "google/gemini-2.5-flash"
    }

    if ($auth -eq "custom-api-key") {
        if (-not $env:OPENCLAW_CUSTOM_BASE_URL) { $env:OPENCLAW_CUSTOM_BASE_URL = Read-RequiredLine "OpenClaw 自定义模型的 Base Url" }
        if (-not $env:OPENCLAW_CUSTOM_MODEL_ID) { $env:OPENCLAW_CUSTOM_MODEL_ID = Read-RequiredLine "OpenClaw 自定义模型的 ID" }
        if (-not $env:CUSTOM_API_KEY) { $env:CUSTOM_API_KEY = Read-RequiredLine "OpenClaw 自定义模型的 api key" }
        $compat = if ($env:OPENCLAW_CUSTOM_COMPATIBILITY) { $env:OPENCLAW_CUSTOM_COMPATIBILITY.Trim() } else { "openai" }
        $apiMode = Get-CustomProviderApiMode -Compat $compat
        $providerId = New-SafeProviderId -Raw $(if ($env:OPENCLAW_CUSTOM_PROVIDER_ID) { $env:OPENCLAW_CUSTOM_PROVIDER_ID } else { "custom" })
        $baseUrl = $env:OPENCLAW_CUSTOM_BASE_URL.Trim().TrimEnd("/")
        $mid = $env:OPENCLAW_CUSTOM_MODEL_ID.Trim()
        $provObj = [ordered]@{
            baseUrl = $baseUrl
            api     = $apiMode
            apiKey  = '${CUSTOM_API_KEY}'
            models  = @(
                [ordered]@{ id = $mid; name = $mid }
            )
        }
        $provJson = ($provObj | ConvertTo-Json -Compress -Depth 8)
        $refKey = "$providerId/$mid"
        $allowMerge = @{}
        $allowMerge[$refKey] = @{}
        $allowJson = $allowMerge | ConvertTo-Json -Compress -Depth 5

        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "models.mode", "merge")) -ne 0) {
            Write-Warn "config set models.mode merge 非 0，继续"
        }
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "models.providers.$providerId", $provJson, "--strict-json", "--merge")) -ne 0) {
            Fail "openclaw config set models.providers 失败"
        }
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "agents.defaults.models", $allowJson, "--strict-json", "--merge")) -ne 0) {
            Fail "openclaw config set agents.defaults.models 失败"
        }
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "agents.defaults.model.primary", $refKey)) -ne 0) {
            Fail "openclaw config set agents.defaults.model.primary 失败"
        }
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("models", "set", $refKey)) -ne 0) {
            Fail "openclaw models set 失败: $refKey"
        }
    } else {
        switch ($auth) {
            "apiKey" {
                if (-not $env:ANTHROPIC_API_KEY) { $env:ANTHROPIC_API_KEY = Read-RequiredLine "ANTHROPIC_API_KEY" }
            }
            "openai-api-key" {
                if (-not $env:OPENAI_API_KEY) { $env:OPENAI_API_KEY = Read-RequiredLine "OPENAI_API_KEY" }
            }
            "gemini-api-key" {
                if (-not $env:GEMINI_API_KEY) { $env:GEMINI_API_KEY = Read-RequiredLine "GEMINI_API_KEY" }
            }
            default { Fail "不支持的 OPENCLAW_AUTH_CHOICE: $auth（预期 apiKey / openai-api-key / gemini-api-key / custom-api-key）" }
        }
        $modelRef = if ($env:OPENCLAW_MODEL_REF -and $env:OPENCLAW_MODEL_REF.Trim()) { $env:OPENCLAW_MODEL_REF.Trim() } else { $defaultBundled[$auth] }
        if (-not $modelRef) { Fail "无法解析默认模型引用（auth=$auth）" }
        if (-not $Silent) {
            $hint = Read-Host "模型 provider/model [回车=$modelRef]"
            if (-not [string]::IsNullOrWhiteSpace($hint)) { $modelRef = $hint.Trim() }
        }
        $allowBundled = @{}
        $allowBundled[$modelRef] = @{}
        $allowOne = $allowBundled | ConvertTo-Json -Compress -Depth 5
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "agents.defaults.models", $allowOne, "--strict-json", "--merge")) -ne 0) {
            Write-Warn "agents.defaults.models merge 非 0，继续"
        }
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "agents.defaults.model.primary", $modelRef)) -ne 0) {
            Fail "openclaw config set agents.defaults.model.primary 失败"
        }
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("models", "set", $modelRef)) -ne 0) {
            Fail "openclaw models set 失败: $modelRef"
        }
    }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "validate")) -ne 0) {
        Write-Warn "openclaw config validate 非 0，请检查 openclaw.json"
    } else {
        Write-Ok "openclaw config validate 通过"
    }
    [void](Invoke-Native -FilePath $cmd -ArgumentList @("models", "status"))
    Write-Ok "模型配置完成（config + models）"
}

function Write-TemplatesAndSkills {
    Write-Step "4/6 轻预装（tools/skills/docs）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令" }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "tools.profile", "full")) -ne 0) { Write-Warn "tools.profile 设置失败" }
    # 旧逻辑封存：在线安装 skills（openclaw skills install）
    # & $cmd skills install $script:DefaultSkills
    # if ($LASTEXITCODE -ne 0) { Write-Warn "skills 安装失败: $($script:DefaultSkills)" }

    $profileDir = if ($env:OPENCLAW_PROFILE_DIR) { $env:OPENCLAW_PROFILE_DIR } else { Join-Path $HOME ".openclaw" }
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    if (-not (Test-Path -LiteralPath $script:OpenClawSkillsZip)) {
        Fail "未找到内置 skills 资源包: $($script:OpenClawSkillsZip)"
    }
    $skillsDir = Join-Path $profileDir "skills"
    New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null
    Expand-Archive -LiteralPath $script:OpenClawSkillsZip -DestinationPath $skillsDir -Force
    Write-Ok "skills 已解压到: $skillsDir"
    foreach ($name in @("AGENTS.md", "IDENTITY.md", "SOUL.md")) {
        $src = Join-Path $script:TemplatesDir $name
        if (Test-Path -LiteralPath $src) {
            $dst = Join-Path $profileDir $name
            if (Test-Path -LiteralPath $dst) {
                Copy-Item -LiteralPath $src -Destination ($dst + ".new") -Force
            } else {
                Copy-Item -LiteralPath $src -Destination $dst -Force
            }
        }
    }
    Write-Ok "轻预装完成"
}

function Test-GatewayRpcOk {
    param([Parameter(Mandatory)][string]$OpenClawExe)
    $code = Invoke-Native -FilePath $OpenClawExe -ArgumentList @("gateway", "status", "--json", "--require-rpc")
    return ($code -eq 0)
}

function Test-GatewayHttpOk {
    param([Parameter(Mandatory)][int]$ListenPort)
    foreach ($h in @("127.0.0.1", "localhost")) {
        foreach ($p in @("/health", "/", "/chat")) {
            $u = "http://${h}:${ListenPort}${p}"
            try {
                $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 5
                if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
            } catch { }
        }
    }
    return $false
}

function Wait-GatewayRpcReady {
    param(
        [Parameter(Mandatory)][string]$OpenClawExe,
        [Parameter(Mandatory)][int]$ListenPort,
        [int]$MaxAttempts = 15,
        [int]$IntervalSec = 4
    )
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        if (Test-GatewayRpcOk -OpenClawExe $OpenClawExe) { return $true }
        if (Test-GatewayHttpOk -ListenPort $ListenPort) { return $true }
        Write-Host "  [..] 等待网关就绪（$i/$MaxAttempts，RPC 与 HTTP 每 ${IntervalSec}s 探测）…" -ForegroundColor DarkGray
        Start-Sleep -Seconds $IntervalSec
    }
    return $false
}

function Configure-Gateway {
    Write-Step "5/6 网关配置与验证"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令" }

    try { [void](Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "stop")) } catch {}
    Start-Sleep -Seconds 4

    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "gateway.mode", "local")) -ne 0) { Write-Warn "gateway.mode 设置返回非 0" }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "gateway.tls.enabled", "false")) -ne 0) { Write-Warn "gateway.tls.enabled 设置返回非 0" }

    $gwi = Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "install", "--force", "--port", "$GatewayPort")
    if ($gwi -ne 0) {
        Write-Warn "gateway install --force 失败，尝试无 --force"
        [void](Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "install", "--port", "$GatewayPort"))
    }

    [void](Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "restart"))
    Start-Sleep -Seconds 5

    $gPort = 0
    if (-not [int]::TryParse($GatewayPort, [ref]$gPort)) { $gPort = 18789 }
    if ($gPort -le 0) { $gPort = 18789 }
    if (-not (Wait-GatewayRpcReady -OpenClawExe $cmd -ListenPort $gPort)) {
        Write-Warn "网关就绪探测未通过，将执行 doctor 后重装网关（doctor 可能需数分钟，会有进度提示）"
        Write-Host "  [i] openclaw doctor --non-interactive（长时任务，每 8s 打点）…" -ForegroundColor DarkGray
        $docCode = Invoke-OpenClawLongRunning -ExePath $cmd -ArgumentList @("doctor", "--non-interactive") -StepLabel "openclaw doctor"
        if ($docCode -ne 0) { Write-Warn "doctor 退出码 $docCode ，仍继续重装网关" }
        Write-Host "  [i] gateway stop → install → restart …" -ForegroundColor DarkGray
        try { [void](Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "stop")) } catch {}
        Start-Sleep -Seconds 4
        [void](Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "install", "--force", "--port", "$GatewayPort"))
        [void](Invoke-Native -FilePath $cmd -ArgumentList @("gateway", "restart"))
        Start-Sleep -Seconds 5
        if (-not (Wait-GatewayRpcReady -OpenClawExe $cmd -ListenPort $gPort -MaxAttempts 12 -IntervalSec 5)) {
            Fail "网关启动失败（RPC 多次探测仍超时）。可手动: openclaw gateway stop；openclaw gateway install --force --port $GatewayPort；openclaw gateway restart；再执行 openclaw gateway status --deep。"
        }
    }
    Write-Ok "OpenClaw 安装完成: http://127.0.0.1:$GatewayPort"
}

function Get-DashboardUrlFromCli {
    param([string]$FallbackUrl)
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { return $FallbackUrl }
    $workDir = $PWD.Path
    Write-Host "  [i] 正在通过 PowerShell Job 运行 openclaw dashboard（捕获 stdout/stderr）…" -ForegroundColor DarkGray
    $maxAttempts = 2
    for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
        $job = Start-Job -ScriptBlock {
            param([string]$OpenClawExe, [string]$WorkDir)
            Set-Location -LiteralPath $WorkDir
            $ErrorActionPreference = "Continue"
            try { $global:PSNativeCommandUseErrorActionPreference = $false } catch {}
            try { $PSNativeCommandUseErrorActionPreference = $false } catch {}
            & $OpenClawExe @("dashboard") 2>$null | Out-String
        } -ArgumentList @($cmd, $workDir)

        $null = Wait-Job -Job $job -Timeout 50
        if ($job.State -ne "Completed") {
            Stop-Job -Job $job -ErrorAction SilentlyContinue
            Write-Warn "openclaw dashboard Job 未完成（$($job.State)），第 $attempt 次"
        }
        $received = Receive-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
        $blob = if ($null -eq $received) { "" } else { @($received) | Out-String }

        if ($blob.Length -lt 120) {
            Write-Warn "dashboard Job 输出过短（len=$($blob.Length)），第 $attempt 次"
        }
        $url = Read-DashboardUrlFromCliOutput $blob
        if ($url -and ($url -match '(?i)(?:#|\?|&)(?:token|access_token)=')) {
            return $url
        }
        if ($url) {
            Write-Warn "openclaw dashboard 已返回 URL，但未检测到 token 片段，将重试: $url"
        } else {
            $preview = if ($blob.Length -le 400) { $blob } else { $blob.Substring(0, 400) }
            Write-Warn "openclaw dashboard 第 $attempt 次未解析出 URL；输出前 400 字符: $preview"
        }
        if ($attempt -lt $maxAttempts) { Start-Sleep -Seconds 2 }
    }
    Write-Warn "未能从 openclaw dashboard 解析到带 token 的 URL，已回退为 $FallbackUrl。请稍后在本机执行: openclaw dashboard"
    return $FallbackUrl
}

function Write-ShortcutScripts {
    $scriptRoot = Join-Path $env:LOCALAPPDATA "OpenClawInstaller"
    if (-not (Test-Path -LiteralPath $scriptRoot)) {
        New-Item -ItemType Directory -Path $scriptRoot -Force | Out-Null
    }
    $startScript = Join-Path $scriptRoot "openclaw-gateway-start.ps1"
    $stopScript = Join-Path $scriptRoot "openclaw-gateway-stop.ps1"

    $ocExe = Get-OpenClawCmd
    if (-not $ocExe) { $ocExe = "openclaw" }
    $ocB64 = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($ocExe))

    $startContent = @"
`$ErrorActionPreference = 'SilentlyContinue'
if (-not [string]::IsNullOrWhiteSpace(`$PSScriptRoot)) { Set-Location -LiteralPath `$PSScriptRoot }
`$scriptDir = (Get-Location).Path
`$port = $GatewayPort
`$fallback = "http://127.0.0.1:`$port"
`$health = "http://127.0.0.1:`$port/health"
`$ok = `$false
try {
  `$r = Invoke-WebRequest -Uri `$health -UseBasicParsing -TimeoutSec 2
  if (`$r.StatusCode -ge 200 -and `$r.StatusCode -lt 300) { `$ok = `$true }
} catch {}
if (-not `$ok) {
  try { & openclaw gateway start 2>`$null } catch { }
  Start-Sleep -Seconds 2
}
function Parse-DashboardUrl([string]`$raw) {
  if ([string]::IsNullOrWhiteSpace(`$raw)) { return `$null }
  `$c = [regex]::Replace(`$raw, '\x1b\[[0-?]*[ -/]*[@-~]', '')
  foreach (`$pattern in @(
    '(?i)https?://(?:127\.0\.0\.1|localhost)(?::\d+)?[^\s\r\n"\x1b<>]*#(?:token|access_token)=[^\s\r\n"\x1b<>`]+',
    '(?i)https?://(?:127\.0\.0\.1|localhost)(?::\d+)?[^\s\r\n"\x1b<>]*\?(?:[^\s\r\n#]*&)*(?:token|access_token)=[^&\s\r\n"\x1b<>]+[^\s\r\n"\x1b<>]*'
  )) {
    `$mx = [regex]::Match(`$c, `$pattern)
    if (`$mx.Success) { return `$mx.Value.Trim() }
  }
  `$m = [regex]::Match(`$c, '(?i)Dashboard\s+URL:\s*(https?://[^\r\n]+)')
  if (`$m.Success) {
    `$u = (`$m.Groups[1].Value.Trim().Trim('"').Trim() -replace '\s+$', '')
    if (`$u -match '(?i)#(?:token|access_token)=') { return `$u }
    if (`$u -match '(?i)(?:\?|&)(?:token|access_token)=') { return `$u }
    `$fh = [regex]::Match(`$c, '(?i)#(?:token|access_token)=[a-zA-Z0-9_.+\-]{8,}')
    if (`$fh.Success) { return (`$u.TrimEnd('/')) + `$fh.Value }
    return `$u
  }
  return `$null
}
`$ocBin = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('$ocB64'))
`$url = `$fallback
for (`$ti = 1; `$ti -le 2; `$ti++) {
  `$job = Start-Job -ScriptBlock {
    param([string]`$OpenClawExe, [string]`$WorkDir)
    Set-Location -LiteralPath `$WorkDir
    `$ErrorActionPreference = 'Continue'
    try { `$global:PSNativeCommandUseErrorActionPreference = `$false } catch {}
    try { `$PSNativeCommandUseErrorActionPreference = `$false } catch {}
    & `$OpenClawExe @('dashboard') 2>`$null | Out-String
  } -ArgumentList @(`$ocBin, `$scriptDir)
  `$null = Wait-Job -Job `$job -Timeout 50
  if (`$job.State -ne 'Completed') { Stop-Job -Job `$job -ErrorAction SilentlyContinue }
  `$recv = Receive-Job -Job `$job -ErrorAction SilentlyContinue
  Remove-Job -Job `$job -Force -ErrorAction SilentlyContinue
  `$blob = if (`$null -eq `$recv) { '' } else { @(`$recv) | Out-String }
  `$u = Parse-DashboardUrl `$blob
  if (`$u -and (`$u -match '(?i)(?:#|\?|&)(?:token|access_token)=')) { `$url = `$u }
  if (`$url -match '(?i)(?:#|\?|&)(?:token|access_token)=') { break }
  if (`$ti -lt 2) { Start-Sleep -Seconds 2 }
}
if (`$url -notmatch '(?i)(?:#|\?|&)(?:token|access_token)=') {
  Write-Host ' [WARN] 未解析到带 token 的 Dashboard 链接，将打开基础地址；请在终端执行 openclaw dashboard。' -ForegroundColor Yellow
}
try {
  `$psi = [System.Diagnostics.ProcessStartInfo]::new()
  `$psi.FileName = `$url
  `$psi.UseShellExecute = `$true
  [void][System.Diagnostics.Process]::Start(`$psi)
} catch {
  try { Start-Process -FilePath `$url } catch {}
}
"@
    [System.IO.File]::WriteAllText($startScript, $startContent, [System.Text.UTF8Encoding]::new($true))

    $stopContent = @"
`$ErrorActionPreference = 'SilentlyContinue'
try { `$global:PSNativeCommandUseErrorActionPreference = `$false } catch {}
`$ocBin = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('$ocB64'))
& `$ocBin gateway stop 2>`$null
"@
    [System.IO.File]::WriteAllText($stopScript, $stopContent, [System.Text.UTF8Encoding]::new($true))

    return @{
        Start  = $startScript
        Stop   = $stopScript
    }
}

function New-DesktopShortcut {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$TargetPath,
        [Parameter(Mandatory)][string]$Arguments,
        [string]$ShortcutWorkingDirectory = ""
    )
    $desktop = [Environment]::GetFolderPath("Desktop")
    $lnk = Join-Path $desktop ($Name + ".lnk")
    $ws = New-Object -ComObject WScript.Shell
    $sc = $ws.CreateShortcut($lnk)
    $sc.TargetPath = $TargetPath
    $sc.Arguments = $Arguments
    if (-not [string]::IsNullOrWhiteSpace($ShortcutWorkingDirectory)) {
        $sc.WorkingDirectory = $ShortcutWorkingDirectory
    } else {
        $sc.WorkingDirectory = Split-Path -Parent $TargetPath
    }
    $sc.Save()
}

function Create-DesktopShortcuts {
    Write-Step "6/6 创建桌面快捷方式"
    $scripts = Write-ShortcutScripts
    $psExe = Get-CommandInvocationPath (Get-Command powershell.exe -ErrorAction SilentlyContinue)
    if ([string]::IsNullOrWhiteSpace($psExe)) { $psExe = Join-Path $env:SystemRoot "System32\WindowsPowerShell\v1.0\powershell.exe" }

    $shortcutWd = Split-Path -Parent $scripts.Start
    New-DesktopShortcut -Name "OpenClaw Start" -TargetPath $psExe -Arguments "-NoProfile -ExecutionPolicy Bypass -File `"$($scripts.Start)`"" -ShortcutWorkingDirectory $shortcutWd
    New-DesktopShortcut -Name "OpenClaw Stop" -TargetPath $psExe -Arguments "-NoProfile -ExecutionPolicy Bypass -File `"$($scripts.Stop)`"" -ShortcutWorkingDirectory $shortcutWd
    Write-Ok "桌面快捷方式已创建（OpenClaw Start / OpenClaw Stop）"
}

function Open-DashboardUrlInBrowser([string]$TargetUrl) {
    if ([string]::IsNullOrWhiteSpace($TargetUrl)) { return }
    try {
        $psi = [System.Diagnostics.ProcessStartInfo]::new()
        $psi.FileName = $TargetUrl
        $psi.UseShellExecute = $true
        [void][System.Diagnostics.Process]::Start($psi)
    } catch {
        try { Start-Process -FilePath $TargetUrl -ErrorAction SilentlyContinue } catch {}
    }
}

function Show-InstallSuccessDialog {
    Add-Type -AssemblyName System.Windows.Forms
    $url = $script:DashboardUrl
    if (-not $url) { $url = "http://127.0.0.1:$GatewayPort" }
    $hasTok = $url -match '(?i)(?:#|\?|&)(?:token|access_token)='
    $msg = "OpenClaw 安装成功。`r`n`r`n访问地址：$url`r`n"
    if (-not $hasTok) {
        $msg += "（注意：未检测到 token 片段，可能无法直接进入控制台；可在终端执行 openclaw dashboard 获取含 #token= 的完整链接。）`r`n"
    }
    $msg += "已创建桌面快捷方式：OpenClaw Start / OpenClaw Stop`r`n`r`n点击确定后将用默认浏览器打开上述地址。"
    [void][System.Windows.Forms.MessageBox]::Show($msg, "OpenClaw Installer", [System.Windows.Forms.MessageBoxButtons]::OK, [System.Windows.Forms.MessageBoxIcon]::Information)
    Open-DashboardUrlInBrowser -TargetUrl $url
}

Run-HardChecks
if (-not $script:SkipInstallOpenClawFromNpm) {
    Install-OpenClawFromOfflineNpm
} else {
    Write-Ok "已检测到 openclaw，跳过步骤 2/6（npm 离线安装）"
}
Configure-OpenClawModel
Write-TemplatesAndSkills
Configure-Gateway
Start-Sleep -Seconds 4
$script:DashboardUrl = Get-DashboardUrlFromCli -FallbackUrl ("http://127.0.0.1:" + $GatewayPort)
Create-DesktopShortcuts
Show-InstallSuccessDialog
