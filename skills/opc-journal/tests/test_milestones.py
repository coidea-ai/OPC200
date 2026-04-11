"""Tests for milestones command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import milestones


def test_detect_milestone():
    result = milestones.run("OPC-001", {"content": "Finally launched the product!", "day": 28})
    assert result["status"] == "success"
    assert result["result"]["count"] >= 1
    assert result["result"]["milestones_detected"][0]["milestone_id"] == "first_product_launch"


def test_detect_first_entry_milestone():
    result = milestones.run("OPC-001", {"content": "这是第一个记录，开始了！", "day": 1})
    assert result["status"] == "success"
    ids = [m["milestone_id"] for m in result["result"]["milestones_detected"]]
    assert "first_journal_entry" in ids


def test_no_milestone():
    result = milestones.run("OPC-001", {"content": "Just another regular day.", "day": 10})
    assert result["status"] == "success"
    assert result["result"]["count"] == 0
