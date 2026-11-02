# Complete Build Plan — Syllabus-Aware NLP Assistant for DS and AoA

**Target:** demonstrable one-day mini-project, four contributors.  
**Primary discipline:** NLP — document preprocessing, OCR as text acquisition, chunking, semantic and lexical retrieval, hybrid ranking, evidence-grounded generation, citations, and evaluation.  
**Required stack choices:** Qdrant stays in the retrieval stack; web search stays in the answer pipeline; the user's existing directory structure is the ingestion contract.

## 1. Project definition

### Title
**Syllabus-Aware Question Answering for Data Structures and Analysis of Algorithms Using Hybrid Retrieval and Grounded Generation**

### Problem statement
Students need exam-style explanations of DS/AoA concepts, dry runs, C code and complexity analysis drawn from their own course material. General-purpose models may miss the exact wording, assumptions, code version, or exam-answer format of course notes. Build a system that retrieves evidence from typed notes, handwritten notes and lab C programs, optionally supplements it with approved web sources, and generates concise or exam-style responses whose cited sources are validated in application code.

### Main question to investigate
Does hybrid retrieval (Qdrant dense retrieval + BM25 lexical retrieval + Reciprocal Rank Fusion) retrieve relevant course evidence more reliably than either dense-only or BM25-only retrieval on a small DS/AoA test set?

### Project objectives
1. Parse the existing notes and code folder layout consistently.
2. Extract searchable text from typed PDFs and C source files; run cached, page-wise OCR on selected handwritten pages.
3. Attach metadata for subject, module/topic, source file, page number, function name, source type and page image.
4. Store dense chunk embeddings in Qdrant, run lexical BM25 retrieval, and fuse rankings.
5. Add notes-first deterministic web routing with Tavily and DDGS as configurable providers.
6. Generate a structured exam response using only retrieved source IDs; programmatically validate cited IDs and build the Sources panel.
7. Evaluate retrieval and grounding on 12–15 manually checked questions.

## 2. Scope: strict MVP boundaries

### In scope
- Both supplied syllabi: Data Structures (DS) and Analysis of Algorithms (AoA).
- Typed PDFs, selected handwritten pages or images, C/H files, and syllabus text.
- PDF page images for source inspection.
- Function-level C-code chunks; preserve original code text.
- Qdrant dense vector index, BM25 and RRF hybrid retrieval.
- Optional web retrieval controlled by a toggle and deterministic fallback rules.
- One configurable LLM adapter, concise/exam answer styles, sources UI and tests.

### Out of scope for the one-day build
- Fine-tuning, LoRA/QLoRA, prompt distillation or a training data-generation pipeline.
- OCR training, guaranteed correct transcription of every handwritten page, or processing every file before integration.
- Diagram captioning, visual-only page retrieval (ColPali/ColQwen), handwritten formula-solving, or promising that a page image was semantically understood.
- Agentic model-controlled tool selection, multiple generators, multiple vector databases, a separate reranker model, user accounts, production deployment or analytics dashboards.
- General-purpose QA outside DS/AoA.

Fine-tuning is deliberately postponed. Establish baseline quality, log failure cases, and only then consider whether a style adapter is warranted. For this project, the NLP contribution is retrieval and grounding, not training a new language model.

## 3. What the uploaded sample files imply

- `AOA_Syllabus.pdf` and `DS_Syllabus.pdf` should seed topic/module metadata and test-question coverage.
- `Fractional_Knapsack.pdf` is a good typed-PDF smoke test; verify that ratios, table columns and algorithm steps survive extraction. If pypdf extraction is garbled, use Docling on those pages/file rather than invoking a VLM on every typed page.
- `Dijkstra.c` and `LinkedList6p.c` are code retrieval tests. Index function bodies as separate chunks but retain the exact parent filename and function name. Before treating retrieved code as an answer, flag known flaws (for example unreachable-vertex handling in Dijkstra and non-void functions that fall through in the linked-list program).
- The supplied `Branch_and_Bound.pdf` and `Linked_List_1.pdf` were not readable by the previous text extraction path. Inspect whether they are image-only PDFs and include them in the OCR pilot rather than assuming their text was extracted.
- All DS notes being handwritten changes the priority: test page-wise OCR early. The entire DS handwritten corpus may not be finished within one day. Do not let full OCR delay the first end-to-end product; start with five representative pages, then syllabus-priority pages, then continue the cached batch if time remains.

