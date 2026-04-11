"""Tests for export command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import export


def test_export_markdown():
    result = export.run("OPC-001", {"format": "markdown", "time_range": "weekly"})
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "markdown"
    assert result["result"]["time_range"] == "weekly"


def test_export_defaults():
    result = export.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["export_format"] == "markdown"
    assert result["result"]["time_range"] == "all"
