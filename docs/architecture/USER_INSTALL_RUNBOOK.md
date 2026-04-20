# 无仓库安装跑通指南（开发者 / 用户）

> **目的**：按顺序操作，使 **GitHub Release 上的引导脚本 + 制品包** 能被真实用户一键跑通（Bootstrap → `install.ps1` / `install.sh`）。  
> **关联**：[`../INSTALL_SCRIPT_SPEC.md`](../INSTALL_SCRIPT_SPEC.md) §9 与 **§9.1**、[`../../agent/README.md`](../../agent/README.md)、[`PREINSTALLED_LOBSTER_ROADMAP.md`](PREINSTALLED_LOBSTER_ROADMAP.md) §2.9。

---

## 1. 开发者须先完成的事项

没有可下载的 **Release 资产**，用户侧「无仓库安装」必然失败。

### 1.1 代码与分支

- 发布所用分支（如 `feature/user-platform`）已合并实现：**`opc200-install.ps1`**、**`opc200-install.sh`**、**`.github/workflows/release-opc-agent.yml`**、打包脚本等与文档一致。
- 与主线的合并策略按团队规范执行（本指南不展开）。

### 1.2 打版本 Tag，触发 CI 发版

- **语义化版本**须与仓库根 **`VERSION`**、`install.ps1` 内 **`AGENT_VERSION`**、制品名 **`opc200-agent-<semver>.zip`** 一致。
- 示例：

```bash
git tag v2.5.1
git push origin v2.5.1
```

- 在 GitHub **Actions** 中确认 **`release-opc-agent`**（或当前 workflow 名称）对该 tag **执行成功**。

### 1.3 核对 Release 资产（必查）

打开该版本的 **GitHub Releases** 页面，确认至少包含：

| 文件 | 说明 |
|------|------|
| `opc200-agent-<semver>.zip` | 制品包 |
| `SHA256SUMS` | 与 zip 配套的校验文件 |
| `opc200-install.ps1` | Windows 引导脚本 |
| `opc200-install.sh` | Linux/macOS 引导脚本 |

缺任一项，`latest` 或固定版本下载/校验会失败。

### 1.4 建议：开发者自测（最小验证）

- **API**：访问  
  `https://api.github.com/repos/<owner>/<repo>/releases/latest`  
  确认 `tag_name` 与 `assets` 中存在上述 zip。
- **本机试跑**（任选平台）：
  - **Windows**：按 `agent/README.md`「用户使用」设置 `OPC200_GITHUB_REPO` 或使用 `-GitHubRepo`，执行 `opc200-install.ps1`。
  - **Linux**：设置 `OPC200_GITHUB_REPO` 或使用 `--github-repo`，执行 `opc200-install.sh`（依赖 `curl`、`unzip`、`python3` 等，见 README）。

**通过标准**：能下载 → SHA256 校验通过 → 解压后存在 `agent/scripts/install.ps1` 或 `install.sh` → 第二阶段安装脚本能启动（完整装完还取决于租户/密钥、网络、权限等）。

---

## 2. 用户应执行的操作

前提：**目标仓库已存在 §1 中的 Release**，且用户知道 **`owner/repo`**（例如 `coidea-ai/OPC200`）。

### 2.1 通用准备

- 准备 **租户 ID**、**平台 ApiKey**（静默安装必填）。
- 若需 **静默执行 OpenClaw onboard**：按 `agent/README.md` 配置 **`OPENCLAW_*`** 等环境变量。
- **Linux / WSL**：默认 onboard 使用 **`--install-daemon`**，须 **用户级 systemd** 可用（`/run/user/<uid>/bus` 等）；不满足时安装脚本在第 6 步 **退出**（见 `docs/INSTALL_SCRIPT_SPEC.md` §9.1）。**显式**跳过用户守护进程：`OPENCLAW_ONBOARD_SKIP_DAEMON=1`。

### 2.2 Windows

1. 从对应 **Release** 下载 **`opc200-install.ps1`**。
2. **管理员 PowerShell** 中：

```powershell
$env:OPC200_GITHUB_REPO = "owner/repo"
powershell -ExecutionPolicy Bypass -File .\opc200-install.ps1 -Version latest
```

3. 静默安装、OpenClaw、租户等参数见 **`agent/README.md`** 中「用户使用」与 Windows 小节（与 `install.ps1` 参数一致）。

### 2.3 Linux / macOS

1. 从 **Release** 下载 **`opc200-install.sh`**，并赋予执行权限：

```bash
chmod +x opc200-install.sh
```

2. 设置仓库并执行（示例为静默 + latest）：

```bash
export OPC200_GITHUB_REPO="owner/repo"
./opc200-install.sh --version latest --silent \
  --opc200-tenant-id "your-tenant" \
  --opc200-api-key "your-platform-key"
```

3. **Linux**：第二阶段会通过 **`sudo -E`** 调用 `install.sh`；需要本机 **`sudo`**，若依赖当前 shell 中的 `OPENCLAW_*`，**`-E`** 用于保留环境变量（详见 README）。装 OpenClaw 网关用户服务前请按 README / SPEC §9.1 准备好 **user systemd**（WSL：`systemd=true`、`loginctl enable-linger` 等）。

### 2.4 建议的「跑通」判据

- Bootstrap：无「校验失败」「找不到 Release 资源」类错误。
- 安装：`[STEP]` 流程走完；按文档可查看 **计划任务 / systemd 服务**；**健康检查 URL**（如 `http://127.0.0.1:8080/health`）可访问或短时后可用。

---

## 3. 推荐执行顺序（从发版到验收）

适合 **同一人** 兼任开发者与首位验证用户时按序操作：

1. **开发者**：推送 **`v*`** tag → 等待 CI 成功 → 确认 Release **四件套**齐全。  
2. **验证用户**：在 **干净 VM 或测试机** 上，仅下载引导脚本 + 设置 **`OPC200_GITHUB_REPO`**（或使用命令行 **`--github-repo` / `-GitHubRepo`**），先以 **`latest`** 跑通一条最小路径。  
3. 再测 **静默 + 真实租户/平台密钥**（与 AGENT-009 **M5** 验收场景一致；建议记录结果）。

---

## 4. 常见问题定位

| 现象 | 可能原因 |
|------|----------|
| 无法下载 zip / SHA256SUMS | 尚未创建 Release、tag 未推送、或 `OPC200_GITHUB_REPO` 写错 |
| 校验失败 | 本地文件不完整、Release 上 zip 与 `SHA256SUMS` 不匹配（需重发版或修正产物） |
| `install` 第二阶段立即失败 | 未用管理员/sudo、Python/依赖缺失、静默未提供租户/密钥 |
| Linux 装完环境变量丢失 | 未使用 `sudo -E`，或需在调用前 `export` 所需变量 |

---

## 5. 相关文档

- [`../INSTALL_SCRIPT_SPEC.md`](../INSTALL_SCRIPT_SPEC.md) §9 — Bootstrap 与制品约定  
- [`../../agent/README.md`](../../agent/README.md) — 「用户使用」与 Windows / Linux 安装参数示例  
- [`PREINSTALLED_LOBSTER_ROADMAP.md`](PREINSTALLED_LOBSTER_ROADMAP.md) §2.9 — 路线图与验收要点  
