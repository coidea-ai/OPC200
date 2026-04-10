#Requires -Version 5.1
<#
.SYNOPSIS
    OPC200 Agent Windows 部署脚本（MVP 验证版）
.DESCRIPTION
    一键部署 OpenClaw Agent 到 Windows 系统，支持服务注册和自动启动
.PARAMETER PlatformUrl
    平台端点地址
.PARAMETER CustomerId
    用户唯一标识
.PARAMETER ApiKey
    API 认证密钥
.PARAMETER InstallDir
    安装目录（默认：$env:LOCALAPPDATA\OPC200）
.PARAMETER Silent
    静默安装模式
.EXAMPLE
    .\install.ps1 -PlatformUrl "https://platform.opc200.co" -CustomerId "opc-001" -ApiKey "sk-xxx"
#>

param(
    [string]$PlatformUrl = "",
    [string]$CustomerId = "",
    [string]$ApiKey = "",
    [string]$InstallDir = "",
    [switch]$Silent
)

# 配置常量
$script:Config = @{
    Version = "1.0.0"
    AgentDownloadUrl = "https://github.com/coidea-ai/OPC200/releases/download/v2.3.0/opc-agent-windows-amd64.exe"
    # 后续切换到自有服务器: "https://cdn.opc200.co/agent/latest/opc-agent-windows-amd64.exe"
    AgentFileName = "opc-agent.exe"
    ServiceName = "OPC200-Agent"
    ServiceDisplayName = "OPC200 Agent Service"
}

# 颜色输出函数
function Write-Info { param([string]$Message) Write-Host "[INFO] $Message" -ForegroundColor Cyan }
function Write-Success { param([string]$Message) Write-Host "[OK] $Message" -ForegroundColor Green }
function Write-Warning { param([string]$Message) Write-Host "[WARN] $Message" -ForegroundColor Yellow }
function Write-Error { param([string]$Message) Write-Host "[ERR] $Message" -ForegroundColor Red }

# 检查管理员权限
function Test-AdminRights {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# 检查系统要求
function Test-SystemRequirements {
    Write-Info "检查系统要求..."
    
    # Windows 版本
    $osInfo = Get-CimInstance Win32_OperatingSystem
    $osVersion = [System.Version]$osInfo.Version
    
    if ($osVersion -lt [System.Version]"10.0.17763") {
        throw "需要 Windows 10 版本 1809 或更高版本"
    }
    
    # 架构检查
    if ($env:PROCESSOR_ARCHITECTURE -ne "AMD64") {
        throw "暂时仅支持 x64 架构"
    }
    
    # 磁盘空间
    $systemDrive = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$($env:SystemDrive)'"
    $freeSpaceGB = [math]::Round($systemDrive.FreeSpace / 1GB, 2)
    if ($freeSpaceGB -lt 1) {
        throw "磁盘空间不足，需要至少 1GB 可用空间"
    }
    
    Write-Success "系统检查通过 (Windows $($osInfo.Version), $freeSpaceGB GB 可用)"
}

# 交互式配置输入
function Get-InteractiveConfig {
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "    OPC200 Agent 安装向导" -ForegroundColor Cyan
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    # Platform URL
    $defaultUrl = "https://platform.opc200.co"
    $inputUrl = Read-Host "请输入平台地址 [$defaultUrl]"
    $script:Config.PlatformUrl = if ($inputUrl) { $inputUrl } else { $defaultUrl }
    
    # Customer ID
    do {
        $script:Config.CustomerId = Read-Host "请输入 Customer ID (必需)"
        if (-not $script:Config.CustomerId) {
            Write-Error "Customer ID 不能为空"
        }
    } while (-not $script:Config.CustomerId)
    
    # API Key
    do {
        $secureKey = Read-Host "请输入 API Key (必需)" -AsSecureString
        $script:Config.ApiKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureKey)
        )
        if (-not $script:Config.ApiKey) {
            Write-Error "API Key 不能为空"
        }
    } while (-not $script:Config.ApiKey)
    
    # Install Directory
    $defaultDir = Join-Path $env:LOCALAPPDATA "OPC200"
    $inputDir = Read-Host "请输入安装目录 [$defaultDir]"
    $script:Config.InstallDir = if ($inputDir) { $inputDir } else { $defaultDir }
}

