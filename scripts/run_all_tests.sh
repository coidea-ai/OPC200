#!/bin/bash
# 全量测试运行脚本

set -e

echo "🧪 OPC200 全量测试套件"
echo "======================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
PASSED=0
FAILED=0
SKIPPED=0

run_test_suite() {
    local name="$1"
    local path="$2"
    local extra_args="${3:-}"
    
    echo "📦 运行: $name"
    echo "------------------------------"
    
    if [ -d "$path" ]; then
        if pytest "$path" -v --tb=short $extra_args 2>&1; then
            echo -e "${GREEN}✅ $name 通过${NC}"
            PASSED=$((PASSED + 1))
        else
            echo -e "${RED}❌ $name 失败${NC}"
            FAILED=$((FAILED + 1))
        fi
    else
        echo -e "${YELLOW}⚠️  $name 目录不存在，跳过${NC}"
        SKIPPED=$((SKIPPED + 1))
    fi
    echo ""
}

# 1. 单元测试
run_test_suite "单元测试" "tests/unit" "--cov=src --cov-report=term-missing"

# 2. 集成测试
run_test_suite "集成测试" "tests/integration" "--timeout=120"

# 3. Skills测试
echo "📦 运行: Skills测试"
echo "------------------------------"
if [ -d "skills/opc-journal" ]; then
    cd skills/opc-journal
    if pytest tests/ -v --tb=short; then
        echo -e "${GREEN}✅ Skills测试通过${NC}"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ Skills测试失败${NC}"
        FAILED=$((FAILED + 1))
    fi
    cd ../..
else
    echo -e "${YELLOW}⚠️  Skills目录不存在${NC}"
    SKIPPED=$((SKIPPED + 1))
fi
echo ""

# 4. E2E测试
run_test_suite "E2E测试" "tests/e2e" "--timeout=300"

# 5. 安全测试
run_test_suite "安全测试" "tests/security"

# 6. 性能测试 (失败不阻塞)
echo "📦 运行: 性能测试"
echo "------------------------------"
if [ -d "tests/performance" ]; then
    pytest tests/performance -v --tb=short 2>&1 || echo -e "${YELLOW}⚠️  性能测试有失败 (非阻塞)${NC}"
else
    echo -e "${YELLOW}⚠️  性能测试目录不存在${NC}"
fi
echo ""

# 汇总
echo "======================"
echo "📊 测试结果汇总"
echo "======================"
echo -e "通过: ${GREEN}$PASSED${NC}"
echo -e "失败: ${RED}$FAILED${NC}"
echo -e "跳过: ${YELLOW}$SKIPPED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ 全量测试通过!${NC}"
    exit 0
else
    echo -e "${RED}❌ 有 $FAILED 个测试套件失败${NC}"
    exit 1
fi
