# OPC200 团队协作规则配置指南

**适用场景**: 多角色团队（Owner/Admin/Maintainer/Write）协作开发

---

## 1. 团队角色与权限矩阵

| 角色 | 权限级别 | 主要职责 | 代码审查要求 |
|------|---------|---------|-------------|
| **Owner** | 最高 | 项目整体架构、关键决策、紧急修复 | 1人审批（其他Owner） |
| **Admin** | 高 | 系统管理、CI/CD配置、安全修复 | 1人审批 |
| **Maintainer** | 中 | 核心功能开发、代码审查、发布管理 | 1人审批 |
| **Write** | 基础 | 功能开发、文档编写、测试 | 2人审批 |

---

## 2. 分支保护策略（严格模式）

### 2.1 Main 分支保护

**Settings → Branches → Add rule**

规则名称: `Protect Main - Strict`
应用到: `main`

#### ✅ 必须勾选

☑️ **Require a pull request before merging**
   - ☑️ Require approvals: **2** （Write成员需要2人审批）
   - ☑️ Dismiss stale PR approvals when new commits are pushed
   - ☑️ Require review from CODEOWNERS
   - ☑️ Restrict who can dismiss pull request reviews: **Owners**

☑️ **Require status checks to pass before merging**
   - ☑️ Require branches to be up to date before merging
   - Required checks:
     - `branch-naming`
     - `commitlint`
     - `code-quality`
     - `test-matrix`
     - `build-image`
     - `trivy-scan` (security)

☑️ **Require conversation resolution before merging**

☑️ **Require signed commits`** (推荐)

☑️ **Include administrators` (Admin也需遵守规则)

☑️ **Restrict pushes that create large files` (>100MB)

☑️ **Require deployments to succeed` (如使用GitHub Environments)

#### ❌ 建议不选

❌ **Allow force pushes` (禁止强制推送)

❌ **Allow deletions` (禁止删除main分支)

☑️ **Do not allow bypassing the above settings` (建议勾选)
   - Owner也需要通过PR，但可以通过临时解除保护处理紧急情况

---

### 2.2 Develop 分支保护（如果使用Git Flow）

规则名称: `Protect Develop`
应用到: `develop`

☑️ **Require a pull request before merging**
   - Require approvals: **1** (比main宽松)
   - ☑️ Dismiss stale PR approvals

☑️ **Require status checks to pass**
   - `code-quality`
   - `test-matrix`

---

### 2.3 Release 分支保护

规则名称: `Protect Release Branches`
应用到: `release/*`

☑️ **Require a pull request before merging**
   - Require approvals: **2** (发布分支需要更严格)
   - ☑️ Require review from CODEOWNERS

☑️ **Restrict who can push**: 仅限 Maintainers 和以上

---

## 3. CODEOWNERS 进阶配置

### 3.1 按目录分配代码所有权

创建 `.github/CODEOWNERS`:

```
# 全局默认 - 所有变更都需要至少一个Owner审查
* @danny @coidea-lead

# =============================================================================
# 核心系统 - 只有Owner和Admin可以批准
# =============================================================================

# 智能合约（安全关键）
/contracts/ @danny @contract-auditor
/contracts/**/security* @danny

# 核心后端API
/src/core/ @danny @backend-lead
/src/auth/ @danny @security-admin
/src/payments/ @danny @finance-admin

# 数据库Schema变更
/migrations/ @danny @db-admin
*.sql @db-admin

# =============================================================================
# Skills 系统 - Maintainer可以批准
# =============================================================================

/skills/ @skills-maintainer @danny
/skills/opc-journal-suite/ @journal-maintainer @danny
/skills/opc-journal-suite/scripts/ @skills-maintainer
/skills/*/tests/ @qa-lead @skills-maintainer

# Skills配置（影响所有用户）
/skills/**/config.yml @danny @skills-maintainer
/skills/**/SKILL.md @docs-maintainer @skills-maintainer

