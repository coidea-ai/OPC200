# OPC200 开发规范

本文档定义了 OPC200 项目的开发规范，包括代码审查、提交信息和分支命名。

> **团队协作**: 本文档适用于多角色团队（Owner/Admin/Maintainer/Write）。
> 完整团队设置指南见 [TEAM_SETUP_QUICK.md](./TEAM_SETUP_QUICK.md) 和 [TEAM_COLLABORATION_GUIDE.md](./TEAM_COLLABORATION_GUIDE.md)。

---

## 0. 团队角色与权限

| 角色 | 权限 | 审查要求 | 主要职责 |
|------|------|---------|---------|
| **Owner** | 最高 | 1 Owner 审批 | 架构决策、紧急修复 |
| **Admin** | 高 | 1 Admin 审批 | CI/CD、系统管理 |
| **Maintainer** | 中 | 1 Maintainer 审批 | 核心功能、代码审查 |
| **Write** | 基础 | 2 人审批 | 功能开发、文档 |

**GitHub Teams**:
- `@coidea-ai/owners` - 项目所有者
- `@coidea-ai/maintainers` - 核心维护者
- `@coidea-ai/ops` - DevOps 团队
- `@coidea-ai/ui` - 前端团队
- `@coidea-ai/qa` - 测试团队
- `@coidea-ai/docs` - 文档团队
- `@coidea-ai/security` - 安全团队
- `@coidea-ai/contributors` - 普通贡献者

---

## 1. CODEOWNERS

代码所有权通过 `.github/CODEOWNERS` 配置：

```
# 全局默认 - 所有变更需要Owner审批
* @coidea-ai/owners

# Skills 目录 - Maintainer可以审批
/skills/ @coidea-ai/maintainers @coidea-ai/owners

# 智能合约 - 需要Owner和Security审批
/contracts/ @coidea-ai/owners @coidea-ai/security

# 文档 - Docs团队可以审批
/docs/ @coidea-ai/docs
```

**规则**:
- 最后匹配的规则生效
- 所有匹配的 Owner 都需要审批
- 敏感路径只有核心团队

---

## 2. 开发工作流

### 标准流程（所有成员）

```bash
# 1. 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/my-feature

# 2. 开发并提交（遵循提交规范）
git add .
git commit -m "feat: add new feature"

# 3. 保持分支更新
git fetch origin
git rebase origin/main

# 4. 推送到远程
git push origin feature/my-feature

# 5. 创建 PR（自动分配审查者）
gh pr create --title "feat: add new feature" --body "描述改动"

# 6. 等待审查和CI
# - 审查者自动分配（基于CODEOWNERS）
# - 所有CI检查必须通过
# - Write成员需要2人审批
# - Maintainer及以上需要1人审批

# 7. Maintainer合并
gh pr merge --squash
```

### 热修复流程（紧急情况）

```bash
# 1. 从main创建热修复分支
git checkout main
git checkout -b hotfix/critical-fix

# 2. 修复并提交
git commit -m "fix(security): patch critical vulnerability"

# 3. 创建PR（标记hotfix）
gh pr create --title "hotfix: critical fix" --label hotfix

# 4. Owner使用 "Merge without waiting" 绕过规则

# 5. 事后补充审查和文档
```

---

## 3. 提交信息规范（Conventional Commits）

### 格式
```
<type>[(scope)][!]: <subject>

[body]

[footer]
```

### 类型（Type）

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat: add user authentication` |
| `fix` | Bug 修复 | `fix(api): resolve null pointer` |
| `docs` | 文档更新 | `docs: update README` |
| `style` | 代码格式 | `style: fix indentation` |
| `refactor` | 重构 | `refactor: simplify logic` |
| `perf` | 性能优化 | `perf: cache query results` |
| `test` | 测试相关 | `test: add unit tests` |
| `build` | 构建系统 | `build: update dependencies` |
| `ci` | CI/CD 变更 | `ci: add Slack notification` |
| `chore` | 其他维护 | `chore: clean up comments` |
| `revert` | 撤销提交 | `revert: feat: old feature` |

### 作用域（Scope）

可选，用于指定变更范围：

- `skills` - Skills 相关
- `api` - API 接口
- `ui` - 用户界面
- `db` - 数据库
- `ci` - CI/CD
- `docs` - 文档
- `deps` - 依赖

### 示例

```bash
# 新功能
feat: add journal entry tagging

# 带作用域的修复
fix(skills): resolve intent detection bug

# 破坏性变更
feat(api)!: change authentication flow

# 多行提交信息
feat(skills): add milestone tracking

- Auto-detect milestones from journal entries
- Generate celebration reports
- Support custom milestone definitions

