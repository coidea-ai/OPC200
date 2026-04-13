# OPC200 全量测试策略

> 完整的测试覆盖方案，确保代码质量和可靠性

---

## 1. 测试金字塔

```
       /\
      /  \      E2E 测试 (5%)     - 用户场景
     /----\     
    /      \    集成测试 (15%)    - 模块交互
   /--------\
  /          \   单元测试 (80%)   - 函数/类
 /------------\
```

## 2. 当前测试状态

| 层级 | 数量 | 覆盖率 | 状态 |
|------|------|--------|------|
| 单元测试 | ~280 | 75% | ✅ 良好 |
| 集成测试 | ~50 | 60% | ⚠️ 需加强 |
| E2E测试 | ~15 | 40% | ⚠️ 需扩展 |
| **总计** | **345** | **70%** | ⚠️ 目标80% |

---

## 3. 测试分层详解

### 3.1 单元测试 (Unit Tests)

**位置**: `tests/unit/`

**目标**: 每个函数/方法至少一个测试

```
tests/unit/
├── journal/           ✅ 日志核心功能
├── security/          ✅ 安全/加密
├── skills/            ✅ 技能系统
├── patterns/          ✅ 模式识别
├── insights/          ✅ 洞察生成
├── tasks/             ✅ 任务调度
├── monitoring/        ✅ 监控指标
├── utils/             ❌ **缺少** - 需添加
└── api/               ❌ **缺少** - 需添加
```

**运行命令**:
```bash
pytest tests/unit -v --cov=src --cov-fail-under=80
```

### 3.2 集成测试 (Integration Tests)

**位置**: `tests/integration/`

**目标**: 模块间交互测试

```
tests/integration/
├── test_end_to_end.py         ✅ 端到端流程
├── test_journal_flow.py       ✅ 日志流程
├── test_security_flow.py      ✅ 安全流程
├── test_skills.py             ✅ 技能集成
├── test_database.py           ❌ **缺少** - 数据库集成
├── test_api_integration.py    ❌ **缺少** - API集成
└── test_external_services.py  ❌ **缺少** - 外部服务
```

**运行命令**:
```bash
pytest tests/integration -v --timeout=120
```

### 3.3 E2E测试 (End-to-End)

**位置**: `tests/e2e/`

**目标**: 完整用户场景

```
tests/e2e/
├── test_user_journey.py           ✅ 用户旅程
├── test_opc_onboarding.py         ❌ **缺少** - 客户入职
├── test_daily_journal_workflow.py ❌ **缺少** - 日志工作流
└── test_admin_operations.py       ❌ **缺少** - 管理员操作
```

### 3.4 Skills专项测试

**位置**: `skills/opc-journal/`

**状态**: 已完整 (83个测试)

```
skills/opc-journal/
├── tests/                         ✅ 44个测试
│   ├── test_coordinate.py
│   ├── test_cron_scheduler.py
│   └── test_init_v2.py
└── opc-*/tests/                   ✅ 39个测试
    ├── opc-journal-core (11)
    ├── opc-pattern-recognition (13)
    ├── opc-milestone-tracker (6)
    ├── opc-async-task-manager (6)
    └── opc-insight-generator (3)
```

---

## 4. 缺失测试清单

### 高优先级 (必须)

| 模块 | 位置 | 测试文件 | 测试场景 |
|------|------|---------|---------|
| Utils | `src/utils/` | `tests/unit/utils/` | 工具函数、辅助方法 |
| API | `src/api/` | `tests/unit/api/` | 路由、控制器、验证 |
| Database | `src/db/` | `tests/integration/test_database.py` | 连接、事务、迁移 |

### 中优先级 (建议)

| 模块 | 位置 | 测试文件 | 测试场景 |
|------|------|---------|---------|
| Config | `src/config/` | `tests/unit/config/` | 配置加载、验证 |
| CLI | `src/cli/` | `tests/unit/cli/` | 命令解析、执行 |
| External APIs | `src/external/` | `tests/integration/test_external.py` | 第三方服务调用 |

### 低优先级 (可选)

| 模块 | 测试类型 | 说明 |
|------|---------|------|
| Performance | `tests/performance/` | 基准测试、负载测试 |
| Security | `tests/security/` | 渗透测试、漏洞扫描 |

---

## 5. 测试生成计划

### Phase 1: 基础补齐 (1周)

```bash
# 1. Utils测试
mkdir -p tests/unit/utils
touch tests/unit/utils/__init__.py
touch tests/unit/utils/test_helpers.py
touch tests/unit/utils/test_validators.py
touch tests/unit/utils/test_formatters.py

# 2. API测试
mkdir -p tests/unit/api
touch tests/unit/api/__init__.py
touch tests/unit/api/test_routes.py
touch tests/unit/api/test_middleware.py
touch tests/unit/api/test_auth.py

# 3. Database集成测试
touch tests/integration/test_database.py
```

### Phase 2: E2E扩展 (1周)

```bash
# E2E场景测试
touch tests/e2e/test_opc_onboarding.py
touch tests/e2e/test_daily_journal_workflow.py
touch tests/e2e/test_admin_operations.py
```

### Phase 3: 性能测试 (3天)

```bash
# 性能基准
touch tests/performance/test_journal_performance.py
touch tests/performance/test_query_performance.py
```

---

## 6. 测试模板

### 单元测试模板

