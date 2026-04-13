# OPC200 TDD 开发指南

> 测试驱动开发 (Test-Driven Development) 实践规范

---

## 什么是 TDD

TDD 循环（红-绿-重构）:

```
┌─────────────┐
│  写测试      │ ← 先写失败的测试
│  (Red)      │
└──────┬──────┘
       ▼
┌─────────────┐
│  写代码      │ ← 让测试通过
│  (Green)    │
└──────┬──────┘
       ▼
┌─────────────┐
│  重构        │ ← 优化代码
│ (Refactor)  │
└──────┬──────┘
       │
       └──────────────→ 回到第一步
```

---

## TDD 原则

### 1. 三定律 (The Three Laws)

1. **第一条**: 编写生产代码之前，先编写失败的单元测试
2. **第二条**: 只编写刚好让测试通过的代码
3. **第三条**: 只编写刚好让一个测试失败的产品代码

### 2. 测试标准 (F.I.R.S.T.)

| 原则 | 说明 | 示例 |
|------|------|------|
| **F**ast | 测试运行快 | < 100ms |
| **I**ndependent | 测试相互独立 | 不依赖其他测试 |
| **R**epeatable | 可重复执行 | 任何环境结果一致 |
| **S**elf-validating | 自验证 | bool结果 |
| **T**imely | 及时编写 | 先写测试 |

---

## TDD 工作流程

### 步骤 1: 写失败的测试 (Red)

```python
# test_calculator.py
def test_add():
    calc = Calculator()
    result = calc.add(2, 3)
    assert result == 5  # 此时 Calculator 类还不存在，测试失败
```

**提交**: `test(calculator): add test for add function`

### 步骤 2: 让测试通过 (Green)

```python
# calculator.py
class Calculator:
    def add(self, a, b):
        return a + b  # 最简单的实现
```

**提交**: `feat(calculator): implement add function`

### 步骤 3: 重构 (Refactor)

```python
# calculator.py
class Calculator:
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
```

**提交**: `refactor(calculator): add type hints and docstring`

---

## 项目 TDD 规范

### 目录结构

```
skills/opc-journal/
├── opc-*/
│   ├── scripts/
│   │   └── feature.py       # 生产代码
│   └── tests/
│       ├── __init__.py
│       └── test_feature.py  # 测试代码 (一一对应)
└── tests/                   # 集成测试
    └── test_integration.py
```

### 测试命名规范

| 类型 | 命名规则 | 示例 |
|------|---------|------|
| 测试文件 | `test_*.py` | `test_journal.py` |
| 测试类 | `Test*` | `TestJournalEntry` |
| 测试函数 | `test_*` | `test_record_entry` |
| 测试方法 | `test_*` | `test_record_missing_content` |

### 测试组织结构

```python
# test_feature.py

class TestFeatureName:
    """测试功能名称."""
    
    def test_success_case(self):
        """测试成功场景."""
        pass
    
    def test_failure_case(self):
        """测试失败场景."""
        pass
    
    def test_edge_case(self):
        """测试边界情况."""
        pass
    
    def test_error_handling(self):
        """测试错误处理."""
        pass
```

---

## 测试编写规范

### AAA 模式 (Arrange-Act-Assert)

```python
def test_record_entry():
    # Arrange (准备)
    customer_id = "OPC-001"
    content = "今日工作总结"
    
    # Act (执行)
    result = record_entry(customer_id, content)
    
    # Assert (验证)
    assert result["success"] is True
    assert result["entry_id"].startswith("JE-")
```

### 测试数据

```python
# 使用 fixtures
import pytest

@pytest.fixture
def sample_customer():
    return {
        "customer_id": "OPC-TEST-001",
        "name": "Test Customer",
        "day": 1
    }

def test_with_fixture(sample_customer):
    result = init_journal(sample_customer["customer_id"])
    assert result["customer_id"] == sample_customer["customer_id"]
```

### 测试隔离

```python
# 使用 tmp_path 隔离文件操作
import pytest

def test_file_write(tmp_path):
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    
    assert file_path.read_text() == "test content"
    # 测试结束后 tmp_path 自动清理
```

---

## 覆盖率要求

### 最低标准

| 类型 | 最低覆盖率 | 目标覆盖率 |
|------|-----------|-----------|
| 单元测试 | 80% | 90% |
| 集成测试 | 60% | 70% |
| 总覆盖率 | 75% | 85% |

### 检查覆盖率

```bash
# 本地检查
cd skills/opc-journal
pytest --cov=. --cov-report=term-missing --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html
```

### 覆盖率配置

```ini
# .coveragerc
[run]
source = .
omit = 
    */tests/*
    */__pycache__/*
    */venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
    if __name__ == .__main__.:

fail_under = 80
```

---

## CI/CD 集成

### 覆盖率检查

```yaml
# .github/workflows/skills-test.yml
- name: Run tests with coverage
  run: |
    cd skills/opc-journal
    pytest tests/ --cov=. --cov-report=xml --cov-fail-under=80
```

### 覆盖率报告

```yaml
- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    fail_ci_if_error: true
```

---

## 示例: 完整的 TDD 流程

