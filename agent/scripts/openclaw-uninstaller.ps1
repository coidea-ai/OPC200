#Requires -Version 5.1
param(
    [switch]$Silent,
    [switch]$KeepUserFiles
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Set-NativeCommandStderrNoThrow {
    try { $global:PSNativeCommandUseErrorActionPreference = $false } catch { }
    try { $PSNativeCommandUseErrorActionPreference = $false } catch { }
}
Set-NativeCommandStderrNoThrow

function Invoke-OpenClawNative {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string[]]$ArgumentList
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

function Write-Step([string]$m) { Write-Host "[STEP] $m" -ForegroundColor Cyan }
function Write-Ok([string]$m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host " [WARN] $m" -ForegroundColor Yellow }
function Fail([string]$m) { Write-Host "  [ERR] $m" -ForegroundColor Red; exit 1 }

function Get-OpenClawCmd {
    foreach ($name in @("openclaw.cmd", "openclaw.exe", "openclaw")) {
        $rows = @(Get-Command -Name $name -CommandType Application -ErrorAction SilentlyContinue)
        foreach ($row in $rows) {
            $p = if ($row.Source) { $row.Source } elseif ($row.Path) { $row.Path } else { "" }
            if ([string]::IsNullOrWhiteSpace($p)) { continue }
            if ($p.ToLowerInvariant().EndsWith(".ps1")) { continue }
            return $p
        }
    }
    return $null
}

function Stop-GatewayIfPossible {
    Write-Step "1/8 停止 OpenClaw 网关"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Write-Warn "未找到 openclaw 命令，跳过网关停止"
        return
    }
    $gs = Invoke-OpenClawNative -FilePath $cmd -ArgumentList @("gateway", "stop")
    if ($gs -ne 0) {
        Write-Warn "gateway stop 返回非零，继续卸载"
    } else {
        Write-Ok "gateway 已停止"
    }
}

function Uninstall-OpenClawCore {
    Write-Step "2/8 官方卸载（openclaw uninstall）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Write-Warn "未找到 openclaw 命令，跳过官方卸载"
        return
    }
    $uc = Invoke-OpenClawNative -FilePath $cmd -ArgumentList @("uninstall", "--all", "--yes", "--non-interactive")
    if ($uc -ne 0) {
        Write-Warn "openclaw uninstall 返回非零（模块可能损坏），继续后续清理"
    } else {
        Write-Ok "官方卸载完成"
    }
}

function Uninstall-OpenClawNpmGlobal {
    Write-Step "3/8 npm 全局卸载 openclaw"
    $npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $npmCmd) { $npmCmd = Get-Command npm -ErrorAction SilentlyContinue }
    if (-not $npmCmd) {
        Write-Warn "未找到 npm，跳过 npm uninstall -g openclaw"
        return
    }
    $nc = 0
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        Set-NativeCommandStderrNoThrow
        $null = & $npmCmd.Source @("uninstall", "-g", "openclaw") 2>$null
        if ($null -eq $LASTEXITCODE) { $nc = 0 } else { $nc = [int]$LASTEXITCODE }
    } finally {
        $ErrorActionPreference = $prevEap
    }
    if ($nc -ne 0) {
        Write-Warn "npm uninstall -g openclaw 返回非零，继续后续清理"
    } else {
        Write-Ok "npm 全局包 openclaw 已移除"
    }
}

function Remove-InstallerDesktopArtifacts {
    $desktop = [Environment]::GetFolderPath("Desktop")
    foreach ($name in @("OpenClaw Start", "OpenClaw Stop")) {
        $lnk = Join-Path $desktop ($name + ".lnk")
        if (Test-Path -LiteralPath $lnk) {
            Remove-Item -LiteralPath $lnk -Force -ErrorAction SilentlyContinue
            Write-Ok "已删除桌面快捷方式: $name.lnk"
        }
    }
    $scriptRoot = Join-Path $env:LOCALAPPDATA "OpenClawInstaller"
    if (Test-Path -LiteralPath $scriptRoot) {
        Remove-Item -LiteralPath $scriptRoot -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除安装器脚本目录: $scriptRoot"
    }
}

