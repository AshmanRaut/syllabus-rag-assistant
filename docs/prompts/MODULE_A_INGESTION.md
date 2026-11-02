# Module A — Ingestion, OCR, and Metadata

## You are Contributor A — the Technical Lead

You are implementing the ingestion pipeline for the **Syllabus-Aware DS/AoA NLP Assistant**, a four-person NLP mini-project. You are also the technical lead responsible for shared schemas and the integration contract.

**Begin implementing immediately.** Do not return another plan. Read the files listed below, then write working code.

---

## Project context

This is a RAG system that answers DS/AoA exam questions using course notes (typed PDFs, handwritten PDFs, C code) with hybrid retrieval (Qdrant + BM25 + RRF) and evidence-grounded generation. Your module ingests the raw course materials and produces the canonical `chunks.jsonl` that all downstream modules consume.

## Repository root

```
/Users/ashmanraut/Ashman/Fr. CRCE/NLP/syllabus-rag-assistant
```

## Course material location

```
SOURCE_ROOT = ./notes
```

The notes directory has these **actual** subdirectories (names are lowercase with underscores):

```
notes/
├── aoa_codes/          (11 .c files — AOA lab code)
├── aoa_notes/
│   ├── Typed/          (18 typed PDFs — AOA theory)
│   ├── Handwritten/    (10 handwritten PDFs — AOA, ~50MB)
│   ├── End_Semester_Exam.pdf
│   ├── Mid_Semester_Exam.pdf
│   └── Practice_Questions.pdf
├── ds_codes/           (30 .c files — DS lab code)
├── ds_notes/
│   └── Handwritten/    (12 handwritten PDFs — DS, ~67MB)
│   (NO Typed/ subfolder — DS has zero typed notes)
└── syllabus/
    ├── AOA_Syllabus.pdf
    └── DS_Syllabus.pdf
```

## Files to inspect first

Read these files before making any changes:

1. `src/course_qa/schemas.py` — canonical Pydantic models (DO NOT CHANGE field names/types)
2. `src/course_qa/contracts.py` — Protocol interfaces
3. `src/course_qa/config.py` — Settings (environment variables)
4. `src/course_qa/ingestion/scanner.py` — **CRITICAL: FOLDER_MAP is wrong**, see below
5. `src/course_qa/ingestion/pdf_parser.py` — page-wise PDF extraction
6. `src/course_qa/ingestion/code_parser.py` — C function splitting
7. `src/course_qa/ingestion/ocr.py` — CachedOCR + PaddleOCR-VL adapter
8. `src/course_qa/ingestion/splitters.py` — text splitting + UUID generation
9. `src/course_qa/ingestion/runner.py` — orchestrator
10. `scripts/scan_sources.py`, `scripts/ingest.py`
11. `docs/SHARED_CONTRACT.md`
12. `tests/test_contract.py`, `tests/test_ocr_cache.py`

## Your files (you own these exclusively)

- `src/course_qa/ingestion/scanner.py`
- `src/course_qa/ingestion/pdf_parser.py`
- `src/course_qa/ingestion/code_parser.py`
- `src/course_qa/ingestion/ocr.py`
- `src/course_qa/ingestion/splitters.py`
- `src/course_qa/ingestion/runner.py`
- `src/course_qa/ingestion/__init__.py`
- `scripts/scan_sources.py`
- `scripts/ingest.py`

As tech lead, you also own (minimal changes only):
- `src/course_qa/config.py` — update `SOURCE_ROOT` default
- `.env.example` — create this file

**DO NOT modify** files owned by other contributors:
- `src/course_qa/retrieval/*` (Contributor B)
- `src/course_qa/web/*` (Contributor B)
- `src/course_qa/generation/*` (Contributor C)
- `src/course_qa/service.py` (Contributor C)
- `src/course_qa/app.py` (Contributor D)

## Shared schemas (FROZEN — do not change)

```python
# From src/course_qa/schemas.py — these are authoritative
Subject = Literal["DS", "AOA", "UNKNOWN"]
SourceType = Literal["typed_pdf", "handwritten_pdf", "image", "code", "syllabus", "web", "text"]

class SourceChunk(BaseModel):
    chunk_id: str                    # stable UUID
    source_id: str                   # hash-derived document ID
    subject: Subject
    source_type: SourceType
    source_file: str                 # relative to SOURCE_ROOT
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

class DiscoveredFile(BaseModel):
    absolute_path: str
    relative_path: str
    subject: Subject
    source_type: SourceType
    bucket: Literal["typed", "handwritten", "code", "syllabus", "other"]
```

## Implementation tasks (in priority order)

### Task 1: Fix `FOLDER_MAP` in `scanner.py` (CRITICAL — do this first)

The current `FOLDER_MAP` expects directory names like `"AOA codes"` and `"AOA notes/Typed"`, but the actual directories use `aoa_codes` and `aoa_notes/Typed`. Update the keys:

```python
FOLDER_MAP = {
    "aoa_codes": ("AOA", "code", "code"),
    "aoa_notes/Typed": ("AOA", "typed_pdf", "typed"),
    "aoa_notes/Handwritten": ("AOA", "handwritten_pdf", "handwritten"),
    "ds_codes": ("DS", "code", "code"),
    "ds_notes/Handwritten": ("DS", "handwritten_pdf", "handwritten"),
    "syllabus": ("UNKNOWN", "syllabus", "syllabus"),
}
```

