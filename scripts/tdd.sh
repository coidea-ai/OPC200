#!/bin/bash
# TDD 快捷脚本
# 使用: ./scripts/tdd.sh [red|green|refactor|coverage|watch]

set -e

SKILLS_DIR="skills/opc-journal"
COVERAGE_THRESHOLD=80

case "${1:-help}" in
    red)
        echo "🔴 TDD Red Phase: Write failing test"
        echo "   Running tests (expecting failures)..."
        cd "$SKILLS_DIR"
        pytest tests/ -v --tb=short || echo "   ✓ Tests failed as expected (Red phase)"
        ;;
    green)
        echo "🟢 TDD Green Phase: Make tests pass"
        echo "   Running tests (expecting success)..."
        cd "$SKILLS_DIR"
        pytest tests/ -v
        echo "   ✓ All tests passed (Green phase)"
        ;;
    refactor)
        echo "🔵 TDD Refactor Phase: Clean up code"
        echo "   Running tests to ensure nothing broke..."
        cd "$SKILLS_DIR"
        pytest tests/ -v
        echo "   ✓ Refactor complete, all tests still passing"
        ;;
    coverage)
        echo "📊 Checking coverage (threshold: ${COVERAGE_THRESHOLD}%)..."
        cd "$SKILLS_DIR"
        pytest tests/ --cov=. --cov-fail-under=$COVERAGE_THRESHOLD -v
        echo "   ✓ Coverage meets threshold"
        ;;
    watch)
        echo "👁️  Watch mode: Running tests on file changes..."
        cd "$SKILLS_DIR"
        if command -v ptw &> /dev/null; then
            ptw -- -v
        else
            echo "   Installing pytest-watch..."
            pip install pytest-watch
            ptw -- -v
        fi
        ;;
    quick)
        echo "⚡ Quick test run..."
        cd "$SKILLS_DIR"
        pytest tests/ -x -q --tb=line
        echo "   ✓ Quick check passed"
        ;;
    all)
        echo "🧪 Running all skills tests..."
        cd "$SKILLS_DIR"
        pytest tests/ -v --cov=. --cov-report=term
        echo "   ✓ All tests passed"
        ;;
    help|*)
        echo "TDD 快捷脚本"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  red       🔴 Run tests (Red phase - expect failures)"
        echo "  green     🟢 Run tests (Green phase - expect success)"
        echo "  refactor  🔵 Verify refactor didn't break tests"
        echo "  coverage  📊 Check coverage meets threshold"
        echo "  watch     👁️  Run tests on file changes"
        echo "  quick     ⚡ Quick test run (fail fast)"
        echo "  all       🧪 Run all skill tests"
        echo "  help      📖 Show this help"
        echo ""
        echo "TDD Workflow:"
        echo "  1. Write failing test"
        echo "  2. $0 red      (verify test fails)"
        echo "  3. Write code to make it pass"
        echo "  4. $0 green    (verify test passes)"
        echo "  5. Refactor code"
        echo "  6. $0 refactor (verify still passes)"
        echo "  7. $0 coverage (check coverage)"
        ;;
esac
