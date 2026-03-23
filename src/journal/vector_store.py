# OPC200 - 向量存储模块
# 提供语义搜索和相似度检索功能

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 尝试导入可选依赖
try:
    import qdrant_client
    from qdrant_client.models import Distance, VectorParams, PointStruct
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算余弦相似度"""
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


@dataclass
class VectorEntry:
    """向量条目"""
    id: str
    vector: List[float]
    payload: Dict[str, Any]
    score: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'vector': self.vector,
            'payload': self.payload,
            'score': self.score
        }


class EmbeddingProvider:
    """
    嵌入向量提供者基类
    """
    
    async def embed(self, text: str) -> List[float]:
        """将文本转换为向量"""
        raise NotImplementedError
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入"""
        tasks = [self.embed(text) for text in texts]
        return await asyncio.gather(*tasks)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI 嵌入 API 提供者
    """
    
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        if not OPENAI_AVAILABLE:
            raise ImportError("openai package required")
        
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
    
    async def embed(self, text: str) -> List[float]:
        """使用 OpenAI API 获取嵌入向量"""
        loop = asyncio.get_event_loop()
        
        def _embed():
            response = self.client.embeddings.create(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        
        return await loop.run_in_executor(None, _embed)


class SimpleEmbeddingProvider(EmbeddingProvider):
    """
    简单嵌入提供者（基于词频，用于离线模式）
    
    这是一个简化实现，用于没有 API 密钥的场景。
    生产环境建议使用 OpenAI 或其他专业嵌入服务。
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        # 简化的词汇表
        self.vocab = {}
    
    async def embed(self, text: str) -> List[float]:
        """基于词频的简单嵌入"""
        words = text.lower().split()
        vector = np.zeros(self.dimension)
        
        for word in words:
            # 使用 hash 将单词映射到维度
            idx = hash(word) % self.dimension
            vector[idx] += 1
        
        # 归一化
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        
        return vector.tolist()


class VectorStore:
    """
    向量存储基类
    """
    
    async def upsert(self, entries: List[VectorEntry]):
        """插入或更新向量"""
        raise NotImplementedError
    
    async def search(self, 
                    query_vector: List[float], 
                    limit: int = 10,
                    filters: Optional[Dict[str, Any]] = None) -> List[VectorEntry]:
        """向量相似度搜索"""
        raise NotImplementedError
    
    async def delete(self, entry_ids: List[str]):
        """删除向量"""
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """
    内存向量存储
    
    适用于小规模数据，无需外部依赖
    """
    
    def __init__(self, dimension: int = 384):
        self.dimension = dimension
        self.vectors: Dict[str, VectorEntry] = {}
    
    async def upsert(self, entries: List[VectorEntry]):
        """插入或更新"""
        for entry in entries:
            self.vectors[entry.id] = entry
        logger.info(f"Upserted {len(entries)} vectors")
    
    async def search(self, 
                    query_vector: List[float], 
                    limit: int = 10,
                    filters: Optional[Dict[str, Any]] = None) -> List[VectorEntry]:
        """
        暴力搜索（计算所有向量的相似度）
        """
        results = []
        
        for entry in self.vectors.values():
            # 应用过滤
            if filters:
                match = True
                for key, value in filters.items():
                    if entry.payload.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # 计算相似度
            score = cosine_similarity(query_vector, entry.vector)
            
            # 创建带分数的副本
            result = VectorEntry(
                id=entry.id,
                vector=entry.vector,
                payload=entry.payload,
                score=score
            )
            results.append(result)
        
        # 排序并返回前 N 个
        results.sort(key=lambda x: x.score or 0, reverse=True)
        return results[:limit]
    
    async def delete(self, entry_ids: List[str]):
        """删除向量"""
        for entry_id in entry_ids:
            self.vectors.pop(entry_id, None)
    
    async def text_search(self,
                         query_text: str,
                         embedding_provider: EmbeddingProvider,
                         limit: int = 10) -> List[VectorEntry]:
        """
        文本搜索（自动嵌入查询文本）
        """
        query_vector = await embedding_provider.embed(query_text)
        return await self.search(query_vector, limit)
    
    def save_to_disk(self, path: str):
        """保存到磁盘"""
        data = {
            'dimension': self.dimension,
            'vectors': {
                k: v.to_dict() 
                for k, v in self.vectors.items()
            }
        }
        with open(path, 'w') as f:
            json.dump(data, f)
    
    def load_from_disk(self, path: str):
        """从磁盘加载"""
        with open(path, 'r') as f:
            data = json.load(f)
        
        self.dimension = data['dimension']
        self.vectors = {
            k: VectorEntry(**v) 
            for k, v in data['vectors'].items()
        }


