"""Task Scheduler tests - DISABLED (组件已标记 LEGACY，使用 OpenClaw 原生 task)"""

import pytest

# 标记整个模块跳过 - Scheduler 已标记 LEGACY，OpenClaw 原生 task 已替代
pytestmark = pytest.mark.skip(reason="Scheduler 已标记 LEGACY (v2.4)，使用 OpenClaw 原生 cron/task")

# 保留原始导入和测试代码供参考
"""
import pytest
from src.tasks.scheduler import TaskScheduler, TaskQueue


class TestTaskQueue:
    async def test_enqueue_task(self):
        ...

    async def test_dequeue_task(self):
        ...

    async def test_task_priority(self):
        ...

    async def test_cancel_task(self):
        ...

    async def test_task_timeout(self):
        ...
"""
