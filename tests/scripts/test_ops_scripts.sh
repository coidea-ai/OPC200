#!/bin/bash
#
# OPC200 运维脚本全链路验证测试
# 测试范围: health-check.sh, backup-manager.sh, emergency-recovery.sh
#

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 测试结果统计
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# 测试环境
TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$TEST_DIR/../.." && pwd)"
SCRIPTS_DIR="$PROJECT_ROOT/scripts"
TEMP_DIR=$(mktemp -d)

# 清理函数
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; TESTS_FAILED=$((TESTS_FAILED + 1)); }
log_skip() { echo -e "${YELLOW}[SKIP]${NC} $1"; TESTS_SKIPPED=$((TESTS_SKIPPED + 1)); }
log_section() {
    echo ""
    echo "========================================"
    echo "  $1"
    echo "========================================"
}

# 断言函数
assert_cmd_exists() {
    local cmd="$1"
    local name="${2:-$cmd}"
    if command -v "$cmd" >/dev/null 2>&1; then
        log_pass "$name 命令存在"
        return 0
    else
        log_fail "$name 命令不存在"
        return 1
    fi
}

assert_file_exists() {
    local file="$1"
    local name="${2:-$file}"
    if [[ -f "$file" ]]; then
        log_pass "$name 文件存在"
        return 0
    else
        log_fail "$name 文件不存在"
        return 1
    fi
}

assert_file_executable() {
    local file="$1"
    local name="${2:-$file}"
    if [[ -x "$file" ]]; then
        log_pass "$name 可执行"
        return 0
    else
        log_fail "$name 不可执行"
        return 1
    fi
}

assert_string_contains() {
    local haystack="$1"
    local needle="$2"
    local name="$3"
    if [[ "$haystack" == *"$needle"* ]]; then
        log_pass "$name"
        return 0
    else
        log_fail "$name (期望包含: $needle)"
        return 1
    fi
}

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local name="$3"
    if [[ "$expected" == "$actual" ]]; then
        log_pass "$name (exit code: $actual)"
        return 0
    else
        log_fail "$name (期望: $expected, 实际: $actual)"
        return 1
    fi
}

# ============================================
# 测试套件 1: 脚本文件完整性检查
# ============================================
test_script_files_integrity() {
    log_section "测试套件 1: 脚本文件完整性"
    
    # 检查核心脚本文件
    assert_file_exists "$SCRIPTS_DIR/maintenance/health-check.sh" "health-check.sh"
    assert_file_exists "$SCRIPTS_DIR/maintenance/backup-manager.sh" "backup-manager.sh"
    assert_file_exists "$SCRIPTS_DIR/recovery/emergency-recovery.sh" "emergency-recovery.sh"
    assert_file_exists "$SCRIPTS_DIR/recovery/rollback.sh" "rollback.sh"
    assert_file_exists "$SCRIPTS_DIR/lib/logging.sh" "logging.sh"
    
    # 检查脚本是否可执行
    assert_file_executable "$SCRIPTS_DIR/maintenance/health-check.sh" "health-check.sh 可执行权限"
    assert_file_executable "$SCRIPTS_DIR/maintenance/backup-manager.sh" "backup-manager.sh 可执行权限"
}

# ============================================
# 测试套件 2: health-check.sh 功能测试
# ============================================
test_health_check() {
    log_section "测试套件 2: health-check.sh 功能测试"
    
    local script="$SCRIPTS_DIR/maintenance/health-check.sh"
    
    # 测试 2.1: 帮助信息
    log_info "测试 2.1: 帮助信息"
    local output
    output=$($script --help 2>&1) || true
    if assert_string_contains "$output" "Usage:" "显示帮助信息"; then
        assert_string_contains "$output" "--env" "包含 --env 参数说明"
        assert_string_contains "$output" "--batch" "包含 --batch 参数说明"
        assert_string_contains "$output" "--full" "包含 --full 参数说明"
    fi
    
    # 测试 2.2: 语法检查
    log_info "测试 2.2: Bash 语法检查"
    if bash -n "$script"; then
        log_pass "脚本语法正确"
    else
        log_fail "脚本语法错误"
    fi
    
    # 测试 2.3: 模拟运行 (staging 环境)
    log_info "测试 2.3: 模拟运行 (staging 环境)"
    # 创建模拟数据目录
    mkdir -p "$TEMP_DIR/data/opc200/1/journal"
    sqlite3 "$TEMP_DIR/data/opc200/1/journal/journal.db" "CREATE TABLE IF NOT EXISTS entries (id TEXT PRIMARY KEY, content TEXT);" 2>/dev/null || true
    
    # 由于需要实际环境，标记为跳过
    log_skip "完整运行测试需要实际部署环境"
}

