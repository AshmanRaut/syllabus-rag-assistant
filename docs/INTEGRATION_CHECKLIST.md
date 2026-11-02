# Integration Checklist — One-Day Build

## Pre-flight (all contributors, 0:00–0:30)

- [x] Python 3.11+ venv: `python -m venv .venv && source .venv/bin/activate`
- [x] Core deps: `pip install -e . -r requirements.txt`
- [x] Web deps: `pip install -r requirements-web.txt`
- [x] `.env.example` created by A → each contributor copies to `.env` (`cp .env.example .env`)
- [x] `SOURCE_ROOT=./notes` set in `.env`
- [ ] Qdrant: `docker run -d --name qdrant -p 6333:6333 -v $(pwd)/qdrant_storage:/qdrant/storage:z qdrant/qdrant` (or leave `QDRANT_URL` blank for local path)
- [x] Verify: `pytest -q` — all baseline tests pass

---

## Contract freeze (A leads, all agree)

- [x] `FOLDER_MAP` in `scanner.py` updated to actual directory names (`aoa_codes`, `aoa_notes/Typed`, `aoa_notes/Handwritten`, `ds_codes`, `ds_notes/Handwritten`, `syllabus`)
- [x] Root-level AOA exam papers mapped (`aoa_notes/*.pdf`)
- [x] `python scripts/scan_sources.py` → discovers 86 files with correct subjects
- [x] `schemas.py` and `contracts.py` reviewed — frozen, no field changes needed
- [x] `.env.example` committed with all defaults documented
- [x] All contributors confirmed schema version

---

## Branch status

```bash
git checkout -b feat/ingestion-ocr          # A: COMPLETE (committed on feat/ingestion-ocr)
git checkout -b feat/qdrant-hybrid-web      # B: IN PROGRESS (next up)
git checkout -b feat/generation-citations   # C: IN PROGRESS
git checkout -b feat/ui-evaluation          # D: IN PROGRESS
```

---

## Parallel development (hours 1–3)

### Contributor A checkpoints — ✅ COMPLETE
- [x] Scanner finds all 86 files: typed PDFs (21), handwritten PDFs (22), C files (41), syllabi (2)
- [x] Typed PDF extraction works (verified with `Fractional_Knapsack.pdf`, `Dijkstra_Algorithm.pdf`, etc.)
- [x] C function splitting works (verified with `Dijkstra.c`, `BinarySearchTree.c`, 362 function chunks)
- [x] `python scripts/ingest.py --resume` produces `chunks.jsonl` (575 chunks written, 0 errors)
- [x] Manifest written: `data/processed/source_manifest.json` (153 pages processed, 281 pending OCR)
- [x] Page images rendered to `data/page_images/` for Gradio UI gallery
- [x] Commit: `4056274 feat(ingestion): fix scanner FOLDER_MAP, verify typed PDF + code ingestion`

### Contributor B checkpoints — ✅ COMPLETE
- [x] `SentenceTransformerEmbedder` loads model (`all-MiniLM-L6-v2`), dimension = 384
- [x] Real chunks available: `data/processed/chunks.jsonl` (575 chunks ready — skip mock chunk creation!)
- [x] Qdrant collection initialized & upsert completed via `python scripts/index.py` (575 points indexed)
- [x] Qdrant dense search returns relevant chunks
- [x] BM25 indexing and scoring works over canonical chunks
- [x] `HybridRetriever.retrieve()` returns RRF-fused results with rank & channel attribution
- [x] `WebSearch().search()` with `WEB_SEARCH_MODE=off` returns `[]`
- [x] `WebSearch().search()` with DDGS / Tavily works on query (integrated with allowlist filter)
- [x] `pytest tests/test_hybrid.py` passes (14 passed)

### Contributor C checkpoints — ✅ COMPLETE
- [x] `MockGenerator` implemented for test & offline runs
- [x] `create_generator()` factory selects `OpenAICompatibleGenerator` or `MockGenerator` based on `LLM_MODEL`
- [x] Evidence labeling builds `[S1]`, `[S2]` with source metadata
- [x] Citation validation (`retain_only_cited_sources`) strips invalid citations
- [x] `QAService` handles routing (notes-only, notes+web, abstain)
- [x] `pytest tests/test_citations.py tests/test_routing.py` passes

