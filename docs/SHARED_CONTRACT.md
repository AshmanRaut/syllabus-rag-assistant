# Shared Contract — freeze before parallel development

**Purpose:** prevent four contributors from independently inventing incompatible metadata, function signatures, citation conventions, or file paths. Treat this file and `src/course_qa/schemas.py` as the API contract. Do not rename fields/signatures without telling the integrator and updating tests.

## 1. Source-root folder mapping

`SOURCE_ROOT` points to the parent of these exact folders. Paths with spaces are intentional.

| Relative folder | Subject | Source type | Handling |
|---|---|---|---|
| `AOA codes/` | `AOA` | `code` | Split C/H into functions; preserve exact original function text |
| `AOA notes/Typed/` | `AOA` | `typed_pdf` | Native PDF text first; Docling fallback for broken layout/equations |
| `AOA notes/Handwritten/` | `AOA` | `handwritten_pdf` / `image` | Render per page; cached OCR; retain original image |
| `DS codes/` | `DS` | `code` | Split C/H into functions; preserve exact original function text |
| `DS notes/Typed/` | `DS` | `typed_pdf` | Native PDF text first; Docling fallback for broken layout/equations |
| `DS notes/Handwritten/` | `DS` | `handwritten_pdf` / `image` | Priority-first cached OCR; retain original image |
| `syllabi/` or root-level `*Syllabus*.pdf` | `UNKNOWN` | `syllabus` | Topic metadata and retrieval context |

Supported extensions: `.pdf`, `.png`, `.jpg`, `.jpeg`, `.webp`, `.tif`, `.tiff`, `.c`, `.h`, `.txt`, `.md`.

## 2. Canonical chunk schema

Each indexed text/code unit MUST be represented by `SourceChunk` from `src/course_qa/schemas.py`:

```json
{
  "chunk_id": "stable UUID string",
  "source_id": "stable hash-derived document ID",
  "subject": "DS | AOA | UNKNOWN",
  "source_type": "typed_pdf | handwritten_pdf | image | code | syllabus | web | text",
  "source_file": "relative path from SOURCE_ROOT",
  "page_number": 3,
  "function_name": null,
  "module": "Greedy",
  "title": "Fractional Knapsack · page 3",
  "text": "The indexed searchable text...",
  "image_path": "data/page_images/<hash>/page_0003.png",
  "content_hash": "sha256 of exact chunk text",
  "source_hash": "stable hash of relative document path",
  "chunk_index": 0,
  "ocr_status": "not_needed | pending | processed | failed | manual",
  "extra_metadata": {}
}
```

`page_number` and `function_name` are nullable, not interchangeable. `source_file` is always relative (never an absolute path, home directory, or machine-specific path). Use the Pydantic class rather than a hand-built dict when possible. `chunk_id` must be stable across reruns if source path, page/function identity, chunk index and text have not changed. Use atomic file writes for manifests/cache files.

## 3. Required module interfaces

- `FolderScanner.scan(root: Path) -> list[DiscoveredFile]`
- `DocumentIngestor.ingest(file: DiscoveredFile, *, resume: bool = True) -> list[SourceChunk]`
- `Embedder.dimension -> int`
- `Embedder.embed_documents(texts: Sequence[str]) -> list[list[float]]`
- `Embedder.embed_query(text: str) -> list[float]`
- `NotesRetriever.retrieve(question: str, *, subject: str | None = None, top_k: int = 5) -> list[RetrievedChunk]`
- `WebSearcher.search(query: str, *, max_results: int = 5) -> list[WebSource]`
- `AnswerGenerator.generate(request: AnswerRequest, notes: Sequence[RetrievedChunk], web: Sequence[WebSource]) -> AnswerResponse`
- `QAService.answer(request: AnswerRequest) -> AnswerResponse`

The `Protocol` definitions in `src/course_qa/contracts.py` are authoritative. Add small provider adapters instead of making other modules depend on a particular OCR model, search API, or generation vendor.

