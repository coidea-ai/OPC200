# 预装版小龙虾（OpenClaw）交付路线图

> **用途**：后续预装版安装、打包、观测相关工作以此文档为单一事实来源；完成项及时勾选，并在文末更新「变更记录」。  
> **最后更新**：2026-04-16（§2.8：OpenClaw 开箱即用配置自动化落地）

---

## 0. 目标与边界

### 0.1 目标

- 用户执行**一条安装命令**（或等价脚本），即可安装**开箱即用**的小龙虾：预置 `SOUL.md`、`IDENTITY.md`、`AGENTS.md`、`skills/` 等默认配置。
- 与 `opc-agent` 服务协同：在合适阶段将 **`agent-health` 指标语义**对齐为「**预装小龙虾整体健康**」（含网关等关键依赖），而非泛化或未定义的「Agent」含义。

### 0.2 产品定位硬约束（必须满足）

- **非深度定制**：不做 OpenClaw 私有分叉，不改 OpenClaw 内核逻辑，不交付“魔改发行版”。
- **官方渠道安装**：用户执行本项目脚本时，底层必须调用 OpenClaw 官方安装渠道，并默认安装**全量 latest**。
- **仅做轻预装层**：在官方安装完成后，仅自动完成两类动作：  
  1) 通过 OpenClaw 自带插件机制（如 clawhub / 原生命令）安装 skills；  
  2) 投放预置文档（`SOUL.md`、`IDENTITY.md`、`AGENTS.md` 等）。

### 0.3 分期依赖关系

- **先做**预装版的最小可运行面（路径、服务/进程形态、网关监听等尽量稳定），**再做** `agent-health` 采集重构，可减少返工。
- `agent-health` 的接口（指标名、标签、0/1 规则）可在第二期初与「小龙虾可观测面」一起冻结。

### 0.4 文档维护约定

- [ ] 每完成一条可验收子项，将对应 `- [ ]` 改为 `- [x]`。
- [ ] 合并较大里程碑时，在文末「变更记录」追加一行（日期 + 摘要）。
- [ ] 若计划项增删或档期调整，同步修改对应分期并记一条变更记录。

---

## 第一期：Demo（能演示「一键装 + 开箱即用」）

### 1.1 安装入口与产物

- [x] 提供 Windows（PowerShell）与 Linux/macOS（bash）**至少一种**可跑通的安装入口（另一种可标为后续）。
- [x] 安装脚本先通过 **OpenClaw 官方渠道**安装全量 latest，再执行本项目轻预装动作。
- [x] 轻预装产物包含：预置 `SOUL.md`、`IDENTITY.md`、`AGENTS.md`、`skills/` 落盘到**约定目录**。
- [x] 安装后用户能完成一次**核心演示流程**（与产品定义的「龙虾默认任务」一致）。

### 1.2 最低限度体验

- [ ] 下载/解压/权限等失败时有**明确报错**与**非零退出**（退出码细分可在第二期）。
- [ ] 文档中写明：安装命令、默认目录、如何卸载（允许第一期为「手动删除目录」级说明）。

### 1.3 本期明确不做（避免范围膨胀）

- [ ] 记录本期**刻意不包含**项（例如：完整 SHA256 链、企业离线包、完整回滚），避免与第二期混淆。

---

## 第二期：最小可交付 MVP（含强烈建议 + `agent-health` 对齐小龙虾）

> **交付含义**：可给外部用户**反复安装/升级**而不易翻车；`opc-agent` 的 `agent-health` 在本期完成语义与采集重构。

### 2.1 发布与完整性（强烈建议）

- [ ] 发布物附带**校验信息**（至少 SHA256；与 `INSTALL_SCRIPT_SPEC` 或现有 Release 流程对齐）。
- [ ] 安装脚本在解压/执行前完成**校验失败则中止**并清理临时文件。
- [x] 脚本中对 OpenClaw 安装步骤保持“官方 latest + 官方渠道”策略，不引入私有 fork 下载源。

### 2.2 幂等与版本

- [ ] 重复安装：不重复污染 `PATH` / shell profile 注入块。
- [ ] 同版本重复执行：行为明确（快速退出或提示「已安装」）。
- [ ] 分别记录**程序版本**与**预置包（preset）版本**（便于排障与对账）。

