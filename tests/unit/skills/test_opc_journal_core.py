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

# Ensure project root is in path for imports
_PROJECT_ROOT = str(Path(__file__).parent.parent.parent.parent.resolve())
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Import src package normally - this loads everything correctly
import src

# Load module helper - execute skill script with src available in namespace
def load_module(module_name, file_path):
    """Load a skill module by executing it with src in namespace."""
    # Create namespace with src module already available
    namespace = {
        '__name__': module_name,
        '__file__': str(file_path),
        'src': src,  # Make src available directly
    }
    
    # Read and execute the skill script
    code = file_path.read_text()
    exec(code, namespace)
    
    # Return a simple module-like object
    class SkillModule:
        pass
    
    module = SkillModule()
    for key, value in namespace.items():
        if not key.startswith('__') and key != 'src':
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
    """Test journal initialization."""

    def test_init_success(self, temp_dir, customer_id):
        """Test successful initialization."""
        context = {
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        }
        result = journal_init.main(context)

        assert result["status"] == "success"
        assert result["result"]["customer_id"] == customer_id
        assert result["result"]["initialized"] is True

    def test_init_missing_customer_id(self, temp_dir):
        """Test initialization with missing customer_id."""
        context = {"input": {"data_dir": temp_dir}}
        result = journal_init.main(context)

        assert result["status"] == "error"
        assert "customer_id" in result["message"]

    def test_init_creates_config(self, temp_dir, customer_id):
        """Test that initialization creates config file."""
        context = {
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        }
        journal_init.main(context)

        config_file = Path(temp_dir) / customer_id / "journal" / "config.json"
        assert config_file.exists()

        with open(config_file) as f:
            config = json.load(f)
        assert config["customer_id"] == customer_id
        assert "storage_path" in config

    def test_init_creates_directories(self, temp_dir, customer_id):
        """Test that initialization creates necessary directories."""
        context = {
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        }
        journal_init.main(context)

        customer_dir = Path(temp_dir) / customer_id / "journal"
        assert customer_dir.exists()


class TestJournalRecord:
    """Test journal recording."""

    def test_record_simple_entry(self, temp_dir, customer_id):
        """Test recording a simple journal entry."""
        # Initialize first
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Today was a productive day!",
            },
        }
        result = journal_record.main(context)

        assert result["status"] == "success"
        assert "entry_id" in result["result"]
        assert "created_at" in result["result"]

    def test_record_with_tags(self, temp_dir, customer_id):
        """Test recording an entry with tags."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Deep work session",
                "tags": ["work", "focus"],
            },
        }
        result = journal_record.main(context)

        assert result["status"] == "success"
        assert "work" in result["result"]["tags"]
        assert "focus" in result["result"]["tags"]

    def test_record_with_energy_level(self, temp_dir, customer_id):
        """Test recording an entry with energy level."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Feeling great!",
                "energy_level": 8,
            },
        }
        result = journal_record.main(context)

        assert result["status"] == "success"
        assert "entry_id" in result["result"]
        assert result["result"]["metadata"]["energy_level"] == 8

    def test_record_with_mood(self, temp_dir, customer_id):
        """Test recording an entry with mood."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Happy day",
                "emotional_state": "happy",
            },
        }
        result = journal_record.main(context)

        assert result["status"] == "success"
        assert result["result"]["metadata"]["emotional_state"] == "happy"

    def test_record_missing_content(self, temp_dir, customer_id):
        """Test recording without content."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })

        context = {
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        }
        result = journal_record.main(context)

        assert result["status"] == "error"
        assert "content" in result["message"]

    def test_record_without_init(self, temp_dir, customer_id):
        """Test recording without initialization returns error."""
        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Orphan entry",
            },
        }
        result = journal_record.main(context)

        # Without initialization, should return error
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()


class TestJournalSearch:
    """Test journal searching."""

    def test_search_by_query(self, temp_dir, customer_id):
        """Test searching entries by query."""
        # Setup
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Meeting with the team about project X",
            },
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Deep work on coding",
            },
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "query": "meeting",
            },
        }
        result = journal_search.main(context)

        assert result["status"] == "success"
        assert len(result["result"]["entries"]) == 1
        assert "meeting" in result["result"]["entries"][0]["content"].lower()

    def test_search_by_tags(self, temp_dir, customer_id):
        """Test searching entries by tags."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Work entry",
                "tags": ["work"],
            },
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Personal entry",
                "tags": ["personal"],
            },
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "tags": ["work"],
            },
        }
        result = journal_search.main(context)

        assert result["status"] == "success"
        assert len(result["result"]["entries"]) == 1
        assert result["result"]["entries"][0]["content"] == "Work entry"

    def test_search_empty_results(self, temp_dir, customer_id):
        """Test searching with no matches."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Some entry",
            },
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "query": "nonexistent",
            },
        }
        result = journal_search.main(context)

        assert result["status"] == "success"
        assert len(result["result"]["entries"]) == 0

    def test_search_without_init(self, temp_dir, customer_id):
        """Test searching without initialization returns error."""
        context = {
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        }
        result = journal_search.main(context)

        # Without initialization, should return error
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()


class TestJournalExport:
    """Test journal exporting."""

    def test_export_json(self, temp_dir, customer_id):
        """Test exporting to JSON format."""
        # Setup
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Entry to export",
            },
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "format": "json",
            },
        }
        result = journal_export.main(context)

        assert result["status"] == "success"
        assert result["result"]["format"] == "json"
        assert "output_path" in result["result"]
        assert result["result"]["entry_count"] >= 1

    def test_export_markdown(self, temp_dir, customer_id):
        """Test exporting to Markdown format."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })
        journal_record.main({
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "content": "Entry for markdown",
            },
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "format": "markdown",
            },
        }
        result = journal_export.main(context)

        assert result["status"] == "success"
        assert result["result"]["format"] == "markdown"
        assert "output_path" in result["result"]

    def test_export_empty_journal(self, temp_dir, customer_id):
        """Test exporting empty journal."""
        journal_init.main({
            "customer_id": customer_id,
            "input": {"data_dir": temp_dir},
        })

        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "format": "json",
            },
        }
        result = journal_export.main(context)

        assert result["status"] == "success"
        assert result["result"]["entry_count"] == 0

    def test_export_without_init(self, temp_dir, customer_id):
        """Test exporting without initialization returns error."""
        context = {
            "customer_id": customer_id,
            "input": {
                "data_dir": temp_dir,
                "format": "json",
            },
        }
        result = journal_export.main(context)

        # Without initialization, should return error
        assert result["status"] == "error"
        assert "not initialized" in result["message"].lower()