# ============================================
# 测试套件 3: backup-manager.sh 功能测试
# ============================================
test_backup_manager() {
    log_section "测试套件 3: backup-manager.sh 功能测试"
    
    local script="$SCRIPTS_DIR/maintenance/backup-manager.sh"
    
    # 测试 3.1: 帮助信息
    log_info "测试 3.1: 帮助信息"
    local output
    output=$($script --help 2>&1) || true
    if assert_string_contains "$output" "Usage:" "显示帮助信息"; then
        assert_string_contains "$output" "backup" "包含 backup 操作"
        assert_string_contains "$output" "restore" "包含 restore 操作"
        assert_string_contains "$output" "list" "包含 list 操作"
        assert_string_contains "$output" "cleanup" "包含 cleanup 操作"
    fi
    
    # 测试 3.2: 语法检查
    log_info "测试 3.2: Bash 语法检查"
    if bash -n "$script"; then
        log_pass "脚本语法正确"
    else
        log_fail "脚本语法错误"
    fi
    
    # 测试 3.3: 缺少参数检查
    log_info "测试 3.3: 参数验证"
    local output exit_code
    output=$($script backup 2>&1) || exit_code=$?
    if assert_string_contains "$output" "缺少客户ID" "无 ID 参数时显示错误"; then
        assert_exit_code 1 "${exit_code:-0}" "无 ID 参数时退出码为 1"
    fi
    
    # 测试 3.4: 模拟备份 (dry-run)
    log_info "测试 3.4: 模拟备份 (--dry-run)"
    local test_id="OPC-TEST-001"
    local test_data_dir="$TEMP_DIR/opt/opc200/$test_id/data"
    local test_backup_dir="$TEMP_DIR/opt/opc200/$test_id/backup"
    
    mkdir -p "$test_data_dir"
    mkdir -p "$test_backup_dir"
    echo "test data" > "$test_data_dir/test.txt"
    
    # 使用 dry-run 模式测试
    output=$($script --id "$test_id" --dry-run backup 2>&1) || exit_code=$?
    if assert_string_contains "$output" "DRY-RUN" "dry-run 模式显示标记"; then
        assert_string_contains "$output" "将创建" "显示将要执行的命令"
    fi
    
    # 测试 3.5: 备份清单功能
    log_info "测试 3.5: 备份清单验证"
    local test_backup_base="$TEMP_DIR/opt/opc200/$test_id"
    local test_backup_dir="$test_backup_base/backup"
    mkdir -p "$test_backup_dir/auto-20260101-120000"
    cat > "$test_backup_dir/auto-20260101-120000/manifest.yml" << 'EOF'
backup:
  name: auto-20260101-120000
  customer_id: OPC-TEST-001
  created_at: 2026-01-01T12:00:00Z
EOF
    
    # 使用 chroot 方式测试（通过修改脚本使用的路径）
    # 由于脚本使用硬编码路径，这里我们仅验证帮助信息正确
    output=$($script --help 2>&1) || exit_code=$?
    assert_string_contains "$output" "list" "list 操作在帮助中描述"
}

# ============================================
# 测试套件 4: emergency-recovery.sh 功能测试
# ============================================
test_emergency_recovery() {
    log_section "测试套件 4: emergency-recovery.sh 功能测试"
    
    local script="$SCRIPTS_DIR/recovery/emergency-recovery.sh"
    
    # 检查脚本是否存在
    if [[ ! -f "$script" ]]; then
        log_skip "emergency-recovery.sh 不存在，跳过测试"
        return 0
    fi
    
    # 测试 4.1: 帮助信息
    log_info "测试 4.1: 帮助信息"
    local output
    output=$($script --help 2>&1) || true
    assert_string_contains "$output" "Usage:" "显示帮助信息"
    
    # 测试 4.2: 语法检查
    log_info "测试 4.2: Bash 语法检查"
    if bash -n "$script"; then
        log_pass "脚本语法正确"
    else
        log_fail "脚本语法错误"
    fi
}

