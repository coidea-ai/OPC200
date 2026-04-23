#Requires -Version 5.1
param(
    [switch]$Silent,
    [string]$OpenClawAuthChoice = "", # 未使用；第 3 步仅支持 Kimi，见 MOONSHOT_API_KEY
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
        $null = & $FilePath @ArgumentList 2>$null
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

function Write-OpenClawCliBlob {
    param([string]$Title, [string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return }
    $s = $Text.Trim()
    if ($s.Length -gt 3000) { $s = $s.Substring(0, 3000) + "`n…" }
    Write-Host "  [i] $Title" -ForegroundColor DarkGray
    Write-Host $s -ForegroundColor DarkGray
}

function Get-OpenClawGateCmdMaxSec {
    $d = 300
    if ($env:OPENCLAW_INSTALLER_GATE_CMD_MAX_SEC) {
        $t = 0
        if ([int]::TryParse($env:OPENCLAW_INSTALLER_GATE_CMD_MAX_SEC, [ref]$t) -and $t -ge 1) { $d = $t }
    }
    return $d
}

function Stop-OpenClawProcessTree {
    param([int]$ProcessId)
    if ($ProcessId -le 0) { return }
    $tk = Join-Path $env:SystemRoot "System32\taskkill.exe"
    if (Test-Path -LiteralPath $tk) {
        $o = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try { $null = & $tk /F /T /PID $ProcessId 2>&1 } catch {}
        $ErrorActionPreference = $o
    } else {
        try { Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue } catch {}
    }
}

# gateway install|restart|stop 会拉起子进程/新窗口；在 PowerShell 用 & 合并 2>&1 时易与控制台管道死锁。此处与 Invoke-NpmProcess 同策略：子进程+重定向+超时。
# 非 .exe 时与 Invoke-OpenClawLongRunning 一致：用 cmd /d /s /c 包一层，避免对 .cmd 直启时子链与等待语义异常。
function Invoke-OpenClawWithRedirect {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList,
        [int]$MaxWaitSec = 0
    )
    if ($MaxWaitSec -le 0) { $MaxWaitSec = (Get-OpenClawGateCmdMaxSec) }
    $outFile = [System.IO.Path]::GetTempFileName()
    $errFile = [System.IO.Path]::GetTempFileName() + ".err"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $workDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { (Get-Location).Path }
    try {
        Set-NativeCommandStderrNoThrow
        $p = $null
        try {
            $ext = [System.IO.Path]::GetExtension($FilePath).ToLowerInvariant()
            if ($ext -eq ".exe") {
                $p = Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $workDir -NoNewWindow -PassThru `
                    -RedirectStandardOutput $outFile -RedirectStandardError $errFile -ErrorAction Stop
            } else {
                $cmdExe = if ($env:ComSpec) { $env:ComSpec } else { Join-Path $env:SystemRoot "System32\cmd.exe" }
                $tlist = [System.Collections.Generic.List[string]]::new()
                [void]$tlist.Add((Format-CmdExeMetacharToken $FilePath))
                foreach ($a in $ArgumentList) { [void]$tlist.Add((Format-CmdExeMetacharToken $a)) }
                $cmdLine = $tlist -join " "
                $p = Start-Process -FilePath $cmdExe -ArgumentList @("/d", "/s", "/c", $cmdLine) -WorkingDirectory $workDir -NoNewWindow -PassThru `
                    -RedirectStandardOutput $outFile -RedirectStandardError $errFile -ErrorAction Stop
            }
        } catch {
            return [pscustomobject]@{ ExitCode = -1; Text = "Start-Process: $($_.Exception.Message)" }
        }
        if (-not $p) { return [pscustomobject]@{ ExitCode = -1; Text = "Start-Process 未返回进程" } }
        $t0 = [DateTime]::UtcNow
        $lastDot = 0
        while ($true) {
            if ($p.WaitForExit(1000)) { break }
            $elapsed = [int]([DateTime]::UtcNow - $t0).TotalSeconds
            if ($elapsed -ge $MaxWaitSec) {
                Stop-OpenClawProcessTree -ProcessId $p.Id
                $o = ""
                if (Test-Path -LiteralPath $outFile) { $o = [System.IO.File]::ReadAllText($outFile) }
                $e = ""
                if (Test-Path -LiteralPath $errFile) { $e = [System.IO.File]::ReadAllText($errFile) }
                $m = "（已超时 $MaxWaitSec 秒，已 taskkill /T 终止进程树）" + [Environment]::NewLine + $o + [Environment]::NewLine + $e
                return [pscustomobject]@{ ExitCode = -1; Text = $m.Trim() }
            }
            if (($elapsed - $lastDot) -ge 20) {
                $lastDot = $elapsed
                try {
                    if (-not $p.HasExited) {
                        Write-Host "  [..] 仍等待子进程 (PID=$($p.Id)) 已 $elapsed 秒 / 最长 $MaxWaitSec 秒…" -ForegroundColor DarkGray
                    }
                } catch { }
            }
        }
        if (-not $p.HasExited) { $p.WaitForExit() }
        $code = 0
        if ($null -ne $p.ExitCode) { $code = [int]$p.ExitCode }
        $o2 = ""
        if (Test-Path -LiteralPath $outFile) { $o2 = [System.IO.File]::ReadAllText($outFile) }
        $e2 = ""
        if (Test-Path -LiteralPath $errFile) { $e2 = [System.IO.File]::ReadAllText($errFile) }
        $merged = ($o2 + [Environment]::NewLine + $e2).Trim()
        return [pscustomobject]@{ ExitCode = $code; Text = $merged }
    } finally {
        $ErrorActionPreference = $prevEap
        Remove-Item -LiteralPath $outFile -Force -ErrorAction SilentlyContinue
        Remove-Item -LiteralPath $errFile -Force -ErrorAction SilentlyContinue
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
        $spinChars = @('|','/','-','\')
        $spinIdx = 0
        $lastPrintSec = -1
        $warned15 = $false
        $maxSec = 1800
        while ($true) {
            if ($p.WaitForExit(300)) { break }
            $sec = [int]((Get-Date) - $t0).TotalSeconds
            $ch = $spinChars[$spinIdx % $spinChars.Count]
            $spinIdx++
            if (-not $warned15 -and $sec -ge 900) {
                $warned15 = $true
                Write-Host ""
                Write-Warn "程序已安装 15 分钟，将在 15 分钟后强制退出"
            }
            if ($sec -ge $maxSec) {
                Write-Host ""
                Stop-OpenClawProcessTree -ProcessId $p.Id
                Write-Host "`r                                                          `r" -NoNewline
                Write-Progress -Id $id -Activity "OpenClaw npm 安装" -Completed -ErrorAction SilentlyContinue
                Invoke-InstallRollback
                Fail "npm install 超时（已等待 30 分钟），已强制终止并回滚。请检查网络或重试。"
            }
            if ($sec -ne $lastPrintSec) {
                $lastPrintSec = $sec
                $min = [int][Math]::Floor($sec / 60)
                $remSec = $sec % 60
                Write-Host "`r  [$ch] npm install 进行中… 已 ${min}m${remSec}s（请勿关闭）" -NoNewline -ForegroundColor DarkGray
            } else {
                Write-Host "`r  [$ch]" -NoNewline -ForegroundColor DarkGray
            }
            Write-Progress -Id $id -Activity "OpenClaw npm 安装" -Status "进行中… 已 $sec 秒" -PercentComplete -1 -ErrorAction SilentlyContinue
        }
        Write-Host "`r                                                          `r" -NoNewline
        Write-Progress -Id $id -Activity "OpenClaw npm 安装" -Completed -ErrorAction SilentlyContinue
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
$script:NodeOfflineDir = Join-Path $script:ScriptDir "node-v24.15.0"
$script:NpmCacheDir = Join-Path $script:ScriptDir "openclaw-npm-cache"
$script:OpenClawSkillsDir = Join-Path $script:ScriptDir "openclaw-skills"
$script:OpenClawSkillsZip = Join-Path $script:OpenClawSkillsDir "skills.zip"
$script:OpenClawNpmVersion = "2026.4.15"
$script:DefaultSkills = "skill-vetter"
$script:DashboardUrl = ""
$script:SkipInstallOpenClawFromNpm = $false
$script:OpenClawExePath = ""

function Write-Step([string]$m) { Write-Host "[STEP] $m" -ForegroundColor Cyan }
function Write-Ok([string]$m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host " [WARN] $m" -ForegroundColor Yellow }
function Fail([string]$m) { Write-Host "  [ERR] $m" -ForegroundColor Red; exit 1 }

function Invoke-InstallRollback {
    Write-Warn "正在回滚已安装的内容…"
    $ocPath = Get-OpenClawCmd
    if ($ocPath) {
        $prevEap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        try {
            Set-NativeCommandStderrNoThrow
            $null = & $ocPath gateway stop 2>$null
            $null = & $ocPath uninstall --all --yes --non-interactive 2>$null
        } catch {} finally { $ErrorActionPreference = $prevEap }
    }
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCmd) { $npmCmd = Get-Command npm -ErrorAction SilentlyContinue }
    if ($npmCmd) {
        $prevEap = $ErrorActionPreference; $ErrorActionPreference = "Continue"
        try {
            Set-NativeCommandStderrNoThrow
            $null = & $npmCmd.Source uninstall -g openclaw 2>$null
        } catch {} finally { $ErrorActionPreference = $prevEap }
    }
    foreach ($varName in @("MOONSHOT_API_KEY", "OPENCLAW_MOONSHOT_REGION")) {
        if ($null -ne [Environment]::GetEnvironmentVariable($varName, "User")) {
            [Environment]::SetEnvironmentVariable($varName, $null, "User")
        }
    }
    $localDir = Join-Path $env:LOCALAPPDATA "OpenClaw"
    if (Test-Path -LiteralPath $localDir) { Remove-Item -LiteralPath $localDir -Recurse -Force -ErrorAction SilentlyContinue }
    $profileDir = if ($env:OPENCLAW_PROFILE_DIR) { $env:OPENCLAW_PROFILE_DIR } else { Join-Path $HOME ".openclaw" }
    if (Test-Path -LiteralPath $profileDir) { Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue }
    Write-Ok "回滚完成"
}

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
    if (-not [string]::IsNullOrWhiteSpace($script:OpenClawExePath) -and (Test-Path -LiteralPath $script:OpenClawExePath)) {
        return $script:OpenClawExePath
    }
    foreach ($name in @("openclaw.cmd", "openclaw.exe", "openclaw")) {
        $rows = @(Get-Command -Name $name -CommandType Application -ErrorAction SilentlyContinue)
        foreach ($row in $rows) {
            $p = Get-CommandInvocationPath $row
            if ([string]::IsNullOrWhiteSpace($p)) { continue }
            if ($p.ToLowerInvariant().EndsWith(".ps1")) { continue }
            return $p
        }
    }
    return $null
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
    return $v.StartsWith("v24.15.0")
}

function Install-NodeFromOfflineBundle {
    Write-Step "1/6 环境检测：Node 离线安装"
    if (-not (Test-Path -LiteralPath $script:NodeOfflineDir)) {
        Fail "未找到离线 Node 目录: $($script:NodeOfflineDir)"
    }
    $arch = $env:PROCESSOR_ARCHITECTURE
    $zipName = "node-v24.15.0-win-x64.zip"
    if ($arch -eq "x86") { $zipName = "node-v24.15.0-win-x86.zip" }
    $zipPath = Join-Path $script:NodeOfflineDir $zipName
    if (-not (Test-Path -LiteralPath $zipPath)) {
        Fail "离线 Node 安装包缺失: $zipPath"
    }
    Write-Ok "使用离线 Node 安装包: $zipPath"
    $nodeRoot = Join-Path $env:LOCALAPPDATA "node-v24.15.0"
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

function Ensure-System32InPath {
    $sys32 = Join-Path $env:SystemRoot "System32"
    if (-not (Test-Path -LiteralPath $sys32)) { return }
    $pathLower = ";$($env:Path.ToLowerInvariant());"
    $sys32Lower = ";$($sys32.ToLowerInvariant());"
    if ($pathLower -notlike "*$sys32Lower*") {
        $env:Path = "$sys32;$env:Path"
        Write-Warn "进程 PATH 缺少 System32，已临时补齐: $sys32"
    }
}

function Run-HardChecks {
    Write-Step "1/6 环境检测（硬检测）"
    Ensure-System32InPath
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
        Write-Warn "Node 未对齐 24.15.0（当前: $cur），使用离线 Node 安装包"
        Install-NodeFromOfflineBundle
        if (-not (Test-NodeMatchesPinned)) {
            Fail "Node 版本仍非 24.15.0，请检查离线 Node 包或 PATH"
        }
    }
    Write-Ok "Node 版本: $(Get-NodeVersionLine)"

    $npmCmd0 = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCmd0) { $npmCmd0 = Get-Command npm -ErrorAction SilentlyContinue }
    if ($npmCmd0) {
        $npmPath0 = Get-CommandInvocationPath $npmCmd0
        $regOut = Invoke-NativeText -FilePath $npmPath0 -ArgumentList @("config", "get", "registry")
        $curReg = if ($regOut.ExitCode -eq 0 -and $regOut.Output) { "$($regOut.Output)".Trim().TrimEnd('/') } else { "" }
        if ($curReg -eq "https://registry.npmjs.org") {
            Write-Warn "npm 源为官方源，切换为淘宝源"
            [void](Invoke-Native -FilePath $npmPath0 -ArgumentList @("config", "set", "registry", "https://registry.npmmirror.com/"))
            Write-Ok "npm registry: https://registry.npmmirror.com/"
        } else {
            Write-Ok "npm registry: $curReg"
        }
    }

    $script:SkipInstallOpenClawFromNpm = $false
    $ocExe = Get-OpenClawCmd
    if ($ocExe) {
        $ov = ""
        $verOut = Invoke-NativeText -FilePath $ocExe -ArgumentList @("--version")
        if ($verOut.ExitCode -eq 0) {
            $vtext = if ($null -eq $verOut.Output) { "" } elseif ($verOut.Output -is [string]) { $verOut.Output } else { ($verOut.Output | ForEach-Object { "$_" }) -join [Environment]::NewLine }
            foreach ($line in ($vtext -split "\r?\n")) {
                if (-not [string]::IsNullOrWhiteSpace($line)) {
                    $ov = $line.Trim()
                    break
                }
            }
        }
        if (-not [string]::IsNullOrWhiteSpace($ov)) {
            Write-Ok "OpenClaw 版本: $ov"
            if (-not $ocExe.ToLowerInvariant().EndsWith(".ps1") -and (Test-Path -LiteralPath $ocExe)) {
                $script:OpenClawExePath = $ocExe
            }
            $script:SkipInstallOpenClawFromNpm = $true
        } else {
            Write-Warn "检测到 openclaw 命令但无法正常运行（模块可能损坏），将重新安装"
        }
    }
}

function Install-OpenClawFromOfflineNpm {
    $spec = "openclaw@$($script:OpenClawNpmVersion)"
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCmd) { $npmCmd = Get-Command npm -ErrorAction SilentlyContinue }
    if (-not $npmCmd) {
        Fail "未找到 npm 命令，请确认 Node 24.15.0 安装目录含 npm.cmd"
    }
    $npmPath = Get-CommandInvocationPath $npmCmd
    if ([string]::IsNullOrWhiteSpace($npmPath)) { Fail "无法解析 npm 可执行文件路径" }

    $hasCache = $false
    if ((Test-Path -LiteralPath $script:NpmCacheDir)) {
        $cacheProbe = Get-ChildItem -LiteralPath $script:NpmCacheDir -ErrorAction SilentlyContinue
        if ($cacheProbe -and $cacheProbe.Count -gt 0) { $hasCache = $true }
    }

    if ($hasCache) {
        Write-Step "2/6 安装 OpenClaw（npm 离线缓存，$spec）"
        $cacheFull = (Resolve-Path -LiteralPath $script:NpmCacheDir).Path
        $env:npm_config_cache = $cacheFull
        $env:npm_config_registry = "https://registry.npmjs.org/"
        $env:npm_config_loglevel = "warn"
        $npmExit = Invoke-NpmProcess -NpmPath $npmPath -ArgumentList @(
            "install", "-g", $spec, "--offline", "--prefer-offline", "--no-audit", "--no-fund"
        )
        if ($npmExit -ne 0) {
            Write-Warn "离线安装失败，回退到在线安装"
            $hasCache = $false
        }
    }

    if (-not $hasCache) {
        Write-Step "2/6 安装 OpenClaw（在线，$spec）"
        $npmExit = Invoke-NpmProcess -NpmPath $npmPath -ArgumentList @(
            "install", "-g", $spec, "--force", "--no-audit", "--no-fund"
        )
        if ($npmExit -ne 0) {
            Fail "npm install -g $spec 失败（在线）。请检查网络连接。"
        }
    }
    # 动态查询 npm 真实全局 prefix（便携式 node 与 MSI 安装差异很大）
    $npmGlobalBins = New-Object System.Collections.Generic.List[string]
    $prOut = Invoke-NativeText -FilePath $npmPath -ArgumentList @("prefix", "-g")
    if ($prOut.ExitCode -eq 0 -and $prOut.Output) {
        $prefixText = if ($prOut.Output -is [string]) { $prOut.Output } else { ($prOut.Output | ForEach-Object { "$_" }) -join [Environment]::NewLine }
        foreach ($line in ($prefixText -split "\r?\n")) {
            $t = $line.Trim()
            if ([string]::IsNullOrWhiteSpace($t)) { continue }
            if (Test-Path -LiteralPath $t) {
                [void]$npmGlobalBins.Add($t)
                $binSub = Join-Path $t "bin"
                if (Test-Path -LiteralPath $binSub) { [void]$npmGlobalBins.Add($binSub) }
            }
            break
        }
    }
    # 兜底候选：便携式 node 目录 + MSI 的 %APPDATA%\npm
    $nodeCmd = Get-Command node -ErrorAction SilentlyContinue
    $nodePath = Get-CommandInvocationPath $nodeCmd
    if (-not [string]::IsNullOrWhiteSpace($nodePath)) {
        $nodeBin = Split-Path -Parent $nodePath
        if ((Test-Path -LiteralPath $nodeBin) -and ($npmGlobalBins -notcontains $nodeBin)) {
            [void]$npmGlobalBins.Add($nodeBin)
        }
    }
    $msiBin = Join-Path $env:APPDATA "npm"
    if ((Test-Path -LiteralPath $msiBin) -and ($npmGlobalBins -notcontains $msiBin)) {
        [void]$npmGlobalBins.Add($msiBin)
    }

    foreach ($bin in $npmGlobalBins) {
        if ($env:Path -notlike "*$bin*") {
            $env:Path = "$bin;$env:Path"
        }
        $oldUserPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if (-not "$oldUserPath".ToLower().Contains($bin.ToLower())) {
            [Environment]::SetEnvironmentVariable("Path", "$bin;$oldUserPath", "User")
        }
    }

    # 绝对路径直接定位 openclaw.cmd / .exe，不依赖 PATH
    $script:OpenClawExePath = ""
    foreach ($bin in $npmGlobalBins) {
        foreach ($fname in @("openclaw.cmd", "openclaw.exe")) {
            $cand = Join-Path $bin $fname
            if (Test-Path -LiteralPath $cand) {
                $script:OpenClawExePath = $cand
                break
            }
        }
        if ($script:OpenClawExePath) { break }
    }

    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        $binsSummary = if ($npmGlobalBins.Count -gt 0) { $npmGlobalBins -join "; " } else { "(未查询到)" }
        Fail "未找到 openclaw 命令。已尝试的 npm 全局目录: $binsSummary"
    }
    Write-Ok "openclaw 命令可用: $cmd"
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

