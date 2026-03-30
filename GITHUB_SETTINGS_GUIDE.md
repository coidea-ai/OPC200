# OPC200 GitHub 设置指南

在 GitHub 网页界面中配置多人协作的具体步骤。

---

## 1. 访问仓库设置

1. 打开 https://github.com/coidea-ai/OPC200
2. 点击顶部导航栏的 **Settings**（设置）

---

## 2. 管理协作者 (Collaborators)

**路径**: Settings → Access → Collaborators

### 添加团队成员

1. 点击 **Add people** 按钮
2. 输入用户名、邮箱或姓名搜索
3. 选择对应用户
4. 点击 **Select a role above** 选择角色：
   - **Read** - 只读（查看代码）
   - **Triage** - 分类（管理Issue/PR）
   - **Write** - 写入（推送代码）
   - **Maintain** - 维护（管理仓库设置）
   - **Admin** - 管理员（所有权限）

### 推荐角色分配

| 成员 | 角色 | 权限说明 |
|------|------|---------|
| Danny (Owner) | Admin | 完整控制权 |
| Tech Lead | Maintain | 可管理设置，不能删除仓库 |
| 核心开发者 | Write | 可推送代码，需PR审查 |
| 贡献者 | Triage | 可管理Issue，不能直接推送 |

---

## 3. 配置分支保护规则 (Branch Protection)

**路径**: Settings → Code and automation → Branches → Add rule

### 创建 Main 分支保护规则

**Step 1: 基础设置**
- **Branch name pattern**: `main`
- ☑️ **Restrict pushes that create large files** (限制大文件推送)

**Step 2: PR要求**
- ☑️ **Require a pull request before merging**
  - Required approvals: **1** (或根据团队规模设为2)
  - ☑️ Dismiss stale PR approvals when new commits are pushed
  - ☑️ Require review from CODEOWNERS
  - ☑️ Restrict who can dismiss pull request reviews: 选择Owner

**Step 3: 状态检查 (CI)**
- ☑️ **Require status checks to pass before merging**
  - ☑️ Require branches to be up to date before merging
  - 搜索并添加以下检查：
    - `code-quality` (如存在)
    - `test` (如存在)

**Step 4: 其他选项**
- ☑️ **Require conversation resolution before merging** (解决所有对话)
- ☑️ **Include administrators** (管理员也需遵守)
- ❌ **Allow force pushes** (不允许强制推送)
- ❌ **Allow deletions** (不允许删除分支)

点击 **Create** 保存

---

## 4. 配置 CODEOWNERS (已自动生效)

`.github/CODEOWNERS` 文件已推送到仓库，GitHub 会自动识别。

**验证方式**:
1. 创建一个新PR
2. 查看PR右侧 "Reviewers" 区域
3. 应该自动显示CODEOWNERS中定义的用户

---

## 5. 启用 Discussions (可选但推荐)

**路径**: Settings → General → Discussions

- ☑️ 勾选 **Discussions**
- 选择一个分类作为默认

用途：技术方案讨论、问答、公告

---

## 6. 配置 Issues 模板 (可选)

**路径**: Settings → General → Issues

### 设置 Issue 模板

1. 点击 **Set up templates** 或手动创建：

`.github/ISSUE_TEMPLATE/bug_report.md`:
```markdown
---
name: Bug报告
about: 提交一个Bug
title: '[BUG] '
labels: bug
assignees: ''
---

**描述Bug**
清晰简洁地描述Bug。

**复现步骤**
1. 进入 '...'
2. 点击 '...'
3. 看到错误

**期望行为**
应该发生什么。

**截图**
如有截图请添加。

**环境**
- OS: [e.g. Ubuntu 22.04]
- 版本: [e.g. 2.2.0]
```

`.github/ISSUE_TEMPLATE/feature_request.md`:
```markdown
---
name: 功能请求
about: 建议一个新功能
title: '[FEAT] '
labels: enhancement
assignees: ''
---

**功能描述**
清晰简洁地描述功能。

**使用场景**
描述这个功能在哪些场景下有用。

**替代方案**
你是否考虑替代方案？
```

---

## 7. 配置 Actions 权限

**路径**: Settings → Actions → General

### 推荐设置

**Actions permissions**:
- ☑️ **Allow all actions and reusable workflows** (允许所有Actions)
  - 或选择 **Allow select actions** 更安全

**Workflow permissions**:
- ☑️ **Read and write permissions** (读写权限，用于自动提交)

---

## 8. 配置 Secrets (用于CI/CD)

**路径**: Settings → Security → Secrets and variables → Actions

### 常用 Secrets

| Secret名称 | 用途 | 谁需要设置 |
|-----------|------|-----------|
| `DOCKER_USERNAME` | Docker Hub登录 | DevOps |
| `DOCKER_PASSWORD` | Docker Hub密码 | DevOps |
| `SLACK_WEBHOOK_URL` | Slack通知 | DevOps |
| `DEPLOY_KEY` | 部署密钥 | Owner |

### 添加 Secret

1. 点击 **New repository secret**
2. Name: 输入大写的secret名称
3. Value: 输入secret值
4. 点击 **Add secret**

---

## 9. 配置 Pages (如需要文档站点)

**路径**: Settings → Pages

**Build and deployment**:
- Source: **Deploy from a branch**
- Branch: `gh-pages` / `main` /docs

---

## 10. 检查清单

配置完成后，验证以下设置：

- [ ] 协作者已添加并分配正确角色
- [ ] Main分支保护规则已启用
- [ ] PR模板生效（创建PR时自动填充）
- [ ] CODEOWNERS自动分配审查者
- [ ] Discussions已启用
- [ ] Issue模板已配置
- [ ] Actions权限已设置
- [ ] 必要的Secrets已添加

---

## 快速测试

### 测试PR流程

1. 创建一个新分支：`git checkout -b test/collaboration`
2. 做一个小的修改（如添加注释）
3. 提交并推送：`git commit -m "test: verify collaboration setup" && git push origin test/collaboration`
4. 在GitHub上创建PR
5. 验证：
   - PR模板是否自动填充？
   - CODEOWNERS是否自动分配审查者？
   - 分支保护是否阻止直接合并？

---

## 常见问题

### Q: CODEOWNERS不生效？
A: 确保：
- 文件路径是 `.github/CODEOWNERS` (大写)
- 文件已推送到默认分支 (main)
- 用户有仓库访问权限

### Q: 如何临时绕过保护规则？
A: Owner可以：
- 在PR页面使用 "Merge without waiting for requirements to be met"
- 或临时禁用分支保护（不推荐）

### Q: 审查者收不到通知？
A: 检查：
- 用户通知设置 (Settings → Notifications)
- 是否被正确添加到CODEOWNERS
- 邮箱是否正确

---

*配置指南 v1.0*  
*配套文档: COLLABORATION.md*
