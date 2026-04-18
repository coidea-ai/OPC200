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
  -e TENANT_ID=opc-001 \
  -e API_KEY=sk-xxx \
  opc-agent:latest
```

## 开发

### Windows

本机开发时建议将 **OPC200 仓库完整克隆**到固定路径。

Agent 代码入口为 `agent/src/opc_agent/`（安装脚本会把仓库根目录写入 `PYTHONPATH` 并调用 `python -m agent.src.opc_agent.cli`）。

- **解释器**：需要 **Python 3.10+**（与 `install.ps1` 中 `Test-Environment` 一致）。优先使用 [python.org](https://www.python.org/downloads/windows/) 或 `winget install Python.Python.3.12` 安装，避免仅用 Microsoft Store 占位符 `WindowsApps\python.exe`。
- **运行安装脚本**：在 **管理员 PowerShell**（建议 5.1+）中执行 `install.ps1`，否则无法写计划任务、部分环境检测也会失败。
- **不跑安装脚本、直接调试 Agent**：在仓库根目录执行，例如  
  `python -m agent.src.opc_agent.cli --config <你的 config.yml 路径> run`  
  需自行准备 `config.yml`、`.env`（或环境变量）中的平台地址、租户与 `OPC200_API_KEY`。
- **单元测试**（仓库根）：`python -m pytest agent/src/tests -q`；单文件示例：`python -m pytest agent/src/tests/test_agent002_install.py -q`。
- **安装/目录约定**：以 `docs/INSTALL_SCRIPT_SPEC.md` 为准；新代码放在 `agent/` 下，勿在根目录遗留 `src/` 上扩展（见 `docs/architecture/DIRECTORY_MIGRATION.md`）。

#### 安装

在 **管理员 PowerShell** 中进入 `agent/scripts`，执行 `.\install.ps1`。完整流程约 **15 步**（环境 → OpenClaw → OPC200 Agent），步骤号见终端 `[STEP]` 输出。

**无仓库（GitHub Release）**：先下载同版本 `opc200-install.ps1`，再执行（需已发布的 `opc200-agent-<ver>.zip` + `SHA256SUMS`）：

```powershell
$env:OPC200_GITHUB_REPO = "your-org/OPC200"   # 示例
powershell -ExecutionPolicy Bypass -File .\opc200-install.ps1 -Version latest
```

详见 `docs/INSTALL_SCRIPT_SPEC.md` §9 与 `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md` §2.9。

**`install.ps1` 参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `-Silent` | switch | `$false` | **静默安装**：不交互询问；第三部分须通过参数或环境变量提供 `OPC200TenantId`（或 `OPC200_TENANT_ID`）、`OPC200ApiKey`（或 `OPC200_API_KEY`）等；OpenClaw onboard 默认**不**执行，除非另设 `OPENCLAW_ONBOARD=1` 或 `-OpenClawOnboard`。 |
| `-InstallDir` | string | `""` | Agent 安装根目录，默认 `$HOME\.opc200`（未传参时）。 |
| `-RepoRoot` | string | `""` | OPC200 **仓库根**（需含 `agent/`）。默认脚本所在目录的 `..\..`（即仓库根）。 |
| `-OpenClawOnboard` | switch | `$false` | **静默**时等价于要求执行 OpenClaw onboard（与 `OPENCLAW_ONBOARD=1` 一致）。**交互安装默认就会 onboard**，一般不必传。 |
| `-SkipOpenClawOnboard` | switch | `$false` | 跳过 OpenClaw 首次配置（`openclaw onboard`）；也可设环境变量 `OPENCLAW_ONBOARD=0`。 |
| `-OpenClawAuthChoice` | string | `""` | 与 `OPENCLAW_AUTH_CHOICE` 相同，静默 onboard 时常用。取值：`apiKey`、`openai-api-key`、`gemini-api-key`、`custom-api-key`（须配合对应密钥环境变量，**不再支持 skip**）。 |
| `-OPC200PlatformUrl` | string | `""` | **OPC200-Agent 服务**时写入 `config.yml` 的平台根地址。交互时可回车使用默认 `https://platform.opc200.co`；**静默**时若省略则脚本内使用上述默认 URL。 |
| `-OPC200TenantId` | string | `""` | **OPC200-Agent 服务**租户 ID（**勿**与 OpenClaw `custom-*` 混淆）。静默必填时可用环境变量 `OPC200_TENANT_ID`；交互安装在第三部分采集。租户值落盘位置与 YAML 键名以 `docs/INSTALL_SCRIPT_SPEC.md` 模板为准（运行时由 `opc_agent` 映射为 `TENANT_ID`）。 |
| `-OPC200ApiKey` | string | `""` | **OPC200-Agent 服务**推送指标用的平台密钥，写入安装目录 `.env`（`OPC200_API_KEY`）。若前面 OpenClaw onboard 已把模型密钥记入脚本内部变量，可与平台共用而不再传；也可用环境变量 `OPC200_API_KEY` 代替（静默）。 |
| `-OPC200Port` | int | `8080` | OPC200-Agent 服务 **健康检查**端口；安装前会检测占用。 |

**常用环境变量（与 OpenClaw 段配合，非 `param` 但安装脚本会读取）**

