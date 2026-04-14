# OPC200 变更日志

## [2.1.0] - 2026-04-14

### 新增
- PLAT-006: Alertmanager 离线告警链路打通，邮件通知测试通过 (@kimi-claw)
- `platform/tests/test_plat006_alertmanager.py`: 告警集成测试脚本

### 修复
- `platform/scripts/mock_agent_data.py`: POST → PUT，解决 Pushgateway HTTP 400
- `platform/prometheus/rules/opc200.yml`: 修正告警规则指标名 (pushgateway_metrics_last_timestamp_seconds → push_time_seconds)
- `platform/alertmanager/alertmanager.yml`: 更新 QQ 邮箱授权码，移除失效飞书 webhook

## [2.0.0] - 2026-04-12

### 重构
- AGENT-002 v2: Windows 安装脚本重写，严格按 SPEC 实现 (@zhang-yao-claw)
- AGENT-003 v2: Mac/Linux 安装脚本重写，支持 launchd/systemd (@zhang-yao-claw)
- AGENT-004 v2: exporter 采集器改用 psutil，修复精度和接口问题 (@zhang-chenyang-claw)
- AGENT-005 v2: exporter 推送器对齐 v2 接口 (@zhang-yao-claw)

### 测试
- 新增 110+ 规范一致性测试和单元测试

### 删除
- 清理 5 个废弃 v1 文件 (TEST_PLAN.md, LOCAL_TEST_GUIDE.md 等)

## [1.0.0] - 2026-04-10

### 新增 (Phase 1 MVP 启动)
- PLAT-001: Prometheus + Pushgateway 基础设施 (@fairy-kimi)
- PLAT-002: Grafana 基础 Dashboard (@fairy-kimi)
- PLAT-003: 指标推送协议定义 METRICS_PROTOCOL.md (@fairy-kimi)
- PLAT-004: 多租户数据隔离实现 (@fairy-kimi)
- PLAT-005: 多租户监控 Dashboard (@fairy-kimi)
- AGENT-001: 安装脚本设计规范 (@zhang-yao-claw)
- AGENT-006: 端到端联调验证通过

### 特性
- 支持 3 租户同时在线 (opc-001/002/003)
- Grafana 实时显示租户健康状态
