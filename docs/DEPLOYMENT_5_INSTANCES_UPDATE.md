# OPC200 5实例部署 - 中转站模型配置更新

## 更新说明

本次更新支持使用**中转站 API** (api.apiatlas.com) 替代官方 OpenAI API。

## 主要变更

### 1. 部署脚本增强

**文件**: `scripts/deploy/generate-5-instances.sh`

新增功能:
- 交互式输入中转站 API Key
- 自动生成 `models.json` 配置文件
- Docker Compose 注入模型环境变量
- 新增模型配置测试脚本

### 2. 配置文件结构

每个实例生成以下配置:

```
/opt/opc200/opc-001/
├── docker-compose.yml          # 包含模型环境变量
├── .env                        # 包含 APIATLAS_API_KEY
├── config/
│   ├── models.json            # ⭐ 新增：中转站模型配置
│   └── prometheus.yml
└── ...
```

### 3. models.json 内容

```json
{
  "models": {
    "providers": {
      "custom": {
        "baseUrl": "https://api.apiatlas.com/v1",
        "apiKey": "${APIATLAS_API_KEY}",
        "api": "openai-completions",
        "models": [
          {
            "id": "gemini-3-flash-preview",
            "name": "gemini-3-flash-preview",
            "api": "openai-completions",
            "reasoning": true,
            "input": ["text", "image"],
            "cost": { "input": 0.5, "output": 3 },
            "contextWindow": 100000,
            "maxTokens": 32384
          },
          // ... 其他模型
        ]
      }
    },
    "default": {
      "provider": "custom",
      "model": "gemini-3-flash-preview"
    }
  }
}
```

### 4. 环境变量注入

**docker-compose.yml** 新增:
```yaml
gateway:
  environment:
    - OPENAI_API_KEY=${APIATLAS_API_KEY}
    - OPENAI_BASE_URL=https://api.apiatlas.com/v1
    - DEFAULT_MODEL=gemini-3-flash-preview
  volumes:
    - ./config/models.json:/etc/openclaw/models.json:ro
```

### 5. 验证脚本更新

**文件**: `scripts/deploy/validate-5-instances.py`

新增测试项:
- **测试10**: 模型配置检查
  - 验证 models.json 存在
  - 验证配置格式正确
  - 验证包含 custom provider
  - 验证中转站 URL

## 使用方法

### 方式1: 交互式输入（推荐）

```bash
# 直接运行脚本，会提示输入API Key
bash scripts/deploy/generate-5-instances.sh

# 提示:
# [INFO] 步骤0/6: 配置中转站API...
# 未检测到 APIATLAS_API_KEY 环境变量
# 请输入中转站API Key (不会显示): [输入后回车]
```

### 方式2: 环境变量预设

```bash
# 先设置环境变量
export APIATLAS_API_KEY="sk-xxxxxxxxxx"

# 运行脚本（会自动读取）
bash scripts/deploy/generate-5-instances.sh
```

### 方式3: 空Key部署（纯测试）

```bash
# 直接回车跳过输入，会生成空配置
bash scripts/deploy/generate-5-instances.sh
# 提示: 未提供API Key，将使用空值部署(模型功能不可用)
```

## 部署后验证

```bash
# 1. 查看模型配置
cat /opt/opc200/opc-001/config/models.json

# 2. 测试模型配置
sudo /opt/opc200/test-models.sh

# 3. 完整验证（包含模型配置检查）
python3 scripts/deploy/validate-5-instances.py
```

## 测试脚本输出示例

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
           模型配置测试
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
中转站: https://api.apiatlas.com/v1
默认模型: gemini-3-flash-preview

[opc-001] Gateway:18789
  ✓ 模型配置文件存在
  ✓ 配置已挂载到容器
  ✓ Gateway健康

[opc-002] Gateway:18790
  ✓ 模型配置文件存在
  ✓ 配置已挂载到容器
  ✓ Gateway健康
...
```

## 支持的模型

当前配置包含以下模型:

| 模型 | ID | 输入类型 | 上下文 |
|------|-----|---------|--------|
| Gemini 3 Flash | gemini-3-flash-preview | text, image | 100K |
| GPT 5.2 | gpt-5.2 | text, image | 100K |
| Claude Sonnet 4.6 | claude-sonnet-4-6 | text, image | 128K |
| Gemini 3 Pro | gemini-3-pro-preview | text, image | 128K |

默认使用: **gemini-3-flash-preview**

## 故障排查

### 问题1: 模型配置未生效

**症状**: Gateway 日志显示使用默认 OpenAI 端点

**检查**:
```bash
# 确认配置挂载
docker exec opc-001-gateway cat /etc/openclaw/models.json

# 确认环境变量
docker exec opc-001-gateway env | grep OPENAI
```

**解决**:
```bash
cd /opt/opc200/opc-001
docker-compose restart gateway
```

### 问题2: API Key 无效

**症状**: 模型调用返回 401/403 错误

**检查**:
```bash
# 验证 Key 格式
cat /opt/opc200/opc-001/.env | grep APIATLAS

# 测试直接调用
curl https://api.apiatlas.com/v1/models \
  -H "Authorization: Bearer $APIATLAS_API_KEY"
```

### 问题3: 验证脚本失败

**症状**: "模型配置检查" 测试失败

**检查**:
```bash
# 查看详细错误
python3 scripts/deploy/validate-5-instances.py 2>&1 | grep -A5 "模型配置"

# 手动检查配置
ls -la /opt/opc200/opc-*/config/models.json
```

## 安全注意事项

1. **API Key 保护**:
   - `.env` 和 `models.json` 文件权限设为 600
   - 不要将 Key 提交到 Git
   - 定期轮换 Key

2. **配置隔离**:
   - 每个实例有独立的 models.json
   - 但可以使用相同的 API Key

3. **日志脱敏**:
   - Gateway 日志不会打印完整 API Key
   - 只显示前8位用于识别

## 回退到官方API

如果需要恢复官方 OpenAI:

```bash
# 修改单个实例
cd /opt/opc200/opc-001
vi .env
# 修改:
# OPENAI_API_KEY=sk-your-openai-key
# OPENAI_BASE_URL=https://api.openai.com/v1

# 重启
docker-compose restart gateway journal
```

---

**更新日期**: 2026-04-07  
**版本**: v1.1
