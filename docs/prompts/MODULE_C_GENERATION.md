# Module C — Answer Generation, Routing, and Citations

## You are Contributor C

You are implementing the answer generation, routing, and citation validation modules for the **Syllabus-Aware DS/AoA NLP Assistant**, a four-person NLP mini-project.

**Begin implementing immediately.** Do not return another plan. Read the files listed below, then write working code.

---

## ✅ Module A status — COMPLETE

Module A (ingestion) is done and merged on branch `feat/ingestion-ocr`. Before you start, pull the latest `main`:

```bash
git checkout main && git pull origin main
```

**What A produced:**

| Item | Detail |
|---|---|
| `data/processed/chunks.jsonl` | **575 chunks** — 195 typed PDF, 362 code, 18 syllabus |
| `.env.example` | All env vars documented, copy to `.env` |
| `.venv/` | Virtual environment already created at repo root |

### ⏳ Module B status — IN PROGRESS

Module B (retrieval) is implementing on branch `feat/qdrant-hybrid-web`. For standalone testing, use the mock dependencies described in Task 6 — **do not block on B**.

When B merges, `HybridRetriever` and `WebSearch` will be available via the `NotesRetriever` / `WebSearcher` protocols. Your `QAService` already accepts them via protocol interfaces, so no changes will be needed on your end.

---

## Project context

This is a RAG system that answers DS/AoA exam questions using course notes (typed PDFs, handwritten PDFs, C code) with hybrid retrieval (Qdrant + BM25 + RRF) and evidence-grounded generation. Your module takes retrieved evidence from Contributor B's retriever, formats it with citation labels, calls a generator (real LLM or mock), validates citations, and returns a complete `AnswerResponse`.

## Repository root

```
/Users/ashmanraut/Ashman/Fr. CRCE/NLP/syllabus-rag-assistant
```

## Files to inspect first

Read these files before making any changes:

1. `src/course_qa/schemas.py` — all Pydantic models (DO NOT CHANGE)
2. `src/course_qa/contracts.py` — Protocol interfaces (DO NOT CHANGE)
3. `src/course_qa/config.py` — Settings dataclass
4. `src/course_qa/generation/generator.py` — OpenAICompatibleGenerator
5. `src/course_qa/generation/citations.py` — Evidence labeling + citation validation
6. `src/course_qa/generation/__init__.py`
7. `src/course_qa/service.py` — QAService + web routing logic
8. `tests/test_citations.py` — existing citation tests
9. `tests/test_routing.py` — existing routing tests
10. `docs/SHARED_CONTRACT.md` — full contract specification

## Your files (you own these exclusively)

- `src/course_qa/generation/generator.py`
- `src/course_qa/generation/citations.py`
- `src/course_qa/generation/__init__.py`
- `src/course_qa/service.py`
- `tests/test_citations.py` (and any new generation/service tests you create)
- `tests/test_routing.py`

**DO NOT modify** files owned by other contributors:
- `src/course_qa/ingestion/*` (Contributor A — COMPLETE, do not touch)
- `src/course_qa/retrieval/*` (Contributor B)
- `src/course_qa/web/*` (Contributor B)
- `src/course_qa/app.py` (Contributor D)
- `src/course_qa/schemas.py` (Contributor A — tech lead)
- `src/course_qa/contracts.py` (Contributor A — tech lead)
- `src/course_qa/config.py` (Contributor A — tech lead)

## Shared schemas (FROZEN — do not change)

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
    label: str                          # e.g. "S1"
    source_kind: Literal["note", "code", "syllabus", "web"]
    source_file: str | None = None
    page_number: int | None = None
    function_name: str | None = None
    url: str | None = None
    title: str | None = None
    image_path: str | None = None
    source_id: str

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

## Required interfaces

```python
class AnswerGenerator(Protocol):
    def generate(self, request: AnswerRequest, notes: Sequence[RetrievedChunk],
                 web: Sequence[WebSource]) -> AnswerResponse: ...

class QAService:
    def __init__(self, notes_retriever, generator, web_searcher): ...
    def answer(self, request: AnswerRequest) -> AnswerResponse: ...
```

## Implementation tasks (in priority order)

### Task 1: Environment setup and run tests

```bash
# From repo root
source .venv/bin/activate    # venv already created by A
# Copy env file if you haven't yet
cp .env.example .env
# Edit .env: set LLM_BASE_URL, LLM_API_KEY, LLM_MODEL (or leave blank for MockGenerator)

pytest tests/test_citations.py tests/test_routing.py -v
```

These should pass. Inspect the results.

### Task 2: Create a MockGenerator for testing

The `OpenAICompatibleGenerator` requires `LLM_MODEL` to be set and valid API credentials. For testing and demos without credentials, create a mock generator:

```python
# In src/course_qa/generation/generator.py (add alongside OpenAICompatibleGenerator)

class MockGenerator:
    """Deterministic generator for testing without LLM API credentials."""
    
    def generate(self, request: AnswerRequest, notes: Sequence[RetrievedChunk],
                 web: Sequence[WebSource]) -> AnswerResponse:
        context, records = build_labelled_evidence(list(notes), list(web))
        if not context:
            return AnswerResponse(
                answer="No evidence available to answer this question.",
                citations=[], notes_used=0, web_used=0, abstained=True,
                warnings=["No evidence retrieved; mock generator abstained."],
            )
        # Build a simple answer that cites all sources
        cited_labels = [f"[{r.label}]" for r in records]
        answer_parts = [f"Based on the available evidence {', '.join(cited_labels)}:"]
        answer_parts.append(f"\n\n**Question:** {request.question}")
        for r in records:
            answer_parts.append(f"\n\nFrom {r.label} ({r.source_kind}): Evidence available from {r.title or r.source_file or r.url or 'source'}.")
        raw_answer = "\n".join(answer_parts)
        answer, used_records, warnings = retain_only_cited_sources(raw_answer, records)
        cited_note_ids = {r.source_id for r in used_records if r.source_kind != "web"}
        cited_web_ids = {r.source_id for r in used_records if r.source_kind == "web"}
        return AnswerResponse(
            answer=answer, citations=used_records,
            notes_used=len(cited_note_ids), web_used=len(cited_web_ids),
            abstained=False, warnings=warnings + ["[Mock generator] Real LLM not configured."],
        )
```

### Task 3: Update `__init__.py` to expose `create_generator()`

In `src/course_qa/generation/__init__.py`, expose a factory that Contributor D will call in `app.py`:

```python
# In src/course_qa/generation/__init__.py
from .generator import OpenAICompatibleGenerator, MockGenerator
from ..config import settings

def create_generator():
    """Factory that returns a real or mock generator based on configuration."""
    if settings.llm_model:
        try:
            return OpenAICompatibleGenerator()
        except Exception as exc:
            import warnings
            warnings.warn(f"LLM init failed ({exc}); falling back to MockGenerator")
            return MockGenerator()
    return MockGenerator()
```

Contributor D will use `from course_qa.generation import create_generator`.

### Task 4: Verify citation pipeline

The citation pipeline has two stages:
1. `build_labelled_evidence()` — assigns `[S1]`, `[S2]`, etc. labels to evidence
2. `retain_only_cited_sources()` — strips invalid labels from the answer, keeps only cited records

Test the full pipeline manually with **real chunk data**:
```python
from course_qa.retrieval.hybrid import load_chunks
from course_qa.schemas import RetrievedChunk
from course_qa.generation.citations import build_labelled_evidence, retain_only_cited_sources

# Load a real typed PDF chunk
chunks = load_chunks()
typed = [c for c in chunks if c.source_type == "typed_pdf"][0]
hit = RetrievedChunk(chunk=typed, score=0.8, channel="hybrid", rank=1)
context, records = build_labelled_evidence([hit], [])
print(context)   # Should show [S1] with chunk text
print(records)   # Should have one CitationRecord with label="S1"

# Simulate model output
answer = f"Dijkstra's algorithm finds shortest paths [S1]. It is very fast [S99]."
cleaned, used, warnings = retain_only_cited_sources(answer, records)
print(cleaned)   # [S99] removed
print(used)      # Only S1
print(warnings)  # Warning about S99
```

### Task 5: Verify web routing logic

The routing in `service.py` uses `should_search_web()`. Review and verify:

1. `use_web=False` → always returns False (strict notes-only)
2. `web_search_mode="off"` → always returns False
3. `use_web=True` + no notes → returns True (web fallback)
4. `use_web=True` + signal words ("real-world application", "compare") → returns True
5. `use_web=True` + good notes → returns False (notes sufficient)

The existing `tests/test_routing.py` covers cases 1, 3, and 4. Add a test for case 5:

```python
def test_web_not_used_when_notes_are_strong():
    from course_qa.schemas import SourceChunk, RetrievedChunk
    chunk = SourceChunk(chunk_id="c1", source_id="s1", subject="AOA",
        source_type="typed_pdf", source_file="test.pdf", text="test",
        content_hash="h", source_hash="s")
    strong_notes = [RetrievedChunk(chunk=chunk, score=0.5, channel="hybrid", rank=1)]
    assert should_search_web(
        AnswerRequest(question="Explain Dijkstra", use_web=True), strong_notes
    ) is False
```

### Task 6: Add service-level tests

Create `tests/test_service.py`:

