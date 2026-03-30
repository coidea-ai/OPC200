# OPC200 7×24 仿真测试 - 快速指南

> 150本地 + 50云端 OpenClaw 实例全天候压力测试

---

## 🚀 快速开始 (5分钟)

### 1. 快速测试 (20实例, 1小时)

```bash
./scripts/simulation-quickstart.sh
```

### 2. 全量测试 (200实例, 7天)

```bash
./scripts/simulation-quickstart.sh --mode full
```

### 3. 自定义配置

```bash
./scripts/simulation-quickstart.sh --local 50 --cloud 20 --duration 4
```

---

## 📊 架构概览

```
                    ┌──────────────────┐
                    │  控制中心        │
                    │  Load Generator  │
                    └────────┬─────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ 本地实例池    │    │  云端实例池   │    │  观测系统    │
│  (150个)     │    │   (50个)     │    │ Prometheus  │
│ Docker       │    │ Kubernetes   │    │ Grafana     │
└──────────────┘    └──────────────┘    └──────────────┘
```

---

## 🎯 测试能力

| 能力 | 说明 |
|------|------|
| **规模** | 200实例并发 (150本地 + 50云端) |
| **时长** | 7×24小时不间断 |
| **负载** | 模拟真实用户行为 (轻度/普通/重度/商业) |
| **混沌** | 自动注入故障 (网络/CPU/内存/重启) |
| **优化** | AI驱动的自动性能优化 |

---

## 📈 监控指标

- **系统**: CPU、内存、磁盘IO、网络延迟
- **业务**: 技能调用数、响应时间、错误率
- **质量**: 数据一致性、故障恢复时间

---

## 🔧 自动优化

系统会自动：

1. **检测问题** → 高延迟、高错误率、内存泄漏
2. **生成建议** → 缓存、熔断、资源调整
3. **应用优化** → 低风险优化自动执行
4. **创建工单** → 复杂优化生成GitHub Issue

---

## 📁 文件说明

| 文件 | 说明 |
|------|------|
| `docs/SIMULATION_ARCHITECTURE.md` | 完整架构文档 (34KB) |
| `scripts/simulation-quickstart.sh` | 一键启动脚本 |
| `simulation/` | 运行时生成的配置和日志 |

---

## 🎮 常用命令

```bash
# 查看实例状态
docker-compose ps

# 查看实时监控
curl http://localhost:9090/api/v1/query?query=opc_skill_invocations_total

# 查看优化报告
ls -la simulation/reports/

# 停止测试
./scripts/simulation-quickstart.sh --stop
```

---

## 📚 详细文档

- [完整架构文档](docs/SIMULATION_ARCHITECTURE.md)
- [TDD测试指南](docs/TDD_GUIDE.md)
- [全量测试策略](docs/FULL_TEST_STRATEGY.md)

---

*最后更新: 2026-03-31*
