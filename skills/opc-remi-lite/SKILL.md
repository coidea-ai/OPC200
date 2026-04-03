---
name: opc-remi-lite
description: |
  Remi Lite - 极简个人记忆系统
  
  只做三件事：
  1. 自动总结对话中的有价值内容
  2. 自然语言查询历史记忆
  3. 一键备份/导入
  
  诚实设计：不假装比 OpenClaw 原生机制更聪明

namespace: coidea
version: 0.1.0

user-invocable: true
command-dispatch: tool
tool: coordinate

commands:
  remi:
    description: "主入口"
    examples:
      - "今天完成了原型设计"
      - "我数据库怎么优化的？"
      - "/remi backup"
      - "/remi imports"

metadata:
  openclaw:
    emoji: 🧠
    requires: {}
---

# Remi Lite

> "记住该记住的，忘记该忘记的"

## 功能

### 1. 自动记录

无需命令，对话中自动捕获：
```
你: 今天把登录功能做完了，用了 JWT，挺顺利的
Remi: 👍 记住了
```

### 2. 自然查询

```
你: 我登录功能怎么做的？
Remi: 找到了！2026-04-02 你说：
      "把登录功能做完了，用了 JWT，挺顺利的"
```

### 3. 周报生成

```
你: /remi digest
Remi: 📊 周报已生成: 2026-W13.md

      # 📊 周报 2026-03-30 ~ 2026-04-06
      
      ## 📈 本周概览
      - ✅ 完成 3 项工作
      - ⚠️ 遇到 1 个问题
      - 💡 做出 1 个决定
      
      ## ⭐ 本周亮点
      1. 今天解决了登录问题
      2. 决定用 React 做前端
```

### 4. 数据可视化

```
你: /remi viz
Remi: 📈 可视化报告

      📅 近期动态
      【04-02】
        15:34  今天完成了登录功能
        15:34  刚才优化了数据库查询
        
      📊 活动热力图
           一  二  三  四  五  六  日 
      W13  ·  ·  ·  █  ·  ·  ·
      
      ⏰ 时段分布
      下午   │██████████████████████████│ 5
      
      🏷️ 关键词频率
      数据库 │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│ 1
```

### 5. 备份管理

```
你: /remi backup
Remi: 📦 备份已生成
      文件名: remi-backup-2026-04-02.zip
      大小: 45 KB

你: /remi imports
Remi: 可用备份：
      1. remi-backup-2026-04-02.zip
```

## 存储结构

```
~/.openclaw/customers/{id}/.remi/
├── sessions/
│   └── 2026-04-02.md      # 当天会话记录
├── digests/
│   └── 2026-W14.md        # 周报（心跳自动生成）
└── exports/
    ├── remi-backup-2026-04-02.zip
    └── safety-before-import-*.zip
```

## 配置

```yaml
# config.yml
remi:
  auto_record: true           # 自动记录
  record_signals:             # 触发记录的信号
    - "今天|刚才|完成了"
    - "做了|遇到|解决"
    - "开心|焦虑|困惑"
  retention_days: 365         # 保留天数
  max_session_size_kb: 500    # 单会话文件大小限制
```

## TDD 开发

```bash
# 1. 先写测试
pytest tests/test_session.py -v

# 2. 实现功能
# 3. 测试通过
# 4. 重构优化
make test-coverage
```

## CI/CD

- GitHub Actions 自动测试
- 代码覆盖率 > 80%
- Bandit 安全扫描
- 自动发布到 ClawHub
