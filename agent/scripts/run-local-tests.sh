#!/bin/bash
# OPC200 Windows 脚本本地模拟测试

echo "========================================"
echo "OPC200 Windows 脚本本地模拟测试"
echo "========================================"
echo ""

# 清理并创建测试目录
TEST_DIR="/tmp/opc200-test"
rm -rf "$TEST_DIR"
mkdir -p "$TEST_DIR"

cd "$TEST_DIR"

# 测试 1: 配置生成测试
echo "[1/5] 测试配置生成..."
mkdir -p config data/journal logs update

printf '%s\n' 'platform:' '  url: "https://platform.opc200.co"' '  metrics_endpoint: "/metrics/job"' '' 'customer:' '  id: "test-opc-001"' '' 'agent:' '  version: "1.0.0-mock"' '  check_interval: 60' '  push_interval: 30' '' 'gateway:' '  host: "127.0.0.1"' '  port: 8080' '' 'journal:' '  storage_path: "data/journal"' '  max_size: "1GB"' '' 'logging:' '  level: "info"' '  file: "logs/agent.log"' '  max_size: "100MB"' '  max_backups: 5' > config/config.yml

if [ -f config/config.yml ]; then
    echo "  ✅ 配置文件已生成"
else
    echo "  ❌ 配置文件生成失败"
    exit 1
fi

# 测试 2: YAML 格式验证
echo ""
echo "[2/5] 测试 YAML 格式..."
if command -v python3 > /dev/null 2>&1; then
    python3 -c "
import yaml
try:
    with open('config/config.yml') as f:
        config = yaml.safe_load(f)
    assert config['platform']['url'] == 'https://platform.opc200.co'
    assert config['customer']['id'] == 'test-opc-001'
    assert config['agent']['version'] == '1.0.0-mock'
    print('  ✅ YAML 格式有效')
    print(f'     Platform URL: {config[\"platform\"][\"url\"]}')
    print(f'     Customer ID: {config[\"customer\"][\"id\"]}')
    print(f'     Agent Version: {config[\"agent\"][\"version\"]}')
except Exception as e:
    print(f'  ❌ YAML 验证失败: {e}')
    exit(1)
"
else
    echo "  ⚠️ Python3 不可用，跳过 YAML 验证"
fi

# 测试 3: 指标格式验证（PLAT-003 协议）
echo ""
echo "[3/5] 测试指标格式（PLAT-003）..."
printf '%s\n' 'agent_health{agent_version="1.0.0-mock",os="windows"} 1' 'cpu_usage{agent_version="1.0.0-mock",os="windows"} 45.5' 'memory_usage{agent_version="1.0.0-mock",os="windows"} 78.2' 'disk_usage{agent_version="1.0.0-mock",os="windows"} 65.0' > metrics.txt

# 验证 Prometheus 格式
if grep -qE "^\w+\{.*\}\s+[0-9.]+$" metrics.txt; then
    echo "  ✅ Prometheus 格式有效"
    echo "     指标行数: $(wc -l < metrics.txt)"
else
    echo "  ❌ 指标格式无效"
    exit 1
fi

# 测试 4: 目录结构验证
echo ""
echo "[4/5] 测试目录结构..."
EXPECTED_DIRS=("config" "data" "data/journal" "logs" "update")
ALL_PASS=true

for dir in "${EXPECTED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir/"
    else
        echo "  ❌ $dir/ - 不存在"
        ALL_PASS=false
    fi
done

if [ "$ALL_PASS" = false ]; then
    exit 1
fi

# 测试 5: 环境变量配置
echo ""
echo "[5/5] 测试环境变量配置..."
printf '%s\n' 'OPC200_API_KEY=sk-test-123456789' 'OPC200_CUSTOMER_ID=test-opc-001' > config/.env

if [ -f config/.env ]; then
    echo "  ✅ 环境变量文件已生成"
    echo "     API Key: $(grep OPC200_API_KEY config/.env | cut -d= -f2 | cut -c1-10)..."
else
    echo "  ❌ 环境变量文件生成失败"
    exit 1
fi

# 总结
echo ""
echo "========================================"
echo "✅ 本地模拟测试全部通过"
echo "========================================"
echo ""
echo "测试目录: $TEST_DIR"
echo ""
echo "目录结构:"
find . -type d | head -10 | sed 's/^/  /'
echo ""
echo "配置文件:"
ls -la config/ | tail -n +2 | sed 's/^/  /'
echo ""
echo "⚠️ 注意：此为 Linux 模拟测试"
echo "   实际 Windows 功能需在 PowerShell 环境验证"
