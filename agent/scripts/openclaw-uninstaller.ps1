#Requires -Version 5.1
param(
    [switch]$Silent,
    [switch]$KeepUserFiles
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:TemplatesDir = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "openclaw-templates"

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
    Write-Step "1/3 停止 OpenClaw 网关"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Write-Warn "未找到 openclaw 命令，跳过网关停止"
        return
    }
    & $cmd gateway stop
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "gateway stop 返回非零，继续卸载"
    } else {
        Write-Ok "gateway 已停止"
    }
}

function Uninstall-OpenClawCore {
    Write-Step "2/3 卸载 OpenClaw"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Write-Warn "未找到 openclaw 命令，跳过官方卸载"
        return
    }
    & $cmd uninstall --all --yes --non-interactive
    if ($LASTEXITCODE -ne 0) {
        Fail "openclaw uninstall 失败"
    }
    Write-Ok "官方卸载完成"
}

function Cleanup-InstallerArtifacts {
    Write-Step "3/3 清理安装器落盘文件"
    if ($KeepUserFiles) {
        Write-Warn "KeepUserFiles 已启用，跳过模板文件清理"
        return
    }
    $profileDir = if ($env:OPENCLAW_PROFILE_DIR) { $env:OPENCLAW_PROFILE_DIR } else { Join-Path $HOME ".openclaw" }
    foreach ($name in @("AGENTS.md", "IDENTITY.md", "SOUL.md")) {
        $dst = Join-Path $profileDir $name
        $dstNew = $dst + ".new"
        if (Test-Path -LiteralPath $dstNew) { Remove-Item -LiteralPath $dstNew -Force -ErrorAction SilentlyContinue }
        if ((Test-Path -LiteralPath $dst) -and (Test-Path -LiteralPath (Join-Path $script:TemplatesDir $name))) {
            try {
                $srcHash = (Get-FileHash -LiteralPath (Join-Path $script:TemplatesDir $name) -Algorithm SHA256).Hash
                $dstHash = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
                if ($srcHash -eq $dstHash) {
                    Remove-Item -LiteralPath $dst -Force -ErrorAction SilentlyContinue
                }
            } catch {
                Write-Warn "对比模板失败: $name"
            }
        }
    }
    Write-Ok "清理完成"
}

if (-not $Silent) {
    $confirm = Read-Host "确认卸载 OpenClaw 吗？输入 YES 继续"
    if ($confirm -ne "YES") { Fail "已取消" }
}

Stop-GatewayIfPossible
Uninstall-OpenClawCore
Cleanup-InstallerArtifacts
