---
name: opc200-release-deliverables
description: Guides OPC200 developers through publishing GitHub Release deliverables (version alignment, v* tag, release-opc-agent CI, four-asset verification) per docs/architecture/USER_INSTALL_RUNBOOK.md. Use when shipping a new agent bundle, cutting a release, verifying opc200-agent zip and bootstrap scripts, or when the user mentions Release assets, tag push, or USER_INSTALL_RUNBOOK.
---

# OPC200 Release 交付物发布

权威说明见仓库 **`docs/architecture/USER_INSTALL_RUNBOOK.md`** §1；本 skill 将 §1 固化为可重复执行的检查清单与命令。

## 何时使用

- 需要发布新的 **无仓库安装** 可用制品（Bootstrap → `install.ps1` / `install.sh`）。
- 已改 **`agent/scripts`**、**`VERSION`** 或 **`.github/workflows/release-opc-agent.yml`**，要打 tag 触发发版。

## 交付物（四件套）

| 资产 | 作用 |
|------|------|
| `opc200-agent-<semver>.zip` | Agent 制品包 |
| `SHA256SUMS` | zip 的 SHA256 清单 |
| `opc200-install.ps1` | Windows 引导脚本 |
| `opc200-install.sh` | Linux/macOS 引导脚本 |

Workflow：`.github/workflows/release-opc-agent.yml`（`on.push.tags: v*`）。Tag 形如 **`v1.2.3`**，**不带 `v` 的 semver** 用于 `VERSION` 与 zip 文件名。

## 流程

### 1. 代码与分支（静态核对）

在**拟打 tag 的提交**上确认：

- [ ] `agent/scripts/opc200-install.ps1` 存在  
- [ ] `agent/scripts/opc200-install.sh` 存在  
- [ ] `.github/workflows/release-opc-agent.yml` 存在且会上传上述四件套  
- [ ] `agent/scripts/build-agent-bundle.sh`（或 workflow 引用的打包路径）与当前 workflow 一致  

合并策略（是否已进 `main`）按团队规范；本 skill 不替团队决定分支，只要求 **tag 指向的 commit 包含发版所需文件**。

### 2. 版本号对齐（必做）

以下必须**一致**（同一 semver，**无 `v` 前缀**）：

| 来源 | 路径或位置 |
|------|------------|
| 仓库根版本文件 | `VERSION` |
| Windows 第二阶段安装脚本 | `agent/scripts/install.ps1` 内 `AGENT_VERSION` |
| Linux 第二阶段安装脚本 | `agent/scripts/install.sh` 内 `AGENT_VERSION` |
| Git tag | `v<semver>`，例如 `VERSION` 为 `2.5.0` → tag **`v2.5.0`** |
| 制品 zip 名 | `opc200-agent-<semver>.zip`（由 workflow 从 tag 解析） |

若仅改文档、未改版本却需**重新发同一版本**，须用团队策略处理（例如撤包、新 patch 版本）；**禁止**在同一 tag 上重复 `git push` 期望覆盖 Release（通常需新 tag）。

### 3. 打 Tag 并推送

```bash
# 在干净工作区、目标分支上，且已与远端策略一致后：
git fetch origin
git tag -a "vX.Y.Z" -m "release: opc200-agent bundle X.Y.Z"
git push origin "vX.Y.Z"
```

将 `X.Y.Z` 换为与 `VERSION` 一致的 semver。

### 4. 确认 CI 成功

```bash
gh run list --workflow=release-opc-agent.yml --limit 5
gh run watch <run-id> --exit-status
```

在 GitHub Actions 中确认 **`Release OPC200 agent bundle`**（或 workflow 标题）对应该 tag **成功**。

**注意**：同一 `v*` push 可能触发仓库内其他监听 tag 的 workflow（例如 `deploy-production.yml`）。与发版无关的失败需单独排查，不否定 Release 已成功上传。

### 5. 核对 Release 四件套

```bash
gh release view "vX.Y.Z" --json name,tagName,assets --jq '.assets[].name'
```

期望至少出现：

- `opc200-agent-X.Y.Z.zip`
- `SHA256SUMS`
- `opc200-install.ps1`
- `opc200-install.sh`

或使用 API：

```bash
curl -sS "https://api.github.com/repos/<owner>/<repo>/releases/tags/vX.Y.Z" | head -c 4000
```

将 `<owner>/<repo>` 换成实际仓库（如 `coidea-ai/OPC200`）。

### 6. 建议：最小自测（可选）

- API：`releases/latest` 中 `tag_name` 与 assets 含 `opc200-agent-*.zip`。  
- 本机：下载 zip + `SHA256SUMS`，`sha256sum -c`（或等价）通过后解压，确认存在 **`agent/scripts/install.ps1`** 与 **`install.sh`**。  

详见 **`docs/architecture/USER_INSTALL_RUNBOOK.md`** §1.4。

## 给 Agent 的执行提示

- 打 tag、push、删除远端 tag 等**写操作**须用户确认权限与目标版本。  
- 发版前若项目要求 **CI 全绿**（lint、单测等），在 tag 之前于目标分支上先跑完团队规定的检查。  
- 更新 `VERSION` / `AGENT_VERSION` 时保持**单次提交只做版本与发版相关变更**的习惯，便于审计（与团队 Conventional Commits 规范一致）。

## 延伸阅读

- [reference.md](reference.md) — 路径速查与 `gh`/`curl` 片段  
- `docs/architecture/USER_INSTALL_RUNBOOK.md` — 开发者 §1 + 用户 §2  
- `docs/INSTALL_SCRIPT_SPEC.md` §9 — Bootstrap 与制品约定  