Closes #123
```

### 提交信息检查

- **本地**: `pre-commit` 钩子自动检查
- **CI**: `.github/workflows/commitlint.yml` 在 PR 时检查

---

## 3. 分支命名规范

### 格式
```
<type>/<description>
```

### 类型前缀

| 前缀 | 用途 | 示例 |
|------|------|------|
| `feature/` | 新功能开发 | `feature/user-auth` |
| `fix/` | Bug 修复 | `fix/login-error` |
| `hotfix/` | 紧急生产修复 | `hotfix/security-patch` |
| `docs/` | 文档更新 | `docs/api-guide` |
| `refactor/` | 代码重构 | `refactor/simplify-parser` |
| `test/` | 测试相关 | `test/add-e2e-tests` |
| `ci/` | CI/CD 变更 | `ci/add-deployment` |
| `release/` | 发布准备 | `release/2.0.0` |

### 命名规则

1. **小写字母**: 全部使用小写
2. **连字符分隔**: 用 `-` 分隔单词
3. **简短清晰**: 描述要准确但不超过 50 字符
4. **关联 Issue**: 如有相关 Issue，可在描述中包含

### 有效示例

```
feature/journal-export
fix/cron-scheduler-timezone
docs/deployment-guide
hotfix/api-memory-leak
refactor/simplify-coordinate-logic
test/integration-tests-for-skills
ci/add-trivy-scanning
release/2.3.0
```

### 无效示例

```
new-feature          # 缺少类型前缀
Feature/NewStuff     # 大写字母
fix_bug              # 下划线分隔
feature/very-long-branch-name-that-is-hard-to-read  # 太长
```

### 分支检查

- **CI**: `.github/workflows/branch-naming.yml` 在创建分支和 PR 时检查

---

## 4. Pull Request 规范

### PR 标题格式
建议使用 Conventional Commits 格式：
```
feat: add milestone tracking
fix(skills): resolve memory leak
docs: update deployment guide
```

### PR 审查要求

| 目标分支 | Write成员 | Maintainer | Admin/Owner |
|---------|----------|-----------|-------------|
| `main` | 2人审批 | 1人审批 | 1人审批 |
| `develop` | 1人审批 | 1人审批 | 1人审批 |
| `release/*` | 不可合并 | 2人审批 | 1人审批 |
| `hotfix/*` | 紧急时可跳过 | 紧急时可跳过 | 可立即合并 |

### 审查者分配

- **自动分配**: 基于 CODEOWNERS 自动分配
- **敏感变更**: 需要 Owner 或 Security 团队额外审批
- **自我审查**: 不允许，必须由其他人审查

---

## 5. CI/CD 检查流程

每次 PR 会触发以下检查：

1. **Branch Naming** - 分支名是否符合规范
2. **Commit Message Lint** - 提交信息是否符合 Conventional Commits
3. **Permission Check** - 用户权限是否足够（敏感文件）
4. **Code Quality** - 代码格式、lint、类型检查
5. **Test Matrix** - 单元测试和集成测试
6. **Build Image** - Docker 镜像构建
7. **Security Scan** - Trivy 漏洞扫描

所有检查通过后才能合并。

---

## 6. 快速参考

### 创建新功能（Write成员）

---

## 5. Pull Request 规范

### PR 标题
建议使用 Conventional Commits 格式（但不强制）：
```
feat: add milestone tracking
fix(skills): resolve memory leak
docs: update deployment guide
```

### PR 描述模板

```markdown
## 变更类型
- [ ] feat: 新功能
- [ ] fix: Bug 修复
- [ ] docs: 文档更新
- [ ] refactor: 代码重构
- [ ] test: 测试相关
- [ ] chore: 其他维护

## 描述
简要描述这次改动做了什么。

## 相关 Issue
Closes #123

## 检查清单
- [ ] 代码通过所有测试
- [ ] 提交信息符合规范
- [ ] 更新了相关文档
- [ ] 没有引入破坏性变更（如有请标注）
```

---

## 6. CI/CD 检查流程

每次 PR 会触发以下检查：

1. **Branch Naming** - 分支名是否符合规范
2. **Commit Message Lint** - 提交信息是否符合 Conventional Commits
3. **Code Quality** - 代码格式、lint、类型检查
4. **Test Matrix** - 单元测试和集成测试
5. **Build Image** - Docker 镜像构建
6. **Security Scan** - Trivy 漏洞扫描

所有检查通过后才能合并。

---

## 7. 快速参考

### 创建新功能
```bash
git checkout -b feature/my-feature
git commit -m "feat: add awesome feature"
git push origin feature/my-feature
gh pr create && gh pr merge --squash
```

### 修复 Bug
```bash
git checkout -b fix/bug-name
git commit -m "fix: resolve bug description"
git push origin fix/bug-name
gh pr create && gh pr merge --squash
```

### 更新文档
```bash
git checkout -b docs/update-readme
git commit -m "docs: update installation instructions"
git push origin docs/update-readme
gh pr create && gh pr merge --squash
```

---

*规范版本: 1.0*  
*最后更新: 2026-03-30*
