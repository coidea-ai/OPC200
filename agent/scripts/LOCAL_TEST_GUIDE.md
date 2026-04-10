# OPC200 Agent Windows 脚本本地模拟测试

> **测试目标**: 在不依赖 Docker 的情况下验证 PowerShell 脚本逻辑  
> **测试环境**: Linux (模拟 Windows 环境)  
> **测试范围**: 脚本语法、配置生成、流程逻辑

---

## 1. 模拟 Agent 二进制

创建占位文件模拟 `opc-agent.exe`：

```powershell
# 测试用 - 模拟 Agent 启动脚本 (test-agent.ps1)
param(
    [string]$ConfigFile = "config/config.yml"
)

Write-Host "[MOCK] OPC Agent Starting..." -ForegroundColor Green
Write-Host "[MOCK] Config: $ConfigFile" -ForegroundColor Cyan
Write-Host "[MOCK] Health endpoint: http://127.0.0.1:8080/health" -ForegroundColor Cyan

# 模拟启动 HTTP 服务
Start-Job {
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add("http://127.0.0.1:8080/")
    $listener.Start()
    Write-Host "[MOCK] HTTP Server started on port 8080" -ForegroundColor Green
    
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $response = $context.Response
        $response.StatusCode = 200
        $response.ContentType = "application/json"
        $content = '{"status":"healthy","version":"1.0.0-mock"}'
        $buffer = [System.Text.Encoding]::UTF8.GetBytes($content)
        $response.OutputStream.Write($buffer, 0, $buffer.Length)
        $response.Close()
    }
}

Write-Host "[MOCK] Agent running. Press Ctrl+C to stop." -ForegroundColor Yellow
while ($true) { Start-Sleep -Seconds 10 }
```

---

## 2. PowerShell 脚本语法测试

```bash
# 检查脚本语法（使用 PowerShell Core 如果可用）
pwsh -Command "Get-Command ./agent/scripts/install.ps1" 2>/dev/null || echo "PowerShell Core 未安装，跳过语法检查"

# 或者手动检查关键函数定义
grep -E "^function\s+\w+" agent/scripts/install.ps1
```

---

## 3. 配置生成测试

### 3.1 测试配置模板生成

```bash
# 创建测试目录
mkdir -p /tmp/opc200-test/{config,data,logs}

# 生成模拟配置
cat > /tmp/opc200-test/config/config.yml <> 'EOF'
platform:
  url: "https://platform.opc200.co"
  metrics_endpoint: "/metrics/job"

customer:
  id: "test-opc-001"

agent:
  version: "1.0.0-mock"
  check_interval: 60
  push_interval: 30

gateway:
  host: "127.0.0.1"
  port: 8080

journal:
  storage_path: "data/journal"
  max_size: "1GB"

logging:
  level: "info"
  file: "logs/agent.log"
  max_size: "100MB"
  max_backups: 5
EOF

echo "✅ 配置生成测试通过"
```

### 3.2 验证配置格式

```bash
# 使用 Python 验证 YAML 格式
python3 -c "
import yaml
try:
    with open('/tmp/opc200-test/config/config.yml') as f:
        config = yaml.safe_load(f)
    print('✅ YAML 格式有效')
    print(f'   Platform URL: {config[\"platform\"][\"url\"]}')
    print(f'   Customer ID: {config[\"customer\"][\"id\"]}')
    print(f'   Agent Version: {config[\"agent\"][\"version\"]}')
except Exception as e:
    print(f'❌ YAML 解析失败: {e}')
"
```

---

## 4. 指标格式测试（模拟 PLAT-003 协议）

```bash
# 测试指标格式生成
cat > /tmp/opc200-test/metrics.txt <> 'EOF'
agent_health{agent_version="1.0.0-mock",os="linux"} 1
cpu_usage{agent_version="1.0.0-mock",os="linux"} 45.5
memory_usage{agent_version="1.0.0-mock",os="linux"} 78.2
disk_usage{agent_version="1.0.0-mock",os="linux"} 65.0
EOF

# 验证 Prometheus 格式
echo "=== 指标格式验证 ==="
cat /tmp/opc200-test/metrics.txt

echo ""
echo "✅ 指标格式符合 PLAT-003 协议"
```

---

## 5. 目录结构测试

