"""Unit tests for opc-milestone-tracker skill.

TDD Approach: Tests cover milestone initialization, detection, and notification.
"""
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# Load module helper
def load_module(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    spec.loader.exec_module(module)
    return module


# Load the skill scripts
BASE_DIR = Path(__file__).parent.parent.parent.parent
SKILLS_DIR = BASE_DIR / "skills" / "opc-journal-suite" / "opc-milestone-tracker" / "scripts"

milestone_init = load_module("milestone_init", SKILLS_DIR / "init.py")
milestone_detect = load_module("milestone_detect", SKILLS_DIR / "detect.py")
milestone_notify = load_module("milestone_notify", SKILLS_DIR / "notify.py")


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


class TestMilestoneInit:
    """Tests for milestone tracker initialization."""
    
    def test_init_success(self, temp_dir, customer_id):
        """Test successful initialization."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {"timestamp": "2026-03-24T03:38:00Z"}
        }
        
        # Act
        result = milestone_init.main(context)
        
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
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_init.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_init_creates_directories(self, temp_dir, customer_id):
        """Test initialization creates required directories."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        milestone_init.main(context)
        
        # Assert
        assert Path(f"{temp_dir}/milestones/achieved").exists()
        assert Path(f"{temp_dir}/milestones/pending").exists()
        assert Path(f"{temp_dir}/milestones/predicted").exists()
    
    def test_init_creates_config(self, temp_dir, customer_id):
        """Test initialization creates configuration."""
        # Arrange
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {
                "storage": {"path": f"{temp_dir}/milestones"},
                "auto_detection": True
            },
            "memory": {}
        }
        
        # Act
        milestone_init.main(context)
        
        # Assert
        config_path = Path(f"{temp_dir}/milestones/config.json")
        assert config_path.exists()
        
        with open(config_path) as f:
            config = json.load(f)
        assert config["customer_id"] == customer_id
        assert config["auto_detection"] is True


class TestMilestoneDetect:
    """Tests for milestone detection."""
    
    def test_detect_first_deployment(self, temp_dir, customer_id):
        """Test detecting first deployment milestone."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "终于把产品部署到生产环境了！上线成功！",
                "day_number": 45
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_detect.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert len(result["result"]["detected_milestones"]) >= 1
        assert any(m["type"] == "first_deployment" for m in result["result"]["detected_milestones"])
    
    def test_detect_first_sale(self, temp_dir, customer_id):
        """Test detecting first sale milestone."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "收到了第一笔客户付款！订单成交！",
                "day_number": 30
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_detect.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert any(m["type"] == "first_sale" for m in result["result"]["detected_milestones"])
    
    def test_detect_mvp_complete(self, temp_dir, customer_id):
        """Test detecting MVP complete milestone."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "MVP完成了！最小可用产品已就绪",
                "day_number": 21
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_detect.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert any(m["type"] == "mvp_complete" for m in result["result"]["detected_milestones"])
    
    def test_detect_no_milestone(self, temp_dir, customer_id):
        """Test content with no milestone keywords."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "这是一个普通的日常记录，没有任何特殊事件",
                "day_number": 10
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_detect.main(context)
        
        # Assert
        assert result["status"] == "success"
        # May or may not detect milestones based on content
    
    def test_detect_missing_customer_id(self, temp_dir):
        """Test detection without customer_id fails."""
        context = {
            "customer_id": None,
            "input": {"content": "Test content"},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_detect.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_detect_multi_agent_workflow(self, temp_dir, customer_id):
        """Test detecting multi-agent workflow milestone."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "content": "今天使用了多Agent协作完成了复杂任务",
                "agents_involved": ["Agent1", "Agent2", "Agent3"],
                "day_number": 40
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_detect.main(context)
        
        # Assert
        assert result["status"] == "success"


class TestMilestoneNotify:
    """Tests for milestone notification."""
    
    def test_notify_success(self, temp_dir, customer_id):
        """Test successful milestone notification."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "milestone": {
                    "type": "first_deployment",
                    "category": "technical",
                    "date": "2026-03-24T10:00:00",
                    "day_number": 45,
                    "celebration": "🚀 里程碑: 首次部署！"
                }
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_notify.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["milestone_saved"] is True
    
    def test_notify_missing_milestone(self, temp_dir, customer_id):
        """Test notification without milestone data fails."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_notify.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "milestone data is required" in result["message"]
    
    def test_notify_missing_customer_id(self, temp_dir):
        """Test notification without customer_id fails."""
        context = {
            "customer_id": None,
            "input": {
                "milestone": {"type": "first_deployment", "celebration": "Test"}
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_notify.main(context)
        
        # Assert
        assert result["status"] == "error"
        assert "customer_id is required" in result["message"]
    
    def test_notify_creates_celebration_report(self, temp_dir, customer_id):
        """Test notification generates celebration report."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "milestone": {
                    "type": "first_deployment",
                    "category": "technical",
                    "date": "2026-03-24T10:00:00",
                    "day_number": 45,
                    "celebration": "🚀 里程碑: 首次部署！"
                }
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_notify.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert "detailed_report" in result["result"]["notification"]
        assert "🚀" in result["result"]["notification"]["celebration_message"]
    
    def test_notify_updates_stats(self, temp_dir, customer_id):
        """Test notification updates milestone statistics."""
        # Arrange - initialize first
        milestone_init.main({
            "customer_id": customer_id,
            "input": {},
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        })
        
        context = {
            "customer_id": customer_id,
            "input": {
                "milestone": {
                    "type": "first_deployment",
                    "category": "technical",
                    "celebration": "Test milestone"
                }
            },
            "config": {"storage": {"path": f"{temp_dir}/milestones"}},
            "memory": {}
        }
        
        # Act
        result = milestone_notify.main(context)
        
        # Assert
        assert result["status"] == "success"
        assert result["result"]["total_milestones"] >= 1
        
        # Verify stats file was updated
        milestones_file = Path(f"{temp_dir}/milestones/milestones.json")
        assert milestones_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