# 下载 Agent 二进制
function Download-Agent {
    param([string]$Destination)
    
    Write-Info "正在下载 Agent..."
    Write-Info "来源: $($script:Config.AgentDownloadUrl)"
    
    try {
        $progressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $script:Config.AgentDownloadUrl -OutFile $Destination -UseBasicParsing
        $progressPreference = 'Continue'
        
        if (-not (Test-Path $Destination)) {
            throw "下载失败：文件未创建"
        }
        
        $fileSize = (Get-Item $Destination).Length / 1MB
        Write-Success "下载完成 ($([math]::Round($fileSize, 2)) MB)"
    }
    catch {
        throw "下载 Agent 失败: $_"
    }
}

# 创建目录结构
function Initialize-DirectoryStructure {
    param([string]$BaseDir)
    
    Write-Info "创建目录结构..."
    
    $dirs = @(
        $BaseDir,
        (Join-Path $BaseDir "config"),
        (Join-Path $BaseDir "data"),
        (Join-Path $BaseDir "data\journal"),
        (Join-Path $BaseDir "logs"),
        (Join-Path $BaseDir "update")
    )
    
    foreach ($dir in $dirs) {
        if (-not (Test-Path $dir)) {
            New-Item -ItemType Directory -Path $dir -Force | Out-Null
        }
    }
    
    Write-Success "目录创建完成"
}

# 写入配置文件
function Write-Configuration {
    param([string]$ConfigDir)
    
    Write-Info "写入配置文件..."
    
    $configContent = @"
# OPC200 Agent 配置文件
# 生成时间: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

platform:
  url: "$($script:Config.PlatformUrl)"
  metrics_endpoint: "/metrics/job"

customer:
  id: "$($script:Config.CustomerId)"

agent:
  version: "$($script:Config.Version)"
  check_interval: 60
  push_interval: 30

gateway:
  host: "127.0.0.1"
  port: 8080

journal:
  storage_path: "data/journal"
  max_size: "1GB"

logging:
  level: "info"
  file: "logs/agent.log"
  max_size: "100MB"
  max_backups: 5
"@

    $configPath = Join-Path $ConfigDir "config.yml"
    $configContent | Out-File -FilePath $configPath -Encoding UTF8
    
    # 写入环境变量文件（敏感信息）
    $envContent = "OPC200_API_KEY=$($script:Config.ApiKey)`n"
    $envPath = Join-Path $ConfigDir ".env"
    $envContent | Out-File -FilePath $envPath -Encoding UTF8
    
    # 设置文件权限（仅限当前用户访问）
    $envItem = Get-Item $envPath
    $envItem.SetAccessControl((New-Object System.Security.AccessControl.FileSecurity))
    
    Write-Success "配置写入完成"
}

# 注册 Windows 服务
function Register-AgentService {
    param(
        [string]$AgentPath,
        [string]$ConfigPath
    )
    
    Write-Info "注册 Windows 服务..."
    
    # 检查服务是否已存在
    $existingService = Get-Service -Name $script:Config.ServiceName -ErrorAction SilentlyContinue
    if ($existingService) {
        Write-Warning "服务已存在，先停止并删除..."
        Stop-Service -Name $script:Config.ServiceName -Force -ErrorAction SilentlyContinue
        sc.exe delete $script:Config.ServiceName | Out-Null
        Start-Sleep -Seconds 2
    }
    
    # 创建服务
    $serviceCmd = '"$AgentPath" --config "$ConfigPath" service run'
    $binPath = "`"$AgentPath`" --config `"$ConfigPath`" service run"
    
    $result = sc.exe create $script:Config.ServiceName `
        binPath= $binPath `
        DisplayName= $script:Config.ServiceDisplayName `
        start= auto `
        obj= "NT AUTHORITY\LocalService" 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        throw "服务注册失败: $result"
    }
    
    Write-Success "服务注册完成"
}

# 启动服务
function Start-AgentService {
    Write-Info "启动 Agent 服务..."
    
    try {
        Start-Service -Name $script:Config.ServiceName -ErrorAction Stop
        Start-Sleep -Seconds 3
        
        $service = Get-Service -Name $script:Config.ServiceName
        if ($service.Status -eq "Running") {
            Write-Success "服务启动成功"
        }
        else {
            throw "服务状态异常: $($service.Status)"
        }
    }
    catch {
        throw "服务启动失败: $_"
    }
}