# `gateway restart` 常不退出，但会后台完成；若用 Invoke-OpenClawWithRedirect 超时时 taskkill /T 会误杀已拉起的网关。本函数仅启动进程不等待，由 5.5 探测验活。
function Start-OpenClawFireAndForget {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList
    )
    $workDir = if ($env:USERPROFILE) { $env:USERPROFILE } else { (Get-Location).Path }
    $prevE = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Set-NativeCommandStderrNoThrow
        $ext = [System.IO.Path]::GetExtension($FilePath).ToLowerInvariant()
        if ($ext -eq ".exe") {
            [void](Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -WorkingDirectory $workDir -NoNewWindow -ErrorAction Stop)
        } else {
            $cmdExe = if ($env:ComSpec) { $env:ComSpec } else { Join-Path $env:SystemRoot "System32\cmd.exe" }
            $tlist = [System.Collections.Generic.List[string]]::new()
            [void]$tlist.Add((Format-CmdExeMetacharToken $FilePath))
            foreach ($a in $ArgumentList) { [void]$tlist.Add((Format-CmdExeMetacharToken $a)) }
            $cmdLine = $tlist -join " "
            [void](Start-Process -FilePath $cmdExe -ArgumentList @("/d", "/s", "/c", $cmdLine) -WorkingDirectory $workDir -NoNewWindow -ErrorAction Stop)
        }
    } catch {
        Write-Warn "已触发子命令但 Start-Process 失败: $($_.Exception.Message)"
    } finally {
        $ErrorActionPreference = $prevE
    }
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
        [string]$StepLabel = "openclaw",
        [int]$MaxWaitSecOverride = -1
    )
    $outPath = [System.IO.Path]::GetTempFileName()
    $errPath = $outPath + ".err"
    $maxSec = 1800
    if ($MaxWaitSecOverride -ge 0) {
        $maxSec = $MaxWaitSecOverride
    } elseif ($env:OPENCLAW_ONBOARD_TIMEOUT_SEC) {
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

function Get-MoonshotBaseUrl {
    $r = if ($env:OPENCLAW_MOONSHOT_REGION) { $env:OPENCLAW_MOONSHOT_REGION.Trim().ToLowerInvariant() } else { "cn" }
    if ($r -eq "intl" -or $r -eq "global" -or $r -eq "international") { return "https://api.moonshot.ai/v1" }
    return "https://api.moonshot.cn/v1"
}

function New-MoonshotKimi25BatchJson {
    param([Parameter(Mandatory)][string]$BaseUrl)
    # 1. secrets.providers.default: source=env（SecretRef 从环境变量解析所必须）
    $providerDefault = [ordered]@{ path = "secrets.providers.default"; provider = [ordered]@{ source = "env" } }
    # 2. models.providers.moonshot（不含 apiKey，由下一条 ref 单独写）
    $providerVal = [ordered]@{
        baseUrl = $BaseUrl
        api     = "openai-completions"
        models  = @(
            [ordered]@{
                id            = "kimi-k2.5"
                name          = "Kimi K2.5"
                reasoning     = $false
                input         = @("text", "image")
                cost          = [ordered]@{ input = 0.6; output = 3; cacheRead = 0.1; cacheWrite = 0 }
                contextWindow = 262144
                maxTokens     = 262144
                api           = "openai-completions"
            }
        )
    }
    $opProvider = [ordered]@{ path = "models.providers.moonshot"; value = $providerVal }
    # 3. models.providers.moonshot.apiKey 写成 SecretRef（ref 格式），而非字符串
    $opApiKey = [ordered]@{
        path = "models.providers.moonshot.apiKey"
        ref  = [ordered]@{ source = "env"; provider = "default"; id = "MOONSHOT_API_KEY" }
    }
    return (ConvertTo-Json -InputObject @($providerDefault, $opProvider, $opApiKey) -Depth 30)
}

function Configure-OpenClawModel {
    Write-Step "3/6 模型配置（Kimi，config + models）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令，请重新打开 PowerShell 后重试" }

    $kimiRef = "moonshot/kimi-k2.5"
    if ($Silent) {
        if ([string]::IsNullOrWhiteSpace($env:MOONSHOT_API_KEY)) { Fail "静默安装须设置环境变量 MOONSHOT_API_KEY" }
    } else {
        if (-not $env:MOONSHOT_API_KEY) { $env:MOONSHOT_API_KEY = Read-RequiredLine "Kimi (Moonshot) API Key（见 platform.moonshot.cn）" }
        if ([string]::IsNullOrWhiteSpace($env:MOONSHOT_API_KEY)) { Fail "需要 MOONSHOT_API_KEY" }
    }
    if ($env:OPENCLAW_MOONSHOT_REGION) {
        if (-not $Silent) { Write-Ok "已用 OPENCLAW_MOONSHOT_REGION 选择 Moonshot 区域" }
    } elseif (-not $Silent) {
        $reg = (Read-Host "使用国际区 api.moonshot.ai？留空/回车=中国区 api.moonshot.cn [y/N]").Trim().ToLowerInvariant()
        if ($reg -eq "y" -or $reg -eq "yes") { $env:OPENCLAW_MOONSHOT_REGION = "intl" } else { $env:OPENCLAW_MOONSHOT_REGION = "cn" }
    } elseif (-not $env:OPENCLAW_MOONSHOT_REGION) {
        $env:OPENCLAW_MOONSHOT_REGION = "cn"
    }
    # 持久化到用户级环境变量，让计划任务（网关进程）也能从环境读取 SecretRef
    [Environment]::SetEnvironmentVariable("MOONSHOT_API_KEY", $env:MOONSHOT_API_KEY, "User")
    Write-Ok "MOONSHOT_API_KEY 已写入用户环境变量（User 级），网关计划任务将从中读取"

    $baseUrl = Get-MoonshotBaseUrl
    $modelsAllowPath = "agents.defaults.models[""$kimiRef""]"

    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "models.mode", "merge")) -ne 0) {
        Write-Warn "config set models.mode merge 非 0，继续"
    }
    $batchContent = New-MoonshotKimi25BatchJson -BaseUrl $baseUrl
    $batchFile = [System.IO.Path]::GetTempFileName() + "openclaw-moonshot-batch.json"
    try {
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($batchFile, $batchContent, $utf8NoBom)
        if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "--batch-file", $batchFile)) -ne 0) {
            Fail "openclaw config set --batch-file（models.providers.moonshot）失败"
        }
    } finally {
        Remove-Item -LiteralPath $batchFile -Force -ErrorAction SilentlyContinue
    }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", $modelsAllowPath, "{}", "--strict-json")) -ne 0) {
        Fail "openclaw config set agents.defaults.models 失败"
    }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "agents.defaults.model.primary", $kimiRef)) -ne 0) {
        Fail "openclaw config set agents.defaults.model.primary 失败"
    }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("models", "set", $kimiRef)) -ne 0) {
        Fail "openclaw models set 失败: $kimiRef"
    }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "validate")) -ne 0) {
        Write-Warn "openclaw config validate 非 0，请检查 openclaw.json"
    } else {
        Write-Ok "openclaw config validate 通过"
    }
    [void](Invoke-Native -FilePath $cmd -ArgumentList @("models", "status"))
    Write-Ok "Kimi 模型已配置: $kimiRef（$baseUrl）"
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

    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "skills.entries.topic-sync.enabled", "true")) -ne 0) {
        Write-Warn "skills.entries.topic-sync.enabled 设置返回非 0"
    } else {
        Write-Ok "skill 已启用: topic-sync"
    }
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
    $r = Invoke-OpenClawWithRedirect -FilePath $OpenClawExe `
        -ArgumentList @("gateway", "status", "--json", "--require-rpc", "--timeout", "5000") `
        -MaxWaitSec 15
    return ($r.ExitCode -eq 0)
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
        [int]$IntervalSec = 4,
        [int]$MaxTotalSec = 0
    )
    if ($MaxTotalSec -le 0) { $MaxTotalSec = $MaxAttempts * ($IntervalSec + 20) }
    $t0 = [DateTime]::UtcNow
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        $elapsed = [int]([DateTime]::UtcNow - $t0).TotalSeconds
        if ($elapsed -ge $MaxTotalSec) {
            Write-Host "  [..] 已超总等待上限 ${MaxTotalSec}s（第 $i 次尝试前），中止等待" -ForegroundColor DarkGray
            return $false
        }
        # 前置门：端口必须真的在 Listen，才允许进入 RPC/HTTP 探测
        # （避免系统代理/shim 退出码异常导致的假通过）
        if (-not (Test-NoListenerOnGatewayPort $ListenPort)) {
            if (Test-GatewayRpcOk -OpenClawExe $OpenClawExe) { return $true }
            if (Test-GatewayHttpOk -ListenPort $ListenPort) { return $true }
        }
        Write-Host "  [..] 等待网关就绪（$i/$MaxAttempts，已 ${elapsed}s/${MaxTotalSec}s，端口+RPC+HTTP 每 ${IntervalSec}s 探测）…" -ForegroundColor DarkGray
        Start-Sleep -Seconds $IntervalSec
    }
    return $false
}

