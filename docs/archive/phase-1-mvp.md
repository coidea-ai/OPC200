# Phase 1 MVP 归档 (2026-04-10 ~ 2026-04-14)

## 目标回顾
- **原定目标**: 平台侧可接收用户侧指标，用户侧可一键安装，5 用户同时在线测试
- **实际达成**: ✅ 全部达成，12 个任务完成，告警链路打通

## 关键里程碑

| 日期 | 事件 | 版本 |
|------|------|------|
| 2026-04-10 | Phase 1 启动，基础设施搭建完成 | v1.0.0 |
| 2026-04-12 | AGENT-002~005 v2 重写 | v2.0.0 |
| 2026-04-14 | PLAT-006 告警链路打通 | v2.1.0 |

## 完成的任务

### 平台侧 (@fairy-kimi / @kimi-claw)

| 任务 | 负责人 | 关键交付 | 验证方式 |
|------|--------|---------|---------|
| PLAT-001 | @fairy-kimi | `platform/docker-compose.yml` (Prometheus+Pushgateway) | `docker-compose up` 成功 |
| PLAT-002 | @fairy-kimi | `platform/grafana/provisioning/` 基础面板 | Grafana 可查看原始指标 |
| PLAT-003 | @fairy-kimi | `docs/METRICS_PROTOCOL.md` 指标推送协议 | 11 个 TDD 测试通过 |
| PLAT-004 | @fairy-kimi / Remua02 | Prometheus 多租户隔离配置 | 3 租户 (opc-001/002/003) 数据隔离验证 |
| PLAT-005 | @fairy-kimi / Remua02 | Grafana "OPC200 多租户监控" Dashboard | 租户统计、健康状态明细表正常显示 |
| PLAT-006 | @kimi-claw | `platform/alertmanager/alertmanager.yml`, `platform/tests/test_plat006_alertmanager.py` | 邮件通知测试通过 ✅ |

### 用户侧 (@zhang-yao-claw / @zhang-chenyang-claw)

| 任务 | 负责人 | 关键交付 | 验证方式 |
|------|--------|---------|---------|
| AGENT-001 | @zhang-yao-claw | `docs/INSTALL_SCRIPT_SPEC.md` 安装脚本设计规范 | SPEC 评审通过 |
| AGENT-002 v2 | @zhang-yao-claw | `agent/scripts/install.ps1`, `uninstall.ps1` | 49 个规范一致性测试通过 |
| AGENT-003 v2 | @zhang-yao-claw | `agent/scripts/install.sh`, `uninstall.sh` | 61 个规范一致性测试通过 |
| AGENT-004 v2 | @zhang-chenyang-claw | `agent/src/exporter/collector.py` (psutil 版) | 16 个单元测试通过 |
| AGENT-005 v2 | @zhang-yao-claw | `agent/src/exporter/pusher.py` (缓存+退避) | 14 个单元测试通过 |
| AGENT-006 | @zhang-yao-claw + @fairy-kimi | 端到端联调验证 | 2 租户链路 (collector→pusher→Pushgateway→Prometheus) 通过 |

## 关键决策

| 决策 | 方案 | 理由 | 时间 |
|------|------|------|------|
| 监控选型 | Prometheus + Pushgateway (vs 自建) | 标准生态，少踩坑，社区成熟 | 2026-04-10 |
| 指标格式 | Prometheus text format | 与 Prometheus 生态完全兼容 | 2026-04-10 |
| 推送方式 | PUT 替换 (vs POST 追加) | 避免类型冲突，幂等安全 | 2026-04-14 |
| 离线缓存 | JSON Lines 文件，上限 500 条 | 简单可靠，恢复后分批推送 | 2026-04-10 |
| 采集实现 | psutil (vs 原生 /proc, wmic) | 跨平台统一，精度高，维护少 | 2026-04-12 |
| 安装脚本 | 严格按 AGENT-001 SPEC 7 步流程 | v1 随意实现导致返工，v2 规范后通过 | 2026-04-12 |

## 经验教训

### ✅ 做得好的
- TDD 测试先行：重构时心里有底，110+ 测试保驾护航
- 协议先行：PLAT-003 先定义 METRICS_PROTOCOL.md，各方对齐后再开发
- 协作分工明确：平台侧 vs 用户侧边界清晰，并行推进

### ❌ 踩过的坑
- **v1 没按 SPEC 做，v2 全重写，浪费 1 天**
  - AGENT-002 v1: 安装目录用 `$LOCALAPPDATA` 而非 `~/.opc200/`
  - AGENT-004 v1: 用 `/proc/stat` 单次读取不准确，wmic 已废弃
  - 教训：SPEC 定稿后严格遵守，减少返工

## 废弃记录

| 旧版本 | 新版本 | 废弃原因 |
|--------|--------|---------|
| ~~AGENT-002 v1~~ (7515747) | v2 (d2c84fb) | 不符合 SPEC 目录结构 |
| ~~AGENT-004 v1~~ (62cdfa8) | v2 (cb0c61d) | 采集精度不足，接口不兼容 |

## 产出物清单

### 文档
- `docs/METRICS_PROTOCOL.md` — 指标推送协议
- `docs/INSTALL_SCRIPT_SPEC.md` — 安装脚本设计规范

### 平台侧代码
- `platform/docker-compose.yml`
- `platform/prometheus/prometheus.yml`
- `platform/prometheus/rules/opc200.yml`
- `platform/alertmanager/alertmanager.yml`
- `platform/grafana/provisioning/`
- `platform/scripts/mock_agent_data.py`
- `platform/tests/test_plat006_alertmanager.py`

### 用户侧代码
- `agent/scripts/install.ps1`
- `agent/scripts/uninstall.ps1`
- `agent/scripts/install.sh`
- `agent/scripts/uninstall.sh`
- `agent/src/exporter/collector.py`
- `agent/src/exporter/pusher.py`
- `agent/src/tests/` (110+ 单元测试)

## 阻塞及解决

| 阻塞 ID | 问题 | 阻塞任务 | 解决方案 | 时间 |
|---------|------|---------|---------|------|
| BLOCK-001 | 指标协议未定义 | AGENT-005 | 发布 METRICS_PROTOCOL.md | 2026-04-10 ✅ |
| BLOCK-002 | 离线缓存策略待确认 | AGENT-005 | 确认：JSON Lines，500条上限，24h丢弃 | 2026-04-10 ✅ |
| BLOCK-003 | Pushgateway HTTP 400 | mock_agent_data.py | POST → PUT，清理脏数据 | 2026-04-14 ✅ |

## 测试统计

| 测试类型 | 数量 | 状态 |
|---------|------|------|
| PLAT-001 TDD | 8 | ✅ 通过 |
| PLAT-002 TDD | 8 | ✅ 通过 |
| PLAT-003 TDD | 11 | ✅ 通过 |
| AGENT-002 规范一致性 | 49 | ✅ 通过 |
| AGENT-003 规范一致性 | 61 | ✅ 通过 |
| AGENT-004 单元测试 | 16 | ✅ 通过 |
| AGENT-005 单元测试 | 14 | ✅ 通过 |
| **总计** | **167** | **✅ 全部通过** |

---

**归档时间**: 2026-04-14  
**归档人**: @kimi-claw  
**关联**: [TASK_BOARD v2.1.0](../TASK_BOARD.md) | [CHANGELOG.md](../CHANGELOG.md)