## 4. Input folder contract

`SOURCE_ROOT` is the parent directory. Spaces and exact casing below are significant on case-sensitive file systems.

```text
SOURCE_ROOT/
├── AOA codes/
├── AOA notes/
│   ├── Typed/
│   └── Handwritten/
├── DS codes/
├── DS notes/
│   ├── Typed/
│   └── Handwritten/
└── syllabi/                 # optional; e.g. AOA_Syllabus.pdf, DS_Syllabus.pdf
```

Root-level `*Syllabus*.pdf` is also accepted by the starter scanner. Supported source types: PDF, common image files, C/H, TXT and Markdown. Run the scanner first and manually inspect category counts before ingestion.

## 5. Target architecture

```text
existing folder tree
   ├── Typed PDFs ──> pypdf text extraction ──> Docling fallback if extraction is poor
   ├── Handwritten PDFs/images ──> render one page at a time ──> PaddleOCR-VL adapter
   │                                                   └── hash cache + per-page transcript + original image
   ├── C/H files ──> C function splitting ──> one chunk per function
   └── Syllabi ──> text + topic/module metadata
                            │
                            ▼
      SourceChunk schema + JSONL corpus + ingestion manifest
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
       sentence embeddings                BM25 lexical index
             │                             │
             ▼                             │
       Qdrant dense store                  │
             └──────────────┬──────────────┘
                            ▼
                 RRF hybrid retrieval
                            │
               subject filter + top 3–5
                            │
                            ▼
                 deterministic web router
          explicit toggle / weak notes / external-comparison intent
                            │
              ┌─────────────┴──────────────┐
              ▼                            ▼
      course-note evidence           web evidence (separately labelled)
              └─────────────┬──────────────┘
                            ▼
                    prompted generator
                            ▼
              code-validated citation labels
                            ▼
             Gradio answer + Sources + page images
```

### Why this remains an NLP project
The core technical path is text acquisition → text normalisation → chunking and metadata → representation/embedding → lexical and semantic retrieval → ranking fusion → prompt-based generation → grounding/citation validation → evaluation. Qdrant and the web client are supporting infrastructure, not the project's end goal.

## 6. Detailed module decisions

### 6.1 Ingestion and document processing

**Typed PDF path**
1. Extract text by page using native PDF extraction first. Avoid OCR or VLM when a good text layer exists.
2. Run a quality heuristic (characters/page, replacement characters, broken line/table signals). If the output is structurally poor, use optional Docling for the affected file/page.
3. Keep page-number metadata and render page images when needed for the source panel.
4. Chunk around headings/paragraphs, typically 700–1,100 characters with 100–180 characters of overlap. Do not split code or a short algorithm step across chunks unnecessarily.

**Handwritten path**
1. Test five pages that represent ordinary handwriting, formula-heavy notes, and pointer/algorithm diagrams.
2. Render each PDF page to a PNG and compute SHA256 of the image bytes.
3. Use a page-level cache keyed by image hash + OCR provider/model/version. Store one Markdown/transcript per page and a manifest status.
4. Keep the image itself. The retrieval index uses OCR text, while UI opens the exact page image.
5. If handwriting OCR fails, correct only high-priority pages manually. Keep status `manual`; never claim the transcript is model-perfect.
6. Do not ask OCR to caption diagrams. Short human-written descriptions may be added only when time permits and must be labelled as human annotations.

**PaddleOCR-VL note**
Use the official current PaddleOCR-VL Python integration through `PaddleOCRVL().predict(...)`, which returns structured results and supports Markdown export. The official docs include an Apple Silicon path; test exact model/runtime versions on the actual machine. Isolate OCR dependencies from the main app environment. Current reference: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md and Apple Silicon guide: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL-Apple-Silicon.en.md . Model/version may evolve, so record the exact installed version instead of assuming one fixed version string.

**C-code path**
- Split by function, retain source file and exact function name; code chunks should not be character-windowed unless a single function is unusually large.
- If a function's content is long, split with continuation metadata but repeat its function name and file.
- Keep original source and any reviewed/fixed copy separately. Never silently modify user code while indexing it.

### 6.2 Metadata and topic classification

Required fields are defined in `docs/SHARED_CONTRACT.md` and `src/course_qa/schemas.py`. Each chunk needs subject (`DS`, `AOA`, `UNKNOWN`), source type, relative source filename, page or function locator, text, stable hashes and optional image reference. Use syllabus topics as lightweight metadata; do not build a separate classifier model during this sprint. If automatic topic assignment is uncertain, use a keyword/topic map and leave the module unknown rather than inventing one.

