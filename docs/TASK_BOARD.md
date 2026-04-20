# OPC200 多 Agent 协同任务板

<!--
📍 你在哪：活跃任务板（只显示未完成/进行中）
📦 当前版本：v2.1.0（任务板结构 v1，内容 v2.1.0）
🔍 找历史：archive/phase-1-mvp.md
📊 看变更：CHANGELOG.md
📝 写归档：Phase 结束复制已完成任务到 archive/phase-X.md
-->

> 多 Agent 协同工作指南与任务追踪

**项目**: OPC200 Push 架构改造  
**分支**: `feat/push-architecture`  
**最后更新**: 2026-04-21（新增 Phase 1.5：4.24 活动冲刺任务拆解）

---

## 📋 使用规则

### 任务状态流转

```
📥 待领取 (Open) → 🏃 进行中 (In Progress) → 👀 审核中 (Review) → ✅ 已完成 (Done)
                    ↓
                ⏸️ 阻塞中 (Blocked)
                    ↓
                ❌ 已取消 (Cancelled)
```

### 任务领取规则

1. **认领方式**: 在任务下方回复 `"@agent-name 认领"`
2. **单任务制**: 一个 Agent 同时最多进行 **2 个** 任务
3. **超时释放**: 任务 4 小时无更新自动标记为 `"待重新认领"`（AI Coding 节奏快）
4. **阻塞上报**: 遇到阻塞立即标记状态并 `@other-agent` 协助

### 任务优先级

| 标识 | 优先级 | 说明 |
|------|--------|------|
| 🔴 P0 | 紧急 | 阻塞整体进度，需立即处理 |
| 🟡 P1 | 高 | 当前阶段关键任务 |
| 🟢 P2 | 中 | 重要但可并行处理 |
| ⚪ P3 | 低 | 优化类任务，可延后 |

---

## 🎯 近期总目标（Phase 1：AI Coding 3天冲刺）

### 目标概述

实现 OPC200 Push 架构 MVP：**平台侧可接收用户侧指标，用户侧可一键安装并推送基础健康信息。**

### 成功标准（验收条件）

- [ ] **平台侧**: Grafana 可看到实时在线用户数和基础健康指标（CPU/内存/磁盘）
- [ ] **用户侧**: Windows/Mac/Linux 一键安装脚本可用
- [ ] **端到端**: 至少 5 个测试用户可同时在线，数据隔离正确，离线可告警

### 关键里程碑

| 阶段 | 时间 | 平台侧交付 | 用户侧交付 | 联合验收 |
|------|------|-----------|-----------|---------|
| **Day 1** | 4月10日 | Prometheus+Pushgateway+Grafana 可运行 | 安装脚本方案确定 | 对齐指标协议 |
| **Day 2** | 4月11日 | 多租户隔离+用户统计面板 | exporter 采集+推送实现 | 1 用户联调通过 |
| **Day 3** | 4月12日 | Alertmanager 离线告警 | 跨平台安装脚本完成 | 5 用户灰度测试 |

---

## 🔴 P0 - 当前优先级任务（Phase 1）

### 平台侧任务（@fairy-kimi 负责）

> 注：PLAT-001~006 已完成，详见 [Phase 1 归档](archive/phase-1-mvp.md)
>
#### PLAT-001: 搭建 Prometheus + Pushgateway 本地环境

- **状态**: ✅ 已完成（Phase 1 归档）
- **负责人**: @fairy-kimi
- **协作方**: 无
- **预计 AI 工时**: 30min
- **产出**:
  - ✅ `platform/docker-compose.yml`（Prometheus + Pushgateway 基础版）
  - ✅ 本地可运行 `docker-compose up`
  - ✅ Pushgateway 可接收测试推送
- **归档**: [phase-1-mvp.md](archive/phase-1-mvp.md)

---

#### PLAT-002: 配置 Grafana 基础 Dashboard

- **状态**: ✅ 已完成（Phase 1 归档）
- **负责人**: @fairy-kimi
- **协作方**: 无
- **预计 AI 工时**: 1h
- **产出**:
  - ✅ `platform/grafana/provisioning/dashboards/` 基础面板
  - ✅ 可查看 Pushgateway 接收的原始指标
- **依赖**: PLAT-001 ✅
- **归档**: [phase-1-mvp.md](archive/phase-1-mvp.md)

---

#### PLAT-003: 定义指标推送协议

- **状态**: ✅ 已完成
- **负责人**: @fairy-kimi
- **协作方**: @zhang-yao-claw, @zhang-chenyang-claw（用户侧需确认）
- **预计 AI 工时**: 30min
- **截止**: Day 1 中午
- **产出**:
  - ✅ `docs/METRICS_PROTOCOL.md` - 指标推送协议文档
  - ✅ 标准 labels: `tenant_id`, `agent_version`, `os`
  - ✅ 标准指标: `agent_health`, `cpu_usage`, `memory_usage`, `disk_usage`
  - ✅ 推送 endpoint: `https://platform.opc200.co/metrics/job/<tenant-id>`
  - ✅ Python 示例代码（单条+批量推送）
  - ✅ 错误处理和指数退避重试策略
- **协议文档位置**: `docs/METRICS_PROTOCOL.md`
- **测试验证**: `platform/tests/test_plat003_metrics_protocol.py` (11 tests passing)
- **已协商确认**（2026-04-10）：
  1. **离线缓存机制**: JSON Lines 文件（`spool/queue.jsonl`），上限 500 条，超出丢最旧，恢复后分批推送（每批 50 条），超过 24h 丢弃
  2. **批量推送上限**: 100 条/次
  3. **推送频率**: 60 秒
  4. **数据压缩**: 暂不启用

---

#### PLAT-004: 实现多租户数据隔离

- **状态**: ✅ 已完成（已验证）
- **负责人**: @fairy-kimi / Remua02
- **协作方**: 无
- **预计 AI 工时**: 2h
- **实际完成**: Day 1 下午
- **产出**:
  - ✅ Prometheus 配置: 按 `tenant_id` 标签自动隔离
  - ✅ Grafana: 数据源配置支持多租户查询
- **验证**: Grafana 面板显示 3个租户（opc-001/002/003）数据正确隔离
- **依赖**: PLAT-001, PLAT-003

