# OPC200 Agent 安装脚本设计规范

> **文档版本**: v1.0  
> **作者**: 陵兰  
> **日期**: 2026-04-10  
> **关联任务**: AGENT-001, AGENT-002, AGENT-003

---

## 1. 概述

### 1.1 目标
设计跨平台（Windows/Mac/Linux）统一的 OPC200 Agent 安装脚本，实现用户侧一键部署。

### 1.2 设计原则
| 原则 | 说明 |
|------|------|
| **一键安装** | 用户只需运行单个脚本，无需手动配置 |
| **开箱即用** | 安装后自动注册系统服务，开机自启 |
| **配置简洁** | 仅需 3 个核心配置项 |
| **安全优先** | API Key 等敏感信息本地加密存储 |

---

## 2. 安装流程

### 2.1 统一流程（所有平台）

```
┌─────────────────────────────────────────────────────────────┐
│                     OPC200 Agent 安装流程                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 环境检查                                                 │
│     ├── 操作系统版本检测（Windows 10+/macOS 12+/Ubuntu 20+） │
│     ├── 架构检测（x64/ARM64）                               │
│     └── 端口占用检测（默认 8080）                            │
│                          ↓                                  │
│  2. 交互式配置（或命令行参数）                                │
│     ├── `-OPC200PlatformUrl` / `--opc200-platform-url`: 平台端点（默认 https://platform.opc200.co）│
│     ├── `-OPC200TenantId` / `--opc200-tenant-id` / `OPC200_TENANT_ID`: 租户唯一标识       │
│     └── `-OPC200ApiKey` / `--opc200-api-key` / `OPC200_API_KEY`: 认证密钥（安全输入，不显示）                 │
│                          ↓                                  │
│  3. 下载 Agent                                               │
│     ├── 从 GitHub Releases 下载对应平台二进制                │
│     └── 校验文件完整性（SHA256）                             │
│                          ↓                                  │
│  4. 安装部署                                                 │
│     ├── 创建目录结构（~/.opc200/）                          │
│     ├── 解压/复制二进制文件                                  │
│     └── 写入配置文件（config.yml）                           │
│                          ↓                                  │
│  5. 注册系统服务                                             │
│     ├── Windows: 创建 Windows Service                        │
│     ├── macOS:  创建 launchd plist                           │
│     └── Linux:  创建 systemd service                         │
│                          ↓                                  │
│  6. 启动验证                                                 │
│     ├── 启动服务                                             │
│     ├── 等待健康检查（/health 端点）                         │
│     └── 测试指标推送（首次推送心跳）                         │
│                          ↓                                  │
│  7. 完成输出                                                 │
│     ├── 显示服务状态                                         │
│     ├── 显示日志查看命令                                     │
│     └── 显示卸载方法                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 目录结构

### 3.1 安装目录

```
~/.opc200/                          # 用户数据主目录
├── bin/
│   └── opc-agent                   # Agent 可执行文件
├── config/
│   └── config.yml                  # 配置文件
├── data/
│   ├── journal/                    # Journal 数据存储
│   └── exporter/                   # 指标缓存
├── logs/
│   ├── agent.log                   # 运行日志
│   └── exporter.log                # 指标推送日志
└── .env                            # 敏感信息（API Key 等）
```

### 3.2 配置文件模板

```yaml
# ~/.opc200/config/config.yml

# 平台配置
platform:
  url: "https://platform.opc200.co"
  metrics_endpoint: "/metrics/job"
  
# 用户身份（YAML 键名仍为 customer，与运行时 TENANT_ID 对应）
customer:
  id: "<TENANT_ID>"
  
# Agent 配置
agent:
  version: "2.3.0"
  check_interval: 60  # 秒，健康检查间隔
  push_interval: 30   # 秒，指标推送间隔
  
# 本地服务
gateway:
  host: "127.0.0.1"
  port: 8080
  
# Journal 配置
journal:
  storage_path: "~/.opc200/data/journal"
  max_size: "1GB"
```

---

## 4. 平台特定实现

### 4.1 Windows (PowerShell)

**脚本位置**: `agent/scripts/install.ps1`

**核心功能**:
- 使用 PowerShell 5.1+ 或 PowerShell 7+
- 管理员权限检测（创建服务需要）
- Windows Service 注册（使用 sc.exe 或 New-Service）
- 防火墙规则自动添加（放行 8080 端口）

**命令行参数**:
```powershell
# 交互式安装（默认）
.\install.ps1