### 6.3 Qdrant and hybrid retrieval

MVP design: Qdrant stores dense embeddings; BM25 runs over the same canonical `chunks.jsonl` corpus; the retriever merges both ranked lists using Reciprocal Rank Fusion. This keeps Qdrant central without adding a sparse embedding model, another service, and another installation risk on day one. The team can later migrate sparse vectors into a named Qdrant vector using its Query API if there is evidence it is needed.

Recommended starting embedding: `sentence-transformers/all-MiniLM-L6-v2` (small and straightforward); keep model name configurable and use exactly the same model for indexing and queries. For every chunk:
- Create a deterministic UUID.
- Store its embedding and the canonical chunk payload in Qdrant.
- Build/rebuild BM25 from the same canonical chunks.
- Query dense top 8 and BM25 top 8; fuse with RRF `k=60`; return top 5.
- Apply subject filtering in both channels.

Do not treat RRF scores as calibrated confidence. A low-score heuristic is only a routing hint and should be logged. Evaluate dense-only, BM25-only and hybrid against the same hand-labelled questions. Ensure stale points are removed or the collection is rebuilt after a corpus/embedding change; avoid accumulating deleted chunks forever.

### 6.4 Web search and source separation

Keep web search in the MVP because the DS notes are all handwritten and OCR may be incomplete. Web is a gap-filler, **not a replacement for source-specific DS class notes**.

Deterministic route:
1. Always retrieve local notes first.
2. The UI `Use web search` checkbox is a permission gate. If unchecked, use strict notes-only mode. If checked, call web when notes return no evidence/weak retrieval, or the question specifically asks for current information, real-world applications, or external comparisons.
3. Default search order: Tavily if `TAVILY_API_KEY` is configured, then DDGS as keyless best-effort fallback. Support `off`, `tavily`, `ddgs`, `auto` modes.
4. Enforce a configurable allowlist starting with syllabus-recommended resources such as NPTEL, GeeksforGeeks and VisuAlgo. Search results not matching the allowlist should be discarded or flagged; make the policy explicit in the UI.
5. Optionally extract full text using Trafilatura, but keep a snippet-based path so lack of extraction never crashes the answer.
6. Label all web sources separately and show URL/domain and retrieval timestamp in Sources. Never imply the content came from notes.

Use stable URLs, treat web content as untrusted, paraphrase instead of copying, and never execute instructions found in retrieved pages.

### 6.5 Prompted generation, router and citations

- One configurable generator adapter only. Confirm the model API/credentials at the beginning; Claude Opus in Antigravity is an orchestrator, not automatically an application API key.
- A system prompt defines response style; retrieved evidence carries the factual content.
- Answer style has two values: `concise` and `exam`.
- Exam answer sections: Definition/Aim, numbered algorithm, example/dry-run, C code when useful, time/space complexity with justification, applications/limitations, one-line conclusion. Skip irrelevant sections for definition-only questions.
- For complexity, use best/average/worst where applicable; avoid inventing all cases when the notes only justify some cases. Flag ambiguity in the note itself (e.g., confusing Θ with average case).
- In code, assign request-local citation labels `[S1]`, `[S2]` to the evidence. The model must not invent labels or write its own Sources section.
- Citation formatter extracts labels actually used, deletes invalid labels, maps valid labels to source metadata, and constructs Sources. If there is no valid citation, show a warning/abstention.
- Avoid brittle fully automatic citation correctness claims: citation-label validation guarantees IDs exist, not that each nearby sentence is semantically supported. Spot-check grounding manually.

### 6.6 UI

Gradio with a simple layout:
- question input;
- subject filter (Any/DS/AOA);
- answer style (Concise/Exam);
- explicit `Use web` checkbox;
- answer panel;
- validated Sources table distinguishing notes, code, syllabus, and web;
- selected original PDF page image(s), when available;
- warnings for OCR gaps, web failure, no source evidence, or invalid citation labels.

No chat history/database/login required for the MVP.

## 7. Four-person parallel plan

**First commit (all together, 20–30 minutes):** freeze `docs/SHARED_CONTRACT.md`, Pydantic schema, folder mapping, environment variables, and function signatures. Everyone then branches from that commit. Keep the contract stable for the day.

