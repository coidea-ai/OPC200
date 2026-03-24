"""
Unit tests for tasks/scheduler.py - Task scheduling functionality.
Following TDD: Red-Green-Refactor cycle.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


class TestTaskScheduler:
    """Tests for task scheduler."""

    def test_scheduler_initialization(self):
        """Test scheduler initialization."""
        # Arrange & Act
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Assert
        assert scheduler is not None
        assert scheduler.jobs == {}

    def test_add_job(self):
        """Test adding a scheduled job."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        def test_task():
            return "done"

        # Act
        job_id = scheduler.add_job(func=test_task, trigger="interval", minutes=30, job_id="test_job")

        # Assert
        assert job_id == "test_job"
        assert "test_job" in scheduler.jobs

    def test_remove_job(self):
        """Test removing a scheduled job."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        def test_task():
            return "done"

        scheduler.add_job(func=test_task, trigger="interval", minutes=30, job_id="test_job")

        # Act
        result = scheduler.remove_job("test_job")

        # Assert
        assert result is True
        assert "test_job" not in scheduler.jobs

    def test_remove_nonexistent_job(self):
        """Test removing a non-existent job."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        # Act
        result = scheduler.remove_job("nonexistent")

        # Assert
        assert result is False

    def test_get_job(self):
        """Test retrieving a job by ID."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        def test_task():
            return "done"

        scheduler.add_job(func=test_task, trigger="interval", minutes=30, job_id="test_job")

        # Act
        job = scheduler.get_job("test_job")

        # Assert
        assert job is not None
        assert job["id"] == "test_job"

    def test_list_jobs(self):
        """Test listing all scheduled jobs."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        def task1():
            pass

        def task2():
            pass

        scheduler.add_job(func=task1, trigger="interval", minutes=30, job_id="job1")
        scheduler.add_job(func=task2, trigger="interval", hours=1, job_id="job2")

        # Act
        jobs = scheduler.list_jobs()

        # Assert
        assert len(jobs) == 2
        job_ids = [j["id"] for j in jobs]
        assert "job1" in job_ids
        assert "job2" in job_ids

    def test_pause_job(self):
        """Test pausing a job."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        def test_task():
            return "done"

        scheduler.add_job(func=test_task, trigger="interval", minutes=30, job_id="test_job")

        # Act
        result = scheduler.pause_job("test_job")

        # Assert
        assert result is True
        assert scheduler.get_job("test_job")["paused"] is True

    def test_resume_job(self):
        """Test resuming a paused job."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler

        scheduler = TaskScheduler()

        def test_task():
            return "done"

        scheduler.add_job(func=test_task, trigger="interval", minutes=30, job_id="test_job")
        scheduler.pause_job("test_job")

        # Act
        result = scheduler.resume_job("test_job")

        # Assert
        assert result is True
        assert scheduler.get_job("test_job")["paused"] is False


class TestCronExpressionParser:
    """Tests for cron expression parsing."""

    def test_parse_cron_minute(self):
        """Test parsing minute field."""
        # Arrange
        from src.tasks.scheduler import CronParser

        parser = CronParser()

        # Act
        result = parser.parse("*/15 * * * *")  # Every 15 minutes

        # Assert
        assert 0 in result["minutes"]
        assert 15 in result["minutes"]
        assert 30 in result["minutes"]
        assert 45 in result["minutes"]

    def test_parse_cron_hour(self):
        """Test parsing hour field."""
        # Arrange
        from src.tasks.scheduler import CronParser

        parser = CronParser()

        # Act
        result = parser.parse("0 9,17 * * *")  # At 9 AM and 5 PM

        # Assert
        assert result["hours"] == [9, 17]
        assert result["minutes"] == [0]

    def test_parse_cron_day_of_week(self):
        """Test parsing day of week field."""
        # Arrange
        from src.tasks.scheduler import CronParser

        parser = CronParser()

        # Act
        result = parser.parse("0 9 * * 1-5")  # Weekdays at 9 AM

        # Assert
        assert result["days_of_week"] == [1, 2, 3, 4, 5]  # Mon-Fri

    def test_get_next_run_time(self):
        """Test calculating next run time from cron."""
        # Arrange
        from src.tasks.scheduler import CronParser

        parser = CronParser()

        # Every day at 9 AM
        cron = "0 9 * * *"
        now = datetime(2024, 3, 15, 10, 0)  # 10 AM today

        # Act
        next_run = parser.get_next_run(cron, now)

        # Assert
        assert next_run.hour == 9
        assert next_run.day == 16  # Next day

    def test_validate_cron_expression(self):
        """Test validating cron expression."""
        # Arrange
        from src.tasks.scheduler import CronParser

        parser = CronParser()

        # Valid expressions
        assert parser.validate("0 9 * * *") is True
        assert parser.validate("*/15 * * * *") is True
        assert parser.validate("0 0 * * 0") is True

        # Invalid expressions
        assert parser.validate("60 * * * *") is False  # Invalid minute
        assert parser.validate("* 25 * * *") is False  # Invalid hour
        assert parser.validate("* * * *") is False  # Missing field


