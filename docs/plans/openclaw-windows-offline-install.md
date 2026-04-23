# Windows OpenClaw 离线安装实施计划

## 版本约定（固定）

- **产品锁定：OpenClaw 2026.4.15 稳定版**（npm 侧使用 **`openclaw@2026.4.15`**；灌 cache 与安装器内须写同一版本号）。
- **Node 锁定：24.15.0**：灌 cache、离线安装、安装器内置离线包均与此一致（见 `agent/scripts/node-v24.15.0/`）。
- 构建、灌 cache、离线安装、验收均以 **同一版本约束** 为准；升级大版本时另开变更。

---

## 1. 目标与边界

**目标**

- 在 **无公网 registry**（或仅内网）的 Windows 上，完成 **OpenClaw CLI（`openclaw` 全局命令）** 的安装，并继续支持现有安装器后续步骤（`onboard`、网关、`dashboard`、快捷方式等）。

**非目标（本期不做或另立项）**

- 替代 macOS 的 `.dmg` / `.zip`（`OpenClaw.app`）分发路径。
- Linux/macOS 离线安装（可复用同一 npm cache 思路，脚本不同）。
- 完全脱离 Node/npm 的「单 exe 内含解释器」形态（若未来需要再评估）。

**原则**

- **官方语义对齐**：离线机上的结果应等价于在同一环境下执行 `npm install -g openclaw@2026.4.15`。
- **平台一致**：生成 cache 的机器与安装目标机 **同为 Windows、同 CPU 架构、Node 均为 24.15.0**（与安装器离线 Node 包一致）。

---

## 2. 方案概述（推荐：npm cache + 离线全局安装）

**原理**

1. 在 **可联网的 Windows** 上，使用 **独立 npm cache 目录** 执行一次 `npm install -g openclaw@2026.4.15`，使该目录内包含安装所需全部包的 tarball。
2. 将 **整个 cache 目录** 作为制品打包，随安装器或内网分发。

**在离线 Windows 上**

1. 解压 cache 到本地路径（或由安装器释放到固定路径）。
2. `npm config set cache <cache 路径>`（仅当前会话或用户级，按实现选择）。
3. `npm install -g openclaw@2026.4.15 --offline --prefer-offline`。
4. 确保全局 `bin` 在 PATH 中（npm 默认会写入用户级路径；安装器需校验 `openclaw` 可解析）。

**与「整目录 zip 全局 prefix」的区别**

| 方式 | 说明 |
|------|------|
| **cache + 离线 install（推荐）** | 搬运的是「包缓存」，离线机由 npm 重新解包、建链，行为与线上一致。 |
| **直接 zip 全局 prefix** | 搬运「已展开树」，路径/Node 小版本更敏感，维护成本高，作备选。 |

---

## 3. 版本与资源锁定

| 项 | 要求 |
|----|------|
| **openclaw 版本** | **固定 2026.4.15 稳定版**：灌 cache 与离线安装均使用 `openclaw@2026.4.15`；发布前可用 `npm view openclaw@2026.4.15 version` 核对。 |
| **Node** | **24.15.0**，与 `node-v24.15.0` 离线包及安装器行为一致。 |
| **架构** | Windows **x64** 为主；若需 x86，需单独灌一套 cache。 |

---

## 4. 分阶段实施

### 阶段 A：构建侧（CI 或发布机）

1. **环境**：Windows runner 或固定构建机，预装 **Node 24.15.0**（与产物一致）。
2. **灌 cache**（示例）：
   - 设置 `npm cache` 为仓库内固定目录，例如 `agent/scripts/openclaw-npm-cache/`（或 `dist/openclaw-npm-cache`）。
   - 执行：`npm install -g openclaw@2026.4.15 --cache <上述绝对路径>`。
3. **校验**：
   - 同机 `npm install -g openclaw@2026.4.15 --offline --prefer-offline` 能成功（可选，用于验证 cache 完整性）。
   - `openclaw --version` 可执行。
4. **artifact**：将 **cache 目录** 整体纳入 `OpenClawInstaller.zip`（或单独 zip，由安装器释放）；记录 **版本号**（文本或 manifest）。

### 阶段 B：安装器脚本（`openclaw-installer.ps1`）

1. **移除或替换**依赖错误制品的逻辑：不再假设 `openclaw-releases/OpenClaw-*.zip` 为 Windows 可执行 CLI（该 zip 为 macOS `.app` 场景）。
2. **新增流程**（顺序建议）：
   - 现有硬检测（Node、端口、磁盘、网络策略按产品决定是否保留「联网检测」）。
   - 确保 Node 为 **24.15.0**（沿用现有离线 Node 解压逻辑，不足则装）。
   - 将内置 **npm cache** 解压/复制到 `%LOCALAPPDATA%\OpenClaw\npm-cache`（或固定路径）。
   - `npm config set cache <路径>`（进程级或用户级，需验证不污染用户全局 npm）。
   - `npm install -g openclaw@2026.4.15 --offline --prefer-offline`。
   - 校验 `Get-Command openclaw` 或 `Get-OpenClawCmd` 成功。
3. **失败处理**：明确错误信息（cache 缺失、版本不匹配、平台不一致）。

### 阶段 C：打包与 Release

1. `pack-openclaw-installer-release.ps1`：
   - 增加对 **npm cache 目录** 的复制与校验（或先由 CI 生成再 pack）。
   - 更新 zip 内容说明（README / 路线图）。
2. **体积**：cache 可能较大，需评估 Release 资产大小与下载体验。

### 阶段 D：测试与验收

1. **干净 Windows VM**（无预装 openclaw、无公网或阻断 npm registry）。
2. 运行安装器 exe，完成全流程。
3. **验收**：`openclaw --version`、`openclaw gateway status`（或等价）、与现有 onboard/快捷方式步骤一致。

---

## 5. 风险与缓解

| 风险 | 缓解 |
|------|------|
| npm 依赖含 **postinstall / 原生模块**，离线装失败 | 灌 cache 时使用与目标机相同 **Node 24.15.0** / OS；失败时查 `npm-debug.log`。 |
| **全局 bin 路径** 未进 PATH | 安装器在安装后显式 `Refresh` env 或把 `npm prefix -g` 下 `bin` 写入用户 PATH。 |
| **用户本机已有全局 npm** | `npm config set cache` 作用域限定为子进程或临时 `NPM_CONFIG_CACHE`，避免覆盖用户全局配置（需具体实现）。 |
| cache **体积过大** | 仅打包 `npm install -g openclaw` 所需依赖；或按版本增量更新策略（后续）。 |

---

## 6. 文档与配置

- 更新 `agent/README.md`「离线安装」小节，指向本计划与最终实现。
- 在代码或 `manifest` 中 **单一来源** 锁定 **`OPENCLAW_NPM_VERSION=2026.4.15`**、**`NODE_VERSION=24.15.0`**（与灌 cache、安装器参数一致）。

---

## 7. 建议的下一步（实现顺序）

1. 在本地/CI 上跑通 **灌 cache → 打包目录 → 离线机 `npm install -g --offline`** 手工验证。
2. 改 `openclaw-installer.ps1`：接入 cache + 离线 `npm install -g`，删除/旁路错误的 `Expand-Archive` OpenClaw zip 逻辑。
3. 更新 `pack-openclaw-installer-release.ps1` 与契约测试。
4. 在干净 VM 上做端到端验收。