---

#### PLAT-005: Grafana 面板：在线用户数、健康状态统计

- **状态**: ✅ 已完成（已验证）
- **负责人**: @fairy-kimi / Remua02
- **协作方**: 无
- **预计 AI 工时**: 2h
- **实际完成**: Day 1 下午
- **产出**:
  - ✅ Dashboard: "OPC200 多租户监控"
  - ✅ 面板 1: 租户数量统计（3个租户在线）
  - ✅ 面板 2: CPU/内存/磁盘使用率（按租户分色）
  - ✅ 面板 3: 租户健康状态明细表
- **验证截图**: 显示 opc-001/002/003 实时数据
- **依赖**: PLAT-004

---

#### PLAT-006: Alertmanager 离线告警配置

- **状态**: ✅ 已完成（2026-04-14）
- **负责人**: @kimi-claw
- **产出**:
  - ✅ `platform/alertmanager/alertmanager.yml`
  - ✅ `platform/tests/test_plat006_alertmanager.py`
  - ✅ 邮件通知测试通过
- **备注**: 告警链路打通，可检测离线并发送邮件

---

### 用户侧任务（@zhang-yao-claw / @zhang-chenyang-claw 负责）

#### AGENT-001: 设计安装脚本方案

- **状态**: ✅ 已完成
- **负责人**: @zhang-yao-claw
- **协作方**: @zhang-chenyang-claw
- **预计 AI 工时**: 30min
- **实际完成**: Day 1 下午
- **产出**:
  - ✅ `docs/INSTALL_SCRIPT_SPEC.md` - 跨平台安装脚本设计规范
  - ✅ 安装流程: 下载 → 配置环境变量 → 启动 Agent
  - ✅ 配置项: `PLATFORM_URL`, `OPC200_TENANT_ID` / `TENANT_ID`, `API_KEY`
  - ✅ 数据目录: `~/.opc200/`
  - ✅ 错误码定义、安全设计、目录结构
- **提交**: `4111c8b` - docs: add Windows install script spec and project setup docs

#### AGENT-002: 实现 Windows 安装脚本（PowerShell）

- **状态**: ✅ 已完成（v2 重写）
- **负责人**: @zhang-yao-claw
- **协作方**: 无
- **预计 AI 工时**: 2h
- **实际完成**: Day 3（2026-04-12 重写）
- **产出**:
  - ✅ `agent/scripts/install.ps1` — 主流程 15 步（1/15–15/15）：环境 → OpenClaw（含 onboard、轻预装 `tools.profile=full`、网关 RPC 优先探测）→ OPC200 Agent；严格按 AGENT-001 SPEC；仅 Python venv+源码
  - ✅ `agent/scripts/uninstall.ps1` — 先 OPC200 再可选卸 OpenClaw；`-KeepOpenClaw`；支持 KeepData
  - ✅ `agent/src/tests/test_agent002_install.py` — 安装脚本规范一致性测试
  - ✅ 目录结构 `~/.opc200/`（bin/config/data/journal/exporter/logs）
  - ✅ 端口占用检测、磁盘空间检查
  - ✅ 错误码 E001-E005（按 SPEC §6.1）
  - ✅ 失败自动回滚（按 SPEC §6.2）
  - ✅ .env ACL 权限受限存储 API Key
- **测试**: `pytest agent/src/tests/test_agent002_install.py` 规范一致性测试通过
- **提交**: `d2c84fb`（v2），~~`7515747`~~（v1 已废弃）
- **v2 改进**:
  - 安装目录从 `$LOCALAPPDATA\OPC200` 改为 `~/.opc200/`（与 SPEC 对齐）
  - 新增 `bin/` 子目录、端口检测、回滚机制（Windows 现仅 venv+源码，无 Release exe 校验）
  - 删除旧 TEST_PLAN.md / LOCAL_TEST_GUIDE.md / run-local-tests.sh
- **依赖**: AGENT-001 ✅

---

#### AGENT-003: 实现 Mac/Linux 安装脚本（Bash）

- **状态**: ✅ 已完成（v2 重写）
- **负责人**: @zhang-yao-claw
- **协作方**: 无
- **预计 AI 工时**: 1.5h
- **实际完成**: Day 3（2026-04-12 重写）
- **产出**:
  - ✅ `agent/scripts/install.sh` — 7 步安装流程，严格按 AGENT-001 SPEC
  - ✅ `agent/scripts/uninstall.sh` — 支持 --keep-data 保留数据
  - ✅ `agent/src/tests/test_agent003_install.py` — 61 个规范一致性测试
  - ✅ 支持 macOS（launchd）和 Linux（systemd）双服务管理
  - ✅ 自动检测 OS/架构（amd64/arm64）、包管理器（brew/apt/yum/dnf/pacman）
  - ✅ SHA256 校验（sha256sum / shasum 兼容）
  - ✅ 错误码 E001-E005、失败自动回滚
  - ✅ .env chmod 600 安全存储 API Key
  - ✅ config.yml YAML 模板（platform/customer/agent/gateway/journal/logging）
- **测试**: 61/61 规范一致性测试通过
- **依赖**: AGENT-001 ✅

---

#### AGENT-004: 实现 exporter 指标采集

- **状态**: ✅ 已完成（v2 重写）
- **负责人**: @zhang-yao-claw
- **协作方**: 无
- **预计 AI 工时**: 2h
- **实际完成**: Day 3（2026-04-12 重写）
- **产出**:
  - ✅ `agent/src/exporter/collector.py` — 基于 psutil 跨平台采集
  - ✅ `agent/src/tests/test_agent004_exporter.py` — 16 个单元测试
  - ✅ CPU / 内存 / 磁盘使用率采集（psutil 统一跨平台）
  - ✅ Agent 健康状态检查（进程状态 + zombie 检测）
  - ✅ `SystemMetrics.to_prometheus(tenant_id)` 输出符合 PLAT-003 协议
  - ✅ psutil 未安装时抛出明确 RuntimeError
- **测试**: 16/16 单元测试通过
- **提交**: `cb0c61d`（v2），~~`62cdfa8`~~（v1 已废弃）
- **v2 改进**:
  - 使用 psutil 替代手写 subprocess，消除 `/proc/stat` 单次读取不准、`wmic` 废弃等问题
  - `_check_health()` 不再重复采集，接收已采集的值做判断
  - 字段名与 PLAT-003 完全对齐（`cpu_usage` / `memory_usage` / `disk_usage` / `agent_health`）