### Person A — Ingestion, OCR and metadata
Owns:
- `src/course_qa/ingestion/*`
- `scripts/scan_sources.py`, `scripts/ingest.py`
- ingestion tests and OCR pilot notes

Tasks:
1. Verify folder scan counts against real directory tree.
2. Implement typed page extraction with Docling fallback for poor PDFs.
3. Implement PaddleOCR-VL adapter, image-hash cache, atomic per-page transcript and manifest.
4. Add OCR page limit/priority filter and resume mode.
5. Split code by function; retain code source metadata and original image references.
6. Emit canonical `SourceChunk` records only; no Qdrant or UI code.

Acceptance: scanner recognises folder types, repeated ingestion skips cached pages, OCR failure is reported, and `chunks.jsonl` is valid SourceChunk JSONL.

### Person B — Qdrant, hybrid retrieval and web search
Owns:
- `src/course_qa/retrieval/*`
- `src/course_qa/web/*`
- `scripts/index.py`
- retrieval/web tests

Tasks:
1. Bring up Qdrant locally using Docker Compose.
2. Load/embed chunks, upsert idempotently and filter by DS/AOA.
3. Implement BM25 from canonical chunk text and RRF fusion.
4. Implement Tavily plus DDGS fallback and optional Trafilatura extraction.
5. Keep web results separately labelled, allowlisted and resilient to API failure.
6. Measure top-3/top-5 retrieval on a shared mini-test set.

Acceptance: the same query can return dense-only, BM25-only and hybrid lists for evaluation; subject filters work; web mode `off` works; unavailable web providers do not crash notes retrieval.

### Person C — Answer generation, routing and citations
Owns:
- `src/course_qa/generation/*`
- `src/course_qa/service.py`
- generator/router/citation tests

Tasks:
1. Confirm the answer model/provider/credentials immediately; keep the adapter interface generic.
2. Implement deterministic notes-first router and explicit web toggle.
3. Format retrieved evidence into `[S#]` context blocks and call generator.
4. Validate cited labels against request-local evidence and build Sources from code, not model-generated prose.
5. Implement abstention/warnings for no evidence and web/API failure.
6. Spot-review factual grounding, algorithm complexity and code responses.

Acceptance: no invalid source IDs survive; sources are only records actually cited; when no evidence is available the app says so; note and web provenance is distinguishable.

### Person D — UI, integration, tests and report/demo
Owns:
- `src/course_qa/app.py` and app wiring
- `tests/*` cross-module smoke/integration tests
- `docs/EVALUATION.md`, demo script and project report outline

Tasks:
1. Build Gradio interface against `QAService.answer(AnswerRequest)` only.
2. Display answer, source table, URLs, and original page images.
3. Create 12–15 ground-truth test questions with expected source chunks/pages/functions.
4. Add integration smoke test that uses fake generator/search adapter if API credentials are absent.
5. Track tests and start an integration checklist; do not wait for OCR or the final generator to create UI wiring.
6. Prepare a repeatable 3-minute demo and report results honestly.

Acceptance: app starts, one note-backed question works, one code query works, one web-enabled question shows web citations, and one out-of-corpus question warns/abstains.

### Integrator (one person, usually D; not a separate fifth role)
- Owns `main`, contract changes, merge order, runnable release.
- Accepts changes only if they conform to schemas and tests.
- Keep main branch always runnable. Each teammate opens a small PR/merge or cherry-picks a single-purpose branch; avoid parallel edits to `schemas.py`, `service.py`, and app entrypoint.

## 8. Critical path for one build day

| Elapsed time | Required outcome | Action if it slips |
|---|---|---|
| 0:00–0:30 | Frozen contract, env file, sample 12–15 questions | No coding past this point until schemas/functions agree |
| 0:30–1:30 | Scanner counts files; Qdrant and generator smoke-tested independently; 5 handwritten pages pilot started | Disable optional integrations that are blocking setup |
| 1:30–3:00 | Chunks JSONL from typed PDFs, code and available OCR pages; BM25/Qdrant indexing works | Manually transcribe priority pages; keep ingestion resumable |
| 3:00–4:00 | Hybrid retrieval plus source IDs works | Use simple RRF; postpone Qdrant sparse-native upgrade |
| 4:00–5:00 | First end-to-end Q&A with citations | This is the hard integration deadline; freeze features until it works |
| 5:00–6:00 | Web fallback, page-image UI and citation hardening | Web snippets only if full-page extraction is slow |
| 6:00–7:00 | Retrieval/generation evaluation and fixes | No fine-tuning; no visual retrieval |
| 7:00–8:00 | Demo, report, environment notes, clean handoff | Demo only tested capabilities; document unprocessed OCR pages |

