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

开发模式下，脚本使用 `Python venv + 仓库源码` 运行 `opc-agent`（不下载 Release exe）。

---

### Windows

#### 安装

在 **管理员 PowerShell** 中进入 `agent/scripts` 执行。

`install.ps1` 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-PlatformUrl` | `https://platform.opc200.co` | 平台地址（第三部分采集；静默可省略则用默认） |
| `-CustomerId` | 无 | 租户标识（第三部分；静默必填） |
| `-ApiKey` | 无 | 平台推送密钥；OpenClaw onboard 已填模型密钥时复用；未采集时用本参数或 `OPC200_API_KEY` |
| `-InstallDir` | `$HOME\.opc200` | 安装目录 |
| `-Port` | `8080` | 本地健康检查端口 |
| `-Silent` | `False` | 静默安装（不交互） |
| `-RepoRoot` | 脚本目录 `..\..` | OPC200 仓库根目录 |
| `-FullRuntimeDeps` | `False` | 安装完整依赖（含重包，耗时长） |
| `-OpenClawOnboard` | `False` | **静默安装**时与 `OPENCLAW_ONBOARD=1` 等价，显式打开 onboard。**交互安装默认就会做 OpenClaw 首次配置**，一般不必传。 |
| `-SkipOpenClawOnboard` | `False` | 跳过 OpenClaw 首次配置（或设环境变量 `OPENCLAW_ONBOARD=0`） |
| `-OpenClawAuthChoice` | 空 | 等价于环境变量 `OPENCLAW_AUTH_CHOICE`（静默时常用） |

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
```

#### OpenClaw 首次配置

官方安装脚本在拉包阶段会设 `OPENCLAW_NO_ONBOARD=1`，避免在 **npm 安装结束时** 再弹一次官方交互向导；随后在 OPC200 脚本里统一用 **`openclaw onboard --non-interactive`** 落地配置。

- **交互安装（未加 `-Silent`）**：官方安装 OpenClaw CLI → **首次配置（onboard）** → **轻预装（skills + 模板）** → `doctor` / 网关重启。须选择模型提供方并采集密钥，然后 `openclaw onboard --non-interactive`。**不需要**再传 `-OpenClawOnboard`。
- **不想配置 OpenClaw**：传 `-SkipOpenClawOnboard`，或事先设置 `OPENCLAW_ONBOARD=0`。
- **静默安装（`-Silent`）**：默认**不**跑 OpenClaw onboard（便于 CI 仅装 Agent）。若要静默完成 OpenClaw 配置，需 **`OPENCLAW_ONBOARD=1`**（或 `-OpenClawOnboard`）并设置 `OPENCLAW_AUTH_CHOICE` 及对应密钥环境变量。
- **其它开关**：`OPENCLAW_SKIP_ONBOARD=1` 与 `-SkipOpenClawOnboard` 等价，强制跳过。
- **认证方式**：`OPENCLAW_AUTH_CHOICE`（或 `-OpenClawAuthChoice`），取值：`apiKey`（Anthropic）、`openai-api-key`、`gemini-api-key`、`custom-api-key`（须配置对应密钥，不再支持 `skip`）。官方参数说明见 [CLI Automation](https://docs.openclaw.ai/start/wizard-cli-automation)。
- **静默且启用 onboard 时**：必须设置 `OPENCLAW_AUTH_CHOICE`，并准备好对应密钥环境变量（如 `ANTHROPIC_API_KEY`、`OPENAI_API_KEY`、`GEMINI_API_KEY`）；`custom-api-key` 还需 `OPENCLAW_CUSTOM_BASE_URL`、`OPENCLAW_CUSTOM_MODEL_ID` 与 `CUSTOM_API_KEY`（plaintext）。`OPENCLAW_SECRET_INPUT_MODE=ref` 时按官方要求仅保留环境引用、勿缺省对应变量。
- **网关与健康**：默认网关端口 `18789`（可用 `OPENCLAW_GATEWAY_PORT` 覆盖）；onboard 后会探测 `OPENCLAW_GATEWAY_HEALTH_URL`，未设置时等价于 `http://127.0.0.1:<端口>/health`。`OPENCLAW_ONBOARD_STRICT=1` 时，onboard 进程非零退出或健康检查超时将**中止整个安装**；否则仅告警并继续安装 opc-agent。
- **超时**：`OPENCLAW_ONBOARD_TIMEOUT_SEC`（默认 `600`，秒）。