- **依赖**: PLAT-003 ✅
- **阻塞解除**: AGENT-005 现在可以开始

---

#### AGENT-005: 实现 exporter 指标推送

- **状态**: ✅ 已完成（v2 重写）
- **负责人**: @zhang-yao-claw
- **协作方**: @fairy-kimi（协议确认）
- **预计 AI 工时**: 2h
- **实际完成**: Day 3（2026-04-12 重写）
- **产出**:
  - ✅ `agent/src/exporter/pusher.py` — 调用 `collector.collect_all()` 推送指标
  - ✅ `agent/src/tests/test_agent005_pusher.py` — 14 个单元测试
  - ✅ Bearer Token 认证，Prometheus text format 推送
  - ✅ 指数退避重试（5 次，最大 60s，含 jitter）
  - ✅ 离线缓存 JSON Lines（`spool/queue.jsonl`，上限 500 条，超 24h 丢弃）
  - ✅ 恢复后分批推送（每批 50 条），批量上限 100 条/次
  - ✅ 推送间隔 60 秒，支持 HTTPS 代理
  - ✅ 支持环境变量 fallback（PLATFORM_URL / TENANT_ID / API_KEY）
- **测试**: 14/14 单元测试通过
- **提交**: `d73af7a`（v2）
- **v2 改进**:
  - 接口与 AGENT-004 v2 完全对齐（`collect_all()` / `SystemMetrics` 字段名一致）
  - `_build_payload()` 直接调用 `SystemMetrics.to_prometheus(tenant_id)`，消除字段名硬编码
- **依赖**: AGENT-004 ✅, PLAT-003 ✅

---

#### AGENT-006: 联调测试（端到端验证）

- **状态**: ✅ 已完成
- **负责人**: @zhang-yao-claw + @fairy-kimi
- **协作方**: 双方
- **预计 AI 工时**: 1h
- **截止**: Day 3 下午
- **产出**:
  - 1 个完整用户链路验证通过
  - 安装脚本 → 启动 Agent → 推送指标 → 平台可见
- **依赖**: 双方 Day 1-2 任务完成

---

## 🟡 P1 - 高优先级任务（Phase 2）

#### AGENT-007: 脚本支持安装 OpenClaw（官方 latest + 轻预装 + health 打通）

- **状态**: ✅ 已完成
- **负责人**: 未分配
- **预计 AI 工时**: 6h
- **描述**: 基于官方渠道安装 OpenClaw 最新版，在其上叠加轻预装层，并打通 exporter 对 OpenClaw 健康数据采集
- **里程碑**:
  - [x] M1 官方渠道安装最新版：安装脚本默认通过 OpenClaw 官方渠道安装全量 latest（官方入口 + https + 官方域名白名单）
  - [x] M2 轻预装层：通过 OpenClaw 自带插件机制安装 skills，投放 `SOUL.md`/`IDENTITY.md`/`AGENTS.md`（skills 失败仅告警继续；文档存在写 `.new`）
  - [x] M3 exporter 打通 openclaw health：`agent_health` 默认探测 `http://127.0.0.1:18789/health` + 本进程存活；详见 `docs/METRICS_PROTOCOL.md`（端到端联调见 Roadmap §2.7 末项）
- **详细计划文档**: `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md`
- **补充**（2026-04-21）：Linux `install.sh` 在 `sudo` 下将 OpenClaw 状态目录对齐 **`SUDO_USER` 的 `~/.openclaw`**，支持 **`OPENCLAW_STATE_HOME`**；`gateway`/`onboard`/8b 补启统一 `HOME`，避免 **`Missing HOME`** 与 `/root` 错位（见 Roadmap §2.8）。
- **补充**（2026-04-22）：Linux 第 6 步 **用户级 systemd** 预检与 onboard 日志识别后 **中止**；**`OPENCLAW_ONBOARD_SKIP_DAEMON`**；`INSTALL_SCRIPT_SPEC` §9.1 与 `agent/README.md` 对齐（见 Roadmap §2.8）。

#### AGENT-008: OpenClaw 开箱即用配置自动化（免手动 setup）

- **状态**: ✅ 已完成
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 4h
- **描述**: 安装脚本自动完成 OpenClaw 最小可用配置（模型提供商/模型/API Key 等），支持交互问答与静默参数输入，完成后可直接可用。
- **里程碑**:
  - [x] M1 明确最小可用配置集（`OPENCLAW_AUTH_CHOICE` + 网关端口 + custom 端点变量；与官方 onboard 文档对齐）
  - [x] M2 安装阶段交互采集 + 静默参数输入（Windows `install.ps1` + Linux `install.sh`）
  - [x] M3 非引导式配置落地（`openclaw onboard --non-interactive`；写配置文件 fallback 列为后续，见 Roadmap §2.8）
  - [x] M4 网关可用性：**Linux** 不在 onboard 段轮询 HTTP（由第 8/8b 步负责）；用户级 systemd 不满足时第 6 步 **退出**；`OPENCLAW_ONBOARD_STRICT` 用于 onboard **超时/其他失败** 的严格中止（**Windows** `install.ps1` 曾含 onboard 后 HTTP 探测，可与 Linux 行为分别看待，以脚本为准）
- **详细计划文档**: `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md`

#### AGENT-009: 无仓库一键安装（Bootstrap + 版本化制品包）

