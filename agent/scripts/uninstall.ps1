#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 卸载脚本
.DESCRIPTION
    完全移除 OPC200 Agent 及其服务
.PARAMETER InstallDir
    安装目录（默认：$env:LOCALAPPDATA\OPC200）
.PARAMETER KeepData
    保留数据目录
.PARAMETER Silent
    静默卸载模式
#>

param(
    [string]$InstallDir = "",
    [switch]$KeepData,
    [switch]$Silent
)

$ServiceName = "OPC200-Agent"

function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warning { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host "[ERR] $Message" -ForegroundColor Red }

# 检查管理员权限
function Test-AdminRights {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 主卸载流程
try {
    Write-Host "`nOPC200 Agent 卸载脚本`n" -ForegroundColor Cyan
    
    if (-not (Test-AdminRights)) {
        throw "请以管理员身份运行 PowerShell 然后重试"
    }
    
    # 确定安装目录
    if (-not $InstallDir) {
        $InstallDir = Join-Path $env:LOCALAPPDATA "OPC200"
    }
    
    Write-Info "安装目录: $InstallDir"
    
    # 停止并删除服务
    $service = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($service) {
        Write-Info "停止服务 $ServiceName..."
        Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        
        Write-Info "删除服务 $ServiceName..."
        $result = sc.exe delete $ServiceName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Success "服务已删除"
        }
        else {
            Write-Warning "服务删除可能失败: $result"
        }
    }
    else {
        Write-Warning "服务 $ServiceName 不存在"
    }
    
    # 删除目录
    if (Test-Path $InstallDir) {
        if (-not $Silent) {
            $confirm = Read-Host "确认删除目录 $InstallDir ? (Y/N)"
            if ($confirm -ne 'Y') {
                Write-Info "卸载已取消"
                exit 0
            }
        }
        
        if ($KeepData) {
            Write-Info "保留数据，仅删除程序文件..."
            # 保留 data 目录，删除其他
            $itemsToRemove = @("opc-agent.exe", "config", "logs", "update")
            foreach ($item in $itemsToRemove) {
                $path = Join-Path $InstallDir $item
                if (Test-Path $path) {
                    Remove-Item -Recurse -Force $path
                    Write-Info "已删除: $item"
                }
            }
        }
        else {
            Write-Info "删除安装目录..."
            Remove-Item -Recurse -Force $InstallDir
        }
        Write-Success "目录清理完成"
    }
    else {
        Write-Warning "安装目录不存在"
    }
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "    卸载完成！" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Green
    
    exit 0
}
catch {
    Write-Error "卸载失败: $_"
    exit 1
}
