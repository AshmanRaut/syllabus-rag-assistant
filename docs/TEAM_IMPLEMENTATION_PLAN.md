# Team Implementation Plan — Syllabus-Aware DS/AoA NLP Assistant

> Generated after full repository and source-material audit on 2026-10-23.

---

## Deliverable 1 — Repository & Source-Material Audit

### Repository root

```
/Users/ashmanraut/Ashman/Fr. CRCE/NLP/syllabus-rag-assistant
```

Git: single commit `1e84138` on `main`. Remote `origin/main` set.

### Discovered course-material paths

Source materials live inside `notes/` within the repository. The `.gitignore` excludes `/notes/` from Git (correct).

| Actual directory on disk | Expected by `FolderScanner.FOLDER_MAP` | Match? |
|---|---|---|
| `notes/aoa_codes/` (11 .c files) | `AOA codes/` | ❌ **Mismatch** — underscored + lowercase vs spaced + mixed case |
| `notes/aoa_notes/Typed/` (18 PDFs) | `AOA notes/Typed/` | ❌ **Mismatch** — `aoa_notes` vs `AOA notes` |
| `notes/aoa_notes/Handwritten/` (10 PDFs) | `AOA notes/Handwritten/` | ❌ **Mismatch** |
| `notes/ds_codes/` (30 .c files) | `DS codes/` | ❌ **Mismatch** |
| `notes/ds_notes/Handwritten/` (12 PDFs) | `DS notes/Handwritten/` | ❌ **Mismatch** |
| `notes/ds_notes/` — **no `Typed/` subfolder** | `DS notes/Typed/` | ❌ **Missing entirely** — DS has only handwritten notes |
| `notes/syllabus/` (2 PDFs) | `syllabi/` | ❌ **Mismatch** — `syllabus` vs `syllabi` |
| `notes/aoa_notes/*.pdf` (3 files at root level) | Not mapped | ⚠️ Unmapped — `End_Semester_Exam.pdf`, `Mid_Semester_Exam.pdf`, `Practice_Questions.pdf` |

**CRITICAL: The scanner will find ZERO files with the current `FOLDER_MAP`.** `SOURCE_ROOT` must point to `notes/` and the `FOLDER_MAP` must be updated to use the actual directory names.

### Source types and file counts

| Category | Directory | Count | File types | Total size (approx) |
|---|---|---:|---|---|
| AOA C code | `notes/aoa_codes/` | 11 | `.c` | ~26 KB |
| AOA typed PDFs | `notes/aoa_notes/Typed/` | 18 | `.pdf` | ~3.5 MB |
| AOA handwritten PDFs | `notes/aoa_notes/Handwritten/` | 10 | `.pdf` | ~50 MB |
| AOA root-level PDFs | `notes/aoa_notes/` | 3 | `.pdf` | ~1.5 MB |
| DS C code | `notes/ds_codes/` | 30 | `.c` | ~113 KB |
| DS handwritten PDFs | `notes/ds_notes/Handwritten/` | 12 | `.pdf` | ~67 MB |
| DS typed PDFs | (none) | 0 | — | — |
| Syllabi | `notes/syllabus/` | 2 | `.pdf` | ~840 KB |
| **Total** | | **86** | | ~136 MB |

> DS has **no typed notes** — all DS notes are handwritten. This makes OCR critical for DS coverage, or the system must rely on DS code + web fallback for DS content.

### Existing implementation status