### 需求: 添加里程碑检测功能

#### 步骤 1: 写测试 (Red)

```python
# test_milestones.py

class TestDetectMilestones:
    """测试里程碑检测功能."""
    
    def test_detect_day_7_milestone(self):
        """测试第7天里程碑检测."""
        # Arrange
        customer_id = "OPC-001"
        day = 7
        
        # Act
        result = detect_milestone(customer_id, day)
        
        # Assert
        assert result["detected"] is True
        assert result["milestone_type"] == "weekly"
        assert result["day"] == 7
    
    def test_no_milestone_on_regular_day(self):
        """测试普通日期无里程碑."""
        result = detect_milestone("OPC-001", day=5)
        assert result["detected"] is False
```

**提交**: `test(milestone): add tests for milestone detection`

#### 步骤 2: 实现功能 (Green)

```python
# detect.py

def detect_milestone(customer_id: str, day: int) -> dict:
    """Detect if current day is a milestone."""
    if day % 7 == 0:
        return {
            "detected": True,
            "milestone_type": "weekly",
            "day": day
        }
    return {"detected": False}
```

**提交**: `feat(milestone): implement basic milestone detection`

#### 步骤 3: 扩展测试 (Red)

```python
# 添加更多测试
def test_detect_day_30_milestone(self):
    """测试第30天里程碑."""
    result = detect_milestone("OPC-001", day=30)
    assert result["detected"] is True
    assert result["milestone_type"] == "monthly"
```

**提交**: `test(milestone): add monthly milestone test`

#### 步骤 4: 完善实现 (Green)

```python
def detect_milestone(customer_id: str, day: int) -> dict:
    """Detect if current day is a milestone."""
    if day % 30 == 0:
        return {
            "detected": True,
            "milestone_type": "monthly",
            "day": day
        }
    if day % 7 == 0:
        return {
            "detected": True,
            "milestone_type": "weekly",
            "day": day
        }
    return {"detected": False}
```

**提交**: `feat(milestone): add monthly milestone detection`

#### 步骤 5: 重构

```python
def detect_milestone(customer_id: str, day: int) -> dict:
    """
    Detect if current day is a milestone.
    
    Milestones:
    - Day 100: Century milestone
    - Day 30, 60, 90: Monthly milestones
    - Day 7, 14, 21: Weekly milestones
    """
    MILESTONE_RULES = [
        (100, "century"),
        (30, "monthly"),
        (7, "weekly"),
    ]
    
    for divisor, milestone_type in MILESTONE_RULES:
        if day % divisor == 0:
            return {
                "detected": True,
                "milestone_type": milestone_type,
                "day": day
            }
    
    return {"detected": False}
```

**提交**: `refactor(milestone): extract milestone rules for clarity`

---

## 常见反模式

### ❌ 不要这样写

```python
# 坏: 测试逻辑复杂
def test_complex(self):
    result = func()
    if result:
        assert result.value > 0
    else:
        assert result.error is not None

# 坏: 一个测试多个断言
def test_multiple(self):
    result = func()
    assert result.a == 1
    assert result.b == 2
    assert result.c == 3
    assert result.d == 4

# 坏: 测试依赖外部状态
def test_with_dependency(self):
    result = func()  # 依赖数据库中的数据
    assert result is not None
```

### ✅ 应该这样写

```python
# 好: 测试简单直接
def test_success(self):
    result = func()
    assert result.value == expected

# 好: 拆分成多个测试
def test_a_is_set(self):
    result = func()
    assert result.a == 1

def test_b_is_set(self):
    result = func()
    assert result.b == 2

# 好: 使用 fixtures 准备数据
@pytest.fixture
def prepared_data():
    return create_test_data()

def test_with_data(prepared_data):
    result = func(prepared_data)
    assert result is not None
```

---

## 检查清单

### 提交前检查

- [ ] 所有测试通过
- [ ] 覆盖率 ≥ 80%
- [ ] 新增功能有对应测试
- [ ] 测试命名清晰
- [ ] 测试独立可重复

### PR 检查

- [ ] 遵循 Red-Green-Refactor 循环
- [ ] 提交信息反映 TDD 阶段
- [ ] 测试覆盖边界情况
- [ ] 测试覆盖错误处理

---

## 工具推荐

| 工具 | 用途 | 安装 |
|------|------|------|
| pytest | 测试框架 | `pip install pytest` |
| pytest-cov | 覆盖率 | `pip install pytest-cov` |
| pytest-watch | 自动重跑 | `pip install pytest-watch` |
| pytest-xdist | 并行测试 | `pip install pytest-xdist` |

### 快捷命令

```bash
# 自动重跑测试
ptw -- -v

# 并行测试
pytest -x -n auto

# 失败时进入 PDB
pytest --pdb

# 只跑失败的测试
pytest --lf
```

---

## 参考资源

- [Test-Driven Development by Example](https://en.wikipedia.org/wiki/Test-Driven_Development_by_Example) - Kent Beck
- [pytest Documentation](https://docs.pytest.org/)
- [Python Testing 101](https://realpython.com/python-testing/)

---

*文档版本: 1.0*  
*最后更新: 2026-03-31*
