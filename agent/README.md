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

### Windows 部署

#### step1. 构建 exe 可执行文件

目前 GitHub Release 未提供 `opc-agent-windows-amd64.exe` 时，可在仓库内先执行 `build-windows-exe.ps1` 本地构建，再配合 `install.ps1 -LocalBinary` 联调。

**命令**（在仓库根目录中执行）：

```powershell
# 先执行 build-windows-exe.ps1，构建安装包
.\agent\scripts\build-windows-exe.ps1
```

**产物**：`dist`目录下会生成 `opc-agent-windows-amd64.exe`

#### step2. 安装 opc-agent 服务

脚本默认从 GitHub Release 拉取：

`https://github.com/coidea-ai/OPC200/releases/download/v2.3.0/opc-agent-windows-amd64.exe`

但由于目前 Release 上尚无该 exe，安装会在「下载 Agent」步骤失败。所以通过 `-LocalBinary` 来启动刚刚本地生成的 exe 文件（也就是表格中的方式 A）。

| 方式                          | 说明                                                         |
| ----------------------------- | ------------------------------------------------------------ |
| **A. 本地二进制（推荐联调）** | 执行 `.\agent\scripts\build-windows-exe.ps1` 生成 `dist\opc-agent-windows-amd64.exe`，再用 `install.ps1 -LocalBinary` |
| **B. 先发布 Release**         | 打 `v2.3.0` tag，上传 `opc-agent-windows-amd64.exe` 与 `SHA256SUMS` 后再用默认下载流程 |

具体命令如下：

```bash
# 以管理员打开 PowerShell，进入脚本目录（路径按本机修改）
cd E:\projects\OPC200\agent\scripts

# 方式A：本地 exe
.\install.ps1 -Silent `
  -LocalBinary "D:\path\to\opc-agent-windows-amd64.exe" `
  -PlatformUrl "http://127.0.0.1:9091" `
  -CustomerId "win-e2e-001" `
  -ApiKey "dev-local-test"

# 方式B：如果 Release 已有 exe，执行以下命令
.\install.ps1 -Silent `
  -PlatformUrl "http://127.0.0.1:9091" `
  -CustomerId "win-e2e-001" `
  -ApiKey "dev-local-test"
```

说明：

- `CustomerId` 在 Pushgateway 中对应路径 `/metrics/job/<id>`；
- 本机 Pushgateway 一般**不校验** Bearer，`ApiKey` 填任意非空测试字符串即可。
- 交互模式安装时，「平台地址」可输入 `http://127.0.0.1:9091`。

- 成功时脚本应完成启动验证；健康检查 URL 为 `http://127.0.0.1:<Port>/health`（与 `-Port` 一致），默认 8080。

- 若 **8080** 已被占用，则更改端口，比如换成 `-Port 18080`。
- 参数说明见 `agent/scripts/install.ps1` 文件头注释。

#### step3. Windows 安装脚本与本机 Docker 平台联调

**前置条件**：本地 Docker 已经跑起 platform 平台服务。

**Pushgateway 是否收到该租户**：

打开 `http://localhost:9091`，能看到 `job="win-e2e-001"`。或者执行以下命令

```powershell
(Invoke-WebRequest -Uri "http://localhost:9091/metrics" -UseBasicParsing).Content | Select-String "win-e2e-001"
```

**Prometheus 是否已抓取**（等待约 15～30 秒）：

```powershell
curl "http://localhost:9090/api/v1/query?query=cpu_usage%7Bjob%3D%22win-e2e-001%22%7D"
```

`data.result` 非空即表示链路已通。

**Grafana（可选）**：打开 `http://localhost:3000`（默认账号见 `platform/docker-compose.yml`，一般为 `admin` / `opc200admin`），在 `Dashboards` 看查看有没有启动服务时设置的 User。比如示例中的 `-CustomerId "win-e2e-001" `，则表明 User 叫 `win-e2e-001`。

#### step4. 测试结束后清理

```powershell
cd E:\projects\OPC200\agent\scripts
.\uninstall.ps1 -Silent -InstallDir "$env:USERPROFILE\.opc200"
```

确认计划任务/旧服务已移除：

```powershell
Get-ScheduledTask -TaskName OPC200-Agent -ErrorAction SilentlyContinue
Get-Service OPC200-Agent -ErrorAction SilentlyContinue
```

#### FAQ 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| E001 非管理员 | 未提升权限 | 管理员 PowerShell 重试 |
| E002 下载失败 | Release 无文件或网络问题 | 检查 Release、代理，或使用 `-LocalBinary` |
| E003 端口占用 | 8080 被占 | `-Port` 换端口 |
| E005 计划任务失败 | 策略或权限 | 查看报错详情，确认以管理员执行 |
| 健康检查超时 | Agent 未监听或启动慢 | 查看 `agent.log`，确认二进制与配置一致 |
| Pushgateway 无数据 | `platform.url` 错误 | 核对 `config.yml` 中 `platform.url` 为 `http://127.0.0.1:9091` |
| Prometheus 无数据 | 抓取间隔未到 | 等待并检查 `platform/prometheus/prometheus.yml` |

### Mac/Linux 部署

#### step1. 构建可执行文件

原因同 Windows 一样，见上。

```bash
cd /mnt/e/projects/OPC200   # 按真实项目路径改
chmod +x agent/scripts/build-linux.sh
./agent/scripts/build-linux.sh
```

#### step2. 安装 opc-agent 服务

本地路径安装刚刚生成的二进制文件（已支持 `--local-binary`）：

```bash
sudo bash agent/scripts/install.sh --silent \
  --local-binary "/mnt/e/projects/OPC200/dist/opc-agent-linux-amd64" \
  --platform-url "http://127.0.0.1:9091" \
  --customer-id "test-001" \
  --api-key "dev"
```

交互安装时同样加上：`sudo bash ./install.sh --local-binary "/mnt/e/projects/OPC200/dist/opc-agent-linux-amd64"`，再按提示填平台地址等。

若以后 Release 里已有同名文件：去掉 `--local-binary`，脚本会改回从 GitHub 下载。

#### step3. 与本地 Docker 平台联调

#### step4. 测试结束后清理

```bash
# agents/scripts 路径
sudo bash ./uninstall.sh --install-dir "$HOME/.opc200"
```

按提示确认删除目录；若不要确认提示：

```bash
sudo bash ./uninstall.sh --install-dir "$HOME/.opc200" --silent
```

加 `--keep-data` 可只删二进制/配置而保留 `data/`。

## 用户安装（todo）

分两类：**Windows** 与 **Mac / Linux**。

### Windows

### Mac / Linux
