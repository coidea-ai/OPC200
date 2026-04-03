"""Backup module - L3: Export and restore memories."""

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class Backup:
    """Backup and restore memory data.

    Simple ZIP-based backup with automatic safety backups.
    """

    def __init__(self, customer_id: str):
        """Initialize backup for a customer.

        Args:
            customer_id: Unique customer identifier
        """
        self.customer_id = customer_id
        self.base_path = Path(f"~/.openclaw/customers/{customer_id}/.remi").expanduser()
        self.exports_dir = self.base_path / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def create(self) -> dict:
        """Create a backup of all memory data.

        Returns:
            Dict with backup info or error
        """
        # Check if there's actual data to backup
        sessions_dir = self.base_path / "sessions"
        has_data = sessions_dir.exists() and any(sessions_dir.glob("*.md"))

        if not has_data:
            return {"success": False, "error": "No data to backup"}

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"remi-backup-{timestamp}.zip"
        filepath = self.exports_dir / filename

        try:
            # Create ZIP archive
            with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
                session_count = 0

                # Add all session files
                sessions_dir = self.base_path / "sessions"
                if sessions_dir.exists():
                    for md_file in sessions_dir.glob("*.md"):
                        zf.write(md_file, md_file.relative_to(self.base_path))
                        session_count += 1

                # Add all digest files
                digests_dir = self.base_path / "digests"
                if digests_dir.exists():
                    for md_file in digests_dir.glob("*.md"):
                        zf.write(md_file, md_file.relative_to(self.base_path))

                # Add manifest
                manifest = {
                    "version": "0.1",
                    "created_at": datetime.now().isoformat(),
                    "customer_id": self.customer_id,
                    "files_backed_up": session_count,
                }
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            size_kb = filepath.stat().st_size // 1024

            return {
                "success": True,
                "filename": filename,
                "path": str(filepath),
                "size_kb": size_kb,
                "stats": {
                    "sessions": session_count,
                },
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_importable(self) -> List[dict]:
        """List all available backups for import (alias for list_backups)."""
        return self.list_backups()

    def list_backups(self) -> List[dict]:
        """List all available backups.

        Returns:
            List of backup info dicts, sorted by date (newest first)
        """
        backups = []

        for zip_file in self.exports_dir.glob("remi-backup-*.zip"):
            stat = zip_file.stat()
            backups.append(
                {
                    "filename": zip_file.name,
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "size_kb": stat.st_size // 1024,
                }
            )

        # Sort by date (newest first), then by filename (for stable ordering)
        return sorted(backups, key=lambda x: (x["created"], x["filename"]), reverse=True)

    def restore(self, filename: str) -> dict:
        """Restore from a backup.

        Creates a safety backup of current data before restoring.

        Args:
            filename: Name of backup file to restore

        Returns:
            Dict with restore result
        """
        filepath = self.exports_dir / filename

        # Validate backup file
        if not filepath.exists():
            return {"success": False, "error": f"备份文件不存在: {filename}"}

        try:
            with zipfile.ZipFile(filepath, "r") as zf:
                zf.testzip()
        except zipfile.BadZipFile:
            return {"success": False, "error": "备份文件损坏"}

        # Create safety backup of current data
        safety_filename = self._create_safety_backup()

        # Clear current data (preserve exports)
        self._clear_current_data()

        # Extract backup
        try:
            with zipfile.ZipFile(filepath, "r") as zf:
                zf.extractall(self.base_path)

            return {
                "success": True,
                "restored_from": filename,
                "safety_backup": safety_filename,
                "message": "恢复完成。如需撤销，可用 safety backup 恢复。",
            }

        except Exception as e:
            # Restore failed - try to recover from safety backup
            self._restore_from_safety(safety_filename)
            return {"success": False, "error": f"恢复失败: {str(e)}。已自动回滚。"}

    def _create_safety_backup(self) -> str:
        """Create safety backup of current data before restore."""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        filename = f"safety-before-import-{timestamp}.zip"
        filepath = self.exports_dir / filename

        with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in self.base_path.rglob("*"):
                if item.is_file() and "exports" not in str(item):
                    zf.write(item, item.relative_to(self.base_path))

        return filename

    def _clear_current_data(self) -> None:
        """Clear current data directories (preserve exports)."""
        for item in self.base_path.iterdir():
            if item.name == "exports":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    def _restore_from_safety(self, safety_filename: str) -> bool:
        """Restore from safety backup."""
        safety_path = self.exports_dir / safety_filename
        if not safety_path.exists():
            return False

        try:
            with zipfile.ZipFile(safety_path, "r") as zf:
                zf.extractall(self.base_path)
            return True
        except Exception:
            return False