### 2.3 预置文件升级策略（强烈建议）

- [x] 首次安装：写入默认 `SOUL.md`、`IDENTITY.md`、`AGENTS.md`、`skills/`。
- [x] 升级：区分用户是否改动；未改动可覆盖；已改动**不直接覆盖**（如生成 `*.new` 或跳过并提示）。

### 2.4 原子安装与卸载

- [ ] 先写入临时目录，成功后再切换到正式目录（或等价原子策略）。
- [ ] 失败后可**再次运行**恢复到一致状态（无半截不可用残留）。
- [ ] 提供卸载路径：移除注入块、主程序目录；**用户数据目录**策略明确（默认保留或可选 `--purge`）。

### 2.5 参数与非交互

- [ ] 支持最小参数集：`--yes`、`-y`、`--preset`（若多预设）、`--install-dir` / `--data-dir`（按实际需要裁剪）。
- [ ] `--help` / `--version` 行为明确。

### 2.6 最小测试矩阵

- [ ] 干净环境首次安装。
- [ ] 同版本重复安装。
- [ ] 跨版本升级 + 用户已改过预置文件。
- [ ] 卸载后重装。

### 2.7 `opc-agent`：`agent-health` 采集重构（本期完成）

> **语义**：`agent-health` 表示**预装小龙虾的运行健康**（例如：龙虾核心是否正常工作、**网关是否正常**等）；实现前须与第一期/本期初冻结的**可观测面**（进程名、服务名、端口、配置路径）对齐。

- [x] 梳理现有代码中所有与 `agent-health` 相关的定义、采集、标签与上报路径（单一清单，避免遗漏）：实现位于 `agent/src/exporter/collector.py`，推送仍为 `MetricsCollector` → `MetricsPusher`。
- [x] 与产品/架构对齐：**健康判定规则**（必选项：本进程存活 + 网关 HTTP 2xx）已文档化至 `docs/METRICS_PROTOCOL.md`「`agent_health` 判定规则」小节。
- [x] **单一配置源**：默认 `OPENCLAW_GATEWAY_HEALTH_URL=http://127.0.0.1:18789/health`，与文档/编排中网关端口约定一致；可通过环境变量覆盖，与安装脚本 `OPENCLAW_*` 命名一致。
- [x] 未安装小龙虾或依赖未就绪时：`agent_health` 为 **`0`**（网关探测失败）；纯 Agent 场景可设 `OPENCLAW_GATEWAY_HEALTH_PROBE=0` 跳过网关探测。
- [x] 单元测试：`agent/src/tests/test_agent004_exporter.py` 覆盖网关成功/失败/连接错误、探测关闭、进程僵尸、采集异常路径。
- [ ] 与现有 `MetricsCollector` / 推送链路集成验收（本地或联调环境一次端到端）。

### 2.8 OpenClaw 开箱即用配置自动化（新增）

> **目标**：用户执行安装脚本后即可直接使用 OpenClaw，不再依赖手动执行 `openclaw dashboard` / `openclaw setup` 完成首次配置。

- [x] 冻结最小可用配置集：`OPENCLAW_AUTH_CHOICE` 支持 `apiKey` / `openai-api-key` / `gemini-api-key` / `custom-api-key`（须配置模型密钥，不支持 `skip`）；网关端口 `OPENCLAW_GATEWAY_PORT`（默认 18789）；自定义端点 `OPENCLAW_CUSTOM_*` / `CUSTOM_API_KEY`；与官方文档 `openclaw onboard --non-interactive` 对齐。
- [x] 安装脚本交互采集配置：非静默模式问答输入（Windows + Linux），敏感字段 `SecureString` / `read -rsp`；执行参数日志不打印密钥。
- [x] 静默模式参数化：`OPENCLAW_AUTH_CHOICE` + 对应 provider 环境变量；Windows 增加 `-OpenClawOnboard` / `-OpenClawAuthChoice` / `-SkipOpenClawOnboard`；Linux 增加 `--openclaw-onboard` / `--skip-openclaw-onboard`；**交互安装默认执行 onboard**；**静默**须 `OPENCLAW_ONBOARD=1`（或 CLI 开关）才跑 onboard，避免无密钥 CI 误跑；`OPENCLAW_ONBOARD=0` 或 `Skip` 可显式跳过。
- [x] 配置落地策略：优先官方 `openclaw onboard --non-interactive`（见 https://docs.openclaw.ai/start/wizard-cli-automation ）；**直接写 `openclaw.json` 的 fallback 仍列为后续**（schema 随版本变化，避免脚本侧误写）。
- [x] 成功判定与兜底：`OPENCLAW_GATEWAY_HEALTH_URL` 或默认 `http://127.0.0.1:<port>/health` 轮询；`OPENCLAW_ONBOARD_STRICT=1` 时 onboard 或健康失败则中止安装；否则告警继续并完成 opc-agent 安装。

