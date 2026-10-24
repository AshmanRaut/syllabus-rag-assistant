from course_qa.schemas import SourceChunk, RetrievedChunk
from course_qa.retrieval.hybrid import HybridRetriever

class FakeEmbedder:
    def embed_query(self, text): return [0.1, 0.2]

class FakeStore:
    def __init__(self, hits): self.hits = hits
    def search(self, vector, *, top_k, subject): return self.hits

def chunk(cid, text, subject="DS"):
    return SourceChunk(chunk_id=cid, source_id="src_" + cid, subject=subject, source_type="text",
        source_file="DS notes/Typed/example.pdf", text=text, content_hash=cid, source_hash="hash")

def test_rrf_fuses_dense_and_bm25_lists_without_score_scale_comparison():
    c1 = chunk("00000000-0000-0000-0000-000000000001", "reverse linked list pointers")
    c2 = chunk("00000000-0000-0000-0000-000000000002", "stack push pop operations")
    dense_hits = [RetrievedChunk(chunk=c1, score=0.9, channel="dense", rank=1)]
    retriever = HybridRetriever([c1, c2], FakeEmbedder(), FakeStore(dense_hits))
    results = retriever.retrieve("reverse linked list pointers", subject="DS", top_k=2)
    assert results
    assert results[0].channel == "hybrid"
    assert results[0].chunk.chunk_id == c1.chunk_id
