"""
Tasks Scheduler Module - Task scheduling and queue management.
"""
import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Optional


@dataclass
class TaskScheduler:
    """Schedule and manage recurring tasks."""
    
    jobs: dict = field(default_factory=dict)
    
    def add_job(self, func: Callable, trigger: str, job_id: str, **kwargs) -> str:
        """Add a scheduled job."""
        job = {
            "id": job_id,
            "func": func,
            "trigger": trigger,
            "kwargs": kwargs,
            "paused": False,
            "created_at": datetime.now().isoformat(),
        }
        
        self.jobs[job_id] = job
        return job_id
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            return True
        return False
    
    def get_job(self, job_id: str) -> Optional[dict]:
        """Get a job by ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self) -> list[dict]:
        """List all scheduled jobs."""
        return list(self.jobs.values())
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a job."""
        if job_id in self.jobs:
            self.jobs[job_id]["paused"] = True
            return True
        return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if job_id in self.jobs:
            self.jobs[job_id]["paused"] = False
            return True
        return False


@dataclass
class CronParser:
    """Parse and evaluate cron expressions."""
    
    def parse(self, cron: str) -> dict:
        """Parse a cron expression."""
        parts = cron.split()
        
        if len(parts) != 5:
            raise ValueError("Invalid cron expression: must have 5 parts")
        
        return {
            "minutes": self._parse_field(parts[0], 0, 59),
            "hours": self._parse_field(parts[1], 0, 23),
            "days_of_month": self._parse_field(parts[2], 1, 31),
            "months": self._parse_field(parts[3], 1, 12),
            "days_of_week": self._parse_field(parts[4], 0, 6),
        }
    
    def _parse_field(self, field: str, min_val: int, max_val: int) -> list[int]:
        """Parse a single cron field."""
        values = []
        
        if field == "*":
            return list(range(min_val, max_val + 1))
        
        for part in field.split(","):
            if "/" in part:
                # Step notation: */15 or 0-30/5
                range_part, step = part.split("/")
                step = int(step)
                
                if range_part == "*":
                    start, end = min_val, max_val
                elif "-" in range_part:
                    start, end = map(int, range_part.split("-"))
                else:
                    start = end = int(range_part)
                
                values.extend(range(start, end + 1, step))
            elif "-" in part:
                # Range notation: 1-5
                start, end = map(int, part.split("-"))
                values.extend(range(start, end + 1))
            else:
                # Single value
                values.append(int(part))
        
        return sorted(list(set(values)))
    
    def validate(self, cron: str) -> bool:
        """Validate a cron expression."""
        try:
            self.parse(cron)
            return True
        except ValueError:
            return False
    
    def get_next_run(self, cron: str, from_time: Optional[datetime] = None) -> datetime:
        """Calculate next execution time from cron expression."""
        parsed = self.parse(cron)
        
        if from_time is None:
            from_time = datetime.now()
        
        # Start from next minute
        next_run = from_time + timedelta(minutes=1)
        next_run = next_run.replace(second=0, microsecond=0)
        
        # Find next matching time (simple implementation)
        for _ in range(366 * 24 * 60):  # Max search one year in minutes
            if (next_run.minute in parsed["minutes"] and
                next_run.hour in parsed["hours"] and
                next_run.month in parsed["months"]):
                
                # Check day constraints
                if (next_run.day in parsed["days_of_month"] or
                    next_run.weekday() in parsed["days_of_week"]):
                    return next_run
            
            next_run += timedelta(minutes=1)
        
        raise ValueError("Could not find next run time")


