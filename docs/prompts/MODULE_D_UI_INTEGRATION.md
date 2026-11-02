# Module D — Gradio UI, Integration, and Project Delivery

## You are Contributor D — the Integrator

You are implementing the Gradio UI, cross-module integration tests, and project delivery artifacts for the **Syllabus-Aware DS/AoA NLP Assistant**, a four-person NLP mini-project. You are also the integrator who ensures all modules work together seamlessly.

**Begin implementing immediately.** Do not return another plan. Read the files listed below, then write working code.

---

## ✅ Module A status — COMPLETE

Module A (ingestion) is finished and committed on branch `feat/ingestion-ocr`.

**What A produced:**

| Item | Detail |
|---|---|
| `data/processed/chunks.jsonl` | **575 canonical chunks** (195 typed PDF, 362 code, 18 syllabus) |
| `data/processed/source_manifest.json` | Page-level OCR manifest (153 processed, 281 pending OCR) |
| `data/page_images/` | Rendered page PNGs for PDF pages (used directly by your UI gallery) |
| `.env.example` | All env vars configured with sensible defaults |
| `.venv/` | Virtual environment set up at repo root |

### ✅ Modules B & C status — COMPLETE

- **Module B** (retrieval & web) is complete on `feat/qdrant-hybrid-web` (commit `8d07297`):
  - 575 canonical chunks indexed in Qdrant & BM25 (`.data/qdrant`, `data/processed/chunks.jsonl`).
  - `HybridRetriever` implements `NotesRetriever` protocol with dense + BM25 RRF fusion.
  - `WebSearch` implements `WebSearcher` protocol with domain allowlist and DDGS fallback.
- **Module C** (generation & citations) is complete on `feat/generation-citations` (commit `7f7009f`):
  - `MockGenerator`: Deterministic offline/testing generator conforming to `AnswerGenerator` protocol.
  - `OpenAICompatibleGenerator`: Provider-neutral LLM generator with deferred imports and clean abstention.
  - `create_generator()`: Factory in `course_qa.generation` that selects the real or mock generator based on `settings.llm_model` and catches init errors.
  - `citations.py`: Assigns sequential `[S1]`, `[S2]`, ... labels, automatically skips OCR-pending/failed or empty chunks, and strips invalid citations via `retain_only_cited_sources()`.
  - `service.py`: `QAService` orchestrates notes retrieval -> `should_search_web` permission gate and routing -> generation -> grounding and abstention enforcement.
  - Module C test suite (`tests/test_citations.py`, `tests/test_routing.py`, `tests/test_service.py`): 29/29 tests passing.

---

## Project context

This is a RAG system that answers DS/AoA exam questions using course notes (typed PDFs, handwritten PDFs, C code) with hybrid retrieval (Qdrant + BM25 + RRF) and evidence-grounded generation. Your module wires all components together through the Gradio UI, validates cross-module behavior with integration tests, compiles evaluation questions, and leads the final system demo.

## Repository root

```
/Users/ashmanraut/Ashman/Fr. CRCE/NLP/syllabus-rag-assistant
```

## Files to inspect first

Read these files before making any changes:

1. `src/course_qa/schemas.py` — all Pydantic models (DO NOT CHANGE)
2. `src/course_qa/contracts.py` — Protocol interfaces (DO NOT CHANGE)
3. `src/course_qa/config.py` — Settings dataclass
4. `src/course_qa/app.py` — existing Gradio UI scaffold
5. `src/course_qa/service.py` — `QAService` and `should_search_web` routing
6. `src/course_qa/retrieval/hybrid.py` — `HybridRetriever` + `load_chunks`
7. `src/course_qa/retrieval/embedder.py` — `SentenceTransformerEmbedder`
8. `src/course_qa/retrieval/qdrant_store.py` — `QdrantDenseStore`
9. `src/course_qa/generation/generator.py` — `MockGenerator`, `OpenAICompatibleGenerator`, `create_generator()`
10. `src/course_qa/generation/citations.py` — `build_labelled_evidence()`, `retain_only_cited_sources()`
11. `src/course_qa/generation/__init__.py` — Generator public API exports (`create_generator`, `MockGenerator`)
12. `src/course_qa/web/search.py` — `WebSearch` with DDGS fallback
13. `tests/test_service.py` — End-to-end service and generator unit tests
14. `docs/SHARED_CONTRACT.md` — full contract specification
15. `docs/INTEGRATION_CHECKLIST.md` — team merge & verification checklist

