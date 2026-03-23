"""
Journal Core Module - JournalEntry class and JournalManager.
Implements the core journal functionality with CRUD operations.
"""
import json
import sqlite3
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union

from src.utils.validation import InputValidator, ValidationError

# Type aliases for better code clarity
EntryId = str
Tag = str
Metadata = dict[str, Any]
EntryDict = dict[str, Any]


@dataclass
class JournalEntry:
    """Represents a single journal entry."""
    
    content: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate entry after initialization."""
        if not isinstance(self.content, str) or not self.content.strip():
            raise ValueError("Content cannot be empty")
        
        # Validate other fields
        try:
            self.tags = InputValidator.validate_tags(self.tags)
            self.metadata = InputValidator.validate_metadata(self.metadata)
        except ValidationError as e:
            raise ValueError(f"Validation failed: {e}") from e
    
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
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        
        required_fields = ["content"]
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")
        
        try:
            created_at = datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid created_at format: {e}") from e
        
        try:
            updated_at = datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now()
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid updated_at format: {e}") from e
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data["content"],
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=created_at,
            updated_at=updated_at,
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
    
    def __init__(self, connection: sqlite3.Connection) -> None:
        """Initialize with database connection."""
        self.connection: sqlite3.Connection = connection
        # Ensure row factory is set for dictionary-style access
        if hasattr(self.connection, 'row_factory') and self.connection.row_factory is None:
            self.connection.row_factory = sqlite3.Row
    
    def create_table(self) -> None:
        """Create journal entries table."""
        cursor: sqlite3.Cursor = self.connection.cursor()
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
        cursor: sqlite3.Cursor = self.connection.cursor()
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
        # Validate input
        entry_id = InputValidator.validate_entry_id(entry_id)
        
        cursor: sqlite3.Cursor = self.connection.cursor()
        
        # Use parameterized query to prevent SQL injection
        cursor.execute(
            "SELECT * FROM journal_entries WHERE id = ?",
            (entry_id,)
        )
        row: Optional[sqlite3.Row] = cursor.fetchone()
        
        if row is None:
            return None
        
        return JournalEntry(
            id=str(row["id"]),
            content=str(row["content"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
    
    def update_entry(self, entry: JournalEntry) -> bool:
        """Update an existing journal entry."""
        cursor: sqlite3.Cursor = self.connection.cursor()
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
        cursor: sqlite3.Cursor = self.connection.cursor()
        cursor.execute("DELETE FROM journal_entries WHERE id = ?", (entry_id,))
        self.connection.commit()
        return cursor.rowcount > 0
    
    def list_entries(self, limit: int = 100, offset: int = 0) -> list[JournalEntry]:
        """List all journal entries with pagination."""
        # Validate pagination parameters
        limit, offset = InputValidator.validate_limit_offset(limit, offset)
        
        cursor: sqlite3.Cursor = self.connection.cursor()
        
        # Use parameterized query for pagination
        cursor.execute("""
            SELECT * FROM journal_entries
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset))
        
        rows: list[sqlite3.Row] = cursor.fetchall()
        entries: list[JournalEntry] = []
        
        for row in rows:
            entries.append(JournalEntry(
                id=str(row["id"]),
                content=str(row["content"]),
                tags=json.loads(row["tags"]) if row["tags"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            ))
        
        return entries
    
    def list_entries_by_tag(self, tag: str) -> list[JournalEntry]:
        """List entries filtered by tag."""
        # Validate tag
        tag = InputValidator.validate_tag(tag)
        
        entries = self.list_entries(limit=10000)
        return [e for e in entries if tag in e.tags]
    
    def search_entries(self, query: str) -> list[JournalEntry]:
        """Search entries by content."""
        # Validate search query
        query = InputValidator.validate_search_query(query)
        
        cursor: sqlite3.Cursor = self.connection.cursor()
        
        # Use parameterized query to prevent SQL injection
        # The LIKE pattern is safely parameterized
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT * FROM journal_entries
            WHERE content LIKE ?
            ORDER BY created_at DESC
        """, (search_pattern,))
        
        rows: list[sqlite3.Row] = cursor.fetchall()
        entries: list[JournalEntry] = []
        
        for row in rows:
            entries.append(JournalEntry(
                id=str(row["id"]),
                content=str(row["content"]),
                tags=json.loads(row["tags"]) if row["tags"] else [],
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"]),
            ))
        
        return entries
    
    def get_all_tags(self) -> list[str]:
        """Get all unique tags across entries."""
        entries = self.list_entries(limit=10000)
        tags: set[str] = set()
        for entry in entries:
            tags.update(entry.tags)
        return sorted(list(tags))
    
    def rename_tag(self, old_name: str, new_name: str) -> bool:
        """Rename a tag across all entries."""
        # Validate tags
        old_name = InputValidator.validate_tag(old_name)
        new_name = InputValidator.validate_tag(new_name)
        
        entries = self.list_entries_by_tag(old_name)
        
        for entry in entries:
            entry.remove_tag(old_name)
            entry.add_tag(new_name)
            self.update_entry(entry)
        
        return len(entries) > 0
    
    def delete_tag(self, tag: str) -> bool:
        """Delete a tag from all entries."""
        # Validate tag
        tag = InputValidator.validate_tag(tag)
        
        entries = self.list_entries_by_tag(tag)
        
        for entry in entries:
            entry.remove_tag(tag)
            self.update_entry(entry)
        
        return len(entries) > 0