class TestTaskQueue:
    """Tests for task queue."""

    @pytest.mark.asyncio
    async def test_enqueue_task(self):
        """Test enqueuing a task."""
        # Arrange
        from src.tasks.scheduler import TaskQueue

        queue = TaskQueue()

        async def test_task():
            return "result"

        # Act
        task_id = await queue.enqueue(test_task, priority=1)

        # Assert
        assert task_id is not None
        assert queue.size() == 1

    @pytest.mark.asyncio
    async def test_dequeue_task(self):
        """Test dequeuing a task."""
        # Arrange
        from src.tasks.scheduler import TaskQueue

        queue = TaskQueue()

        async def test_task():
            return "result"

        await queue.enqueue(test_task, priority=1)

        # Act
        task = await queue.dequeue()

        # Assert
        assert task is not None
        assert queue.size() == 0

    @pytest.mark.asyncio
    async def test_task_priority(self):
        """Test task priority ordering."""
        # Arrange
        from src.tasks.scheduler import TaskQueue

        queue = TaskQueue()

        results = []

        async def low_priority_task():
            results.append("low")

        async def high_priority_task():
            results.append("high")

        await queue.enqueue(low_priority_task, priority=5)
        await queue.enqueue(high_priority_task, priority=1)

        # Act
        task1 = await queue.dequeue()
        task2 = await queue.dequeue()

        # Assert - High priority should come first
        assert task1["priority"] == 1
        assert task2["priority"] == 5

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test cancelling a queued task."""
        # Arrange
        from src.tasks.scheduler import TaskQueue

        queue = TaskQueue()

        async def test_task():
            return "result"

        task_id = await queue.enqueue(test_task)

        # Act
        result = await queue.cancel(task_id)

        # Assert
        assert result is True
        assert queue.size() == 0

    @pytest.mark.asyncio
    async def test_task_timeout(self):
        """Test task timeout handling."""
        # Arrange
        import asyncio
        from src.tasks.scheduler import TaskQueue

        queue = TaskQueue(default_timeout=1)  # 1 second timeout

        async def slow_task():
            await asyncio.sleep(10)
            return "result"

        # Act & Assert - use asyncio.TimeoutError for compatibility
        with pytest.raises(asyncio.TimeoutError):
            await queue.execute(slow_task)


class TestRecurringTask:
    """Tests for recurring task management."""

    def test_create_recurring_task(self):
        """Test creating a recurring task."""
        # Arrange
        from src.tasks.scheduler import RecurringTask

        def test_func():
            return "done"

        # Act
        task = RecurringTask(func=test_func, cron="0 9 * * *", task_id="daily_backup")

        # Assert
        assert task.id == "daily_backup"
        assert task.cron == "0 9 * * *"
        assert task.enabled is True

    def test_get_next_execution_time(self):
        """Test getting next execution time."""
        # Arrange
        from src.tasks.scheduler import RecurringTask

        def test_func():
            return "done"

        task = RecurringTask(func=test_func, cron="0 9 * * *", task_id="daily_task")

        now = datetime(2024, 3, 15, 10, 0)

        # Act
        next_run = task.get_next_run(now)

        # Assert
        assert next_run.hour == 9
        assert next_run > now

    def test_is_due_for_execution(self):
        """Test checking if task is due."""
        # Arrange
        from src.tasks.scheduler import RecurringTask
        from datetime import datetime, timedelta

        def test_func():
            return "done"

        task = RecurringTask(func=test_func, cron="0 * * * *", task_id="hourly_task")  # Every hour

        # Set last run to 2 hours ago and next_run to past
        task.last_run = datetime.now() - timedelta(hours=2)
        task.next_run = datetime.now() - timedelta(minutes=5)  # 5 minutes ago

        # Act
        is_due = task.is_due()

        # Assert
        assert is_due is True

    def test_execution_count_tracking(self):
        """Test tracking execution count."""
        # Arrange
        from src.tasks.scheduler import RecurringTask

        def test_func():
            return "done"

        task = RecurringTask(func=test_func, cron="0 * * * *", task_id="hourly_task")

        # Act
        task.record_execution(success=True)
        task.record_execution(success=True)
        task.record_execution(success=False)

        # Assert
        assert task.execution_count == 3
        assert task.success_count == 2
        assert task.failure_count == 1


class TestSchedulerPersistence:
    """Tests for scheduler state persistence."""

    def test_save_scheduler_state(self, temp_dir):
        """Test saving scheduler state."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler, SchedulerPersistence

        scheduler = TaskScheduler()
        scheduler.add_job(func=lambda: "test", trigger="interval", minutes=30, job_id="test_job")

        persistence = SchedulerPersistence(storage_path=temp_dir)

        # Act
        result = persistence.save_state(scheduler)

        # Assert
        assert result is True
        assert (temp_dir / "scheduler_state.json").exists()

    def test_load_scheduler_state(self, temp_dir):
        """Test loading scheduler state."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler, SchedulerPersistence

        scheduler = TaskScheduler()
        scheduler.add_job(func=lambda: "test", trigger="interval", minutes=30, job_id="test_job")

        persistence = SchedulerPersistence(storage_path=temp_dir)
        persistence.save_state(scheduler)

        # Create new scheduler and load state
        new_scheduler = TaskScheduler()

        # Act
        result = persistence.load_state(new_scheduler)

        # Assert
        assert result is True
        assert "test_job" in new_scheduler.jobs

    def test_save_task_history(self, temp_dir):
        """Test saving task execution history."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler, SchedulerPersistence

        persistence = SchedulerPersistence(storage_path=temp_dir)

        history = [
            {"task_id": "task1", "timestamp": datetime.now().isoformat(), "success": True},
            {"task_id": "task2", "timestamp": datetime.now().isoformat(), "success": False},
        ]

        # Act
        result = persistence.save_history(history)

        # Assert
        assert result is True
        assert (temp_dir / "task_history.json").exists()


