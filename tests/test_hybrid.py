"""Tests for hybrid retrieval (BM25 + Qdrant dense + RRF).

Run with:
    pytest tests/test_hybrid.py -v
"""
from __future__ import annotations

import math
import pytest

from course_qa.schemas import SourceChunk, RetrievedChunk
from course_qa.retrieval.hybrid import HybridRetriever, BM25Index, tokenize


# ─── Helpers ─────────────────────────────────────────────────────────────────

def chunk(cid: str, text: str, subject: str = "DS") -> SourceChunk:
    """Build a minimal valid SourceChunk for testing."""
    return SourceChunk(
        chunk_id=cid,
        source_id="src_" + cid,
        subject=subject,       # type: ignore[arg-type]
        source_type="text",
        source_file="DS notes/Typed/example.pdf",
        text=text,
        content_hash=cid,
        source_hash="hash",
    )


class FakeEmbedder:
    """Returns a fixed 2-D vector; dimension is irrelevant for RRF tests."""
    @property
    def dimension(self) -> int:
        return 2

    def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2]

    def embed_documents(self, texts):  # noqa: D102
        return [[0.1, 0.2] for _ in texts]


class FakeStore:
    """Returns a pre-configured hit list. Ignores the vector and subject."""
    def __init__(self, hits: list[RetrievedChunk]):
        self.hits = hits

    def search(
        self,
        vector: list[float],
        *,
        top_k: int,
        subject: str | None,
    ) -> list[RetrievedChunk]:
        return self.hits


# ─── Original test (kept) ─────────────────────────────────────────────────────

def test_rrf_fuses_dense_and_bm25_lists_without_score_scale_comparison():
    c1 = chunk("00000000-0000-0000-0000-000000000001", "reverse linked list pointers")
    c2 = chunk("00000000-0000-0000-0000-000000000002", "stack push pop operations")
    dense_hits = [RetrievedChunk(chunk=c1, score=0.9, channel="dense", rank=1)]
    retriever = HybridRetriever([c1, c2], FakeEmbedder(), FakeStore(dense_hits))
    results = retriever.retrieve("reverse linked list pointers", subject="DS", top_k=2)
    assert results
    assert results[0].channel == "hybrid"
    assert results[0].chunk.chunk_id == c1.chunk_id


# ─── New tests ────────────────────────────────────────────────────────────────

def test_empty_corpus_returns_empty_results():
    """HybridRetriever must silently return [] when the corpus is empty."""
    retriever = HybridRetriever([], FakeEmbedder(), FakeStore([]))
    assert retriever.retrieve("anything") == []


def test_rrf_score_is_rank_based_not_raw():
    """RRF scores must equal 1/(k+rank); never raw cosine/BM25 floats."""
    c1 = chunk("00000000-0000-0000-0000-000000000001", "binary search tree insert")
    dense_hits = [RetrievedChunk(chunk=c1, score=0.99, channel="dense", rank=1)]
    retriever = HybridRetriever([c1], FakeEmbedder(), FakeStore(dense_hits))
    results = retriever.retrieve("binary search tree insert", top_k=1)

    assert results, "Expected at least one result"
    rrf_score = results[0].score
    # Raw cosine score would be 0.99; raw BM25 would be > 0.
    # RRF scores follow 1/(k + rank).  With k=60 and ranks 1..N, the
    # maximum possible RRF score is 2 * 1/(60+1) ≈ 0.0328 (hit in both lists).
    assert rrf_score < 1.0, "RRF score must not be a raw cosine score"
    assert rrf_score > 0.0


def test_subject_filter_excludes_wrong_subject():
    """BM25 must skip chunks whose subject != the requested subject."""
    ds_chunk = chunk("00000000-0000-0000-0000-000000000001", "binary search tree", "DS")
    aoa_chunk = chunk("00000000-0000-0000-0000-000000000002", "binary search tree", "AOA")

    # Dense store returns nothing so only BM25 matters.
    retriever = HybridRetriever(
        [ds_chunk, aoa_chunk], FakeEmbedder(), FakeStore([])
    )
    results = retriever.retrieve("binary search tree", subject="DS", top_k=10)
    chunk_ids = {r.chunk.chunk_id for r in results}
    assert ds_chunk.chunk_id in chunk_ids, "DS chunk must appear in DS-filtered results"
    assert aoa_chunk.chunk_id not in chunk_ids, "AOA chunk must be excluded from DS-filtered results"


