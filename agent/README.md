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

## 用户安装

分两类：**Windows** 与 **Mac / Linux**。

### Windows

1. 以管理员身份打开 **PowerShell 5.1+**（脚本含 `#Requires -Version 5.1`）。
2. 进入本仓库 `agent/scripts` 目录，执行安装脚本（参数按实际填写；`-Silent` 可选）：

```powershell
cd agent\scripts
.\install.ps1 `
  -PlatformUrl "https://platform.opc200.co" `
  -CustomerId "opc-001" `
  -ApiKey "sk-xxx"
```

脚本会校验系统版本、拉取发布包、注册 **OPC200-Agent** 服务并启动。默认安装目录为 `~/.opc200`（即用户目录下 `.opc200`）。卸载可在同目录执行 `.\uninstall.ps1`。

若需自行用容器运行，可先安装 [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)，再按下文「构建」「运行」操作；数据目录在 PowerShell 中可写为 `-v ${env:USERPROFILE}\.opc200:/data`。

### Mac / Linux

1. 安装 [Docker Engine](https://docs.docker.com/engine/install/)（Mac 可用 [Docker Desktop](https://docs.docker.com/desktop/install/mac-install/)），确认 `docker version` 可用。
2. 在终端进入本仓库的 `agent` 目录，按下文「构建」生成镜像，再按「运行」启动容器；`-v ~/.opc200:/data` 将数据持久化到当前用户主目录下的 `.opc200`。

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