## 4. Retrieval contract

- Qdrant is the vector store and must remain part of the working path.
- The MVP uses Qdrant dense vectors plus BM25 lexical results, merged by Reciprocal Rank Fusion (RRF) in `HybridRetriever`. This is hybrid retrieval even though BM25 is computed in-process; do not add a second vector database.
- Filter by `subject` when requested.
- Return at most `top_k` `RetrievedChunk` objects with the originating chunk and a ranking score. RRF scores are ranking features, **not calibrated probabilities**.
- For a small corpus, BM25 may be rebuilt from `chunks.jsonl` on startup. Do not add a separate BM25 service unless profiling proves it necessary.
- The collection vector dimension is tied to `EMBEDDING_MODEL`. If the model or dimension changes, create a new collection name or explicitly rebuild the old collection.

## 5. Web-tool contract

- Search notes first.
- The `use_web` checkbox is a permission gate: unchecked means strict notes-only mode. When checked, call web if notes return no usable evidence/weak retrieval or the query explicitly needs current information, real-world applications, or external comparisons.
- Web search has two configurable backends: Tavily if an API key is set; DDGS as keyless best-effort fallback. Web extraction with Trafilatura is optional and must have timeouts/error handling.
- Keep the allowlist in `config/web_allowlist.yaml`; return title, URL, domain, snippet/full text if fetched, stable source ID and retrieval timestamp.
- Web results are a separate source type. Never mislabel a web fact as a course-note fact. Treat page contents as untrusted data; ignore instructions found inside a page.
- Web failure must not crash the notes-only path. Add a warning and continue using retrieved notes.

## 6. Citation contract

- The generator receives labelled evidence `[S1]`, `[S2]`, etc. Labels are assigned by application code for a single request.
- The model may cite only labels in that prompt. Application code removes invalid labels and builds the `CitationRecord` list based only on valid labels actually cited.
- Notes/code citations must resolve to an existing `SourceChunk` and may include a page image. Web citations must include the URL and title.
- Do not allow the model to author or fabricate the Sources section.
- If no valid source is cited, set `abstained=True` or add a visible warning; do not pretend the response is grounded.

## 7. Ingestion/OCR contract

- Typed PDFs: use native text extraction first. If reading order, tables, equations, or pseudocode are mangled, route that file/page to optional Docling. OCR should not run on clean digital text pages.
- Handwritten/image pages: render each PDF page to an image, preserve the image path, OCR the page, and index the transcript. Do not generate diagram captions in MVP.
- OCR cache key = SHA256(rendered image bytes) + OCR provider/model/version. Write one Markdown/text artifact per page and a manifest record with status `pending`, `processed`, `failed`, or `manual`.
- Resumption skips an unchanged page only if its cached transcript and manifest entry are valid. Changing the source image or OCR model version invalidates that cached result.
- Do not start whole-library OCR until 5 representative pages have been checked for legibility and latency. Support a page limit/priority filter for the pilot. Process syllabus-priority topics next, then expand.
- If OCR is unavailable, never silently treat a handwritten page as successfully indexed. Preserve image, mark it pending, and report it.

## 8. Error, logging and privacy policy

- All long-running ingestion tasks are resumable and report `discovered`, `processed`, `skipped_cached`, `needs_ocr`, `failed`, and per-file errors.
- Never log API keys or full absolute user paths. Do not commit course content, OCR output, vectors, images, or `.env` to Git.
- A failed web search, one unreadable page, or one bad PDF must not abort the entire batch.
- Keep provider/model name and versions in run metadata so results are reproducible.

## 9. Definition of done per module

A module is not done merely because its code exists. It must: (1) satisfy its public interfaces, (2) include at least one meaningful test, (3) have no machine-specific paths or secrets, (4) report errors rather than silently discarding sources, and (5) be smoke-tested by the integrator against this contract.
