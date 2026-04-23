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
    $cmd = Get-Command openclaw -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Stop-GatewayIfPossible {
    Write-Step "1/6 停止 OpenClaw 网关"
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
    Write-Step "2/6 官方卸载（openclaw uninstall）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Write-Warn "未找到 openclaw 命令，跳过官方卸载"
        return
    }
    $uc = Invoke-OpenClawNative -FilePath $cmd -ArgumentList @("uninstall", "--all", "--yes", "--non-interactive")
    if ($uc -ne 0) {
        Fail "openclaw uninstall 失败"
    }
    Write-Ok "官方卸载完成"
}

function Uninstall-OpenClawNpmGlobal {
    Write-Step "3/6 npm 全局卸载 openclaw"
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
    Write-Step "4/6 清理安装器落盘（快捷方式、安装器脚本）"
    Remove-InstallerDesktopArtifacts
    if ($KeepUserFiles) {
        Write-Warn "KeepUserFiles 已启用，下一步将保留 ~/.openclaw（或 OPENCLAW_PROFILE_DIR）"
    }
    Write-Ok "清理完成"
}

function Remove-OpenClawStateDirectories {
    Write-Step "5/6 删除 OpenClaw 状态目录"
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

function Remove-ReleaseBundleArtifacts {
    Write-Step "6/6 删除安装包 zip 与解压目录（OpenClawInstaller）"
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
Remove-OpenClawStateDirectories
Remove-ReleaseBundleArtifacts