# =============================================================================
# CI/CD 和基础设施 - Admin可以批准
# =============================================================================

/.github/workflows/ @devops-admin @danny
/.github/actions/ @devops-admin
/.github/scripts/ @devops-admin
/terraform/ @devops-admin @infrastructure-lead
/k8s/ @devops-admin
/helm/ @devops-admin
Dockerfile @devops-admin

# =============================================================================
# 文档 - Docs Maintainer可以批准
# =============================================================================

/docs/ @docs-maintainer @danny
*.md @docs-maintainer
README.md @docs-maintainer @danny
CONTRIBUTING.md @docs-maintainer
ARCHITECTURE.md @danny

# =============================================================================
# 前端/UI - UI Maintainer可以批准
# =============================================================================

/src/ui/ @ui-maintainer @frontend-lead
/src/components/ @ui-maintainer
/public/ @ui-maintainer
*.css @ui-maintainer
*.scss @ui-maintainer

# =============================================================================
# 测试 - QA Lead可以批准
# =============================================================================

/tests/ @qa-lead
/tests/e2e/ @qa-lead @danny
*.test.js @qa-lead
*.test.ts @qa-lead
*.test.py @qa-lead

# =============================================================================
# 依赖（安全敏感）- 需要Owner审批
# =============================================================================

/requirements*.txt @danny @security-admin
/package.json @danny @frontend-lead
/package-lock.json @danny @frontend-lead
yarn.lock @danny @frontend-lead
Pipfile @danny @security-admin
poetry.lock @danny @security-admin

# =============================================================================
# 安全和合规 - 只有Owner
# =============================================================================

SECURITY.md @danny
AUDIT_REPORT.md @danny
LICENSE @danny
.pii* @danny
*.key @danny
*.pem @danny
```

### 3.2 CODEOWNERS 工作原理

1. **最后匹配优先**: 后面的规则覆盖前面的
2. **所有匹配的Owner都需要审批**: 如果文件匹配多个规则，所有Owner都要审批
3. **最小权限原则**: 敏感路径只有少数人拥有

---

## 4. 审查流程设计

### 4.1 基于路径的审查要求

```yaml
# 使用 GitHub Actions 实现动态审查要求
name: Review Requirements

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  check-review-requirements:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Check sensitive files
        id: sensitive
        run: |
          # 检查是否修改了敏感文件
          SENSITIVE=$(git diff --name-only HEAD^ | grep -E "(contracts/|src/auth/|migrations/)" || true)
          if [ -n "$SENSITIVE" ]; then
            echo "::set-output name=requires_owner::true"
            echo "Sensitive files changed: $SENSITIVE"
          fi
      
      - name: Require Owner approval for sensitive changes
        if: steps.sensitive.outputs.requires_owner == 'true'
        uses: actions/github-script@v7
        with:
          script: |
            const { data: reviews } = await github.rest.pulls.listReviews({
              owner: context.repo.owner,
              repo: context.repo.repo,
              pull_number: context.issue.number
            });
            
            const ownerApprovals = reviews.filter(r => 
              r.state === 'APPROVED' && 
              ['danny', 'coidea-lead'].includes(r.user.login)
            );
            
            if (ownerApprovals.length === 0) {
              core.setFailed('Changes to sensitive files require Owner approval');
            }
```

### 4.2 自动分配审查者

创建 `.github/reviewers.yml`:

```yaml
# 自动审查者分配规则
reviewers:
  # Skills 目录
  - path: "skills/**"
    reviewers:
      - skills-maintainer
      - danny
    min_reviewers: 1
  
  # 合约目录
  - path: "contracts/**"
    reviewers:
      - danny
      - contract-auditor
    min_reviewers: 2
  
  # CI/CD
  - path: ".github/**"
    reviewers:
      - devops-admin
    min_reviewers: 1
