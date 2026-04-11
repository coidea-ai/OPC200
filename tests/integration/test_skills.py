"""Integration tests for OPC Journal Suite Skills.

Tests each skill's core functionality flows.
"""
import sys
import tempfile
import shutil
from pathlib import Path

# Add skill paths
BASE_DIR = Path(__file__).parent.parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite"

sys.path.insert(0, str(SKILLS_DIR / "opc-journal-core" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "opc-pattern-recognition" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "opc-milestone-tracker" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "opc-async-task-manager" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "opc-insight-generator" / "scripts"))
sys.path.insert(0, str(SKILLS_DIR / "scripts"))

from init import main as journal_init
from record import main as journal_record
from search import main as journal_search
from export import main as journal_export
from analyze import main as pattern_analyze
from detect import main as milestone_detect
from create import main as task_create
from status import main as task_status
from daily_summary import main as insight_daily_summary
from coordinate import main as suite_coordinate
from utils.storage import write_memory_file, build_memory_path


def test_journal_core_init():
    """Test journal core initialization."""
    result = journal_init({
        "customer_id": "OPC-TEST-001",
        "input": {
            "day": 1,
            "goals": ["Complete MVP"],
            "preferences": {"timezone": "Asia/Shanghai"}
        }
    })
    
    assert result["status"] == "success"
    assert result["result"]["initialized"] is True
    assert result["result"]["customer_id"] == "OPC-TEST-001"
    print("✓ journal_core.init: PASSED")
    return True


def test_journal_core_record():
    """Test recording journal entries."""
    result = journal_record({
        "customer_id": "OPC-TEST-001",
        "input": {
            "content": "今天完成了用户注册功能",
            "day": 5,
            "metadata": {"energy_level": 6}
        }
    })
    
    assert result["status"] == "success"
    assert "entry_id" in result["result"]
    print("✓ journal_core.record: PASSED")
    return True


def test_journal_core_search():
    """Test searching journal entries."""
    result = journal_search({
        "customer_id": "OPC-TEST-001",
        "input": {"query": "database connection"}
    })
    
    assert result["status"] == "success"
    assert "search_params" in result["result"]
    print("✓ journal_core.search: PASSED")
    return True


def test_journal_core_export():
    """Test exporting journal entries."""
    result = journal_export({
        "customer_id": "OPC-TEST-001",
        "input": {
            "format": "markdown",
            "time_range": "all"
        }
    })
    
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "markdown"
    print("✓ journal_core.export: PASSED")
    return True


def test_pattern_recognition_analyze():
    """Test pattern analysis from memory files."""
    # Seed memory files for OPC-TEST-001
    write_memory_file(
        build_memory_path("OPC-TEST-001", "2026-04-01"),
        "今天完成了原型设计，感到兴奋和满足。决定先验证方向再写代码。"
    )
    write_memory_file(
        build_memory_path("OPC-TEST-001", "2026-04-02"),
        "遇到了API瓶颈，有点焦虑。完成了数据库查询优化。"
    )

    result = pattern_analyze({
        "customer_id": "OPC-TEST-001",
        "input": {
            "days": 7,
            "type": "weekly"
        }
    })

    assert result["status"] == "success"
    assert "interpretation" in result["result"]
    print("✓ pattern_recognition.analyze: PASSED")
    return True


def test_milestone_tracker_detect():
    """Test milestone detection."""
    result = milestone_detect({
        "customer_id": "OPC-TEST-001",
        "input": {
            "content": "终于把产品部署上线了！",
            "day": 45
        }
    })
    
    assert result["status"] == "success"
    assert "milestones_detected" in result["result"]
    print("✓ milestone_tracker.detect: PASSED")
    return True


def test_async_task_manager_create():
    """Test task creation."""
    result = task_create({
        "customer_id": "OPC-TEST-001",
        "input": {
            "type": "research",
            "description": "竞品分析报告",
            "timeout_hours": 8
        }
    })
    
    assert result["status"] == "success"
    assert "task_id" in result["result"]
    print("✓ async_task_manager.create: PASSED")
    return True


def test_async_task_manager_status():
    """Test task status query."""
    result = task_status({
        "customer_id": "OPC-TEST-001",
        "input": {"task_id": "TASK-20260327-A1B2C3"}
    })
    
    assert result["status"] == "success"
    assert "search_params" in result["result"]
    print("✓ async_task_manager.status: PASSED")
    return True


def test_insight_generator_daily_summary():
    """Test daily summary generation."""
    result = insight_daily_summary({
        "customer_id": "OPC-TEST-001",
        "input": {
            "day": 7,
            "entries": [
                {"content": "Worked on feature A"},
                {"content": "Met with customer"}
            ]
        }
    })
    
    assert result["status"] == "success"
    assert result["result"]["day"] == 7
    print("✓ insight_generator.daily_summary: PASSED")
    return True


def test_suite_coordinate():
    """Test suite coordination."""
    result = suite_coordinate({
        "customer_id": "OPC-TEST-001",
        "input": {"text": "记录今天的进度"}
    })
    
    assert result["status"] == "success"
    assert result["result"]["action"] == "delegate"
    assert result["result"]["delegation"]["target_skill"] == "opc-journal-core"
    print("✓ suite.coordinate: PASSED")
    return True


def test_suite_coordinate_chinese():
    """Test suite coordination with Chinese input."""
    result = suite_coordinate({
        "customer_id": "OPC-TEST-001",
        "input": {"text": "分析我的工作习惯"}
    })
    
    assert result["status"] == "success"
    assert result["result"]["delegation"]["intent"] == "pattern_analyze"
    print("✓ suite.coordinate_chinese: PASSED")
    return True


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("OPC Journal Suite - Integration Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_journal_core_init,
        test_journal_core_record,
        test_journal_core_search,
        test_journal_core_export,
        test_pattern_recognition_analyze,
        test_milestone_tracker_detect,
        test_async_task_manager_create,
        test_async_task_manager_status,
        test_insight_generator_daily_summary,
        test_suite_coordinate,
        test_suite_coordinate_chinese,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: FAILED - {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
