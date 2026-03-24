"""
Input Validation Module - Input validation and sanitization utilities.
"""
import re
from datetime import datetime
from typing import Any, Optional


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """Input validation utilities."""
    
    # Maximum lengths for various fields
    MAX_ENTRY_ID_LENGTH = 256
    MAX_CONTENT_LENGTH = 1_000_000  # 1MB
    MAX_TAG_LENGTH = 100
    MAX_TAGS_COUNT = 1000
    MAX_METADATA_SIZE = 100_000  # 100KB
    
    # ID pattern: alphanumeric, hyphens, underscores
    ID_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    
    # Tag pattern: alphanumeric, spaces, hyphens
    TAG_PATTERN = re.compile(r'^[a-zA-Z0-9\s_-]+$')
    
    @classmethod
    def validate_entry_id(cls, entry_id: str) -> str:
        """Validate entry ID format."""
        if not isinstance(entry_id, str):
            raise ValidationError(f"Entry ID must be a string, got {type(entry_id).__name__}")
        
        entry_id = entry_id.strip()
        
        if not entry_id:
            raise ValidationError("Entry ID cannot be empty")
        
        if len(entry_id) > cls.MAX_ENTRY_ID_LENGTH:
            raise ValidationError(f"Entry ID too long: {len(entry_id)} > {cls.MAX_ENTRY_ID_LENGTH}")
        
        if not cls.ID_PATTERN.match(entry_id):
            raise ValidationError(f"Invalid entry ID format: {entry_id}")
        
        return entry_id
    
    @classmethod
    def validate_content(cls, content: str) -> str:
        """Validate entry content."""
        if not isinstance(content, str):
            raise ValidationError(f"Content must be a string, got {type(content).__name__}")
        
        content = content.strip()
        
        if not content:
            raise ValidationError("Content cannot be empty")
        
        if len(content) > cls.MAX_CONTENT_LENGTH:
            raise ValidationError(f"Content too long: {len(content)} > {cls.MAX_CONTENT_LENGTH}")
        
        # Check for potential SQL injection patterns
        sql_patterns = [
            r'--',
            r'/\*',
            r'\*/',
            r';\s*\b(drop|delete|insert|update|select)\b',
        ]
        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                raise ValidationError(f"Content contains potentially unsafe pattern: {pattern}")
        
        return content
    
    @classmethod
    def validate_tag(cls, tag: str) -> str:
        """Validate a single tag."""
        if not isinstance(tag, str):
            raise ValidationError(f"Tag must be a string, got {type(tag).__name__}")
        
        tag = tag.strip()
        
        if not tag:
            raise ValidationError("Tag cannot be empty")
        
        if len(tag) > cls.MAX_TAG_LENGTH:
            raise ValidationError(f"Tag too long: {len(tag)} > {cls.MAX_TAG_LENGTH}")
        
        if not cls.TAG_PATTERN.match(tag):
            raise ValidationError(f"Invalid tag format: {tag}")
        
        return tag.lower()  # Normalize to lowercase
    
    @classmethod
    def validate_tags(cls, tags: list[str]) -> list[str]:
        """Validate list of tags."""
        if not isinstance(tags, list):
            raise ValidationError(f"Tags must be a list, got {type(tags).__name__}")
        
        if len(tags) > cls.MAX_TAGS_COUNT:
            raise ValidationError(f"Too many tags: {len(tags)} > {cls.MAX_TAGS_COUNT}")
        
        validated = []
        seen = set()
        
        for tag in tags:
            validated_tag = cls.validate_tag(tag)
            if validated_tag not in seen:
                validated.append(validated_tag)
                seen.add(validated_tag)
        
        return validated
    
    @classmethod
    def validate_metadata(cls, metadata: dict) -> dict:
        """Validate entry metadata."""
        if not isinstance(metadata, dict):
            raise ValidationError(f"Metadata must be a dict, got {type(metadata).__name__}")
        
        # Check size by serializing to JSON
        import json
        try:
            json_str = json.dumps(metadata)
            if len(json_str) > cls.MAX_METADATA_SIZE:
                raise ValidationError(f"Metadata too large: {len(json_str)} > {cls.MAX_METADATA_SIZE}")
        except (TypeError, ValueError) as e:
            raise ValidationError(f"Invalid metadata: {e}") from e
        
        # Recursively validate keys and string values
        def validate_recursive(obj: Any, depth: int = 0) -> None:
            if depth > 10:
                raise ValidationError("Metadata nesting too deep")
            
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if not isinstance(k, str):
                        raise ValidationError(f"Metadata key must be string: {k}")
                    validate_recursive(v, depth + 1)
            elif isinstance(obj, list):
                for item in obj:
                    validate_recursive(item, depth + 1)
            elif isinstance(obj, str):
                # Check for unsafe patterns in string values
                if any(pattern in obj.lower() for pattern in ['<script', 'javascript:', 'onerror=']):
                    raise ValidationError("Metadata contains potentially unsafe content")
        
        validate_recursive(metadata)
        
        return metadata
    
    @classmethod
    def validate_datetime(cls, dt: Optional[datetime], field_name: str = "datetime") -> Optional[datetime]:
        """Validate datetime value."""
        if dt is None:
            return None
        
        if not isinstance(dt, datetime):
            raise ValidationError(f"{field_name} must be a datetime, got {type(dt).__name__}")
        
        # Check for reasonable date range
        min_date = datetime(1970, 1, 1)
        max_date = datetime(2100, 1, 1)
        
        if dt < min_date:
            raise ValidationError(f"{field_name} is too old: {dt}")
        
        if dt > max_date:
            raise ValidationError(f"{field_name} is too far in future: {dt}")
        
        return dt
    
    @classmethod
    def validate_limit_offset(cls, limit: int, offset: int) -> tuple[int, int]:
        """Validate pagination parameters."""
        if not isinstance(limit, int):
            raise ValidationError(f"Limit must be an integer, got {type(limit).__name__}")
        
        if not isinstance(offset, int):
            raise ValidationError(f"Offset must be an integer, got {type(offset).__name__}")
        
        if limit < 1:
            raise ValidationError(f"Limit must be positive: {limit}")
        
        if limit > 10000:
            raise ValidationError(f"Limit too large: {limit} > 10000")
        
        if offset < 0:
            raise ValidationError(f"Offset cannot be negative: {offset}")
        
        if offset > 10_000_000:
            raise ValidationError(f"Offset too large: {offset} > 10,000,000")
        
        return limit, offset
    
    @classmethod
    def validate_search_query(cls, query: str) -> str:
        """Validate search query."""
        if not isinstance(query, str):
            raise ValidationError(f"Query must be a string, got {type(query).__name__}")
        
        query = query.strip()
        
        if not query:
            raise ValidationError("Search query cannot be empty")
        
        if len(query) > 1000:
            raise ValidationError(f"Search query too long: {len(query)} > 1000")
        
        # Escape special SQLite LIKE characters if they appear at start
        # User can still use % and _ for pattern matching
        return query


def sanitize_sql_like(pattern: str) -> str:
    """Sanitize a LIKE pattern by escaping special characters.
    
    SQLite LIKE special characters:
    - % matches any sequence of characters
    - _ matches any single character
    
    We escape them with backslash to make them literal.
    """
    # Escape backslashes first
    pattern = pattern.replace('\\', '\\\\')
    # Escape % and _
    pattern = pattern.replace('%', '\\%')
    pattern = pattern.replace('_', '\\_')
    return pattern
