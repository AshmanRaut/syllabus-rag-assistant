"""Smoke tests for QdrantDenseStore using local embedded mode.

These tests use Qdrant's in-process embedded mode (no Docker required).
They are marked 'qdrant' and can be skipped with:
    pytest tests/ -v -m "not qdrant"

Run them explicitly with:
    pytest tests/test_qdrant_store.py -v
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from course_qa.schemas import SourceChunk, RetrievedChunk


# ─── Fixtures ─────────────────────────────────────────────────────────────────

def _make_chunk(cid: str, text: str, subject: str = "DS") -> SourceChunk:
    return SourceChunk(
        chunk_id=cid,
        source_id="src_" + cid,
        subject=subject,          # type: ignore[arg-type]
        source_type="text",
        source_file="test/example.txt",
        text=text,
        content_hash=cid,
        source_hash="sh_" + cid,
    )


CHUNKS = [
    _make_chunk("00000000-0000-0000-0000-000000000001", "Dijkstra shortest path graph"),
    _make_chunk("00000000-0000-0000-0000-000000000002", "binary search tree insert delete"),
    _make_chunk("00000000-0000-0000-0000-000000000003", "merge sort divide and conquer"),
    _make_chunk("00000000-0000-0000-0000-000000000004", "heap sort priority queue", subject="AOA"),
    _make_chunk("00000000-0000-0000-0000-000000000005", "Floyd Warshall all pairs shortest path", subject="AOA"),
]

VECTOR_DIM = 4
FAKE_VECTORS = [
    [1.0, 0.0, 0.0, 0.0],
    [0.0, 1.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.0],
    [0.0, 0.0, 0.0, 1.0],
    [0.7, 0.0, 0.0, 0.7],
]


@pytest.fixture(scope="module")
def store_and_collection():
    """Spin up an embedded Qdrant store with test data, yield it, then clean up.

    The client is closed explicitly before the tempdir is removed to prevent
    a Windows WinError 32 (file in use) on the Qdrant .lock file.
    """
    try:
        from qdrant_client import QdrantClient, models
    except ImportError:
        pytest.skip("qdrant-client not installed")

    tmpdir = tempfile.mkdtemp()
    try:
        from course_qa.retrieval.qdrant_store import QdrantDenseStore

        client = QdrantClient(path=tmpdir)
        collection = "test_course_chunks"
        client.create_collection(
            collection_name=collection,
            vectors_config=models.VectorParams(size=VECTOR_DIM, distance=models.Distance.COSINE),
        )

        # Build store object manually (bypass __init__ that reads settings).
        store = object.__new__(QdrantDenseStore)
        store.client = client
        store.collection = collection

        count = store.upsert(CHUNKS, FAKE_VECTORS)
        assert count == len(CHUNKS)

        yield store

    finally:
        # Close the client first so Qdrant releases the .lock file.
        try:
            client.close()
        except Exception:
            pass
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.mark.qdrant
def test_upsert_and_count(store_and_collection):
    store = store_and_collection
    info = store.client.get_collection(store.collection)
    assert info.points_count == len(CHUNKS)


@pytest.mark.qdrant
def test_search_returns_results(store_and_collection):
    store = store_and_collection
    query_vec = [1.0, 0.0, 0.0, 0.0]  # close to chunk 0
    results = store.search(query_vec, top_k=3)
    assert len(results) >= 1
    assert all(isinstance(r, RetrievedChunk) for r in results)
    assert all(r.channel == "dense" for r in results)


@pytest.mark.qdrant
def test_search_subject_filter(store_and_collection):
    store = store_and_collection
    query_vec = [0.0, 0.0, 0.0, 1.0]  # close to chunk 3 (AOA)
    results_aoa = store.search(query_vec, top_k=5, subject="AOA")
    assert results_aoa, "Expected at least one AOA result"
    assert all(r.chunk.subject == "AOA" for r in results_aoa), (
        "All filtered results must have subject=AOA"
    )


@pytest.mark.qdrant
def test_search_no_subject_filter_returns_any(store_and_collection):
    store = store_and_collection
    results = store.search([0.5, 0.5, 0.0, 0.0], top_k=5, subject=None)
    subjects = {r.chunk.subject for r in results}
    assert len(subjects) > 0


@pytest.mark.qdrant
def test_upsert_is_idempotent(store_and_collection):
    """Re-upserting the same chunks must not change point count."""
    store = store_and_collection
    before = store.client.get_collection(store.collection).points_count
    store.upsert(CHUNKS, FAKE_VECTORS)
    after = store.client.get_collection(store.collection).points_count
    assert before == after, "Duplicate upsert must not increase point count"


@pytest.mark.qdrant
def test_search_top_k_respected(store_and_collection):
    store = store_and_collection
    for k in [1, 2, 3]:
        results = store.search([1.0, 0.0, 0.0, 0.0], top_k=k)
        assert len(results) <= k


@pytest.mark.qdrant
def test_ranks_are_1_indexed(store_and_collection):
    store = store_and_collection
    results = store.search([1.0, 0.0, 0.0, 0.0], top_k=3)
    if results:
        assert results[0].rank == 1
        for i, r in enumerate(results, start=1):
            assert r.rank == i