class TestSchedulerMetrics:
    """Tests for scheduler metrics."""

    def test_get_scheduler_metrics(self):
        """Test getting scheduler metrics."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler, SchedulerMetrics

        scheduler = TaskScheduler()
        scheduler.add_job(func=lambda: "a", trigger="interval", minutes=30, job_id="job1")
        scheduler.add_job(func=lambda: "b", trigger="interval", hours=1, job_id="job2")
        scheduler.pause_job("job2")

        metrics = SchedulerMetrics(scheduler)

        # Act
        stats = metrics.get_statistics()

        # Assert
        assert stats["total_jobs"] == 2
        assert stats["active_jobs"] == 1
        assert stats["paused_jobs"] == 1

    def test_get_job_execution_stats(self):
        """Test getting job execution statistics."""
        # Arrange
        from src.tasks.scheduler import TaskScheduler, RecurringTask, SchedulerMetrics

        scheduler = TaskScheduler()

        task = RecurringTask(func=lambda: "test", cron="0 * * * *", task_id="test_task")
        task.record_execution(success=True)
        task.record_execution(success=True)
        task.record_execution(success=False)

        scheduler.jobs["test_task"] = task

        metrics = SchedulerMetrics(scheduler)

        # Act
        stats = metrics.get_job_stats("test_task")

        # Assert
        assert stats["execution_count"] == 3
        assert stats["success_rate"] == 2 / 3