| Module | Files | Status |
|---|---|---|
| **Schemas** | `schemas.py` | ✅ Complete. Well-defined Pydantic models. |
| **Contracts** | `contracts.py` | ✅ Complete. Protocol classes match `SHARED_CONTRACT.md`. |
| **Config** | `config.py` | ✅ Complete. All env vars defined. |
| **Scanner** | `ingestion/scanner.py` | ⚠️ **Logic works but FOLDER_MAP keys are wrong** for actual directory names. |
| **Splitters** | `ingestion/splitters.py` | ✅ Complete. Paragraph-aware splitting with stable UUIDs. |
| **Code parser** | `ingestion/code_parser.py` | ✅ Complete. Function-level C extraction works. |
| **PDF parser** | `ingestion/pdf_parser.py` | ✅ Complete. Page-wise extraction with OCR integration, budget, manifest. |
| **OCR** | `ingestion/ocr.py` | ✅ Complete scaffold. `CachedOCR` with atomic writes, `PaddleOCRVLProvider` adapter. Untested on actual hardware. |
| **Runner** | `ingestion/runner.py` | ✅ Complete. Orchestrates scan → parse → chunk → save. |
| **Embedder** | `retrieval/embedder.py` | ✅ Complete. `SentenceTransformerEmbedder` wrapper. |
| **Qdrant store** | `retrieval/qdrant_store.py` | ✅ Complete. Upsert + search with subject filtering. |
| **Hybrid retriever** | `retrieval/hybrid.py` | ✅ Complete. BM25 + Qdrant dense + RRF fusion. |
| **Web search** | `web/search.py` | ✅ Complete. Tavily + DDGS + allowlist + Trafilatura. `ddgs` import uses `from ddgs import DDGS` — verify package name. |
| **Citations** | `generation/citations.py` | ✅ Complete. Label builder + invalid-citation stripper. |
| **Generator** | `generation/generator.py` | ✅ Complete. `OpenAICompatibleGenerator` with system prompt. |
| **Service** | `service.py` | ✅ Complete. `QAService` with web routing logic. |
| **App (UI)** | `app.py` | ✅ Complete scaffold. Gradio Blocks layout with all required controls. |
| **Scripts** | `scan_sources.py`, `ingest.py`, `index.py` | ✅ Complete. CLI wiring for all pipeline stages. |
| **Tests** | 5 test files | ✅ Good coverage of contracts, hybrid retrieval, OCR cache, citations, routing. |

### Critical issues to fix

1. **`FOLDER_MAP` mismatch** — Scanner won't discover any files. Must update keys to `aoa_codes`, `aoa_notes/Typed`, `aoa_notes/Handwritten`, `ds_codes`, `ds_notes/Handwritten`, `syllabus`.
2. **`SOURCE_ROOT` default** — Currently `./materials`. Should be `./notes` or set via `.env`.
3. **Unmapped AOA PDFs** — 3 PDFs sit directly in `aoa_notes/` (exam/practice papers). Need a mapping rule.
4. **Missing DS typed notes** — DS has zero typed notes. The system must handle this gracefully.
5. **No `.env.example`** — Referenced in README but does not exist in the repo.
6. **`ddgs` import** — `web/search.py` uses `from ddgs import DDGS`. The pip package is `ddgs` (version ≥9). Verify this is correct (older versions used `duckduckgo_search`).
7. **No `conftest.py`** — Tests don't have a shared conftest for fixtures.
8. **`data/evaluation/`** — Empty. `questions.csv` needs to be created.
9. **Mock generator** — No mock/fake generator exists for testing without LLM credentials.

### Dependency risks

- `sentence-transformers` model download (~80MB) happens on first use.
- Qdrant Docker must be running for non-local-path mode.
- No LLM API credentials verified yet — `OpenAICompatibleGenerator` will fail at init.
- PaddleOCR-VL is optional but DS coverage depends on it.

---

## Deliverable 2 — Final Architecture & Shared Contract

### Architecture diagram

```
notes/                          ← SOURCE_ROOT (set via .env)
  ├── aoa_codes/*.c             → code_parser → function chunks
  ├── aoa_notes/Typed/*.pdf     → pdf_parser (pypdf) → page chunks
  ├── aoa_notes/Handwritten/*.pdf → pdf_parser → OCR adapter → cached page chunks
  ├── aoa_notes/*.pdf           → pdf_parser (typed) → page chunks
  ├── ds_codes/*.c              → code_parser → function chunks
  ├── ds_notes/Handwritten/*.pdf → pdf_parser → OCR adapter → cached page chunks
  └── syllabus/*.pdf            → pdf_parser (typed) → syllabus chunks
                    │
                    ▼
        SourceChunk → chunks.jsonl (canonical corpus)
                    │
          ┌─────────┴──────────┐
          ▼                    ▼
    SentenceTransformer    BM25Index (in-process)
    → Qdrant upsert            │
          │                    │
          └────────┬───────────┘
                   ▼
            RRF HybridRetriever.retrieve()
                   │
                   ▼
          QAService.answer()
          ├── should_search_web() → WebSearch (Tavily/DDGS)
          ├── AnswerGenerator.generate()
          │   ├── build_labelled_evidence() → [S1], [S2]...
          │   ├── LLM call (OpenAI-compatible)
          │   └── retain_only_cited_sources()
          └── AnswerResponse
                   │
                   ▼
            Gradio UI (app.py)
            ├── Answer panel
            ├── Sources table (note/code/web)
            ├── Page image gallery
            └── Warnings
```

