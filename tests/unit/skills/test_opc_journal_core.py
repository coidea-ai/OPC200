"""Unit tests for opc-journal-core skill.

TDD Approach: Tests cover initialization, recording, searching, and exporting
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Load module helper - use exec() in current context
def load_module(module_name, file_path):
    """Load a skill module by executing it in current context."""
    # Create a module-like namespace
    namespace = {
        '__name__': module_name,
        '__file__': str(file_path),
    }
    
    # Read and execute the skill script in current context
    code = file_path.read_text()
    exec(code, namespace)
    
    # Return a simple module-like object with the exported functions
    class SkillModule:
        pass
    
    module = SkillModule()
    for key, value in namespace.items():
        if not key.startswith('__'):
            setattr(module, key, value)
    
    return module


# Load the skill scripts
BASE_DIR = Path(__file__).parent.parent.parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite" / "opc-journal-core" / "scripts"

journal_init = load_module("journal_init", SKILLS_DIR / "init.py")
journal_record = load_module("journal_record", SKILLS_DIR / "record.py")
journal_search = load_module("journal_search", SKILLS_DIR / "search.py")
journal_export = load_module("journal_export", SKILLS_DIR / "export.py")


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


class TestJournalInit:
    """Tests for journal initialization."""
    
    def test_init_success(self, temp_dir, customer_id):
        """Test successful initialization."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {"timestamp": "2026-03-24T03:38:00Z"}
        }
        
        # Act
        result = journal_init.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["customer_id"] == customer_id
        assert result["result"]["initialized"] is True
        assert Path(result["result"]["db_path"]).exists()
    
    def test_init_missing_customer_id(self, temp_dir):
        """Test initialization without customer_id fails."""
        # Arrange
        context = {
            "customer_id": None,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_init.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_init_empty_customer_id(self, temp_dir):
        """Test initialization with empty customer_id fails."""
        # Arrange
        context = {
            "customer_id": "",
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_init.main(context)
        
        # Assert
        assert result["status"] == "error"


class TestJournalRecord:
    """Tests for journal recording."""
    
    def test_record_success(self, temp_dir, customer_id):
        """Test successful entry recording."""
        # Arrange - initialize first
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "Test journal entry",
                "tags": ["test"],
                "metadata": {"energy_level": 7}
            },
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {"session_id": "test-session"}
        }
        
        # Act
        result = journal_record.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "entry_id" in result["result"]
        assert result["result"]["customer_id"] == customer_id
        assert result["result"]["tags"] == ["test"]
    
    def test_record_missing_content(self, temp_dir, customer_id):
        """Test recording without content fails."""
        # Arrange - initialize first
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"tags": ["test"]},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_record.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "content is required" in result["message"]
    
    def test_record_empty_content(self, temp_dir, customer_id):
        """Test recording with empty content fails."""
        # Arrange - initialize first
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"content": "", "tags": ["test"]},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_record.main(context)
        
        # Assert
        assert result["status"] == "error"
    
    def test_record_without_init(self, temp_dir, customer_id):
        """Test recording without initialization fails."""
        # Arrange - no initialization
        context = {
            "customer_id": customer_id,
            "input": {"content": "Test entry"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_record.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
    
    def test_record_with_metadata(self, temp_dir, customer_id):
        """Test recording with full metadata."""
        # Arrange - initialize first
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "Entry with full metadata",
                "tags": ["work", "important"],
                "metadata": {
                    "energy_level": 8,
                    "emotional_state": "excited",
                    "agents_involved": ["Agent1", "Agent2"],
                    "tasks_completed": ["TASK-001"]
                }
            },
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_record.main(context)
        
        # Assert
        assert result["status"] == "success"
        # Metadata is stored, verify it exists in the result


class TestJournalSearch:
    """Tests for journal searching."""
    
    def test_search_by_query(self, temp_dir, customer_id):
        """Test searching by query text."""
        # Arrange - initialize and add entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        journal_record.main({
            "customer_id": customer_id,
            "input": {"content": "Meeting with team about project"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"query": "meeting", "limit": 10},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_search.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["total_count"] >= 1
        assert result["result"]["query"] == "meeting"
    
    def test_search_by_tags(self, temp_dir, customer_id):
        """Test searching by tags."""
        # Arrange - initialize and add entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        journal_record.main({
            "customer_id": customer_id,
            "input": {"content": "Tagged entry", "tags": ["special"]},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"tags": ["special"]},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_search.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["total_count"] >= 1
    
    def test_search_empty_results(self, temp_dir, customer_id):
        """Test search with no matching results."""
        # Arrange - initialize but no entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"query": "nonexistent"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_search.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["total_count"] == 0
    
    def test_search_without_init(self, temp_dir, customer_id):
        """Test searching without initialization fails."""
        context = {
            "customer_id": customer_id,
            "input": {"query": "test"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_search.main(context)
        
        # Assert
        assert result["status"] == "error"


class TestJournalExport:
    """Tests for journal exporting."""
    
    def test_export_json(self, temp_dir, customer_id):
        """Test exporting to JSON format."""
        # Arrange - initialize and add entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        journal_record.main({
            "customer_id": customer_id,
            "input": {"content": "Entry to export"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"format": "json"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_export.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["format"] == "json"
        assert result["result"]["entry_count"] >= 1
        assert Path(result["result"]["output_path"]).exists()
    
    def test_export_markdown(self, temp_dir, customer_id):
        """Test exporting to Markdown format."""
        # Arrange - initialize and add entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        journal_record.main({
            "customer_id": customer_id,
            "input": {"content": "Entry to export"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"format": "markdown"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_export.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["format"] == "markdown"
    
    def test_export_empty_journal(self, temp_dir, customer_id):
        """Test exporting empty journal."""
        # Arrange - initialize but no entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"format": "json"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_export.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["entry_count"] == 0
    
    def test_export_without_init(self, temp_dir, customer_id):
        """Test exporting without initialization fails."""
        context = {
            "customer_id": customer_id,
            "input": {"format": "json"},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        }
        
        # Act
        result = journal_export.main(context)
        
        # Assert
        assert result["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