```python
"""Test QAService end-to-end with mock dependencies."""
from course_qa.schemas import *
from course_qa.service import QAService

class FakeRetriever:
    def __init__(self, results): self._results = results
    def retrieve(self, question, *, subject=None, top_k=5): return self._results

class FakeWebSearcher:
    def __init__(self, results=None): self._results = results or []
    def search(self, query, *, max_results=5): return self._results

class FakeGenerator:
    def generate(self, request, notes, web):
        if not notes and not web:
            return AnswerResponse(answer="No evidence.", citations=[], notes_used=0, web_used=0, abstained=True)
        citations = [CitationRecord(label="S1", source_kind="note", source_file="test.pdf", source_id="c1")]
        return AnswerResponse(answer="Answer [S1].", citations=citations, notes_used=1, web_used=0)

def test_service_returns_answer_with_citations():
    chunk = SourceChunk(chunk_id="c1", source_id="s1", subject="AOA",
        source_type="typed_pdf", source_file="test.pdf", text="Dijkstra...",
        content_hash="h", source_hash="s")
    notes = [RetrievedChunk(chunk=chunk, score=0.5, channel="hybrid", rank=1)]
    service = QAService(FakeRetriever(notes), FakeGenerator(), FakeWebSearcher())
    response = service.answer(AnswerRequest(question="Explain Dijkstra"))
    assert response.answer
    assert not response.abstained

def test_service_abstains_when_no_evidence():
    service = QAService(FakeRetriever([]), FakeGenerator(), FakeWebSearcher())
    response = service.answer(AnswerRequest(question="Something unknown"))
    assert response.abstained
    assert any("no note or web evidence" in w.lower() for w in response.warnings)

def test_service_does_not_call_web_when_disabled():
    class TrackingWebSearcher:
        def __init__(self): self.called = False
        def search(self, query, *, max_results=5): self.called = True; return []
    web = TrackingWebSearcher()
    service = QAService(FakeRetriever([]), FakeGenerator(), web)
    service.answer(AnswerRequest(question="test", use_web=False))
    assert not web.called
```

### Task 7: Verify system prompt and answer styles

Review the `SYSTEM_PROMPT` in `generator.py`. It instructs the model to:
- Use supplied evidence labels `[S1]`, `[S2]`
- Never invent source labels
- Follow exam answer format when requested
- Not append a Sources section

This is correct. No changes needed unless you find a specific issue.

For the `concise` vs `exam` style, the generator passes `Style: {style}` in the user prompt. Verify this distinction works with the mock generator.

### Task 8: Handle edge cases

Verify these edge cases work:
1. **No evidence at all** → abstain with warning
2. **Evidence but model cites nothing** → warning "no valid evidence cited"
3. **Model cites invalid labels** → stripped, warning generated
4. **Web search fails** → warning appended, notes-only answer returned
5. **All notes are OCR-pending** → effectively no useful text evidence, abstain

Note: Real chunks with `ocr_status="pending"` have `text=""` (empty). Make sure your citation builder handles empty-text chunks gracefully — they should not appear as `[S1]` evidence in the prompt.

## Dependencies

- **From Contributor A**: ✅ `data/processed/chunks.jsonl` ready. Use `load_chunks()` from `hybrid.py` to load real data during manual testing.
- **From Contributor B**: `HybridRetriever` (via `NotesRetriever` protocol) and `WebSearch` (via `WebSearcher` protocol). **Not yet merged — use fake/mock implementations for now.**
- **External (optional)**: OpenAI-compatible LLM API. Without credentials, `MockGenerator` is used automatically.

## Tests to run

```bash
pytest tests/test_citations.py -v
pytest tests/test_routing.py -v
pytest tests/test_service.py -v      # after you create it
```

## Acceptance criteria

- [ ] All existing tests pass: `pytest tests/test_citations.py tests/test_routing.py -v`
- [ ] `MockGenerator` exists and produces valid `AnswerResponse` with citations
- [ ] `create_generator()` factory falls back to mock when `LLM_MODEL` is unset
- [ ] Invalid citation labels (`[S99]`) are stripped from answers
- [ ] Answers with no valid citations produce warnings
- [ ] `should_search_web()` respects the `use_web` toggle as a permission gate
- [ ] `QAService.answer()` works end-to-end with mock dependencies
- [ ] Web search failures produce warnings, not crashes
- [ ] Abstention occurs when no evidence is available
- [ ] New `tests/test_service.py` passes
- [ ] `create_generator()` is importable from `course_qa.generation`

## Integration instructions

1. Work on branch `feat/generation-citations`
2. Your branch merges **THIRD** (after A and B)
3. Expose `create_generator()` from `src/course_qa/generation/__init__.py` for Contributor D
4. Contributor D will wire `QAService(retriever, generator, web_searcher)` in `app.py`
5. The `QAService.answer()` method is the single entry point the UI calls

## Important constraints

- Do NOT use Claude/Gemini (your orchestrator) as the application's LLM — they are separate
- Do NOT let the model generate the Sources section — citations are validated by your code
- Do NOT assume API credentials exist — always support `MockGenerator` fallback
- Do NOT modify retrieval or web search modules — use them via their Protocol interfaces
- Citation labels `[S1]`, `[S2]` are request-local, not global identifiers

## Git commands

```bash
git checkout main && git pull origin main
git checkout -b feat/generation-citations
# ... implement changes ...
pytest -q
git add -A
git commit -m "feat(generation): add mock generator, service tests, citation hardening"
git push origin feat/generation-citations
```