```python
# tests/unit/xxx/test_feature.py
"""测试XXX功能."""

import pytest
from unittest.mock import Mock, patch


class TestFeatureName:
    """测试功能名称."""
    
    @pytest.fixture
    def setup(self):
        """测试夹具."""
        return {
            "mock_data": "test",
            "config": {}
        }
    
    def test_success_case(self, setup):
        """测试成功场景."""
        # Arrange
        data = setup["mock_data"]
        
        # Act
        result = function_to_test(data)
        
        # Assert
        assert result == expected_value
    
    def test_failure_case(self):
        """测试失败场景."""
        with pytest.raises(ValueError):
            function_to_test(invalid_input)
    
    def test_edge_case(self):
        """测试边界条件."""
        # 边界值测试
        assert function_to_test(boundary_value) == expected
```

### 集成测试模板

```python
# tests/integration/test_feature_integration.py
"""测试XXX集成."""

import pytest


class TestFeatureIntegration:
    """测试功能集成."""
    
    @pytest.fixture(scope="module")
    def setup_module(self):
        """模块级设置."""
        # 初始化数据库、服务等
        pass
    
    def test_module_integration(self, setup_module):
        """测试模块间集成."""
        # 测试多个模块协作
        pass
    
    def test_database_integration(self):
        """测试数据库集成."""
        # 测试数据库操作
        pass
```

### E2E测试模板

```python
# tests/e2e/test_user_scenario.py
"""测试用户场景."""

import pytest


class TestUserScenario:
    """测试用户场景."""
    
    @pytest.fixture(scope="class")
    def setup_environment(self):
        """设置测试环境."""
        # 启动服务、准备数据
        pass
    
    def test_complete_user_journey(self, setup_environment):
        """测试完整用户旅程."""
        # 步骤1: 用户注册
        # 步骤2: 创建日志
        # 步骤3: 查看分析
        # 步骤4: 导出数据
        pass
```

---

## 7. 自动化命令

### 一键运行全量测试

```bash
#!/bin/bash
# scripts/run_all_tests.sh

echo "🧪 OPC200 全量测试"
echo "=================="

# 1. 单元测试
echo "1. 运行单元测试..."
pytest tests/unit -v --cov=src --cov-report=term || exit 1

# 2. 集成测试
echo "2. 运行集成测试..."
pytest tests/integration -v --timeout=120 || exit 1

# 3. Skills测试
echo "3. 运行Skills测试..."
cd skills/opc-journal
pytest tests/ -v --cov=. || exit 1
for dir in opc-*/; do
    cd "$dir" && pytest tests/ -v || exit 1
    cd ..
done
cd ../..

# 4. E2E测试
echo "4. 运行E2E测试..."
pytest tests/e2e -v --timeout=300 || exit 1

# 5. 安全测试
echo "5. 运行安全测试..."
pytest tests/security -v || exit 1

# 6. 性能测试 (可选)
echo "6. 运行性能测试..."
pytest tests/performance -v || true

echo "✅ 全量测试通过!"
```

### Makefile添加

```makefile
# 添加到 Makefile

test-full: ## 运行全量测试
	@echo "🧪 Running full test suite..."
	$(MAKE) test-unit
	$(MAKE) test-integration
	$(MAKE) test-skills
	$(MAKE) test-e2e
	$(MAKE) test-security

test-unit: ## 单元测试
	pytest tests/unit -v --cov=src --cov-fail-under=80

test-integration: ## 集成测试
	pytest tests/integration -v --timeout=120

test-e2e: ## E2E测试
	pytest tests/e2e -v --timeout=300

test-security: ## 安全测试
	pytest tests/security -v

test-coverage: ## 覆盖率检查
	pytest tests/ --cov=src --cov-report=html --cov-fail-under=80
```

---

## 8. CI/CD集成

### 全量测试工作流

```yaml
# .github/workflows/full-test-suite.yml
name: 🧪 Full Test Suite

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # 每天凌晨2点

jobs:
  unit-tests:
    name: 单元测试
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest tests/unit -v --cov=src --cov-fail-under=80
      
  integration-tests:
    name: 集成测试
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest tests/integration -v --timeout=120
      
  skills-tests:
    name: Skills测试
    runs-on: ubuntu-latest
    needs: unit-tests
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: |
          cd skills/opc-journal
          pytest tests/ -v --cov=. --cov-fail-under=80
          for dir in opc-*/; do
            cd "$dir" && pytest tests/ -v && cd ..
          done
      
  e2e-tests:
    name: E2E测试
    runs-on: ubuntu-latest
    needs: [unit-tests, integration-tests]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pytest tests/e2e -v --timeout=300
      
  security-tests:
    name: 安全测试
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pytest tests/security -v
      - run: bandit -r src/
```

---

## 9. 覆盖率目标

| 模块 | 当前 | 目标 | 状态 |
|------|------|------|------|
| src/journal/ | 85% | 90% | 🟡 |
| src/security/ | 80% | 90% | 🟡 |
| src/api/ | 60% | 80% | 🔴 |
| src/utils/ | 40% | 80% | 🔴 |
| skills/ | 75% | 85% | 🟡 |
| **整体** | **70%** | **80%** | 🟡 |

---

## 10. 测试检查清单

### 新建功能测试清单

- [ ] 单元测试覆盖所有函数
- [ ] 集成测试覆盖模块交互
- [ ] E2E测试覆盖用户场景
- [ ] 异常路径测试
- [ ] 边界条件测试
- [ ] 性能基准测试
- [ ] 覆盖率 ≥ 80%

### PR提交前检查

- [ ] 全量测试通过
- [ ] 覆盖率不下降
- [ ] 无flake8错误
- [ ] 无安全警告

---

*文档版本: 1.0*  
*目标: 80%覆盖率, 500+测试*
