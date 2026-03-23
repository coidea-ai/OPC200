# OPC200 - 任务调度模块
# 管理异步任务、定时任务、后台处理

import os
import json
import asyncio
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Coroutine
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import logging
import uuid

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消
    RETRYING = "retrying"    # 重试中


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0    # 紧急
    HIGH = 1        # 高
    NORMAL = 2      # 正常
    LOW = 3         # 低
    BACKGROUND = 4  # 后台


@dataclass
class Task:
    """任务定义"""
    id: str
    name: str
    description: str
    priority: TaskPriority
    status: TaskStatus
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    payload: Dict[str, Any] = None
    result: Any = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    dependencies: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'priority': self.priority.value,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'payload': self.payload,
            'result': self.result,
            'error': self.error,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'dependencies': self.dependencies or []
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            id=data['id'],
            name=data['name'],
            description=data['description'],
            priority=TaskPriority(data['priority']),
            status=TaskStatus(data['status']),
            created_at=datetime.fromisoformat(data['created_at']),
            scheduled_at=datetime.fromisoformat(data['scheduled_at']) if data.get('scheduled_at') else None,
            started_at=datetime.fromisoformat(data['started_at']) if data.get('started_at') else None,
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            payload=data.get('payload', {}),
            result=data.get('result'),
            error=data.get('error'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            dependencies=data.get('dependencies', [])
        )