```

---

## 5. 团队工作流

### 5.1 标准开发流程

```bash
# 1. Write 成员创建功能分支
git checkout -b feature/user-profile

# 2. 开发和提交
git commit -m "feat: add user profile page"

# 3. 推送到远程
git push origin feature/user-profile

# 4. 创建 PR（自动分配审查者）
gh pr create --title "feat: add user profile" --reviewer skills-maintainer

# 5. 等待 CI 和审查
# - CI 必须全部通过
# - 至少 1 个 Maintainer 或 2 个 Write 成员审批
# - 所有 CODEOWNERS 审批（如果涉及对应路径）

# 6. 合并（由 Maintainer 执行）
gh pr merge --squash
```

### 5.2 角色特定工作流

#### Write 成员
- 只能推送到 feature/*, fix/*, docs/* 分支
- 不能合并到 main
- 需要 2 人审查

#### Maintainer
- 可以推送到 develop
- 可以审查并合并 Write 成员的 PR
- 可以创建 release/* 分支

#### Admin
- 管理 CI/CD 配置
- 处理安全修复
- 管理 GitHub 设置

#### Owner
- 可以解除分支保护（紧急情况）
- 审查关键架构变更
- 最终发布决策

---

## 6. 紧急情况处理

### 6.1 热修复流程 (Hotfix)

```bash
# 1. 从 main 创建热修复分支（Maintainer 以上）
git checkout main
git checkout -b hotfix/critical-security-fix

# 2. 修复并提交
git commit -m "fix(security): patch critical vulnerability"

# 3. 推送并创建 PR（标记为 hotfix）
gh pr create --title "hotfix: critical security patch" --label hotfix

# 4. 绕过审查（Owner 权限）
# 在 PR 页面使用 "Merge without waiting for requirements"

# 5. 合并后同步到其他分支
git checkout develop
git cherry-pick <hotfix-commit>
```

### 6.2 绕过保护规则

Owner 可以在紧急情况下绕过规则：

1. 在 PR 页面点击 "Merge without waiting for requirements to be met"
2. 或者临时解除分支保护（不推荐）

---

## 7. GitHub Teams 设置

### 7.1 创建团队

在组织设置中创建：

| 团队 | 成员 | 仓库权限 |
|------|------|---------|
| `owners` | danny, co-founder | Admin |
| `maintainers` | senior-dev-1, senior-dev-2 | Maintain |
| `contributors` | dev-1, dev-2, dev-3 | Write |
| `docs` | tech-writer | Write |
| `security` | security-lead | Maintain |
| `ops` | devops-1, devops-2 | Maintain |

### 7.2 CODEOWNERS 使用团队

```
# 使用团队而不是个人
* @coidea-ai/owners
/skills/ @coidea-ai/maintainers @coidea-ai/owners
/docs/ @coidea-ai/docs @coidea-ai/owners
/.github/ @coidea-ai/ops @coidea-ai/owners
```

---

## 8. 完整配置检查清单

### 分支保护
- [ ] main: 2个审批 + CODEOWNERS + 所有CI检查
- [ ] develop: 1个审批 + 基础CI检查
- [ ] release/*: 2个审批 + CODEOWNERS

### CODEOWNERS
- [ ] 按目录分配所有权
- [ ] 敏感路径只有Owner
- [ ] 使用团队而不是个人

### CI/CD
- [ ] branch-naming 检查
- [ ] commitlint 检查
- [ ] code-quality 检查
- [ ] test-matrix 检查
- [ ] build-image 检查
- [ ] trivy-scan 安全检查

### 团队管理
- [ ] GitHub Teams 创建
- [ ] 成员分配到对应团队
- [ ] 团队权限设置

### 文档
- [ ] CONTRIBUTING.md 更新
- [ ] 审查指南文档
- [ ] 紧急处理流程

---

*版本: 1.0*  
*适用于: 多角色团队协作*