- **状态**: 🏃 进行中
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 8h
- **依赖**: AGENT-002、AGENT-003、`AGENT_VERSION` 与发布渠道可约定（无硬依赖某平台任务）
- **描述**: 用户无需 `git clone`：通过托管的 **Bootstrap 脚本**（Windows PowerShell / Linux curl）下载 **Release 制品包（zip/tar）+ `SHA256SUMS`**，校验后解压，再以 **`-RepoRoot` / `--repo-root`** 调用现有 `install.ps1` / `install.sh`，完成 OpenClaw 官方安装 + 轻预装 + OPC200 Agent（与当前仓库内安装等价）。
- **里程碑**:
  - [x] **M1 交付物定义冻结**：制品包最小目录树、`opc200-agent-<ver>.zip` + `SHA256SUMS`；`AGENT_VERSION` 与 `VERSION` 对齐
  - [x] **M2 Bootstrap（Windows）**：`agent/scripts/opc200-install.ps1`（下载、校验、解压至 `%USERPROFILE%\.opc200\agent-bundle\<ver>`、`install.ps1` 二阶段；校验失败 exit 4）
  - [x] **M3 Bootstrap（Linux/macOS）**：`agent/scripts/opc200-install.sh`（下载/校验/unzip、`sudo -E install.sh --repo-root` 透传）；`release-opc-agent.yml` 附带；`README` / `INSTALL_SCRIPT_SPEC` §9；`test_agent009_bootstrap_bash.py`
  - [x] **M4 CI 发布**：`.github/workflows/release-opc-agent.yml`（tag `v*`）+ `build-agent-bundle.sh` / `pack-agent-release.ps1`
  - [ ] **M5 验收**：无 Git 干净 VM「一条命令」装通；篡改包字节 VM 复现；文档互链已完成
- **详细计划文档**: `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md` **§2.9**

#### AGENT-010: 调整 Python import 路径

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 1h
- **描述**: 批量替换 `from src.xxx` → 新包名

#### AGENT-011: 实现 selfhealer/l1_local_fix.py

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 3h
- **描述**: L1 本地自动修复机制

#### AGENT-012: 实现 updater/update_client.py

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 4h
- **描述**: 版本更新客户端

#### AGENT-013: 创建 platform/docker-compose.yml 完整版

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 1h
- **描述**: 包含 version-control 服务

---

## 🟢 P2 - 中优先级任务（Phase 3）

#### AGENT-014: 创建 shared/proto/ 通信协议

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 2h

#### AGENT-015: 实现 version-control 版本管理服务

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 6h

#### AGENT-016: 迁移测试文件到 tests/agent/ 和 tests/platform/

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 1.5h

---

## ⚪ P3 - 低优先级任务（Backlog）

#### AGENT-017: 删除旧目录 src/, skills/, config/

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 30min

#### AGENT-018: 完善 CI/CD 脚本适配新结构

- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 2h
- **描述**: 调整 CI workflow 以匹配新的代码目录结构

---

## 🟠 Phase 1.5：4.24 活动冲刺（4/21–4/24）

> **目标**: 4月24日活动现场支持 40+ 用户成功安装 OpenClaw + Skills，完成课题讨论与协作。
> **冻结时间**: 4月23日晚（所有 P0 必须完成）

### 成功标准（验收条件）

- [ ] 用户成功安装 OpenClaw（Windows/Mac 一键脚本）
- [ ] 用户成功安装预定 Skills（按课题分组分发）
- [ ] 用户成功使用 Claw 能力讨论和解答课题
- [ ] 平台侧可监控 40+ 用户实时在线状态
- [ ] 用户可改进 Skills、可上传自定义 Skills
- [ ] 用户希望 Claw 能帮他完成后续工作（留存钩子）

### 关键里程碑

| 阶段 | 时间 | 里程碑 | 负责人 |
|------|------|--------|--------|
| **Day -3** | 4/21 | 需求确认冻结 + 域名开通 + 云服务器就绪 | 琛阳 + 李明 |
| **Day -2** | 4/22 | 平台侧部署完成 + 安装脚本域名替换 + 资源站点就绪 | 李明 + 张尧 |
| **Day -1** | 4/23 | 40用户并发压测通过 + 飞书告警联调 + 备选方案就绪 | 李明 + 张尧 |
| **Day 0** | 4/24 | 现场支持：大屏幕展示 + 专属Skills分发 + 技术支持 | 全员 |

---

### 🔴 P0 - 阻塞级（4月23日前必须完成）

#### INFRA-001: 开通子域名 `opc200.meerkatai.cn`

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 30min
- **截止时间**: 4/22
- **交付物**:
  - DNS A 记录指向云服务器 IP
  - `opc200.meerkatai.cn` 可解析
- **阻塞影响**: 阻塞所有安装脚本 URL 和 Exporter 推送地址
- **备注 / 待确认**:
  - ⚠️ 域名审批进度？如 4/22 拿不到，需准备备用域名/IP 直连 fallback

---

#### INFRA-002: 云服务器准备与基础环境

- **状态**: 📥 待领取
- **负责人**: @li-ming / Danny
- **预计 AI 工时**: 1h
- **截止时间**: 4/22
- **交付物**:
  - 云服务器 IP、SSH 访问凭证
  - Docker + Docker Compose 安装完成
  - 防火墙开放必要端口（80/443/9091/9093 等）
- **备注 / 待确认**:
  - ⚠️ 服务器规格？（建议 ≥2C4G，带宽 ≥5Mbps，40并发推送）
  - ⚠️ 是 Danny 提供还是自行购买？

---

#### PLAT-007: 平台侧服务部署

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 2h
- **截止时间**: 4/23
- **交付物**:
  - `docker-compose up` 正常运行（Prometheus + Pushgateway + Grafana + Alertmanager）
  - Dashboard 可通过域名访问
  - Pushgateway 可接收测试指标推送
- **依赖**: INFRA-001 ✅, INFRA-002 ✅
- **备注 / 待确认**:
  - ⚠️ Pushgateway 默认配置扛不住 40 并发，需调整 `--persistence.file` 和 `--persistence.interval`
  - ⚠️ 建议推送频率从 60s 调整为 120s，降低并发压力

---

#### PLAT-008: 资源站点目录结构搭建

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 1h
- **截止时间**: 4/23
- **交付物**:
  - 资源站点目录结构就绪：
    ```
    opc200.meerkatai.cn/
    ├── install/
    │   ├── windows.ps1
    │   └── mac-linux.sh
    ├── resources/
    │   ├── openclaw-images/       # 安装时必要镜像
    │   ├── skills/
    │   │   ├── topic-001.zip      # 课题1 skill bundle
    │   │   ├── topic-002.zip
    │   │   └── ...
    │   └── custom-skills/         # 用户上传的skills
    └── metrics/                   # Pushgateway 接收端点
    ```
- **依赖**: INFRA-001 ✅, PLAT-007 ✅

---

