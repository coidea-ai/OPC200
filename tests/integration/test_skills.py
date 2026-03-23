"""Integration tests for OPC200 Skills.

These tests verify the integration between skills and the core system.
"""
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

# Import skill modules
from skills.opc_journal_suite.opc_journal_core.scripts import init as journal_init
from skills.opc_journal_suite.opc_journal_core.scripts import record as journal_record
from skills.opc_journal_suite.opc_journal_core.scripts import search as journal_search
from skills.opc_journal_suite.opc_pattern_recognition.scripts import init as pattern_init
from skills.opc_journal_suite.opc_pattern_recognition.scripts import analyze as pattern_analyze
from skills.opc_journal_suite.opc_milestone_tracker.scripts import init as milestone_init
from skills.opc_journal_suite.opc_milestone_tracker.scripts import detect as milestone_detect
from skills.opc_journal_suite.opc_async_task_manager.scripts import init as task_init
from skills.opc_journal_suite.opc_async_task_manager.scripts import create as task_create
from skills.opc_journal_suite.opc_insights_generator.scripts import init as insights_init


@pytest.fixture
def test_customer_id():
    """Provide a test customer ID."""
    return "OPC-TEST-001"


@pytest.fixture
def temp_customer_dir(tmp_path):
    """Create a temporary directory for test customer data."""
    customer_dir = tmp_path / "customers" / "OPC-TEST-001"
    customer_dir.mkdir(parents=True)
    return customer_dir


@pytest.fixture
def journal_context(temp_customer_dir, test_customer_id):
    """Provide context for journal skill tests."""
    return {
        "customer_id": test_customer_id,
        "input": {},
        "config": {
            "storage": {"path": str(temp_customer_dir / "journal")},
            "privacy": {"default_level": "normal"},
            "retention_days": 365
        },
        "memory": {"timestamp": datetime.now().isoformat()}
    }


class TestJournalCoreSkill:
    """Tests for opc-journal-core skill."""
    
    def test_init(self, journal_context, temp_customer_dir):
        """Test journal initialization."""
        result = journal_init.main(journal_context)
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        assert result["result"]["customer_id"] == "OPC-TEST-001"
        
        # Verify database was created
        db_path = temp_customer_dir / "journal" / "journal.db"
        assert db_path.exists()
    
    def test_record(self, journal_context, temp_customer_dir):
        """Test recording a journal entry."""
        # First initialize
        journal_init.main(journal_context)
        
        # Then record
        journal_context["input"] = {
            "content": "Test journal entry for testing",
            "tags": ["test", "development"],
            "metadata": {
                "agents_involved": ["TestAgent"],
                "emotional_state": "focused",
                "energy_level": 8
            }
        }
        
        result = journal_record.main(journal_context)
        
        assert result["status"] == "success"
        assert result["result"]["entry_id"].startswith("JE-")
        assert result["result"]["customer_id"] == "OPC-TEST-001"
    
    def test_search(self, journal_context, temp_customer_dir):
        """Test searching journal entries."""
        # Initialize and record
        journal_init.main(journal_context)
        
        journal_context["input"] = {
            "content": "Test content with specific keyword",
            "tags": ["test"]
        }
        journal_record.main(journal_context)
        
        # Search
        journal_context["input"] = {
            "query": "specific keyword",
            "limit": 10
        }
        
        result = journal_search.main(journal_context)
        
        assert result["status"] == "success"
        assert result["result"]["total_count"] >= 0


class TestPatternRecognitionSkill:
    """Tests for opc-pattern-recognition skill."""
    
    @pytest.fixture
    def pattern_context(self, temp_customer_dir, test_customer_id):
        """Provide context for pattern recognition tests."""
        return {
            "customer_id": test_customer_id,
            "input": {},
            "config": {
                "storage": {"path": str(temp_customer_dir / "patterns")},
                "analysis_frequency": "weekly",
                "insight_depth": "detailed"
            },
            "memory": {"timestamp": datetime.now().isoformat()}
        }
    
    def test_init(self, pattern_context, temp_customer_dir):
        """Test pattern recognition initialization."""
        result = pattern_init.main(pattern_context)
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        
        # Verify config was created
        config_path = temp_customer_dir / "patterns" / "config.json"
        assert config_path.exists()