function Stop-GatewayAndConfirm {
    param(
        [Parameter(Mandatory)][string]$OpenClawExe,
        [Parameter(Mandatory)][int]$ListenPort,
        [string]$Label = "gateway stop"
    )
    [void](Invoke-OpenClawWithRedirect -FilePath $OpenClawExe -ArgumentList @("gateway", "stop") -MaxWaitSec 90)
    Start-Sleep -Seconds 5
    # 端口门：没人在 Listen 就认定已停止，忽略 RPC 可能的假报
    if (Test-NoListenerOnGatewayPort $ListenPort) { return }
    if ((Test-GatewayRpcOk -OpenClawExe $OpenClawExe)) {
        Write-Warn "$Label 后网关仍在运行，再次执行 stop"
        [void](Invoke-OpenClawWithRedirect -FilePath $OpenClawExe -ArgumentList @("gateway", "stop") -MaxWaitSec 90)
        Start-Sleep -Seconds 5
    }
}

function Kill-PortOccupier {
    param([Parameter(Mandatory)][int]$Port)
    if (Test-NoListenerOnGatewayPort $Port) { return }
    Write-Warn "端口 $Port 被占用，正在强制结束占用进程"
    if (-not (Try-ReleaseLocalPort -Port $Port)) {
        $detail = Get-LocalPortConnSummary -Port $Port
        Write-Warn "端口 $Port 仍被占用: $detail"
    }
    if (Test-NoListenerOnGatewayPort $Port) {
        Write-Ok "端口 $Port 已释放"
    } else {
        Write-Warn "端口 $Port 释放失败，继续尝试"
    }
}

