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

### Linux / macOS（含 WSL）

本机开发建议将 **OPC200 仓库完整克隆**到固定路径。

Agent 代码入口为 `agent/src/opc_agent/`（安装脚本会把仓库根目录写入 `PYTHONPATH`/`runtime.env` 并调用 `python -m agent.src.opc_agent.cli`）。

- **解释器**：需要 **Python 3.10+**（与 `install.sh` 中环境检查一致）。Linux 可用发行版包或 [python.org](https://www.python.org/downloads/source/)；macOS 可用 `brew install python@3.12`。
- **运行安装脚本**：Linux 需 **root 或 sudo**（systemd 写 `/etc/systemd/system/`）；macOS 使用 launchd，脚本不以 root 跑完整流程时须保证对 `~/Library/LaunchAgents` 等与安装目录的写权限。在 `agent/scripts` 下执行：`sudo ./install.sh`（Linux）或 `./install.sh`（macOS，按提示）。
- **不跑安装脚本、直接调试 Agent**：在仓库根执行，例如  
  `python3 -m agent.src.opc_agent.cli --config <你的 config.yml 路径> run`  
  需自行准备 `config.yml`、`.env`（或环境变量）中的平台地址、租户与 `OPC200_API_KEY`。
- **单元测试**（仓库根）：`python3 -m pytest agent/src/tests -q`；单文件示例：`python3 -m pytest agent/src/tests/test_agent003_install.py -q`。
- **安装/目录约定**：以 `docs/INSTALL_SCRIPT_SPEC.md` 为准；新代码放在 `agent/` 下，勿在根目录遗留 `src/` 上扩展（见 `docs/architecture/DIRECTORY_MIGRATION.md`）。

**无仓库（GitHub Release）**：下载与 Release 同版本的 `opc200-install.sh`，`chmod +x` 后执行（需已存在 `opc200-agent-<ver>.zip` 与 `SHA256SUMS`）。Linux 下第二阶段会 **`sudo -E`** 调用 `install.sh`，以便继承当前 shell 中的 `OPENCLAW_*` 等环境变量（若需保留）。

```bash
export OPC200_GITHUB_REPO="your-org/OPC200"
bash /path/to/opc200-install.sh --version latest --silent \
  --opc200-tenant-id "tenant-001" --opc200-api-key "your-platform-key"
```

详见 `docs/INSTALL_SCRIPT_SPEC.md` §9。

#### 安装

在 `agent/scripts` 下执行 `./install.sh`（Linux 下通常 `sudo ./install.sh`）。主流程与 Windows **15 步**对齐（环境 → 安装目录 → Node（Linux）→ 网络 → OpenClaw 官方安装 → onboard → 轻预装含 `tools.profile` → 网关配置 → **平台与租户** → venv → 安装部署 → systemd/launchd → 验证），`[STEP]` 序号见终端输出。

**`install.sh` 参数（与 `install.ps1` 对齐）**

| 参数 | 说明 |
|------|------|
| `--silent` | 静默安装；第三部分须 `--opc200-tenant-id` / `OPC200_TENANT_ID` 与平台 ApiKey；OpenClaw onboard 默认不执行，除非 `--openclaw-onboard` 或 `OPENCLAW_ONBOARD=1`。 |
| `--install-dir DIR` | 安装根目录，默认 `$HOME/.opc200`。 |
| `--repo-root DIR` | OPC200 仓库根（含 `agent/`），默认脚本所在目录的 `../..`。 |
| `--opc200-platform-url URL` | 平台根地址；静默时可省略则用默认 `https://platform.opc200.co`。 |
| `--opc200-tenant-id ID` | 租户 ID；兼容旧名 `--customer-id`。 |
| `--opc200-api-key KEY` | 平台密钥；兼容 `--api-key`。 |
| `--opc200-port N` | Agent HTTP 健康检查端口，默认 `8080`；兼容 `--port`。 |
| `--openclaw-onboard` | 静默时要求执行 `openclaw onboard`（同 `OPENCLAW_ONBOARD=1`）。交互安装默认会 onboard。 |
| `--skip-openclaw-onboard` | 跳过 onboard；同 `OPENCLAW_SKIP_ONBOARD=1`。 |
| `--binary` / `--local-binary PATH` | 使用发布二进制路径（非 venv 源码模式）。 |
| `--full-runtime-deps` | venv 使用完整依赖列表（体积大、耗时长）。 |

**常用环境变量**：与 Windows 相同，`OPENCLAW_ONBOARD`、`OPENCLAW_AUTH_CHOICE`、`OPENCLAW_ONBOARD_STRICT`、`OPC200_TENANT_ID`、`OPC200_API_KEY`、`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` 等，见上表 Windows 小节。

**示例**

```bash
cd /path/to/OPC200/agent/scripts

# 直接交互式安装
sudo ./install.sh

# 静默安装 + 不跑 openclaw onboard
sudo ./install.sh --silent \
  --opc200-platform-url "https://platform.opc200.co" \
  --opc200-tenant-id "tenant-001" \
  --opc200-api-key "your-platform-key"

# 静默安装 + 跑 openclaw onboard
sudo env \
  OPENCLAW_ONBOARD=1 \
  OPENCLAW_AUTH_CHOICE=custom-api-key \
  OPENCLAW_CUSTOM_BASE_URL="https://your-llm.example/v1" \
  OPENCLAW_CUSTOM_MODEL_ID="your-model-id" \
  CUSTOM_API_KEY="sk-your-inference-key" \

./install.sh --silent --openclaw-onboard \
	--opc200-platform-url "https://platform.opc200.co" \
	--opc200-tenant-id "your-tenant-id" \
	--opc200-api-key "your-opc200-platform-key"
```

可选：`OPENCLAW_CUSTOM_COMPATIBILITY=openai`、`OPENCLAW_CUSTOM_PROVIDER_ID=...`；严格失败可再加 `OPENCLAW_ONBOARD_STRICT=1`。

#### 卸载

在 `agent/scripts` 下执行 **`sudo ./uninstall.sh`**（Linux）或 **`./uninstall.sh`**（macOS，视安装目录权限而定）。行为与 `uninstall.ps1` 对齐：先必选 **是否保留 OpenClaw**（交互），再停服务、删目录；卸载 OpenClaw 前会先 **`openclaw gateway stop`**（若可检测到网关），再执行官方 `openclaw uninstall --all --yes --non-interactive`。

| 参数 | 说明 |
|------|------|
| `--install-dir DIR` | 安装根目录，默认 `$HOME/.opc200`。 |
| `--keep-data` | 保留 `data/`，仅删除 `bin`、`config`、`logs`、`venv`、`.env` 等。 |
| `--silent` | 不交互确认删目录；是否保留 OpenClaw 仅由 `--keep-openclaw` 决定（不传则尝试卸载 OpenClaw）。 |
| `--keep-openclaw` | 保留本机 OpenClaw（与 `-KeepOpenClaw` 一致）。 |
| `--purge-openclaw` | 兼容旧参数，表示要卸载 OpenClaw；推荐改用默认行为 + 不传 `--keep-openclaw`。 |

```bash
sudo ./uninstall.sh --install-dir "$HOME/.opc200"

sudo ./uninstall.sh --silent --keep-openclaw --install-dir "$HOME/.opc200"

sudo ./uninstall.sh --silent --install-dir "$HOME/.opc200"
```

#### 重启 OPC200-Agent 服务（Linux systemd）

```bash
sudo systemctl restart opc200-agent
sudo systemctl status opc200-agent
journalctl -u opc200-agent -f
```

#### 重启 / 查看（macOS launchd）

```bash
launchctl unload ~/Library/LaunchAgents/co.opc200.agent.plist 2>/dev/null
launchctl load ~/Library/LaunchAgents/co.opc200.agent.plist
tail -f ~/.opc200/logs/agent.log
```

## 用户使用

### 第一步，下载引导脚本

从 GitHub **Release** 下载引导脚本。

**Windows（PowerShell）**

```powershell
# 在 D 盘创建一个名为 OPC200 的文件夹
New-Item -ItemType Directory -Force -Path "D:\OPC200" | Out-Null

# 从 GitHub 下载 PowerShell 安装脚本，保存到刚才创建的 D:\OPC200 文件夹里。
Invoke-WebRequest -Uri "https://github.com/coidea-ai/OPC200/releases/latest/download/opc200-install.ps1" -OutFile "D:\OPC200\opc200-install.ps1"
```

**Linux / macOS**

```bash
# 创建文件夹 /data/opc200
mkdir -p /data/opc200

# 从 GitHub 下载安装脚本，保存到 /data/opc200 目录
curl -fsSL -o /data/opc200/opc200-install.sh "https://github.com/coidea-ai/OPC200/releases/latest/download/opc200-install.sh"

# 给脚本添加 “可执行权限”
chmod +x /data/opc200/opc200-install.sh
```

注意：URL 中的 `coidea-ai/OPC200` 指仓库的地址，需要与第二步命令里的 **`-GitHubRepo` / `--github-repo`** 要一致。

### 第二步，执行安装脚本

#### Windows

1. 管理员身份打开 powershell。

2. 用户交互式引导安装

   ```powershell
   # 进入刚才创建的 D:\OPC200 文件夹
   cd D:\OPC200
   
   # 会询问用户并让用户输入相关信息
   powershell -ExecutionPolicy Bypass -File .\opc200-install.ps1 `
     -GitHubRepo "coidea-ai/OPC200" `
     -Version latest `
     -ExtractParent "D:\OPC200"
   ```

3. 如果不想交互式安装，可以选择静默安装（示例：**静默 + OpenClaw onboard + `custom-api-key`**）

   `custom-api-key` 时，**兼容 OpenAI 的 base URL、模型 ID、推理用 API Key** 须通过环境变量 **`OPENCLAW_CUSTOM_BASE_URL`**、**`OPENCLAW_CUSTOM_MODEL_ID`**、**`CUSTOM_API_KEY`** 提供（安装脚本静默路径从环境读取，与下方 `install.ps1` 参数表一致）。请把占位符换成你的真实值，**勿将密钥写入版本库**。

   ```powershell
   # 进入刚才创建的 D:\OPC200 文件夹
   cd D:\OPC200

   # OpenClaw custom 端点（须先于同一 PowerShell 会话中设置，再调用引导脚本）
   $env:OPENCLAW_CUSTOM_BASE_URL = "https://your-llm.example/v1"
   $env:OPENCLAW_CUSTOM_MODEL_ID = "your-model-id"
   $env:CUSTOM_API_KEY = "sk-your-inference-key"
   # 可选：$env:OPENCLAW_CUSTOM_COMPATIBILITY = "openai"
   # 可选：$env:OPENCLAW_CUSTOM_PROVIDER_ID = "my-provider"

   powershell -ExecutionPolicy Bypass -File .\opc200-install.ps1 `
     -GitHubRepo "coidea-ai/OPC200" `
     -Version latest `
     -ExtractParent "D:\OPC200" `
     -Silent `
     -OpenClawOnboard `
     -OpenClawAuthChoice "custom-api-key" `
     -OPC200PlatformUrl "https://platform.opc200.co" `
     -OPC200TenantId "your-tenant-id" `
     -OPC200ApiKey "your-opc200-platform-key"
   ```

#### Linux / macOS

todo

#### 命令常用参数含义

| Windows (`opc200-install.ps1`) | Linux/macOS (`opc200-install.sh`) | 含义                                                         |
| ------------------------------ | --------------------------------- | ------------------------------------------------------------ |
| `-GitHubRepo`                  | `--github-repo`                   | **必填（若未设环境变量）**：Release 所在仓库，格式 `owner/repo`。 |
| `-Version`                     | `--version`                       | 要装的版本：`latest`（默认跟最新 Release）或 **不带 `v` 的语义化版本**（如 `2.5.0`）。 |
| `-ExtractParent`               | `--extract-parent`                | **可选**：下载的 zip、`SHA256SUMS` 与解压目录的根路径。不设则默认在用户主目录下 `.opc200\agent-bundle\<版本>`（Windows）或 `$HOME/.opc200/agent-bundle/<版本>`（Linux/macOS）。若希望**所有文件落在同一个自选文件夹**（例如整盘不用 C:），把脚本与 `-ExtractParent` 指到**同一目录**即可。 |
| `-DownloadOnly`                | `--download-only`                 | 仅下载并校验，不执行第二阶段的 `install.ps1` / `install.sh`。 |

第二阶段安装（静默、租户、OpenClaw 等）的参数与下文 **「安装」** 小节中 `install.ps1` / `install.sh` 一致；Bootstrap 会把多余参数**原样传给**第二阶段。

### FAQ

#### 固定某一版本（不用 `latest`）

将 `-Version` / `--version` 设为 **语义化版本号，不带 `v` 前缀**（例如 `2.5.0`），且该版本在 GitHub 上已存在对应 **tag** 与 **Release**。

#### 安装完成后如何确认「跑通」

- Bootstrap 阶段无「找不到 Release」「SHA256 校验失败」等错误。
- 第二阶段终端中 **`[STEP]`** 流程能走完。
- Agent **健康检查**（默认端口见安装参数 **`-OPC200Port` / `--opc200-port`**，常为 `8080`）：例如 `http://127.0.0.1:8080/health`（以你本机配置为准）。

服务查看方式：**Windows** 见下文「重启 OPC200-Agent 服务」计划任务；**Linux** 见 `systemctl status opc200-agent`。

#### 可选：私有仓库或 API 限流

若 Release 在**私有仓库**或访问 GitHub API 受限，可设置环境变量 **`GITHUB_TOKEN`**（有读 Release 权限的 token），再执行上述命令；Bootstrap 会把 token 用于 API 请求。
