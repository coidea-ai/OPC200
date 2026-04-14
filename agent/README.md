# OPC Agent (用户侧)

OPC200 用户端部署组件，为单个用户提供轻量级 AI 助手服务。

## 目录结构

```
agent/
├── src/                    # 源代码
│   ├── gateway/           # 精简版 OpenClaw Gateway
│   ├── journal/           # 本地 SQLite 存储
│   ├── exporter/          # 指标推送到平台
│   ├── selfhealer/        # 自修复机制
│   └── updater/           # 版本更新客户端
├── config/                # 配置文件
├── skills/                # 用户侧 Skills
└── scripts/               # 安装/卸载脚本
```

## 构建

```bash
cd agent
docker build -t opc-agent:latest .
```

## 运行

```bash
docker run -d \
  --name opc-agent \
  -v ~/.opc200:/data \
  -e PLATFORM_URL=https://opc200.co \
  -e CUSTOMER_ID=opc-001 \
  -e API_KEY=sk-xxx \
  opc-agent:latest
```

## 开发

开发模式下，脚本默认使用 `Python venv + 仓库源码` 运行 `opc-agent`（无需先构建可执行文件）。  
如需二进制模式，可显式传 `--binary` / `-UseBinary` 或 `--local-binary` / `-LocalBinary`。

---

### Windows

#### 安装

在 **管理员 PowerShell** 中进入 `agent/scripts` 执行。

`install.ps1` 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-PlatformUrl` | `https://platform.opc200.co` | 平台地址（Pushgateway 根地址） |
| `-CustomerId` | 无 | 租户标识，必填（静默模式） |
| `-ApiKey` | 无 | API Key，必填（静默模式） |
| `-InstallDir` | `$HOME\.opc200` | 安装目录 |
| `-Port` | `8080` | 本地健康检查端口 |
| `-Silent` | `False` | 静默安装（不交互） |
| `-LocalBinary` | 空 | 使用本地 exe，跳过下载/源码模式 |
| `-UseBinary` | `False` | 强制使用 Release 二进制模式 |
| `-RepoRoot` | 脚本目录 `..\..` | OPC200 仓库根目录 |
| `-FullRuntimeDeps` | `False` | 安装完整依赖（含重包，耗时长） |

安装示例：

```powershell
# 交互安装（默认：源码 + 精简依赖）
cd E:\projects\OPC200\agent\scripts
.\install.ps1

# 静默安装（默认：源码 + 精简依赖）
.\install.ps1 -Silent `
  -PlatformUrl "http://127.0.0.1:9091" `
  -CustomerId "win-e2e-001" `
  -ApiKey "dev-local-test"

# 静默 + 完整依赖
.\install.ps1 -Silent -FullRuntimeDeps `
  -PlatformUrl "http://127.0.0.1:9091" `
  -CustomerId "win-e2e-001" `
  -ApiKey "dev-local-test"

# 使用本地 exe 安装（前提：需要先执行 build-windows-exe.ps1 生成 exe 文件）
.\install.ps1 -Silent `
  -LocalBinary "E:\projects\OPC200\dist\opc-agent-windows-amd64.exe" `
  -PlatformUrl "http://127.0.0.1:9091" `
  -CustomerId "win-e2e-001" `
  -ApiKey "dev-local-test"
```

#### 卸载

`uninstall.ps1` 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-InstallDir` | `$HOME\.opc200` | 安装目录 |
| `-KeepData` | `False` | 保留 `data/` |
| `-Silent` | `False` | 静默卸载（不交互确认） |

卸载示例：

```powershell
cd E:\projects\OPC200\agent\scripts

# 交互卸载
.\uninstall.ps1

# 指定目录静默卸载
.\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200" -Silent

# 保留 data
.\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200" -KeepData
```

---

### Mac/Linux（含 WSL）

#### 安装

在 `agent/scripts` 目录中使用 `sudo` 执行。

`install.sh` 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--platform-url` | `https://platform.opc200.co` | 平台地址（Pushgateway 根地址） |
| `--customer-id` | 无 | 租户标识，必填（静默模式） |
| `--api-key` | 无 | API Key，必填（静默模式） |
| `--install-dir` | `$HOME/.opc200` | 安装目录 |
| `--port` | `8080` | 本地健康检查端口 |
| `--local-binary` | 空 | 使用本地二进制路径 |
| `--repo-root` | 脚本目录 `../..` | OPC200 仓库根目录 |
| `--binary` | `False` | 强制二进制下载模式 |
| `--full-runtime-deps` | `False` | 安装完整依赖（含重包，耗时长） |
| `--silent` | `False` | 静默安装（不交互） |

安装示例：

```bash
# 交互安装（默认：源码 + 精简依赖）
cd /mnt/e/projects/OPC200/agent/scripts
sudo bash ./install.sh

# 静默安装（默认：源码 + 精简依赖）
sudo bash ./install.sh --silent \
  --platform-url "http://127.0.0.1:9091" \
  --customer-id "linux-e2e-001" \
  --api-key "dev-local-test"

# 静默 + 完整依赖
sudo bash ./install.sh --silent --full-runtime-deps \
  --platform-url "http://127.0.0.1:9091" \
  --customer-id "linux-e2e-001" \
  --api-key "dev-local-test"

# 使用本地二进制安装（前提：需要先执行 build-linux.sj 生成可执行文件）
sudo bash ./install.sh --silent \
  --local-binary "/mnt/e/projects/OPC200/dist/opc-agent-linux-amd64" \
  --platform-url "http://127.0.0.1:9091" \
  --customer-id "linux-e2e-001" \
  --api-key "dev-local-test"
```

#### 卸载

`uninstall.sh` 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--install-dir` | `$HOME/.opc200` | 安装目录 |
| `--keep-data` | `False` | 保留 `data/` |
| `--silent` | `False` | 静默卸载（不交互确认） |

卸载示例：

```bash
cd /mnt/e/projects/OPC200/agent/scripts

# 交互卸载
sudo bash ./uninstall.sh

# 指定目录静默卸载
sudo bash ./uninstall.sh --install-dir "$HOME/.opc200" --silent

# 通过 sudo 安装在 root 目录时
sudo bash ./uninstall.sh --install-dir "/root/.opc200"

# 保留 data
sudo bash ./uninstall.sh --install-dir "$HOME/.opc200" --keep-data
```

## 用户安装（todo）

分两类：**Windows** 与 **Mac / Linux**。

### Windows

### Mac / Linux
