"""Integration tests for OPC Journal Suite Skills.

Tests each skill's initialization and core functionality flows.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Helper function to load module from file
def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    
    # Add project root to path before executing
    import sys
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    
    spec.loader.exec_module(module)
    return module


# Load all skill modules
BASE_DIR = Path(__file__).parent.parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite"

# Journal Core
journal_init = load_module("journal_init", SKILLS_DIR / "opc-journal-core" / "scripts" / "init.py")
journal_record = load_module("journal_record", SKILLS_DIR / "opc-journal-core" / "scripts" / "record.py")
journal_search = load_module("journal_search", SKILLS_DIR / "opc-journal-core" / "scripts" / "search.py")
journal_export = load_module("journal_export", SKILLS_DIR / "opc-journal-core" / "scripts" / "export.py")

# Pattern Recognition
pattern_init = load_module("pattern_init", SKILLS_DIR / "opc-pattern-recognition" / "scripts" / "init.py")
pattern_analyze = load_module("pattern_analyze", SKILLS_DIR / "opc-pattern-recognition" / "scripts" / "analyze.py")
pattern_detect_outliers = load_module("pattern_detect_outliers", SKILLS_DIR / "opc-pattern-recognition" / "scripts" / "detect_outliers.py")

# Milestone Tracker
milestone_init = load_module("milestone_init", SKILLS_DIR / "opc-milestone-tracker" / "scripts" / "init.py")
milestone_detect = load_module("milestone_detect", SKILLS_DIR / "opc-milestone-tracker" / "scripts" / "detect.py")
milestone_notify = load_module("milestone_notify", SKILLS_DIR / "opc-milestone-tracker" / "scripts" / "notify.py")

# Async Task Manager
task_init = load_module("task_init", SKILLS_DIR / "opc-async-task-manager" / "scripts" / "init.py")
task_create = load_module("task_create", SKILLS_DIR / "opc-async-task-manager" / "scripts" / "create.py")
task_execute = load_module("task_execute", SKILLS_DIR / "opc-async-task-manager" / "scripts" / "execute.py")
task_status = load_module("task_status", SKILLS_DIR / "opc-async-task-manager" / "scripts" / "status.py")

# Insight Generator
insight_init = load_module("insight_init", SKILLS_DIR / "opc-insight-generator" / "scripts" / "init.py")
insight_daily_summary = load_module("insight_daily_summary", SKILLS_DIR / "opc-insight-generator" / "scripts" / "daily_summary.py")
insight_weekly_review = load_module("insight_weekly_review", SKILLS_DIR / "opc-insight-generator" / "scripts" / "weekly_review.py")
insight_recommendations = load_module("insight_recommendations", SKILLS_DIR / "opc-insight-generator" / "scripts" / "recommendations.py")


def test_journal_core_init():
    """Test journal core initialization."""
    temp_dir = tempfile.mkdtemp()
    try:
        result = journal_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {"timestamp": "2026-03-24T03:38:00Z"}
        })
        
        assert result["status"] == "success", f"Init failed: {result['message']}"
        assert result["result"]["initialized"] is True
        assert Path(result["result"]["db_path"]).exists()
        print("✓ journal_core.init: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_journal_core_record_and_search():
    """Test recording and searching journal entries."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize
        journal_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        # Record entry
        result = journal_record.main({
            "customer_id": "OPC-TEST-001",
            "input": {
                "content": "今天完成了用户注册功能",
                "metadata": {"energy_level": 6}
            },
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        
        # Search
        result = journal_search.main({
            "customer_id": "OPC-TEST-001",
            "input": {"query": "注册"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert result["result"]["total_count"] >= 1
        print("✓ journal_core.record & search: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_journal_core_export():
    """Test exporting journal entries."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize and record
        journal_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        journal_record.main({
            "customer_id": "OPC-TEST-001",
            "input": {"content": "Test entry"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        # Export
        result = journal_export.main({
            "customer_id": "OPC-TEST-001",
            "input": {"format": "json"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert Path(result["result"]["output_path"]).exists()
        print("✓ journal_core.export: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_pattern_recognition_init():
    """Test pattern recognition initialization."""
    temp_dir = tempfile.mkdtemp()
    try:
        result = pattern_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        print("✓ pattern_recognition.init: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_pattern_recognition_analyze():
    """Test pattern analysis."""
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize journal and add entries
        journal_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        for i in range(5):
            journal_record.main({
                "customer_id": "OPC-TEST-001",
                "input": {"content": f"Entry {i}", "metadata": {"energy_level": 5 + i % 3}},
                "config": {"storage": {"path": f"{temp_dir}/journal"}},
                "memory": {}
            })
        
        pattern_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {}
        })
        
        result = pattern_analyze.main({
            "customer_id": "OPC-TEST-001",
            "input": {"dimensions": ["growth_trajectory"]},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert "patterns" in result["result"]
        print("✓ pattern_recognition.analyze: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_milestone_tracker_init():
    """Test milestone tracker initialization."""
    temp_dir = tempfile.mkdtemp()
    try:
        result = milestone_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        print("✓ milestone_tracker.init: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_milestone_tracker_detect():
    """Test milestone detection."""
    temp_dir = tempfile.mkdtemp()
    try:
        milestone_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        result = milestone_detect.main({
            "customer_id": "OPC-TEST-001",
            "input": {"content": "终于把产品部署上线了！", "day_number": 45},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert "detected_milestones" in result["result"]
        print("✓ milestone_tracker.detect: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_async_task_manager_init():
    """Test async task manager initialization."""
    temp_dir = tempfile.mkdtemp()
    try:
        result = task_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        print("✓ async_task_manager.init: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_async_task_manager_create_and_status():
    """Test task creation and status query."""
    temp_dir = tempfile.mkdtemp()
    try:
        task_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        create_result = task_create.main({
            "customer_id": "OPC-TEST-001",
            "input": {"title": "测试任务", "task_type": "research"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        assert create_result["status"] == "success"
        task_id = create_result["result"]["task_id"]
        
        status_result = task_status.main({
            "customer_id": "OPC-TEST-001",
            "input": {"task_id": task_id},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        assert status_result["status"] == "success"
        assert status_result["result"]["task"]["id"] == task_id
        print("✓ async_task_manager.create & status: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_insight_generator_init():
    """Test insight generator initialization."""
    temp_dir = tempfile.mkdtemp()
    try:
        result = insight_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        print("✓ insight_generator.init: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_insight_generator_recommendations():
    """Test recommendation generation."""
    temp_dir = tempfile.mkdtemp()
    try:
        insight_init.main({
            "customer_id": "OPC-TEST-001",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        result = insight_recommendations.main({
            "customer_id": "OPC-TEST-001",
            "input": {
                "type": "productivity",
                "productivity_data": {"peak_hours": [9, 14]}
            },
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 3, "min_quality_score": 0.5}
            },
            "memory": {}
        })
        
        assert result["status"] == "success"
        assert "recommendations" in result["result"]
        print("✓ insight_generator.recommendations: PASSED")
        return True
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def run_all_tests():
    """Run all integration tests."""
    print("\n" + "=" * 60)
    print("OPC Journal Suite - Integration Tests")
    print("=" * 60 + "\n")
    
    tests = [
        test_journal_core_init,
        test_journal_core_record_and_search,
        test_journal_core_export,
        test_pattern_recognition_init,
        test_pattern_recognition_analyze,
        test_milestone_tracker_init,
        test_milestone_tracker_detect,
        test_async_task_manager_init,
        test_async_task_manager_create_and_status,
        test_insight_generator_init,
        test_insight_generator_recommendations,
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
    import sys
    sys.path.insert(0, str(BASE_DIR))
    
    success = run_all_tests()
    sys.exit(0 if success else 1)