@dataclass
class TaskQueue:
    """Async task queue with priority support."""
    
    tasks: list = field(default_factory=list)
    default_timeout: int = 60
    _counter: int = field(default=0, init=False)
    
    async def enqueue(self, task_func: Callable, priority: int = 5, **kwargs) -> str:
        """Add a task to the queue."""
        self._counter += 1
        task_id = f"task_{self._counter}_{datetime.now().timestamp()}"
        
        task = {
            "id": task_id,
            "func": task_func,
            "priority": priority,
            "kwargs": kwargs,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
        }
        
        self.tasks.append(task)
        self.tasks.sort(key=lambda t: t["priority"])
        
        return task_id
    
    async def dequeue(self) -> Optional[dict]:
        """Get next task from queue."""
        pending = [t for t in self.tasks if t["status"] == "pending"]
        if not pending:
            return None
        
        task = pending[0]
        task["status"] = "processing"
        return task
    
    async def execute(self, task_func: Callable, timeout: Optional[int] = None) -> Any:
        """Execute a task with timeout."""
        timeout = timeout or self.default_timeout
        
        return await asyncio.wait_for(task_func(), timeout=timeout)
    
    async def cancel(self, task_id: str) -> bool:
        """Cancel a pending task."""
        for task in self.tasks:
            if task["id"] == task_id and task["status"] == "pending":
                task["status"] = "cancelled"
                return True
        return False
    
    def size(self) -> int:
        """Get queue size."""
        return len([t for t in self.tasks if t["status"] == "pending"])


@dataclass
class RecurringTask:
    """A recurring scheduled task."""
    
    func: Callable
    cron: str
    task_id: str
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    def __post_init__(self):
        if self.next_run is None:
            parser = CronParser()
            self.next_run = parser.get_next_run(self.cron)
    
    def get_next_run(self, from_time: Optional[datetime] = None) -> datetime:
        """Calculate next run time."""
        parser = CronParser()
        return parser.get_next_run(self.cron, from_time)
    
    def is_due(self) -> bool:
        """Check if task is due for execution."""
        if not self.enabled:
            return False
        
        if self.next_run is None:
            return True
        
        return datetime.now() >= self.next_run
    
    def record_execution(self, success: bool) -> None:
        """Record task execution."""
        self.execution_count += 1
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
        
        self.last_run = datetime.now()
        self.next_run = self.get_next_run()


@dataclass
class SchedulerPersistence:
    """Persist scheduler state."""
    
    storage_path: Path
    
    def __post_init__(self):
        self.storage_path = Path(self.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def save_state(self, scheduler: TaskScheduler) -> bool:
        """Save scheduler state."""
        state_file = self.storage_path / "scheduler_state.json"
        
        state = {
            "jobs": [
                {
                    "id": job["id"],
                    "trigger": job["trigger"],
                    "paused": job.get("paused", False),
                    "created_at": job.get("created_at"),
                }
                for job in scheduler.list_jobs()
            ],
            "saved_at": datetime.now().isoformat()
        }
        
        state_file.write_text(json.dumps(state, indent=2))
        return True
    
    def load_state(self, scheduler: TaskScheduler) -> bool:
        """Load scheduler state."""
        state_file = self.storage_path / "scheduler_state.json"
        
        if not state_file.exists():
            return False
        
        state = json.loads(state_file.read_text())
        
        # Note: Actual job functions cannot be restored from state
        # This would require job registration system
        
        return True
    
    def save_history(self, history: list[dict]) -> bool:
        """Save task execution history."""
        history_file = self.storage_path / "task_history.json"
        history_file.write_text(json.dumps(history, indent=2))
        return True


@dataclass
class SchedulerMetrics:
    """Track scheduler metrics."""
    
    scheduler: TaskScheduler
    
    def get_statistics(self) -> dict:
        """Get scheduler statistics."""
        jobs = self.scheduler.list_jobs()
        
        total = len(jobs)
        paused = sum(1 for j in jobs if j.get("paused"))
        active = total - paused
        
        return {
            "total_jobs": total,
            "active_jobs": active,
            "paused_jobs": paused,
        }
    
    def get_job_stats(self, job_id: str) -> dict:
        """Get statistics for a specific job."""
        job = self.scheduler.get_job(job_id)
        
        if job is None:
            return {}
        
        # Note: In real implementation, would track actual executions
        return {
            "job_id": job_id,
            "execution_count": 0,
            "success_rate": 0.0,
        }