### Contributor D checkpoints — ✅ COMPLETE
- [x] Gradio UI starts cleanly with resilient fallbacks: `python -m course_qa.app`
- [x] `data/evaluation/questions.csv` created (15 benchmark questions)
- [x] Integration test suite created: `tests/test_integration.py` (33 passed)
- [x] PDF page image gallery verified with rendered images in `data/page_images/`
- [x] `pytest tests/test_integration.py` passes

---

## First vertical slice (hour 3–4)

All of these must work in sequence:

- [x] A: `chunks.jsonl` has ≥50 chunks (actual: **575 canonical chunks**)
- [x] B: `python scripts/index.py` — chunks indexed in Qdrant (575 points)
- [x] B: `HybridRetriever.retrieve("Dijkstra")` returns relevant chunks
- [x] C: `AnswerGenerator.generate()` returns answer with `[S1]` (mock or real)
- [x] C: `retain_only_cited_sources()` validates citations
- [x] D: `QAService.answer()` → complete `AnswerResponse`

---

## Integration merge (hour 4–5)

### Merge order (strictly sequential)

1. **A → main**: Scanner fix + ingestion (READY)
   ```bash
   git checkout main && git merge feat/ingestion-ocr
   pytest -q
   python scripts/scan_sources.py  # verify 86 files
   ```

2. **B → main**: Retrieval + web
   ```bash
   git checkout main && git merge feat/qdrant-hybrid-web
   pytest -q
   python scripts/index.py  # verify indexing
   ```

3. **C → main**: Generation + service
   ```bash
   git checkout main && git merge feat/generation-citations
   pytest -q
   ```

4. **D → main**: UI + integration tests
   ```bash
   git checkout main && git merge feat/ui-evaluation
   pytest -q
   python -m course_qa.app  # verify app starts
   ```

### After each merge
- [x] `pytest -q` passes with zero failures (106 passed)
- [x] No import errors or missing optional dependencies
- [x] No broken cross-module references

---

## End-to-end verification (hour 5–6)

- [x] `python -m course_qa.app` starts successfully on `localhost:7860`
- [x] AOA typed-note question works with note citation (`[S1]`)
- [x] DS code question works with function citation (`BinarySearchTree.c::insert`)
- [x] Web toggle off → zero web calls made
- [x] Web toggle on → web citations shown separately (`[W1]`)
- [x] Out-of-corpus question → abstention/warning triggered
- [x] Subject filter works (`DS`-only, `AOA`-only)
- [x] Page images display in gallery for PDF citations
- [x] Sources table shows accurate metadata

---

## Evaluation (hour 6–7)

- [x] Run 15 benchmark questions from `data/evaluation/questions.csv`
- [x] Record Hit@3 and Hit@5 retrieval accuracy
- [x] Record citation validity
- [x] Record abstention behavior
- [x] Fill in `docs/EVALUATION.md`
- [x] Document OCR pilot status (281 handwritten pages pending full OCR pass)

---

## Final demo prep (hour 7–8)

- [x] 3-minute demo script prepared and rehearsed (`docs/DEMO_SCRIPT.md`)
- [x] Demo covers: typed note question, code question, web question, abstention
- [x] Report outline prepared (`docs/EVALUATION.md`)
- [x] All test results documented (106 tests passing, Hit@5=78.6%, Citation Validity=100%)
- [x] Known limitations listed (handwritten OCR pilot, zero typed notes in DS)
- [x] Entrypoint ready (`run.py` & `python -m course_qa.app`)

---

## Critical rules

- **Never commit**: `.env`, raw notes, page image PNGs, Qdrant storage, `chunks.jsonl`
- **Never modify without approval**: `schemas.py`, `contracts.py`, `config.py`
- **Always run**: `pytest -q` before merging
- **Always report**: actual empirical results honestly — do not claim untested features work
