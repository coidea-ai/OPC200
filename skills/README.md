# OPC200 Skills 开发指南

## 概述

本文档介绍如何为 OPC200 开发自定义 Skills。

## Skill 结构

一个完整的 Skill 包含：

```
skill-name/
├── SKILL.md              # Skill 定义文档（必需）
├── config.yml            # 默认配置
└── scripts/              # 执行脚本（必需）
    ├── init.py
    └── ...
```

## SKILL.md 格式

```markdown
# skill-name

## Description
简短描述 Skill 的功能。

## Install
\`\`\`bash
clawhub install namespace/skill-name
\`\`\`

## Overview
详细说明 Skill 的功能和使用场景。

## Triggers
- 关键词触发
- 正则匹配

## Scripts
- script1.py: 功能说明

## Configuration
\`\`\`yaml
config_key: default_value
\`\`\`
```

## 开发示例

### 1. 创建目录结构

```bash
mkdir -p skills/my-custom-skill/scripts
touch skills/my-custom-skill/SKILL.md
```

### 2. 编写 SKILL.md

```markdown
# my-custom-skill

## Description
我的自定义 Skill

## Install
\`\`\`bash
clawhub install user/my-custom-skill
\`\`\`

## Overview
这个 Skill 演示如何开发 OPC200 Skills。

## Triggers
- "运行我的技能"
- "my skill"

## Scripts
- run.py: 主执行脚本
```

### 3. 编写脚本

```python
# skills/my-custom-skill/scripts/run.py
def main(context):
    """Main entry point."""
    user_input = context.get("input", "")
    
    # Your logic here
    result = process_input(user_input)
    
    return {
        "status": "success",
        "result": result
    }

def process_input(text):
    return f"Processed: {text}"

if __name__ == "__main__":
    import sys
    import json
    
    context = json.load(sys.stdin)
    output = main(context)
    print(json.dumps(output))
```

### 4. 测试 Skill

```bash
# 本地测试
echo '{"input": "test"}' | python skills/my-custom-skill/scripts/run.py
```

## 发布到 ClawHub

### 1. 打包 Skill

```bash
tar -czf my-custom-skill-v1.0.0.tar.gz skills/my-custom-skill/
```

### 2. 提交到仓库

按照 ClawHub 的指南提交您的 Skill。

## 最佳实践

1. **单一职责**: 一个 Skill 只做一件事
2. **配置化**: 使用 config.yml 管理可配置项
3. **错误处理**: 优雅地处理异常情况
4. **日志记录**: 使用结构化日志记录
5. **版本控制**: 使用语义化版本号

## 版本管理

所有 Skills 应该使用统一的版本号格式：

```
主版本.次版本.修订版本

例如：2.2.0
```

当前项目版本：**2.2.0**

## 调试技巧

```python
# 启用调试日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 模拟上下文
mock_context = {
    "customer_id": "OPC-TEST",
    "input": "测试输入",
    "config": {
        "key": "value"
    }
}
```

## 参考

- [OpenClaw Skills 文档](https://docs.openclaw.ai/skills)
- [OPC200 项目文档](../README.md)
