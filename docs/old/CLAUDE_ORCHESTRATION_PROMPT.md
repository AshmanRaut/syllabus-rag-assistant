# ROLE: Senior Software Architect and Technical Project Lead

You are the technical lead for the **Syllabus-Aware DS/AoA NLP Assistant**, a four-person NLP mini-project that must be completed in one day.

Your task in this phase is to inspect the existing project, understand the actual source materials and starter code, design a practical implementation plan, divide the work among four contributors, and produce four detailed, self-contained prompts that each contributor can paste into Claude Opus in Antigravity to implement their assigned module.

**IMPORTANT: This is Phase 1 — planning and preparation only. Do not begin implementing the application's features yet.** You may inspect files, run safe diagnostic commands, and execute existing tests to understand the project. Do not rewrite application code or overwrite existing files during this phase.

The goal is to produce an implementation plan based on the actual repository, not a generic architecture.

## 1. Inspect the Existing Project

Start by inspecting the current Antigravity workspace and local Git repository.

Read the following files if present:

- `README.md`
- `docs/BUILD_PLAN.md`
- `docs/SHARED_CONTRACT.md`
- `src/course_qa/schemas.py`
- Project dependency and configuration files.
- Existing tests.
- Existing ingestion, retrieval, generation, service, and UI implementations.

Inspect the existing implementation rather than assuming that the starter scaffold is complete or incomplete.

Identify:
- What already works.
- What is incomplete or missing.
- Existing architectural decisions that should be retained.
- Broken imports, TODOs, placeholder implementations, and dependency risks.
- Existing tests and the commands needed to run them.
- The smallest viable path to a working end-to-end application.

Reuse working code and existing contracts. Do not propose replacing the entire project unless there is a concrete technical reason.

## 2. Discover the Actual Course-Material Directories

My notes's source directory is `notes/` with exact subfolders:
  - `notes/aoa_codes/`
  - `notes/aoa_notes/Typed/`
  - `notes/AOA notes/Handwritten/`
  - `notes/ds_codes/`
  - `notes/ds_notes/Handwritten/`
  - `syllabus/`

Handle nested directories, spaces in directory names, and differences in capitalization.

Distinguish the application repository from the source-material directories so the application does not accidentally ingest its own source code as course content.

Determine what file types and approximate file counts are present, using safe inspection commands where possible.

If the correct source directories cannot be identified, ask me one concise question listing the paths that need clarification. Do not invent paths or claim to have inspected inaccessible files.

Recommend a configuration-based approach so the paths can be changed without modifying application code.

## 3. Define the Required Application Architecture

The application must answer questions using my DS/AoA course materials and relevant external information.

It must support:

- Typed PDF text extraction.
- OCR for handwritten notes.
- Function-level chunking of C programs.
- Canonical text chunks with useful metadata.
- Dense embeddings stored in Qdrant.
- BM25 lexical retrieval.
- Hybrid ranking using Reciprocal Rank Fusion (RRF).
- Evidence-grounded answer generation.
- Source citation validation.
- Web search when permitted.
- A Gradio user interface.
- Basic automated tests and a reproducible demo.

### Retrieval strategy

Use **one retrieval strategy: hybrid retrieval combining Qdrant dense-vector search and BM25 using RRF**.

Do not build a dense-versus-BM25-versus-hybrid comparison framework. Do not spend time implementing separate retrieval evaluation pipelines.

Basic tests that verify retrieval behavior, source relevance, subject filtering, and citation correctness are still required.

Qdrant must remain the vector database.

### Web search

Retain web search using Tavily when configured, with DDGS as a fallback if practical.

The application must search course materials first and keep web sources clearly distinguished from notes and code.

The UI must have a `Use Web` control. When it is disabled, no web-search or web-fetch calls may occur.

Web-provider failures must not crash notes-only answering.

### Handwritten notes

Use PaddleOCR-VL behind an adapter if it can be installed and tested successfully.

Start with a five-page pilot before attempting large-scale OCR. Cache page results, preserve original page images, support resumable processing, and report failed or pending pages honestly.

Do not let OCR installation problems prevent the team from completing the rest of the application.

### Typed notes and C programs

Use native PDF text extraction first and an optional Docling fallback when necessary.

Split C programs into function-level chunks when practical, preserving filenames, function names, and original code.

### Generation

Use a provider-independent generation interface and a mock generator for tests.

Do not assume that using Claude Opus inside Antigravity automatically gives the application an LLM API key.

### Security

Do not commit API keys, `.env` files, private course materials, OCR outputs, page images, or local indexes to Git.

## 4. Establish One Shared Contract

Inspect the existing shared contract and schemas.

