# OPC200 多人协作开发指南

> **项目**: One Person Company 超级智能体支持平台  
> **目标**: 200个客户，100天陪伴式成长

---

## 1. 团队结构与角色

### 核心角色

| 角色 | 职责 | 代码审查权 | 合并权限 |
|------|------|-----------|---------|
| **项目Owner** | 架构决策、安全审查、发布批准 | 全部 | main分支 |
| **Tech Lead** | 技术方案、代码质量、技能培训 | 全部 | develop分支 |
| **核心开发者** | 功能开发、Bug修复、测试 | 一般PR | feature分支 |
| **贡献者** | 文档、测试、小型功能 | 小型PR | 需审查 |

### 模块负责人

| 模块 | 负责人 | 说明 |
|------|--------|------|
| `skills/opc-journal-suite/` | @danny | 核心技能套件 |
| `src/core/` | Tech Lead | 核心业务逻辑 |
| `src/auth/` | Security Lead | 认证授权（敏感） |
| `.github/workflows/` | DevOps Lead | CI/CD配置 |
| `docs/` | Docs Lead | 文档维护 |

---

## 2. 分支策略

### 分支模型: GitHub Flow (简化版)

```
main (生产分支)
  ↑
feature/* (功能分支)
  ↑
fix/* (修复分支)
  ↑
hotfix/* (紧急修复)
```

### 分支命名规范

```
feature/<描述>          # 新功能: feature/journal-export
fix/<描述>             # Bug修复: fix/memory-leak
docs/<描述>            # 文档: docs/api-guide
refactor/<描述>        # 重构: refactor/simplify-parser
test/<描述>            # 测试: test/e2e-coverage
hotfix/<描述>          # 紧急修复: hotfix/security-patch
```

---

## 3. 开发工作流

### 标准开发流程

```bash
# 1. 同步主线
git checkout main
git pull origin main

# 2. 创建功能分支
git checkout -b feature/my-feature

# 3. 开发（遵循提交规范）
git commit -m "feat: add user profile page"

# 4. 保持同步（定期rebase）
git fetch origin
git rebase origin/main

# 5. 推送分支
git push origin feature/my-feature

# 6. 创建PR
gh pr create --title "feat: add user profile" --reviewer <tech-lead>

# 7. 等待审查和CI
# 8. 合并（由Tech Lead或Owner执行）
```

### PR 审查流程

1. **自动检查** (CI)
   - 代码格式检查
   - 单元测试
   - 集成测试
   - 安全扫描

2. **人工审查**
   - 代码逻辑审查
   - 架构合理性
   - 性能影响评估
   - 安全风险评估

3. **审查清单**
   - [ ] 代码符合项目规范
   - [ ] 测试覆盖率足够
   - [ ] 文档已更新
   - [ ] 无敏感信息泄露
   - [ ] 无破坏性变更（如有需标注）

---

## 4. 提交信息规范

### Conventional Commits

```
<type>[(scope)]: <subject>

[body]

[footer]
```

### 类型说明

| 类型 | 用途 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add milestone tracking` |
| `fix` | Bug修复 | `fix(skills): resolve intent detection` |
| `docs` | 文档更新 | `docs: update deployment guide` |
| `style` | 代码格式 | `style: fix indentation` |
| `refactor` | 重构 | `refactor: simplify logic` |
| `test` | 测试 | `test: add unit tests` |
| `chore` | 维护 | `chore: update dependencies` |

### 示例

```bash
# 简单提交
feat: add journal entry tagging

# 带作用域
fix(skills): resolve memory leak in coordinator

# 带描述
feat(journal): add milestone tracking

- Auto-detect milestones from entries
- Generate celebration reports
- Support custom definitions

Closes #123

# 破坏性变更
feat(api)!: change authentication flow