#### AGENT-019: 安装脚本域名替换

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 1h
- **截止时间**: 4/23
- **交付物**:
  - `install.ps1` / `install.sh` 中所有下载 URL 替换为 `opc200.meerkatai.cn`
  - `opc200-install.ps1` / `opc200-install.sh` Bootstrap 脚本域名替换
  - 本地干净 VM 测试通过
- **依赖**: INFRA-001 ✅, PLAT-008 ✅
- **备注 / 待确认**:
  - ⚠️ 如域名延迟，需在脚本内加 fallback（直连 IP）

---

#### AGENT-020: Exporter 推送 URL 调整

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 30min
- **截止时间**: 4/23
- **交付物**:
  - `agent/src/exporter/pusher.py` 推送地址改为 `opc200.meerkatai.cn/metrics/job/<tenant-id>`
  - 与 PLAT-003 协议保持一致
  - 本地端到端测试通过
- **依赖**: PLAT-007 ✅, PLAT-008 ✅

---

#### AGENT-021: Mac/Linux 安装脚本最终测试

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 1h
- **截止时间**: 4/23
- **交付物**:
  - 在干净 Mac VM / Linux VM 上测试域名版 `install.sh`
  - 确认 OpenClaw 安装 + Skill 预装 + Exporter 推送全链路通过
- **依赖**: AGENT-019 ✅

---

#### COORD-001: 与罗确认活动边界和最终方案

- **状态**: 📥 待领取
- **负责人**: @zhang-chenyang-claw
- **预计 AI 工时**: 1h
- **截止时间**: 4/21 今晚
- **交付物**:
  - 会议纪要（活动目的、支持边界、我们负责范围）
  - 最终实施方案确认
  - 风险清单 + 应急预案
- **阻塞影响**: 阻塞方案冻结和任务分配

---

### 🟡 P1 - 高优先级（4月23日完成）

#### PLAT-009: 飞书告警接入

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 1h
- **截止时间**: 4/23
- **交付物**:
  - Alertmanager 飞书 webhook 配置
  - 告警模板：用户离线 / 推送异常
  - 飞书机器人测试消息发送成功
- **依赖**: PLAT-007 ✅
- **备注 / 待确认**:
  - ⚠️ 飞书机器人 token 谁提供？建议由活动组织方或我们自己创建

---

#### PLAT-010: 40 用户并发监控验证

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 2h
- **截止时间**: 4/23
- **交付物**:
  - 4090 上模拟 40 个 tenant 并发推送
  - Grafana Dashboard 可显示 40 个用户在线
  - Pushgateway 无丢包、无 OOM
- **依赖**: PLAT-007 ✅, PLAT-009 ✅
- **备注 / 待确认**:
  - ⚠️ 4090 上测试 vs 云服务器测试？建议两边都跑一遍

---

#### AGENT-022: 专属 Skills 链接生成机制

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 1.5h
- **截止时间**: 4/23
- **交付物**:
  - Skill bundle 打包脚本（zip 格式）
  - URL 规则：`opc200.meerkatai.cn/skills/{topic-id}/bundle.zip`
  - 按课题分组，每组一个 skill bundle（减少组合复杂度）
  - 现场大屏幕展示各组下载链接
- **依赖**: PLAT-008 ✅
- **备注 / 待确认**:
  - ⚠️ 预计多少个课题？每个课题一个 skill bundle？
  - ⚠️ 用户改进/上传 skill 的流程是什么？（现场如何收集和分发）

---

#### AGENT-023: 停用脚本 `stop.sh`

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 30min
- **截止时间**: 4/23
- **交付物**:
  - `agent/scripts/stop.sh`（停止 agent 服务，不卸载）
  - `agent/scripts/stop.ps1`（Windows 对应版本）
  - 支持优雅停止 exporter 推送和进程
- **依赖**: AGENT-002 ✅, AGENT-003 ✅

---

#### SKILL-001: 与圣琪确认 Skill 方案

- **状态**: 📥 待领取
- **负责人**: @zhang-chenyang-claw
- **预计 AI 工时**: 1h
- **截止时间**: 4/22
- **交付物**:
  - Skill 清单（课题对应关系）
  - Skill 分配方案
  - 用户上传 skill 的收集和审核流程
- **依赖**: COORD-001 ✅
- **备注 / 待确认**:
  - ⚠️ Skill 内容是否已就绪？是否需要现场前预装测试？

---

### 🟢 P2 - 现场支持（4月24日当天）

#### LIVE-001: 大屏幕显示统一安装脚本链接

- **状态**: 📥 待领取
- **负责人**: @li-ming / @zhang-yao-claw
- **预计 AI 工时**: 30min
- **交付物**:
  - PPT / 网页：`opc200.meerkatai.cn/install`
  - 显示 Windows 和 Mac 安装命令
  - 显示各组专属 Skill 下载链接

---

#### LIVE-002: 现场技术支持

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw + @zhang-chenyang-claw
- **预计 AI 工时**: 全天
- **交付物**:
  - 现场答疑、安装问题处理
  - 安装失败用户的诊断和修复

---

#### LIVE-003: 专属 Skills 分发

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 1h（现场执行）
- **交付物**:
  - 按用户/课题分配 skills 下载链接
  - 现场引导用户安装 skill

---

#### LIVE-004: API KEY 分发

- **状态**: 📥 待领取
- **负责人**: @zhang-yao-claw
- **预计 AI 工时**: 30min
- **交付物**:
  - Kimi Key 分配方案（预分配 or 现场发放）
- **备注 / 待确认**:
  - ⚠️ **建议优先让用户用自己的 Kimi Key**（减少我们 key 的限流和泄露风险）
  - ⚠️ 如必须使用统一 key，准备 3-5 个 key 按桌/组分配

---

### ⚪ P3 - 备选方案（提前准备，现场应急）

#### FALLBACK-001: Kimi Claw 云端账号准备

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 30min
- **交付物**:
  - 准备 5-10 个 Kimi Claw 账号
  - 预配置好 OpenClaw 环境和基础 Skills
- **触发条件**: 用户没带电脑

---

#### FALLBACK-002: 4090 云端 Claw 配置

- **状态**: 📥 待领取
- **负责人**: @li-ming
- **预计 AI 工时**: 1h
- **交付物**:
  - 4090 上部署 OpenClaw，限制资源（防止挤占）
  - 提供 Web 访问入口