# 测试健康检查
function Test-AgentHealth {
    param([int]$Port = 8080)
    
    Write-Info "测试 Agent 健康状态..."
    
    $maxRetries = 10
    $retryInterval = 2
    
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Success "Agent 健康检查通过"
                return $true
            }
        }
        catch {
            Write-Warning "第 $i/$maxRetries 次检查失败，${retryInterval}秒后重试..."
            Start-Sleep -Seconds $retryInterval
        }
    }
    
    Write-Error "健康检查失败，Agent 可能未正常启动"
    return $false
}

# 显示安装摘要
function Show-InstallSummary {
    param([string]$InstallDir)
    
    Write-Host "`n========================================" -ForegroundColor Green
    Write-Host "    安装完成！" -ForegroundColor Green
    Write-Host "========================================`n" -ForegroundColor Green
    
    Write-Host "安装目录: $InstallDir" -ForegroundColor Cyan
    Write-Host "配置文件: $(Join-Path $InstallDir "config\config.yml")" -ForegroundColor Cyan
    Write-Host "数据目录: $(Join-Path $InstallDir "data")" -ForegroundColor Cyan
    Write-Host "日志文件: $(Join-Path $InstallDir "logs\agent.log")" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "服务名称: $($script:Config.ServiceName)" -ForegroundColor Cyan
    Write-Host "管理地址: http://127.0.0.1:8080" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "常用命令:" -ForegroundColor Yellow
    Write-Host "  查看状态: Get-Service $($script:Config.ServiceName)" -ForegroundColor Gray
    Write-Host "  停止服务: Stop-Service $($script:Config.ServiceName)" -ForegroundColor Gray
    Write-Host "  启动服务: Start-Service $($script:Config.ServiceName)" -ForegroundColor Gray
    Write-Host "  查看日志: Get-Content '$(Join-Path $InstallDir "logs\agent.log")' -Tail 50" -ForegroundColor Gray
    Write-Host ""
    Write-Host "卸载方法:" -ForegroundColor Yellow
    Write-Host "  1. 停止服务: Stop-Service $($script:Config.ServiceName)" -ForegroundColor Gray
    Write-Host "  2. 删除服务: sc.exe delete $($script:Config.ServiceName)" -ForegroundColor Gray
    Write-Host "  3. 删除目录: Remove-Item -Recurse '$InstallDir'" -ForegroundColor Gray
    Write-Host ""
}

# 主安装流程
function Install-OPCAgent {
    try {
        Write-Host "`nOPC200 Agent Windows 安装脚本 v$($script:Config.Version)`n" -ForegroundColor Cyan
        
        # 步骤1: 检查管理员权限
        if (-not (Test-AdminRights)) {
            throw "请以管理员身份运行 PowerShell 然后重试"
        }
        
        # 步骤2: 检查系统要求
        Test-SystemRequirements
        
        # 步骤3: 获取配置
        if ($Silent) {
            if (-not $PlatformUrl -or -not $CustomerId -or -not $ApiKey) {
                throw "静默模式需要提供所有参数: -PlatformUrl, -CustomerId, -ApiKey"
            }
            $script:Config.PlatformUrl = $PlatformUrl
            $script:Config.CustomerId = $CustomerId
            $script:Config.ApiKey = $ApiKey
            $script:Config.InstallDir = if ($InstallDir) { $InstallDir } else { Join-Path $env:LOCALAPPDATA "OPC200" }
        }
        else {
            Get-InteractiveConfig
        }
        
        # 步骤4: 创建目录
        Initialize-DirectoryStructure -BaseDir $script:Config.InstallDir
        
        # 步骤5: 下载 Agent
        $agentPath = Join-Path $script:Config.InstallDir $script:Config.AgentFileName
        Download-Agent -Destination $agentPath
        
        # 步骤6: 写入配置
        $configDir = Join-Path $script:Config.InstallDir "config"
        Write-Configuration -ConfigDir $configDir
        
        # 步骤7: 注册服务
        Register-AgentService -AgentPath $agentPath -ConfigPath (Join-Path $configDir "config.yml")
        
        # 步骤8: 启动服务
        Start-AgentService
        
        # 步骤9: 健康检查
        $health = Test-AgentHealth
        
        # 步骤10: 显示摘要
        Show-InstallSummary -InstallDir $script:Config.InstallDir
        
        if (-not $health) {
            Write-Warning "Agent 可能未完全启动，请检查日志"
        }
        
        Write-Success "安装流程完成"
        return 0
    }
    catch {
        Write-Error "安装失败: $_"
        return 1
    }
}

# 执行安装
$exitCode = Install-OPCAgent
exit $exitCode