Also handle the 3 root-level PDFs in `aoa_notes/` (exam/practice papers). Add them as typed PDFs for AOA, or add a mapping entry for `"aoa_notes"` that only picks up direct children (not recursing into `Typed/` and `Handwritten/` which are already mapped).

Update the root-level syllabus scanner to also check for `*Syllabus*.pdf` in the `syllabus/` subfolder since that's where they actually are.

### Task 2: Update `SOURCE_ROOT` default and create `.env.example`

In `config.py`, change the default `SOURCE_ROOT` from `"./materials"` to `"./notes"`.

Create `.env.example` at the repository root:

```env
# Copy to .env and fill in. Never commit .env itself.
SOURCE_ROOT=./notes
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=course_chunks
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
LLM_TEMPERATURE=0.1
WEB_SEARCH_MODE=auto
TAVILY_API_KEY=
OCR_PROVIDER=disabled
OCR_MAX_PAGES=5
```

### Task 3: Verify scanner works

After fixing `FOLDER_MAP`, run `python scripts/scan_sources.py` and confirm it discovers all ~86 files with correct subjects and source types. Report actual counts.

### Task 4: Test and fix typed PDF extraction

Run ingestion on a few typed AOA PDFs (e.g., `Fractional_Knapsack.pdf`, `Dijkstra_Algorithm.pdf`). Verify that pypdf extracts usable text. The existing `pdf_parser.py` already handles page-wise extraction with image rendering — verify it works on real files.

If any typed PDF produces garbled text (tables, equations broken), note it but do not block on Docling integration. A Docling fallback is optional for day one.

### Task 5: Test and fix C code function splitting

Verify that `code_parser.py` correctly splits the actual C files. Test with:
- `notes/aoa_codes/Dijkstra.c`
- `notes/ds_codes/BinarySearchTree.c`

Confirm function names are extracted and each function becomes a separate chunk.

### Task 6: Run full ingestion

Execute `python scripts/ingest.py --resume --max-ocr-pages 0` (0 = skip OCR for now, rely on typed + code).

Verify `data/processed/chunks.jsonl` is created with valid `SourceChunk` JSONL lines.

Report: how many chunks were produced, from how many files, and which files failed.

### Task 7: OCR pilot (if time permits)

Only attempt this after Tasks 1–6 are complete and `chunks.jsonl` exists.

1. Test PaddleOCR-VL installation in an isolated environment
2. Set `OCR_PROVIDER=paddleocr_vl` and `OCR_MAX_PAGES=5`
3. Run `python scripts/ingest.py --resume --max-ocr-pages 5`
4. Check quality of 5 handwritten pages
5. Report results honestly — do not claim OCR works if it doesn't

### Task 8: Handle the cross-module import

In `runner.py` line 71, there's `from ..retrieval.hybrid import save_chunks`. This creates a coupling to module B's code. The `save_chunks` function is a simple JSONL writer. Either:
- Keep it as-is (it's just a utility function), OR
- Move `save_chunks`/`load_chunks` to a shared utility if it causes import issues

## Runner dependency note

`runner.py` imports `from ..retrieval.hybrid import save_chunks`. This function is a simple JSONL writer in module B's code. If this import breaks during development, temporarily inline a `save_chunks` function in the runner. Coordinate with B when merging.

## Tests to run

```bash
pytest tests/test_contract.py -v     # Scanner, splitters, code parser
pytest tests/test_ocr_cache.py -v    # OCR caching
python scripts/scan_sources.py       # Verify file discovery
```

After ingestion:
```bash
python -c "from course_qa.retrieval.hybrid import load_chunks; cs = load_chunks(); print(f'{len(cs)} chunks')"
```

## Acceptance criteria

- [ ] `python scripts/scan_sources.py` discovers all 86 source files with correct subjects
- [ ] `python scripts/ingest.py --resume` produces `chunks.jsonl` with >50 chunks
- [ ] Typed PDFs produce readable text chunks
- [ ] C files split into individual function chunks with correct `function_name`
- [ ] Repeated runs with `--resume` skip already-processed files
- [ ] OCR-disabled pages have `ocr_status="pending"` (not silently dropped)
- [ ] Existing tests pass: `pytest tests/test_contract.py tests/test_ocr_cache.py -v`
- [ ] `.env.example` exists at repo root
- [ ] No absolute paths, API keys, or course content committed to Git

## Integration instructions

1. Work on branch `feat/ingestion-ocr`
2. Your branch merges to `main` FIRST (before B, C, D)
3. After merging, notify team that `chunks.jsonl` format is ready
4. If schema changes are needed (unlikely), update `schemas.py` and notify all contributors

## Error reporting

If something fails (OCR doesn't install, a PDF can't be parsed, function extraction misses functions), report the failure honestly in the `IngestReport.errors` list and in your commit message. Do not silently skip files or claim success.

## Git commands

```bash
git checkout -b feat/ingestion-ocr
# ... implement changes ...
pytest -q
git add -A
git commit -m "feat(ingestion): fix scanner FOLDER_MAP, verify typed PDF + code ingestion"
git push origin feat/ingestion-ocr
```