# 静默安装（自动化部署）
.\install.ps1 -OPC200PlatformUrl "https://platform.opc200.co" `
              -OPC200TenantId "CUST_001" `
              -OPC200ApiKey "sk-xxx" `
              -Silent
```

### 4.2 macOS/Linux (Bash)

**脚本位置**: `agent/scripts/install.sh`

**核心功能**:
- 单脚本支持 macOS 和 Linux
- systemd (Linux) / launchd (macOS) 服务注册
- 自动检测包管理器（brew/apt/yum）

**命令行参数**:
```bash
# 交互式安装
./install.sh

# 静默安装
./install.sh --opc200-platform-url "https://platform.opc200.co" \
             --opc200-tenant-id "CUST_001" \
             --opc200-api-key "sk-xxx" \
             --silent
```

---

## 5. 配置项说明

| 配置项 | 必需 | 说明 | 示例 |
|--------|------|------|------|
| `-OPC200PlatformUrl` / `--opc200-platform-url` | ✅（静默可省略用默认 URL） | 平台端点地址 | `https://platform.opc200.co` |
| `-OPC200TenantId` / `--opc200-tenant-id` / `OPC200_TENANT_ID` | ✅ | 租户唯一标识（与 OpenClaw `custom-*` 无关） | `CUST_001`, `user@example.com` |
| `-OPC200ApiKey` / `--opc200-api-key` / `OPC200_API_KEY` | ✅ | 认证密钥 | `sk-abc123...` |
| `INSTALL_DIR` / `--install-dir` | ❌ | 安装目录 | 默认 `~/.opc200` |
| `-OPC200Port` / `--opc200-port` | ❌ | 本地 Agent HTTP 端口 | 默认 `8080` |

---

## 6. 错误处理

### 6.1 错误码定义

| 错误码 | 说明 | 用户提示 |
|--------|------|---------|
| `E001` | 权限不足 | 请以管理员/root权限运行脚本 |
| `E002` | 网络连接失败 | 无法连接平台，请检查网络 |
| `E003` | 端口占用 | 端口 8080 被占用，请更换端口 |
| `E004` | 校验失败 | 下载文件校验失败，请重试 |
| `E005` | 服务注册失败 | 系统服务注册失败，请检查系统配置 |

### 6.2 回滚机制

安装失败时自动清理:
1. 停止已创建的服务
2. 删除已复制的文件
3. 恢复系统配置修改
4. 输出详细错误日志

---

## 7. 安全设计

### 7.1 API Key 存储
- 用户输入时不回显
- 存储在 `~/.opc200/.env`，权限 600
- 支持 Windows DPAPI / macOS Keychain / Linux keyring（后续版本）

### 7.2 传输安全
- 强制 HTTPS 与平台通信
- 证书固定（可选）

---

## 8. 后续优化方向

- [ ] 图形化安装界面（Windows MSI / macOS DMG）
- [ ] 容器化安装（Docker）
- [ ] 配置热更新（无需重启服务）
- [ ] 自动更新机制

---

## 9. 无仓库安装（Bootstrap + GitHub Release）

- **制品**：`opc200-agent-<semver>.zip` 与 **`SHA256SUMS`**（同 tag 的 GitHub Release）。
- **Bootstrap**：`agent/scripts/opc200-install.ps1`（Release 附带同名文件）。需设置 **`OPC200_GITHUB_REPO=owner/repo`**（或 `-GitHubRepo`）；**`-Version`** 为 semver 或 **`latest`**（默认读 `OPC200_INSTALL_VERSION`，未设则 `latest`）。
- **本地打包**：`agent/scripts/pack-agent-release.ps1` 或 CI（`release-opc-agent.yml`，打 tag `v*`）。解压根目录默认保留在 **`%USERPROFILE%\.opc200\agent-bundle\<ver>`**（供安装后 `PYTHONPATH` 指向的源码树）。

---

## 附录

### A. 参考脚本
- 现有 Linux 脚本: `scripts/install-local.sh`
- 现有云端脚本: `scripts/install-cloud.sh`

### B. 测试矩阵

| 平台 | 版本 | 架构 | 测试状态 |
|------|------|------|---------|
| Windows 11 | 23H2 | x64 | ⏳ 待测试 |
| Windows 10 | 22H2 | x64 | ⏳ 待测试 |
| macOS | 14.x | Apple Silicon | ⏳ 待测试 |
| macOS | 14.x | Intel | ⏳ 待测试 |
| Ubuntu | 22.04 | x64 | ⏳ 待测试 |
| Ubuntu | 20.04 | x64 | ⏳ 待测试 |
