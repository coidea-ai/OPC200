"""Tests for milestones command."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.commands import milestones


def test_detect_milestone():
    result = milestones.run("OPC-001", {"content": "Finally launched the product!", "day": 28})
    assert result["status"] == "success"
    assert result["result"]["candidate"]["raw_content"] == "Finally launched the product!"
    assert result["result"]["candidate"]["day"] == 28


def test_detect_first_entry_milestone():
    result = milestones.run("OPC-001", {"content": "这是第一个记录，开始了！", "day": 1})
    assert result["status"] == "success"
    assert result["result"]["candidate"]["raw_content"] == "这是第一个记录，开始了！"


def test_no_milestone():
    result = milestones.run("OPC-001", {"content": "Just another regular day.", "day": 10})
    assert result["status"] == "success"
    assert result["result"]["candidate"]["raw_content"] == "Just another regular day."
