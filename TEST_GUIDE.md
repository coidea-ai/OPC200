# OPC200 全量测试指南

## 快速开始

### 一键运行所有测试

```bash
./scripts/run_all_tests.sh
```

### 分别运行各层测试

```bash
# 1. 单元测试 (280个)
pytest tests/unit -v --cov=src --cov-fail-under=80

# 2. 集成测试 (50个)
pytest tests/integration -v --timeout=120

# 3. Skills测试 (83个)
cd skills/opc-journal-suite
pytest tests/ -v --cov=.
for dir in opc-*/; do cd "$dir" && pytest tests/ -v && cd ..; done

# 4. E2E测试 (15个)
pytest tests/e2e -v --timeout=300

# 5. 安全测试
pytest tests/security -v
```

## 测试统计

| 层级 | 数量 | 覆盖率 | 位置 |
|------|------|--------|------|
| 单元测试 | ~280 | 75% | `tests/unit/` |
| 集成测试 | ~50 | 60% | `tests/integration/` |
| Skills测试 | 83 | 75% | `skills/opc-journal-suite/**/tests/` |
| E2E测试 | ~15 | 40% | `tests/e2e/` |
| **总计** | **~428** | **70%** | - |

## 添加新测试

### 单元测试模板

```python
# tests/unit/xxx/test_feature.py
import pytest

class TestFeatureName:
    def test_success_case(self):
        result = function_to_test(valid_input)
        assert result == expected
    
    def test_failure_case(self):
        with pytest.raises(ValueError):
            function_to_test(invalid_input)
```

### 运行单个测试文件

```bash
pytest tests/unit/utils/test_validation.py -v
```

### 运行带覆盖率

```bash
pytest tests/unit -v --cov=src --cov-report=html
open htmlcov/index.html
```

## 覆盖率目标

- **当前**: 70%
- **目标**: 80%
- **关键模块**: 90%

## 文档

详细策略见: [docs/FULL_TEST_STRATEGY.md](docs/FULL_TEST_STRATEGY.md)
