# Remi Lite - 极简记忆系统

> **⚠️ DEPRECATED**: 此 Skill 已于 2026-04-10 被标记为废弃。
> 
> **原因**: OpenClaw v2026.4.9+ 的原生 dreaming、REM backfill、结构化 diary view 和 `/tasks` 面板已完全覆盖 Remi Lite 的所有功能。
> 
> **替代方案**: 直接使用 OpenClaw 内置的 `memory/YYYY-MM-DD.md`、`dreams.md`、sqlite-vec 搜索和 Task Flow。
> 
> 本目录仅保留作为历史参考，新用户请勿安装。

---

## 概述（历史存档）

Remi Lite 是 OPC200 项目的轻量级记忆 skill，只做三件事：
1. **自动总结** - 对话中自动记录有价值的内容
2. **引用对话** - 自然语言查询历史记忆
3. **备份导入** - 简单的导出/恢复

## 设计原则

- **诚实**: 不做过度设计，承认 OpenClaw session 已解决 80% 问题
- **极简**: 3 层存储（sessions/digests/exports），无复杂压缩
- **实用**: 用户只说"记录"、"之前怎么做的"、"备份"即可

## 文件结构

```
opc-remi-lite/
├── SKILL.md              # Skill 文档
├── config.yml            # 配置
├── pyproject.toml        # Python 包配置
├── requirements.txt      # 依赖
├── requirements-test.txt # 测试依赖
├── Makefile             # 构建脚本
├── .github/
│   └── workflows/
│       └── ci.yml       # CI/CD
├── remi_lite/           # 核心代码
│   ├── __init__.py
│   ├── core.py          # 统一入口
│   ├── session.py       # L1: 会话总结
│   ├── recall.py        # L2: 记忆检索
│   ├── backup.py        # L3: 备份导出
│   └── heartbeat.py     # 自动维护
└── tests/               # 测试
    ├── __init__.py
    ├── test_session.py  # 会话总结测试
    ├── test_recall.py   # 检索测试
    ├── test_backup.py   # 备份测试
    └── test_core.py     # 集成测试
```

## 安装

```bash
# 开发安装
cd opc-remi-lite
pip install -e .
pip install -r requirements-test.txt

# 测试
pytest tests/ -v --cov=remi_lite

# 发布到 ClawHub
make publish
```

## 使用

```
用户: 今天完成了数据库优化，从2秒降到200ms
Remi: 👍 记住了

用户: 我数据库怎么优化的？
Remi: 找到了！2026-04-02 你说："完成了数据库优化，从2秒降到200ms"

用户: /remi backup
Remi: 📦 备份已生成：remi-backup-2026-04-02.zip (45KB)
```

## License

MIT - OPC200 Project
