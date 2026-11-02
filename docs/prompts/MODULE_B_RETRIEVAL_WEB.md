# Module B — Qdrant, Hybrid Retrieval, and Web Search

## You are Contributor B

You are implementing the retrieval and web-search modules for the **Syllabus-Aware DS/AoA NLP Assistant**, a four-person NLP mini-project.

**Begin implementing immediately.** Do not return another plan. Read the files listed below, then write working code.

---

## ✅ Module A status — COMPLETE

Module A (ingestion) is done and merged on branch `feat/ingestion-ocr`. Before you start, pull the latest `main`:

```bash
git checkout main && git pull origin main
```

**What A produced for you:**

| Item | Detail |
|---|---|
| `data/processed/chunks.jsonl` | **575 chunks** (195 typed PDF, 362 code, 18 syllabus) |
| `data/processed/source_manifest.json` | Page-level OCR manifest (153 processed, 281 pending OCR) |
| `data/page_images/` | Rendered page PNGs for every PDF page (gitignored, generated locally) |
| `.env.example` | All env vars pre-filled with correct defaults |

**Do NOT wait for chunks — they exist now.** Skip Task 3 (creating test chunks) and go straight to indexing real data.

### Actual folder layout (use these exact paths in tests)

```
notes/
├── aoa_codes/          (11 .c files)
├── aoa_notes/Typed/    (18 typed PDFs)
├── aoa_notes/Handwritten/  (10 handwritten PDFs — pending OCR)
├── aoa_notes/          (3 root-level exam PDFs)
├── ds_codes/           (30 .c files)
├── ds_notes/Handwritten/   (12 handwritten PDFs — pending OCR)
└── syllabus/           (AOA_Syllabus.pdf, DS_Syllabus.pdf)
```

### Chunk breakdown (actual counts)
- `typed_pdf`: 195 chunks (AOA theory notes + exam papers)
- `code`: 362 chunks (C functions, one chunk per function)
- `syllabus`: 18 chunks
- `handwritten_pdf`: 0 text chunks yet (281 pages marked `ocr_status="pending"`)

---

## Project context

This is a RAG system that answers DS/AoA exam questions using course notes (typed PDFs, handwritten PDFs, C code) with hybrid retrieval (Qdrant dense + BM25 + Reciprocal Rank Fusion) and evidence-grounded generation. Your module takes the canonical `chunks.jsonl` produced by Contributor A, indexes chunks in Qdrant, provides BM25 retrieval, fuses results with RRF, and implements web search with Tavily/DDGS.

## Repository root

```
/Users/ashmanraut/Ashman/Fr. CRCE/NLP/syllabus-rag-assistant
```

## Files to inspect first

Read these files before making any changes:

1. `src/course_qa/schemas.py` — all Pydantic models (DO NOT CHANGE)
2. `src/course_qa/contracts.py` — Protocol interfaces (DO NOT CHANGE)
3. `src/course_qa/config.py` — Settings dataclass with all env vars
4. `src/course_qa/retrieval/hybrid.py` — HybridRetriever with BM25 + RRF (also has `load_chunks`, `save_chunks`)
5. `src/course_qa/retrieval/embedder.py` — SentenceTransformerEmbedder
6. `src/course_qa/retrieval/qdrant_store.py` — QdrantDenseStore
7. `src/course_qa/web/search.py` — WebSearch with Tavily + DDGS + allowlist
8. `scripts/index.py` — indexing script
9. `config/web_allowlist.yaml` — allowed web domains
10. `tests/test_hybrid.py` — existing hybrid retrieval test
11. `docs/SHARED_CONTRACT.md` — full contract specification

## Your files (you own these exclusively)

- `src/course_qa/retrieval/embedder.py`
- `src/course_qa/retrieval/hybrid.py`
- `src/course_qa/retrieval/qdrant_store.py`
- `src/course_qa/retrieval/__init__.py`
- `src/course_qa/web/search.py`
- `src/course_qa/web/__init__.py`
- `scripts/index.py`
- `config/web_allowlist.yaml`
- `tests/test_hybrid.py` (and any new retrieval/web tests you add)

**DO NOT modify** files owned by other contributors:
- `src/course_qa/ingestion/*` (Contributor A — COMPLETE, do not touch)
- `src/course_qa/generation/*` (Contributor C)
- `src/course_qa/service.py` (Contributor C)
- `src/course_qa/app.py` (Contributor D)
- `src/course_qa/schemas.py` (Contributor A — tech lead)
- `src/course_qa/contracts.py` (Contributor A — tech lead)
- `src/course_qa/config.py` (Contributor A — tech lead)

## Shared schemas (FROZEN — do not change)