class TestMilestoneTrackerSkill:
    """Tests for opc-milestone-tracker skill."""
    
    @pytest.fixture
    def milestone_context(self, temp_customer_dir, test_customer_id):
        """Provide context for milestone tracker tests."""
        return {
            "customer_id": test_customer_id,
            "input": {},
            "config": {
                "storage": {"path": str(temp_customer_dir / "milestones")},
                "auto_detection": True,
                "celebration_enabled": True
            },
            "memory": {"timestamp": datetime.now().isoformat()}
        }
    
    def test_init(self, milestone_context, temp_customer_dir):
        """Test milestone tracker initialization."""
        result = milestone_init.main(milestone_context)
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        
        # Verify directories were created
        assert (temp_customer_dir / "milestones" / "achieved").exists()
        assert (temp_customer_dir / "milestones" / "pending").exists()
    
    def test_detect_milestone(self, milestone_context):
        """Test milestone detection."""
        milestone_init.main(milestone_context)
        
        milestone_context["input"] = {
            "content": "终于把产品部署到生产环境了！上线成功！",
            "day_number": 45
        }
        
        result = milestone_detect.main(milestone_context)
        
        assert result["status"] == "success"
        assert len(result["result"]["detected_milestones"]) > 0


class TestAsyncTaskManagerSkill:
    """Tests for opc-async-task-manager skill."""
    
    @pytest.fixture
    def task_context(self, temp_customer_dir, test_customer_id):
        """Provide context for async task manager tests."""
        return {
            "customer_id": test_customer_id,
            "input": {},
            "config": {
                "storage": {"path": str(temp_customer_dir / "tasks")},
                "max_concurrent": 5,
                "default_timeout": "8h",
                "notification_channels": ["feishu"]
            },
            "memory": {}
        }
    
    def test_init(self, task_context, temp_customer_dir):
        """Test async task manager initialization."""
        result = task_init.main(task_context)
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        assert result["result"]["max_concurrent"] == 5
    
    def test_create_task(self, task_context):
        """Test creating an async task."""
        task_init.main(task_context)
        
        task_context["input"] = {
            "title": "Test Research Task",
            "description": "Test task description",
            "task_type": "research",
            "agent": "TestAgent"
        }
        
        result = task_create.main(task_context)
        
        assert result["status"] == "success"
        assert result["result"]["task_id"].startswith("TASK-")
        assert result["result"]["status"] == "pending"


class TestInsightsGeneratorSkill:
    """Tests for opc-insights-generator skill."""
    
    @pytest.fixture
    def insights_context(self, temp_customer_dir, test_customer_id):
        """Provide context for insights generator tests."""
        return {
            "customer_id": test_customer_id,
            "input": {},
            "config": {
                "storage": {"path": str(temp_customer_dir / "insights")},
                "generation_frequency": "daily",
                "include_recommendations": True
            },
            "memory": {"timestamp": datetime.now().isoformat()}
        }
    
    def test_init(self, insights_context, temp_customer_dir):
        """Test insights generator initialization."""
        result = insights_init.main(insights_context)
        
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        
        # Verify directories were created
        assert (temp_customer_dir / "insights" / "daily").exists()
        assert (temp_customer_dir / "insights" / "weekly").exists()


class TestSkillIntegration:
    """Integration tests across multiple skills."""
    
    def test_full_workflow(self, temp_customer_dir, test_customer_id):
        """Test a complete workflow using multiple skills."""
        base_context = {
            "customer_id": test_customer_id,
            "input": {},
            "memory": {"timestamp": datetime.now().isoformat()}
        }
        
        # Step 1: Initialize journal
        journal_ctx = base_context.copy()
        journal_ctx["config"] = {
            "storage": {"path": str(temp_customer_dir / "journal")},
            "privacy": {"default_level": "normal"},
            "retention_days": 365
        }
        result = journal_init.main(journal_ctx)
        assert result["status"] == "success"
        
        # Step 2: Initialize milestone tracker
        milestone_ctx = base_context.copy()
        milestone_ctx["config"] = {
            "storage": {"path": str(temp_customer_dir / "milestones")},
            "auto_detection": True,
            "celebration_enabled": True
        }
        result = milestone_init.main(milestone_ctx)
        assert result["status"] == "success"
        
        # Step 3: Initialize task manager
        task_ctx = base_context.copy()
        task_ctx["config"] = {
            "storage": {"path": str(temp_customer_dir / "tasks")},
            "max_concurrent": 5,
            "default_timeout": "8h"
        }
        result = task_init.main(task_ctx)
        assert result["status"] == "success"
        
        # Step 4: Record a journal entry
        journal_ctx["input"] = {
            "content": "完成产品发布！部署到生产环境成功！",
            "tags": ["milestone", "deployment"],
            "metadata": {
                "agents_involved": ["DevAgent", "DeployAgent"],
                "day_number": 45,
                "emotional_state": "excited"
            }
        }
        result = journal_record.main(journal_ctx)
        assert result["status"] == "success"
        entry_id = result["result"]["entry_id"]
        
        # Step 5: Detect milestones
        milestone_ctx["input"] = {
            "content": "完成产品发布！部署到生产环境成功！",
            "day_number": 45
        }
        result = milestone_detect.main(milestone_ctx)
        assert result["status"] == "success"
        
        # Verify milestone was detected
        assert len(result["result"]["detected_milestones"]) > 0
        
        print(f"✓ Full workflow test passed for customer {test_customer_id}")