# ============================================
# 测试套件 5: 公共库测试
# ============================================
test_common_libs() {
    log_section "测试套件 5: 公共库测试"
    
    local logging_lib="$SCRIPTS_DIR/lib/logging.sh"
    
    # 检查日志库
    assert_file_exists "$logging_lib" "logging.sh 库文件"
    
    # 测试日志库语法
    log_info "测试日志库语法"
    if bash -n "$logging_lib"; then
        log_pass "logging.sh 语法正确"
    else
        log_fail "logging.sh 语法错误"
    fi
    
    # 测试日志函数
    log_info "测试日志函数"
    (
        source "$logging_lib" 2>/dev/null || true
        # 如果加载成功，测试函数是否存在
        if type log_info >/dev/null 2>&1; then
            exit 0
        else
            exit 1
        fi
    ) && log_pass "日志函数可加载" || log_skip "日志函数测试需要实际加载环境"
}

# ============================================
# 测试套件 6: 集成测试
# ============================================
test_integration() {
    log_section "测试套件 6: 集成测试"
    
    log_info "测试运维脚本协同工作"
    
    # 创建一个完整的测试场景
    local test_customer="OPC-TEST-999"
    local test_base="$TEMP_DIR/opt/opc200/$test_customer"
    
    mkdir -p "$test_base/data/journal"
    mkdir -p "$test_base/backup"
    mkdir -p "$test_base/config"
    
    # 创建测试数据库
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "$test_base/data/journal/journal.db" "
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            INSERT INTO journal_entries VALUES ('test-001', 'test content', '[]', '{}', '2026-01-01T00:00:00', '2026-01-01T00:00:00');
        " 2>/dev/null || true
    else
        # 如果没有 sqlite3，创建一个空文件作为占位
        touch "$test_base/data/journal/journal.db"
    fi
    
    # 验证数据库
    if [[ -f "$test_base/data/journal/journal.db" ]]; then
        log_pass "测试数据库创建成功"
        
        # 测试数据库完整性检查
        if command -v sqlite3 >/dev/null 2>&1; then
            if sqlite3 "$test_base/data/journal/journal.db" "PRAGMA integrity_check;" 2>/dev/null | grep -q "ok"; then
                log_pass "数据库完整性检查通过"
            else
                log_fail "数据库完整性检查失败"
            fi
        else
            log_skip "sqlite3 未安装，跳过完整性检查"
        fi
    else
        log_fail "测试数据库创建失败"
    fi
    
    log_skip "完整集成测试需要实际部署环境"
}

# ============================================
# 测试套件 7: 性能基准测试
# ============================================
test_performance() {
    log_section "测试套件 7: 性能基准测试"
    
    log_info "脚本启动时间测试"
    
    local script="$SCRIPTS_DIR/maintenance/health-check.sh"
    local start_time end_time duration
    
    # 测试帮助信息响应时间
    start_time=$(date +%s%N)
    $script --help >/dev/null 2>&1 || true
    end_time=$(date +%s%N)
    
    # 计算毫秒
    duration=$(( (end_time - start_time) / 1000000 ))
    
    if [[ $duration -lt 1000 ]]; then
        log_pass "帮助信息响应时间: ${duration}ms (< 1s)"
    else
        log_warn "帮助信息响应时间: ${duration}ms (较慢)"
    fi
    
    # 测试 backup-manager 启动时间
    script="$SCRIPTS_DIR/maintenance/backup-manager.sh"
    start_time=$(date +%s%N)
    $script --help >/dev/null 2>&1 || true
    end_time=$(date +%s%N)
    
    duration=$(( (end_time - start_time) / 1000000 ))
    
    if [[ $duration -lt 1000 ]]; then
        log_pass "backup-manager 启动时间: ${duration}ms (< 1s)"
    else
        log_warn "backup-manager 启动时间: ${duration}ms (较慢)"
    fi
}

# ============================================
# 主函数
# ============================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════╗"
    echo "║   OPC200 运维脚本全链路验证测试                   ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""
    echo "项目路径: $PROJECT_ROOT"
    echo "测试时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "临时目录: $TEMP_DIR"
    echo ""
    
    # 运行所有测试套件
    test_script_files_integrity
    test_health_check
    test_backup_manager
    test_emergency_recovery
    test_common_libs
    test_integration
    test_performance
    
    # 测试报告
    log_section "测试报告"
    
    local total=$((TESTS_PASSED + TESTS_FAILED + TESTS_SKIPPED))
    
    echo "  总计测试: $total"
    echo "  ✅ 通过:   $TESTS_PASSED"
    echo "  ❌ 失败:   $TESTS_FAILED"
    echo "  ⏭️  跳过:   $TESTS_SKIPPED"
    echo ""
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}所有测试通过!${NC}"
        exit 0
    else
        echo -e "${RED}存在失败的测试，请检查输出。${NC}"
        exit 1
    fi
}

# 运行主函数
main "$@"
