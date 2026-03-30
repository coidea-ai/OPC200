## TDD 检查清单

### 红-绿-重构循环

- [ ] **Red**: 先写失败的测试
- [ ] **Green**: 写最少代码让测试通过  
- [ ] **Refactor**: 重构代码，保持测试通过

### 测试质量

- [ ] 测试命名清晰描述行为
- [ ] 使用 AAA 模式 (Arrange-Act-Assert)
- [ ] 每个测试一个概念/断言
- [ ] 测试相互独立
- [ ] 使用 fixtures 准备测试数据

### 覆盖率

- [ ] 新增代码覆盖率 ≥ 80%
- [ ] 覆盖率报告已生成 (`pytest --cov`)
- [ ] 关键路径 100% 覆盖

### 测试类型

- [ ] 正常路径测试
- [ ] 异常路径测试
- [ ] 边界条件测试
- [ ] 错误处理测试

### 提交规范

```
test(scope): description  # Red 阶段
feat(scope): description  # Green 阶段
refactor(scope): description  # Refactor 阶段
```

---

**覆盖率要求**:
- 主套件: ≥ 80%
- 子技能: ≥ 70%
