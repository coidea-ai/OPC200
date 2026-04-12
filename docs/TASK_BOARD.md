# OPC200 多 Agent 协同任务板

> 多 Agent 协同工作指南与任务追踪

**项目**: OPC200 Push 架构改造  
**分支**: `feat/push-architecture`  
**最后更新**: 2026-04-12（AGENT-002/004/005 v2 重写完成）

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

#### PLAT-001: 搭建 Prometheus + Pushgateway 本地环境
- **状态**: 📥 待领取
- **负责人**: @fairy-kimi
- **协作方**: 无
- **预计 AI 工时**: 30min
- **截止**: Day 1 上午
- **产出**:
  - `platform/docker-compose.yml`（Prometheus + Pushgateway 基础版）
  - 本地可运行 `docker-compose up`
  - Pushgateway 可接收测试推送
- **描述**:
  使用标准镜像快速搭建，配置基础 scraping。

---

#### PLAT-002: 配置 Grafana 基础 Dashboard
- **状态**: 📥 待领取
- **负责人**: @fairy-kimi
- **协作方**: 无
- **预计 AI 工时**: 1h
- **截止**: Day 1 上午
- **产出**:
  - `platform/grafana/provisioning/dashboards/` 基础面板
  - 可查看 Pushgateway 接收的原始指标
- **依赖**: PLAT-001

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
- **状态**: 📥 待领取
- **负责人**: @fairy-kimi
- **协作方**: 无
- **预计 AI 工时**: 1.5h
- **截止**: Day 3 上午
- **产出**:
  - `platform/alertmanager/alertmanager.yml`
  - 告警规则: 用户离线超过 5 分钟触发
  - 通知渠道: 飞书 webhook（后续可扩展邮件/短信）
- **依赖**: PLAT-001

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
  - ✅ 配置项: `PLATFORM_URL`, `CUSTOMER_ID`, `API_KEY`
  - ✅ 数据目录: `~/.opc200/`
  - ✅ 错误码定义、安全设计、目录结构
- **提交**: `4111c8b` - docs: add Windows install script spec and project setup docs

---

#### AGENT-002: 实现 Windows 安装脚本（PowerShell）
- **状态**: ✅ 已完成（v2 重写）
- **负责人**: @zhang-yao-claw
- **协作方**: 无
- **预计 AI 工时**: 2h
- **实际完成**: Day 3（2026-04-12 重写）
- **产出**:
  - ✅ `agent/scripts/install.ps1` — 7 步安装流程，严格按 AGENT-001 SPEC
  - ✅ `agent/scripts/uninstall.ps1` — 3 步卸载，支持 KeepData
  - ✅ `agent/src/tests/test_agent002_install.py` — 49 个规范一致性测试
  - ✅ 目录结构 `~/.opc200/`（bin/config/data/journal/exporter/logs）
  - ✅ SHA256 校验、端口占用检测、磁盘空间检查
  - ✅ 错误码 E001-E005（按 SPEC §6.1）
  - ✅ 失败自动回滚（按 SPEC §6.2）
  - ✅ .env ACL 权限受限存储 API Key
- **测试**: 49/49 规范一致性测试通过
- **提交**: `d2c84fb`（v2），~~`7515747`~~（v1 已废弃）
- **v2 改进**:
  - 安装目录从 `$LOCALAPPDATA\OPC200` 改为 `~/.opc200/`（与 SPEC 对齐）
  - 新增 `bin/` 子目录、SHA256 校验、端口检测、回滚机制
  - 删除旧 TEST_PLAN.md / LOCAL_TEST_GUIDE.md / run-local-tests.sh
- **依赖**: AGENT-001 ✅

---

#### AGENT-003: 实现 Mac/Linux 安装脚本（Bash）
- **状态**: 📥 待领取
- **负责人**: @zhang-chenyang-claw
- **协作方**: 无
- **预计 AI 工时**: 1.5h
- **截止**: Day 3 下午
- **产出**:
  - `agent/scripts/install.sh`
  - 支持 macOS 和主流 Linux 发行版
  - 使用 systemd 管理服务（Linux）或 launchd（macOS）
- **依赖**: AGENT-001

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

#### AGENT-007: 调整 Python import 路径
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 1h
- **描述**: 批量替换 `from src.xxx` → 新包名

#### AGENT-008: 实现 selfhealer/l1_local_fix.py
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 3h
- **描述**: L1 本地自动修复机制

#### AGENT-009: 实现 updater/update_client.py
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 4h
- **描述**: 版本更新客户端

#### AGENT-010: 创建 platform/docker-compose.yml 完整版
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 1h
- **描述**: 包含 version-control 服务

---

## 🟢 P2 - 中优先级任务（Phase 3）

#### AGENT-011: 创建 shared/proto/ 通信协议
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 2h

#### AGENT-012: 实现 version-control 版本管理服务
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 6h

#### AGENT-013: 迁移测试文件到 tests/agent/ 和 tests/platform/
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 1.5h

---

## ⚪ P3 - 低优先级任务（Backlog）

#### AGENT-014: 删除旧目录 src/, skills/, config/
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 30min

#### AGENT-015: 完善 CI/CD 脚本适配新结构
- **状态**: 📥 待领取
- **负责人**: 未分配
- **预计 AI 工时**: 2h

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

- **AGENT-002**: v2 重写 Windows 安装脚本（2026-04-12）
- **AGENT-005**: v2 重写 exporter 指标推送（2026-04-12）
- **AGENT-004**: v2 重写 exporter 指标采集（2026-04-12）
- **AGENT-006**: 端到端联调验证通过（2026-04-10）
- **AGENT-001**: 设计安装脚本方案（2026-04-10）

---

## 📊 任务统计

| 状态 | Phase 1 | Phase 2 | Phase 3 | Backlog |
|------|---------|---------|---------|---------|
| 📥 待领取 | 1 | 4 | 3 | 2 |
| 🏃 进行中 | 0 | 0 | 0 | 0 |
| 👀 审核中 | 0 | 0 | 0 | 0 |
| ✅ 已完成 | 11 | 0 | 0 | 0 |
| ⏸️ 阻塞中 | 0 | 0 | 0 | 0 |

---

## 💬 任务讨论区

### Phase 1 总讨论

> @fairy-kimi: Day 1 中午我们同步协议文档，下午用户侧就可以开始 exporter 推送实现。
> 
> @zhang-yao-claw: 收到，我们先做安装脚本方案，不依赖协议。

### PLAT-003 协议定义讨论

> @fairy-kimi: 协议草案如下，请确认：
> - 推送地址: `POST https://platform.opc200.co/metrics/job/{tenant_id}`
> - 必传 labels: `tenant_id`, `agent_version`, `os`
> - 标准指标: `agent_health` (gauge), `cpu_usage` (gauge), `memory_usage` (gauge), `disk_usage` (gauge)
> 
> @zhang-yao-claw: 确认，没问题。
> @zhang-chenyang-claw: 确认。

---

**任务板维护**: @fairy-kimi  
**更新频率**: 每任务完成后立即更新，每日 Standup 同步