BREAKING CHANGE: JWT token format changed
```

---

## 5. 代码审查指南

### 审查原则

1. **建设性反馈** - 指出问题同时提供建议
2. **及时响应** - 24小时内响应审查请求
3. **知识共享** - 审查是学习和教学的机会

### 审查重点

#### 功能性
- 代码是否实现了预期功能
- 边界情况是否处理
- 错误处理是否完善

#### 安全性
- 无敏感信息硬编码
- 输入验证充分
- 权限检查正确

#### 性能
- 无明显的性能问题
- 资源使用合理
- 大数据量处理考虑

#### 可维护性
- 命名清晰有意义
- 注释充分且准确
- 代码结构合理

### 审查用语

| 级别 | 标记 | 含义 |
|------|------|------|
| 阻塞 | 🔴 | 必须修改才能合并 |
| 建议 | 🟡 | 建议修改，但非强制 |
| 疑问 | 🔵 | 需要澄清 |
| 赞赏 | 🟢 | 做得好的地方 |

---

## 6. 敏感代码处理

### 敏感路径

以下路径的变更需要额外审查：

```
/contracts/           # 智能合约（安全关键）
/src/auth/            # 认证授权
/src/payments/        # 支付相关
/migrations/          # 数据库变更
/config/production*   # 生产配置
.github/workflows/    # CI/CD配置
```

### 敏感变更流程

1. **提前沟通** - 在实现前与Tech Lead讨论
2. **安全审查** - 必须经过Security Lead审查
3. **测试加强** - 增加额外的安全测试
4. **文档更新** - 更新安全相关文档

---

## 7. 冲突解决

### 预防冲突

- **频繁同步** - 每天至少一次 `git pull origin main`
- **小步提交** - 避免大型PR，控制在500行以内
- **及时沟通** - 改动公共文件前在群里说一声

### 解决冲突

```bash
# 1. 获取最新代码
git fetch origin

# 2. rebase到最新main
git rebase origin/main

# 3. 解决冲突
# - 打开冲突文件
# - 保留需要的更改
# - 删除冲突标记

# 4. 继续rebase
git add .
git rebase --continue

# 5. 强制推送（仅限自己的分支）
git push --force-with-lease origin feature/my-feature
```

---

## 8. 紧急修复流程

### Hotfix 流程

```bash
# 1. 从main创建hotfix分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix

# 2. 修复问题（最小化改动）
git commit -m "fix(security): patch critical vulnerability"

# 3. 创建PR（标记hotfix）
gh pr create --title "hotfix: critical security fix" --label hotfix

# 4. Tech Lead快速审查

# 5. Owner绕过规则合并（如必要）
# PR页面 → "Merge without waiting"

# 6. 同步回开发分支
git checkout main
git pull origin main
git checkout develop
git cherry-pick <hotfix-commit>
```

---

## 9. 文档协作

### 文档位置

| 文档类型 | 位置 | 维护者 |
|---------|------|--------|
| 架构文档 | `ARCHITECTURE.md` | Tech Lead |
| API文档 | `docs/api/` | API Lead |
| 部署文档 | `DEPLOYMENT_CHECKLIST_200_OPC.md` | DevOps |
| 开发规范 | `COLLABORATION.md` | Tech Lead |

### 文档更新规范

- 代码变更必须同步更新相关文档
- 新功能必须有文档说明
- API变更必须更新接口文档

---

## 10. 沟通渠道

### 异步沟通

- **GitHub Issues** - 功能讨论、Bug报告
- **Pull Requests** - 代码审查讨论
- **GitHub Discussions** - 技术方案讨论

### 同步沟通

- **飞书/钉钉群** - 日常沟通、快速问题
- **Weekly Sync** - 每周进度同步会议

### 沟通规范

- @mentions 使用恰当，不要滥用
- 复杂问题开Issue讨论，不要在群里长篇大论
- 文档化重要决策，不要只口头传达

---

## 快速参考

### 常用命令

```bash
# 创建功能分支
git checkout -b feature/my-feature

# 创建修复分支
git checkout -b fix/bug-description

# 保持同步
git fetch origin && git rebase origin/main

# 创建PR
gh pr create --title "feat: description" --reviewer <username>

# 查看PR状态
gh pr view

# 合并PR
gh pr merge --squash
```

### 紧急联系

| 情况 | 联系人 |
|------|--------|
| 生产事故 | @danny (Owner) |
| 安全漏洞 | Security Lead |
| CI/CD故障 | DevOps Lead |
| 代码审查堵塞 | Tech Lead |

---

*文档版本: 1.0*  
*最后更新: 2026-03-31*