- **触发条件**: 用户电脑性能不足
- **备注 / 待确认**:
  - ⚠️ 备选方案预算是否已批准？（Kimi Claw 账号 + 4090 资源占用）

---

## 🗺️ 路线图：近期目标 → 远期最终目标

### Phase 1：MVP 验证（AI Coding 3天）

**时间**: Day 1-3（4月10-12日）  
**目标**: 平台可接收指标，用户可一键安装，5用户在线测试  
**关键交付**:

- ✅ 平台侧：Prometheus + Pushgateway + Grafana + Alertmanager
- ✅ 用户侧：Win/Mac/Linux 安装脚本 + exporter 推送
- ✅ 端到端：1用户完整链路 + 5用户灰度测试

### Phase 2：核心功能完善（AI Coding 5天）

**时间**: Day 4-8（4月13-17日）  
**目标**: Agent 完整功能可用，平台可管理版本  
**关键交付**:

- ✅ Agent：import 调整、自修复机制、版本更新客户端
- ✅ Platform：version-control 服务、灰度发布
- ✅ 测试：完整单元测试 + 集成测试
- ✅ 试点：10-20 个真实用户测试

### Phase 3：规模验证（AI Coding 7天）

**时间**: Day 9-15（4月18-24日）  
**目标**: 支持 100 用户同时在线，平台稳定运行  
**关键交付**:

- ✅ 性能优化：Pushgateway 水平扩展、Grafana 查询优化
- ✅ 安全加固：HTTPS 强制、签名验证、审计日志
- ✅ 批量部署：50 用户上线

### Phase 4：全面上线（AI Coding 10天）

**时间**: Day 16-25（4月25日-5月4日）  
**目标**: 200 用户全部上线，SLA 99.9%  
**关键交付**:

- ✅ 全量部署：200 用户分批次上线
- ✅ 运维体系：7×24 值班、应急预案、故障演练
- ✅ 监控大盘：实时业务指标、用户增长、健康度

### Phase 5：持续优化（长期）

**时间**: 5月后  
**目标**: 产品迭代、新功能开发  
**关键方向**:

- 🔮 AI 智能诊断：自动分析用户问题并修复
- 🔮 预测性维护：提前发现潜在故障
- 🔮 个性化推荐：基于用户数据的智能建议
- 🔮 生态扩展：支持更多 Skills、第三方集成

---

## 📝 任务变更日志

### 2026-04-21（晚）

- **新增**: Phase 1.5 — 4.24 活动冲刺任务板（紧急插入，冻结时间 4/23）
  - 6 个 P0 阻塞级任务（INFRA-001/002, PLAT-007/008, AGENT-019/020/021, COORD-001）
  - 5 个 P1 高优先级任务（PLAT-009/010, AGENT-022/023, SKILL-001）
  - 4 个 P2 现场支持任务（LIVE-001~004）
  - 2 个 P3 备选方案（FALLBACK-001/002）
  - 资源站点目录结构：`opc200.meerkatai.cn/{install,resources/{skills,custom-skills},metrics}/`
  - 关键待确认事项：域名审批、服务器规格、Kimi Key 方案、课题数量、飞书机器人 token、备选预算
  - 建议 API KEY 方案：优先让用户用自己的 Kimi Key，减少限流和泄露风险
- **调整**: 原 Phase 2 任务顺延（AGENT-010~018 仍 📥 待领取）
- **更新**: 任务统计表增加 Phase 1.5 列

### 2026-04-21

- **对齐**: `PLAT-001`、`PLAT-002` 与 [Phase 1 归档](archive/phase-1-mvp.md) 一致，标记为 ✅ 已完成。
- **Roadmap**: `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md` — §2.8 增补 Linux `sudo` 下 `~/.openclaw` / `OPENCLAW_STATE_HOME` / `_openclaw_run`（§2.9.2 Bootstrap 入口勾选）。
- **安装脚本**: `agent/scripts/install.sh` — `sudo` 安装时 OpenClaw 默认使用调用用户家目录，非 `/root`；网关 part2 / 8b / onboard / 轻预装目录与之一致。

### 2026-04-20

- **文档**: 对照 `install.sh` / `opc200-install.sh` / `uninstall.sh` 与 Windows 交付物，`agent/README.md`「用户使用」补全 Linux/macOS 第二步（交互 / 静默 custom-api-key）与第三步卸载路径；开发小节修正 `sudo env … ./install.sh` 续行示例。

### 2026-04-17

- **推进**: AGENT-009 **M3** — `opc200-install.sh`、`release-opc-agent.yml` 附带；`INSTALL_SCRIPT_SPEC` §9、`README`；`test_agent009_bootstrap_bash.py`
- **推进**: AGENT-009（Windows）— `opc200-install.ps1`、`build-agent-bundle.sh`、`pack-agent-release.ps1`、`release-opc-agent.yml`；`install.ps1` 与根 `VERSION` 对齐 `AGENT_VERSION=2.5.1`；`INSTALL_SCRIPT_SPEC` §9、`README`、`PREINSTALLED_LOBSTER_ROADMAP` §2.9；`test_agent009_release_bundle.py`

### 2026-04-16