All OCR must run asynchronously relative to human development in the sense of being a separate process/job, but the code must be resumable; do not make the software depend on an unbounded background promise. Start the five-page pilot immediately and continue only after the quality check.

## 9. Evaluation plan and success criteria

Use 12–15 fixed queries covering:
- 3 definition/algorithm explanation questions;
- 3 dry-run/example questions;
- 3 code-function questions;
- 2 complexity questions;
- 2 paraphrased questions that test semantic retrieval;
- 2 unsupported/out-of-corpus or external-comparison questions.

Create a CSV with columns: `question_id, question, subject, expected_source_file, expected_page_or_function, relevant_chunk_ids, question_type, use_web_expected`.

Measure/report:
1. `Hit@3` and `Hit@5` for whether at least one expected relevant source is in the top-k.
2. Dense-only versus BM25-only versus hybrid Hit@5.
3. Citation validity rate = valid referenced source labels / all labels emitted before validation, and final invalid-label count (should be zero after filtering).
4. Answer format pass rate using a lightweight checker and human review.
5. Grounding review on five answers: supported/partly supported/unsupported.
6. OCR quality on five handwritten pilot pages: human-estimated legible transcription and obvious code/formula errors.
7. Abstention behavior on at least two unanswerable questions.

Do not claim a general accuracy benchmark. Use the small evaluation to justify trade-offs and explain limits.

## 10. Risk controls

- **OCR too slow or poor:** page-wise cache; process five representative pages first; prioritize syllabus pages; manually correct only high-value pages; leave status pending/failed visibly.
- **Generator/provider credentials missing:** check this during the first 30 minutes; implement adapter interface and use a fake deterministic generator for integration tests meanwhile.
- **Qdrant setup trouble:** use `qdrant-client` persistent local mode as fallback without changing the store interface.
- **PDF equations/reading order broken:** trigger Docling on only those files/pages; don't call a VLM on clean typed documents.
- **Stale or duplicate vector records:** deterministic IDs and upserts; include a documented collection rebuild operation.
- **Bad citation semantics:** valid IDs only prevent fabrication of IDs; manual grounding checks are still needed.
- **Web hallucination or source mixing:** allowlist, web source labels, timestamps, URLs, untrusted-content warning, answer-level source separation.
- **No time for polish:** keep the core RAG flow; discard optional extraction, OCR completeness, fine-tuning and advanced UI effects.

## 11. Commands and checkpoints

```bash
# Setup
python -m venv .venv && source .venv/bin/activate
pip install -e . -r requirements.txt -r requirements-web.txt
cp .env.example .env

# Verify paths before processing
python scripts/scan_sources.py

# OCR pilot: add an OCR page limit to the final CLI before the first full run
# then run cached ingestion
python scripts/ingest.py --resume

# Start Qdrant and build dense index
docker compose up -d qdrant
python scripts/index.py

# UI and tests
python -m course_qa.app
pytest -q
```

Install the optional OCR and Docling stacks only as their owner requires, preferably in dedicated/tested environments. See the current official docs rather than assuming dependencies from another machine will work:
- Qdrant local client and hybrid search: https://qdrant.tech/documentation/search-tuning/hybrid-search/ and https://qdrant.tech/documentation/search/hybrid-queries/
- Docling formats/OCR: https://docling.org/formats
- PaddleOCR-VL inference: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL.en.md
- PaddleOCR-VL Apple Silicon setup: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/pipeline_usage/PaddleOCR-VL-Apple-Silicon.en.md
- Tavily Search API: https://help.tavily.com/articles/4840311948-what-is-the-tavily-search-api

## 12. What is delivered at the end of the day

- A running Gradio prototype.
- A repeatable ingestion/indexing pipeline and resumable OCR cache for the pages processed.
- A Qdrant collection with dense embeddings plus BM25/RRF hybrid retrieval.
- Notes-first web fallback with visible separate web citations.
- Validated source labels and original page images when those sources are cited.
- An evaluation CSV and a short result summary.
- A short list of known limitations, especially unreadable/unprocessed handwritten pages and citation semantics that still require manual review.