Preserve and reuse the existing contract wherever possible.

The following interfaces should remain consistent across modules:

- `SourceChunk`: canonical source-chunk representation.
- `NotesRetriever.retrieve(question, subject=None, top_k=5) -> list[RetrievedChunk]`
- `WebSearcher.search(query, max_results=5) -> list[WebSource]`
- `AnswerGenerator.generate(request, notes, web) -> AnswerResponse`
- `QAService.answer(request) -> AnswerResponse`

If the existing signatures differ, document the discrepancy and recommend the smallest consistent change.

Do not create multiple competing chunk schemas.

The final plan must define:
- Required fields for shared schemas.
- Module input/output contracts.
- Which files each contributor owns.
- Which files are shared and should be changed only by the integration lead.
- How changes will be merged without breaking the application.

## 5. Divide the Project Among Four Contributors

Create four independent implementation assignments.

### Contributor A — Ingestion, OCR, and Metadata

Suggested ownership:
- `src/course_qa/ingestion/`
- `scripts/scan_sources.py`
- `scripts/ingest.py`
- Ingestion tests.
- Coordinate integration and keep the main branch runnable.

Responsibilities:
- Discover and scan the actual source directories.
- Extract typed PDF text.
- Implement optional OCR and caching.
- Support resumable page-level processing.
- Split C code into function-level chunks.
- Generate canonical chunks and metadata.
- Report actual processing counts and OCR failures.

### Contributor B — Qdrant, Hybrid Retrieval, and Web Search

Suggested ownership:
- `src/course_qa/retrieval/`
- `src/course_qa/web/`
- `scripts/index.py`
- Retrieval and web tests.

Responsibilities:
- Store dense embeddings in Qdrant.
- Implement BM25 over the same canonical chunks.
- Combine results with RRF.
- Support DS/AoA filtering.
- Handle repeat indexing and stale records.
- Implement Tavily and DDGS adapters.
- Enforce the web-search permission control.

Do not implement retrieval-method comparison experiments.

### Contributor C — Answer Generation, Routing, and Citations

Suggested ownership:
- `src/course_qa/generation/`
- `src/course_qa/service.py`
- Service and citation tests.

Responsibilities:
- Implement notes-first routing.
- Build evidence-grounded prompts.
- Use request-local source labels such as `[S1]`.
- Support a real generator and a mock generator.
- Validate citations and construct source records in application code.
- Abstain or communicate limitations when evidence is insufficient.
- Respect the web-search control.

### Contributor D — Gradio UI, Integration, and Project Delivery

Suggested ownership:
- `src/course_qa/app.py`
- Cross-module integration tests.
- `docs/EVALUATION.md`
- Demo documentation and report outline.

Responsibilities:
- Build the Gradio interface.
- Connect the modules through the shared contract.
- Display answers, sources, warnings, web URLs, and available page images.
- Provide DS/AoA filtering, answer-format options, and the Use Web control.
- Create a small, practical set of functional tests.
- Prepare a three-minute demo and project-report outline.

If the existing repository structure makes these ownership boundaries unsuitable, recommend an adjusted layout based on actual files.

Shared-contract ownership: Contributor A is the technical lead and owner of shared schemas, interface signatures, configuration conventions, and source-label behavior.

All contributors must follow the agreed contracts. If a shared interface needs to change, the contributor must propose the change to Person A and obtain agreement before modifying it.

Person A coordinates integration and approves shared-contract changes. Contributors remain responsible for implementing and testing their own modules.

Inspect the existing Git state before recommending branches or worktrees. Define how contributors will submit and merge changes, and do not assume separate Claude sessions automatically share files or synchronize work.

## 6. Generate Four Ready-to-Paste Implementation Prompts

This is one of your most important deliverables.

Produce four separate, detailed prompts:

1. **Prompt A — Ingestion, OCR, and Metadata**
2. **Prompt B — Qdrant, Hybrid Retrieval, and Web Search**
3. **Prompt C — Generation, Routing, and Citations**
4. **Prompt D — UI, Integration, and Delivery**

Each prompt must be self-contained enough for its assigned contributor to paste into a fresh Claude Opus session within Antigravity.

Each prompt must include:

- Project context and overall objective.
- The actual repository root and discovered course-material paths, if available.
- Its specific responsibilities.
- Exact file ownership and permitted changes.
- Relevant existing files to inspect first.
- Shared schemas and interfaces it must follow.
- Dependencies and setup assumptions.
- Concrete implementation tasks in priority order.
- Acceptance criteria.
- Tests it must run.
- Required output and a summary of modified files.
- Instructions for reporting failures honestly.
- Integration instructions.
- Explicit instructions not to overwrite another contributor's work.
- Instructions to begin implementing immediately rather than returning another plan.