---

## 第三期：可长期分发（规模化 / 企业化 / 长期维护）

### 3.1 发布与渠道

- [ ] `stable` / `beta`（或等价）渠道与版本策略。
- [ ] 变更日志、破坏性变更说明、弃用周期（如适用）。

### 3.2 升级、回滚与供应链

- [ ] 保留上一版本；失败回退或一键回滚策略。
- [ ] 签名验证（如 cosign/minisign 等）与发布门禁对齐。
- [ ] 合规需要时：SBOM、漏洞响应流程简述或链到 `SECURITY.md`。

### 3.3 企业场景

- [ ] 离线/内网安装包与镜像源说明。
- [ ] 代理、MDM/组策略类分发说明（按目标客群裁剪）。

### 3.4 可观测与运维

- [ ] 结构化日志、诊断打包命令、常见故障 playbook。
- [ ] `agent-health` 与多实例/多租户场景下的标签规范（若适用），与 `METRICS_PROTOCOL.md` 统一。

### 3.5 质量门禁

- [ ] CI：构建、测试、lint、发布物校验生成、安装脚本 dry-run（按仓库现有 CI 能力裁剪）。

---

## 变更记录

| 日期 | 摘要 |
|------|------|
| 2026-04-16 | Windows `install.ps1`：三段流程（环境 → OpenClaw → OPC200 Agent）；onboard 后轻预装；`doctor`+`gateway restart`；平台 URL/租户在 Agent 前采集；平台 ApiKey 复用模型密钥；无 exe 分支 |
| 2026-04-16 | 交互安装默认执行 OpenClaw onboard；静默仍须 `OPENCLAW_ONBOARD=1`；支持 `OPENCLAW_ONBOARD=0` / Skip 显式关闭 |
| 2026-04-16 | §2.8 落地：`install.ps1` / `install.sh` 可选 `openclaw onboard --non-interactive` + 网关 HTTP 健康检查；单测 `test_agent008_openclaw_onboard_install.py` |
| 2026-04-15 | 新增第二期 §2.8：OpenClaw 开箱即用配置自动化（最小配置集、交互采集、静默参数、配置落地与验证兜底） |
| 2026-04-15 | AGENT-007：Windows/Linux 卸载脚本交互对齐（确认是否卸载 OpenClaw + 卸载进度提示 + CLI 手动清理提醒） |
| 2026-04-15 | 第二期 §2.7：`agent_health` 改为 OpenClaw 网关 HTTP 探测 + 本进程存活；协议与单测已更新（端到端联调待办） |
| 2026-04-15 | 第一期 §1.1：核心演示流程已走通并完成勾选（安装入口 + 官方 OpenClaw + 轻预装 + 默认任务演示） |
| 2026-04-15 | AGENT-007：Linux 安装脚本在 OpenClaw 官方安装前补齐 Node v22+ 前置检测与自动安装兜底 |
| 2026-04-14 | 初版：三期计划 + 第二期纳入 `agent-health` 对齐小龙虾 |
| 2026-04-14 | 明确硬约束：非深度定制、官方渠道安装全量 latest、仅做轻预装层 |

---

## 相关文档

- `docs/INSTALL_SCRIPT_SPEC.md` — 安装目录与脚本约定  
- `docs/METRICS_PROTOCOL.md` — 指标与推送协议（若扩展 `agent-health` 需同步）  
- `agent/README.md` — `opc-agent` 构建与安装说明  