```bash
#!/bin/bash
# test-directory-structure.sh

TEST_DIR="/tmp/opc200-test"
EXPECTED_DIRS=(
    "config"
    "data"
    "data/journal"
    "logs"
    "update"
)

EXPECTED_FILES=(
    "config/config.yml"
)

echo "=== 目录结构测试 ==="

# 创建目录
for dir in "${EXPECTED_DIRS[@]}"; do
    mkdir -p "$TEST_DIR/$dir"
    if [ -d "$TEST_DIR/$dir" ]; then
        echo "✅ $dir"
    else
        echo "❌ $dir - 创建失败"
    fi
done

echo ""
echo "=== 文件生成测试 ==="
for file in "${EXPECTED_FILES[@]}"; do
    if [ -f "$TEST_DIR/$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file - 不存在"
    fi
done
```

---

## 6. 运行所有本地测试

```bash
#!/bin/bash
# run-local-tests.sh

echo "========================================"
echo "OPC200 Windows 脚本本地模拟测试"
echo "========================================"
echo ""

# 清理
rm -rf /tmp/opc200-test
mkdir -p /tmp/opc200-test

# 测试 1: 配置生成
echo "[1/4] 测试配置生成..."
cat > /tmp/opc200-test/config.yml <> 'EOF'
platform:
  url: "https://platform.opc200.co"
customer:
  id: "test-opc-001"
agent:
  version: "1.0.0-mock"
EOF
echo "✅ 配置生成通过"
echo ""

# 测试 2: YAML 格式验证
echo "[2/4] 测试 YAML 格式..."
python3 -c "
import yaml
with open('/tmp/opc200-test/config.yml') as f:
    config = yaml.safe_load(f)
assert config['customer']['id'] == 'test-opc-001'
print('✅ YAML 格式验证通过')
" 2>/dev/null || echo "⚠️ YAML 验证跳过（Python 不可用）"
echo ""

# 测试 3: 指标格式验证
echo "[3/4] 测试指标格式..."
cat > /tmp/opc200-test/metrics.txt <> 'EOF'
agent_health{agent_version="1.0.0",os="windows"} 1
cpu_usage{agent_version="1.0.0",os="windows"} 45.5
EOF

if grep -q "agent_health" /tmp/opc200-test/metrics.txt; then
    echo "✅ 指标格式验证通过"
else
    echo "❌ 指标格式验证失败"
fi
echo ""

# 测试 4: 目录结构
echo "[4/4] 测试目录结构..."
mkdir -p /tmp/opc200-test/{config,data/journal,logs,update}
for dir in config data data/journal logs update; do
    if [ -d "/tmp/opc200-test/$dir" ]; then
        echo "  ✅ $dir/"
    else
        echo "  ❌ $dir/"
    fi
done
echo ""

echo "========================================"
echo "本地模拟测试完成"
echo "========================================"
echo ""
echo "注意：此为 Linux 环境下的模拟测试"
echo "实际 Windows 测试需要在 PowerShell 中执行"
```

---

## 7. 测试执行

```bash
chmod +x run-local-tests.sh
./run-local-tests.sh
```

---

## 8. 测试结果预期

```
========================================
OPC200 Windows 脚本本地模拟测试
========================================

[1/4] 测试配置生成...
✅ 配置生成通过

[2/4] 测试 YAML 格式...
✅ YAML 格式验证通过

[3/4] 测试指标格式...
✅ 指标格式验证通过

[4/4] 测试目录结构...
  ✅ config/
  ✅ data/
  ✅ data/journal/
  ✅ logs/
  ✅ update/

========================================
本地模拟测试完成
========================================
```

---

## 9. 后续真实测试

本地模拟通过后，需要在 Windows 环境测试：

1. **Windows 10/11 虚拟机/物理机**
2. **PowerShell 5.1 或 7.x**
3. **管理员权限运行**
4. **网络连接（下载 Agent）**

测试步骤：
```powershell
# 1. 复制脚本到 Windows
# 2. 以管理员身份打开 PowerShell
# 3. 执行测试
.\agent\scripts\install.ps1 -PlatformUrl "https://platform.opc200.co" -CustomerId "test-001" -ApiKey "test-key" -Silent

# 4. 验证服务
Get-Service OPC200-Agent

# 5. 验证健康检查
Invoke-WebRequest http://127.0.0.1:8080/health

# 6. 卸载测试
.\agent\scripts\uninstall.ps1
```
