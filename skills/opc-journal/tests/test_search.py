"""Tests for search command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import search


def test_search_basic():
    result = search.run("OPC-001", {"query": "pricing"})
    assert result["status"] == "success"
    assert result["result"]["query"] == "pricing"
    assert "memory_search" in result["result"]["tool_hint"]


def test_search_empty_query():
    result = search.run("OPC-001", {})
    assert result["status"] == "success"
    assert result["result"]["query"] == ""