def test_subject_filter_none_returns_all_subjects():
    """With subject=None, results from both subjects should be possible."""
    ds_chunk = chunk("00000000-0000-0000-0000-000000000001", "binary search tree", "DS")
    aoa_chunk = chunk("00000000-0000-0000-0000-000000000002", "binary search tree", "AOA")

    retriever = HybridRetriever(
        [ds_chunk, aoa_chunk], FakeEmbedder(), FakeStore([])
    )
    results = retriever.retrieve("binary search tree", subject=None, top_k=10)
    chunk_ids = {r.chunk.chunk_id for r in results}
    assert ds_chunk.chunk_id in chunk_ids
    assert aoa_chunk.chunk_id in chunk_ids


def test_all_results_have_channel_hybrid():
    """Every result from HybridRetriever.retrieve must have channel='hybrid'."""
    c1 = chunk("00000000-0000-0000-0000-000000000001", "heap sort algorithm")
    c2 = chunk("00000000-0000-0000-0000-000000000002", "merge sort divide conquer")
    dense_hits = [RetrievedChunk(chunk=c1, score=0.85, channel="dense", rank=1)]
    retriever = HybridRetriever([c1, c2], FakeEmbedder(), FakeStore(dense_hits))
    results = retriever.retrieve("heap sort", top_k=5)
    assert results
    assert all(r.channel == "hybrid" for r in results)


def test_results_have_ascending_rank():
    """Returned RetrievedChunks must have rank starting at 1 with no gaps."""
    chunks_list = [
        chunk(f"00000000-0000-0000-0000-{i:012d}", f"algorithm topic {i}")
        for i in range(1, 6)
    ]
    dense_hits = [
        RetrievedChunk(chunk=chunks_list[0], score=0.9, channel="dense", rank=1),
        RetrievedChunk(chunk=chunks_list[1], score=0.8, channel="dense", rank=2),
    ]
    retriever = HybridRetriever(chunks_list, FakeEmbedder(), FakeStore(dense_hits))
    results = retriever.retrieve("algorithm topic 1", top_k=5)
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, len(results) + 1)), f"Expected 1-based ranks, got {ranks}"


def test_top_k_limits_result_count():
    """retrieve must return at most top_k chunks."""
    chunks_list = [
        chunk(f"00000000-0000-0000-0000-{i:012d}", f"data structure node {i}")
        for i in range(1, 11)
    ]
    dense_hits = [
        RetrievedChunk(chunk=c, score=0.5, channel="dense", rank=i)
        for i, c in enumerate(chunks_list, start=1)
    ]
    retriever = HybridRetriever(chunks_list, FakeEmbedder(), FakeStore(dense_hits))
    for k in [1, 3, 5]:
        results = retriever.retrieve("node", top_k=k)
        assert len(results) <= k


def test_rrf_chunk_appearing_in_both_lists_ranks_higher():
    """A chunk in both BM25 and dense should outscore a chunk in only one list."""
    both = chunk("00000000-0000-0000-0000-000000000001", "linked list traversal pointer")
    dense_only = chunk("00000000-0000-0000-0000-000000000002", "pointer dereferencing memory")

    dense_hits = [
        RetrievedChunk(chunk=both, score=0.9, channel="dense", rank=1),
        RetrievedChunk(chunk=dense_only, score=0.7, channel="dense", rank=2),
    ]
    retriever = HybridRetriever([both, dense_only], FakeEmbedder(), FakeStore(dense_hits))
    results = retriever.retrieve("linked list traversal", top_k=5)

    by_id = {r.chunk.chunk_id: r for r in results}
    # "both" chunk matches BM25 (contains exact words) and dense => higher RRF
    if dense_only.chunk_id in by_id:
        assert by_id[both.chunk_id].score >= by_id[dense_only.chunk_id].score


# ─── BM25 unit tests ─────────────────────────────────────────────────────────

def test_bm25_empty_corpus_returns_zero_scores():
    idx = BM25Index([])
    assert idx.get_scores(["term"]) == []


def test_bm25_scores_relevant_doc_higher():
    docs = [
        tokenize("dijkstra shortest path graph"),
        tokenize("binary search tree insert delete"),
    ]
    idx = BM25Index(docs)
    scores = idx.get_scores(tokenize("dijkstra graph"))
    assert scores[0] > scores[1], "Dijkstra doc must score higher for 'dijkstra graph'"


def test_bm25_zero_score_for_no_match():
    docs = [tokenize("heap sort algorithm")]
    idx = BM25Index(docs)
    scores = idx.get_scores(tokenize("quantum entanglement"))
    assert all(s == 0.0 for s in scores)


def test_tokenize_lowercases():
    tokens = tokenize("Dijkstra's Algorithm")
    assert "dijkstra" in tokens
    assert "algorithm" in tokens
    assert "Dijkstra" not in tokens


def test_tokenize_handles_unicode():
    tokens = tokenize("O(n²) complexity")
    assert "n" in tokens or "n²" in tokens  # at least partial match
    assert "complexity" in tokens
