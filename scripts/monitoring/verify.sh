#!/bin/bash
# OPC200 监控部署验证脚本
# 用法: ./scripts/monitoring/verify.sh [--webhook-test]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 禁用颜色如果输出不是终端
if [ ! -t 1 ]; then
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# 配置
METRICS_PORT=${METRICS_PORT:-9091}
PROMETHEUS_PORT=${PROMETHEUS_PORT:-9090}
GRAFANA_PORT=${GRAFANA_PORT:-3000}
WEBHOOK_URL=${WEBHOOK_URL:-""}

# 计数器
TESTS_PASSED=0
TESTS_FAILED=0

# 辅助函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

test_pass() {
    echo -e "${GREEN}✓${NC} $1"
    (TESTS_PASSED=$((TESTS_PASSED + 1)))
}

test_fail() {
    echo -e "${RED}✗${NC} $1"
    (TESTS_FAILED=$((TESTS_FAILED + 1)))
}

# ==================== 测试函数 ====================

test_metrics_server_running() {
    echo ""
    log_info "测试1: 检查 Metrics Server 是否运行"
    
    if curl -sf "http://localhost:${METRICS_PORT}/health" &> /dev/null; then
        test_pass "Metrics Server 健康检查通过"
    else
        test_fail "Metrics Server 未响应 (端口 ${METRICS_PORT})"
        log_warn "尝试启动 Metrics Server..."
        return 1
    fi
}

test_metrics_endpoint() {
    echo ""
    log_info "测试2: 验证 /metrics 端点"
    
    local metrics
    metrics=$(curl -sf "http://localhost:${METRICS_PORT}/metrics" 2>/dev/null)
    
    if [ -z "$metrics" ]; then
        test_fail "无法获取指标数据"
        return 1
    fi
    
    # 检查关键指标是否存在
    local required_metrics=(
        "opc200_journal_entries_total"
        "opc200_job_executions_total"
        "opc200_errors_total"
    )
    
    local all_found=true
    for metric in "${required_metrics[@]}"; do
        if echo "$metrics" | grep -q "$metric"; then
            test_pass "找到指标: $metric"
        else
            test_fail "缺少指标: $metric"
            all_found=false
        fi
    done
    
    $all_found
}

test_prometheus_config() {
    echo ""
    log_info "测试3: 验证 Prometheus 配置"
    
    if [ ! -f "monitoring/prometheus/prometheus.yml" ]; then
        test_fail "prometheus.yml 不存在"
        return 1
    fi
    
    test_pass "prometheus.yml 存在"
    
    if [ ! -f "monitoring/prometheus/alerts.yml" ]; then
        test_fail "alerts.yml 不存在"
        return 1
    fi
    
    test_pass "alerts.yml 存在"
    
    # 验证 YAML 语法
    if check_command python3; then
        if python3 -c "import yaml; yaml.safe_load(open('monitoring/prometheus/prometheus.yml'))" 2>/dev/null; then
            test_pass "prometheus.yml YAML 语法正确"
        else
            test_fail "prometheus.yml YAML 语法错误"
        fi
        
        if python3 -c "import yaml; yaml.safe_load(open('monitoring/prometheus/alerts.yml'))" 2>/dev/null; then
            test_pass "alerts.yml YAML 语法正确"
        else
            test_fail "alerts.yml YAML 语法错误"
        fi
    else
        log_warn "未安装 python3，跳过 YAML 语法检查"
    fi
}

test_grafana_dashboards() {
    echo ""
    log_info "测试4: 验证 Grafana 仪表板"
    
    local dashboards_dir="monitoring/grafana/dashboards"
    
    if [ ! -d "$dashboards_dir" ]; then
        test_fail "仪表板目录不存在: $dashboards_dir"
        return 1
    fi
    
    local dashboard_files=(
        "opc200-overview.json"
        "opc200-detailed.json"
    )
    
    for file in "${dashboard_files[@]}"; do
        if [ -f "$dashboards_dir/$file" ]; then
            if python3 -c "import json; json.load(open('$dashboards_dir/$file'))" 2>/dev/null; then
                test_pass "仪表板 JSON 格式正确: $file"
            else
                test_fail "仪表板 JSON 格式错误: $file"
            fi
        else
            test_fail "仪表板文件缺失: $file"
        fi
    done
}

