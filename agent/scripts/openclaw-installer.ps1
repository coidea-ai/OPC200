#Requires -Version 5.1
param(
    [switch]$Silent,
    [string]$OpenClawAuthChoice = "",
    [string]$GatewayPort = "18789"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:ReleaseVersion = "2026.4.15"
$script:ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:ReleaseDir = Join-Path $script:ScriptDir "openclaw-releases"
$script:TemplatesDir = Join-Path $script:ScriptDir "openclaw-templates"
$script:DefaultZip = Join-Path $script:ReleaseDir ("OpenClaw-" + $script:ReleaseVersion + ".zip")
$script:DefaultSkills = "skill-vetter"

function Write-Step([string]$m) { Write-Host "[STEP] $m" -ForegroundColor Cyan }
function Write-Ok([string]$m) { Write-Host "  [OK] $m" -ForegroundColor Green }
function Write-Warn([string]$m) { Write-Host " [WARN] $m" -ForegroundColor Yellow }
function Fail([string]$m) { Write-Host "  [ERR] $m" -ForegroundColor Red; exit 1 }

function Get-OpenClawCmd {
    $cmd = Get-Command openclaw -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

function Install-OpenClawFromBundledZip {
    Write-Step "1/4 安装 OpenClaw（内置 Release）"
    $zipPath = $script:DefaultZip
    if (-not (Test-Path -LiteralPath $zipPath)) {
        $anyZip = Get-ChildItem -LiteralPath $script:ReleaseDir -Filter "OpenClaw-*.zip" -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($anyZip) {
            $zipPath = $anyZip.FullName
            Write-Warn "未命中默认版本 zip，改用: $zipPath"
        } else {
            Fail "未找到内置 Windows 资产 zip（目录: $script:ReleaseDir）"
        }
    }
    $targetRoot = Join-Path $env:LOCALAPPDATA "OpenClaw"
    if (-not (Test-Path -LiteralPath $targetRoot)) {
        New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
    }
    Expand-Archive -LiteralPath $zipPath -DestinationPath $targetRoot -Force
    $binDir = $targetRoot
    $env:Path = "$binDir;$env:Path"
    [Environment]::SetEnvironmentVariable("Path", "$binDir;" + [Environment]::GetEnvironmentVariable("Path", "User"), "User")
    $cmd = Get-OpenClawCmd
    if (-not $cmd) {
        Write-Warn "当前会话未检测到 openclaw，尝试继续使用直接路径"
    } else {
        Write-Ok "openclaw 命令可用"
    }
}

function Read-RequiredLine([string]$prompt) {
    while ($true) {
        $v = Read-Host $prompt
        if (-not [string]::IsNullOrWhiteSpace($v)) { return $v.Trim() }
    }
}

function Run-Onboard {
    Write-Step "2/4 模型配置（onboard）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令，请重新打开 PowerShell 后重试" }

    $auth = $OpenClawAuthChoice.Trim()
    if (-not $auth -and $env:OPENCLAW_AUTH_CHOICE) { $auth = $env:OPENCLAW_AUTH_CHOICE.Trim() }
    if (-not $auth -and -not $Silent) {
        Write-Host "1) apiKey  2) openai-api-key  3) gemini-api-key  4) custom-api-key"
        switch ((Read-Host "选择 [1-4]").Trim()) {
            "1" { $auth = "apiKey" }
            "2" { $auth = "openai-api-key" }
            "3" { $auth = "gemini-api-key" }
            "4" { $auth = "custom-api-key" }
            default { Fail "无效选择" }
        }
    }
    if (-not $auth) { Fail "静默模式必须指定 OpenClawAuthChoice 或 OPENCLAW_AUTH_CHOICE" }

    if ($auth -eq "custom-api-key") {
        if (-not $env:OPENCLAW_CUSTOM_BASE_URL) { $env:OPENCLAW_CUSTOM_BASE_URL = Read-RequiredLine "OPENCLAW_CUSTOM_BASE_URL" }
        if (-not $env:OPENCLAW_CUSTOM_MODEL_ID) { $env:OPENCLAW_CUSTOM_MODEL_ID = Read-RequiredLine "OPENCLAW_CUSTOM_MODEL_ID" }
        if (-not $env:CUSTOM_API_KEY) { $env:CUSTOM_API_KEY = Read-RequiredLine "CUSTOM_API_KEY" }
        & $cmd onboard --non-interactive --accept-risk --mode local --auth-choice custom-api-key --gateway-port $GatewayPort --gateway-bind loopback --custom-base-url $env:OPENCLAW_CUSTOM_BASE_URL --custom-model-id $env:OPENCLAW_CUSTOM_MODEL_ID
    } else {
        & $cmd onboard --non-interactive --accept-risk --mode local --auth-choice $auth --gateway-port $GatewayPort --gateway-bind loopback
    }
    if ($LASTEXITCODE -ne 0) { Fail "openclaw onboard 失败" }
    Write-Ok "onboard 完成"
}

function Write-TemplatesAndSkills {
    Write-Step "3/4 轻预装（tools/skills/docs）"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令" }
    & $cmd config set tools.profile full
    if ($LASTEXITCODE -ne 0) { Write-Warn "tools.profile 设置失败" }
    & $cmd skills install $script:DefaultSkills
    if ($LASTEXITCODE -ne 0) { Write-Warn "skills 安装失败: $($script:DefaultSkills)" }

    $profileDir = if ($env:OPENCLAW_PROFILE_DIR) { $env:OPENCLAW_PROFILE_DIR } else { Join-Path $HOME ".openclaw" }
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
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

function Configure-Gateway {
    Write-Step "4/4 网关配置与验证"
    $cmd = Get-OpenClawCmd
    if (-not $cmd) { Fail "未找到 openclaw 命令" }
    & $cmd config set gateway.mode local
    & $cmd config set gateway.tls.enabled false
    & $cmd gateway install --port $GatewayPort
    & $cmd gateway restart
    Start-Sleep -Seconds 2
    & $cmd gateway status --json --require-rpc
    if ($LASTEXITCODE -ne 0) {
        Write-Warn "网关未就绪，执行 doctor 诊断"
        & $cmd doctor --non-interactive
        & $cmd gateway restart
        Start-Sleep -Seconds 2
        & $cmd gateway status --json --require-rpc
        if ($LASTEXITCODE -ne 0) { Fail "网关启动失败，请检查 doctor 输出" }
    }
    Write-Ok "OpenClaw 安装完成: http://127.0.0.1:$GatewayPort"
}

Install-OpenClawFromBundledZip
Run-Onboard
Write-TemplatesAndSkills
Configure-Gateway
