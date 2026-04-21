# OPC200 Release — 参考速查

## 流程文档

| 文档 | 路径 |
|------|------|
| 无仓库安装发布与验收 | `docs/INSTALL_SCRIPT_SPEC.md` §9.0 |

## 仓库内关键路径

| 用途 | 路径 |
|------|------|
| 语义化版本（无 `v`） | `VERSION` |
| Windows 第二阶段 `AGENT_VERSION` | `agent/scripts/install.ps1` |
| Linux 第二阶段 `AGENT_VERSION` | `agent/scripts/install.sh` |
| Bootstrap（上传为 Release 资产） | `agent/scripts/opc200-install.ps1`, `opc200-install.sh` |
| 发版 workflow | `.github/workflows/release-opc-agent.yml` |
| 打包脚本（workflow 调用） | `agent/scripts/build-agent-bundle.sh` |

## 常用命令

```bash
# 列出 v* tag
git tag -l 'v*'

# 查看某 tag 指向的提交
git rev-parse vX.Y.Z^{}

# 仅查看 Release workflow 最近一次运行
gh run list --workflow=release-opc-agent.yml -L 3

# Release 资产名称列表
gh release view vX.Y.Z --json assets -q '.assets[].name'

# latest 是否为预期 tag（替换 owner/repo）
curl -sS https://api.github.com/repos/owner/repo/releases/latest | jq -r '.tag_name, (.assets[].name)'
```

## 四件套文件名模式

- `opc200-agent-<semver>.zip` — `<semver>` 与 `VERSION` 一致，无 `v`。  
- `SHA256SUMS` — 与 zip 同 tag 的 `releases/download` 下。  
- 引导脚本：固定名 `opc200-install.ps1`、`opc200-install.sh`。