## Your files (you own these exclusively)

- `src/course_qa/app.py`
- `tests/test_integration.py` (create this)
- `data/evaluation/questions.csv` (create this)
- `docs/EVALUATION.md` (fill in results)

**DO NOT modify** files owned by other contributors:
- `src/course_qa/ingestion/*` (Contributor A)
- `src/course_qa/retrieval/*` (Contributor B)
- `src/course_qa/web/*` (Contributor B)
- `src/course_qa/generation/*` (Contributor C) — call via protocol / factory
- `src/course_qa/service.py` (Contributor C)
- `src/course_qa/schemas.py` (Contributor A)
- `src/course_qa/contracts.py` (Contributor A)
- `src/course_qa/config.py` (Contributor A)

## Shared schemas (FROZEN — reference only)

```python
class AnswerRequest(BaseModel):
    question: str
    subject: Subject | None = None      # "DS" | "AOA" | "UNKNOWN" | None
    use_web: bool = False
    answer_style: Literal["concise", "exam"] = "exam"

class AnswerResponse(BaseModel):
    answer: str
    citations: list[CitationRecord]
    notes_used: int
    web_used: int
    abstained: bool = False
    warnings: list[str] = Field(default_factory=list)

class CitationRecord(BaseModel):
    label: str                          # "S1", "S2", etc.
    source_kind: Literal["note", "code", "syllabus", "web"]
    source_file: str | None = None
    page_number: int | None = None
    function_name: str | None = None
    url: str | None = None
    title: str | None = None
    image_path: str | None = None
    source_id: str
```

---

## Implementation tasks (in priority order)

### Task 1: Verify existing UI scaffold

Read `src/course_qa/app.py`. It has:
- Question input text box, subject dropdown (`Any`, `DS`, `AOA`), answer style radio (`concise`, `exam`), web toggle checkbox
- Answer markdown panel, sources table/dataframe, warnings box, and page image gallery
- `build_service()` that wires all components

Test starting the app now:
```bash
source .venv/bin/activate
python -m course_qa.app
```
Identify any failure points when Qdrant or LLM credentials are not configured.

---

### Task 2: Make `build_service()` resilient

Make `build_service()` robust against missing external services (e.g. Qdrant daemon down, no LLM API key set, or unindexed chunks):

```python
def build_service():
    from .config import settings
    from .retrieval.hybrid import load_chunks, HybridRetriever
    from .retrieval.embedder import SentenceTransformerEmbedder
    from .retrieval.qdrant_store import QdrantDenseStore
    from .service import QAService
    from .web.search import WebSearch
    from .generation import create_generator, MockGenerator

    chunks = load_chunks()
    if not chunks:
        import warnings
        warnings.warn("No chunks loaded from data/processed/chunks.jsonl. Retrieval will return empty results.")
        chunks = []

    try:
        embedder = SentenceTransformerEmbedder(settings.embedding_model)
        store = QdrantDenseStore(embedder.dimension)
        retriever = HybridRetriever(chunks, embedder, store)
    except Exception as e:
        import warnings
        warnings.warn(f"Failed to initialize Qdrant/Embedder: {e}. Falling back to empty mock retriever.")
        class _EmptyRetriever:
            def retrieve(self, question, *, subject=None, top_k=5):
                return []
        retriever = _EmptyRetriever()

    # Generator: create_generator() automatically returns MockGenerator when LLM_MODEL is unset or init fails
    try:
        generator = create_generator()
    except Exception as e:
        import warnings
        warnings.warn(f"Failed to initialize generator: {e}. Using MockGenerator.")
        generator = MockGenerator()

    try:
        web_searcher = WebSearch()
    except Exception:
        class _NoOpWeb:
            def search(self, query, *, max_results=5):
                return []
        web_searcher = _NoOpWeb()

    return QAService(retriever, generator, web_searcher)
```