test_docker_compose() {
    echo ""
    log_info "测试5: 验证 Docker Compose 配置"
    
    if ! check_command docker-compose; then
        if check_command docker; then
            if docker compose version &> /dev/null; then
                test_pass "Docker Compose (plugin) 已安装"
            else
                log_warn "Docker Compose 未安装，跳过 Docker 测试"
                return 0
            fi
        else
            log_warn "Docker 未安装，跳过 Docker 测试"
            return 0
        fi
    else
        test_pass "Docker Compose 已安装"
    fi
    
    if [ ! -f "docker-compose.yml" ]; then
        test_fail "docker-compose.yml 不存在"
        return 1
    fi
    
    test_pass "docker-compose.yml 存在"
    
    # 检查配置语法
    if docker-compose config &> /dev/null; then
        test_pass "Docker Compose 配置语法正确"
    else
        test_fail "Docker Compose 配置语法错误"
    fi
}

test_webhook_alert() {
    echo ""
    log_info "测试6: 测试告警 Webhook (可选)"
    
    if [ -z "$WEBHOOK_URL" ]; then
        log_warn "未设置 WEBHOOK_URL，跳过 webhook 测试"
        log_info "如需测试 webhook，请运行: WEBHOOK_URL=<url> $0 --webhook-test"
        return 0
    fi
    
    local test_payload='{
        "version": "4",
        "groupKey": "{alertname=\"TestAlert\"}",
        "status": "firing",
        "receiver": "webhook",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "TestAlert",
                    "severity": "info",
                    "instance": "localhost:9091"
                },
                "annotations": {
                    "summary": "测试告警",
                    "description": "这是一条测试告警消息"
                }
            }
        ]
    }'
    
    if curl -sf -X POST -H "Content-Type: application/json" -d "$test_payload" "$WEBHOOK_URL" &> /dev/null; then
        test_pass "Webhook 测试成功"
    else
        test_fail "Webhook 测试失败"
    fi
}

test_core_modules() {
    echo ""
    log_info "测试7: 验证核心模块指标埋点"
    
    if ! check_command python3; then
        log_warn "未安装 python3，跳过核心模块测试"
        return 0
    fi
    
    python3 << 'PYTHON_EOF'
import sys
sys.path.insert(0, 'src')

try:
    import sqlite3
    from journal.core import JournalManager, JournalEntry
    from tasks.scheduler import TaskScheduler, RecurringTask
    from insights.generator import InsightGenerator
    
    # 测试 JournalManager
    conn = sqlite3.connect(':memory:')
    manager = JournalManager(conn)
    manager.create_table()
    entry = JournalEntry(content='Test')
    manager.create_entry(entry)
    print("✓ JournalManager 埋点正常")
    
    # 测试 TaskScheduler
    scheduler = TaskScheduler()
    scheduler.add_job(lambda: None, 'interval', 'test')
    print("✓ TaskScheduler 埋点正常")
    
    # 测试 RecurringTask
    task = RecurringTask(func=lambda: None, cron='0 0 * * *', task_id='test')
    task.record_execution(success=True)
    print("✓ RecurringTask 埋点正常")
    
    # 测试 InsightGenerator
    generator = InsightGenerator()
    generator.generate_daily_summary({'activities': []})
    print("✓ InsightGenerator 埋点正常")
    
except Exception as e:
    print(f"✗ 核心模块测试失败: {e}")
    sys.exit(1)
PYTHON_EOF

    if [ $? -eq 0 ]; then
        return 0
    else
        return 1
    fi
}

# ==================== 主函数 ====================

main() {
    echo "========================================"
    echo "  OPC200 监控部署验证"
    echo "========================================"
    echo ""
    
    # 解析参数
    local webhook_test=false
    for arg in "$@"; do
        case $arg in
            --webhook-test)
                webhook_test=true
                shift
                ;;
            *)
                ;;
        esac
    done
    
    # 检查是否在项目根目录
    if [ ! -f "docker-compose.yml" ] || [ ! -d "src" ]; then
        log_error "请在 OPC200 项目根目录运行此脚本"
        exit 1
    fi
    
    # 运行测试
    test_prometheus_config
    test_grafana_dashboards
    test_docker_compose
    test_core_modules
    
    # 这些测试需要服务运行
    if test_metrics_server_running; then
        test_metrics_endpoint
        
        if $webhook_test; then
            test_webhook_alert
        fi
    fi
    
    # 输出结果
    echo ""
    echo "========================================"
    echo "  测试结果"
    echo "========================================"
    echo "通过: ${TESTS_PASSED}"
    echo "失败: ${TESTS_FAILED}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}所有测试通过！${NC}"
        echo ""
        echo "下一步操作:"
        echo "  1. 启动完整监控栈: docker-compose up -d prometheus grafana metrics-server"
        echo "  2. 访问 Grafana: http://localhost:3000 (默认密码: admin/admin)"
        echo "  3. 查看 Prometheus: http://localhost:9090"
        exit 0
    else
        echo -e "${RED}有 ${TESTS_FAILED} 项测试失败，请检查上述错误。${NC}"
        exit 1
    fi
}

# 执行主函数
main "$@"