### Shared contract (preserved from existing code)

The existing schemas in `schemas.py` and protocols in `contracts.py` are **complete and correct**. No changes to field names or types are needed.

**One required fix:** The `FOLDER_MAP` in `scanner.py` must be updated to match actual directory names. This is a configuration change, not a contract change.

### Module boundaries and data flow

| Interface | Input | Output | Owner |
|---|---|---|---|
| `FolderScanner.scan(root)` | `Path` | `list[DiscoveredFile]` | A |
| `DocumentIngestor.ingest(file)` | `DiscoveredFile` | `list[SourceChunk]` | A |
| `ingest_all()` | settings | `(list[SourceChunk], IngestReport)` | A |
| `Embedder.embed_documents(texts)` | `Sequence[str]` | `list[list[float]]` | B |
| `QdrantDenseStore.upsert(chunks, vectors)` | chunks + vectors | count | B |
| `NotesRetriever.retrieve(question, subject, top_k)` | str, filters | `list[RetrievedChunk]` | B |
| `WebSearcher.search(query, max_results)` | str | `list[WebSource]` | B |
| `AnswerGenerator.generate(request, notes, web)` | request + evidence | `AnswerResponse` | C |
| `QAService.answer(request)` | `AnswerRequest` | `AnswerResponse` | C |
| `app.py main()` | — | Gradio server | D |

---

## Deliverable 3 — Four-Person Task Allocation

| Contributor | Responsibilities | Files Owned | Dependencies | Acceptance Criteria | Deliverables |
|---|---|---|---|---|---|
| **A — Ingestion** | Fix scanner, extract typed PDFs, OCR adapter, C function splitting, emit chunks.jsonl | `src/course_qa/ingestion/*`, `scripts/scan_sources.py`, `scripts/ingest.py`, `.env.example` | None (runs first) | Scanner finds all 86 files; `chunks.jsonl` has valid SourceChunks; repeated runs skip cached pages; OCR failures reported | Working scanner + ingestion pipeline + `.env.example` |
| **B — Retrieval & Web** | Qdrant indexing, BM25, RRF fusion, web search adapters | `src/course_qa/retrieval/*`, `src/course_qa/web/*`, `scripts/index.py` | A produces `chunks.jsonl` | Dense + BM25 + hybrid retrieval works; subject filter works; web disabled = no web calls; web failure doesn't crash | Working retrieval + web search |
| **C — Generation** | LLM adapter, mock generator, citation validation, service routing | `src/course_qa/generation/*`, `src/course_qa/service.py` | B provides retriever, A provides chunks | Citations validated; invalid labels stripped; abstention on no evidence; mock generator passes tests | Working generator + citation pipeline |
| **D — UI & Integration** | Gradio UI, integration tests, evaluation, demo | `src/course_qa/app.py`, `tests/*` (integration), `docs/EVALUATION.md`, `data/evaluation/` | A, B, C provide modules | App starts; end-to-end Q&A works; sources displayed; web toggle works; demo runs | Working UI + test suite + demo |

### Shared files (changed only by A as tech lead)

- `src/course_qa/schemas.py`
- `src/course_qa/contracts.py`
- `src/course_qa/config.py`

---

## Deliverable 4 — Execution Schedule (8 hours)