function Cleanup-InstallerArtifacts {
    Write-Step "4/8 清理安装器落盘（快捷方式、安装器脚本）"
    Remove-InstallerDesktopArtifacts
    if ($KeepUserFiles) {
        Write-Warn "KeepUserFiles 已启用，下一步将保留 ~/.openclaw（或 OPENCLAW_PROFILE_DIR）"
    }
    Write-Ok "清理完成"
}

function Remove-OpenClawEnvVars {
    Write-Step "5/8 清理环境变量"
    foreach ($varName in @("MOONSHOT_API_KEY", "OPENCLAW_MOONSHOT_REGION")) {
        $val = [Environment]::GetEnvironmentVariable($varName, "User")
        if ($null -ne $val) {
            [Environment]::SetEnvironmentVariable($varName, $null, "User")
            Write-Ok "已删除用户环境变量: $varName"
        }
    }
}

function Remove-OpenClawStateDirectories {
    Write-Step "6/8 删除 OpenClaw 状态目录"
    $localProbe = Join-Path $env:LOCALAPPDATA "OpenClaw"
    if (Test-Path -LiteralPath $localProbe) {
        Remove-Item -LiteralPath $localProbe -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除: $localProbe"
    }
    if ($KeepUserFiles) {
        Write-Warn "KeepUserFiles 已启用，保留用户配置目录（未删除 ~/.openclaw 或 OPENCLAW_PROFILE_DIR）"
        return
    }
    $profileDir = if ($env:OPENCLAW_PROFILE_DIR) { $env:OPENCLAW_PROFILE_DIR } else { Join-Path $HOME ".openclaw" }
    if (Test-Path -LiteralPath $profileDir) {
        Remove-Item -LiteralPath $profileDir -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除: $profileDir"
    }
}

function Remove-OpenClawNode {
    Write-Step "7/8 卸载随安装包装的 Node.js（可选）"
    $nodeDir = Join-Path $env:LOCALAPPDATA "node-v24.15.0"
    if (-not (Test-Path -LiteralPath $nodeDir)) {
        Write-Ok "未检测到随安装包装的 Node ($nodeDir)，跳过"
        return
    }
    if ($Silent) {
        Write-Warn "静默模式，跳过 Node 卸载（若需卸载请手动删除 $nodeDir 并清理 User PATH）"
        return
    }
    $a = Read-Host "是否卸载随安装包装的 Node.js 及其 PATH？目录：$nodeDir [y/N]"
    $ans = "$a".Trim().ToLowerInvariant()
    if ($ans -ne "y" -and $ans -ne "yes") {
        Write-Ok "已跳过 Node 卸载"
        return
    }

    $nodeDirLower = $nodeDir.ToLowerInvariant()
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath) {
        $entries = $userPath -split ";" | Where-Object {
            $t = "$_".Trim()
            if ([string]::IsNullOrWhiteSpace($t)) { return $false }
            return -not ($t.ToLowerInvariant().StartsWith($nodeDirLower))
        }
        $newUserPath = ($entries -join ";")
        if ($newUserPath -ne $userPath) {
            [Environment]::SetEnvironmentVariable("Path", $newUserPath, "User")
            Write-Ok "已从用户 PATH 移除 Node 路径"
        }
    }

    $npmGlobalBin = Join-Path $env:APPDATA "npm"
    if (Test-Path -LiteralPath $npmGlobalBin) {
        Remove-Item -LiteralPath $npmGlobalBin -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除 npm 全局目录: $npmGlobalBin"
    }
    foreach ($cacheDir in @(
        (Join-Path $env:APPDATA "npm-cache"),
        (Join-Path $env:LOCALAPPDATA "npm-cache")
    )) {
        if (Test-Path -LiteralPath $cacheDir) {
            Remove-Item -LiteralPath $cacheDir -Recurse -Force -ErrorAction SilentlyContinue
            Write-Ok "已删除 npm 缓存目录: $cacheDir"
        }
    }

    $tempOpenClaw = Join-Path $env:LOCALAPPDATA "Temp\openclaw"
    if (Test-Path -LiteralPath $tempOpenClaw) {
        Remove-Item -LiteralPath $tempOpenClaw -Recurse -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除 openclaw 日志目录: $tempOpenClaw"
    }

    $npmrc = Join-Path $env:USERPROFILE ".npmrc"
    if (Test-Path -LiteralPath $npmrc) {
        try {
            $lines = [System.IO.File]::ReadAllLines($npmrc)
            $newLines = $lines | Where-Object {
                $t = "$_".Trim()
                -not ($t -match '^\s*registry\s*=\s*https?://registry\.npmmirror\.com/?\s*$')
            }
            if ($newLines.Count -eq 0) {
                Remove-Item -LiteralPath $npmrc -Force -ErrorAction SilentlyContinue
                Write-Ok "已删除空的 .npmrc: $npmrc"
            } elseif ($newLines.Count -ne $lines.Count) {
                [System.IO.File]::WriteAllLines($npmrc, $newLines, (New-Object System.Text.UTF8Encoding $false))
                Write-Ok "已从 .npmrc 移除安装脚本写入的淘宝源设置"
            } else {
                Write-Warn ".npmrc 存在其他内容，已保留: $npmrc"
            }
        } catch {
            Write-Warn "处理 .npmrc 失败: $_"
        }
    }

    try {
        Remove-Item -LiteralPath $nodeDir -Recurse -Force -ErrorAction Stop
        Write-Ok "已删除 Node 目录: $nodeDir"
    } catch {
        Write-Warn "删除 Node 目录失败: $_"
    }
}

