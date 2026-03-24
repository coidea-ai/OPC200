"""Unit tests for opc-pattern-recognition skill.

TDD Approach: Tests cover pattern initialization, analysis, and outlier detection
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Load module helper - use exec() with proper sys.path setup
def load_module(module_name, file_path):
    """Load a skill module by executing it with proper import context."""
    # Calculate project root
    project_root = str(Path(__file__).parent.parent.parent.parent.resolve())
    
    # Create a copy of sys module's path for isolation
    import sys as _sys
    _original_path = _sys.path.copy()
    
    # Ensure project root is in path
    if project_root not in _sys.path:
        _sys.path.insert(0, project_root)
    
    try:
        # Create namespace with access to real sys
        namespace = {
            '__name__': module_name,
            '__file__': str(file_path),
        }
        
        # Read and execute the skill script
        code = file_path.read_text()
        exec(code, namespace)
        
        # Return a simple module-like object
        class SkillModule:
            pass
        
        module = SkillModule()
        for key, value in namespace.items():
            if not key.startswith('__'):
                setattr(module, key, value)
        
        return module
    finally:
        # Restore original sys.path
        _sys.path[:] = _original_path


# Load the skill scripts
BASE_DIR = Path(__file__).parent.parent.parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite"

# Load journal core for setup
journal_init = load_module(
    "journal_init",
    SKILLS_DIR / "opc-journal-core" / "scripts" / "init.py"
)
journal_record = load_module(
    "journal_record",
    SKILLS_DIR / "opc-journal-core" / "scripts" / "record.py"
)

# Load pattern recognition
pattern_init = load_module(
    "pattern_init",
    SKILLS_DIR / "opc-pattern-recognition" / "scripts" / "init.py"
)
pattern_analyze = load_module(
    "pattern_analyze",
    SKILLS_DIR / "opc-pattern-recognition" / "scripts" / "analyze.py"
)
pattern_detect_outliers = load_module(
    "pattern_detect_outliers",
    SKILLS_DIR / "opc-pattern-recognition" / "scripts" / "detect_outliers.py"
)


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


class TestPatternInit:
    """Tests for pattern recognition initialization."""
    
    def test_init_success(self, temp_dir, customer_id):
        """Test successful initialization."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {"timestamp": "2026-03-24T03:38:00Z"}
        }
        
        # Act
        result = pattern_init.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["initialized"] is True
        assert result["result"]["customer_id"] == customer_id
    
    def test_init_missing_customer_id(self, temp_dir):
        """Test initialization without customer_id fails."""
        # Arrange
        context = {
            "customer_id": None,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {}
        }
        
        # Act
        result = pattern_init.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_init_creates_config(self, temp_dir, customer_id):
        """Test initialization creates configuration file."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {
                "storage": {"path": f"{temp_dir}/patterns"},
                "analysis_frequency": "daily"
            },
            "memory": {}
        }
        
        # Act
        result = pattern_init.main(context)
        
        # Assert
        config_path = Path(f"{temp_dir}/patterns/config.json")
        assert config_path.exists()


class TestPatternAnalyze:
    """Tests for pattern analysis."""
    
    def test_analyze_with_entries(self, temp_dir, customer_id):
        """Test analysis with journal entries."""
        # Arrange - setup journal with entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        for i in range(5):
            journal_record.main({
                "customer_id": customer_id,
                "input": {
                    "content": f"Entry {i}",
                    "metadata": {"energy_level": 5 + i % 3}
                },
                "config": {"storage": {"path": f"{temp_dir}/journal"}},
                "memory": {}
            })
        
        pattern_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"dimensions": ["growth_trajectory"]},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_analyze.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "patterns" in result["result"]
        assert result["result"]["entry_count"] == 5
    
    def test_analyze_without_journal(self, temp_dir, customer_id):
        """Test analysis without journal fails."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {"dimensions": ["work_rhythm"]},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_analyze.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
    
    def test_analyze_empty_journal(self, temp_dir, customer_id):
        """Test analysis with empty journal."""
        # Arrange - setup empty journal
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        pattern_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"dimensions": ["work_rhythm"]},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_analyze.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["entry_count"] == 0
    
    def test_analyze_multiple_dimensions(self, temp_dir, customer_id):
        """Test analysis with multiple dimensions."""
        # Arrange - setup journal with entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        for i in range(10):
            journal_record.main({
                "customer_id": customer_id,
                "input": {"content": f"Entry about decision {i}", "metadata": {"energy_level": 6}},
                "config": {"storage": {"path": f"{temp_dir}/journal"}},
                "memory": {}
            })
        
        pattern_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/patterns"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "dimensions": ["work_rhythm", "decision_patterns", "growth_trajectory"]
            },
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_analyze.main(context)
        
        # Assert
        assert result["status"] == "success"
        patterns = result["result"]["patterns"]
        assert "work_rhythm" in patterns


class TestPatternDetectOutliers:
    """Tests for outlier detection."""
    
    def test_detect_energy_outliers(self, temp_dir, customer_id):
        """Test detecting energy level outliers."""
        # Arrange - setup journal with outlier entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        # Add entries with one outlier (energy level 2 among 5-7)
        for energy in [6, 7, 6, 5, 2, 6, 7]:
            journal_record.main({
                "customer_id": customer_id,
                "input": {"content": "Test entry", "metadata": {"energy_level": energy}},
                "config": {"storage": {"path": f"{temp_dir}/journal"}},
                "memory": {}
            })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "types": ["energy_outliers"],
                "threshold": 1.5
            },
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_detect_outliers.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "outliers" in result["result"]
    
    def test_detect_no_outliers(self, temp_dir, customer_id):
        """Test with data that has no outliers."""
        # Arrange - setup journal with consistent entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        # Add entries with similar energy levels
        for energy in [6, 6, 7, 6, 6, 7, 6]:
            journal_record.main({
                "customer_id": customer_id,
                "input": {"content": "Test entry", "metadata": {"energy_level": energy}},
                "config": {"storage": {"path": f"{temp_dir}/journal"}},
                "memory": {}
            })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "types": ["energy_outliers"],
                "threshold": 2.0
            },
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_detect_outliers.main(context)
        
        # Assert
        assert result["status"] == "success"
    
    def test_detect_insufficient_data(self, temp_dir, customer_id):
        """Test detection with insufficient data."""
        # Arrange - setup journal with few entries
        journal_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/journal"}},
            "memory": {}
        })
        
        # Add only 2 entries
        for _ in range(2):
            journal_record.main({
                "customer_id": customer_id,
                "input": {"content": "Test entry"},
                "config": {"storage": {"path": f"{temp_dir}/journal"}},
                "memory": {}
            })
        
        context = {
            "customer_id": customer_id,
            "input": {"types": ["energy_outliers"]},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_detect_outliers.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "insufficient" in result["result"].get("message", "").lower() or result["result"]["outlier_count"] == 0
    
    def test_detect_without_init(self, temp_dir, customer_id):
        """Test detection without journal fails."""
        context = {
            "customer_id": customer_id,
            "input": {"types": ["energy_outliers"]},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/patterns"}
            },
            "memory": {}
        }
        
        # Act
        result = pattern_detect_outliers.main(context)
        
        # Assert
        assert result["status"] == "error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
