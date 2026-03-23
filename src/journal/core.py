"""
Journal Core Module - JournalEntry class and JournalManager.
Implements the core journal functionality with CRUD operations.
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class JournalEntry:
    """Represents a single journal entry."""
    
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate entry after initialization."""
        if not self.content or not self.content.strip():
            raise ValueError("Content cannot be empty")
    
    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "tags": self.tags.copy(),
            "metadata": self.metadata.copy(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JournalEntry":
        """Create entry from dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )
    
    def to_json(self) -> str:
        """Convert entry to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "JournalEntry":
        """Create entry from JSON string."""
        return cls.from_dict(json.loads(json_str))
    
    def add_tag(self, tag: str) -> None:
        """Add a tag to the entry."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.updated_at = datetime.now()
    
    def remove_tag(self, tag: str) -> None:
        """Remove a tag from the entry."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.updated_at = datetime.now()
    
    def has_tag(self, tag: str) -> bool:
        """Check if entry has a specific tag."""
        return tag in self.tags
    
    def update_content(self, new_content: str) -> None:
        """Update entry content."""
        if not new_content or not new_content.strip():
            raise ValueError("Content cannot be empty")
        self.content = new_content
        self.updated_at = datetime.now()
    
    def update_metadata(self, updates: dict[str, Any]) -> None:
        """Update entry metadata."""
        self.metadata.update(updates)
        self.updated_at = datetime.now()
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a specific metadata value."""
        self.metadata[key] = value
        self.updated_at = datetime.now()
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get a specific metadata value."""
        return self.metadata.get(key, default)
    
    def delete_metadata(self, key: str) -> None:
        """Delete a metadata key."""
        if key in self.metadata:
            del self.metadata[key]
            self.updated_at = datetime.now()
    
    def has_metadata(self, key: str) -> bool:
        """Check if metadata key exists."""
        return key in self.metadata
    
    def search_content(self, query: str) -> bool:
        """Search for text within entry content."""
        return query.lower() in self.content.lower()


class JournalManager:
    """Manages journal entries with CRUD operations."""
    
    def __init__(self, connection):
        """Initialize with database connection."""
        self.connection = connection
        # Ensure row factory is set for dictionary-style access
        if hasattr(self.connection, 'row_factory') and self.connection.row_factory is None:
            import sqlite3
            self.connection.row_factory = sqlite3.Row
    
    def create_table(self) -> None:
        """Create journal entries table."""
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
        self.connection.commit()
    
    def create_entry(self, entry: JournalEntry) -> JournalEntry:
        """Create a new journal entry."""
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
        return entry
    
    def get_entry(self, entry_id: str) -> Optional[JournalEntry]:
        """Get a journal entry by ID."""
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
    
    def update_entry(self, entry: JournalEntry) -> bool:
        """Update an existing journal entry."""
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
        """Delete a journal entry."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def list_entries(self, limit: int = 100, offset: int = 0) -> list[JournalEntry]:
        """List all journal entries with pagination."""
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
    
    def list_entries_by_tag(self, tag: str) -> list[JournalEntry]:
        """List entries filtered by tag."""
        entries = self.list_entries(limit=10000)
        return [e for e in entries if tag in e.tags]
    
    def search_entries(self, query: str) -> list[JournalEntry]:
        """Search entries by content."""
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
    
    def get_all_tags(self) -> list[str]:
        """Get all unique tags across entries."""
        entries = self.list_entries(limit=10000)
        tags = set()
        for entry in entries:
            tags.update(entry.tags)
        return sorted(list(tags))
    
    def rename_tag(self, old_name: str, new_name: str) -> bool:
        """Rename a tag across all entries."""
        entries = self.list_entries_by_tag(old_name)
        
        for entry in entries:
            entry.remove_tag(old_name)
            entry.add_tag(new_name)
            self.update_entry(entry)
        
        return len(entries) > 0
    
    def delete_tag(self, tag: str) -> bool:
        """Delete a tag from all entries."""
        entries = self.list_entries_by_tag(tag)
        
        for entry in entries:
            entry.remove_tag(tag)
            self.update_entry(entry)
        
        return len(entries) > 0
