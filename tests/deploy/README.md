# OPC200 简化部署测试方案

## 概述

**测试类型**: Demo/验证性测试  
**测试范围**: 5 服务简化部署（不含 Tailscale）  
**测试目的**: 验证核心设计目标在资源受限环境下的可行性

---

## 设计目标对照

| 设计目标 | 完整部署 | 简化部署 | 测试覆盖 |
|---------|---------|---------|---------|
| **7×24 智能体陪伴** | ✅ Gateway + Skills | ⚠️ Gateway + 简化 Journal | 服务可用性测试 |
| **User Journal** | ✅ 完整三层记忆 | ⚠️ Qdrant 向量存储 | 数据存储测试 |
| **数据主权** | ✅ 本地存储 + 加密 | ✅ 本地 Qdrant + 卷 | 数据隔离测试 |
| **监控告警** | ✅ Prometheus + Grafana + Alertmanager | ✅ Prometheus + Grafana | 监控集成测试 |
| **混合部署** | ✅ 150本地 + 50云端 | ✅ 本地单实例 | 部署可行性测试 |
| **安全网络** | ✅ Tailscale VPN | ❌ 未部署 | 标记为已知限制 |

---

## TDD 测试设计

### 测试金字塔

```
       /\
      /  \      E2E 部署测试 (本方案)
     /----\     
    /      \    集成测试（服务间通信）
   /--------\
  /          \   单元测试（已有 315+）
 /------------\
```

### 测试分类

| 测试类 | 测试数量 | 验证目标 | P0 优先级 |
|--------|---------|---------|----------|
| `TestDeploymentInfrastructure` | 2 | Docker 环境就绪 | ✅ |
| `TestServiceAvailability` | 7 | 各服务端口/健康检查 | ✅ |
| `TestMonitoringIntegration` | 2 | Prometheus/Grafana 集成 | ✅ |
| `TestResourceConstraints` | 2 | 内存/容器数限制 | ✅ |
| `TestDataStorage` | 3 | Qdrant 向量操作 | ⚠️ |
| `TestKnownLimitations` | 2 | 记录已知限制 | ℹ️ |

**总计**: 18 个测试用例

---

## CI 适配说明

### 当前 CI 配置

现有 CI 要求:
- 代码覆盖率 ≥ 80%
- 所有单元测试通过
- Skills 测试通过

### Demo 测试的 CI 策略

**方案 1：独立 CI Job（推荐）**
```yaml
# .github/workflows/deploy-test.yml
name: Deployment Validation
on: [workflow_dispatch]  # 手动触发

jobs:
  deploy-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build minimal images
        run: docker build -f Dockerfile.light -t opc200:light .
      - name: Start services
        run: docker compose -f docker-compose.5svc.yml up -d
      - name: Run deployment tests
        run: pytest tests/deploy/test_minimal_deployment.py -v
```

**方案 2：标记为 slow 测试**
```python
@pytest.mark.slow
@pytest.mark.deploy
class TestDeploymentInfrastructure:
    ...
```

### 覆盖率处理

| 方案 | 说明 |
|------|------|
| **A. 不纳入覆盖率** | Demo 测试不计算覆盖率（推荐） |
| **B. 独立覆盖率** | 单独计算 deploy 测试覆盖率 |
| **C. 补充单元测试** | 为核心逻辑补充单元测试覆盖 |

**推荐**: 方案 A - Demo 测试是集成测试，不纳入单元测试覆盖率计算

---

## PR 提交说明

### PR 标题
```
test(deploy): add minimal deployment validation tests

Add comprehensive deployment tests for 5-service minimal stack:
- Gateway + Journal + Qdrant + Prometheus + Grafana
- 18 test cases covering availability, monitoring, data storage
- Marked as demo/validation tests, not production deployment
- Document known limitations (Tailscale skipped)
```

### PR 描述

**背景**
当前云服务器资源受限（7.5GB 内存），无法运行完整 6 服务栈。本 PR 提供一套验证性测试，证明核心设计目标在简化部署下可行。

**测试范围**
- ✅ Docker 基础设施
- ✅ 5 服务可用性（端口、健康检查）
- ✅ Prometheus + Grafana 监控集成
- ✅ Qdrant 向量存储操作
- ⚠️ 资源限制验证
- ❌ 已知限制：Tailscale 未部署

**CI 适配**
- 新增独立 CI job（手动触发）
- 不纳入单元测试覆盖率（集成测试性质）
- 依赖 Docker 环境

**后续工作**
- [ ] 在 96GB 机器上验证完整 6 服务栈
- [ ] 补充 Tailscale 网络测试
- [ ] 性能基准测试

### 检查清单
- [x] 测试可本地运行
- [x] 测试有明确的成功/失败标准
- [x] 已知限制已文档化
- [ ] CI 配置已添加（待确认）
- [ ] 代码审查通过

---

## 运行测试

### 本地运行
```bash
# 1. 启动服务
cd ~/.openclaw/storage/projects/opc-200
docker compose -f docker-compose.5svc.yml up -d

# 2. 运行测试
python -m pytest tests/deploy/test_minimal_deployment.py -v

# 3. 停止服务
docker compose -f docker-compose.5svc.yml down
```

### 预期输出
```
tests/deploy/test_minimal_deployment.py::TestDeploymentInfrastructure::test_docker_daemon_running PASSED
tests/deploy/test_minimal_deployment.py::TestDeploymentInfrastructure::test_required_images_exist PASSED
tests/deploy/test_minimal_deployment.py::TestServiceAvailability::test_qdrant_health PASSED
...
tests/deploy/test_minimal_deployment.py::TestKnownLimitations::test_tailscale_not_deployed PASSED

18 passed, 0 failed
```

---

## 风险评估

| 风险 | 可能性 | 影响 | 缓解措施 |
|------|--------|------|---------|
| CI 环境无 Docker | 低 | 高 | 使用 GitHub Actions 自带 Docker |
| 测试不稳定 | 中 | 中 | 增加重试机制，标记为 flaky |
| 与现有测试冲突 | 低 | 中 | 独立目录，独立 CI job |
| 覆盖率下降 | 低 | 高 | 明确说明不纳入覆盖率计算 |

---

## 结论

本测试方案：
1. ✅ 验证核心设计目标在资源受限环境下的可行性
2. ✅ 提供明确的通过/失败标准
3. ⚠️ 作为 Demo/验证性测试，不是生产部署标准
4. ℹ️ 已知限制已文档化（Tailscale、OpenAI）

建议先本地验证测试通过，再决定是否提交 PR。