- **推进**（Windows 安装脚本阶段性收束）：`install.ps1` **放开 `Main` 全注释**，默认跑满第一～三部分；轻预装增加 **`openclaw config set tools.profile full`**；网关段 **RPC 优先**（`--require-rpc`）避免重复 `gateway install`；`uninstall.ps1` 已对齐 **`-KeepOpenClaw`** 与卸载顺序。`agent/README.md`、`docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md`、相关单测已同步。
- **重构**: `install.ps1`（AGENT-007/002 对齐）：安装开头不再采集平台三件套；OpenClaw 顺序为官方安装 → PATH 同步 → onboard → 轻预装 → 网关配置（现以 RPC 探测为先，非固定 `doctor` 首跑）；OPC200 Agent 前再采平台与租户，平台 ApiKey 复用 OpenClaw 模型密钥或 `-OPC200ApiKey` / `OPC200_API_KEY`；移除 `-LocalBinary`/`-UseBinary` 与 Release exe 下载，仅 venv+pip；`agent/README.md` + `test_agent002_install.py` 同步
- **完成**: AGENT-008 OpenClaw 开箱即用配置自动化
  - `agent/scripts/install.ps1`：可选 `-OpenClawOnboard` / `-SkipOpenClawOnboard` / `-OpenClawAuthChoice`；`OPENCLAW_ONBOARD=1` 时执行 `openclaw onboard --non-interactive`；交互 `SecureString`；`OPENCLAW_ONBOARD_STRICT`（onboard 超时/失败等；网关 HTTP 由后续网关段负责，与 Linux `install.sh` 对齐）
  - `agent/scripts/install.sh`：`--openclaw-onboard` / `--skip-openclaw-onboard`；子 shell 注入密钥；GNU `timeout` 包裹 onboard；**用户级 systemd** 预检、`OPENCLAW_ONBOARD_SKIP_DAEMON`、onboard 失败日志识别后中止（见 `INSTALL_SCRIPT_SPEC` §9.1）
  - 单测：`agent/src/tests/test_agent008_openclaw_onboard_install.py`；Roadmap §2.8 已勾选

### 2026-04-15

- **规划**: 将“OpenClaw 开箱即用配置自动化”纳入 P1，落位为 AGENT-008，并顺延后续任务编号（AGENT-009~017）
  - 目标：安装阶段完成 OpenClaw 最小可用配置采集与落地，避免用户手动 `openclaw dashboard/setup`
  - 方案：交互问答 + 静默参数；优先官方 CLI 非引导式配置，失败 fallback 到配置文件写入；完成后做可用性验证
- **推进**: AGENT-007 完成里程碑 M3（`agent_health` 语义对齐 OpenClaw 网关）
  - `agent/src/exporter/collector.py`：`agent_health` 默认 HTTP GET `OPENCLAW_GATEWAY_HEALTH_URL`（默认 `http://127.0.0.1:18789/health`），支持 `OPENCLAW_GATEWAY_HEALTH_PROBE=0` 跳过网关探测
  - `docs/METRICS_PROTOCOL.md`、`docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md` §2.7 已同步；`test_agent004_exporter.py` 已扩展并通过
- **同步**: AGENT-007 卸载脚本体验对齐（Windows + Linux）
  - 交互式卸载新增“是否同时卸载 OpenClaw”确认；保留 `-PurgeOpenClaw` 非交互行为
  - OpenClaw 卸载阶段增加进度提示，并保留“CLI 全局包需自行 npm/pnpm 移除”提醒
- **推进**: AGENT-007 预装小龙虾路线图第一期 §1.1「核心演示流程」已走通并完成勾选（见 `docs/architecture/PREINSTALLED_LOBSTER_ROADMAP.md`）
- **修复**: AGENT-007 Linux 安装路径补齐 OpenClaw 的 Node v22+ 前置保障
  - `install.sh` 新增 `step_prepare_node_runtime`，在调用 OpenClaw 官方安装器前检测 `node -v`
  - Linux 下若 Node 不存在或主版本 < 22，则从 `nodejs.org` 官方 `latest-v22.x` 下载对应架构 tar.xz 并安装到 `/usr/local`
  - 安装步骤提示由 9 步调整为 10 步；`test_agent003_install.py` 已更新并通过（77 passed）
- **修复**: AGENT-007 Windows 安装路径上 OpenClaw 官方脚本要求 Node v22+，而 winget 对已装旧版常无法升级、且当前 shell 未刷新 PATH
  - `install.ps1` 在调用官方安装器前增加 `Ensure-OpenClawNodeRuntime`：合并 Machine/User `Path`、可选 winget、失败则从 `nodejs.org` 拉取 win-x64 MSI 静默安装
  - 安装步骤提示由 9 步调整为 10 步；`test_agent002_install.py` 已更新并通过

### 2026-04-14

- **推进**: AGENT-007 完成里程碑 M1（官方渠道安装 latest）
  - `install.ps1` 默认官方入口调整为 `https://openclaw.ai/install.ps1`
  - `install.sh` 默认官方入口调整为 `https://openclaw.ai/install.sh`
  - 增加 https 与官方域名白名单校验，非 latest 渠道回退 latest
  - 安装脚本测试通过：`test_agent002_install.py` + `test_agent003_install.py`（122 passed）
- **推进**: AGENT-007 完成里程碑 M2（轻预装层）
  - 新增轻预装步骤：skills 安装（失败仅告警继续）+ 文档模板投放
  - 文档策略：`SOUL.md`/`IDENTITY.md`/`AGENTS.md` 已存在时写入对应 `.new`
  - 模板来源：改为独立模板目录 `agent/scripts/openclaw-templates/`
  - 安装脚本测试更新并通过：`test_agent002_install.py` + `test_agent003_install.py`（128 passed）

### 2026-04-12 (深夜)

- **重写**: AGENT-003 Mac/Linux 安装/卸载脚本（v2）
  - `agent/scripts/install.sh` — 7 步安装，支持 macOS(launchd) + Linux(systemd)
  - `agent/scripts/uninstall.sh` — 卸载，支持 --keep-data
  - 61 个规范一致性测试通过
  - 包管理器检测并提示（brew/apt/yum/dnf/pacman）
  - 补全 `agent/README.md` Mac/Linux 安装说明

### 2026-04-12 (晚)

- **重写**: AGENT-002 Windows 安装/卸载脚本（v2）
  - 清理 `agent/scripts/` 旧文件（5 个），全部重写
  - 严格按 AGENT-001 SPEC 实现 7 步安装流程 + 回滚
  - 49 个规范一致性测试通过
  - 提交: `d2c84fb`

### 2026-04-12

- **重写**: AGENT-004 + AGENT-005 全部重写（v2）
  - 清理 `agent/src/exporter/` 旧代码（collector.py / pusher.py / test_collector.py / README.md）
  - 清理 `tests/agent/` 遗留失效测试
  - AGENT-004: 基于 psutil 重写采集器，修复接口不匹配、`_check_health` 重复采集、`/proc/stat` 不准等问题
  - AGENT-005: 重写推送器，与 AGENT-004 v2 接口完全对齐
  - 测试迁移到 `agent/src/tests/`（30 tests passing）
  - 提交: `cb0c61d`（AGENT-004）、`d73af7a`（AGENT-005）