function Install-GatewayWithFallback {
    param([Parameter(Mandatory)][string]$OpenClawExe, [Parameter(Mandatory)][string]$Port)
    $r1 = Invoke-OpenClawWithRedirect -FilePath $OpenClawExe -ArgumentList @("gateway", "install", "--force", "--port", $Port)
    if ($r1.ExitCode -eq 0) { return }
    Write-Warn "gateway install --force 失败（退出码 $($r1.ExitCode)），将尝试无 --force"
    Write-OpenClawCliBlob -Title "openclaw 输出（供排查）" -Text $r1.Text
    $r2 = Invoke-OpenClawWithRedirect -FilePath $OpenClawExe -ArgumentList @("gateway", "install", "--port", $Port)
    if ($r2.ExitCode -ne 0) {
        Write-Warn "gateway install 仍失败（退出码 $($r2.ExitCode)）"
        Write-OpenClawCliBlob -Title "openclaw 输出（供排查）" -Text $r2.Text
    }
}

function Configure-Gateway {
    Write-Step "5/6 网关配置与验证"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令" }

    $gPort = 0
    if (-not [int]::TryParse($GatewayPort, [ref]$gPort)) { $gPort = 18789 }
    if ($gPort -le 0) { $gPort = 18789 }

    # 5.1 gateway stop + 确认关闭
    Write-Host "  [i] 5.1 openclaw gateway stop + 确认关闭…" -ForegroundColor DarkGray
    Stop-GatewayAndConfirm -OpenClawExe $cmd -ListenPort $gPort

    # 5.2 config
    Write-Host "  [i] 5.2 config：gateway.mode=local, gateway.tls.enabled=false…" -ForegroundColor DarkGray
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "gateway.mode", "local")) -ne 0) { Write-Warn "gateway.mode 设置返回非 0" }
    if ((Invoke-Native -FilePath $cmd -ArgumentList @("config", "set", "gateway.tls.enabled", "false")) -ne 0) { Write-Warn "gateway.tls.enabled 设置返回非 0" }

    # 5.3 端口查杀
    Write-Host "  [i] 5.3 检测端口 $gPort 占用…" -ForegroundColor DarkGray
    Kill-PortOccupier -Port $gPort

    # 5.4 gateway install
    Write-Host "  [i] 5.4 gateway install --force --port $GatewayPort（计划任务/服务注册）…" -ForegroundColor DarkGray
    Install-GatewayWithFallback -OpenClawExe $cmd -Port "$GatewayPort"

    # 5.4.a 网关启动探测（3 分钟墙钟）
    Write-Host "  [i] 5.4.a 网关启动探测（最多 3 分钟）…" -ForegroundColor DarkGray
    if (Wait-GatewayRpcReady -OpenClawExe $cmd -ListenPort $gPort -MaxAttempts 40 -IntervalSec 5 -MaxTotalSec 180) {
        Write-Ok "OpenClaw 安装完成: http://127.0.0.1:$GatewayPort"
        return
    }

    # 5.4.b 端口占用分流
    if (Test-NoListenerOnGatewayPort $gPort) {
        Write-Host "  [i] 5.4.b 端口 $gPort 未被占用，gateway 未启动，执行 gateway start…" -ForegroundColor DarkGray
        Start-OpenClawFireAndForget -FilePath $cmd -ArgumentList @("gateway", "start")
        Start-Sleep -Seconds 6
    } else {
        Write-Host "  [i] 5.4.b 端口 $gPort 已被占用（疑似启动中），再探测 2 分钟…" -ForegroundColor DarkGray
        if (Wait-GatewayRpcReady -OpenClawExe $cmd -ListenPort $gPort -MaxAttempts 30 -IntervalSec 5 -MaxTotalSec 120) {
            Write-Ok "OpenClaw 安装完成: http://127.0.0.1:$GatewayPort"
            return
        }
        Write-Warn "2 分钟后仍未就绪，强制释放端口 $gPort 并 gateway restart"
        Kill-PortOccupier -Port $gPort
        Start-OpenClawFireAndForget -FilePath $cmd -ArgumentList @("gateway", "restart")
        Start-Sleep -Seconds 6
    }

    # 5.5 探测本机网关 RPC/HTTP（8 分钟墙钟）
    Write-Host "  [i] 5.5 探测本机网关 RPC/HTTP（未就绪时最多等待约 8 分钟）…" -ForegroundColor DarkGray
    if (-not (Wait-GatewayRpcReady -OpenClawExe $cmd -ListenPort $gPort -MaxAttempts 60 -IntervalSec 8 -MaxTotalSec 480)) {
        if ($env:OPENCLAW_INSTALLER_SKIP_DOCTOR -eq "1") {
            Write-Warn "已设 OPENCLAW_INSTALLER_SKIP_DOCTOR=1，跳过 doctor，直接尝试重装网关"
        } else {
            Write-Warn "网关就绪探测未通过。接着将执行: openclaw doctor --non-interactive（可能 10–30+ 分钟；每 8s 打点；可用 OPENCLAW_INSTALLER_DOCTOR_MAX_SEC 或 OPENCLAW_ONBOARD_TIMEOUT_SEC 限时长；或设 OPENCLAW_INSTALLER_SKIP_DOCTOR=1 跳过）"
            $docMax = -1
            $dsec = 0
            if ([int]::TryParse($env:OPENCLAW_INSTALLER_DOCTOR_MAX_SEC, [ref]$dsec) -and $dsec -gt 0) { $docMax = $dsec }
            Write-Host "  [i] 5.6 openclaw doctor --non-interactive（长时）…" -ForegroundColor DarkGray
            $docCode = Invoke-OpenClawLongRunning -ExePath $cmd -ArgumentList @("doctor", "--non-interactive") -StepLabel "openclaw doctor" -MaxWaitSecOverride $docMax
            if ($docCode -ne 0) { Write-Warn "doctor 退出码 $docCode ，仍继续重装网关" }
        }

        # 5.7 重复：stop + 确认 → 端口查杀 → install
        Write-Host "  [i] 5.7 gateway stop + 端口查杀 + install --force…" -ForegroundColor DarkGray
        Stop-GatewayAndConfirm -OpenClawExe $cmd -ListenPort $gPort -Label "5.7 gateway stop"
        Kill-PortOccupier -Port $gPort
        Install-GatewayWithFallback -OpenClawExe $cmd -Port "$GatewayPort"

        # 5.8 再次探测 RPC/HTTP（8 分钟墙钟）
        Write-Host "  [i] 5.8 再次探测 RPC/HTTP（最多约 8 分钟）…" -ForegroundColor DarkGray
        if (-not (Wait-GatewayRpcReady -OpenClawExe $cmd -ListenPort $gPort -MaxAttempts 60 -IntervalSec 8 -MaxTotalSec 480)) {
            Fail "网关启动失败（RPC 多次探测仍超时）。可手动: openclaw gateway stop；openclaw gateway install --force --port $GatewayPort；再执行 openclaw gateway status --deep。"
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