> [!NOTE]
> `MockGenerator` is already fully implemented and exported directly from `course_qa.generation` (`from course_qa.generation import MockGenerator, create_generator`).
> The `create_generator()` factory automatically inspects `settings.llm_model` and falls back to `MockGenerator` if no LLM credentials are set or if the real generator fails to initialize. You can also import `MockGenerator` directly for tests, eliminating the need to maintain an inline generator duplicate in `app.py`.

---

### Task 3: Improve the Gradio UI & Image Viewer

Enhance `respond()` in `app.py`:

1. **Catch exceptions gracefully**: Never crash the Gradio server; return errors cleanly in the warnings panel.
2. **Page image resolution**: For PDF citations with `c.image_path`, resolve them relative to the project root (e.g., `data/page_images/...`), check that the file exists, and pass the valid image paths to the Gradio gallery.
3. **Clean display formatting**:
   - Format source metadata clearly: `[S1]`, `kind`, `title`, `locator` (`file · page N` or `file · func()`), `URL`.
   - When `response.abstained` is `True`, prepend a prominent warning banner: `⚠️ Abstained: Insufficient course evidence`.

```python
def respond(question, subject, use_web, style):
    if not question or not question.strip():
        return "Please enter a question.", [], "No warnings.", []
    try:
        subj = None if subject in ("Any", None) else subject
        request = AnswerRequest(
            question=question.strip(),
            subject=subj,
            use_web=bool(use_web),
            answer_style=style,
        )
        response = service.answer(request)
        
        source_rows = []
        for c in response.citations:
            locator = c.source_file or c.url or c.title or c.source_id
            if c.page_number is not None:
                locator += f" · page {c.page_number}"
            if c.function_name:
                locator += f" · {c.function_name}()"
            source_rows.append([
                f"[{c.label}]", c.source_kind, c.title or "",
                locator, c.url or "", c.image_path or ""
            ])

        warnings_text = "\n".join(response.warnings) if response.warnings else "No warnings."
        if response.abstained:
            warnings_text = "⚠️ **Abstained**: " + warnings_text

        images = [
            str(Path(c.image_path))
            for c in response.citations
            if c.image_path and Path(c.image_path).exists()
        ]
        return response.answer, source_rows, warnings_text, images
    except Exception as exc:
        return f"Error: {type(exc).__name__}: {exc}", [], f"⚠️ Service error: {exc}", []
```

---

### Task 4: Create Evaluation Questions (`data/evaluation/questions.csv`)

Create `data/evaluation/questions.csv` using the verified paths in `notes/`:

```csv
question_id,question,subject,question_type,expected_source_file,expected_page_or_function,relevant_chunk_ids,use_web_expected
Q01,"Explain Dijkstra's algorithm with an example",AOA,algorithm,aoa_notes/Typed/Dijkstra_Algorithm.pdf,,_fill_after_indexing_,false
Q02,"Write the C code for BST insertion and explain its time complexity",DS,code,ds_codes/BinarySearchTree.c,insert,_fill_after_indexing_,false
Q03,"Explain the Fractional Knapsack problem using greedy approach",AOA,algorithm,aoa_notes/Typed/Fractional_Knapsack.pdf,,_fill_after_indexing_,false
Q04,"What is a circular queue? How is it implemented in C?",DS,code,ds_codes/CircularQueue.c,enqueue,_fill_after_indexing_,false
Q05,"Explain the N-Queen problem and solve for N=4",AOA,algorithm,aoa_notes/Typed/N_Queen_problem.pdf,,_fill_after_indexing_,false
Q06,"What is the time complexity of merge sort? Compare it with quicksort.",AOA,complexity,aoa_codes/SortingAlgorithms.c,mergeSort,_fill_after_indexing_,false
Q07,"Compare BFS and DFS traversals with their implementations",DS,code,ds_codes/DFSandBFS.c,BFS,_fill_after_indexing_,false
Q08,"Explain Floyd-Warshall algorithm for all-pairs shortest path",AOA,algorithm,aoa_notes/Typed/All_pair_shortest_path.pdf,,_fill_after_indexing_,false
Q09,"How does infix to postfix conversion work using a stack?",DS,code,ds_codes/InfixPostfix.c,infixToPostfix,_fill_after_indexing_,false
Q10,"What are real-world applications of Dijkstra's algorithm in networking?",AOA,application,,,true
Q11,"Compare Prim's and Kruskal's algorithms for Minimum Spanning Trees",AOA,algorithm,aoa_notes/Typed/Prim_Algorithm.pdf,,_fill_after_indexing_,false
Q12,"Explain the Sum of Subsets problem using backtracking",AOA,algorithm,aoa_notes/Typed/Sum_Of_Subsets.pdf,,_fill_after_indexing_,false
Q13,"What is quantum entanglement and quantum computing?",UNKNOWN,unsupported,,,_none_,false
Q14,"Explain recent developments in multimodal LLM architectures",UNKNOWN,unsupported,,,_none_,true
Q15,"Explain Bellman-Ford algorithm and how it handles negative weights",AOA,algorithm,aoa_notes/Typed/Bellman_Ford.pdf,,_fill_after_indexing_,false
```