```python
class SourceChunk(BaseModel):
    chunk_id: str
    source_id: str
    subject: Subject          # "DS" | "AOA" | "UNKNOWN"
    source_type: SourceType
    source_file: str
    page_number: int | None = None
    function_name: str | None = None
    module: str | None = None
    title: str | None = None
    text: str
    image_path: str | None = None
    content_hash: str
    source_hash: str
    chunk_index: int = 0
    ocr_status: Literal["not_needed", "pending", "processed", "failed", "manual"] = "not_needed"
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

class RetrievedChunk(BaseModel):
    chunk: SourceChunk
    score: float
    channel: Literal["dense", "bm25", "hybrid"]
    rank: int | None = None

class WebSource(BaseModel):
    source_id: str
    title: str
    url: str
    domain: str
    snippet: str
    retrieved_at: str
    text: str | None = None
    source_type: Literal["web"] = "web"
```

## Required interfaces (from contracts.py)

```python
class Embedder(Protocol):
    @property
    def dimension(self) -> int: ...
    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

class NotesRetriever(Protocol):
    def retrieve(self, question: str, *, subject: str | None = None, top_k: int = 5) -> list[RetrievedChunk]: ...

class WebSearcher(Protocol):
    def search(self, query: str, *, max_results: int = 5) -> list[WebSource]: ...
```

## Implementation tasks (in priority order)

### Task 1: Environment setup

```bash
# Copy the pre-filled example (A already created this)
cp .env.example .env
# Edit .env to set your Qdrant URL and optionally Tavily key
# Then activate the venv A created:
source .venv/bin/activate
# Install web extras:
pip install -r requirements-web.txt
```

Start Qdrant:
```bash
docker compose up -d qdrant
# Verify:
curl http://localhost:6333/healthz
```

### Task 2: Run existing tests first

```bash
pytest tests/test_hybrid.py -v
```

### Task 3: ~~Create test chunks~~ — SKIP, use real data

**Module A has already produced 575 real chunks.** Load them directly:

```python
from course_qa.retrieval.hybrid import load_chunks
chunks = load_chunks()
print(f"{len(chunks)} chunks")  # → 575 chunks
```

Use real chunks for all your development and testing. The test chunks suggested in the original spec are no longer needed.

### Task 4: Test embedding and Qdrant indexing

Verify `SentenceTransformerEmbedder` loads and produces vectors:
```python
from course_qa.retrieval.embedder import SentenceTransformerEmbedder
embedder = SentenceTransformerEmbedder("sentence-transformers/all-MiniLM-L6-v2")
assert embedder.dimension == 384
vectors = embedder.embed_documents(["Dijkstra's shortest path"])
assert len(vectors[0]) == 384
```

Verify `QdrantDenseStore` can upsert and search:
```python
from course_qa.retrieval.qdrant_store import QdrantDenseStore
store = QdrantDenseStore(embedder.dimension)
# Use a small sample first
sample = chunks[:10]
sample_vecs = embedder.embed_documents([c.text for c in sample])
store.upsert(sample, sample_vecs)
results = store.search(embedder.embed_query("Dijkstra shortest path"), top_k=3)
assert len(results) > 0
```

### Task 5: Test BM25 and hybrid retrieval

Verify `HybridRetriever.retrieve()` returns fused results:
```python
from course_qa.retrieval.hybrid import HybridRetriever
retriever = HybridRetriever(chunks, embedder, store)
results = retriever.retrieve("Dijkstra's algorithm", top_k=3)
assert all(r.channel == "hybrid" for r in results)
for r in results:
    print(r.chunk.source_file, r.chunk.function_name or f"page {r.chunk.page_number}")
```

Test subject filtering:
```python
# DS code chunks should rank highly for BST question
ds_results = retriever.retrieve("binary search tree insert", subject="DS", top_k=3)
assert all(r.chunk.subject == "DS" for r in ds_results)
```

### Task 6: Run `scripts/index.py` with real data

```bash
python scripts/index.py
```

This embeds all 575 chunks and upserts them into Qdrant. Verify with:
```python
from qdrant_client import QdrantClient
client = QdrantClient(url="http://localhost:6333")
info = client.get_collection("course_chunks")
print(f"Points: {info.points_count}")  # → 575
```

### Task 7: Verify web search adapters

The existing `web/search.py` is already complete. Test it:

1. **Web disabled mode**: Set `WEB_SEARCH_MODE=off` → `WebSearch().search("test")` returns `[]`
2. **DDGS fallback**: Without `TAVILY_API_KEY`, verify DDGS search works (best-effort, may be throttled)
3. **Allowlist enforcement**: Verify only allowed domains pass through
4. **Error resilience**: Web search failure must not raise — it should be caught by the caller in `service.py`