class QdrantVectorStore(VectorStore):
    """
    Qdrant 向量数据库存储
    
    适用于生产环境的大规模数据
    """
    
    def __init__(self, 
                 host: str = "localhost",
                 port: int = 6333,
                 collection_name: str = "journal",
                 dimension: int = 384):
        if not QDRANT_AVAILABLE:
            raise ImportError("qdrant-client required")
        
        self.client = qdrant_client.QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.dimension = dimension
        
        # 确保集合存在
        self._ensure_collection()
    
    def _ensure_collection(self):
        """确保集合存在"""
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE
                )
            )
    
    async def upsert(self, entries: List[VectorEntry]):
        """插入或更新"""
        points = [
            PointStruct(
                id=entry.id,
                vector=entry.vector,
                payload=entry.payload
            )
            for entry in entries
        ]
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
        )
    
    async def search(self, 
                    query_vector: List[float], 
                    limit: int = 10,
                    filters: Optional[Dict[str, Any]] = None) -> List[VectorEntry]:
        """搜索相似向量"""
        loop = asyncio.get_event_loop()
        
        def _search():
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                query_filter=self._build_filter(filters) if filters else None
            )
            
            return [
                VectorEntry(
                    id=r.id,
                    vector=r.vector if hasattr(r, 'vector') else [],
                    payload=r.payload,
                    score=r.score
                )
                for r in results
            ]
        
        return await loop.run_in_executor(None, _search)
    
    def _build_filter(self, filters: Dict[str, Any]):
        """构建 Qdrant 过滤条件"""
        from qdrant_client.models import FieldCondition, MatchValue, Filter
        
        conditions = []
        for key, value in filters.items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(value=value)
                )
            )
        
        return Filter(must=conditions)
    
    async def delete(self, entry_ids: List[str]):
        """删除向量"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.delete(
                collection_name=self.collection_name,
                points_selector=entry_ids
            )
        )


class JournalVectorSearch:
    """
    Journal 向量搜索集成
    
    结合 SQLite 日志和向量存储提供语义搜索
    """
    
    def __init__(self, 
                 vector_store: VectorStore,
                 embedding_provider: EmbeddingProvider):
        self.vector_store = vector_store
        self.embedding_provider = embedding_provider
    
    async def index_journal_entry(self, 
                                  entry_id: str, 
                                  content: str,
                                  metadata: Dict[str, Any]):
        """
        为日志条目创建向量索引
        """
        # 生成嵌入
        vector = await self.embedding_provider.embed(content)
        
        # 存储到向量数据库
        entry = VectorEntry(
            id=entry_id,
            vector=vector,
            payload={
                'content': content,
                'entry_id': entry_id,
                'indexed_at': datetime.now().isoformat(),
                **metadata
            }
        )
        
        await self.vector_store.upsert([entry])
    
    async def semantic_search(self, 
                             query: str, 
                             limit: int = 10,
                             filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        语义搜索日志
        
        Returns:
            搜索结果列表，包含相关度和原始内容
        """
        # 嵌入查询
        query_vector = await self.embedding_provider.embed(query)
        
        # 搜索
        results = await self.vector_store.search(
            query_vector=query_vector,
            limit=limit,
            filters=filters
        )
        
        # 格式化结果
        return [
            {
                'entry_id': r.id,
                'score': r.score,
                'content': r.payload.get('content', ''),
                'metadata': {k: v for k, v in r.payload.items() 
                           if k not in ['content', 'entry_id', 'indexed_at']}
            }
            for r in results
        ]
    
    async def find_similar(self, 
                          entry_id: str, 
                          limit: int = 5) -> List[Dict[str, Any]]:
        """
        查找相似条目
        """
        # 获取原始向量
        # 注意：这里假设内存存储，其他存储需要实现 get 方法
        if isinstance(self.vector_store, InMemoryVectorStore):
            if entry_id not in self.vector_store.vectors:
                return []
            
            query_vector = self.vector_store.vectors[entry_id].vector
            
            results = await self.vector_store.search(
                query_vector=query_vector,
                limit=limit + 1  # 包含自身
            )
            
            # 排除自身
            return [
                {
                    'entry_id': r.id,
                    'score': r.score,
                    'content': r.payload.get('content', '')
                }
                for r in results 
                if r.id != entry_id
            ][:limit]
        
        return []


# 工厂函数
def create_vector_store(store_type: str = "memory", **kwargs) -> VectorStore:
    """
    创建向量存储实例
    
    Args:
        store_type: 存储类型 (memory/qdrant)
        **kwargs: 传递给具体实现的参数
    """
    if store_type == "memory":
        return InMemoryVectorStore(**kwargs)
    elif store_type == "qdrant":
        return QdrantVectorStore(**kwargs)
    else:
        raise ValueError(f"Unknown store type: {store_type}")


def create_embedding_provider(provider_type: str = "simple", **kwargs) -> EmbeddingProvider:
    """
    创建嵌入提供者实例
    
    Args:
        provider_type: 提供者类型 (simple/openai)
        **kwargs: 传递给具体实现的参数
    """
    if provider_type == "simple":
        return SimpleEmbeddingProvider(**kwargs)
    elif provider_type == "openai":
        return OpenAIEmbeddingProvider(**kwargs)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