---

### Task 5: Create Cross-Module Integration Tests

Create `tests/test_integration.py` to test end-to-end integration without requiring external servers:

```python
"""Cross-module integration tests using mock external providers."""
import pytest
from pathlib import Path
from course_qa.schemas import (
    AnswerRequest,
    AnswerResponse,
    RetrievedChunk,
    SourceChunk,
    CitationRecord,
)
from course_qa.generation import MockGenerator
from course_qa.service import QAService

# --- Mock components ---
class MockRetriever:
    def __init__(self, chunks=None):
        self._chunks = chunks or []

    def retrieve(self, question, *, subject=None, top_k=5):
        results = self._chunks
        if subject and subject != "UNKNOWN":
            results = [r for r in results if r.chunk.subject == subject]
        return results[:top_k]

class MockWebSearcher:
    def __init__(self, results=None, should_fail=False):
        self._results = results or []
        self._should_fail = should_fail

    def search(self, query, *, max_results=5):
        if self._should_fail:
            raise ConnectionError("Web search unavailable")
        return self._results[:max_results]

# Note: MockGenerator is imported directly from course_qa.generation.
# It uses the real Module C citation validation and evidence formatting pipeline.

# --- Fixtures ---
@pytest.fixture
def sample_chunk():
    return SourceChunk(
        chunk_id="int-test-001",
        source_id="src_int1",
        subject="AOA",
        source_type="typed_pdf",
        source_file="aoa_notes/Typed/Dijkstra_Algorithm.pdf",
        page_number=1,
        text="Dijkstra's algorithm finds shortest paths from a single source node in a weighted graph with non-negative edges.",
        content_hash="h1",
        source_hash="s1",
        title="Dijkstra · page 1",
    )

@pytest.fixture
def sample_code_chunk():
    return SourceChunk(
        chunk_id="int-test-002",
        source_id="src_int2",
        subject="DS",
        source_type="code",
        source_file="ds_codes/BinarySearchTree.c",
        function_name="insert",
        text="struct Node* insert(struct Node* node, int key) { if (node == NULL) return newNode(key); ... }",
        content_hash="h2",
        source_hash="s2",
        title="BinarySearchTree.c::insert",
    )

@pytest.fixture
def service_with_notes(sample_chunk):
    notes = [RetrievedChunk(chunk=sample_chunk, score=0.85, channel="hybrid", rank=1)]
    return QAService(MockRetriever(notes), MockGenerator(), MockWebSearcher())

# --- Tests ---
def test_note_backed_question_returns_citations(service_with_notes):
    response = service_with_notes.answer(AnswerRequest(question="Explain Dijkstra's algorithm"))
    assert response.answer
    assert len(response.citations) > 0
    assert not response.abstained
    assert response.notes_used == 1

def test_code_query_returns_function_citation(sample_code_chunk):
    notes = [RetrievedChunk(chunk=sample_code_chunk, score=0.9, channel="hybrid", rank=1)]
    service = QAService(MockRetriever(notes), MockGenerator(), MockWebSearcher())
    response = service.answer(AnswerRequest(question="BST insertion code", subject="DS"))
    assert any(c.source_kind == "code" for c in response.citations)
    assert any(c.function_name == "insert" for c in response.citations)

def test_out_of_corpus_question_abstains():
    service = QAService(MockRetriever([]), MockGenerator(), MockWebSearcher())
    response = service.answer(AnswerRequest(question="What is quantum entanglement?"))
    assert response.abstained
    assert len(response.citations) == 0
    assert len(response.warnings) > 0

def test_web_disabled_does_not_call_web():
    class TrackingWeb:
        called = False
        def search(self, query, *, max_results=5):
            TrackingWeb.called = True
            return []
    web = TrackingWeb()
    service = QAService(MockRetriever([]), MockGenerator(), web)
    service.answer(AnswerRequest(question="test", use_web=False))
    assert not TrackingWeb.called

def test_web_failure_does_not_crash(sample_chunk):
    notes = [RetrievedChunk(chunk=sample_chunk, score=0.01, channel="hybrid", rank=1)]
    service = QAService(MockRetriever(notes), MockGenerator(), MockWebSearcher(should_fail=True))
    response = service.answer(AnswerRequest(question="real world applications", use_web=True))
    assert response.answer
    assert any("web search failed" in w.lower() for w in response.warnings)

def test_subject_filter_respected(sample_chunk, sample_code_chunk):
    all_notes = [
        RetrievedChunk(chunk=sample_chunk, score=0.8, channel="hybrid", rank=1),
        RetrievedChunk(chunk=sample_code_chunk, score=0.7, channel="hybrid", rank=2),
    ]
    service = QAService(MockRetriever(all_notes), MockGenerator(), MockWebSearcher())
    response = service.answer(AnswerRequest(question="test", subject="DS"))
    for c in response.citations:
        if c.source_file:
            assert "ds_" in c.source_file.lower() or c.source_kind == "web"
```

