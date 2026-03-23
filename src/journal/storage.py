"""
Journal Storage Module - SQLite storage backend.
Implements persistence layer for journal entries.
"""
import json
import shutil
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Generator, Optional


class SQLiteStorage:
    """SQLite storage backend for journal data."""
    
    def __init__(self, db_path: Optional[Path] = None, connection: Optional[sqlite3.Connection] = None):
        """Initialize storage with database path or connection."""
        if connection:
            self.connection = connection
            self.db_path = None
        else:
            self.db_path = Path(db_path) if db_path else Path("journal.db")
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
    
    def create_tables(self) -> None:
        """Create database tables."""
        cursor = self.connection.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                tags TEXT,
                metadata TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entry_tags (
                entry_id TEXT,
                tag_id INTEGER,
                FOREIGN KEY (entry_id) REFERENCES journal_entries(id),
                FOREIGN KEY (tag_id) REFERENCES tags(id),
                PRIMARY KEY (entry_id, tag_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY
            )
        """)
        
        # Initialize schema version
        cursor.execute("INSERT OR IGNORE INTO schema_version (version) VALUES (1)")
        
        self.connection.commit()
    
    def get_schema_version(self) -> int:
        """Get current schema version."""
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT version FROM schema_version")
            row = cursor.fetchone()
            return row["version"] if row else 1
        except sqlite3.OperationalError:
            return 1
    
    def migrate_to_version(self, target_version: int) -> bool:
        """Migrate database to target version."""
        current_version = self.get_schema_version()
        
        if current_version >= target_version:
            return True
        
        cursor = self.connection.cursor()
        
        # Migration from version 1 to 2
        if current_version == 1 and target_version >= 2:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entry_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id TEXT,
                    action TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (entry_id) REFERENCES journal_entries(id)
                )
            """)
            cursor.execute("UPDATE schema_version SET version = 2")
        
        self.connection.commit()
        return True
    
    def rollback_migration(self, version: int) -> bool:
        """Rollback migration to previous version."""
        cursor = self.connection.cursor()
        
        if version == 2:
            cursor.execute("DROP TABLE IF EXISTS entry_history")
            cursor.execute("UPDATE schema_version SET version = 1")
        
        self.connection.commit()
        return True
    
    def check_migration_needed(self, target_version: int) -> bool:
        """Check if migration is needed."""
        return self.get_schema_version() < target_version
    
    def insert_entry(self, entry) -> bool:
        """Insert a journal entry."""
        from src.journal.core import JournalEntry
        
        cursor = self.connection.cursor()
        cursor.execute("""
            INSERT INTO journal_entries (id, content, tags, metadata, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.content,
            json.dumps(entry.tags),
            json.dumps(entry.metadata),
            entry.created_at.isoformat(),
            entry.updated_at.isoformat(),
        ))
        self.connection.commit()
        return True
    
    def get_entry(self, entry_id: str):
        """Get entry by ID."""
        from src.journal.core import JournalEntry
        
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM journal_entries WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return JournalEntry(
            id=row["id"],
            content=row["content"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    def update_entry(self, entry) -> bool:
        """Update an existing entry."""
        cursor = self.connection.cursor()
        entry.updated_at = datetime.now()
        
        cursor.execute("""
            UPDATE journal_entries
            SET content = ?, tags = ?, metadata = ?, updated_at = ?
            WHERE id = ?
        """, (
            entry.content,
            json.dumps(entry.tags),
            json.dumps(entry.metadata),
            entry.updated_at.isoformat(),
            entry.id,
        ))
        
        self.connection.commit()
        return cursor.rowcount > 0
    
    def delete_entry(self, entry_id: str) -> bool:
        """Delete an entry."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def list_entries(self, limit: int = 100, offset: int = 0):
        """List entries with pagination."""
        from src.journal.core import JournalEntry
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM journal_entries
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows = cursor.fetchall()
        entries = []
        
        for row in rows:
            entries.append(JournalEntry(
                id=row["id"],
                content=row["content"],
                tags=json.loads(row["tags"]) if row["tags"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            ))
        
        return entries
    
    def search_by_content(self, query: str):
        """Search entries by content."""
        from src.journal.core import JournalEntry
        
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT * FROM journal_entries
            WHERE content LIKE ?
            ORDER BY created_at DESC
        """, (f"%{query}%",))
        
        rows = cursor.fetchall()
        entries = []
        
        for row in rows:
            entries.append(JournalEntry(
                id=row["id"],
                content=row["content"],
                tags=json.loads(row["tags"]) if row["tags"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            ))
        
        return entries
    
    def list_by_tag(self, tag: str):
        """List entries by tag."""
        entries = self.list_entries(limit=10000)
        return [e for e in entries if tag in e.tags]
    
    def create_backup(self, backup_path: Path) -> bool:
        """Create database backup."""
        if self.db_path:
            shutil.copy2(self.db_path, backup_path)
            return True
        return False
    
    def restore_from_backup(self, backup_path: Path) -> bool:
        """Restore database from backup."""
        if self.db_path:
            self.connection.close()
            shutil.copy2(backup_path, self.db_path)
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            return True
        return False
    
    def export_to_json(self, export_path: Path) -> bool:
        """Export all entries to JSON."""
        entries = self.list_entries(limit=10000)
        data = [entry.to_dict() for entry in entries]
        
        with open(export_path, "w") as f:
            json.dump(data, f, indent=2)
        
        return True
    
    def import_from_json(self, import_path: Path) -> bool:
        """Import entries from JSON with validation."""
        from src.journal.core import JournalEntry
        
        import_path = Path(import_path)
        if not import_path.exists():
            raise FileNotFoundError(f"Import file not found: {import_path}")
        
        if not import_path.suffix.lower() == '.json':
            raise ValueError(f"Expected .json file, got: {import_path.suffix}")
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    raise ValueError("Import file is empty")
                data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}") from e
        
        if not isinstance(data, list):
            raise ValueError(f"Expected JSON array, got: {type(data).__name__}")
        
        # Validate entries before import
        validated_entries: list[JournalEntry] = []
        errors: list[tuple[int, str]] = []
        
        for idx, entry_data in enumerate(data):
            try:
                if not isinstance(entry_data, dict):
                    errors.append((idx, f"Expected dict, got {type(entry_data).__name__}"))
                    continue
                
                # Required fields check
                if 'content' not in entry_data:
                    errors.append((idx, "Missing required field: 'content'"))
                    continue
                
                if not isinstance(entry_data['content'], str) or not entry_data['content'].strip():
                    errors.append((idx, "Field 'content' must be a non-empty string"))
                    continue
                
                entry = JournalEntry.from_dict(entry_data)
                validated_entries.append(entry)
            except (ValueError, TypeError) as e:
                errors.append((idx, str(e)))
        
        # Import validated entries
        imported_count = 0
        for entry in validated_entries:
            try:
                self.insert_entry(entry)
                imported_count += 1
            except Exception as e:
                errors.append((validated_entries.index(entry), f"Database insert failed: {e}"))
        
        # Report results
        if errors:
            error_summary = "\n".join([f"  Entry {i}: {msg}" for i, msg in errors[:5]])
            if len(errors) > 5:
                error_summary += f"\n  ... and {len(errors) - 5} more errors"
            raise ValueError(f"Import completed with {len(errors)} errors:\n{error_summary}")
        
        return True
    
    def check_integrity(self) -> bool:
        """Check database integrity."""
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        return result[0] == "ok"
    
    def rebuild_indexes(self) -> bool:
        """Rebuild database indexes."""
        cursor = self.connection.cursor()
        cursor.execute("REINDEX")
        self.connection.commit()
        return True
    
    def vacuum(self) -> bool:
        """Vacuum the database."""
        cursor = self.connection.cursor()
        cursor.execute("VACUUM")
        return True
    
    def optimize(self) -> bool:
        """Optimize the database."""
        cursor = self.connection.cursor()
        cursor.execute("PRAGMA optimize")
        self.connection.commit()
        return True
    
    @contextmanager
    def transaction(self) -> Generator["SQLiteStorage", None, None]:
        """Context manager for database transactions."""
        try:
            yield self
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
