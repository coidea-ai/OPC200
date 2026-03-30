# OPC200 GitHub Rules 配置建议（单人开发）

## 推荐方案：保护 Main + PR 工作流

### 1. 分支保护规则（Settings → Branches → Add rule）

**规则名称**: Protect Main  
**应用到**: main

#### 勾选以下选项：

☑️ **Require a pull request before merging**
   - Require approvals: 0 （单人项目不需要他人审批）
   - ☑️ Dismiss stale PR approvals when new commits are pushed
   - ☑️ Require review from CODEOWNERS （如果有设置）

☑️ **Require status checks to pass before merging**
   - ☑️ Require branches to be up to date before merging
   - Status checks that are required:
     - `code-quality` (来自 validation-pipeline.yml)
     - `test-matrix` (来自 validation-pipeline.yml)
     - `build-image` (来自 validation-pipeline.yml)

☑️ **Require conversation resolution before merging**
   （确保所有 PR 评论都被处理）

☑️ **Require signed commits** (可选，推荐)
   （增强安全性，所有提交必须签名）

☑️ **Restrict pushes that create files larger than 100MB**
   （防止意外提交大文件）

❌ **Do not allow bypassing the above settings**
   单人项目建议 **不选**，这样你可以紧急情况下直接推送到 main

---

### 2. 开发工作流建议

#### 日常开发流程：
```bash
# 1. 创建功能分支
git checkout -b feature/new-feature

# 2. 开发和提交
git add .
git commit -m "feat: add new feature"

# 3. 推送分支
git push origin feature/new-feature

# 4. 创建 PR（GitHub CLI 或网页）
gh pr create --title "feat: add new feature" --body "描述改动"

# 5. 等待 CI 通过后自审并合并
gh pr merge --squash
```

---

### 3. 三种方案对比

| 方案 | PR 必需 | CI 必需 | 自己可绕过 | 适合场景 |
|------|---------|---------|-----------|---------|
| **A: 完全保护** | ✅ | ✅ | ❌ | 追求代码质量，习惯 PR |
| **B: 半保护** | ✅ | ✅ | ✅ | 推荐！平衡灵活和质量 |
| **C: 仅签名** | ❌ | ❌ | - | 快速迭代，不讲究 |

**推荐 B 方案**（半保护）：
- 平时走 PR + CI，保证质量
- 紧急情况可以直接 push
- 适合 OPC200 当前阶段

---

### 4. 实施步骤

1. 打开 GitHub 仓库页面
2. Settings → Branches → Add rule
3. 按上面的勾选设置
4. 保存

---

### 5. 可选增强

#### CODEOWNERS 文件
创建 `.github/CODEOWNERS`：
```
# 全局所有者
* @danny

# Skills 目录
/skills/ @danny

# CI/CD 配置
/.github/workflows/ @danny
```

#### 提交签名设置
```bash
# 启用 GPG 签名提交
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_KEY_ID
```

---

## 总结

对于单人开发的 OPC200：

1. **启用分支保护**：强制 PR + CI 通过
2. **允许绕过**：不勾选 "do not allow bypassing"，紧急情况直接推
3. **使用功能分支**：feature/*, fix/*, docs/*
4. **养成习惯**：即使自己也要走 PR 流程自审
