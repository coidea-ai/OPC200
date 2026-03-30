# OPC200 团队设置快速指南

为团队协作配置 GitHub 仓库的简明步骤。

---

## 快速设置（15分钟）

### 1. 创建 GitHub Teams（组织设置）

访问: `https://github.com/orgs/coidea-ai/teams`

创建以下团队:

```
owners          → Admin 权限
maintainers     → Maintain 权限
ops             → Maintain 权限（CI/CD）
ui              → Write 权限（前端）
qa              → Write 权限（测试）
docs            → Write 权限（文档）
contributors    → Write 权限（普通开发）
security        → Maintain 权限（安全）
```

添加成员到对应团队。

---

### 2. 配置分支保护

访问: `Settings → Branches → Add rule`

#### Rule 1: `main` 分支

**Apply to**: `main`

**勾选**:
- ✅ Require a pull request before merging
  - Required approvals: **2**
  - ☑️ Dismiss stale PR approvals
  - ☑️ Require review from CODEOWNERS
- ✅ Require status checks to pass
  - ☑️ Require branches to be up to date
  - Required checks:
    - `branch-naming`
    - `commitlint`
    - `code-quality`
    - `test-matrix`
    - `build-image`
- ✅ Require conversation resolution
- ✅ Include administrators
- ❌ Allow force pushes
- ❌ Allow deletions

#### Rule 2: `develop` 分支（可选）

**Apply to**: `develop`

- Required approvals: **1**
- 其他同上

---

### 3. 验证 CODEOWNERS

确保 `.github/CODEOWNERS` 使用了团队名称:

```
* @coidea-ai/owners
/skills/ @coidea-ai/maintainers @coidea-ai/owners
/contracts/ @coidea-ai/owners @coidea-ai/security
/docs/ @coidea-ai/docs
```

---

### 4. 启用工作流

所有工作流文件已配置好，push 后会自动运行:

- `.github/workflows/branch-naming.yml`
- `.github/workflows/commitlint.yml`
- `.github/workflows/auto-assign-reviewers.yml`
- `.github/workflows/permission-check.yml`
- `.github/workflows/validation-pipeline.yml`

---

## 团队工作流速查

### Write 成员（普通开发）

```bash
# 1. 创建功能分支（从main）
git checkout main && git pull origin main
git checkout -b feature/my-feature

# 2. 开发和提交
git commit -m "feat: add new feature"

# 3. 推送到远程
git push origin feature/my-feature

# 4. 创建 PR（自动分配审查者）
gh pr create --title "feat: add new feature"

# 5. 等待审查（需要2人批准）
# CI必须全部通过

# 6. Maintainer合并
```

### Maintainer

```bash
# 审查PR
gh pr review --approve

# 合并PR
gh pr merge --squash

# 创建release分支
git checkout -b release/1.2.0
```

### Admin

```bash
# 管理CI/CD配置
git checkout -b ci/update-workflow

# 紧急修复（如需绕过规则）
# 在PR页面使用 "Merge without waiting"
```

---

## 权限矩阵

| 操作 | Write | Maintainer | Admin | Owner |
|------|-------|------------|-------|-------|
| Push to feature/* | ✅ | ✅ | ✅ | ✅ |
| Create PR | ✅ | ✅ | ✅ | ✅ |
| Review PR | ✅ | ✅ | ✅ | ✅ |
| Merge to develop | ❌ | ✅ | ✅ | ✅ |
| Merge to main | ❌ | ✅ | ✅ | ✅ |
| Push to main | ❌ | ❌ | ❌ | ✅* |
| Modify CI/CD | ❌ | ❌ | ✅ | ✅ |
| Modify contracts | ❌ | ❌ | ✅ | ✅ |
| Bypass protection | ❌ | ❌ | ❌ | ✅ |

*Owner也不应该直接push，但技术上可行

---

## 常见问题

### Q: Write成员无法合并PR？
A: 正常。main分支需要2人审查，由Maintainer合并。

### Q: 如何紧急修复生产问题？
A: 
1. 创建hotfix分支
2. 提交PR
3. Owner使用 "Merge without waiting" 绕过规则
4. 事后补充审查

### Q: 修改了CODEOWNERS但没生效？
A: CODEOWNERS在PR创建时读取，修改后需要重新创建PR。

### Q: 团队成员收不到审查通知？
A: 检查:
1. 是否在CODEOWNERS中正确引用团队
2. 团队是否有仓库访问权限
3. 个人通知设置

---

## 关键文件位置

```
.github/
├── CODEOWNERS              # 代码所有权配置
├── pull_request_template.md # PR模板
└── workflows/
    ├── branch-naming.yml   # 分支名检查
    ├── commitlint.yml      # 提交信息检查
    ├── auto-assign-reviewers.yml  # 自动分配审查者
    ├── permission-check.yml       # 权限检查
    └── validation-pipeline.yml    # 主CI流程

TEAM_COLLABORATION_GUIDE.md  # 完整团队指南
CONTRIBUTING.md              # 贡献指南
```

---

*快速设置指南 v1.0*
