from __future__ import annotations
import json
import re
import math
from collections import Counter
from pathlib import Path
from ..config import settings
from ..schemas import SourceChunk, RetrievedChunk
from .embedder import SentenceTransformerEmbedder
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .qdrant_store import QdrantDenseStore

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[^\W\d_]", re.UNICODE)
def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text)]

class BM25Index:
    """Small in-process Okapi BM25 index. Adequate for the course-sized corpus; no separate service."""
    def __init__(self, documents: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1, self.b = k1, b
        self.term_counts = [Counter(doc) for doc in documents]
        self.lengths = [len(doc) for doc in documents]
        self.n = len(documents)
        self.avgdl = (sum(self.lengths) / self.n) if self.n else 0.0
        df = Counter(term for doc in documents for term in set(doc))
        self.idf = {term: math.log(1.0 + (self.n - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def get_scores(self, query_tokens: list[str]) -> list[float]:
        scores = [0.0] * self.n
        if not self.n or self.avgdl <= 0: return scores
        for i, counts in enumerate(self.term_counts):
            doc_len = self.lengths[i]
            norm = self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
            for term in query_tokens:
                tf = counts.get(term, 0)
                if tf:
                    scores[i] += self.idf.get(term, 0.0) * (tf * (self.k1 + 1)) / (tf + norm)
        return scores

class HybridRetriever:
    """Qdrant dense retrieval + BM25 lexical retrieval, fused with Reciprocal Rank Fusion."""
    def __init__(self, chunks: list[SourceChunk], embedder: SentenceTransformerEmbedder,
                 store: QdrantDenseStore):
        self.chunks = chunks
        self.embedder = embedder
        self.store = store
        self._bm25 = BM25Index([tokenize(c.text) for c in chunks]) if chunks else None

    def retrieve(self, question: str, *, subject: str | None = None, top_k: int = 5) -> list[RetrievedChunk]:
        dense = self.store.search(self.embedder.embed_query(question), top_k=settings.dense_top_k, subject=subject)
        lexical: list[RetrievedChunk] = []
        if self._bm25 is not None:
            scores = self._bm25.get_scores(tokenize(question))
            candidates = sorted(range(len(scores)), key=lambda i: float(scores[i]), reverse=True)
            rank = 0
            for i in candidates:
                chunk = self.chunks[i]
                if subject and subject != "UNKNOWN" and chunk.subject != subject: continue
                if scores[i] <= 0: break
                rank += 1
                lexical.append(RetrievedChunk(chunk=chunk, score=float(scores[i]), channel="bm25", rank=rank))
                if rank >= settings.bm25_top_k: break
        # RRF avoids comparing dense cosine scores directly with BM25 scores.
        fused: dict[str, dict] = {}
        for hit in dense + lexical:
            entry = fused.setdefault(hit.chunk.chunk_id, {"chunk": hit.chunk, "rrf": 0.0, "channels": set()})
            entry["rrf"] += 1.0 / (settings.rrf_k + (hit.rank or 1))
            entry["channels"].add(hit.channel)
        ordered = sorted(fused.values(), key=lambda x: x["rrf"], reverse=True)[:top_k]
        return [RetrievedChunk(chunk=x["chunk"], score=x["rrf"], channel="hybrid", rank=i)
                for i, x in enumerate(ordered, start=1)]

def load_chunks(path: Path | None = None) -> list[SourceChunk]:
    path = path or settings.chunks_jsonl
    if not path.exists(): return []
    chunks: list[SourceChunk] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip(): chunks.append(SourceChunk.model_validate_json(line))
    return chunks

def save_chunks(chunks: list[SourceChunk], path: Path | None = None) -> None:
    path = path or settings.chunks_jsonl
    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replacement: a crash should not leave a half-written corpus.
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        for chunk in chunks: handle.write(chunk.model_dump_json() + "\n")
    temp.replace(path)