| 变量 | 说明 |
|------|------|
| `OPENCLAW_ONBOARD` | `1` 表示静默时也跑 onboard；`0` 表示跳过。 |
| `OPENCLAW_AUTH_CHOICE` | 与 `-OpenClawAuthChoice` 一致。 |
| `OPENCLAW_SKIP_ONBOARD` | `1` 时强制跳过 onboard。 |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GEMINI_API_KEY` / `CUSTOM_API_KEY` 等 | 按所选 `OPENCLAW_AUTH_CHOICE` 提供；`custom-api-key` 还需 `OPENCLAW_CUSTOM_BASE_URL`、`OPENCLAW_CUSTOM_MODEL_ID` 等。 |
| `OPENCLAW_GATEWAY_PORT` | 网关端口，默认 `18789`。 |
| `OPENCLAW_ONBOARD_STRICT` | `1` 时 onboard 或网关健康失败会中止整个安装。 |
| `OPC200_TENANT_ID` | 静默时可用作租户 ID，与 `-OPC200TenantId` 二选一或互为补充。 |
| `OPC200_API_KEY` | 静默时可用作平台密钥，与 `-OPC200ApiKey` 二选一或互为补充。 |

**示例**

```powershell
# 交互安装（默认精简依赖、含 OpenClaw 全流程）
cd E:\projects\OPC200\agent\scripts
.\install.ps1

# 指定仓库根与安装目录
.\install.ps1 -RepoRoot "E:\projects\OPC200" -InstallDir "$env:USERPROFILE\.opc200"

# 静默安装 Agent（不跑 OpenClaw onboard）
.\install.ps1 -Silent `
  -OPC200TenantId "tenant-001" `
  -OPC200ApiKey "your-platform-key"

# 静默 + 指定平台 URL
.\install.ps1 -Silent `
  -OPC200PlatformUrl "https://platform.opc200.co" `
  -OPC200TenantId "tenant-001" `
  -OPC200ApiKey "your-platform-key"

# 静默且执行 OpenClaw onboard（Anthropic）
$env:OPENCLAW_ONBOARD = "1" 			# 1 -> 执行 openclaw onboard
$env:OPENCLAW_AUTH_CHOICE = "apiKey"	# 指当前是 Anthropic
$env:ANTHROPIC_API_KEY = "sk-ant-..."	# Anthropic 的 apikey（勿提交仓库）
.\install.ps1 -Silent `
  -OPC200PlatformUrl "https://platform.opc200.co" `
  -OPC200TenantId "tenant-001" `
  -OPC200ApiKey "your-platform-key"
  
# 静默且执行 OpenClaw onboard（自定义模型）
$env:OPENCLAW_ONBOARD = "1"						# 1 -> 执行 openclaw onboard
$env:OPENCLAW_AUTH_CHOICE = "custom-api-key"	# 指当前是自定义的models，需要提供以下信息

$env:OPENCLAW_CUSTOM_BASE_URL = "https://your-llm.example/v1"	# 自定义模型的 base_url
$env:OPENCLAW_CUSTOM_MODEL_ID = "your-model-id"					# 自定义模型的 id
$env:CUSTOM_API_KEY = "sk-your-inference-key"					# 自定义模型的 api-key

# 可选：OPENCLAW_CUSTOM_COMPATIBILITY 默认 openai；可选 provider id
# $env:OPENCLAW_CUSTOM_COMPATIBILITY = "openai"
# $env:OPENCLAW_CUSTOM_PROVIDER_ID = "my-provider"

cd C:\path\to\OPC200\agent\scripts

.\install.ps1 -Silent -OpenClawOnboard -OpenClawAuthChoice "custom-api-key" `
  -RepoRoot "C:\path\to\OPC200" `
  -OPC200PlatformUrl "https://platform.opc200.co" `
  -OPC200TenantId "your-tenant-id" `
  -OPC200ApiKey "your-opc200-platform-key"
```

OpenClaw 段细节（onboard、轻预装 `tools.profile`、网关 RPC 探测等）见 `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md`。

#### 卸载

在 **管理员 PowerShell** 中进入 `agent/scripts`，执行 `.\uninstall.ps1`。

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-InstallDir` | `$HOME\.opc200` | 安装根目录。 |
| `-KeepData` | `$false` | 为 `$true` 时保留 `data/`，仅删除 `bin`、`config`、`logs`、`venv`、`.env` 等。 |
| `-Silent` | `$false` | 静默：不交互确认删除目录；是否保留 OpenClaw 仅由 `-KeepOpenClaw` 决定。 |
| `-KeepOpenClaw` | 未传 | **交互**：开头必须选择是否保留 OpenClaw。**静默**：传则表示保留；不传则卸载 OpenClaw（先停 gateway，再执行官方 `openclaw uninstall`）。 |

```powershell
# 交互（开头询问是否保留 OpenClaw）
.\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200"

# 静默删除 OPC200 目录并保留 OpenClaw
.\uninstall.ps1 -Silent -KeepOpenClaw -InstallDir "$env:USERPROFILE\.opc200"

# 静默一并卸载 OpenClaw（不传 -KeepOpenClaw）
.\uninstall.ps1 -Silent -InstallDir "$env:USERPROFILE\.opc200"
```

#### 重启 OPC200-Agent 服务

```powershell
# 重启
Stop-ScheduledTask -TaskName "OPC200-Agent" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName "OPC200-Agent"

# 查看状态
Get-ScheduledTask -TaskName "OPC200-Agent" | Format-List TaskName,State
Get-ScheduledTaskInfo -TaskName "OPC200-Agent" | Format-List LastRunTime,LastTaskResult
```

### Mac/Linux（含 WSL）

#### 安装

与 Windows 相同的三段流程，脚本为 `agent/scripts/install.sh`。静默示例：

```bash
./install.sh --silent \
  --opc200-platform-url "https://platform.opc200.co" \
  --opc200-tenant-id "tenant-001" \
  --opc200-api-key "your-platform-key"
```

（亦可用环境变量 `OPC200_TENANT_ID`、`OPC200_API_KEY` 代替对应参数，见 `docs/INSTALL_SCRIPT_SPEC.md`。）

#### 卸载
