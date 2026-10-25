from __future__ import annotations
import logging
from pathlib import Path
from typing import Sequence
from qdrant_client import QdrantClient, models
from ..config import settings
from ..schemas import SourceChunk, RetrievedChunk

logger = logging.getLogger(__name__)

class QdrantDenseStore:
    """Dense vector store in Qdrant. The app-level BM25 retriever is fused with this result set by RRF."""
    def __init__(self, vector_size: int, client: QdrantClient | None = None, collection: str | None = None):
        self.collection = collection or settings.qdrant_collection
        if client is not None:
            self.client = client
            names = {c.name for c in self.client.get_collections().collections}
        elif settings.qdrant_url:
            try:
                self.client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, timeout=2.0)
                names = {c.name for c in self.client.get_collections().collections}
            except Exception as exc:
                logger.warning(
                    "Failed to connect to Qdrant at %s (%s); falling back to embedded local mode at %s",
                    settings.qdrant_url,
                    exc,
                    settings.qdrant_local_path,
                )
                settings.qdrant_local_path.mkdir(parents=True, exist_ok=True)
                self.client = QdrantClient(path=str(settings.qdrant_local_path))
                names = {c.name for c in self.client.get_collections().collections}
        else:
            settings.qdrant_local_path.mkdir(parents=True, exist_ok=True)
            self.client = QdrantClient(path=str(settings.qdrant_local_path))
            names = {c.name for c in self.client.get_collections().collections}

        if self.collection not in names:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
            )

    def close(self) -> None:
        """Close the underlying client connection (releases locks in embedded mode)."""
        try:
            self.client.close()
        except Exception:
            pass

    def upsert(self, chunks: Sequence[SourceChunk], vectors: Sequence[list[float]], batch_size: int = 64) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        for start in range(0, len(chunks), batch_size):
            points = []
            for chunk, vector in zip(chunks[start:start + batch_size], vectors[start:start + batch_size]):
                payload = chunk.model_dump(mode="json")
                points.append(models.PointStruct(id=chunk.chunk_id, vector=vector, payload=payload))
            self.client.upsert(collection_name=self.collection, points=points, wait=True)
        return len(chunks)

    def search(self, vector: list[float], *, top_k: int = 8, subject: str | None = None) -> list[RetrievedChunk]:
        query_filter = None
        if subject and subject != "UNKNOWN":
            query_filter = models.Filter(must=[models.FieldCondition(key="subject", match=models.MatchValue(value=subject))])
        response = self.client.query_points(collection_name=self.collection, query=vector,
            query_filter=query_filter, limit=top_k, with_payload=True)
        hits: list[RetrievedChunk] = []
        for rank, point in enumerate(response.points, start=1):
            if not point.payload: continue
            chunk = SourceChunk.model_validate(point.payload)
            hits.append(RetrievedChunk(chunk=chunk, score=float(point.score), channel="dense", rank=rank))
        return hits
