"""Index all chunks from chunks.jsonl into the Qdrant collection.

Usage:
    python scripts/index.py             # upsert (idempotent)
    python scripts/index.py --rebuild   # drop + recreate collection, then index
"""
from __future__ import annotations

import argparse
import sys
import time

# Ensure src/ is on the path when run directly.
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from course_qa.config import settings
from course_qa.retrieval.hybrid import load_chunks
from course_qa.retrieval.embedder import SentenceTransformerEmbedder
from course_qa.retrieval.qdrant_store import QdrantDenseStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Index course chunks into Qdrant.")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Drop and recreate the Qdrant collection before indexing. "
             "Use after removing chunks to clear stale points.",
    )
    args = parser.parse_args()

    # ── Load chunks ──────────────────────────────────────────────────────────
    print(f"Loading chunks from {settings.chunks_jsonl} …")
    chunks = load_chunks()
    if not chunks:
        raise SystemExit(
            "No chunks found. Run scripts/ingest.py first to produce chunks.jsonl."
        )
    print(f"Loaded {len(chunks)} chunks.")

    # ── Load embedder ────────────────────────────────────────────────────────
    print(f"Loading embedding model '{settings.embedding_model}' …")
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    print(f"Embedder ready. Dimension = {embedder.dimension}.")

    # ── Connect to Qdrant (create collection if missing) ────────────────────
    store = QdrantDenseStore(embedder.dimension)

    # ── Optionally rebuild (drop + recreate) ────────────────────────────────
    if args.rebuild:
        print(f"--rebuild: dropping collection '{settings.qdrant_collection}' …")
        store.client.delete_collection(settings.qdrant_collection)
        from qdrant_client import models as qmodels
        store.client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=qmodels.VectorParams(
                size=embedder.dimension,
                distance=qmodels.Distance.COSINE,
            ),
        )
        print(f"Collection '{settings.qdrant_collection}' recreated.")

    # ── Embed + upsert in batches ────────────────────────────────────────────
    batch_size = 32
    total = 0
    t0 = time.perf_counter()

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        vectors = embedder.embed_documents([c.text for c in batch])
        total += store.upsert(batch, vectors)
        elapsed = time.perf_counter() - t0
        print(
            f"  Indexed {total}/{len(chunks)} chunks "
            f"({elapsed:.1f}s elapsed, "
            f"{total / elapsed:.1f} chunks/s)"
        )

    elapsed = time.perf_counter() - t0
    print(
        f"\nDone. Indexed {total} chunks into collection "
        f"'{settings.qdrant_collection}' in {elapsed:.1f}s."
    )

    # ── Quick sanity-check ───────────────────────────────────────────────────
    info = store.client.get_collection(settings.qdrant_collection)
    print(f"Collection point count: {info.points_count}")
    if info.points_count != len(chunks):
        print(
            f"WARNING: expected {len(chunks)} points, "
            f"got {info.points_count}. "
            "Some chunks may share a chunk_id (duplicate upsert is idempotent)."
        )
    store.close()


if __name__ == "__main__":
    main()
