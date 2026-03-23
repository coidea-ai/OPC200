"""opc-milestone-tracker scripts package.

This package contains scripts for the milestone tracker skill.
"""

from .init import main as init
from .detect import main as detect
from .notify import main as notify

__all__ = ["init", "detect", "notify"]