静默 + OpenClaw onboard + Anthropic 示例：

```powershell
$env:OPENCLAW_ONBOARD = "1"
$env:OPENCLAW_AUTH_CHOICE = "apiKey"
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # 勿提交到仓库

.\install.ps1 -Silent `
  -PlatformUrl "http://127.0.0.1:9091" `
  -CustomerId "win-e2e-001" `
  -ApiKey "dev-local-test"
```

#### 重启

```powershell
# 重启
Stop-ScheduledTask -TaskName "OPC200-Agent" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Start-ScheduledTask -TaskName "OPC200-Agent"

# 查看状态
Get-ScheduledTask -TaskName "OPC200-Agent" | Format-List TaskName,State
Get-ScheduledTaskInfo -TaskName "OPC200-Agent" | Format-List LastRunTime,LastTaskResult
```

#### 卸载

`uninstall.ps1` 参数说明：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `-InstallDir` | `$HOME\.opc200` | 安装目录 |
| `-KeepData` | `False` | 保留 `data/` |
| `-Silent` | `False` | 静默卸载（不交互确认） |
| `-PurgeOpenClaw` | `False` | 勾选时才执行 OpenClaw 官方卸载：`openclaw uninstall --all --yes --non-interactive`（未装 `openclaw` 或命令失败仅告警；CLI 全局包可能仍需自行 `npm`/`pnpm` 移除） |

卸载示例：

```powershell
cd E:\projects\OPC200\agent\scripts

# 交互卸载
.\uninstall.ps1

# 指定目录静默卸载
.\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200" -Silent

# 保留 data
.\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200" -KeepData

# 同时按官方推荐卸载 OpenClaw（服务/状态/工作区等，见 https://docs.openclaw.ai/cli/uninstall ）
.\uninstall.ps1 -InstallDir "$env:USERPROFILE\.opc200" -Silent -PurgeOpenClaw
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
| `--repo-root` | 脚本目录 `../..` | OPC200 仓库根目录 |
| `--full-runtime-deps` | `False` | 安装完整依赖（含重包，耗时长） |
| `--silent` | `False` | 静默安装（不交互） |
| `--openclaw-onboard` | `False` | **静默**时与 `OPENCLAW_ONBOARD=1` 等价。**交互安装默认即会做 OpenClaw 首次配置**，一般不必传。 |
| `--skip-openclaw-onboard` | `False` | 跳过 OpenClaw 首次配置（或 `OPENCLAW_ONBOARD=0`） |

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
```

与 Windows 相同：**交互安装默认会提示并完成 OpenClaw onboard**；静默需 `OPENCLAW_ONBOARD=1` 并设置 `OPENCLAW_AUTH_CHOICE` 与密钥。环境变量在 `sudo` 前 `export`，对静默 + onboard 使用 `sudo -E` 保留环境。交互模式下密钥通过 `read -rsp` 读入且仅在子 shell 中传给 `openclaw`。若系统有 GNU `timeout`，onboard 会受 `OPENCLAW_ONBOARD_TIMEOUT_SEC` 约束。

静默 + OpenClaw onboard + OpenAI 示例：

```bash
export OPENCLAW_ONBOARD=1
export OPENCLAW_AUTH_CHOICE=openai-api-key
export OPENAI_API_KEY=sk-...   # 勿提交到仓库

cd /path/to/OPC200/agent/scripts
sudo -E bash ./install.sh --silent \
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
| `--purge-openclaw` | `False` | 勾选时才执行 OpenClaw 官方卸载：`openclaw uninstall --all --yes --non-interactive`（未装 `openclaw` 或命令失败仅告警；CLI 全局包可能仍需自行 `npm`/`pnpm` 移除） |

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

# 同时按官方推荐卸载 OpenClaw（见 https://docs.openclaw.ai/cli/uninstall ）
sudo bash ./uninstall.sh --install-dir "$HOME/.opc200" --silent --purge-openclaw
```
