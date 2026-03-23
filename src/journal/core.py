# OPC200 - Journal 服务核心模块
# 提供日志记录、检索、摘要生成功能

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import logging

logger = logging.getLogger(__name__)

@dataclass
class JournalEntry:
    """日志条目数据结构"""
    id: str
    timestamp: datetime
    entry_type: str  # thought, action, milestone, insight, system
    content: str
    metadata: Dict[str, Any]
    tags: List[str]
    sentiment: Optional[float] = None  # -1.0 to 1.0
    vector_embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'entry_type': self.entry_type,
            'content': self.content,
            'metadata': self.metadata,
            'tags': self.tags,
            'sentiment': self.sentiment,
            'vector_embedding': self.vector_embedding
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JournalEntry':
        return cls(
            id=data['id'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            entry_type=data['entry_type'],
            content=data['content'],
            metadata=data.get('metadata', {}),
            tags=data.get('tags', []),
            sentiment=data.get('sentiment'),
            vector_embedding=data.get('vector_embedding')
        )


class JournalCore:
    """
    Journal 核心管理器
    
    功能：
    - 日志条目 CRUD
    - 时间范围查询
    - 类型过滤
    - 标签管理
    """
    
    def __init__(self, db_path: str, vault_key: Optional[str] = None):
        """
        初始化 Journal Core
        
        Args:
            db_path: SQLite 数据库路径
            vault_key: 数据保险箱密钥（可选，用于加密敏感字段）
        """
        self.db_path = Path(db_path)
        self.vault_key = vault_key
        self._ensure_db()
        
    def _ensure_db(self):
        """确保数据库和表结构存在"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS journal_entries (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    tags TEXT,
                    sentiment REAL,
                    vector_embedding TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON journal_entries(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entry_type 
                ON journal_entries(entry_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags 
                ON journal_entries(tags)
            """)
            conn.commit()
    
    def _generate_id(self, content: str, timestamp: datetime) -> str:
        """生成唯一 ID"""
        data = f"{content}:{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    async def record(self, 
                     content: str, 
                     entry_type: str = "thought",
                     metadata: Optional[Dict[str, Any]] = None,
                     tags: Optional[List[str]] = None,
                     sentiment: Optional[float] = None) -> JournalEntry:
        """
        记录日志条目
        
        Args:
            content: 日志内容
            entry_type: 条目类型 (thought/action/milestone/insight/system)
            metadata: 元数据字典
            tags: 标签列表
            sentiment: 情感分数 (-1.0 到 1.0)
            
        Returns:
            JournalEntry 对象
        """
        timestamp = datetime.now()
        entry_id = self._generate_id(content, timestamp)
        
        entry = JournalEntry(
            id=entry_id,
            timestamp=timestamp,
            entry_type=entry_type,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
            sentiment=sentiment
        )
        
        # 异步写入数据库
        await self._save_entry(entry)
        logger.info(f"Journal entry recorded: {entry_id}")
        
        return entry
    
    async def _save_entry(self, entry: JournalEntry):
        """保存条目到数据库"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._sync_save, entry)
    
    def _sync_save(self, entry: JournalEntry):
        """同步保存（用于 executor）"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO journal_entries 
                (id, timestamp, entry_type, content, metadata, tags, sentiment, vector_embedding)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.timestamp.isoformat(),
                entry.entry_type,
                entry.content,
                json.dumps(entry.metadata),
                json.dumps(entry.tags),
                entry.sentiment,
                json.dumps(entry.vector_embedding) if entry.vector_embedding else None
            ))
            conn.commit()
    
    async def get(self, entry_id: str) -> Optional[JournalEntry]:
        """获取单个条目"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_get, entry_id)
    
    def _sync_get(self, entry_id: str) -> Optional[JournalEntry]:
        """同步获取"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM journal_entries WHERE id = ?", 
                (entry_id,)
            ).fetchone()
            
            if row:
                return self._row_to_entry(row)
            return None
    
    async def query(self,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    entry_types: Optional[List[str]] = None,
                    tags: Optional[List[str]] = None,
                    limit: int = 100,
                    offset: int = 0) -> List[JournalEntry]:
        """
        查询日志条目
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
            entry_types: 类型过滤
            tags: 标签过滤（包含任一标签）
            limit: 返回数量限制
            offset: 分页偏移
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_query, start_time, end_time, entry_types, tags, limit, offset
        )
    
    def _sync_query(self, start_time, end_time, entry_types, tags, limit, offset) -> List[JournalEntry]:
        """同步查询"""
        conditions = []
        params = []
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        if entry_types:
            placeholders = ','.join('?' * len(entry_types))
            conditions.append(f"entry_type IN ({placeholders})")
            params.extend(entry_types)
        
        query = "SELECT * FROM journal_entries"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(query, params).fetchall()
            entries = [self._row_to_entry(row) for row in rows]
        
        # 标签过滤在内存中进行（SQLite JSON 查询较复杂）
        if tags:
            entries = [
                e for e in entries 
                if any(tag in e.tags for tag in tags)
            ]
        
        return entries
    
    def _row_to_entry(self, row) -> JournalEntry:
        """数据库行转换为 Entry 对象"""
        return JournalEntry(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            entry_type=row[2],
            content=row[3],
            metadata=json.loads(row[4]) if row[4] else {},
            tags=json.loads(row[5]) if row[5] else [],
            sentiment=row[6],
            vector_embedding=json.loads(row[7]) if row[7] else None
        )
    
    async def get_daily_summary(self, date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        获取每日摘要
        
        Args:
            date: 指定日期，默认今天
        """
        if date is None:
            date = datetime.now()
        
        start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        
        entries = await self.query(start_time=start, end_time=end, limit=1000)
        
        # 统计
        type_counts = {}
        sentiments = []
        
        for entry in entries:
            type_counts[entry.entry_type] = type_counts.get(entry.entry_type, 0) + 1
            if entry.sentiment is not None:
                sentiments.append(entry.sentiment)
        
        return {
            'date': start.date().isoformat(),
            'total_entries': len(entries),
            'type_distribution': type_counts,
            'avg_sentiment': sum(sentiments) / len(sentiments) if sentiments else None,
            'key_entries': [e.to_dict() for e in entries[:10]]
        }
    
    async def search_by_content(self, keyword: str, limit: int = 50) -> List[JournalEntry]:
        """关键词搜索（简单 LIKE 查询）"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_search, keyword, limit)
    
    def _sync_search(self, keyword: str, limit: int) -> List[JournalEntry]:
        """同步搜索"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM journal_entries WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{keyword}%", limit)
            ).fetchall()
            return [self._row_to_entry(row) for row in rows]
    
    async def delete(self, entry_id: str) -> bool:
        """删除条目"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_delete, entry_id)
    
    def _sync_delete(self, entry_id: str) -> bool:
        """同步删除"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM journal_entries WHERE id = ?", 
                (entry_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
    
    async def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """获取统计信息"""
        start = datetime.now() - timedelta(days=days)
        
        with sqlite3.connect(self.db_path) as conn:
            # 总条目数
            total = conn.execute(
                "SELECT COUNT(*) FROM journal_entries WHERE timestamp >= ?",
                (start.isoformat(),)
            ).fetchone()[0]
            
            # 类型分布
            type_dist = conn.execute(
                """SELECT entry_type, COUNT(*) FROM journal_entries 
                   WHERE timestamp >= ? GROUP BY entry_type""",
                (start.isoformat(),)
            ).fetchall()
            
            # 每日条目数
            daily = conn.execute(
                """SELECT date(timestamp), COUNT(*) FROM journal_entries 
                   WHERE timestamp >= ? GROUP BY date(timestamp)""",
                (start.isoformat(),)
            ).fetchall()
        
        return {
            'period_days': days,
            'total_entries': total,
            'type_distribution': {t: c for t, c in type_dist},
            'daily_counts': {d: c for d, c in daily}
        }


class JournalManager:
    """高级 Journal 管理器 - 提供批量操作和导出功能"""
    
    def __init__(self, core: JournalCore):
        self.core = core
    
    async def export_to_json(self, 
                            output_path: str,
                            start_time: Optional[datetime] = None,
                            end_time: Optional[datetime] = None) -> str:
        """
        导出日志到 JSON
        
        Returns:
            输出文件路径
        """
        entries = await self.core.query(
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        data = {
            'exported_at': datetime.now().isoformat(),
            'total_entries': len(entries),
            'entries': [e.to_dict() for e in entries]
        }
        
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Journal exported to {output}")
        return str(output)
    
    async def import_from_json(self, input_path: str, merge: bool = True) -> int:
        """
        从 JSON 导入日志
        
        Args:
            input_path: JSON 文件路径
            merge: 是否合并重复条目
            
        Returns:
            导入条目数
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        count = 0
        for entry_data in data.get('entries', []):
            entry = JournalEntry.from_dict(entry_data)
            
            # 检查是否已存在
            existing = await self.core.get(entry.id)
            if existing and not merge:
                continue
            
            await self.core._save_entry(entry)
            count += 1
        
        logger.info(f"Imported {count} entries from {input_path}")
        return count
    
    async def cleanup_old_entries(self, days: int = 365, dry_run: bool = False) -> int:
        """
        清理旧条目（归档而非删除）
        
        Args:
            days: 保留天数
            dry_run: 仅预览不执行
        """
        cutoff = datetime.now() - timedelta(days=days)
        
        entries = await self.core.query(end_time=cutoff, limit=10000)
        
        if dry_run:
            return len(entries)
        
        # 实际归档逻辑
        archived = 0
        for entry in entries:
            # 这里可以实现归档逻辑
            archived += 1
        
        return archived
