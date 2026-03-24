"""Unit tests for opc-async-task-manager skill.

TDD Approach: Tests cover task initialization, creation, execution, and status queries
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure project root is in path for all skill imports
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent.resolve())
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
os.environ["PYTHONPATH"] = _PROJECT_ROOT + os.pathsep + os.environ.get("PYTHONPATH", "")

# Pre-import src package to ensure it's available for skill scripts
import src

# Load module helper - simpler approach using regular import after path setup
def load_module(module_name, file_path):
    """Load a skill module by dynamically importing it."""
    # Add the skills directory to path for relative imports within skills
    skills_dir = str(file_path.parent)
    if skills_dir not in sys.path:
        sys.path.insert(0, skills_dir)
    
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


# Load the skill scripts
BASE_DIR = Path(__file__).parent.parent.parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite" / "opc-async-task-manager" / "scripts"

task_init = load_module("task_init", SKILLS_DIR / "init.py")
task_create = load_module("task_create", SKILLS_DIR / "create.py")
task_execute = load_module("task_execute", SKILLS_DIR / "execute.py")
task_status = load_module("task_status", SKILLS_DIR / "status.py")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmp = tempfile.mkdtemp()
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def customer_id():
    """Return a test customer ID."""
    return "OPC-TEST-001"


class TestTaskInit:
    """Tests for async task manager initialization."""
    
    def test_init_success(self, temp_dir, customer_id):
        """Test successful initialization."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {
                "storage": {"path": f"{temp_dir}/tasks"},
                "max_concurrent": 5
            },
            "memory": {"timestamp": "2026-03-24T03:38:00Z"}
        }
        
        # Act
        result = task_init.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        assert result["result"]["max_concurrent"] == 5
    
    def test_init_missing_customer_id(self, temp_dir):
        """Test initialization without customer_id fails."""
        # Arrange
        context = {
            "customer_id": None,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_init.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_init_creates_directories(self, temp_dir, customer_id):
        """Test initialization creates required directories."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        task_init.main(context)
        
        # Assert
        assert Path(f"{temp_dir}/tasks/queue").exists()
        assert Path(f"{temp_dir}/tasks/completed").exists()
        assert Path(f"{temp_dir}/tasks/failed").exists()
    
    def test_init_creates_queue_file(self, temp_dir, customer_id):
        """Test initialization creates queue file."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        task_init.main(context)
        
        # Assert
        queue_file = Path(f"{temp_dir}/tasks/queue/tasks.json")
        assert queue_file.exists()


class TestTaskCreate:
    """Tests for task creation."""
    
    def test_create_success(self, temp_dir, customer_id):
        """Test successful task creation."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "title": "Test Task",
                "description": "A test task description",
                "task_type": "research",
                "estimated_duration": "4h"
            },
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_create.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "task_id" in result["result"]
        assert result["result"]["title"] == "Test Task"
        assert result["result"]["status"] == "pending"
    
    def test_create_missing_title(self, temp_dir, customer_id):
        """Test creation without title fails."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"description": "No title"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_create.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "title is required" in result["message"]
    
    def test_create_without_init(self, temp_dir, customer_id):
        """Test creation without initialization fails."""
        # Arrange - no initialization
        context = {
            "customer_id": customer_id,
            "input": {"title": "Test Task"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_create.main(context)
        
        # Assert - should fail without init
        assert result["status"] == "error"
    
    def test_create_with_deadline(self, temp_dir, customer_id):
        """Test task creation with deadline."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "title": "Task with deadline",
                "deadline": "tomorrow 08:00"
            },
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_create.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "deadline" in result["result"]
    
    def test_create_generates_execution_plan(self, temp_dir, customer_id):
        """Test task creation generates execution plan."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "title": "Task with plan",
                "estimated_duration": "4h"
            },
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_create.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "execution_plan" in result["result"]
        assert len(result["result"]["execution_plan"]) > 0


class TestTaskExecute:
    """Tests for task execution."""
    
    def test_execute_success(self, temp_dir, customer_id):
        """Test successful task execution."""
        # Arrange - initialize and create task
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        create_result = task_create.main({
            "customer_id": customer_id,
            "input": {"title": "Task to execute"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        task_id = create_result["result"]["task_id"]
        
        context = {
            "customer_id": customer_id,
            "input": {"task_id": task_id},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_execute.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["status"] in ["completed", "failed"]
    
    def test_execute_missing_task_id(self, temp_dir, customer_id):
        """Test execution without task_id fails."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_execute.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "task_id is required" in result["message"]
    
    def test_execute_nonexistent_task(self, temp_dir, customer_id):
        """Test execution of non-existent task."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"task_id": "NONEXISTENT-123"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_execute.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


class TestTaskStatus:
    """Tests for task status queries."""
    
    def test_status_by_task_id(self, temp_dir, customer_id):
        """Test querying status by task ID."""
        # Arrange - initialize and create task
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        create_result = task_create.main({
            "customer_id": customer_id,
            "input": {"title": "Task to check"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        task_id = create_result["result"]["task_id"]
        
        context = {
            "customer_id": customer_id,
            "input": {"task_id": task_id},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_status.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["task"]["id"] == task_id
    
    def test_status_list_all(self, temp_dir, customer_id):
        """Test listing all tasks."""
        # Arrange - initialize and create tasks
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        for i in range(3):
            task_create.main({
                "customer_id": customer_id,
                "input": {"title": f"Task {i}"},
                "config": {"storage": {"path": f"{temp_dir}/tasks"}},
                "memory": {}
            })
        
        context = {
            "customer_id": customer_id,
            "input": {"list_all": True},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_status.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["total_count"] >= 3
    
    def test_status_queue_stats(self, temp_dir, customer_id):
        """Test getting queue statistics."""
        # Arrange - initialize
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_status.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "queue_stats" in result["result"]
    
    def test_status_nonexistent_task(self, temp_dir, customer_id):
        """Test status query for non-existent task."""
        # Arrange - initialize first
        task_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"task_id": "NONEXISTENT-123"},
            "config": {"storage": {"path": f"{temp_dir}/tasks"}},
            "memory": {}
        }
        
        # Act
        result = task_status.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
