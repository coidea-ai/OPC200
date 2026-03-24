# OPC200 自动验证流水线

> **10 阶段全自动验证流水线** — 从代码提交到生产部署的完整 CI/CD

---

## 流水线概览

```
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Phase 1 │ → │ Phase 2 │ → │ Phase 3 │ → │ Phase 4 │ → │ Phase 5 │
│ 代码安全 │   │ 静态分析 │   │ 测试矩阵 │   │ 集成测试 │   │ 性能测试 │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
     ↓
┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐
│ Phase 6 │ → │ Phase 7 │ → │ Phase 8 │ → │ Phase 9 │ → │ Phase 10│
│ 镜像构建 │   │ 灰度部署 │   │ 试点验证 │   │ 全量部署 │   │ 后验证  │
└─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘
```

---

## 阶段详情

### Phase 1: 代码质量与安全扫描 🔍

| 检查项 | 工具 | 失败策略 |
|--------|------|---------|
| Lint | flake8 | 阻塞 |
| 安全扫描 | bandit | 阻塞 |
| 依赖漏洞 | safety | 阻塞 |
| 密钥扫描 | detect-secrets | 阻塞 |

**输出**: 安全报告、代码质量评分

---

### Phase 2: 静态分析 📊

| 检查项 | 工具 | 阈值 |
|--------|------|------|
| 类型检查 | mypy | 0 errors |
| 类型覆盖率 | mypy | > 80% |

**输出**: 类型覆盖率报告

---

### Phase 3: 测试矩阵 🧪

**多版本 Python 测试**
- Python 3.10
- Python 3.11
- Python 3.12

**测试范围**
- 单元测试 (296 个)
- 安全测试 (11 个)
- 代码覆盖率 (> 80%)

**输出**: 测试报告、覆盖率报告

---

### Phase 4: 集成测试 🔗

**依赖服务**
- Qdrant 向量数据库 (Docker)

**测试范围**
- 端到端工作流
- 技能集成
- 日记流程
- 安全流程

**输出**: 集成测试报告

---

### Phase 5: 性能测试 ⚡

| 指标 | 阈值 |
|------|------|
| 日记创建 | < 100ms |
| 搜索响应 | < 500ms |
| 内存占用 | < 512MB |

**输出**: 性能基准报告

---

### Phase 6: 镜像构建 🐳

| 检查项 | 说明 |
|--------|------|
| 多架构 | AMD64 + ARM64 |
| 漏洞扫描 | Trivy |
| 镜像签名 | Cosign (可选) |
| 缓存 | GitHub Actions Cache |

**输出**: 容器镜像、漏洞报告

---

### Phase 7: Staging 部署 🚀

**触发条件**: `develop` 分支推送

**验证**
- 服务启动
- 健康检查
- E2E 测试

---

### Phase 8: Pilot 部署 🎯

**触发条件**: `main` 分支 + 手动确认

**规模**: 10 用户
- 5 云端
- 5 本地

**验证**
- 健康检查
- 指标收集
- 错误率 < 1%

---

### Phase 9: 生产部署 🏭

**触发条件**: Pilot 成功 + 手动确认

**分批次部署**
```
Batch 1: OPC-001 ~ OPC-050   (验证 5 分钟)
Batch 2: OPC-051 ~ OPC-100   (验证 5 分钟)
Batch 3: OPC-101 ~ OPC-150   (验证 5 分钟)
Batch 4: OPC-151 ~ OPC-200   (验证 5 分钟)
```

**自动回滚**: 单批次失败自动回滚

---

### Phase 10: 部署后验证 ✅

| 检查项 | 方法 |
|--------|------|
| 全量健康检查 | health-check.sh --full |
| 技能验证 | 调用 5 个核心技能 |
| 部署报告 | 自动生成 |

---

## 配套脚本

### 批量部署脚本
```bash
./scripts/deploy/batch-deploy.sh \
  --start 1 \
  --count 50 \
  --env production \
  --image ghcr.io/coidea-ai/opc200:v2.2.0
```

### 健康检查脚本
```bash
# 检查特定批次
./scripts/maintenance/health-check.sh --env production --batch 1

# 全量检查
./scripts/maintenance/health-check.sh --env production --full
```

### 回滚脚本
```bash
./scripts/recovery/rollback.sh \
  --env production \
  --batch 2 \
  --to-version v2.1.0
```

---

## 触发方式

### 自动触发
- **Push to develop**: Phases 1-7
- **Push to main**: Phases 1-7 + Pilot 部署通知
- **Daily at 02:00**: 全量验证 (Schedule)

### 手动触发
```bash
# GitHub CLI
github workflow run validation-pipeline.yml \
  -f deployment_target=pilot \
  -f skip_tests=false
```

---

## 通知与告警

| 事件 | 渠道 | 收件人 |
|------|------|--------|
| 部署成功 | Slack #opc200-deployments | 全团队 |
| 部署失败 | Slack + PagerDuty | On-call |
| 安全漏洞 | Slack + Email | 安全团队 |
| 性能退化 | Slack | 性能团队 |

---

## 质量门禁

```yaml
代码质量:
  - flake8: 0 errors
  - bandit: 0 high severity
  - mypy: 0 errors

测试:
  - 单元测试: 100% pass
  - 集成测试: 100% pass
  - 代码覆盖率: > 80%

部署:
  - Pilot 错误率: < 1%
  - 健康检查: > 95% 通过
  - 回滚时间: < 5 分钟
```

---

## 故障排查

### 常见问题

**1. 测试失败**
```bash
# 本地运行测试
pytest tests/unit -v --tb=short
```

**2. 镜像构建失败**
```bash
# 本地构建测试
docker build -t opc200:test .
```

**3. 部署失败**
```bash
# 查看部署日志
cat logs/deploy-*/report.md

# 检查特定实例
./scripts/maintenance/health-check.sh --env production --batch 1
```

**4. 回滚失败**
```bash
# 强制回滚
./scripts/recovery/rollback.sh --env production --batch 1 --force
```

---

## 相关文档

- [部署检查清单](./DEPLOYMENT_CHECKLIST_200_OPC.md)
- [部署指南](./docs/DEPLOYMENT.md)
- [安全指南](./docs/SECURITY.md)
