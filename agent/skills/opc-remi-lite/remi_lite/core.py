"""Core module - Swiss Army Knife style."""
import re
from pathlib import Path
from typing import Optional

from remi_lite.backup import Backup
from remi_lite.digest import DigestGenerator
from remi_lite.recall import Recall
from remi_lite.session import SessionSummarizer
from remi_lite.visualize import Visualizer


class RemiLite:
    """Remi Lite - Minimalist memory companion."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.summarizer = SessionSummarizer(customer_id)
        self.recall = Recall(customer_id)
        self.backup = Backup(customer_id)
        self.digest = DigestGenerator(customer_id)
        self.visualizer = Visualizer(customer_id)

    def hear(self, text: str, context: Optional[dict] = None) -> Optional[str]:
        """Process user input."""
        text_lower = text.lower().strip()

        # Handle "remi, xxx" format
        if text_lower.startswith("remi,"):
            remainder = text[5:].strip()
            if "啥情况" in remainder.lower():
                return self._cmd_status()
            results = self.recall.search(remainder)
            return self.recall.format_response(results, remainder)

        intent = self._detect_intent(text)

        if intent == "command":
            return self._handle_command(text)
        if intent == "query":
            results = self.recall.search(text)
            return self.recall.format_response(results, text)
        if intent == "record":
            summary = self.summarizer.summarize_turn(text, "", context)
            return "👍 记住了" if summary else None

        return None  # chat

    def _detect_intent(self, text: str) -> str:
        """Detect user intent."""
        text_lower = text.lower().strip()

        if text_lower.startswith("/remi"):
            return "command"

        # Query patterns
        query_patterns = [
            r"(怎么|如何|什么|多少|几|吗|呢|？|\?)",
            r"^(what|how|when|where|why|who)",
        ]
        if any(re.search(p, text_lower) for p in query_patterns):
            return "query"

        # Record patterns
        record_patterns = [
            r"(今天|刚才|早上|下午|晚上)",
            r"(完成|解决|做了|遇到|优化)",
            r"(开心|焦虑|困惑|累)",
            r"(决定|选择|放弃)",
        ]
        if any(re.search(p, text_lower) for p in record_patterns):
            return "record"

        return "chat"

    def _handle_command(self, text: str) -> str:
        """Handle /remi commands."""
        parts = text.split()
        cmd = parts[1] if len(parts) > 1 else "status"

        if cmd == "backup":
            return self._cmd_backup()
        if cmd == "status":
            return self._cmd_status()
        if cmd == "imports":
            return self._cmd_imports()
        if cmd == "import" and len(parts) > 2:
            return self._cmd_import(parts[2])
        if cmd in ("digest", "weekly"):
            return self._cmd_digest()
        if cmd == "graph":
            return self._cmd_graph()

        return f"未知命令: {cmd}。可用: backup, status, imports, import, digest, graph"

    def _cmd_backup(self) -> str:
        result = self.backup.create()
        if result["success"]:
            return f"📦 备份已生成: {result['filename']} ({result['size_kb']} KB)"
        return f"备份失败: {result['error']}"

    def _cmd_status(self) -> str:
        base = Path(f"~/.openclaw/customers/{self.customer_id}/.remi").expanduser()
        sessions = len(list((base / "sessions").glob("*.md"))) if (base / "sessions").exists() else 0
        digests = len(list((base / "digests").glob("*.md"))) if (base / "digests").exists() else 0
        backups = len(list(self.backup.exports_dir.glob("remi-backup-*.zip")))

        return (
            f"📊 Remi 状态\n\n"
            f"会话记录: {sessions} 天\n"
            f"周报汇总: {digests} 份\n"
            f"备份文件: {backups} 个\n\n"
            f"backup  - 创建备份\n"
            f"digest  - 生成周报\n"
            f"graph   - 活动图"
        )

    def _cmd_imports(self) -> str:
        backups = self.backup.list_importable()
        if not backups:
            return "暂无备份"
        lines = [f"备份 ({len(backups)}):"]
        for b in backups[:5]:
            lines.append(f"  {b['filename']}")
        return "\n".join(lines)

    def _cmd_import(self, filename: str) -> str:
        result = self.backup.restore(filename)
        if result["success"]:
            return f"✅ 已恢复: {result['restored_from']}"
        return f"恢复失败: {result['error']}"

    def _cmd_digest(self) -> str:
        digest_file = self.digest.generate_weekly_digest()
        if digest_file:
            lines = digest_file.read_text(encoding="utf-8").split("\n")[:20]
            return f"📊 周报: {digest_file.name}\n\n" + "\n".join(lines) + "\n..."
        return "本周暂无数据"

    def _cmd_graph(self) -> str:
        return f"📊 活动热力图\n\n{self.visualizer.generate_activity_heatmap(30)}"