**Important**: The `ddgs` package import is `from ddgs import DDGS`. Verify this is correct for the installed version. Older versions used `from duckduckgo_search import DDGS`. If the import fails, fix it.

### Task 8: Write additional tests

Add tests to `tests/test_hybrid.py` or create new test files:

```python
# Test subject filtering
def test_subject_filter_excludes_wrong_subject():
    # Create DS and AOA chunks, query with subject="DS", verify AOA excluded from BM25

# Test RRF doesn't compare raw scores
def test_rrf_score_is_rank_based_not_raw():
    # Verify RRF scores are 1/(k+rank), not raw cosine/BM25 scores

# Test empty corpus
def test_empty_corpus_returns_empty_results():
    retriever = HybridRetriever([], FakeEmbedder(), FakeStore([]))
    assert retriever.retrieve("anything") == []
```

For web:
```python
# tests/test_web.py
def test_web_search_off_returns_empty():
    # Mock settings.web_search_mode = "off"
    
def test_allowlist_rejects_unlisted_domains():
    from course_qa.web.search import _in_allowlist
    assert _in_allowlist("https://geeksforgeeks.org/test", ["geeksforgeeks.org"])
    assert not _in_allowlist("https://evil.com/test", ["geeksforgeeks.org"])
```

### Task 9: Add `--rebuild` flag to `scripts/index.py`

If re-indexing is needed after a corpus change, the collection should be rebuilt. The current code uses `upsert` with `chunk_id` as the point ID, so re-indexing is idempotent. However, if chunks are removed, stale points remain.

Add a `--rebuild` flag that drops and recreates the collection:

```python
parser.add_argument("--rebuild", action="store_true", help="Drop and recreate the Qdrant collection")
```

## Dependencies

- **From Contributor A**: ✅ `data/processed/chunks.jsonl` — **575 chunks ready now**. `load_chunks()` from `hybrid.py` reads it.
- **External**: Qdrant (Docker or local path mode), `sentence-transformers` model download (~80MB first time).

## Configuration (from config.py)

```python
qdrant_url: str         # "http://localhost:6333" — blank for local path mode
qdrant_collection: str  # "course_chunks"
embedding_model: str    # "sentence-transformers/all-MiniLM-L6-v2"
dense_top_k: int        # 8
bm25_top_k: int         # 8
hybrid_top_k: int       # 5
rrf_k: int              # 60
web_search_mode: str    # "auto" | "off" | "tavily" | "ddgs"
tavily_api_key: str     # empty = no Tavily, falls back to DDGS
web_max_results: int    # 5
web_extract_full_text: bool  # false
```

## Tests to run

```bash
pytest tests/test_hybrid.py -v
pytest tests/test_web.py -v          # if you create this
python scripts/index.py              # indexes real 575 chunks
```

## Acceptance criteria

- [ ] `pytest tests/test_hybrid.py -v` passes
- [ ] Qdrant running (Docker or local path) with 575 indexed chunks
- [ ] `HybridRetriever.retrieve("Dijkstra")` returns relevant chunks with `channel="hybrid"`
- [ ] Subject filter restricts results to the requested subject
- [ ] `WebSearch().search("test")` does not crash (returns results or empty list)
- [ ] `WEB_SEARCH_MODE=off` → web search returns empty list
- [ ] Web provider failure does not crash (caught by caller)
- [ ] Allowlist filtering works correctly
- [ ] `scripts/index.py` runs successfully and indexes all 575 chunks
- [ ] No retrieval-method comparison framework built (just the hybrid pipeline)

## Integration instructions

1. Work on branch `feat/qdrant-hybrid-web`
2. Your branch merges **SECOND** (after Contributor A, whose branch is already on `feat/ingestion-ocr`)
3. Pull `main` first — A's scanner fix and pyproject.toml updates are already there
4. Contributor C will use `HybridRetriever` via the `NotesRetriever` protocol
5. Contributor C will use `WebSearch` via the `WebSearcher` protocol

## Error reporting

If Qdrant won't start, the embedding model won't download, or DDGS is throttled, report the error honestly. Use Qdrant local path mode as fallback. Document which web provider works.

## Important constraints

- Do NOT build a retrieval comparison framework (dense vs BM25 vs hybrid evaluation pipeline)
- Do NOT add a second vector database
- Do NOT add a separate reranker model
- The BM25 index is built in-process from `chunks.jsonl` — this is correct for the corpus size
- RRF scores are rank-based fusion values, NOT calibrated probabilities

## Git commands

```bash
git checkout main && git pull origin main
git checkout -b feat/qdrant-hybrid-web
# ... implement changes ...
pytest -q
git add -A
git commit -m "feat(retrieval): index 575 chunks, verify hybrid retrieval, web tests"
git push origin feat/qdrant-hybrid-web
```