function Remove-ReleaseBundleArtifacts {
    Write-Step "8/8 删除安装包 zip 与解压目录（OpenClawInstaller）"
    $zipName = "OpenClawInstaller.zip"
    foreach ($zd in @(
        (Join-Path ([Environment]::GetFolderPath("UserProfile")) "Downloads"),
        ([Environment]::GetFolderPath("Desktop"))
    )) {
        $zp = Join-Path $zd $zipName
        if (Test-Path -LiteralPath $zp) {
            Remove-Item -LiteralPath $zp -Force -ErrorAction SilentlyContinue
            Write-Ok "已删除: $zp"
        }
    }

    $bundle = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($bundle)) {
        try {
            $bundle = Split-Path -Parent ([System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName)
        } catch {
            $bundle = ""
        }
    }
    if ([string]::IsNullOrWhiteSpace($bundle)) {
        Write-Warn "无法解析当前程序所在目录，跳过删除解压目录"
        return
    }
    if ((Split-Path -Leaf $bundle) -ine "OpenClawInstaller") {
        Write-Warn "当前不在名为 OpenClawInstaller 的解压目录中，跳过删除该目录（已尝试删除「下载」「桌面」下的 zip）"
        return
    }
    $parent = Split-Path -Parent $bundle
    $zipSibling = Join-Path $parent $zipName
    if (Test-Path -LiteralPath $zipSibling) {
        Remove-Item -LiteralPath $zipSibling -Force -ErrorAction SilentlyContinue
        Write-Ok "已删除: $zipSibling"
    }
    try {
        $cmdExe = Join-Path $env:SystemRoot "System32\cmd.exe"
        $arg = "/c timeout /t 4 /nobreak >nul & rd /s /q `"$bundle`""
        Start-Process -FilePath $cmdExe -ArgumentList $arg -WindowStyle Hidden
        Write-Ok "已安排约 4 秒后删除解压目录: $bundle（可关闭本窗口，删除在后台执行）"
    } catch {
        Write-Warn "无法安排延迟删除解压目录: $_"
    }
}

if (-not $Silent) {
    $confirm = Read-Host "确认卸载 OpenClaw 吗？输入 YES 继续"
    if ($confirm -ne "YES") { Fail "已取消" }
}

Stop-GatewayIfPossible
Uninstall-OpenClawCore
Uninstall-OpenClawNpmGlobal
Cleanup-InstallerArtifacts
Remove-OpenClawEnvVars
Remove-OpenClawStateDirectories
Remove-OpenClawNode
Remove-ReleaseBundleArtifacts