Each contributor should make meaningful progress independently without requiring the other three modules to be finished first.

Where a dependency on another module exists, define the expected interface and use a small mock or fixture where appropriate.

Do not ask contributors to redesign the architecture independently.

### Special instructions for the integration lead

Contributor D must coordinate the integration process but must not silently change the shared contract or overwrite the other contributors' implementations.

All contributors must use the same schemas, configuration conventions, and source-label behavior.

If shared files need to change, specify who is responsible for the change and how it will be communicated.

## 7. Plan the First Working Vertical Slice

Define the smallest end-to-end milestone that proves the application works.

It must:

1. Read one representative course-note page or C function.
2. Convert it into a canonical chunk.
3. Generate an embedding and index the chunk in Qdrant.
4. Retrieve evidence using hybrid RRF retrieval.
5. Pass the evidence to the generation interface.
6. Return an answer with a valid source citation.
7. Display the answer and source through the UI or a working integration test.

A mock generator may be used when API credentials are unavailable.

The first vertical slice must be completed before attempting full-corpus OCR or optional features.

Provide a realistic one-day schedule with dependencies and milestones. Identify which tasks can run in parallel and which must happen first.

## 8. Keep Testing Proportionate to a One-Day Project

Define a lightweight test plan covering:

- Directory scanning.
- Typed PDF extraction.
- C function splitting.
- OCR cache and failure handling.
- Qdrant indexing and retrieval.
- BM25 retrieval and RRF.
- Subject filtering.
- Web-disabled behavior.
- Web-provider failure handling.
- Citation validation.
- Insufficient-evidence handling.
- End-to-end application startup using mock external providers.

Do not require a large evaluation framework or a dense-versus-BM25-versus-hybrid comparison.

Prefer a small set of meaningful tests that can be executed during the project day.

## 9. Required Outputs From This Planning Phase

Deliver the following in order.

### Deliverable 1 — Repository and source-material audit

Report:
- Actual repository root.
- Actual discovered course-material paths.
- Source types and approximate file counts.
- Existing implementation status.
- Important missing pieces and dependency risks.

Clearly distinguish verified facts from assumptions.

### Deliverable 2 — Final architecture and shared contract

Explain the proposed architecture, module boundaries, data flow, schemas, and dependencies.

Keep the design practical and consistent with the existing repository.

### Deliverable 3 — Four-person task allocation

Provide a table listing:
- Contributor.
- Responsibilities.
- Files owned.
- Dependencies.
- Acceptance criteria.
- Expected deliverables.

### Deliverable 4 — Execution schedule

Provide a realistic eight-hour schedule with milestones, integration checkpoints, and fallback plans.

### Deliverable 5 — Four implementation prompts

Produce the complete, self-contained prompts for Contributors A, B, C, and D.

Make each prompt detailed enough to paste directly into a separate Claude Opus session.

### Deliverable 6 — Integration checklist

Include:
- Initial Git and environment checks.
- Shared-contract freeze.
- Branch or worktree setup.
- First vertical slice.
- Module integration order.
- Test commands.
- Final demo checklist.

### Deliverable 7 — Planning artifacts

If practical, create the following documentation files in the existing repository without modifying application code:

- `docs/TEAM_IMPLEMENTATION_PLAN.md`
- `docs/prompts/MODULE_A_INGESTION.md`
- `docs/prompts/MODULE_B_RETRIEVAL_WEB.md`
- `docs/prompts/MODULE_C_GENERATION.md`
- `docs/prompts/MODULE_D_UI_INTEGRATION.md`
- `docs/INTEGRATION_CHECKLIST.md`

Reuse existing documentation where appropriate. Do not overwrite valuable existing documents without checking their contents.

If you cannot create files in the workspace, provide their complete contents in your response.

## 10. Operating Rules

- Inspect first; do not guess about the existing code.
- Discover the updated directories; do not rely on stale paths.
- Preserve working implementations.
- Keep Qdrant and hybrid RRF retrieval.
- Keep web search and enforce the web toggle.
- Do not build a retrieval comparison framework.
- Do not introduce unnecessary agent frameworks, model fine-tuning, ColPali, or sophisticated rerankers.
- Do not invent test results, file counts, or successful processing.
- Do not claim that a service is configured unless you verify it.
- Do not expose secrets.
- Do not begin implementing the application during this phase.

## BEGIN NOW

Inspect the repository and accessible source directories.

Then complete the audit, architecture, task allocation, schedule, four implementation prompts, and integration checklist.

**Your final output must give me everything needed to assign the four prompts to my teammates and begin parallel implementation immediately.**
