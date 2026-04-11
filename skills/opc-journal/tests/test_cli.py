"""Tests for opc-journal CLI entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.main import main, parse_args


def test_help_command():
    result = main({"input": {"argv": ["help"]}, "customer_id": "OPC-001"})
    assert result["status"] == "success"
    assert result["result"]["help_displayed"]


def test_empty_argv():
    result = main({"input": {"argv": []}, "customer_id": "OPC-001"})
    assert result["status"] == "success"
    assert result["result"]["help_displayed"]


def test_unknown_command():
    result = main({"input": {"argv": ["foobar"]}, "customer_id": "OPC-001"})
    assert result["status"] == "error"
    assert "invalid choice" in result["message"]


def test_parse_from_text():
    result = main({"input": {"text": "status"}, "customer_id": "OPC-001"})
    assert result["status"] == "success"
    assert "journal" in result["message"].lower()