class TaskScheduler:
    """
    任务调度器
    
    功能：
    - 任务队列管理
    - 优先级调度
    - 依赖解析
    - 重试机制
    - 定时任务
    """
    
    def __init__(self, db_path: str, max_workers: int = 5):
        """
        Args:
            db_path: 任务数据库路径
            max_workers: 最大并发工作数
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        
        self._task_handlers: Dict[str, Callable] = {}
        self._running = False
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._workers: List[asyncio.Task] = []
        
        self._ensure_db()
    
    def _ensure_db(self):
        """确保数据库结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    priority INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    scheduled_at TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    payload TEXT,
                    result TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    dependencies TEXT
                )
            """)
            
            # 定时任务表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    cron_expression TEXT,
                    next_run_at TEXT,
                    payload TEXT,
                    enabled INTEGER DEFAULT 1,
                    last_run_at TEXT
                )
            """)
            
            conn.commit()
    
    def register_handler(self, task_name: str, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_name: 任务名称
            handler: 处理函数，接收 task.payload 作为参数
        """
        self._task_handlers[task_name] = handler
        logger.info(f"Registered handler for task: {task_name}")
    
    async def submit(self,
                    name: str,
                    description: str = "",
                    payload: Dict[str, Any] = None,
                    priority: TaskPriority = TaskPriority.NORMAL,
                    scheduled_at: Optional[datetime] = None,
                    dependencies: List[str] = None) -> Task:
        """
        提交任务
        
        Args:
            name: 任务名称（需已注册处理器）
            description: 任务描述
            payload: 任务数据
            priority: 优先级
            scheduled_at: 计划执行时间
            dependencies: 依赖任务ID列表
        """
        task = Task(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            scheduled_at=scheduled_at,
            payload=payload or {},
            dependencies=dependencies or []
        )
        
        # 保存到数据库
        await self._save_task(task)
        
        # 如果立即执行，加入队列
        if scheduled_at is None or scheduled_at <= datetime.now():
            await self._queue.put((priority.value, task.id))
        
        logger.info(f"Task submitted: {task.id} ({name})")
        return task
    
    async def _save_task(self, task: Task):
        """保存任务到数据库"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_save_task, task)
    
    def _sync_save_task(self, task: Task):
        """同步保存任务"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks 
                (id, name, description, priority, status, created_at, scheduled_at,
                 started_at, completed_at, payload, result, error, retry_count, 
                 max_retries, dependencies)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.name, task.description, task.priority.value,
                task.status.value, task.created_at.isoformat(),
                task.scheduled_at.isoformat() if task.scheduled_at else None,
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                json.dumps(task.payload),
                json.dumps(task.result) if task.result else None,
                task.error, task.retry_count, task.max_retries,
                json.dumps(task.dependencies)
            ))
            conn.commit()
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get_task, task_id)
    
    def _sync_get_task(self, task_id: str) -> Optional[Task]:
        """同步获取任务"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
            
            if row:
                return self._row_to_task(row)
            return None
    
    def _row_to_task(self, row) -> Task:
        """数据库行转 Task"""
        return Task(
            id=row[0],
            name=row[1],
            description=row[2] or "",
            priority=TaskPriority(row[3]),
            status=TaskStatus(row[4]),
            created_at=datetime.fromisoformat(row[5]),
            scheduled_at=datetime.fromisoformat(row[6]) if row[6] else None,
            started_at=datetime.fromisoformat(row[7]) if row[7] else None,
            completed_at=datetime.fromisoformat(row[8]) if row[8] else None,
            payload=json.loads(row[9]) if row[9] else {},
            result=json.loads(row[10]) if row[10] else None,
            error=row[11],
            retry_count=row[12] or 0,
            max_retries=row[13] or 3,
            dependencies=json.loads(row[14]) if row[14] else []
        )
    
    async def start(self):
        """启动调度器"""
        self._running = True
        
        # 启动工作线程
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self._workers.append(worker)
        
        # 启动定时任务检查
        asyncio.create_task(self._scheduled_task_checker())
        
        logger.info(f"Task scheduler started with {self.max_workers} workers")
    
    async def stop(self):
        """停止调度器"""
        self._running = False
        
        # 取消所有工作线程
        for worker in self._workers:
            worker.cancel()
        
        await asyncio.gather(*self._workers, return_exceptions=True)
        logger.info("Task scheduler stopped")
    
    async def _worker_loop(self, worker_id: str):
        """工作线程主循环"""
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # 获取任务
                priority, task_id = await asyncio.wait_for(
                    self._queue.get(), timeout=1.0
                )
                
                await self._execute_task(task_id)
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
    
    async def _execute_task(self, task_id: str):
        """执行任务"""
        task = await self.get_task(task_id)
        if not task:
            return
        
        # 检查依赖
        if task.dependencies:
            for dep_id in task.dependencies:
                dep_task = await self.get_task(dep_id)
                if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                    logger.info(f"Task {task_id} waiting for dependency {dep_id}")
                    # 重新排队，稍后重试
                    await asyncio.sleep(5)
                    await self._queue.put((task.priority.value, task_id))
                    return
        
        # 更新状态
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        await self._save_task(task)
        
        # 获取处理器
        handler = self._task_handlers.get(task.name)
        if not handler:
            task.status = TaskStatus.FAILED
            task.error = f"No handler registered for task: {task.name}"
            await self._save_task(task)
            return
        
        # 执行
        try:
            logger.info(f"Executing task: {task_id} ({task.name})")
            
            if asyncio.iscoroutinefunction(handler):
                result = await handler(task.payload)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, handler, task.payload)
            
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()
            
            logger.info(f"Task completed: {task_id}")
            
        except Exception as e:
            logger.error(f"Task failed: {task_id} - {e}")
            
            task.retry_count += 1
            if task.retry_count < task.max_retries:
                task.status = TaskStatus.RETRYING
                # 指数退避
                delay = 2 ** task.retry_count
                await asyncio.sleep(delay)
                await self._queue.put((task.priority.value, task_id))
            else:
                task.status = TaskStatus.FAILED
                task.error = str(e)
        
        await self._save_task(task)
    
    async def _scheduled_task_checker(self):
        """定时任务检查器"""
        while self._running:
            try:
                await self._check_scheduled_tasks()
                await asyncio.sleep(60)  # 每分钟检查一次
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduled task checker error: {e}")
    
    async def _check_scheduled_tasks(self):
        """检查并触发定时任务"""
        loop = asyncio.get_event_loop()
        now = datetime.now()
        
        def _check():
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """SELECT * FROM scheduled_tasks 
                       WHERE enabled = 1 AND next_run_at <= ?""",
                    (now.isoformat(),)
                ).fetchall()
                
                for row in rows:
                    # 提交任务
                    asyncio.create_task(self.submit(
                        name=row[1],
                        description=row[2] or "",
                        payload=json.loads(row[5]) if row[5] else {}
                    ))
                    
                    # 更新下次执行时间
                    # 简化实现：固定间隔
                    next_run = now + timedelta(minutes=5)  # 默认5分钟间隔
                    conn.execute(
                        "UPDATE scheduled_tasks SET next_run_at = ?, last_run_at = ? WHERE id = ?",
                        (next_run.isoformat(), now.isoformat(), row[0])
                    )
                
                conn.commit()
        
        await loop.run_in_executor(None, _check)
    
    def schedule_recurring(self,
                          name: str,
                          description: str,
                          interval_minutes: int,
                          payload: Dict[str, Any] = None) -> str:
        """
        创建定时任务
        
        Args:
            name: 任务名称
            description: 描述
            interval_minutes: 执行间隔（分钟）
            payload: 任务数据
            
        Returns:
            定时任务ID
        """
        task_id = str(uuid.uuid4())[:8]
        next_run = datetime.now() + timedelta(minutes=interval_minutes)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO scheduled_tasks 
                (id, name, description, next_run_at, payload)
                VALUES (?, ?, ?, ?, ?)
            """, (
                task_id, name, description, next_run.isoformat(),
                json.dumps(payload or {})
            ))
            conn.commit()
        
        logger.info(f"Scheduled recurring task: {task_id} ({name}) every {interval_minutes}min")
        return task_id
    
    async def get_pending_tasks(self) -> List[Task]:
        """获取待处理任务"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get_pending)
    
    def _sync_get_pending(self) -> List[Task]:
        """同步获取待处理任务"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE status IN (?, ?) ORDER BY priority, created_at",
                (TaskStatus.PENDING.value, TaskStatus.RETRYING.value)
            ).fetchall()
            return [self._row_to_task(row) for row in rows]
    
    async def get_task_stats(self, days: int = 7) -> Dict[str, Any]:
        """获取任务统计"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get_stats, days)
    
    def _sync_get_stats(self, days: int) -> Dict[str, Any]:
        """同步获取统计"""
        since = (datetime.now() - timedelta(days=days)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            # 状态分布
            status_dist = conn.execute(
                """SELECT status, COUNT(*) FROM tasks 
                   WHERE created_at >= ? GROUP BY status""",
                (since,)
            ).fetchall()
            
            # 平均执行时间
            avg_time = conn.execute(
                """SELECT AVG(
                       julianday(completed_at) - julianday(started_at)
                   ) * 24 * 60  -- 转换为分钟
                   FROM tasks 
                   WHERE status = ? AND created_at >= ?""",
                (TaskStatus.COMPLETED.value, since)
            ).fetchone()
            
            # 失败率
            total = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE created_at >= ?",
                (since,)
            ).fetchone()[0]
            
            failed = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE status = ? AND created_at >= ?",
                (TaskStatus.FAILED.value, since)
            ).fetchone()[0]
        
        return {
            'period_days': days,
            'total_tasks': total,
            'status_distribution': {status: count for status, count in status_dist},
            'avg_execution_minutes': round(avg_time[0], 2) if avg_time[0] else 0,
            'failure_rate': round(failed / total, 3) if total > 0 else 0
        }


