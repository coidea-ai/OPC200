# OPC200 Python 模块初始化文件

"""
OPC200 - One Person Company 超级智能体支持平台

Python 核心模块包
"""

__version__ = "2.2.0"
__author__ = "coidea.ai"

from .journal.core import JournalCore, JournalManager, JournalEntry
from .journal.storage import StorageManager, EncryptedStorage, BackupManager, DataVault
from .journal.vector_store import (
    VectorStore, InMemoryVectorStore, QdrantVectorStore,
    EmbeddingProvider, OpenAIEmbeddingProvider, SimpleEmbeddingProvider,
    JournalVectorSearch
)
from .security.vault import SecureVault, VaultKeyManager, VaultHealthChecker
from .security.encryption import (
    EncryptionManager, AESGCMEncryption, AsymmetricEncryption,
    HashUtility, SecureRandom
)
from .patterns.analyzer import PatternAnalyzer, PatternProfile
from .tasks.scheduler import (
    TaskScheduler, Task, TaskStatus, TaskPriority,
    CommonTaskHandlers, create_default_scheduler
)
from .insights.generator import InsightEngine, Insight, RecommendationEngine

__all__ = [
    # Journal
    'JournalCore',
    'JournalManager',
    'JournalEntry',
    'StorageManager',
    'EncryptedStorage',
    'BackupManager',
    'DataVault',
    'VectorStore',
    'InMemoryVectorStore',
    'QdrantVectorStore',
    'EmbeddingProvider',
    'OpenAIEmbeddingProvider',
    'SimpleEmbeddingProvider',
    'JournalVectorSearch',
    # Security
    'SecureVault',
    'VaultKeyManager',
    'VaultHealthChecker',
    'EncryptionManager',
    'AESGCMEncryption',
    'AsymmetricEncryption',
    'HashUtility',
    'SecureRandom',
    # Patterns
    'PatternAnalyzer',
    'PatternProfile',
    # Tasks
    'TaskScheduler',
    'Task',
    'TaskStatus',
    'TaskPriority',
    'CommonTaskHandlers',
    'create_default_scheduler',
    # Insights
    'InsightEngine',
    'Insight',
    'RecommendationEngine',
]
