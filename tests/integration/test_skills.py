"""Integration tests for opc-journal skill.

Tests the unified CLI-style skill entry point through OpenClaw context.
"""
import sys
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
_OPC_JOURNAL = BASE_DIR / "skills" / "opc-journal"
_OPC_MAIN = _OPC_JOURNAL / "scripts" / "main.py"

if _OPC_MAIN.is_file():
    sys.path.insert(0, str(_OPC_JOURNAL))
    from scripts.main import main
else:
    main = None  # noqa: F811

pytestmark = pytest.mark.skipif(
    main is None,
    reason="skills/opc-journal/scripts/main.py not in tree",
)


def test_opc_journal_init():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["init", "--day", "1", "--goals", "Ship MVP"]
        }
    })
    assert result["status"] == "success"
    assert result["result"]["initialized"] is True
    assert result["result"]["customer_id"] == "OPC-TEST-001"
    print("✓ opc-journal.init: PASSED")


def test_opc_journal_record():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["record", "Shipped MVP today", "--day", "5"]
        }
    })
    assert result["status"] == "success"
    assert "entry_id" in result["result"]
    print("✓ opc-journal.record: PASSED")


def test_opc_journal_search():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["search", "--query", "MVP"]
        }
    })
    assert result["status"] == "success"
    assert "query" in result["result"]
    print("✓ opc-journal.search: PASSED")


def test_opc_journal_export():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["export", "--format", "markdown", "--time-range", "all"]
        }
    })
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "markdown"
    print("✓ opc-journal.export: PASSED")


def test_opc_journal_analyze():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["analyze", "--days", "7"]
        }
    })
    assert result["status"] == "success"
    assert "signal_summary" in result["result"]
    print("✓ opc-journal.analyze: PASSED")


def test_opc_journal_milestones():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["milestones", "--content", "Finally launched the product!", "--day", "28"]
        }
    })
    assert result["status"] == "success"
    assert "candidate" in result["result"]
    print("✓ opc-journal.milestones: PASSED")


def test_opc_journal_task():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["task", "--description", "Research competitors", "--timeout-hours", "8"]
        }
    })
    assert result["status"] == "success"
    assert "task_id" in result["result"]
    print("✓ opc-journal.task: PASSED")


def test_opc_journal_insights():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["insights", "--day", "7"]
        }
    })
    assert result["status"] == "success"
    assert "signal_counts" in result["result"]
    print("✓ opc-journal.insights: PASSED")


def test_opc_journal_status():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["status"]
        }
    })
    assert result["status"] == "success"
    assert "total_entries" in result["result"]
    print("✓ opc-journal.status: PASSED")


def test_opc_journal_help():
    result = main({
        "customer_id": "OPC-TEST-001",
        "input": {
            "argv": ["help"]
        }
    })
    assert result["status"] == "success"
    assert result["result"]["help_displayed"] is True
    print("✓ opc-journal.help: PASSED")


def run_all_tests():
    print("\n" + "=" * 60)
    print("OPC Journal - Integration Tests")
    print("=" * 60 + "\n")

    tests = [
        test_opc_journal_init,
        test_opc_journal_record,
        test_opc_journal_search,
        test_opc_journal_export,
        test_opc_journal_analyze,
        test_opc_journal_milestones,
        test_opc_journal_task,
        test_opc_journal_insights,
        test_opc_journal_status,
        test_opc_journal_help,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: FAILED - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    if main is None:
        print("skip: opc-journal bundle not in tree")
        sys.exit(0)
    success = run_all_tests()
    sys.exit(0 if success else 1)