# 预定义的任务处理器
class CommonTaskHandlers:
    """常用任务处理器"""
    
    @staticmethod
    async def generate_daily_summary(payload: Dict) -> Dict:
        """生成每日摘要"""
        user_id = payload.get('user_id')
        logger.info(f"Generating daily summary for user: {user_id}")
        
        # 实际实现会调用 journal 模块
        return {
            'type': 'daily_summary',
            'user_id': user_id,
            'generated_at': datetime.now().isoformat()
        }
    
    @staticmethod
    async def analyze_patterns(payload: Dict) -> Dict:
        """分析用户模式"""
        user_id = payload.get('user_id')
        logger.info(f"Analyzing patterns for user: {user_id}")
        
        return {
            'type': 'pattern_analysis',
            'user_id': user_id,
            'analyzed_at': datetime.now().isoformat()
        }
    
    @staticmethod
    async def backup_data(payload: Dict) -> Dict:
        """备份数据"""
        user_id = payload.get('user_id')
        logger.info(f"Backing up data for user: {user_id}")
        
        return {
            'type': 'backup',
            'user_id': user_id,
            'backup_at': datetime.now().isoformat()
        }
    
    @staticmethod
    async def cleanup_old_entries(payload: Dict) -> Dict:
        """清理旧条目"""
        days = payload.get('retention_days', 365)
        logger.info(f"Cleaning up entries older than {days} days")
        
        return {
            'type': 'cleanup',
            'retention_days': days,
            'cleaned_at': datetime.now().isoformat()
        }


def create_default_scheduler(db_path: str) -> TaskScheduler:
    """创建默认配置的调度器"""
    scheduler = TaskScheduler(db_path)
    
    # 注册常用处理器
    handlers = CommonTaskHandlers()
    scheduler.register_handler("daily_summary", handlers.generate_daily_summary)
    scheduler.register_handler("analyze_patterns", handlers.analyze_patterns)
    scheduler.register_handler("backup_data", handlers.backup_data)
    scheduler.register_handler("cleanup_old_entries", handlers.cleanup_old_entries)
    
    return scheduler
