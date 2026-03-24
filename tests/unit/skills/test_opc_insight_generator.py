"""Unit tests for opc-insight-generator skill.

TDD Approach: Tests cover insight generation, daily summaries, weekly reviews, and recommendations
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
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite" / "opc-insight-generator" / "scripts"

insight_init = load_module("insight_init", SKILLS_DIR / "init.py")
insight_daily_summary = load_module("insight_daily_summary", SKILLS_DIR / "daily_summary.py")
insight_weekly_review = load_module("insight_weekly_review", SKILLS_DIR / "weekly_review.py")
insight_recommendations = load_module("insight_recommendations", SKILLS_DIR / "recommendations.py")


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


class TestInsightInit:
    """Tests for insight generator initialization."""
    
    def test_init_success(self, temp_dir, customer_id):
        """Test successful initialization."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"enabled": True, "max_per_day": 3}
            },
            "memory": {"timestamp": "2026-03-24T03:38:00Z"}
        }
        
        # Act
        result = insight_init.main(context)
        
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
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        result = insight_init.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_init_creates_directories(self, temp_dir, customer_id):
        """Test initialization creates required directories."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        insight_init.main(context)
        
        # Assert
        assert Path(f"{temp_dir}/insights/daily").exists()
        assert Path(f"{temp_dir}/insights/weekly").exists()
        assert Path(f"{temp_dir}/insights/recommendations").exists()
    
    def test_init_creates_config(self, temp_dir, customer_id):
        """Test initialization creates configuration file."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 5}
            },
            "memory": {}
        }
        
        # Act
        insight_init.main(context)
        
        # Assert
        config_path = Path(f"{temp_dir}/insights/config.json")
        assert config_path.exists()
        
        with open(config_path) as f:
            config = json.load(f)
        assert config["customer_id"] == customer_id


class TestDailySummary:
    """Tests for daily summary generation."""
    
    def test_daily_summary_success(self, temp_dir, customer_id):
        """Test successful daily summary generation."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"date": "2026-03-24"},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/insights"}
            },
            "memory": {}
        }
        
        # Act
        result = insight_daily_summary.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["date"] == "2026-03-24"
        assert "summary" in result["result"]
    
    def test_daily_summary_without_journal(self, temp_dir, customer_id):
        """Test daily summary without journal data."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {
                "journal_storage": {"path": f"{temp_dir}/journal"},
                "storage": {"path": f"{temp_dir}/insights"}
            },
            "memory": {}
        }
        
        # Act
        result = insight_daily_summary.main(context)
        
        # Assert
        assert result["status"] == "success"
        # Result structure may vary
    
    def test_daily_summary_missing_customer_id(self, temp_dir):
        """Test daily summary without customer_id fails."""
        context = {
            "customer_id": None,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        result = insight_daily_summary.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]


class TestWeeklyReview:
    """Tests for weekly review generation."""
    
    def test_weekly_review_success(self, temp_dir, customer_id):
        """Test successful weekly review generation."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"week_start": "2026-03-17"},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        result = insight_weekly_review.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "review" in result["result"]
        assert result["result"]["week_start"] == "2026-03-17"
    
    def test_weekly_review_default_week(self, temp_dir, customer_id):
        """Test weekly review with default week start."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        result = insight_weekly_review.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "review" in result["result"]
        assert "week" in result["result"]
    
    def test_weekly_review_missing_customer_id(self, temp_dir):
        """Test weekly review without customer_id fails."""
        context = {
            "customer_id": None,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        result = insight_weekly_review.main(context)
        
        # Assert
        assert result["status"] == "error"


class TestRecommendations:
    """Tests for recommendation generation."""
    
    def test_recommendations_productivity(self, temp_dir, customer_id):
        """Test productivity recommendations."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "type": "productivity",
                "productivity_data": {
                    "peak_hours": [9, 14],
                    "avg_focus_session": 25
                }
            },
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 3, "min_quality_score": 0.5}
            },
            "memory": {}
        }
        
        # Act
        result = insight_recommendations.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "recommendations" in result["result"]
    
    def test_recommendations_work_life(self, temp_dir, customer_id):
        """Test work-life balance recommendations."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "type": "work_life",
                "work_patterns": {
                    "avg_daily_hours": 10,
                    "weekend_work_frequency": 0.5
                }
            },
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 3, "min_quality_score": 0.5}
            },
            "memory": {}
        }
        
        # Act
        result = insight_recommendations.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "recommendations" in result["result"]
    
    def test_recommendations_all_types(self, temp_dir, customer_id):
        """Test recommendations for all types."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "type": "all",
                "productivity_data": {"peak_hours": [9, 14]},
                "work_patterns": {"avg_daily_hours": 8},
                "skill_data": {"skill_gaps": ["marketing"]}
            },
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 5, "min_quality_score": 0.5}
            },
            "memory": {}
        }
        
        # Act
        result = insight_recommendations.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert len(result["result"]["recommendations"]) > 0
    
    def test_recommendations_quality_filter(self, temp_dir, customer_id):
        """Test recommendations with quality filter."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"type": "productivity"},
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 3, "min_quality_score": 0.9}
            },
            "memory": {}
        }
        
        # Act
        result = insight_recommendations.main(context)
        
        # Assert
        assert result["status"] == "success"
        # With high threshold, might return fewer recommendations
        for rec in result["result"]["recommendations"]:
            assert rec.get("quality_score", 0) >= 0.9
    
    def test_recommendations_missing_customer_id(self, temp_dir):
        """Test recommendations without customer_id fails."""
        context = {
            "customer_id": None,
            "input": {"type": "productivity"},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        }
        
        # Act
        result = insight_recommendations.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_recommendations_saves_to_file(self, temp_dir, customer_id):
        """Test recommendations are saved to file."""
        # Arrange - initialize first
        insight_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/insights"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {"type": "productivity"},
            "config": {
                "storage": {"path": f"{temp_dir}/insights"},
                "proactive": {"max_per_day": 3, "min_quality_score": 0.5}
            },
            "memory": {}
        }
        
        # Act
        result = insight_recommendations.main(context)
        
        # Assert
        assert result["status"] == "success"
        
        # Check that file was created
        rec_dir = Path(f"{temp_dir}/insights/recommendations")
        assert any(rec_dir.iterdir())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