| Time | Milestone | Who | Depends On | Fallback |
|---|---|---|---|---|
| **0:00–0:30** | Environment setup, `.env.example`, fix `FOLDER_MAP`, freeze contract | All | — | If scanner broken, fix is A's first task |
| **0:30–1:00** | Scanner produces correct counts; Qdrant Docker started | A, B | — | B uses local Qdrant path if Docker fails |
| **1:00–2:00** | Typed PDF + code ingestion → `chunks.jsonl`; OCR 5-page pilot started | A | — | Skip OCR; use typed + code only |
| **1:00–2:00** | (parallel) Embedder + Qdrant upsert tested with sample chunks; web adapter tested | B | Sample chunks from A or fixture | B creates own test chunks |
| **1:00–2:00** | (parallel) Mock generator + citation validator tested standalone | C | — | Uses fixture evidence |
| **1:00–2:00** | (parallel) Gradio shell with fake service started | D | — | Stub returns hardcoded response |
| **2:00–3:00** | Full indexing: all typed PDFs + code in Qdrant; BM25 built | A→B | `chunks.jsonl` ready | Index whatever is available |
| **3:00–4:00** | **Vertical slice:** question → retrieve → generate → answer with citation | B+C | Indexed chunks | Use mock generator if no LLM key |
| **4:00–5:00** | **Integration checkpoint:** UI wired to real service; first live demo | D | B+C services | Stub missing modules |
| **5:00–6:00** | Web fallback integrated; OCR pages added if available; citation hardening | All | Core working | Web is optional enhancement |
| **6:00–7:00** | Evaluation: run 12–15 test questions; fill EVALUATION.md | D+C | Working system | Report whatever works |
| **7:00–8:00** | Demo prep, report outline, final commit, cleanup | All | — | Demo what works; document gaps |

### Critical path

```
Fix scanner → Ingest typed+code → Index in Qdrant → Hybrid retrieve → Generate answer → UI display
    A              A                    B                  B               C              D
```

Anything off this path (OCR, web search, evaluation) is parallel enhancement work.

---

## Deliverable 6 — Integration Checklist

### Pre-flight

- [ ] All contributors have cloned the repo and are on `main` at `1e84138`
- [ ] Python 3.11+ venv created and `pip install -e . -r requirements.txt` succeeds
- [ ] `.env.example` created by A; each contributor copies to `.env`
- [ ] `SOURCE_ROOT` set to `./notes` in `.env`
- [ ] Docker running: `docker compose up -d qdrant` (or `QDRANT_URL` left blank for local path)

### Shared contract freeze

- [ ] `FOLDER_MAP` in `scanner.py` updated to match actual directory names
- [ ] `python scripts/scan_sources.py` discovers 86 files with correct subjects
- [ ] `schemas.py` and `contracts.py` unchanged (or changes approved by A)
- [ ] All contributors confirm they are reading from the same schema version

### Branch setup

```bash
# Each contributor creates their branch from main
git checkout -b feat/ingestion-ocr          # Person A
git checkout -b feat/qdrant-hybrid-web      # Person B
git checkout -b feat/generation-citations   # Person C
git checkout -b feat/ui-evaluation          # Person D
```

### First vertical slice (hour 3–4)

- [ ] `chunks.jsonl` exists with ≥50 chunks from typed PDFs + code
- [ ] `scripts/index.py` completes: chunks in Qdrant
- [ ] `HybridRetriever.retrieve("Dijkstra")` returns relevant chunks
- [ ] `AnswerGenerator.generate()` returns answer with `[S1]` citations (mock or real LLM)
- [ ] Citations validated: no invalid labels in response

### Module integration order

1. **A merges first** → scanner fix + ingestion (produces `chunks.jsonl`)
2. **B merges second** → retrieval + web (consumes `chunks.jsonl`)
3. **C merges third** → generation + service (consumes retriever + web)
4. **D merges last** → UI + tests (wires everything)

### Test commands

```bash
pytest tests/test_contract.py -v      # Schemas, splitters, code parser, scanner
pytest tests/test_hybrid.py -v        # RRF fusion logic
pytest tests/test_ocr_cache.py -v     # OCR caching behavior
pytest tests/test_citations.py -v     # Citation validation
pytest tests/test_routing.py -v       # Web routing logic
pytest -q                             # All tests
```

### Final demo checklist

- [ ] App starts: `python -m course_qa.app`
- [ ] AOA typed-note question works with note citations
- [ ] DS code question works with function citation
- [ ] Web-disabled question returns notes-only answer
- [ ] Web-enabled question shows web citations separately
- [ ] Out-of-corpus question triggers abstention/warning
- [ ] Subject filter restricts results correctly
- [ ] Sources table shows correct metadata
- [ ] Page images display for PDF-sourced citations
- [ ] All warnings displayed when appropriate