### 2026-04-10 (晚上)

- **更新**: @zhang-chenyang-claw 完成 AGENT-004 exporter 指标采集器（v1，已被 v2 替代）
  - ~~实现跨平台 CPU/内存/磁盘采集 (Linux/macOS/Windows)~~
  - ~~15个单元测试全部通过~~
- **状态变更**: AGENT-004 ✅ 已完成，解除 AGENT-005 阻塞

### 2026-04-10 (晚)

- **更新**: PLAT-004, PLAT-005 标记为已完成（同事测试验证通过）
  - Grafana 截图显示 3个租户（opc-001/002/003）数据正常
  - 多租户隔离功能验证通过
  - 监控面板功能验证通过
- **进度**: Phase 1 平台侧任务 5/6 完成，仅剩 PLAT-006

### 2026-04-10 (下午)

- **更新**: @zhang-yao-claw 更新负责模块状态
  - AGENT-001: 标记为 ✅ 已完成（`docs/INSTALL_SCRIPT_SPEC.md` 已提交）
  - AGENT-002: 标记为 ✅ MVP 已完成（`install.ps1`, `uninstall.ps1`, `TEST_PLAN.md`）
- **同步**: 拉取远程更新，包含 PLAT-004（多租户隔离）
- **阻塞解除**: PLAT-003 协议定义完成，AGENT-005 阻塞已解除
- **新增**: 每2小时自动检查分支更新定时任务
- **完成**: AGENT-006 端到端联调，2 租户链路验证通过（collector -> pusher -> Pushgateway -> Prometheus）
- **完成**: AGENT-005 exporter 指标推送，产出 `agent/src/exporter/pusher.py`
- **完成**: AGENT-004 exporter 指标采集，产出 `agent/src/exporter/collector.py`
- **完成**: AGENT-001 安装脚本方案，产出 `docs/INSTALL_SCRIPT_SPEC.md`

### 2026-04-09

- **重构**: 重新按 AI Coding 节奏规划任务（3天 MVP 冲刺）
- **新增**: Phase 1 核心任务（PLAT-001~006, AGENT-001~006）
- **新增**: 路线图：Phase 1-5 完整规划
- **后移**: 原 AGENT-007~011 到 Phase 2/3

---

## 👥 Agent 分工表

| Agent | 主要职责 | 当前任务 | 进行中 |
|-------|----------|----------|--------|
| @fairy-kimi | 平台侧开发、架构设计 | PLAT-001~006 | - |
| @zhang-yao-claw | 用户侧 Windows 开发 | AGENT-001, AGENT-002, AGENT-005, AGENT-006 | - |
| @zhang-chenyang-claw | 用户侧 Mac/Linux 开发 | AGENT-001, AGENT-003, AGENT-004, AGENT-006 | - |

---

## 🚧 阻塞问题

| 问题 ID | 描述 | 阻塞任务 | 需要协助 | 状态 |
|---------|------|----------|----------|------|
| BLOCK-001 | ~~PLAT-003 指标协议未定义~~ | ~~AGENT-005~~ | @fairy-kimi | ✅ 已解除（2026-04-10） |
| BLOCK-002 | ~~AGENT-005 离线缓存策略待确认~~ | ~~AGENT-005~~ | @zhang-yao-claw | ✅ 已解除（2026-04-10，策略已确认并实现） |

---

## ✅ 最近完成任务

- **AGENT-007/008 补充**（2026-04-21）：Linux `install.sh` — `sudo` 下 OpenClaw 状态目录对齐 `~/.openclaw`（`SUDO_USER`）、`OPENCLAW_STATE_HOME`、统一 `HOME` 执行 CLI（与 Roadmap §2.8 一致）
- **docs**: `agent/README.md` 用户使用（Linux/macOS 引导安装与卸载说明对齐 Windows）（2026-04-20）
- **AGENT-008**: OpenClaw 非交互 onboard；Linux 用户级 systemd / `SKIP_DAEMON` / 第 8–9 步网关与 **AGENT-008** 文档持续对齐（2026-04-16 起，2026-04-22 SPEC/README 统一）
- **AGENT-007**: OpenClaw 官方安装 + 轻预装 + `agent_health` 网关探测打通（2026-04-15）
- **AGENT-003**: v2 重写 Mac/Linux 安装脚本（2026-04-12）
- **AGENT-002**: v2 重写 Windows 安装脚本（2026-04-12）
- **AGENT-005**: v2 重写 exporter 指标推送（2026-04-12）
- **AGENT-004**: v2 重写 exporter 指标采集（2026-04-12）
- **AGENT-006**: 端到端联调验证通过（2026-04-10）
- **AGENT-001**: 设计安装脚本方案（2026-04-10）

---

## 📊 任务统计

| 状态 | Phase 1 | Phase 1.5 | Phase 2 | Phase 3 | Backlog |
|------|---------|-----------|---------|---------|---------|
| 📥 待领取 | 0 | 16 | 4 | 3 | 2 |
| 🏃 进行中 | 0 | 0 | 1 | 0 | 0 |
| 👀 审核中 | 0 | 0 | 0 | 0 | 0 |
| ✅ 已完成 | 12 | 0 | 2 | 0 | 0 |
| ⏸️ 阻塞中 | 0 | 0 | 0 | 0 | 0 |

---

## 💬 任务讨论区

### Phase 1 总讨论

> @fairy-kimi: Day 1 中午我们同步协议文档，下午用户侧就可以开始 exporter 推送实现。
>
> @zhang-yao-claw: 收到，我们先做安装脚本方案，不依赖协议。

### PLAT-003 协议定义讨论

> @fairy-kimi: 协议草案如下，请确认：
>
> - 推送地址: `POST https://platform.opc200.co/metrics/job/{tenant_id}`
> - 必传 labels: `tenant_id`, `agent_version`, `os`
> - 标准指标: `agent_health` (gauge), `cpu_usage` (gauge), `memory_usage` (gauge), `disk_usage` (gauge)
>
> @zhang-yao-claw: 确认，没问题。
> @zhang-chenyang-claw: 确认。

---

**任务板维护**: @fairy-kimi  
**更新频率**: 每任务完成后立即更新，每日 Standup 同步
