"""Retrieval sub-package.

Public API:
    SentenceTransformerEmbedder  – Embedder implementation
    QdrantDenseStore             – Dense vector store
    HybridRetriever              – BM25 + Qdrant dense, fused with RRF
    load_chunks / save_chunks    – Corpus I/O helpers
"""
from .embedder import SentenceTransformerEmbedder
from .qdrant_store import QdrantDenseStore
from .hybrid import HybridRetriever, load_chunks, save_chunks

__all__ = [
    "SentenceTransformerEmbedder",
    "QdrantDenseStore",
    "HybridRetriever",
    "load_chunks",
    "save_chunks",
]
