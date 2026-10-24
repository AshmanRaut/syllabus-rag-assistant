from course_qa.config import settings
from course_qa.retrieval.hybrid import load_chunks
from course_qa.retrieval.embedder import SentenceTransformerEmbedder
from course_qa.retrieval.qdrant_store import QdrantDenseStore

if __name__ == "__main__":
    chunks = load_chunks()
    if not chunks: raise SystemExit("No chunks found. Run scripts/ingest.py first.")
    embedder = SentenceTransformerEmbedder(settings.embedding_model)
    store = QdrantDenseStore(embedder.dimension)
    batch_size = 32
    total = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors = embedder.embed_documents([c.text for c in batch])
        total += store.upsert(batch, vectors)
        print(f"Indexed {total}/{len(chunks)} chunks")
    print(f"Indexed {total} chunks into Qdrant collection {settings.qdrant_collection!r}")
