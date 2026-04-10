# OPC200 Agent Windows 安装脚本测试方案

> **测试目标**: 验证 `install.ps1` 脚本在 Windows 环境中的正确性  
> **测试环境**: Windows 10/11 (x64)  
> **测试日期**: 2026-04-10

---

## 1. 测试前置条件

### 1.1 环境准备

| 项目 | 要求 | 检查方法 |
|------|------|---------|
| 操作系统 | Windows 10 (1809+) 或 Windows 11 | `winver` |
| PowerShell | 5.1 或 7.x | `$PSVersionTable.PSVersion` |
| 网络连接 | 能访问 GitHub/cdn.opc200.co | `Test-NetConnection github.com -Port 443` |
| 管理员权限 | 以管理员身份运行 PowerShell | `[Security.Principal.WindowsIdentity]::GetCurrent().Groups -contains 'S-1-5-32-544'` |
| 磁盘空间 | 至少 1GB 可用空间 | `Get-PSDrive C` |

### 1.2 测试数据

```powershell
# 测试用配置
$TestConfig = @{
    PlatformUrl = "https://platform.opc200.co"
    CustomerId = "test-opc-001"
    ApiKey = "sk-test-123456789"
}
```

---

## 2. 测试用例

### TC-001: 交互式安装测试

**目的**: 验证正常交互安装流程

**步骤**:
```powershell
# 1. 右键 PowerShell → 以管理员身份运行
# 2. 执行脚本
.\agent\scripts\install.ps1

# 3. 按提示输入:
#    - 平台地址: https://platform.opc200.co
#    - Customer ID: test-opc-001
#    - API Key: sk-test-123456789
#    - 安装目录: (回车使用默认)
```

**预期结果**:
- [ ] 显示 "系统检查通过"
- [ ] 成功下载 Agent 二进制
- [ ] 创建目录结构 `%LOCALAPPDATA%\OPC200`
- [ ] 生成 `config.yml` 和 `.env` 文件
- [ ] 注册 Windows 服务 "OPC200-Agent"
- [ ] 服务成功启动
- [ ] 健康检查通过（或显示警告）
- [ ] 显示安装完成摘要

**验证命令**:
```powershell
Get-Service OPC200-Agent
Test-NetConnection 127.0.0.1 -Port 8080
Get-Content "$env:LOCALAPPDATA\OPC200\logs\agent.log" -Tail 20
```

---

### TC-002: 静默安装测试

**目的**: 验证命令行参数安装（用于自动化部署）

**步骤**:
```powershell
.\agent\scripts\install.ps1 `
    -PlatformUrl "https://platform.opc200.co" `
    -CustomerId "test-opc-002" `
    -ApiKey "sk-test-987654321" `
    -InstallDir "C:\OPC200-Test" `
    -Silent
```

**预期结果**:
- [ ] 无交互式提示
- [ ] 安装到指定目录 `C:\OPC200-Test`
- [ ] 服务自动启动
- [ ] 退出代码为 0

**验证**:
```powershell
$LASTEXITCODE -eq 0
Test-Path "C:\OPC200-Test\opc-agent.exe"
```

---

### TC-003: 权限检查测试

**目的**: 验证非管理员运行时的错误处理

**步骤**:
```powershell
# 以普通用户身份运行 PowerShell
.\agent\scripts\install.ps1
```

**预期结果**:
- [ ] 检测到非管理员权限
- [ ] 显示错误: "请以管理员身份运行 PowerShell 然后重试"
- [ ] 退出代码为 1

---

### TC-004: 系统要求检查

**目的**: 验证 Windows 版本和磁盘空间检查

**步骤**:
1. 在 Windows 7/8 上运行脚本（如果有环境）
2. 或者模拟低磁盘空间环境

**预期结果**:
- [ ] Windows 版本低于 10 (1809) 时提示错误
- [ ] 磁盘空间不足 1GB 时提示错误

---

### TC-005: 重复安装测试

**目的**: 验证服务已存在时的处理

**步骤**:
```powershell
# 第一次安装
.\agent\scripts\install.ps1 -Silent -PlatformUrl "..." -CustomerId "..." -ApiKey "..."

# 第二次安装（相同 CustomerId 或不同）
.\agent\scripts\install.ps1 -Silent -PlatformUrl "..." -CustomerId "test-opc-003" -ApiKey "..."
```

**预期结果**:
- [ ] 检测到服务已存在
- [ ] 停止并删除旧服务
- [ ] 重新安装新服务
- [ ] 新服务正常启动

---

### TC-006: 网络失败测试

**目的**: 验证下载失败时的错误处理

**步骤**:
```powershell
# 断开网络或修改下载 URL 为无效地址
# 编辑脚本临时修改 $Config.AgentDownloadUrl 为无效地址
.\agent\scripts\install.ps1 -Silent ...
```

**预期结果**:
- [ ] 显示下载失败错误
- [ ] 不创建不完整文件
- [ ] 退出代码为 1

---

## 3. 卸载测试

### TC-007: 服务卸载

**步骤**:
```powershell
# 停止服务
Stop-Service OPC200-Agent

# 删除服务
sc.exe delete OPC200-Agent

# 删除目录
Remove-Item -Recurse "$env:LOCALAPPDATA\OPC200"
```

**预期结果**:
- [ ] 服务从系统中移除
- [ ] 文件完全删除
- [ ] 无残留注册表项

---

## 4. 日志检查

**日志位置**: `%LOCALAPPDATA%\OPC200\logs\agent.log`

**应包含内容**:
- [ ] Agent 启动日志
- [ ] 配置加载日志
- [ ] 与平台通信日志（尝试推送指标）

---

## 5. 测试报告模板

```markdown
## 测试报告 - [日期]

| 用例 | 结果 | 备注 |
|------|------|------|
| TC-001 交互式安装 | ✅/❌ | |
| TC-002 静默安装 | ✅/❌ | |
| TC-003 权限检查 | ✅/❌ | |
| TC-004 系统要求 | ✅/❌ | |
| TC-005 重复安装 | ✅/❌ | |
| TC-006 网络失败 | ✅/❌ | |
| TC-007 卸载 | ✅/❌ | |

### 发现的问题
1. 

### 建议改进
1. 
```

---

## 6. 已知限制

1. **Agent 二进制**: 当前使用 GitHub Releases，需要替换为自有 CDN
2. **服务注册**: 使用 `sc.exe`，可能需要改为 `New-Service` 以更好支持 PowerShell 7
3. **健康检查**: 如果 Agent 启动慢，健康检查可能超时
4. **卸载脚本**: 当前需要手动执行，后续提供 `uninstall.ps1`

---

## 7. 后续优化

- [ ] 添加 `uninstall.ps1` 脚本
- [ ] 支持 PowerShell 7 的 `New-Service`
- [ ] 添加安装进度条
- [ ] 支持代理配置
- [ ] 添加数字签名验证