---

### Task 6: Prepare Demo Script

Prepare a 3-minute live presentation flow:

1. **Boot**: `python -m course_qa.app` (starts Gradio on `http://127.0.0.1:7860`).
2. **Typed PDF Question**: "Explain Dijkstra's algorithm"
   - Show `[S1]` inline citations.
   - Show page number in Sources table.
   - Show PDF page image in gallery.
3. **C Code Question**: "Write C code for BST insertion"
   - Show function-level citation `BinarySearchTree.c::insert`.
4. **Web Search Augmentation**: Toggle Web ON, ask: "What are real-world applications of Dijkstra's algorithm in networking?"
   - Show sequential `[Sn]` citations (with kind `"web"`), domain labels, and URLs in Sources table.
5. **Abstention Behavior**: Ask: "What is quantum computing?"
   - Show abstention warning and absence of hallucinated notes.

---

### Task 7: Fill Evaluation Results (`docs/EVALUATION.md`)

After retrieval and generation are active, execute the 15 questions from `questions.csv` and document:
- Hit@3 and Hit@5 retrieval accuracy
- Citation precision (% of citations that actually support claims)
- Abstention rate on out-of-domain questions
- Average query latency

---

## Acceptance criteria

- [ ] `python -m course_qa.app` boots cleanly without crashing
- [ ] Gradio UI displays all controls (question, subject, answer style, web toggle)
- [ ] Note-backed questions display answers with citations and source metadata
- [ ] Code questions display function-level citations
- [ ] Web-disabled mode makes no web queries
- [ ] Web-enabled mode displays web citations separately
- [ ] Out-of-corpus queries trigger abstention cleanly
- [ ] Rendered page images appear in Gradio gallery when PDF sources are cited
- [ ] `pytest tests/test_integration.py` passes
- [ ] `data/evaluation/questions.csv` contains 15 curated questions
- [ ] All repository tests pass: `pytest -q`

---

## Integration and Git Workflow

1. Work on branch `feat/ui-evaluation`:
   ```bash
   git checkout -b feat/ui-evaluation
   ```
2. Your branch merges **LAST** (after A, B, and C):
   ```
   A (ingestion) → B (retrieval/web) → C (generation) → D (UI/integration)
   ```
3. Run tests frequently:
   ```bash
   pytest -q
   ```
4. Commit:
   ```bash
   git add src/course_qa/app.py tests/test_integration.py data/evaluation/questions.csv docs/EVALUATION.md
   git commit -m "feat(ui): resilient Gradio app, integration suite, evaluation questions"
   ```
